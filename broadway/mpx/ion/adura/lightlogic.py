"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
"""
from mpx.lib import msglog

from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import as_boolean

from mpx.lib.exceptions import EResourceError
from mpx.lib.exceptions import EConnectionError
from mpx.lib.exceptions import ETimeout

from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent

from mpx.lib.threading import Lock
from mpx.lib.threading import Condition
from mpx.lib.threading import Queue
from mpx.lib.threading import ImmortalThread

from mpx.lib.thread_pool import NORMAL

from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import ScheduleChangedEvent

from moab.linux.lib import uptime
 
from mpx.lib.scheduler import scheduler

from mpx.lib import msglog
from mpx.lib.msglog.types import ERR
from mpx.lib.msglog.types import WARN
from mpx.lib.msglog.types import INFO

from mpx.lib.adura.gateway import XCommandIface
from mpx.lib.adura.gateway import SerialFramerIface
from mpx.lib.adura.framedef import AduraFrame

import time

#Adura XML-RPC constants
ADURA_CLR_SCHED = 1536
ADURA_SET_SCHED_DAY = 1792
ADURA_SET_SCHED_HOUR = 2304
ADURA_SET_SCHED_MIN = 2560
ADURA_SET_SCHED_GROUP = 2816
ADURA_SET_SCHED_ACTION = 2048
ADURA_ALL_LIGHT_POINTS_GRP = 12
ADURA_ALL_LIGHT_POINTS_ADDR = 65535
ADURA_SCHED_MSG_DELAY = 2

# Adura LightLogic wireless gateway
class Gateway(CompositeNode):
    def __init__(self):
        self.lightpoints = {}
        self.running = False
        self.endpoint = None
        self.lh = None
        self._seq_num = 1
        self._sched_lock = Lock()
        super(Gateway, self).__init__()
        
    def configure(self, cd):
        super(Gateway, self).configure(cd)
        set_attribute(self, 'address', REQUIRED, cd)
        set_attribute(self, 'debug', 1, cd, int)
        set_attribute(self, 'net_grp_id', 125, cd, int) # network net_grp_id
        set_attribute(self, 'rpc_port', 9003, cd, int)
        set_attribute(self, 'serial_forwarder_port', 9001, cd, int)
        if self.running is True:
            # force endpoint reconfiguration
            if self.endpoint and self.endpoint.connection_ok():
                self.endpoint.close_connection()
            self.running = False 
            self.start() 
        
    def configuration(self):
        cd = super(Gateway, self).configuration()
        get_attribute(self, 'address', cd)
        get_attribute(self, 'debug', cd)
        get_attribute(self, 'net_grp_id', cd)
        get_attribute(self, 'rpc_port', cd)
        get_attribute(self, 'serial_forwarder_port', cd)
        return cd
        
    def start(self):
        if self.running is False:
            self.endpoint = XCommandIface(
                self.rpc_port, 
                self.address, 
                self.debug
            )
            self.lh = SerialFramerIface(
                self.serial_forwarder_port, 
                self.address, 
                self.debug
            )
            self._thread = ImmortalThread(target=self._run, args=())
            self.running = True
            self._thread.start()
        super(Gateway, self).start()
        
    def stop(self):
        self.running = False
        
    def _run(self):
        while self.running:
            # initialize the communications interface
            try:
                msglog.log('Adura', INFO, 'Initializing XServer SerialFramer connection.')
                self.lh.open_connection()
                msglog.log('Adura', INFO, 'XServer connection succeeded.')
            except EResourceError:
                self.stop()
                msglog.log('Adura', ERR, 'Failed to connect to XServer.')
                raise
            except (EConnectionError, ETimeout):
                msglog.log('Adura', WARN, 'Failed to connect to XServer - attempting to reconnect.') 
                pass
            except:
                # unaccounted for exception - send it to the msglog
                msglog.log('Adura', ERR, 'Failed to connect to XServer.')
                msglog.exception()
            while self.lh.connection_ok():
                msg = None
                try:
                    msg = self.lh.get_next_msg()
                except:
                    # connection will now be closed, re-init comm.
                    msglog.exception(prefix='Ignored')
                if msg:
                    frame = AduraFrame(msg)
                    if self.debug:
                        msglog.log('Adura', INFO, frame.get_value_string())
                    if frame.frame_type == 'lightpoint_data_config':
                        lp = self.lightpoints.get(frame.get('firmware_id'))
                        if lp is not None:
                            lp.update(frame)
            time.sleep(30) #pause before attempting to reconnect
        else: 
            if self.lh.connection_ok():
                self.lh.close_connection()
            self._thread.should_die()
        return
        
    def register(self, lightpoint):
        self.lightpoints[lightpoint.lightpoint_id] = lightpoint
        
    def _check_cov_timeout(self):
        for lp in self.lightpoints:
            if (uptime.secs() - lp._last_update) > lp.group.ttl:
                # generate an ETimeout for the benefit of event consumers
                lp.update({'relayState1':ETimeout()})
        
    def _get_next_seq(self):
        seq = self._seq_num
        self._seq_num += 1
        if self._seq_num >= 0xffff:
            self._seq_num = 1
        return seq
        
    # LightLogic XML-RPC methods follow.  Note, HTTP is *not* used
    # for transport.  It's just a raw socket that begins with a 4-byte 
    # length field followed by xml-rpc based payload.
    
    ##
    # The control command for an individual LightPoint
    # 
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network (125)
    # @param actDevice  The id of the relay (5)
    # @actState  The action (0 = OFF, 1 = ON)
    #
    def actuate(self, dest, act_device, act_state):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':act_device,
                  'actState':act_state}
        if act_device == 12:
            # broadcast to all lightpoints - requires additional param 
            # that is a 16 bit incrementing seq number.
            params['seqNumber'] = self._get_next_seq()
        return self.endpoint.write('xmesh.actuate', params)
            
    ##
    # Clears previous schedule events
    #
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actState  1536
    # @param seqNumber  Unique sequence number for the specific command
    #
    def adura_clear_schedule(self, dest=ADURA_ALL_LIGHT_POINTS_ADDR):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actState':ADURA_CLR_SCHED,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('xmesh.adura_clear_schedule', params)
        
    # The following 5 messages are repeated n times, depending on how many
    # schedule events are required.
    
    ##
    # Sets the day of the schedule event (currently 10 - all days)
    #
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actDevice  Day ID (10) 
    # @param actState  1792
    # @param seqNumber  Unique sequence number for the specific command
    #
    def adura_setschedule_day(self, dest, act_device):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':act_device,
                  'actState':ADURA_SET_SCHED_DAY,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('adura_setschedule_day', params)
        
    ##
    # Sets the number of hours relative to sunrise
    #
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actDevice  The hours 0 - 23 or
    # Sunrise == hour + 128 = number of hours after sunrise
    #            hour + 160 = number of hours before sunrise
    # Sunset == hour + 64 = number of hourse after sunset
    #           hour + 96 = number of hours before sunset
    # @param  actState  2304
    # @param  seqNumber  Unique sequence number for the specific command 
    def adura_setschedule_hour(self, dest, act_device):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':act_device,
                  'actState':ADURA_SET_SCHED_HOUR,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('adura_setschedule_hour', params)
                                                    
    ##
    # Sets the number of minutes relative to adura_setschedule_hour
    #
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actDevice  Minutes (0-60).  Added to hour above
    # @param actState  2560
    # @param seqNumber  Unique sequence number for the specific command 
    #
    def adura_setschedule_minute(self, dest, act_device):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':act_device,
                  'actState':ADURA_SET_SCHED_MIN,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('adura_setschedule_minute', params)
                                                      
    ##
    # Sets the lighting group that the schedule controls.  Currently that is limited to the 
    # "All LightPoints group (12).
    #
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actDevice  The lighting group to actuate
    # @param actState  2816
    # @param seqNumber  Unique sequence number for the specific command 
    #
    def adura_setschedule_group(self, dest):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':ADURA_ALL_LIGHT_POINTS_GRP,
                  'actState':ADURA_SET_SCHED_GROUP,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('adura_setschedule_group', params)
                                                     
    ##
    # Sets the action for the schedule event and initiates the schedule event
    #
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actDevice  0 = Off, 1 = On
    # @param actState  2048
    # @param seqNumber  Unique sequence number for the specific command 
    #
    def adura_setschedule_action(self, dest, act_device):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':act_device,
                  'actState':ADURA_SET_SCHED_ACTION,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('adura_setschedule_group', params)
                                                              
    ##
    # Sets the current date and time.  Date and time are stored in a 32-bit format.
    # Two messages must be sent, the first to set the high word, the latter the low word.
    # 
    # @param destAddress  The LightPoint ID to which the command is sent or 0xffff (all)
    # @param groupId  The network group id of the lighting network
    # @param actDevice  DateTime value (16bit value)
    # @param actState  Which word to set, 0x0502 == high, 0x0501 == low
    # @param seqNumber  Unique sequence number for the specific command 
    #
    def adura_setdatetime(self, dest, act_device, act_state):
        params = {'destAddress':dest,
                  'groupId':self.net_grp_id,
                  'actDevice':act_device,
                  'actState':act_state,
                  'seqNumber':self._get_next_seq()}
        return self.endpoint.write('adura_setdatetime', params)
        
# Date and Time are stored within a LightPoint using a 32-bit format.
# VALUE                             BITFIELD
# Years since 2006 (eg. 2007 == 1)  27:32
# Month (1-12)                      23:26
# Day (1-31)                        18:22
# Hour (0-23)                       13:17
# Minute (0-59)                     7:12
# Second (0-59)                     1:6
def gen_date_time():
    BASE_YEAR = 2006 #LightPoint epoch
    yr, mon, day, hr, min, sec, wday, yday, isdst = time.localtime()
    return ((yr-BASE_YEAR) << 26)|(mon << 22)|(day << 17)|\
           (hour << 12)|(min << 6)|(sec)

#
# A logical grouping of LightPoint motes
class LightingGroup(CompositeNode, EventConsumerMixin):
    def __init__(self):
        self.__server = None
        self.__sched_lock = Lock()
        self.__sched_thread = None
        self.__schedules = Queue()
        self.__pv = None
        super(LightingGroup, self).__init__()
        EventConsumerMixin.__init__(self, self._sched_update,
                                    self._sched_exception)
        return
    
    def configure(self, cd):
        super(LightingGroup, self).configure(cd)
        set_attribute(self, 'group_id', 10, cd, int)
        set_attribute(self, 'ttl', 120, cd, int)
        #@fixme - the ability to store schedules locally in the LightPoint is 
        #currently not being utilized.
        set_attribute(self, 'schedule_link', '', cd)
        # config attr to deal with current Adura scheduling limitations
        # a future version of their API will address XML-RPC scheduling
        # deficiencies.
        set_attribute(self, 'one_schedule_only', 0, cd, as_boolean)
        
    def configuration(self):
        cd = super(LightingGroup, self).configuration()
        get_attribute(self, 'group_id', cd)
        get_attribute(self, 'ttl', cd)
        get_attribute(self, 'schedule_link', cd)
        return cd
        
    def start(self):
        if self.schedule_link:
            try:
                l = as_node(self.schedule_link)
                l.event_subscribe(self, ScheduleChangedEvent)
                self.__sched_thread = Thread(target=self._update_schedules)
                self.__sched_thread.start()
            except:
                msg = '%s: error subscribing to schedule changes' % \
                       self.as_node_url()
                msglog.log('Adura', ERR, msg)
        super(LightingGroup, self).start()
        for x in self.children_nodes():
            #force initial update
            try:
                x.get()
            except:
                pass
        
    def stop(self):
        if self.schedule_link:
            try:
                l = as_node(self.schedule_link)
                l.event_unsubscribe(self, ScheduleChangedEvent)
            except:
                msg = '%s: error unsubscribing from schedule changes' % \
                       self.as_node_url()
                msglog.log('Adura', ERR, msg)
        super(CompositeNode, self).stop()
    
    def get(self, skipCache=0):
        if self.__pv is None:
            count = 0
            in_err = 0
            for x in self.children_nodes():
                try:
                    count += int(x.get())
                except:
                    in_err += 1
            if count >= ((len(self.children_names()) - in_err)/2):
                #set the initial state of the lighting group
                #based on the average present state of the lightpoints
                self.__pv = 1
            else:
                self.__pv = 0
        return self.__pv
    
    #sets all LightPoints that are part of this group
    def set(self, value):
        value = int(value)
        if value < 0 or value > 1:
            raise EInvalidValue()
        self.__pv = value
        for lp in self.children_nodes():
            try:
                lp.set(value)
            except:
                msglog.exception()
        
    def _sched_exception(self, exc):
        msglog.exception()
        
    def _sched_update(self, evt):
        if isinstance(evt, ScheduleChangedEvent):
            daily = evt.new_schedule[0]
            schedule = AduraSched(daily)
            self.__schedules.put(schedule)
                
    def _update_schedules(self):
        days = ['sunday', 'monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday']
        day_int_map = {'sunday':0,
                       'monday':1,
                       'tuesday':2,
                       'wednesday':3,
                       'thursday':4,
                       'friday':5,
                       'saturday':6,
                       'all':10}
        while 1:
            sched = self.__schedules.get()
            self._send_sched_msg('adura_clear_schedule')
            if self.one_schedule_only:
                days = ['all']
            for day in days:
                self._send_sched_msg(
                    'adura_setschedule_day', 
                    ADURA_ALL_LIGHT_POINTS_ADDR, 
                    day_int_map[day]
                    )
                for entry in sched.get_entries(day):
                    self._send_sched_msg(
                        'adura_setschedule_hour',
                        ADURA_ALL_LIGHT_POINTS_ADDR,
                        entry.h
                        )
                    self._send_sched_msg(
                        'adura_setschedule_minute', 
                        ADURA_ALL_LIGHT_POINTS_ADDR,
                        entry.m
                        )
                    self._send_sched_msg(
                        'adura_setschedule_group', 
                        ADURA_ALL_LIGHT_POINTS_ADDR
                    )
                    self._send_sched_msg(
                        'adura_setschedule_action', 
                        ADURA_ALL_LIGHT_POINTS_ADDR,
                        entry.value
                    )
        return
        
    def _send_sched_msg(self, method_name, *args):
        getattr(self.server, method_name)(args)
        _sched_pause()
        
    # Adura currently requires a 2 second pause between individual
    # schedule update messages
    def _sched_pause():
        time.sleep(ADURA_SCHED_MSG_DELAY)
            
    def _get_next_sched_entry(self):
        self.__sched_lock.acquire()
        try:
            self.__schedules.reverse()
            s = self.__schedules.pop()
            self.__schedules.reverse()
            return s
        finally:
            self.__sched_lock.release()
        
    def __get_server(self):
        if self.__server is None:
            self.__server = self.parent
        return self.__server
        
    server = property(__get_server)

##
# Actual LightPoint mote
class LightPoint(CompositeNode, EventProducerMixin):
    def __init__(self):
        self.__group = None
        self._value = None
        self._old_value = None
        self._last_update = 0
        self.__cv = Condition()
        super(LightPoint, self).__init__()
        EventProducerMixin.__init__(self)
        
    def configure(self, cd):
        super(LightPoint, self).configure(cd)
        set_attribute(self, 'lightpoint_id', REQUIRED, cd, int)
        set_attribute(self, 'timeout', 2, cd, int)
        #relay number 5 actuates lights
        set_attribute(self, 'relay_num', 5, cd, int)
        
    def configuration(self):
        cd = super(LightPoint, self).configuration()
        get_attribute(self, 'lightpoint_id', cd)
        get_attribute(self, 'timeout', cd)
        get_attribute(self, 'relay_num', cd)
        return cd
        
    def start(self):
        self.parent.parent.register(self)
        super(LightPoint, self).start()
        
    def get(self, skipCache=0):
        rslt = self._value
        # cache miss
        if (uptime.secs() - self._last_update) > self.group.ttl:
            # motes periodically push updates - if it's been silent for 
            # too long force an update.  @fixme: the first read will still
            # return stale data - add blocking call and ETimeout logic
            last = self._last_update
            self.__cv.acquire()
            try:
                try:
                    self._force_update()
                except:
                    # an error using the XCommand interface occured
                    # raise an exception but do not cache the ETimeout
                    msglog.exception()
                    raise ETimeout()
                self.__cv.wait(self.timeout)
                if last != self._last_update:
                    # an update has occurred
                    rslt = self._value
                else:
                    self._last_update = uptime.secs()
                    # let ETimeouts affect our value caching as well,
                    # if a better update comes from the mesh, great.
                    rslt = self._value = ETimeout()
            finally:
                self.__cv.release()
        if isinstance(rslt, ETimeout):
            raise rslt
        return rslt
        
    def set(self, value):
        value = int(value)
        if value < 0 or value > 1:
            raise EInvalidValue()
        self.group.server.actuate(self.lightpoint_id, self.relay_num, value)
        
    def has_cov(self):
        return 1
        
    def event_subscribe(self, *args):
        super(LightPoint, self).event_subscribe(self, *args)
        self._old_value = self.get()
        # generate initial event
        self.event_generate(ChangeOfValueEvent(self, self._old_value, 
                            self._old_value, time.time()))
        
    def _force_update(self):
        ACTION_NONE = 2
        self.group.server.actuate(self.lightpoint_id, self.relay_num, ACTION_NONE)
        
    def update(self, data):
        self.__cv.acquire()
        try:
            self._old_value = self._value
            self._value = data.get('relayState1')
            self._last_update = uptime.secs()
            self.__cv.notifyAll()
            self.event_generate(ChangeOfValueEvent(self, self._old_value, 
                                self._value, time.time()))
        finally:
            self.__cv.release()
        
    def __get_group(self):
        if self.__group is None:
            self.__group = self.parent
        return self.__group
        
    group = property(__get_group)
    
##
# helper classes to manage schedule entries
class AduraSchedEntry(object):
    def __init__(self, t, value):
        h, m, s = t.split(':')
        self.h = int(h)
        self.m = int(m)
        if value.upper() in ['ON', 'OFF']:
            self.value = {'ON':1, 'OFF':0}.get(value)
        else:
            self.value = int(value)
    
class AduraSched(object):        
    def __init__(self, daily):
        # all key == temp hack to deal with their current 
        # limitations.  Presently each day must follow the
        # same schedule
        self.__days = {
            'sunday':[],
            'monday':[],
            'tuesday':[],
            'wednesday':[],
            'thursday':[],
            'friday':[],
            'saturday':[],
            'all':[]
            }
        have_entry = False
        for day in daily:
            day_name = day[0]
            if day_name not in self.days.keys():
                continue
            for entry in day:
                t = entry[1]
                value = entry
                self.__days.get(day_name).append(SchedEntry(t, value))
                if not have_entry:
                    have_entry = True
            if have_entry and not self.__days.get('all'):
                # one entry to rule them all
                self.__days.get('all').append(self.__days.get(day_name))
        
    def get_entries(self, day):
        return self.__days.get(day, [])
    
        

"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
##
# module provides support for Vaisala's WXT510 weather
# transmitter.
# TODO:
#   1) add optional crc support
#   2) Test in 'polled' mode
#   3) Better support for dynamic reconfigurations
from mpx.lib.node import CompositeNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib import threading

from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent

from mpx.lib.scheduler import scheduler

from mpx.lib.exceptions import ETimeout

from mpx.lib import msglog
from mpx.lib.msglog.types import WARN

from moab.linux.lib import uptime

from mpx.lib.thread_pool import NORMAL

import array
import time
import Queue

##
# ION modeling a WXT network.  The WXT supports the following
# communication mechanisms:
#   1) RS-232: ASCII automatic and polled
#   2) RS-232: NMEA 0183 v3.0 automatic and query
#   3) RS-232: SDI-12 v.1.3 and SDI-12 v1.3 continous measurement
#   4) RS-485: ASCII automatic and polled
#   5) RS-485: NMEA 0183 v3.0 automatic and query
#   6) RS-485: SDI-12 v.1.3 and SDI-12 v1.3 continous measurement
#   7) RS-422: ASCII automatic and polled
#   8) RS-422: NMEA 0183 v3.0 automatic and query
#   9) RS-422: SDI-12 v.1.3 and SDI-12 v1.3 continous measurement
#   10)SDI-12 Serial Iface: SDI-12 v.1.3 and SDI-12 v.1.3 continuous measurement
#
# We presently support 1 and 4.  See wxt-user-guide.pdf in cvs for additional
# details.  
class WXT510AsciiNetwork(CompositeNode):
    ##
    # message queue, utilized in Ascii polled mode.
    class CmdQueue(object):
        def __init__(self):
            self.__q = Queue.Queue()
            self.__lock = threading.Lock()
        
        def add_message(self, msg):
            self.__lock.acquire()
            try:
                # only 1 instance of a message need exist
                if not self.__q.queue.count(msg):
                    self.__q.put(msg)
            finally:
                self.__lock.release()
            
        def remove_message(self, msg):
            self.__lock.acquire()
            try:
                if self.__q.queue.count(msg):
                    self.__q.queue.remove(msg)
            finally:
                self.__lock.release()
                
        def next(self):
            self.__lock.acquire()
            has_lock = True
            try:
                if self.__q.qsize() == 0:
                    # release lock to prevent add_message deadlock
                    self.__lock.release()
                    has_lock = False
                # blocks indefinitely if the queue is empty
                msg = self.__q.get()
                if not has_lock:
                    # @fixme - there's a small window here where 
                    # remove_message() of a message that's not in the 
                    # queue could be missed. 
                    self.__lock.acquire()
                # recycle it
                self.__q.put(msg)
            finally:
                self.__lock.release()
            return msg
        
    def __init__(self):
        self.__callbacks = {}
        self.__callback_lock = threading.Lock()
        self._rqst_queue = None
        self.running = False
        self.port = None
        super(WXT510AsciiNetwork, self).__init__()
    
    def configure(self, cd):
        super(WXT510AsciiNetwork, self).configure(cd)
        # protocol == automatic or polled
        set_attribute(self, 'protocol', 'automatic', cd)
        # delay between messages - only applicable in polled mode.
        set_attribute(self, 'intraframe_delay', .25, cd, float)
        # if we've been reconfigured at runtime - see if the line handler
        # needs to be reconfigured
        if self.running:
            self._setup_lh()
        
    def configuration(self):
        cd = super(WXT510AsciiNetwork, self).configuration()
        get_attribute(self, 'protocol', cd)
        get_attribute(self, 'intraframe_delay', cd)
        return cd

    def start(self):
        if self.running is False:
            self._setup_lh()
            self._thread = threading.ImmortalThread(target=self._run, args=())
            self.running = True
            self._thread.start()
        super(WXT510AsciiNetwork, self).start()
        
    def stop(self):
        self.running = False
        
    def _setup_lh(self):
        if self.protocol == 'polled' and not self._rqst_queue:
            self._rqst_queue = self.CmdQueue()
        elif self.protocol == 'automatic':
            self._rqst_queue = None
        if self.protocol == 'polled':
            self._lh_timeout = 2
            self._lh_delay = self.intraframe_delay
        else:
            self._lh_timeout = 300
            self._lh_delay = None
        
    ##
    # Weather station(s) register their interest in a particular
    # message
    def register(self, address, cmd, callback):
        callback_key = (address, cmd.upper(),)
        self.__callback_lock.acquire()
        try:
            if self.__callbacks.get(callback_key):
                if callback in self.__callbacks.get(callback_key):
                    # callback already exits
                    return
                self.__callbacks.get(callback_key).append(callback)
            else:
                self.__callbacks[callback_key] = [callback]
            if self._rqst_queue is not None:
                self._rqst_queue.add_message(address+cmd)
        finally:
            self.__callback_lock.release()
            
    def unregister(self, address, cmd, callback):
        callback_key = (address, cmd,)
        self.__callback_lock.acquire()
        try:
            cbs = self.__callbacks.get(callback_key)
            if cbs:
                idx = cbs.index(callback)
                # delete the callback, even if it's empty, leave
                # the callback list and dict key in place
                del cbs[idx]
                if self._rqst_queue is not None:
                    self._rqst_queue.remove_message(address+cmd)
        finally:
            self.__callback.lock.release()
            
    # update nodes that have registered interest.
    def _distribute_results(self, msg):
        address = msg[0].upper()
        cmd = msg[1:3].upper()
        callback_key = (address, cmd,)
        callback_list = self.__callbacks.get(callback_key)
        if callback_list:
            for cb in callback_list:
                cb(msg)
        
    def _run(self):
        if self.protocol == 'automatic':
            self._lh_timeout = 300
            self._lh_delay = None
        else:
            self._lh_timeout = 2
            self._lh_delay = self.intraframe_delay
        self.port = self.parent
        if not self.port.is_open():
            self.port.open()
            self.port.drain()
        while self.running:
            rx_buff = array.array('c')
            snd_buff = array.array('c')
            if self._rqst_queue is not None:
                try:
                    msg = self._rqst_queue.next().upper() + '\r\n'
                except AttributeError:
                    # rqst_queue went away - ie. reconfigured at runtime from 
                    # polled to automatic mode
                    continue
                except:
                    msglog.exception(prefix='Ignored')
                    continue
                snd_buff.fromstring(msg)
                self.port.write(snd_buff)
            in_read = True
            while in_read:
                try:
                    self.port.read(rx_buff, 1, self._lh_timeout)
                except:
                    # throw away what we have and continue
                    in_read = False
                    continue
                if len(rx_buff) >= 3: # addr + \r\n
                    # \r\n terminates message
                    if rx_buff[-2] == '\r' and rx_buff[-1] == '\n':
                        self._distribute_results(rx_buff.tostring())
                        in_read = False
            if self._lh_delay: time.sleep(self._lh_delay)
        else:
            self.port.close()
            self._thread.should_die()
##
# The WXT510 weather station - Composite container
class WeatherStation(CompositeNode):
    def configure(self, cd):
        super(WeatherStation, self).configure(cd)
        # address as string ...
        set_attribute(self, 'address', '0', cd)
    
    def configuration(self):
        cd = super(WeatherStation, self).configuration()
        get_attribute(self, 'address', cd)
        return cd
        
    def start(self):
        MAX = 10000000 #arbitrary max
        timeout = MAX
        for container in self.children_nodes():
            if not isinstance(container, WeatherStationProperties):
                continue
            if container.timeout < timeout:
                timeout = container.timeout
        self.timeout = min(timeout, MAX)
        if self.timeout:
            self.schedule()
        super(WeatherStation, self).start()
        
    def schedule(self):
        self._scheduled = scheduler.seconds_from_now_do(self.timeout, self.run_check_timeouts)
        
    def run_check_timeouts(self):
        NORMAL.queue_noresult(self.check_timeouts)
        
    def check_timeouts(self):
        for prop_container in self.children_nodes():
            if not isinstance(prop_container, WeatherStationProperties):
                continue
            prop_container.check_timeout()
        self.schedule()
##
# Container for resets
class WeatherStationResets(CompositeNode):
    def __init__(self):
        self.__address = None
        self.__lh = None
        super(WeatherStationResets, self).__init__()
    
    def __get_address(self):
        if self.__address is None:
            self.__address = self.parent.address
        return self.__address
        
    address = property(__get_address)
    
    def __get_lh(self):
        if self.__lh is None:
            self.__lh = self.parent.parent
        return self.__lh
        
    lh = property(__get_lh)
    
##
# Supported Weather station reset commands, include
# (XZ) Reset Command - performs a software reset on the WXT
# (ZXRU) Precipitation Counter Reset - resets main hail accumulator
# and duration parameters Rc, Rd, Hc and Hd
# (ZXRI) Precipitation Intensity Reset - resets the rain and hail 
# accumulation and duration parameters Rc, Rd, Hc and Hd
# (XZM) Measurement Reset - interrupts all ongoing measurements
# of the transmitter and starts from the beginning
#
class WeatherStationReset(CompositeNode):
    def __init__(self):
        self.__address = None
        self.__lh = None
        super(WeatherStationReset, self).__init__()
        
    def configure(self, cd):
        super(WeatherStationReset, self).configure(cd)
        set_attribute(self, 'cmd', REQUIRED, cd)
        
    def configuration(self):
        cd = super(WeatherStationReset, self).configuration()
        get_attribute(self, 'cmd', cd)
        return cd
        
    def start(self):
        if self.parent.parent.parent.protocol == 'polled':
            # we're in polled mode - there's stats to reset
            setattr(self, 'set', _set)
        super(WeatherStationReset, self).start()
        
    def get(self):
        return None
        
    def set(self, v):
        msg = '%s: cannot reset stats in automatic mode' % (self.as_node_url())
        msglog.log('wxt510', WARN, msg)
        
    def _set(self, v):
        rslt = self.lh.send_cmd(self.address, self.cmd)
        
    def __get_address(self):
        if self.__address is None:
            self.__address = self.parent.address
        return self.__address
        
    address = property(__get_address)
    
    def __get_lh(self):
        if self.__lh is None:
            self.__lh = self.parent.parent
        return self.__lh
        
    lh = property(__get_lh)
    
##
# Supported Weather Station Properties:
# (R1) Wind Data Measurement:
#       Dn == Wind direction minimum
#       Dm == Wind direction average
#       Dx == Wind direction maximum
#       Sn == Wind speed minimum
#       Sm == Wind speed maximum
#       Sx == Wind speed average
# (R2) Pressure, Temperature and Humidity Data Message:
#       Ta == Air temperature
#       Ua == Relative Humidity
#       Pa == Air Pressure
# (R3) Precipitation Data Message
#       Rc == Rain accumulation
#       Rd == Rain duration
#       Ri == Rain intensity
#       Hc == Hail accumulation
#       Hd == Hail duration
#       Hi == Hail intensity
#       Rp == Rain peak intensity
#       Hp == Hail peak intensity
#
class WeatherStationProperties(CompositeNode):
    def __init__(self):
        self.__address = None
        self.__lh = None
        self._results = {}
        self._last_update = uptime.secs()
        super(WeatherStationProperties, self).__init__()
        
    def configure(self, cd):
        super(WeatherStationProperties, self).configure(cd)
        set_attribute(self, 'cmd', REQUIRED, cd)
        set_attribute(self, 'timeout', 300, cd, int)
        
    def configuration(self):
        cd = super(WeatherStationProperties, self).configuration()
        get_attribute(self, 'cmd', cd)
        get_attribute(self, 'timeout', cd)
        return cd
        
    def start(self):
        self.register()
        super(WeatherStationProperties, self).start()
        
    def get_property(self, name):
        return self._results.get(name, None)
        
    def last_update(self):
        return self._last_update
        
    def check_timeout(self):
        if self.timeout and self._results and\
            self._last_update < (uptime.secs() - self.timeout):
            self._results = {}
            # propagate timeout
            self._update_properties()
        
    def update(self, msg):
        self._last_update = uptime.secs()
        for key_value in msg[4:-5].split(','):
            key, value = key_value.split('=')
            self._results[key] = value #value includes units
        self._update_properties()
        
    def register(self):
        self.lh.register(self.address, self.cmd, self.update)
        
    def _update_properties(self):
        for prop in self.children_nodes():
            if not isinstance(prop, WeatherStationProperty):
                continue
            prop._trigger_cov() #will force cov propagation
        
    def __get_address(self):
        if self.__address is None:
            self.__address = self.parent.address
        return self.__address
        
    address = property(__get_address)
    
    def __get_lh(self):
        if self.__lh is None:
            self.__lh = self.parent.parent
        return self.__lh
        
    lh = property(__get_lh)
    
class WeatherStationProperty(CompositeNode, EventProducerMixin):
    def __init__(self):
        self.__container = None
        self.__raw_units = 'Unknown'
        self._last_value = None
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        
    def configure(self, cd):
        super(WeatherStationProperty, self).configure(cd)
        set_attribute(self, 'prop_id', REQUIRED, cd)
        
    def configuration(self):
        cd = super(WeatherStationProperty, self).configuration()
        get_attribute(self, 'prop_id', cd)
        cd['units'] = self._get_units()
        cd['units'] = self._get_description()
        return cd
        
    def get(self, skipCache=0):
        rlst = None
        rslt = self.container.get_property(self.prop_id)
        if rslt is not None:
            #The WXT can be reconfigured to express properties
            #in different units on the fly - save the current unit
            self.__raw_units = rslt[-1] 
            rslt = rslt[:-1]
            try:
                rslt = float(rslt)
            except:
                pass
        # in automatic mode, not all values update continuously.
        # precipitation data, f.e., only updates when it's raining.
        # in these instances, allow the user to simply return 0
        # instead of raising a timeout.
        elif self.parent.timeout:
            raise ETimeout()
        else:
            rslt = 0
        return rslt
        
    def has_cov(self):
        return 1
        
    def event_subscribe(self, *args):
        EventProducerMixin.event_subscribe(self, *args)
        try:
            self._last_value = self.get()
        except:
            self._last_value = None
        # generate initial event
        self.event_generate(ChangeOfValueEvent(self, self._last_value, self._last_value, time.time()))
                
    def _trigger_cov(self):
        try:
            v = self.get()
        except:
            v = ETimeout()
        cov = ChangeOfValueEvent(self, self._last_value, v, time.time())
        self.event_generate(cov)
        self._last_value = v
        
    def _get_units(self):
        return get_units_info(self.prop_id, self.__raw_units).get('units')
        
    def _get_description(self):
        return get_units_info(self.prop_id, self.__raw_units).get('description')
        
    def __get_container(self):
        if self.__container is None:
            self.__container = self.parent
        return self.__container
        
    container = property(__get_container)
    
def get_units_info(property, raw_units):
    u_info = {'Sn':{'descr':'Wind speed minimum', 
                    'unit_map':{'M':'m/s', 'K':'km/h', 'S':'mph', 'N':'knots'}},
              'Sm':{'descr':'Wind speed average',
                    'unit_map':{'M':'m/s', 'K':'km/h', 'S':'mph', 'N':'knots'}},
              'Sx':{'descr':'Wind speed maximum',
                    'unit_map':{'M':'m/s', 'K':'km/h', 'S':'mph', 'N':'knots'}},
              'Dn':{'descr':'Wind direction minimum',
                    'unit_map':{'D':'deg'}},
              'Dm':{'descr':'Wind direction average',
                    'unit_map':{'D':'deg'}},
              'Dx':{'descr':'Wind direction maximum',
                    'unit_map':{'D':'deg'}},
              'Pa':{'descr':'Air pressure',
                    'unit_map':{'H':'hPa', 'P':'Pa', 'B':'bar', 'M':'mmHg', 'I':'inHg'}},
              'Ta':{'descr':'Air temperature',
                    'unit_map':{'C':'C', 'F':'F'}},
              'Tp':{'descr':'Internal temperature',
                    'unit_map':{'C':'C', 'F':'F'}},
              'Ua':{'descr':'Relative humidity',
                    'unit_map':{'P':'%RH'}},
              'Rc':{'descr':'Rain accumulation',
                    'unit_map':{'M':'mm', 'I':'in'}},
              'Rd':{'descr':'Rain duration',
                    'unit_map':{'S':'s'}},
              'Ri':{'descr':'Rain intensity',
                    'unit_map':{'M':'mm/h', 'I':'in/h'}},
              'Rp':{'descr':'Rain peak intensity',
                    'unit_map':{'M':'mm/h', 'I':'in/h'}},
              'Hc':{'descr':'Hail accumulation',
                    'unit_map':{'M':'hits/cm2', 'I':'hits/in2', 'H':'hits'}},
              'Hd':{'descr':'Hail duration',
                    'unit_map':{'S':'s'}},
              'Hi':{'descr':'Hail intensity',
                    'unit_map':{'M':'hits/cm2h', 'I':'hits/in2h', 'H':'hits/h'}},
              'Hp':{'descr':'Hail peak intensity',
                    'unit_map':{'M':'hits/cm2h', 'I':'hits/in2h', 'H':'hits/h'}},
              'Th':{'descr':'Heating temperature',
                    'unit_map':{'C':'C', 'F':'F'}},
              'Vh':{'descr':'Heating voltage',
                    'unit_map':{'N':'V', 'V':'V', 'W':'V', 'F':'V'}},
              'Vs':{'descr':'Supply voltage',
                    'unit_map':{'V':'V'}},
              'Vr':{'descr':'3.5 V ref. voltage',
                    'unit_map':{'V':'V'}}}
    u_i = u_info.get(property)
    descr = u_i.get('descr')
    try:
        units = u_i.get('unit_map').get(raw_units)
    except:
        units = 'Unknown'
    return {'description':descr, 'units':units}
                    

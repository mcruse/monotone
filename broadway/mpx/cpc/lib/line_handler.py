"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
# mpx/cpc/lib/line_handler.py: Code that handles all direct communication
# between the MFW and a single multi-drop RS232 network of CPC controllers
# (ie connected to a single COM port on a Mediator).
# @author spenner@envenergy.com
# @fixme Need to handle high-index properties (eg Input Points: 952 possible...) in LineHandler._send_req()

import array, string, types, time, math, termios, struct, fcntl
from mpx.ion.host.port import Port
from mpx.lib import threading, msglog, EnumeratedDictionary, EnumeratedValue
from mpx.lib.exceptions import MpxException, ETimeout, EInvalidValue, ENotFound, \
        EDeviceNotFound, ENotStarted, EBusy, ENameInUse
from mpx.cpc.lib import tables
from mpx.cpc.lib.tables import ObjData, ItemData
from mpx.cpc.lib import utils
from mpx.lib.threading import RLock
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER
from mpx.lib import event

class ItemInstData(EnumeratedValue):
    def __init__(self, value, text, inst_nums=None):
        EnumeratedValue.__init__(self, value, text)
        if inst_nums is None:
            inst_nums = {0:0}
        self.instance_nums = inst_nums
        return
    def __new__(klass, value, text, inst_nums=None):
        return EnumeratedValue.__new__(klass, value, text)
    
class DevInstData(EnumeratedValue):
    def __init__(self, value, text, dev=None):
        EnumeratedValue.__init__(self, value, text)
        self.dev = dev
        return
    def __new__(klass, value, text, dev=None):
        return EnumeratedValue.__new__(klass, value, text)

##
# class CpcBase: Base class for all Python classes that reflect CPC
# hierarchical objects (Device, Item, Object, Property).
class CpcBase:
    def as_list(self):
        return []
    def __str__(self):
        return str(self.as_list())
##
# class Device: Reflects important data obtained from hardware CPC device, or
# set offline for intended connection to a hardware device.
# self._items: A dict of dicts. 
#  Outer Dict: key = ItemType name, value = instance of Inner Dict
#  Inner Dict: key = Item instance num, value = placeholder 0 (treat this dict as Set)
class Device(CpcBase):
    def __init__(self, id, line_handler, name=None, model=None, revision=None, items=None):
        self._lock = RLock()
        self._id = id
        self._line_handler = line_handler
        self._device_name = name
        if model is None:
            model = 'RMCC' # default is OK; all models support ItemType 1 (ie 'Base')
        self._model_name = model
        self._revision = revision
        self._security_code = None
        self.item_types = None # ref to table
        self._items = None
        if items is None:
            self._items = EnumeratedDictionary({'Base':ItemInstData(1,'Base', {0:0})})
        else:
            self._items = items
        self._PDO = None
        try:
            self._PDO = PersistentDataObject(self.__class__.__name__ + str(id), dmtype=GC_NEVER)
            self._PDO.last_alarm_ID = 0x0000
            self._PDO.load()
        except ENameInUse, e:
            msglog.log('mpx',msglog.types.ERR,'mpx.cpc.lib.line_handler: Attempted to created a duplicate Device object.' \
                            ' Don\'t do that.')
    def as_list(self):
        lst = [None, None, None, None]
        self._lock.acquire()
        try:
            lst = [self._id, self._device_name, self._model_name, self._revision]
        finally:
            self._lock.release()
        return lst
    ##
    # @fixme Maybe replace placeholding "0"-value in innermost dict with Item Name, if available
    def add_item(self, item_type_id_or_name, item_inst_num):
        if self.item_types is None:
            return ENotStarted('Device %u not yet initialized.' % self._id)
        if not self.item_types.has_key(item_type_id_or_name):
            return EInvalidValue('item_type_id_or_name',item_type_id_or_name, \
                                'Cannot add item; bad type ID or name')
        item_type_id = int(self.item_types[item_type_id_or_name])
        item_type_name = str(self.item_types[item_type_id_or_name])
        self._lock.acquire()
        try:
            if self._items.has_key(item_type_id_or_name):
                if self._items[item_type_id_or_name].instance_nums.has_key(item_inst_num):
                    return EInvalidValue('item_inst_num',item_inst_num, \
                                'Item with instance num %u already exists' % item_inst_num)
            else:
                self._items[item_type_id_or_name] = ItemInstData(item_type_id, item_type_name, {item_inst_num:0})
            self._items[item_type_id_or_name].instance_nums[item_inst_num] = 0
        finally:
            self._lock.release()
        return None
    def get_id(self):
        return self.as_list()[0]
    def get_name(self):
        return self.as_list()[1]
    def get_model(self):
        return self.as_list()[2]
    def get_rev(self):
        return self.as_list()[3]
    ##
    # get_item_type_names(): Returns list of ItemType names (eg 'Base')
    # for which at least one Item instance is configured for this device.
    def get_item_type_names(self):
        return self._items.string_keys()
    ##
    # get_item_inst_nums(): Returns list of instance numbers of configured Items
    # of given ItemType.
    # @param item_type_id_or_name ID or name of desired ItemType
    def get_item_inst_nums(self, item_type_id_or_name):
        item_inst_nums = []
        self._lock.acquire()
        try:
            item_inst_nums = self._items[item_type_id_or_name].instance_nums.keys()
        finally:
            self._lock.release()
        return item_inst_nums
    def get_values(self, reqs, wait=1):
        return self._line_handler.get_values(self._id, reqs, wait)
    def get_alarms(self):
        alarm_objs = []
        reqs = [['Alarm',0,'LastId',0,0,0,0,0,None]]
        reqs.append(['Alarm',0,'NumAlarms',0,0,0,0,0,None])
        values = self.get_values(reqs)
        if (values is None) or isinstance(values, Exception):
            msglog.log('mpx',msglog.types.ERR,'Failed to get Alarm LastId and ' \
                            'NumAlarms from device %s, due to error: %s' \
                            % (self._device_name, values))
            return [values]
        last_alarm_ID = values[0][0]
        if (last_alarm_ID != 0):
            msglog.log('mpx',msglog.types.ERR,'Read of Alarm LastId on Device %s ' \
                            'yielded error %s' % (self._device_name, last_alarm_ID))
            return []
        last_alarm_ID = values[0][1]
        if (last_alarm_ID == self._PDO.last_alarm_ID):
            return [] # we've already read this dev's alarms
        num_alarms = values[1][0]
        if num_alarms != 0:
            msglog.log('mpx',msglog.types.ERR,'Read of Alarm NumAlarms on Device %s ' \
                            'yielded error %s' % (self._device_name, num_alarms))
            return []
        num_alarms = values[1][1]
        last_alarm_diff = ((last_alarm_ID - self._PDO.last_alarm_ID) & 0xFFFF)
        if last_alarm_diff < num_alarms:
            num_alarms = last_alarm_diff
        ##
        # @todo Aggregate up to 4 GetAlarmRpt reqs into a single call to _do_pkt_xchg()
        start_id = ((last_alarm_ID + 1 - num_alarms) & 0xFFFF)
        end_id0 = ((last_alarm_ID + 1) & 0xFFFF)
        end_id1 = 0x0000
        if start_id > end_id0:
            end_id1 = end_id0
            end_id0 = 0x10000 # one more than last ID to process
        for cur_alarm_ID in range(start_id, end_id0):
            alarm_objs.append(self._get_alarm_obj(cur_alarm_ID))
        start_id = 0x0000
        for cur_alarm_ID in range(start_id, end_id1):
            alarm_objs.append(self._get_alarm_obj(cur_alarm_ID))
        self._PDO.last_alarm_ID = last_alarm_ID
        self._PDO.save()
        return alarm_objs
    def _get_alarm_obj(self, cur_alarm_ID):
        byte_0 = (cur_alarm_ID & 0xFF)
        byte_1 = ((cur_alarm_ID >> 8) & 0xFF)
        reqs = [['Alarm',0,'GetAlarmRpt',0,byte_1,byte_0,0,0,None]]
        resp_list = self.get_values(reqs)
        if (resp_list is None) or isinstance(resp_list,Exception):
            return resp_list
        alarm_obj = resp_list[0][0]
        if alarm_obj == 0:
            alarm_obj = resp_list[0][1]
            alarm_obj.item = self.item_types[alarm_obj.item] # return EnumVal obj
            if alarm_obj.item.obj_types.has_key(alarm_obj.obj):
                alarm_obj.obj = alarm_obj.item.obj_types[alarm_obj.obj] # return EnumVal obj
            else:
                alarm_obj.obj = EnumeratedValue(alarm_obj.obj,'Obj%s' % alarm_obj.obj) # return EnumVal obj
            alarm_obj.device_name = self._device_name
        return alarm_obj

class AutoDiscDoneEvent(event.Event):
    def __init__(self, code, src):
        event.Event.__init__(self,source=src)
        self.code = code
        return
##
# class LineHandler: MFW creates a single instance of this class for each 
# Mediator COM port to which a CPC multidrop RS232 ("COM C") network is 
# attached. Each instance mediates all communication between "clients" in 
# the MFW and a set of CPC controllers ("servers"). Uses a single thread to
# pass messages between clients and servers.
class LineHandler(event.EventProducerMixin):
    _query_devs = array.array('B', '\r\r#$512\r') # NOT part of UHP; leftover, undocumented call apparently specific to RMCx controllers; NO convenient UHP equivalent!
    ##
    # __init__():
    # @param port Ref to instance of mpx.ion.host.port.Port, OR instance of another class that supports "standard" Port interface
    def __init__(self, port):
        event.EventProducerMixin.__init__(self)
        self._port = port # must support (what will become) "std" port object i/f
        self._lock = RLock()
        self._devices = EnumeratedDictionary()
        self._state = 'stopped'
        self._go = 0
        self._poll_interval = 5.0 # sec
        self._wr_pkt = array.array('B', 512 * '\0') # max UHP pkt size is 512 bytes
        self._rd_buf = array.array('B')
        self._rd_pkt = array.array('B', 7 * '\0') # max UHP pkt size is 512 bytes
        self._rd_pkt_idx = 0
        self._rd_pkt_data_len = 0
        self._pkt_seq_num_gen = 0
        self._start_thread_instance = None
        self._state = 0 # 0:Stopped, 1:Running, 2: CPC modem has preempted Mediator
        self._rd_state = 0
        self.debug_lvl = 2
        self._min_req_interval = 0.1
        self._max_values_per_req = 4
        self._autodisc_period = 30 # sec
        return
    ##
    # start(): Start one-and-only thread.
    def start(self):
        self._state = 0
        self._port.open(0) # want non-blocking, to allow easy response timeouts
        self._start_thread_instance = threading.Thread(None,self._start_thread)
        self._start_thread_instance.start()
        return
    def stop(self):
        self._go = 0
        timeout = 30.0
        self._start_thread_instance.join(timeout) # wait for _start_thread() to end
        self._start_thread_instance = None
        # Do exit cleanup:
        self._port.close()
        self._devices.clear()
        return
    ##
    # get_values(): Reads specified property values from specified device.
    # @param dev_id_or_name ID or name of hardware device instance (eg 3 or 'R006 Encino')
    # @param reqs List of lists of request-addressing data; inner lists contain the following:
    # @key item_type_name Name of ItemType (eg 'Base', 'Circuit', etc.)
    # @key item_inst Instance num of desired item (eg 2 for 2nd Circuit Item)
    # @key obj_type_name Name of ObjectType (eg 'Name', 'CaseTemps', 'Status', etc.)
    # @key obj_idx Array index num for desired instance of ObjectType (eg 3 for 3rd CaseTemps Object)
    # @key prop_type_name Name of PropertyType (eg 'Value', 'Status', 'EngUnits', etc.)
    # @key prop_idx Array index num for desired instance of PropertyType (eg ???)
    # @param wait Whether or not caller wants to wait for query to hardware device
    # @default 1 wait
    def get_values(self, dev_id_or_name, reqs, wait=1):
        dev = None
        values = [] # list of [item_result,item_value]s
        self._lock.acquire()
        try:
            if not self._devices.has_key(dev_id_or_name):
                return EDeviceNotFound('get_values: Dev %s not found.' % dev_id_or_name)
            dev = self._devices[dev_id_or_name].dev
            # Break request list into pkt-sized portions, and send requests:
            num_reqs = len(reqs)
            num_pkts = num_reqs / 4
            if (num_reqs % 4) != 0:
                num_pkts += 1
            for i in range(num_pkts):
                base_idx = i * 4
                cur_reqs = reqs[base_idx:base_idx + min(4, num_reqs - base_idx)]
                item_resp_list = self._do_pkt_xchg(dev._id, 'GetValue', cur_reqs)
                if isinstance(item_resp_list, Exception):
                    values.append(item_resp_list)
                    continue
                elif item_resp_list is None:
                    msglog.log('mpx',msglog.types.ERR,'Failed to receive valid response from Device %s, ' \
                                    'to Request %s' % (dev_id_or_name, cur_reqs))
                    item_resp_list = ['Comm Error']
                values.extend(item_resp_list)
        finally:
            self._lock.release()
        return values
    def set_values(self, dev_id_or_name, prop_addrs, wait=1):
        pass # @todo
    def get_devs(self):
        return self._devices
    ##
    # get_alarms: For entire site (ie for all items on all controllers).
    def get_alarms(self):
        alarm_objs = []
        self._lock.acquire()
        try:
            for dev_inst_data in self._devices.values():
                dev = dev_inst_data.dev
                dev_alarm_objs = dev.get_alarms()
                alarm_objs.extend(dev_alarm_objs)
        finally:
            self._lock.release()
        return alarm_objs
    ##
    # _start_thread(): Thread does autodiscovery, and then monitors changes 
    # in modem line states, particularly CTS. If CTS state ever goes from 1 
    # to 0, then the CPC modem has activated, and a user has probably connected 
    # with UltraSite. If the user made any changes to the site with US, then
    # the MFW should be stopped and restarted, to initiate a new
    # autodiscovery and initialization sequence.
    def _start_thread(self):
        self._go = 0
        end_time = time.time() + self._autodisc_period
        self._devices = EnumeratedDictionary() # clear any devices found previously
        result = 0
        while (time.time() < end_time) or (result != 0):
            result = self._autodiscover()
            time.sleep(0.1) # give mpx.service.hal.alarm.cpc.cpc_client.CpcClient._poll_alarms() thread a chance at get_alarms()
        if (len(self._devices) < 1):
            msglog.log('mpx', msglog.types.WARN, 'CPC LineHandler failed to find ' \
                            'even 1 CPC device. Aborting LineHandler startup...')
            self.event_generate(AutoDiscDoneEvent('no_device',self))
            return
        self._go = 1
        self.get_state()
        self.event_generate(AutoDiscDoneEvent('ok',self))
        while self._go:
            self.get_state()
            time.sleep(1.0) # check for transitions every 1 sec; should catch all of them
        return
    def get_state(self):
        if (self._go == 0):
            self._state = 0 # 'Stopped'
            return self._state
        CTS = 0x20
        i = 0
        s = struct.pack('I', i)
        self._lock.acquire()
        s_flags = 0
        try:
            fd = self._port.file.fileno()
            s_flags = fcntl.ioctl(fd, termios.TIOCMGET, s)
        finally:
            self._lock.release()
        flags = struct.unpack('I', s_flags)[0]
        if ((flags & CTS) == 0) and (self._state != 2): # if CTS has been deactivated, indicates modem now active:
            msglog.log('mpx',msglog.types.WARN,'Mediator Preempted! May need ' \
                            'to restart Mediator to find any changes made by UltraSite!')
            self._state = 2 # 'Preempted by CPC modem'
        elif ((flags & CTS) != 0) and (self._state != 1): # if CTS has been activated, indicates modem now inactive:
            self._state = 1 # 'Able to send'
        return self._state
    def get_autodiscover_period(self):
        return self._autodisc_period
    ##
    # _autodiscover(): Called when _start_thread starts, to determine CPC network config.
    # @fixme Currently, only handle REFLECS Device autodiscovery (ie #$512). Need to handle UHP general (ie seq'l querying of up to 39 Devices)
    def _autodiscover(self):
        self._lock.acquire()
        result = 0
        # Find all devices on COM port, create Device for each, discover items:
        try:
            new_devices = [] # devices not discovered on previous passes through this method
            termios.tcflush(self._port.file.fileno(), termios.TCOFLUSH)
            self._port.drain() # drain C-buffer of all unread bytes recvd till now
            self._port.write(self._query_devs) # invite responses from all listening devices
            while 1:
                self._rd_buf = array.array('B')
                try:
                    self._port.read(self._rd_buf, 16, 6.0)
                except ETimeout:
                    break
                if (self._rd_buf[0] != ord('\n')) or (self._rd_buf[1] != ord('\r')):
                    self._rd_buf = array.array('B') # clear _rd_buf
                    continue
                dev_name = self._rd_buf[2:16].tostring() # may be right-padded with 0x20's (spaces)
                self._rd_buf = array.array('B')
                string.rstrip(dev_name)
                id = int(dev_name[:2])
                if self._devices.has_key(id):
                    continue # do NOT add this device to our table of new devices
                dev = None
                try:
                    dev = Device(id, self)
                except Exception, e:
                    msglog.exception()
                    continue
                new_devices.append(DevInstData(dev._id, dev_name, dev)) # add dev to list of new
            while len(new_devices) > 0:
                dev_inst_data = new_devices.pop(0)
                dev_id = int(dev_inst_data)
                self._devices[dev_id] = dev_inst_data # probationary add, to support acquisition of additional info...
                if self._get_dev_info(dev_inst_data.dev) != 0:
                    msglog.log('mpx:cpc',msglog.types.WARN,'LineHandler: Failed to _get_dev_info() for %s (Dev %u)' \
                               % (str(dev_inst_data), int(dev_inst_data)))
                    result = -1
                    del self._devices[dev_id]
                    continue
                if self._get_dev_items(dev_inst_data.dev) != 0:
                    msglog.log('mpx:cpc',msglog.types.WARN,'LineHandler: Failed to _get_dev_items() for %s (Dev %u)' \
                               % (str(dev_inst_data), int(dev_inst_data)))
                    result = -1
                    del self._devices[dev_id]
                    continue
            msglog.log('mpx',msglog.types.INFO,'Found %u CPC devices so far...' % len(self._devices))
            self.debug_print(str(self._devices), 2)
        finally:
            self._lock.release()
        return result
    ##
    # _get_dev_info(): Query device for info. If more than 4 Objects are to be
    # queried, then break the current, single Request pkt into more than one
    # pkt, with no more than 4 Item Requests per pkt. (CPC programming 
    # "suggestion".)
    # @param dev Device ID number
    def _get_dev_info(self, dev):
        reqs = []
        dev_base_objs = [('SecurityCode','_security_code'), \
                    ('ModelName','_model_name'), \
                    ('Revision','_revision'), \
                    ('DeviceName','_device_name')]
        for dev_base_obj in dev_base_objs:
            req = ('Base',0,dev_base_obj[0],0,0,0,0,0,None)
            reqs.append(req)
        item_resp_list = self._do_pkt_xchg(dev._id, 'GetValue', reqs)
        if (item_resp_list is None) or isinstance(item_resp_list,Exception):
            return -1
        for i in range(len(dev_base_objs)):
            value = item_resp_list[i][0]
            if value != 0:
                msglog.log('mpx',msglog.types.ERR, \
                                'Failed to get Name Object Value for %s Item %u. '\
                                'Return code = %u' % (self.name, item_inst_num, result[0]))
            else:
                value = item_resp_list[i][1]
            setattr(dev,dev_base_objs[i][1], value)
        return 0
    ##
    # _get_dev_items():
    def _get_dev_items(self, dev):
        dev.item_types = tables._device_types[dev._model_name][1] # one-and-only place to set dev.item_types
        item_type_names = dev.item_types.string_keys()
        for item_type_name in item_type_names:
            if (item_type_name == 'None') or (item_type_name == 'Base') or (item_type_name == 'Alarm'):
                continue
            reqs = [(item_type_name,0,'Obj1',0,0,0,0,0,None), \
                        (item_type_name,0,'Obj2',0,0,0,0,0,None)] # get max num items, flags for config'd items
            item_resp_list = self._do_pkt_xchg(dev._id, 'GetValue', reqs)
            if (item_resp_list is None) or isinstance(item_resp_list,Exception):
                return -1
            max_num_items = item_resp_list[0][0]
            if max_num_items == 0:
                max_num_items = item_resp_list[0][1]
            configured_item_flags = item_resp_list[1][0] # an array of bytes
            if configured_item_flags == 0:
                configured_item_flags = item_resp_list[1][1]
            if configured_item_flags == 0:
                continue # no configured items means do not add a key/value pair to dev._items
            # Special handling for Power Item, since it's one-and-only inst num is "0", not "1":
            if (item_type_name == 'Power') \
                and (configured_item_flags == 1):
                rslt = dev.add_item(item_type_name, 0)
                if not rslt is None:
                    msglog.log('mpx',msglog.types.ERR,str(rslt))
                continue
            # Handling for items of all non-Power types:
            flag_mask = 0x01L
            for i in range(1, max_num_items + 1):
                if (flag_mask & configured_item_flags) != 0:
                    rslt = dev.add_item(item_type_name, i)
                    if not rslt is None:
                        msglog.log('mpx',msglog.types.ERR,str(rslt))
                flag_mask = (flag_mask << 1)
        return 0
    ##
    #
    def _do_pkt_xchg(self, dev_id, cmd, reqs):
        item_resp_list = None
        for i in range(5): # up to 5 attempts (1 initial + 4 retries)
            result = self._send_req(dev_id, cmd, reqs)
            if isinstance(result, Exception):
                msglog.log('mpx',msglog.types.ERR,str(result))
                return result
            item_resp_list = self._get_resp()
            if item_resp_list is None:
                msglog.log('mpx',msglog.types.WARN,'Attempt %u: Failed to receive valid ' \
                                'response from Device %s, to Request %s %s.' % (i, dev_id, cmd, reqs))
            else:
                break
        return item_resp_list
    ##
    # _send_req(): Formats and sends a UHP Request packet to the specified CPC 
    #  controller.
    # @param dev_id_or_name target device ID (1 - 39, or value of corresponding DeviceName Object)
    # @param cmd_id_or_name UHP Command (see tables for valid numeric and text values)
    # @param reqs Requests for command (list of ONE to FOUR 9-tuples: (ItemType,ItemIdx,ObjType,ObjIdx,PropType,PropIdx,DataLen,DataType,Data))
    def _send_req(self, dev_id_or_name, cmd_id_or_name, reqs):
        if self.get_state() > 1:
            return EBusy('Mediator comms with CPC have been preempted by CPC modem, OR are stopped.')
        if not self._devices.has_key(dev_id_or_name):
            msg = '_send_req: Dev %s not found.' % dev_id_or_name
            msglog.log('mpx',msglog.types.ERR,msg)
            return EDeviceNotFound(msg)
        dev = self._devices[dev_id_or_name].dev
        self._wr_pkt[0] = 0x7e # UHP-specific SOH
        self._wr_pkt[1] = dev._id
        self._wr_pkt[2] = (self._pkt_seq_num_gen & 0xFF)
        self._pkt_seq_num_gen += 1 # prep for next pkt
        if not tables._cmds.has_key(cmd_id_or_name):
            return ENotFound('_send_req: UHP Request Command %s not found.' \
                                    % cmd_id_or_name)
        cmd = int(tables._cmds[cmd_id_or_name])
        self._wr_pkt[5] = cmd
        self._wr_pkt[6] = len(reqs)
        next_byte = 7
        dev_type_num, item_types = tables._device_types[dev._model_name]
        for req in reqs:
            if not item_types.has_key(req[0]):
                return ENotFound('_send_req: ItemType %s not found.' % str(req[0]))
            item_type_data = item_types[req[0]]
            item_type_id = int(item_type_data)
            obj_types = item_type_data.obj_types
            self._wr_pkt[next_byte] = item_type_id # item type num
            next_byte += 1
            self._wr_pkt[next_byte] = req[1] # item instance num
            next_byte += 1
            if not obj_types.has_key(req[2]):
                return ENotFound('_send_req: ObjType %s not found.' % str(req[2]))
            obj_type = obj_types[req[2]]
            obj_type_id = int(obj_type)
            self._wr_pkt[next_byte] = obj_type_id # obj type num
            next_byte += 1
            prop_types = [0]
            max_obj_insts = 1
            if isinstance(obj_type, tables.ObjData):
                prop_types = obj_type.prop_types
                max_obj_insts = obj_type.max_num_instances
            if req[3] >= max_obj_insts:
                return EInvalidValue('obj_inst_num',req[3], \
                                            'Max = %u' % (max_obj_insts - 1))
            self._wr_pkt[next_byte] = req[3] # obj instance num
            next_byte += 1
            if ((item_type_id != 2) or (obj_type_id != 1)): # NOT Alarm/GetAlarmRpt:
                # Ensure that req[4] is in numeric form:
                prop_type = int(tables._props[req[4]])
                # If prop ID is not found in list of allowed prop IDs, then scream:
                if (not prop_type in prop_types):
                    return ENotFound('_send_req: PropType %s not found.' % str(req[4]))
            else:
                assert type(req[4]) == types.IntType,'req[4] should be IntType!'
                prop_type = req[4]
            self._wr_pkt[next_byte] = prop_type
            next_byte += 1
            self._wr_pkt[next_byte] = req[5]
            next_byte += 1
            set_data_len = 0
            set_data_type = 0
            set_data = []
            if cmd == 2: # if cmd is SetValue:
                set_data_len = len(req[8])
                if not tables._data_types.has_key(req[7]):
                    return ENotFound('_send_req: DataType %s not found.' \
                                            % str(req[7]))
                set_data_type = int(tables._data_types[req[7]])
                set_data = req[8]
            self._wr_pkt[next_byte] = set_data_len
            next_byte += 1
            self._wr_pkt[next_byte] = set_data_type
            next_byte += 1
            for byte in set_data:
                self._wr_pkt[next_byte] = byte
                next_byte += 1
        # Set length of data portion, now that we know it:
        total_len_data = next_byte - 7
        self._wr_pkt[3] = (total_len_data & 0xFF)
        self._wr_pkt[4] = ((total_len_data >> 8) & 0xFF)
        # Calc CRC:
        crc = utils.make_xmodem_crc(self._wr_pkt, next_byte)
        self._wr_pkt[next_byte] = crc & 0xFF
        next_byte += 1
        self._wr_pkt[next_byte] = (crc >> 8) & 0xFF
        next_byte += 1
        pkt = self._wr_pkt[:next_byte]
        self.debug_print(pkt, 2)
        # Clear all unsent bytes from output buffer:
        termios.tcflush(self._port.file.fileno(), termios.TCOFLUSH)
        # Clear out all the stray bytes that may have been arriving due
        # to conversation between CPC net and UltraSite:
        self._port.drain()
        # Send pkt to port:
        self._port.write(pkt)
    def _get_resp(self):
        self._rd_pkt = array.array('B', 7 * '\0') # allocate space for fixed-len hdr
        self._rd_pkt_idx = 0
        self._rd_pkt_data_len = 0
        read_timeout = 5.0
        overall_timeout = read_timeout * 2.0 # loop for up to 2x read wait time (arbitrary), looking for hdr valid bytes
        self._rd_pkt_idx = 0
        start_time = time.time()
        while self._rd_pkt_idx < 7: # use loop to discard/tolerate any garbage bytes before actual response:
            self._rd_buf = array.array('B')
            num_bytes_left = 7 - self._rd_pkt_idx
            try:
                self._port.read(self._rd_buf, num_bytes_left, read_timeout) # read at least ACK + fixed header
            except ETimeout:
                msglog.log('mpx',msglog.types.WARN,'Port.read failed to receive 7 ' \
                                'response header bytes within %f sec' % read_timeout)
                return None
            result = 0
            for byte in self._rd_buf:
                result = self._process_hdr_byte(byte)
                if result == 0:
                    break
            if result == 0:
                break
            if ((time.time() - start_time) > overall_timeout):
                msglog.log('mpx',msglog.types.WARN,'Failed to receive 7 response ' \
                                'header bytes within %f sec' % overall_timeout)
                return None
        # Get remaining bytes:
        num_bytes_left = self._rd_pkt_data_len + 2 # data bytes plus 2-byte CRC
        try:
            self._port.read(self._rd_pkt, num_bytes_left, read_timeout) # append remaining bytes to _rd_pkt
        except ETimeout:
            msglog.log('mpx',msglog.types.WARN,'Failed to read %u data/CRC bytes within %f sec' \
                            % (num_bytes_left, read_timeout))
            return None
        # Verify CRC:
        len_hdr_and_data = 6 + self._rd_pkt_data_len
        crc_calc = utils.make_xmodem_crc(self._rd_pkt[1:], len_hdr_and_data)
        crc_given = self._rd_pkt[len_hdr_and_data + 1] + (self._rd_pkt[len_hdr_and_data + 2] << 8)
        if crc_calc != crc_given:
            msglog.log('mpx', msglog.types.WARN, '%s: Bad CRC. calc = 0x%04x, got = 0x%04x' \
                            % (self.__class__.__name__, crc_calc, crc_given))
            return None
        # Extract ResponseItems into a list:
        resp_lists = []
        for i in range(self._rd_pkt[6]): # read data for each response:
            resp_list = []
            result = self._rd_pkt[self._rd_pkt_idx]
            resp_list.append(result)
            # @todo Process non-ACCEPTED results...
            data_len = self._rd_pkt[self._rd_pkt_idx + 1]
            if data_len != 0: # only for GetValue Responses:
                data_type = self._rd_pkt[self._rd_pkt_idx + 2]
                self._rd_pkt_idx += 3
                data = utils._convert_funcs[data_type](self._rd_pkt[self._rd_pkt_idx:(self._rd_pkt_idx + data_len)])
                resp_list.append(data)
                self._rd_pkt_idx += data_len
            else:
                self._rd_pkt_idx += 3
            resp_lists.append(resp_list)
        return resp_lists
            
    def _process_hdr_byte(self, byte):
        self._rd_pkt[self._rd_pkt_idx] = byte
        result = -1
        if self._rd_pkt_idx == 0:
            if byte == 0x06:
                self._rd_pkt_idx = 1
            else:
                self.debug_print('Expected 0x06, got 0x%02x' % byte, 1)
                self._rd_pkt_idx = 0
        elif self._rd_pkt_idx == 1:
            if byte == 0x7e:
                self._rd_pkt_idx = 2
            else:
                self.debug_print('Expected 0x7e, got 0x%02x' % byte, 1)
                self._rd_pkt_idx = 0
        elif self._rd_pkt_idx == 2:
            if (byte >= 1) and (byte <= 39):
                self._rd_pkt_idx = 3
            else:
                self.debug_print('Expected Device ID (1 - 39), got 0x%02x' % byte, 1)
                self._rd_pkt_idx = 0
        elif self._rd_pkt_idx == 3:
            if (byte == self._wr_pkt[2]): # cf given seq num to last sent (we, as master, set seq num)
                self._rd_pkt_idx = 4
            else:
                self.debug_print('Expected SeqNum 0x%02x, got 0x%02x' % (self._wr_pkt[2], byte), 1)
                self._rd_pkt_idx = 0
        elif self._rd_pkt_idx == 4:
            self._rd_pkt_idx = 5
        elif self._rd_pkt_idx == 5:
            len_data = self._rd_pkt[4] + (self._rd_pkt[5] << 8)
            if (len_data >= 0) and (len_data <= 512):
                self._rd_pkt_data_len = len_data
                self._rd_pkt_idx = 6
            else:
                self.debug_print('Expected DataLen (0 - 512), got 0x%04x' % len_data, 1)
                self._rd_pkt_idx = 0
        elif self._rd_pkt_idx == 6:
            if (byte == self._wr_pkt[6]): # cf given num of items to last sent
                self._rd_pkt_idx = 7
                result = 0 # indicate that header is complete
            else:
                self.debug_print('Expected 0x%02x ResponseItems, got 0x%02x' % (self._wr_pkt[6], byte), 1)
                self._rd_pkt_idx = 0
        else:
            raise EInvalidValue('self._rd_pkt_idx', self._rd_pkt_idx, 'Must be 0 - 6')
        return result
    def debug_print(self, msg, msg_lvl):
        if msg_lvl < self.debug_lvl:
            if isinstance(msg, array.ArrayType):
                utils.print_array_as_hex(msg, 16)
            else:
                print 'cpc.lib.LineHandler: ' + msg
    


    
        
    
    
    
    
    
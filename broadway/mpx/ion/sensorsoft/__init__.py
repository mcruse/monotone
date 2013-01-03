"""
Copyright (C) 2010 2011 Cisco Systems

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
# module provides support for Sensorsoft's ST6105 
# series RS-232 sensors

from mpx.lib.node import CompositeNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib import thread_pool
from mpx.lib import threading
from mpx.lib import Result

from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent

from mpx.lib.scheduler import scheduler

from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import EConfiguration

from mpx.lib import msglog
from mpx.lib.msglog.types import WARN

from moab.linux.lib import uptime

import struct
import array
import time

STATUS_RQST = 0xc1
TEMP_RQST = 0xc5
ID_RQST = 0xc3

class RqstMsg(object):
    def __init__(self, address):
        self._cmd = None
        self._len = 0
        self._address = address
        self._argument = None
        self._packed = None
        if address == 0x01:
            self._get_crc = self._static_crc
        else:
            self._get_crc = self._calcd_crc
        
    def encode(self):
        if self._packed is not None:
            return self._packed
        packed = ''
        # address is 6 bytes - struct only supports 4 (long) and long longs(8)
        # deal with the most significant 2 bytes "by hand".
        msb = self._address & 0xffff00000000 
        packed = struct.pack('<BHLH', self._cmd, self._len, self._address, msb)
        if self._argument is not None:
            packed += struct.pack('B', self._argument)
        crc = self._get_crc()
        packed += struct.pack('<H', crc)
        self._packed = packed
        return self._packed
    
    def _get_crc(self):
        pass
    
    def _static_crc(self):
        pass
    
    def _calcd_crc(self):
        #@todo - implement
        pass

        
class StatusRqstMsg(RqstMsg):
    def __init__(self, address):
        RqstMsg.__init__(self, address)
        self._cmd = STATUS_RQST
        self._len = 0x0b        
            
    def _static_crc(self):
        return 0x9847
    
class TemperatureRqstMsg(RqstMsg):
    def __init__(self, address):
        RqstMsg.__init__(self, address)
        self._cmd = TEMP_RQST
        self._len = 0x0c
        self._argument = 0x02        
            
    def _static_crc(self):
        return 0x796d
    
class IdRqstMsg(RqstMsg):
    def __init__(self, address):
        RqstMsg.__init__(self, address)
        self._cmd = ID_RQST
        self._len = 0x0b
    
    def _static_crc(self):
        return 0x5e20
    
class RspMsg(object):
    def __init__(self, msg):
        #self._rsp = struct.unpack('B', msg[0])[0]
        #self._len = struct.unpack('>H', msg[1:3])[0]
        self._rsp = msg[0]
        self._len = (msg[2] << 8) | msg[1]
        # data remains packed
        self._data = msg[3:-2]
        self._crc = msg
        self._raw_msg = msg
        
class StatusRspMsg(RspMsg):
    LOW_POWER = 1 # Voltage is unacceptable for reliable operation.
    POWER_UP = 8 # Device just powered up.
    TAMPER = 16 #Sensor element is disconnected or broken.
    def __init__(self, msg):
        RspMsg.__init__(self, msg)
        self._data = self._data[0]
    
    def _get_bit_status(self, bit):
        return self._data & bit
    
    def __get_low_power(self):
        return self._get_bit_status(self.LOW_POWER)
    low_power = property(__get_low_power)
    
    def __get_power_up(self):
        return self._get_bit_status(self.POWER_UP)
    power_up = property(__get_power_up)
    
    def __get_tamper(self):
        return self._get_bit_status(self.TAMPER)
    tamper = property(__get_tamper)

class TemperatureRspMsg(RspMsg):
    def __init__(self, msg):
        RspMsg.__init__(self, msg)
        self._data = self._data.tostring()
        self._temp_c = None
        self._temp_f = None
        
    def __get_temp_c(self):
        if self._temp_c is None:
            if len(self._data) == 4:
                self._temp_c = struct.unpack('<f', self._data)[0]
            else:
                # ieee floating point not supported
                temp = struct.unpack('<2B', self._data)[0]
                if (temp >> 8) == 0xff:
                    # negative.  get (compliment + 1) * -1 of lsb.
                    temp = ((~(temp & 0xff)) + 1) * -1
                self._temp_c = temp * .5
        return self._temp_c
    temp_c = property(__get_temp_c)
    
    def __get_temp_f(self):
        if self._temp_f is None:
            self._temp_f = ((self.temp_c * 9) / 5) + 32
        return self._temp_f
    temp_f = property(__get_temp_f)
    
class IdRspMsg(RspMsg):
    def __init__(self, msg):
        RspMsg.__init__(self, msg)
        data = self._data[6:].tostring()
        fields = data.split('\x00')
        self.device_name = fields[0]
        self.manufacturer = fields[1]
        self.model_number = fields[2]
        self.firmware_version = fields[3]
        
##
# ION modeling a Sensorsoft network. 
# Typically the network, being RS232 based, consists
# of exactly one ST6105 device.  This is
# not enforced by the "Sensorsoft Device Protocol"
# which includes an address field.

##
# Protocol details (little endian)
# 
# Example Status Request Message, delimited (|) by field.
#
# 0xc1 | 0b00 | 010000000000 | 4c98
#
# 0xc1 (Command byte)
# 0x0b00 (Packet length, including CRC)
# 0x010000000000 (Device address - typically 1)
# 0x4798 (Crc)
#
class Protocol(CompositeNode, ProtocoLicense):    
    def __init__(self):
        self._threadpool = None
        self._init_complete = False
        self._port = None
        self._request = {} # k:(rqst_type, addr,) v: request object
        self.__update_freqs = {} 
        self.__callbacks = {}
        self.__callback_lock = threading.Lock()
        self.__port_lock = threading.Lock()
        CompositeNode.__init__(self)
                    
    def start(self):
        if not self._threadpool:
            port_name = self.parent.name
            self._threadpool = thread_pool.ThreadPool(
                1, name='Sensorsoft ThreadPool-'+port_name
                )
        if not self._port or not self._port.is_open():
            self._port = self.parent
            self._port.open()
            self._port.drain()
        CompositeNode.start(self)
        
    ##
    # Devices
    def register(self, address, cmd, callback, update_freq=60):
        callback_key = (address, cmd)
        self.__callback_lock.acquire()
        try:
            callback_list = self.__callbacks.get(callback_key)
            if callback_list:
                exists = False
                new_list = []
                for cb, freq in callback_list:
                    if callback == cb:
                        # callback already exits
                        # we're just modifying the update frequency
                        exists = True
                        freq = update_freq
                    new_list.append((cb, freq))
                self.__callbacks[callback_key] = new_list
                if not exists:
                    self.__callbacks.get(callback_key).append(
                        (callback, update_freq)
                        )
            else:
                self.__callbacks[callback_key] = [(callback, update_freq)]
            self.send_request(address, cmd, self._distribute_results)
        finally:
            self.__callback_lock.release()
            
    def unregister(self, address, cmd, callback):
        callback_key = (address, cmd)
        self.__callback_lock.acquire()
        try:
            cbs = self.__callbacks.get(callback_key)
            if cbs:
                try:
                    idx = cbs.index(callback)
                    # delete the callback, even if it's empty, leave
                    # the callback list and dict key in place
                    del cbs[idx]
                except ValueError:
                    # callback does not exist
                    pass
        finally:
            self.__callback_lock.release()
    
    def send_request(self, address, cmd, callback=None):
        rqst = self._get_rqst_obj(address, cmd)
        if callback:
            self._threadpool.queue_noresult(self._send_request, rqst, callback)
        else:
            return self._send_request(rqst, callback)
        
    def _send_request(self, rqst, callback):
        self.__port_lock.acquire()
        try:
            self._port.write(rqst.encode())
            errs = 0
            rsp = ETimeout()
            while errs < 5:
                buff = array.array('B')
                try:
                    self._port.read(buff, 1, 1) #1 char read, 1 sec timeout.
                    cmd = buff[0]
                    if not cmd in [0x90, 0x94]:
                        errs += 1
                        print 'err'
                        continue
                    self._port.read(buff, 2, 1)
                    p_len = (buff[2] << 8) | buff[1] -3
                    self._port.read(buff, p_len, 1)
                    rsp = self._get_rsp_obj(rqst._cmd, buff)
                    break
                except:
                    msglog.exception()
                    break
            if callback:
                callback(rqst, rsp)
            else:
                return rsp
        finally:
            self.__port_lock.release()
        
    def _get_rqst_obj(self, address, cmd):
        cmd_rqst_map = {
            STATUS_RQST:StatusRqstMsg,
            TEMP_RQST:TemperatureRqstMsg,
            ID_RQST:IdRqstMsg
            }
        assert cmd in cmd_rqst_map.keys()
        rqst = self._request.get((address, cmd))
        if rqst is None:
            rqst_klass = cmd_rqst_map.get(cmd)
            rqst = rqst_klass(address)
            self._request[(address, cmd)] = rqst
        return rqst
    
    def _get_rsp_obj(self, cmd, rsp):
        cmd_rsp_map = {
            STATUS_RQST:StatusRspMsg,
            TEMP_RQST:TemperatureRspMsg,
            ID_RQST:IdRspMsg
            }
        assert cmd in cmd_rsp_map.keys()
        # return a response object
        return cmd_rsp_map.get(cmd)(rsp)
    # update nodes that have registered interest and reschedule
    # pass a results object here
    def _distribute_results(self, rqst, rsp):
        address = rqst._address
        cmd = rqst._cmd
        callback_key = (address, cmd)
        min_freq = 100000 # arbitrarily large poll freq.
        self.__callback_lock.acquire()
        try:
            callback_list = self.__callbacks.get(callback_key)
            if callback_list:
                for cb, freq in callback_list:
                    try:
                        cb(rsp)
                    except:
                        msglog.exception()
                    if freq < min_freq:
                        # used to establish when we will send another request
                        min_freq = freq
                #@fixme - add delay
                scheduler.seconds_from_now_do(
                    min_freq, self.send_request, 
                    address, cmd, self._distribute_results
                    )
        finally:
            self.__callback_lock.release()
            
class IdContainer(CompositeNode):
    pass

class DiagsContainer(CompositeNode):
    pass
##
# The Sensorsoft Thermometer
class ST61015(CompositeNode):
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'address', 1, cd, int)
    
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'address', cd)
        return cd
            
class ST61015Property(CompositeNode, EventProducerMixin):
    def __init__(self):
        self._last_result = None
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self._subscribe_lock = threading.Lock()
        self._subscribed = 0
        self._last_rcvd = 0
        self._cached_result = None
        self._msg_req_type = None
        self._device_node = None
        self._protocol_node = None
        
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'prop_name', REQUIRED, cd)
        set_attribute(self, 'ttl', 60, cd, int)
        self._set_msg_req()
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'prop_name', cd)
        get_attribute(self, 'ttl', cd)
        return cd
    
    def start(self):
        ancestor = self.parent
        # walk up the node tree until we find the protocol node
        while 1:
            if isinstance(ancestor, ST61015):
                self._device_node = ancestor
            elif isinstance(ancestor, Protocol):
                self._protocol_node = ancestor
            # found them both
            if not (self._protocol_node and self._device_node):
                try:
                    ancestor = ancestor.parent
                except:
                    msg = 'Invalid Configuration - both a device and '\
                    'protocol must be configured.'
                    raise EConfiguration(msg)
            else:
                break
        CompositeNode.start(self)
            
    def _set_msg_req(self):
        prop_req_type_map = {
            'low_power':STATUS_RQST,
            'power_up':STATUS_RQST,
            'tamper':STATUS_RQST,
            'temp_c':TEMP_RQST,
            'temp_f':TEMP_RQST,
            'device_name':ID_RQST,
            'manufacturer':ID_RQST,
            'model_number':ID_RQST,
            'firmware_version':ID_RQST
            }
        assert self.prop_name in prop_req_type_map.keys()
        self._msg_req_type = prop_req_type_map.get(self.prop_name)
        
    def get(self, skipCache=0):
        value = self.get_result(skipCache).value
        if isinstance(value, Exception):
            raise ETimeout
        return value
    
    def get_result(self, skipCache=0):
        dt = uptime.secs() - self._last_rcvd
        if dt > self.ttl or self._cached_result is None:
            # data is stale
            value = self.sync_read() # blocks
        return self._cached_result
    
    def sync_read(self):
        address = self._device_node.address
        cmd = self._msg_req_type
        callback = None
        msg = self._protocol_node.send_request(address, cmd, callback)
        self.update(msg)
        
    def update(self, msg):
        self._last_rcvd = uptime.secs()
        if self._cached_result is None:
            change_count = 1
            last_value = None
        else:
            change_count = self._cached_result.changes + 1
            last_value = self._cached_result.value
        if isinstance(msg, Exception):
            value = msg
        else:
            value = getattr(msg, self.prop_name)
        self._cached_result = Result(
            value, time.time(), changes=change_count
            )
        self._trigger_cov(last_value)
    
    def has_cov(self):
        return 1
        
    def event_subscribe(self, *args):
        self._subscribe_lock.acquire()
        try:
            self._subscribed += 1
            EventProducerMixin.event_subscribe(self, *args)
            if self._cached_result is None:
                last_value = None
            else:
                last_value = self._cached_result.value
            try:
                self.get() # throw away
            except:
                pass
            # generate initial event
            self._trigger_cov(last_value)
            if self._subscribed == 1:
                # initial subscription
                address = self._device_node.address
                cmd = self._msg_req_type
                callback = self.update
                self._protocol_node.register(
                    address, cmd, callback, self.ttl / 2
                    )
        finally:
            self._subscribe_lock.release()
            
    def event_unsubscribe(self, *args):
        self._subscribe_lock.acquire()
        try:
            assert self._subscribed >= 0
            self._subscribed -= 1
            EventProducerMixin.event_subscribe(self, *args)
            if self._subscribed == 0:
                address = self._device_node.address
                cmd = self._msg_req_type
                callback = self.update
                self._protocol_node.unregister(address, cmd, callback)
        finally:
            self._subscribe_lock.release()
    
    def _trigger_cov(self, old_value):
        cov = ChangeOfValueEvent(
            self, old_value, self._cached_result.value, time.time()
            )
        self.event_generate(cov)
        
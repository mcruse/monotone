"""
Copyright (C) 2011 Cisco Systems

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
import time
import mpx.lib.omni.rt as device
from mpx.lib.configure import set_attribute, get_attribute, as_boolean
from mpx.lib.exceptions import EAlreadyRunning, ENotRunning
from mpx.lib.exceptions import EInvalidMessage, EBadChecksum, EInvalidValue
from mpx.lib.node import CompositeNode
from mpx.lib.msglog.types import INFO, WARN, ERR
from mpx.ion.omni.rs5_device import DeviceRS5
from mpx.lib.threading import Lock
from mpx.ion.omni import calc_sum
from mpx.ion.omni import format_address, format_password, format_reading
from mpx.ion.omni import format_rt_reading

class DeviceRT(DeviceRS5):
    def __init__(self):
        self.rt_request_obj = device.real_time_value_req()
        self.rt_response_obj = device.real_time_value_res()
        self.cr_request_obj = device.control_relay_req()
        self.cr_response_obj = device.control_relay_res()
        self.rt_lock = Lock()
        self.cr_lock = Lock()
        self.rt_last_updated = 0
        super(DeviceRT, self).__init__()

    def configure(self, config):
        set_attribute(self, 'password', '11111100', config, str)
        super(DeviceRT, self).configure(config)

    def start(self):
        if self.is_running():
            raise EAlreadyRunning()
        #bug: CSCts88534
        if self.parent.parent.baud == 9600:
            self.response_obj = device.readmeterres()
        #bug ended
        self.configure_rt_packet()
        self.configure_cr_packet()
        super(DeviceRT, self).start()

    def configure_rt_packet(self):
        req_addr = self.rt_request_obj.findChildByName('addr')
        req_bcc = self.rt_request_obj.findChildByName('bcc')
        req_addr.setValue(self.bin_addr)
        checksum = (0xC3 + calc_sum(self.bin_addr)) & 0xFF
        req_bcc.setValue(checksum)

    def configure_cr_packet(self):
        req_addr = self.cr_request_obj.findChildByName('addr')
        req_pwd = self.cr_request_obj.findChildByName('pwd')
        password = format_password(self.password)
        req_addr.setValue(self.bin_addr)
        req_pwd.setValue(password)
        self.cr_checksum = (0x58 + calc_sum(self.bin_addr) + 
                            calc_sum(password)) & 0xFF

    def _read_rt_value(self, wait_time=None, numretries=None):
        """Don't use Me.

        """
        if numretries is None:
            numretries = self.retry_count
        while numretries:
            try:
                self._send_request(self.rt_request_obj, 
                                   self.rt_response_obj, wait_time, 1)
                resp_addr = self.rt_response_obj.findChildByName('addr')
                resp_data = self.rt_response_obj.findChildByName('data')
                resp_bcc = self.rt_response_obj.findChildByName('bcc')
                addr = resp_addr.getValue()
                data = resp_data.getValue()
                bcc = resp_bcc.getValue()
                checksum = (0xD9 + calc_sum(addr) + calc_sum(data)) & 0xFF
                if checksum != bcc:
                    raise EBadChecksum()
                if self.bin_addr != addr:
                    raise EInvalidMessage()

                values = {}
                values['EM_RecMeterValue'] = format_rt_reading(data[0:4])
                values['EM_SenMeterValue'] = format_rt_reading(data[4:8])
                values['EM_RecActivePower'] = format_rt_reading(data[8:12])
                values['EM_SenActivePower'] = format_rt_reading(data[12:16])
                values['EM_RecPassive1MeterValue'] = format_rt_reading(data[16:20])
                values['EM_RecPassive2MeterValue'] = format_rt_reading(data[20:24])
                values['EM_RecPassivePower1'] = format_rt_reading(data[24:28])
                values['EM_RecPassivePower2'] = format_rt_reading(data[28:32])    
                values['EM_SenPassive1MeterValue'] = format_rt_reading(data[32:36])
                values['EM_SenPassive2MeterValue'] = format_rt_reading(data[36:40])
                values['EM_SenPassivePower1'] = format_rt_reading(data[40:44])
                values['EM_SenPassivePower2'] = format_rt_reading(data[44:48]) 

                #have to rename voltages and currents
                values['EM_Voltage_1'] = format_rt_reading(data[48:52])
                values['EM_Voltage_2'] = format_rt_reading(data[52:56])      
                values['EM_Voltage_3'] = format_rt_reading(data[56:60])      
                values['EM_Current_1'] = format_rt_reading(data[60:64])
                values['EM_Current_2'] = format_rt_reading(data[64:68])
                values['EM_Current_3'] = format_rt_reading(data[68:72])
                values['EM_Phase_1'] = format_rt_reading(data[72:76])
                values['EM_Phase_2'] = format_rt_reading(data[76:80])
                values['EM_Phase_3'] = format_rt_reading(data[80:84])
                values['EM_Hz'] = format_rt_reading(data[84:88])
                values['EM_PowerRelay'] = format_rt_reading(data[88:92])

                values['WM_MeterValue'] = format_rt_reading(data[92:96])
                values['WM_MeterPower'] = format_rt_reading(data[96:100])
                values['HM_MeterValue'] = format_rt_reading(data[100:104])
                values['HM_MeterPower'] = format_rt_reading(data[104:108])
                values['GM_MeterValue'] = format_rt_reading(data[108:112])
                values['GM_MeterPower'] = format_rt_reading(data[112:116])
                values['CM_MeterValue'] = format_rt_reading(data[116:120])
                values['CM_MeterPower'] = format_rt_reading(data[120:124])
                self.update_rt_value(values)
                return
            except:
                numretries -= 1
        raise
                
    def _write_cr_value(self, value, wait_time=None, numretries=None):
        """Only to be used by set_cr_value method

        Value should only be an integer
        """
        if not self.is_running():
            raise ENotRunning()
        if numretries is None:
            numretries = self.retry_count
        data = self.cr_request_obj.findChildByName('data')
        bcc = self.cr_request_obj.findChildByName('bcc')
        checksum = (self.cr_checksum + value) & 0xFF
        data.setValue(value)
        bcc.setValue(checksum)
        while numretries:
            try:
                self._send_request(self.cr_request_obj,
                                   self.cr_response_obj, wait_time, 1)
                resp_addr = self.cr_response_obj.findChildByName('addr')
                resp_bcc = self.cr_response_obj.findChildByName('bcc')
                addr = resp_addr.getValue()
                bcc = resp_bcc.getValue()
                checksum = (0xD3 + calc_sum(addr)) & 0xFF
                if checksum != bcc:
                    raise EBadChecksum()
                if self.bin_addr != addr:
                    raise EInvalidMessage()
                return
            except:
                numretries -= 1
        raise

    def get_rt_value_as_dict(self):
        return self.rt_value

    def update_rt_value(self, value):
        self.rt_value = value
        self.rt_last_updated = time.time()

    def is_rt_value_stale(self):
        return ((time.time() - self.rt_last_updated) > self.cache_life)

    def get_rt_value_by_name(self, name, skipcache=0):
        """get method for rt values
        
        name is case sensitive
        """
        self.rt_lock.acquire()
        try:
            if self.is_rt_value_stale() or skipcache:
                self._read_rt_value()
        finally:
            self.rt_lock.release()
        return self.rt_value[name]

    def set_cr_value(self, value):
        self.cr_lock.acquire()
        try:
            self._write_cr_value(value)
        finally:
            self.cr_lock.release()

class RTPlaceHolder(CompositeNode):
    def get_rt_value_by_name(self, name, skipcache):
        return self.parent.get_rt_value_by_name(name, skipcache)

    def set_cr_value(self, value):
        self.parent.set_cr_value(value)

class RS5PlaceHolder(CompositeNode):
    def get_value_by_name(self, name, skipcache):
        return self.parent.get_value_by_name(name, skipcache)

class PointRT(CompositeNode):
    def __init__(self):
        super(PointRT, self).__init__()
        
    def configure(self, config):
        super(PointRT, self).configure(config)
        
    def configuration(self):
        config = super(PointRT, self).configuration()
        return config
    
    def get(self, skipcache=0):
        return self.parent.get_rt_value_by_name(self.name, skipcache)

class RelayPointRT(PointRT):
    """Relay Point
    
    Provides set method too
    """
    
    def __init__(self):
        self._dirty = True
        super(RelayPointRT, self).__init__()

    def set(self, value):
        try:
            value = as_boolean(value)
        except EInvalidValue:
            raise
        if value:
            value = 0x07
        value = value + 0x33
        #someone has to take responsibility of adding 0x33.
        #Putting it on point, as I couldn't find any other person to do it
        self.parent.set_cr_value(value)
        self._set_dirty_flag()

    def get(self, skipcache=0):
        if self._is_dirty():
            skipcache = True
            
        value = super(RelayPointRT, self).get(skipcache)
        self._reset_dirty_flag()
        return value

    def _set_dirty_flag(self):
        self._dirty = True

    def _reset_dirty_flag(self):
        self._dirty = False

    def _is_dirty(self):
        return self._dirty

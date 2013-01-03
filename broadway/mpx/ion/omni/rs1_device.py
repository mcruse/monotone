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
import mpx.lib.omni.rs1 as device
from mpx.lib.exceptions import EAlreadyRunning, ENotRunning
from mpx.lib.exceptions import EInvalidMessage
from mpx.lib.exceptions import EBadChecksum
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.ion.omni.omni_device import OmniDevice
from mpx.ion.omni import calc_sum, format_reading

class DeviceRS1(OmniDevice):
    
    def __init__(self):
        self.request_obj = device.readmeterreq()
        self.response_obj = device.readmeterres()
        self.value = None
        super(DeviceRS1, self).__init__()

    def start(self):
        if self.is_running():
            raise EAlreadyRunning()
        self.configure_packet()
        super(DeviceRS1, self).start()

    def configure_packet(self):
        req_addr = self.request_obj.findChildByName('addr')
        req_cs = self.request_obj.findChildByName('cs')
        req_addr.setValue(self.bin_addr)
            #0xD9 is checksum of rest of field, which will remain constant
        checksum = (0xD9 + calc_sum(self.bin_addr)) & 0xFF
        req_cs.setValue(checksum)

    def _read(self, wait_time=None, numretries=None):
        """Reads the device.

        Sends the request packet, recieves the response packet.
        Parses it. Updates the current reading value

        Should be called only by get_value()
        """
        if numretries is None:
            numretries = self.retry_count
        while numretries:
            try:
                self._send_request(self.request_obj,
                                   self.response_obj, wait_time, 1)
                resp_addr = self.response_obj.findChildByName('addr')
                resp_cs = self.response_obj.findChildByName('cs')
                resp_data = self.response_obj.findChildByName('data')
                addr = resp_addr.getValue()
                cs = resp_cs.getValue()
                data = resp_data.getValue()
                checksum = (0x5D + calc_sum(addr) + calc_sum(data)) & 0xFF
                if checksum != cs:
                    #some error in the response packet
                    if self.debug:
                        msglog.log("omnimeter", msglog.types.WARN, 
                                   "Checksum didn't match %s" % self.address)
                    raise EBadChecksum()
                if self.bin_addr != addr:
                    #it's not me. don't think this would ever happen, but who knows
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.WARN, 
                                   "Got some other meter's response (Strange!!) %s"
                                   % self.address)
                    raise EInvalidMessage()
                meter_reading = format_reading(data)
                self.update_value(meter_reading)
                return
            except:
                numretries -= 1
        raise 
        
    def get_value(self, skipcache=0):
        """get method.

        returns the current meter reading
        """

        if not self.is_running(): 
            raise ENotRunning()
        self.lock.acquire()
        try:
            if self.is_value_stale() or skipcache:
                self._read()
        finally:
            self.lock.release()
        return self.value

class PointRS1(CompositeNode):
    def __init__(self):
        super(PointRS1, self).__init__()
        
    def configure(self, config):
        super(PointRS1, self).configure(config)

    def configuration(self):
        config = super(PointRS1, self).configuration()
        return config

    def get(self, skipcache=0):
        return self.parent.get_value(skipcache)

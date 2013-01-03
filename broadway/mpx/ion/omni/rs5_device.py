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
import mpx.lib.omni.rs5 as device
from mpx.lib.exceptions import EAlreadyRunning, ENotRunning, MpxException
from mpx.lib.exceptions import EInvalidMessage, EConnectionError
from mpx.lib.exceptions import EBadChecksum
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.ion.omni.omni_device import OmniDevice
from mpx.ion.omni import calc_sum, format_reading

class DeviceRS5(OmniDevice):

    def __init__(self):
        self.request_obj = device.readmeterreq()
        # In NBM RS485 request packet is loopedback followed by 
        # the real response
        self.response_obj = device.readmeterres()
        self.value = {'EM':None,'WM':None,'HM':None,'GM':None,'CM':None,
                      'SP':None }
        super(DeviceRS5, self).__init__()

    def start(self):
        if self.is_running():
            raise EAlreadyRunning()
        self.configure_packet()
        super(DeviceRS5, self).start()

    def configure_packet(self):
        req_addr = self.request_obj.findChildByName('addr')
        req_cs = self.request_obj.findChildByName('cs')
        req_addr.setValue(self.bin_addr)
        checksum = (0x39 + calc_sum(self.bin_addr)) & 0xFF
        req_cs.setValue(checksum)

    def _read(self, wait_time=None, numretries=None):
        """Reads the device
        Sends the request packet, recieves the response packet,
        Parses it. Updates the current reading value

        Shouldn't be called by anyone. Use get_value_by_name instead
        """
        if numretries is None:
            numretries = self.retry_count
        while numretries:
            try:
                self._send_request(self.request_obj,
                                   self.response_obj, wait_time, 1)
                resp_addr = self.response_obj.findChildByName('addr')
                resp_data = self.response_obj.findChildByName('data')
                resp_cs = self.response_obj.findChildByName('cs')
                addr = resp_addr.getValue()
                data = resp_data.getValue()
                cs = resp_cs.getValue()
                #relay variable included because of bug #CSCts88534
                relay = 0
                resp_relay = self.response_obj.findChildByName('relay')
                if resp_relay is not None:
                    relay = resp_relay.getValue() + 1
                checksum = (0xD2 + calc_sum(addr) + 
                            calc_sum(data) + relay) & 0xFF
                if self.debug:
                    msglog.log('omnimeter', msglog.types.INFO, 
                               'checksum calculated %s Received %s' 
                               % (str(checksum),
                                  str(cs)))
                if checksum != cs:
                    msglog.log("omnimeter", msglog.types.WARN, 
                               "Checksum didn't match %s" % self.address)
                    raise EBadChecksum()
                if self.bin_addr != addr:
                    #it's not me. don't think this would ever happen, but who knows
                    msglog.log('omnimeter', msglog.types.WARN, 
                               "Got some other meter's response (Strange!!!) %s" % 
                               self.address)
                    raise EInvalidMessage()
                #everything fine till here, get the reading and update self.value
                #Get the error status flag
                meter_reading = {}
                err_status = ord(data[24]) - 0x33
                if not (err_status & 0x01):
                    meter_reading['SP'] = format_reading(data[20:24])
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO, 
                                   "Got Reading SP:%s" % (meter_reading['SP'],))
                else:
                    meter_reading['SP'] = EConnectionError()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO,
                                   'Did not get reading for SP')
                if not (err_status & 0x02):
                    meter_reading['CM'] = format_reading(data[12:16])
                    if self.debug:
                        msglog.log('omnimeter',msglog.types.INFO, 
                                   "Got Reading CM:%s" % (meter_reading['CM'],))
                else:
                    meter_reading['CM'] = EConnectionError()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO,
                                   'Did not get reading for CM')
                if not (err_status & 0x04):
                    meter_reading['GM'] = format_reading(data[8:12])
                    if self.debug:
                        msglog.log('omnimeter',msglog.types.INFO, 
                                   "Got Reading GM:%s" % (meter_reading['GM'],))
                else:
                    meter_reading['GM'] = EConnectionError()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO,
                                   'Did not get reading for GM')
                if not (err_status & 0x08):
                    meter_reading['HM'] = format_reading(data[4:8])
                    if self.debug:
                        msglog.log('omnimeter',msglog.types.INFO, 
                                   "Got Reading HM:%s" % (meter_reading['HM'],))
                else:
                    meter_reading['HM'] = EConnectionError()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO,
                                   'Did not get reading for HM')
                if not (err_status & 0x10):
                    meter_reading['WM'] = format_reading(data[0:4])
                    if self.debug:
                        msglog.log('omnimeter',msglog.types.INFO, 
                                   "Got Reading WM:%s" % (meter_reading['WM'],))
                else:
                    meter_reading['WM'] = EConnectionError()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO,
                                   'Did not get reading for WM')
                if not (err_status & 0x20):
                    meter_reading['EM'] = format_reading(data[16:20])
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO, 
                                   "Got Reading EM:%s" 
                                   % (meter_reading['EM'],))
                else:
                    meter_reading['EM'] = EConnectionError()
                    if self.debug:
                        msglog.log('omnimeter', msglog.types.INFO,
                                   'Did not get reading for EM')
                self.update_value(meter_reading)
                return
            except:
                numretries -= 1
        raise

    def get_value_as_dict(self):
        """Only for debugging purpose
        
        """
        return self.value

    def get_value_by_name(self, name, skipcache=0):
        """Get method for RS-5

        This method takes a name. 
        Name is case sensitive
        """
        if not self.is_running():
            raise ENotRunning()
        if isinstance(self.value[name], MpxException):
            if self.debug:
                msglog.log('omnimeter', msglog.types.INFO, 
                           ('Last request had failed. So nothing in cache.'
                            'Sending packet again %s') % str(self.address))
            skipcache = 1
        self.lock.acquire()
        try:
            if self.is_value_stale() or skipcache:
                self._read()
        finally:
            self.lock.release()
        if isinstance(self.value[name], MpxException):
                raise self.value[name]
        return self.value[name]

class PointRS5(CompositeNode):
    def __init__(self):
        super(PointRS5, self).__init__()
     
    def configure(self, config):
        super(PointRS5, self).configure(config)

    def configuration(self):
        config = super(PointRS5, self).configuration()
        return config

    def get(self, skipcache=0):
        return self.parent.get_value_by_name(self.name.upper(), skipcache)

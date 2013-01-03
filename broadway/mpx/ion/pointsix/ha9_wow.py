"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import array
import time

from mpx.lib import msglog, threading
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute, get_attribute, \
     as_boolean, as_onoff
from mpx.lib.exceptions import EAlreadyRunning, \
     ETimeout, EInvalidValue

class HA9(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.running = 0
        self.devices = {}
    
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'debug', 0, config, as_boolean)
        self.port = self.parent
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        return config
    
    def start(self):
        if not self.running:
            if self.port.configuration()['baud'] != '19200':
                msglog.log(msglog.types.WARN, 'HA9-WOW Port baud incorrect')
            self.running = 1
            for child in self.children_nodes():
                self.devices[child.serial] = child
            if not self.port.is_open():
                self.port.open()
            t = threading.Thread(target=self._run,args=())
            t.start()
        else:
            raise EAlreadyRunning
    
    def stop(self):
        self.running = 0
    
    def _run(self):
        while self.running:
            input = array.array('c')
            try:
                self.port.read_upto(input, [chr(0x0d)], 60)
                input = input.tostring()
            except ETimeout:
                continue
            if not self._check_crc(input[0:22], input[22:26]):
                continue
            time_in = time.time()
            mode = input[0:2]
            device_id = input[2:18]
            value = input[18:22]
            if self.devices.has_key(device_id):
                self.devices[device_id].last_time = time_in
                self.devices[device_id].value = value
    
    def _check_crc(self, data, crc):
        return 1

def factory():
    return HA9()

"""
Copyright (C) 2002 2008 2010 2011 Cisco Systems

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
from _device import Device
from mpx.lib import msglog
from mpx.lib.node import CompositeNode, as_node, as_node_url
from mpx.lib.configure import set_attribute, get_attribute, \
     REQUIRED
from mpx.lib.exceptions import ETimeout, EInvalidValue
from mpx.lib.translator import Translator
from mpx.lib.translator.f_from_c import FfromC
from mpx.lib.translator.k_from_c import KfromC

class TemperatureHumidity(Device):
    class _Temperature(CompositeNode):
        def configure(self, config):
            CompositeNode.configure(self, config)
            set_attribute(self, 'timeout', self.parent.timeout, config, int)
        
        def configuration(self):
            config = CompositeNode.configuration(self)
            get_attribute(self, 'timeout', config, str)
            return config
        
        def get(self, skip_cache=0):
            if self.parent.value == None or \
               time.time() - self.parent.last_time > self.timeout:
                raise ETimeout('Value has not been received yet or is stale')
            value = self.parent.value
            return int(value[2:4],16)
        
        def is_negative(self):
            value = self.parent.value
            if int(value[0],16) & 0x08:
                return True
            return False
    
    class _C(Translator):
        def get(self, skip_cache=0):
            subtract = 0
            value = self.ion.get(skip_cache)
            if self.ion.is_negative():
                subtract = 128
            return (value / 2.0) - subtract
    
    class _Humidity(CompositeNode):
        def configure(self, config):
            CompositeNode.configure(self, config)
            set_attribute(self, 'timeout', self.parent.timeout, config, int)
        
        def configuration(self):
            config = CompositeNode.configuration(self)
            get_attribute(self, 'timeout', config, str)
            return config
        
        def get(self, skip_cache=0):
            if self.parent.value == None or \
               time.time() - self.parent.last_time > self.timeout:
                raise ETimeout('Value has not been received yet or is stale')
            value = self.parent.value[0:2]
            return int(value,16) & 0x7f
    
    def __init__(self):
        self.value = None
        self.last_time = 0
        CompositeNode.__init__(self)
    
    def configure(self, config):
        Device.configure(self, config)
        set_attribute(self, 'timeout', 300, config, int)
        humidity = self._Humidity()
        humidity.configure({'name':'RH', 'parent':self})
        temp = self._Temperature()
        temp.configure({'name':'temperature', 'parent':self})
        c = self._C()
        c.configure({'name':'C', 'parent':temp, 'ion':temp})
        f = FfromC()
        f.configure({'name':'F', 'parent':temp, 'ion':c})
        k = KfromC()
        k.configure({'name':'K', 'parent':temp, 'ion':c})
    
    def configuration(self):
        config = Device.configuration(self)
        get_attribute(self, 'timeout', config, str)
        return config

def factory():
    return TemperatureHumidity()

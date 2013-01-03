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
from mpx.lib.bacnet import network
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.ion.bacnet.network import _Network
from mpx.lib.bacnet.bvlc import start_bbmd_service
from mpx.ion.host.eth.ip import IP

class BacnetIp(_Network):
    def configure(self, config):
        _Network.configure(self, config)
        set_attribute(self, 'port', REQUIRED, config, int)
        
    def configuration(self):
        config = _Network.configuration(self)
        get_attribute(self, 'port', config, str)
        return config
    
    def start(self):
        if self.debug:
            print 'open interface'
            print str(self.network)
        if self.parent.__class__ == IP: #then under 'internet_protocol node' (<=1.3)
            name = self.parent.parent.name
        else: #must be directly under eth# (1.4)
            name = self.parent.name
        self.interface = network.open_interface('IP', name, self.network, port=self.port)
        if self.debug:
            print 'interface opened, now start children'
            print 'starting BacnetIP'
            print self.children_names()
        _Network.start(self)
    def stop(self):
        network.close_interface(self.interface)
        _Network.stop(self)
            
def factory():
    return BacnetIp()

"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.lib.node import Node

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import set_attributes, get_attributes, as_boolean

class Application(Node):
    __node_id__ = "58266060-5c54-46e2-8190-ffd597aca507"
    def __init__(self):
        Node.__init__(self)
        self._cbus = None
        self.app = None
        return
    def _get_cbus(self):
        return self.parent._get_cbus()
    def configure(self,config):
        Node.configure(self,config)
        set_attribute(self, 'app', REQUIRED, config, int)
        return
    def configuration(self):
        config = Node.configuration(self)
        get_attribute(self, 'app', config)
        return config
    def start(self):
        self._cbus = self._get_cbus()
        Node.start(self)
        return
    def stop(self):
        Node.stop(self)
        self._cbus = None
        return

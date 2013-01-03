"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx.lib.threading import Condition,Lock
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import CompositeNode,as_node,as_node_url

class _Value:
    def __init__(self):
        self._value = None
        self._last_time = 0
    def set(self,value):
        self._last_time = time.time()
        self._value = value
    def get(self, skipCache=0):
        return self._value
    def age(self):
        return time.time() - self._time

class CachedValue(CompositeNode):
    def __init__(self):
        self._lock = Lock()
        self._value = _Value()
        CompositeNode.__init__(self)
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'expires_after', 0, config, float)
        set_attribute(self, 'node', self.parent, config, as_node)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'expires_after', config, str)
        get_attribute(self, 'node', config, as_node_url)
        return config
    def get(self, skipCache=0):
        self._lock.acquire()
        try:
            if self._value.age() > self.expires_after:
                self._value.set(self.node.get())
        finally:
            self._lock.release()
        return self._value.get()

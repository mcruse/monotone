"""
Copyright (C) 2002 2005 2011 Cisco Systems

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
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import CompositeNode,as_node
from mpx.lib.configure import as_boolean
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import EventProducerMixin
import time

def _get_func(name):
    return _conversions[name]

def _get_name(function):
    for name,func in _conversions.items():
        if func == function:
            return name
    raise KeyError

def _no_conversion(value):
    return value

_conversions = {'str':str,
                'int':int,
                'float':float,
                'boolean':as_boolean,
                'none':_no_conversion}

class ChangeFlag(CompositeNode):
    def __init__(self):
        self._last_value = None
        CompositeNode.__init__(self)
    def configure(self,config):
        set_attribute(self,'node',None,config)
	CompositeNode.configure(self,config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self,'node',config)
        return config
    def start(self):
        CompositeNode.start(self)
        if self.node is not None:
            self._node = as_node(self.node)
        else:
            self._node = self.parent
    def get(self):
        last_value = self._last_value
        self._last_value = self._node.get()
	if last_value is None:
	  return 0
        return last_value != self._last_value

class SimpleValue(CompositeNode, EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
    def configure(self,config):
        set_attribute(self, 'conversion', _get_func('none'), config, _get_func)
        set_attribute(self, 'value', None, config, self.conversion)
        CompositeNode.configure(self,config)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'conversion', config, _get_name)
        get_attribute(self, 'value', config, str)
        return config
    
    def get(self, skipCache=0):
        return self.value
    
    def set(self,value, asyncOK=1):
        old_value = self.value
        self.value = self.conversion(value)
        self._trigger_cov(self.value, old_value)  # notify SM

    def _trigger_cov(self, new_value, old_value):
        if new_value != old_value: # prevent needless events for unchanging value
            cov_event = ChangeOfValueEvent(self, old_value, \
                        new_value, time.time())
            self.event_generate(cov_event)

    def event_subscribe(self, *args): # called for a new event subscription
        EventProducerMixin.event_subscribe(self, *args)
        # trigger initial value update to get things started
        self._trigger_cov(self.value, None)

    def has_cov(self): # lets the SM know we support cov
        return True

class SimplePersistentValue(SimpleValue):
    def configure(self, config):
        SimpleValue.configure(self, config)
        self._pdo = PersistentDataObject(self)
        self._pdo.value = None
        self._pdo.conversion = None
        self._pdo.load()
        conversion = _get_name(self.conversion)
        if (self._pdo.value == None or 
            self._pdo.conversion != conversion):
            self._pdo.value = self.value
            self._pdo.conversion = conversion
            self._pdo.save()
        else:
            self.value = self._pdo.value
    def configuration(self):
        self.value = self._pdo.value
        return SimpleValue.configuration(self)
    def set(self,value,asyncOK=1):
        SimpleValue.set(self, value, asyncOK)
        self._pdo.value = self.value
        self._pdo.save()
    def get(self, skipCache=0):
        return self._pdo.value

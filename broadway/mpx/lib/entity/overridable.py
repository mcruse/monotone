"""
Copyright (C) 2009 2010 2011 2012 Cisco Systems

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
# An overridable node

from mpx.lib import ReloadableSingletonFactory
from mpx.lib.persistence.datatypes import PersistentDictionary
from mpx.lib.node import NodeDecorator
from mpx.lib.node import CompositeNode
from mpx.lib.node import ConfigurableNode
from mpx.lib.node import is_settable
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.lib.exceptions import EInvalidValue
from types import StringType 

RELINQUISH_DEFAULT = '17'
CONFIG_DEFAULT = '18'
   
def is_overridable(obj):
    return hasattr(obj, 'override') and hasattr(obj, 'release')

def assert_level(level):
    level = int(level)
    if level < 1 or level > 16:
        msg = 'Override level must be between 1 and 16.'
        raise EInvalidValue("level", str(level), msg)
        
class OverrideManager(object):
    def __init__(self):
        self._priority_arrays = PersistentDictionary('OverrideManager')
    
    def get_array(self, nodepath):
        pa = self._priority_arrays.get(nodepath)
        if pa is None:
            pa = {'1':None, '2':None,
                  '3':None, '4':None,
                  '5':None, '6':None,
                  '7':None, '8':None,
                  '9':None, '10':None,
                  '11':None, '12':None,
                  '13':None, '14':None,
                  '15':None, '16':None,
                  '17':None, '18':None}
            self._priority_arrays[nodepath] = pa
        return pa
    
    def notify_changed(self, nodepath, priority_array=None):
        if priority_array is not None:
            self._priority_arrays[nodepath] = priority_array
        self._priority_arrays.notify_changed(nodepath)
    
    def singleton_unload_hook(self):
        pass
    
class Override(tuple):
    def __new__(cls, value, priority):
        return tuple.__new__(cls, (value, priority))
    
    def __init__(self, value, priority):
        self.__value = value
        self.__priority = priority
    
    def __get_value(self):
        return self.__value
    value = property(__get_value)
    
    def __get_priority(self):
        return self.__priority
    priority = property(__get_priority)
    
    def __int__(self):
        return int(self.value)
    
    def __float__(self):
        return float(self.value)
    
    def __eq__(self, o):
        if self.__class__ != o.__class__:
            return self.value == o
        return self.value == o.value
    
    def __ne__(self, o):
        return not self.__eq__(o)
    
    def __lt__(self, o):
        if self.__class__ != o.__class__:
            return self.value < o
        return self.value < o.value
    
    def __le__(self, o):
        if self.__class__ != o.__class__:
            return self.value <= o
        return self.value <= o.value
    
    def __gt__(self, o):
        if self.__class__ != o.__class__:
            return self.value > o
        return self.value > o.value
    
    def __ge__(self, o):
        if self.__class__ != o.__class__:
            return self.value >= o
        return self.value >= o.value
    
    def __add__(self, o):
        if self.__class__ != o.__class__:
            return self.value + o
        return self.value + o.value
    
    def __radd__(self, o):
        if self.__class__ != o.__class__:
            return o + self.value
        return o.value + self.value
    
    def __sub__(self, o):
        if self.__class__ != o.__class__:
            return self.value - o
        return self.value - o.value
    
    def __rsub__(self, o):
        if self.__class__ != o.__class__:
            return o - self.value
        return o.value - self.value
    
    def __mul__(self, o):
        if self.__class__ != o.__class__:
            return self.value * o
        return self.value * o.value
    
    def __rmul__(self, o):
        if self.__class__ != o.__class__:
            return o * self.value
        return o.value * self.value
    
    def __div__(self, o):
        if self.__class__ != o.__class__:
            return self.value / o
        return self.value / o.value
    
    def __rdiv__(self, o):
        if self.__class != o.__class__:
            return o / self.value
        return o.value / self.value
    
    def __divmod__(self, o):
        if self.__class__ != o.__class__:
            return divmod(self.value, o)
        return divmod(self.value, o.value)
    
    def __rdivmod__(self, o):
        if self.__class__ != o.__class__:
            return divmod(o, self.value)
        return divmod(self.value, o.value)
    
    def __floordiv__(self, o):
        if self.__class__ != o.__class__:
            return self.value // o
        return self.value // o.value
    
    def __rfloordiv__(self, o):
        if self.__class__ != o.__class__:
            return o // self.value
        return o.value // self.value
    
    def __mod__(self, o):
        if self.__class__ != o.__class__:
            return self.value % o
        return self.value % o
    
    def __rmod__(self, o):
        if self.__class__ != o.__class__:
            return o % self.value
        return o % self.value
    
    def __abs__(self):
        return abs(self.value)
    
    def __neg__(self):
        return -self.value
    
    def __pow__(self, o, z=None):
        if self.__class__ != o.__class__:
            y = o
        else:
            y = o.value
        if z is not None:
            return pow(self.value, y, z)
        return pow(self.value, y)
    
    def __rpow__(self, o, z=None):  
        if self.__class__ != o.__class__:
            x = o
        else:
            x = o.value
        if z is not None:
            return pow(x, self.value, z)
        return pow(x, self.value) 
    
class OverrideDict(object):
    def __init__(self, priority_array, default):
        self._ovr = {}
        for x in range(1, 16+1):
            x = str(x)
            self._ovr[x] = priority_array.get(x)
        self.default = default
        self.__active = None
        
    def as_dict(self):
        a_dict = self._ovr.copy()
        a_dict['active'] = self.active
        a_dict['default'] = self.default
        return a_dict
        
    def get_override(self, level):
        return self._ovr[str(level)]
        
    def set_override(self, value, level):
        assert_level(level)
        self._ovr[str(level)] = value
        # recalc active
        self.__active = None
    
    def __str__(self):
        return str(self.as_dict())
    
    def __repr__(self):
        return str(self)
    
    def __get_active(self):
        active = RELINQUISH_DEFAULT
        if self.__active is None:
            for index in range(1,17):
                index = str(index)
                if self._ovr[index] is not None:
                    active = index
                    break
            self.__active = active
        return self.__active
        
    active = property(__get_active)
    
class OverrideMixin(object):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, *args, **kw):
        self.__priority_array = None
        self.__relinquish_default = kw.get('relinquish_default', None)
        self.__active = '17'
        self._set_target = self
        
    def restore_override(self):
        self.__priority_array = OVERRIDE_MANAGER.get_array(self.as_node_url())
        self.__update_active()
        current_default = self.get_default()
        cd_default = self.__priority_array[CONFIG_DEFAULT]
        if self.__relinquish_default != cd_default:
            self.__priority_array[CONFIG_DEFAULT] = dflt
            if dlft != current_default:
                self.__priority_array[RELINQUISH_DEFAULT] = dflt
        if not self.has_child('Priority Array'):
            pa = PriorityArrayNode()
            cd = {'name':'Priority Array',
                  'parent':self}
            pa.configure(cd)
            for idx in range(1, 16+1):
                level = Level()
                cd = {'name':str(idx),
                      'parent':pa}
                level.configure(cd)
    
    security.protect('override', 'Override')
    def override(self, value, level=16):
        override_list = []
        pre_ovr_values_list = []
        released = False
        active_level = self.__get_active()
        active_value = self.__priority_array[active_level]
        if isinstance(value, OverrideDict):
            current_ovr = self.get_override()
            for pa_level in range(1, 16+1):
                ovr = value.get_override(pa_level)
                if isinstance(ovr, StringType):
                    try:
                        ovr = float(ovr)
                    except:
                        pass
                if ovr != current_ovr.get_override(pa_level):
                    override_list.append((ovr, pa_level))
        else:
            if isinstance(value, StringType):
                try:
                    value = float(value)
                except:
                    pass
            override_list.append((value, level))
        for value, level in override_list:
            # for historical reasons, override(None, level) has the same behavior 
            # as release(level)
            if value is None or value == 'None':
                self.release(level)
                continue
            level = str(level)
            try:
                self.__assert_level(level)
            except:
                continue
            if self.__priority_array[level] != value:
                pre_ovr_values_list.append((self.__priority_array[level], level))
                self.__priority_array[level] = value
                OVERRIDE_MANAGER.notify_changed(
                    self.as_node_url(), self.__priority_array
                )
                if int(level) <= int(self.__get_active()):
                    self.__active = level
        new_active_level = self.__get_active()
        new_active_value = self.__priority_array[new_active_level]
        #CSCtn72781
        if active_level != new_active_level or active_value != new_active_value or \
        (active_level == new_active_level and active_value == new_active_value):
            # this latest override takes precedence
            if hasattr(self._set_target, 'set_proxy'):
                try:
                   self._set_target.set_proxy(new_active_value)
                except:
                   #Revert values if Device is offline and Override fails
                   for prior_value, level in pre_ovr_values_list:
                      self.__priority_array[level] = prior_value
                   OVERRIDE_MANAGER.notify_changed(self.as_node_url(), self.__priority_array)
            else:
                try:
                   self._set_target.set(new_active_value)
                except:
                   for prior_value, level in pre_ovr_values_list:
                      self.__priority_array[level] = prior_value
                   OVERRIDE_MANAGER.notify_changed(self.as_node_url(), self.__priority_array)
                   
    security.protect('release', 'Override')
    def release(self, level):
        self.__assert_level(level)
        level = str(level)
        pa = self.__priority_array
        last_value = pa[level]
        pa[level] = None
        OVERRIDE_MANAGER.notify_changed(self.as_node_url())
        self.__update_active()
        active = self.__get_active()
        value = pa[active]
        if value != last_value:
            if not(active == RELINQUISH_DEFAULT and value == None):
                if hasattr(self._set_target, 'set_proxy'):
                    self._set_target.set_proxy(value)
                else:
                    self._set_target.set(value)
    
    security.protect('get_override', 'View')
    def get_override(self):
        pa = self.__priority_array.copy()
        active = self.__get_active()
        default = self.get_default()
        return OverrideDict(pa, default)
    
    security.protect('get_override_at', 'View')
    def get_override_at(self, level):
        return self.__priority_array[str(level)]
    
    security.protect('set_default', 'Override')
    def set_default(self, value):
        self.__priority_array[RELINQUISH_DEFAULT] = value
 
    security.protect('get_default', 'View')
    def get_default(self):
        return self.__priority_array[RELINQUISH_DEFAULT]
    
    security.protect('get_write_priority', 'View')
    def get_write_priority(self):
        wp = int(self.__get_active())
        if wp == 17:
            wp = None
        return wp
    
    def __get_active(self):
        return self.__active
    
    def __assert_level(self, level):
        assert_level(level)
        
    def __update_active(self):
        active = RELINQUISH_DEFAULT
        for index in range(1,17):
            index = str(index)
            if self.__priority_array[index] is not None:
                active = index
                break
        self.__active = active
        
class PriorityArrayNode(CompositeNode):
    pass

class Level(ConfigurableNode):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self):
        ConfigurableNode.__init__(self)
        self.__device = None
        
    def set(self, value):
        level = self.name
        self.device.override(value, level)
        
    def get(self, skipCache=0):
        level = self.name
        return self.device.get_override_at(level)
    
    def _get_device(self):
        if self.__device is None:
            self.__device = self.parent.parent
            assert hasattr(self.__device, 'override'), (
                'Device must support the override method before associating priority arrays.'                                        
                )
        return self.__device
    
    device = property(_get_device)

class OverrideDecorator(OverrideMixin, NodeDecorator):
    _PREFIX = 'ovr_decorator_'
    def __init__(self, *args, **kw):
        OverrideMixin.__init__(self)
        NodeDecorator.__init__(self)
        
    def start(self):
        # OverrideDecorators manage the override behavior of their parent node.
        #directly_provides(self.parent, IOverridable)
        self._set_target = self.parent
        for attr in ['override', 'release' 'get_override', 'set_default', 'get_default']:
            self.set_attribute(attr, getattr(self, attr), {}, strict=False)
                
def add_override(node, **kw):
    assert is_settable(node), (
        'Node\'s must support the set method before adding override behavior.'
        )
    cd = {'name':'__override__',
          'parent':node}
    ovr = OverrideDecorator(kw)
    ovr.configure(cd)
    ovr.start()
    
OVERRIDE_MANAGER = ReloadableSingletonFactory(OverrideManager)


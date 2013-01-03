"""
Copyright (C) 2002 2003 2004 2005 2006 2007 2010 2011 Cisco Systems

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
import time, string, types

from mpx.ion import Result
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.bacnet._exceptions import *
from mpx.lib.exceptions import EUnreachableCode
from mpx.lib.bacnet import property
from mpx.lib.bacnet.property import _Property as GenericProperty
from mpx.lib.bacnet.property import properties, prop_from_id
from mpx.lib.exceptions import EPermission
from mpx.lib.bacnet._bacnet import read_property_multiple_g3 as rpm
from mpx.lib import msglog
from mpx.lib.bacnet._exceptions import BACnetError, BACnetReject
from mpx.lib.bacnet.sequence import _OPTIONAL as OPTIONAL

from mpx.lib.persistent import PersistentDataObject
from mpx.lib import msglog
from mpx.lib import Callback

MAXIMUM_CACHE_AGE = 10.0
debug = 0

def underscored_name(s):
    def f(c): return c not in string.punctuation
    return string.join(filter(f, s.replace('/',' ')).split(), '_').lower()

def from_id(id):
    if prop_from_id.has_key(id):
        return eval(prop_from_id[id]+'()')
    return _Property(id)

def name_string(node_or_class, identifier):
    #answer a string based on our class name
    #override in subclass for properties that don't conform to this name convention
    #print 'base: ', node_or_class, identifier
    try:
        answer = ''
        classname = '_Property'
        if isinstance(node_or_class, ConfigurableNode):
            classname = node_or_class.__class__.__name__
        elif type(node_or_class) == types.ClassType:
            classname = node_or_class.__name__
        elif type(node_or_class) == types.TypeType:
            classname = node_or_class.__name__
        if classname == '_Property': #no class name, use ID number
            classname = prop_from_id[identifier]
            return underscored_name(classname)
        for char in classname:
            if char.isupper():
                if len(answer):
                    answer += '_'
                answer += char.lower()
            else:
                answer += char
        return answer
    except:
        print 'base exception: ', node_or_class, identifier
        raise

class _PersistentAttribute(PersistentDataObject):
    def __init__(self, node):
        self.server_attribute = None
        PersistentDataObject.__init__(self, node)
        PersistentDataObject.load(self)

class _Property(CompositeNode): #, AutoDiscoveredNode):
    _server_attribute = None
    _server_conversion = int
    _default_ttl = 10
    _node_def_id = None
    _server_default = REQUIRED
    def __init__(self, identifier=None):
        CompositeNode.__init__(self)
        #AutoDiscoveredNode.__init__(self)
        self.__node_id__ = self._node_def_id
        self._parent_device = None
        self._generic_property = GenericProperty
        self.identifier = identifier
        self.bacnet_property = None
        self.get_batch_manager = self._get_batch_manager
        self._local_batch_manager = None
        self._array_discovered = 0
        self._pdo = None
        
    def configure(self, cd, identifier=None):
        from mpx.ion.bacnet.network import vendor_mods
        CompositeNode.configure(self, cd)
        if identifier is None:
            if self.identifier is None:
                props = properties # basic BACnet properties imported from mpx.lib.bacnet.property
                try: # in case no device_info found below:
                    vendor_id = self.parent.parent.device_info.vendor_id
                    if not vendor_id is None:
                        if vendor_mods.has_key(vendor_id):
                            vendor_lib_module_prop = vendor_mods[vendor_id].lib_prop
                            props = getattr(vendor_lib_module_prop, 'properties')
                except:
                    pass
                if props.has_key(self.__class__.__name__):
                    if debug:
                        print 'configure property for: ',self.__class__.__name__
                    identifier = props[self.__class__.__name__][0]
            else:
                identifier = self.identifier #for numerically defined properties
        if identifier is None:
            raise EMissingAttribute, 'property type missing'
        self.identifier = identifier
        set_attribute(self, 'ttl', self._default_ttl, cd, int)
        set_attribute(self, 'discovered', 0, cd, int)
        self._parent_device = self.parent._parent_device
        self.is_client = self._parent_device.is_client()
        self.is_server = not self.is_client
        if self._server_attribute:
            if self.is_server:
                set_attribute(self, self._server_attribute, self._server_default, cd, self._server_conversion)
                #assert hasattr(self, self._server_attribute), 'Failed to add server_attribute! (Check XML source file...)'
                #hack until bug#5387 is fixed
                if self._server_attribute == 'OPTIONAL':
                    self._server_attribute = self._server_default
                #end hack
            else: #since client
                set_attribute(self, self._server_attribute, None, cd)
        set_attribute(self, '__node_id__',self.__node_id__, cd, str)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'discovered', cd, str)
        get_attribute(self, 'ttl', cd, str)
        get_attribute(self, '__node_id__', cd)
        if self._server_attribute:
            get_attribute(self, self._server_attribute, cd, str)
            if self._pdo:
                self.__pdo_filename__ = self._pdo._persistent.filename
                get_attribute(self, '__pdo_filename__', cd, str)
        if self.bacnet_property is not None:
            cd['object_type'] = str(self.bacnet_property.object_type)
            cd['identifier'] = str(self.bacnet_property.identifier)
        return cd
    def start(self):
        self.cache=self.parent.cache
        self._batch_manager = self.parent.parent #device
        if self.parent.parent.device_info is None:
            
            self.bacnet_property = self._generic_property(self.parent.obj_type, 
                                               self.parent.instance,
                                               None,
                                               self.identifier,
                                               None)
        else:
            self.bacnet_property = self._generic_property(self.parent.obj_type, 
                                               self.parent.instance,
                                               None,
                                               self.identifier,
                                               None,
                                               vendor_id = self.parent.parent.device_info.vendor_id)
            if not hasattr(self, 'set'): #protect existing overloaded set's
                self.set = self._set #until we have a way to tell what trane propertiers allow setting, do all
        self.bacnet_property.ttl = self.ttl
        self.bacnet_property.average_read_time = self.bacnet_property.ttl
        self.bacnet_property.owner = self
        CompositeNode.start(self)
        if self.is_client:
            # DISABLE UNTIL CACHING IS TURNED BACK ON AND FIND AGE GROUP REFACTORED TO NOT USE INSTANCE AS KEY IN DICT
            #self.cache.find_age_group_for(self.bacnet_property) #preload the age groups so the first read is productive
            pass
        elif self._server_attribute: #since server with a property to set
            try:
                pdo = self.get_pdo()
                if pdo:
                    if pdo.server_attribute is not None:
                        self.__dict__[self._server_attribute] = self._server_conversion(pdo.server_attribute)
            except:
                msglog.exception()
            self.bacnet_property.value = self.__dict__[self._server_attribute]
            
    def ripeness(self):
        return self.bacnet_property.ripeness()
        
    def get_pdo(self):
        if self.is_client:
            return None
        if self._pdo is None:
            self._pdo = _PersistentAttribute(self)
        return self._pdo

    def get(self, skipCache=0):
        if debug: '_Property get invoked'
        self.get_result(skipCache)
        return self.bacnet_property

    def get_result(self, skipCache=0, **keywords):
        if self.is_client:
            if debug: print 'get result for: ', self.name
            if keywords.has_key('callback'):
                keywords['callback'].callback(self.get_callback)
                result = self.bacnet_property.get_result_from(self.parent.parent.instance, **keywords)
                if isinstance(result, Callback):
                    return result #used as flag
            else:
                result = self.bacnet_property.get_result_from(self.parent.parent.instance, skipCache)
            answer = Result()
            answer.timestamp = result.timestamp
            answer.value = self.bacnet_property
            return result #answer
        else:
            return self.bacnet_property #get whatever we have currently
        #except EDeviceNotFound, e:
            #if debug: print 'EDeviceNotFound', str(e)
            #raise EDeviceNotFound('EDeviceNotFound  ' + self.name)

    def get_callback(self, result):
        try:
            if isinstance(result, Exception):
                return result
            if isinstance(result, Result):
                if isinstance(result.value, Exception):
                    return result
                result.value = self.bacnet_property
            return result
        except Exception, e: #any other exception
            return e
        except:
            return Exception(sys.exc_info()[0])
        
    def get_magnitude(self, skipCache=0):
        answer = self.get(skipCache)
        if answer is not None:
            return answer.as_magnitude()
        return None
    def _set(self, value, priority=None, asyncOK=1):
        #self.bacnet_property.value = value
        self._write_server_attribute(value)
        if self.is_client: #make it write to the other device
            self.bacnet_property.set(self.parent.parent.instance, priority)
    def as_tags(self, index=None):
        return self.bacnet_property.as_tags(index)
    def name_string(self):
        #answer a string based on our class name
        #override in subclass for properties that don't conform to this name convention
        return name_string(self, self.identifier)
    def write(self, value, priority=16):
        raise EPermission('not writable', self.name, 'read only property')
    def _write_server_attribute(self, value):
        self.bacnet_property.value = value
        if self.is_server:
            if self._server_attribute is not None:
                self.__dict__[self._server_attribute] = value
                if self.get_pdo():
                    try:
                        self._pdo.server_attribute = str(value)
                        self._pdo.save()
                    except:
                        msglog.exception()
    # invoke method in nodebrowser to see raw packet
    # ?action=invoke&method=_encoding
    def _encoding(self):
        return repr(self.bacnet_property.encoding())
    ##
    def _get_batch_manager(self, prop=None):
        if self.bacnet_property._can_get_multiple():
            return self.parent.get_batch_manager(self)
        return None
    def _get_local_batch_manager(self, prop=None):
        return self._local_batch_manager
    def set_batch_manager(self, m):
        self._local_batch_manager = m
        self.get_batch_manager = self._get_local_batch_manager
    def decoder(self):
        return self.bacnet_property
    def _property_tuple(self):
        return self.bacnet_property.property_tuple
        
    def _comm3segment(self):
        return self.bacnet_property._comm3segment
    def is_array(self):
        return self.bacnet_property.is_array()
    def _discover_children(self):
        if not self._array_discovered:
            if self.bacnet_property: #not None means we have started
                if self.is_array():
                    self._nascent_children['array'] = ProperyArray()
                self._array_discovered = 1
        return self._nascent_children
    def get_obj_instance(self):
        return self.parent.get_obj_instance()
class AckedTransitions(_Property):
    pass
class ActiveText(_Property):
    _server_attribute = 'active_text'
    _server_conversion = str
    def set(self, name):
        try:
            self.parent.get_child('present_value')._bpv_enum_table = None
        except:
            pass
        try:
            self.parent.get_child('priority_array')._bpv_enum_table = None
        except:
            pass
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class ActiveVtSessions(_Property):
    pass
class AlarmValue(_Property):
    pass
class ApduSegmentTimeout(_Property):
    _node_def_id = '549'
    _server_attribute = 'timeout'
    _default_ttl = 7200
    def set(self, name):
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
    pass
class ApduTimeout(_Property):
    _node_def_id = '550'
    _server_attribute = 'timeout'
    _default_ttl = 7200
    def set(self, name):
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)

def _ApplicationVersion():
    from mpx import properties as mp
    try:
        return mp.RELEASE_VERSION
    except:
        return 'unknown'

class ApplicationSoftwareVersion(_Property):
    _node_def_id = '533'
    _server_attribute = 'sw_version'
    _server_conversion = str
    _default_ttl = 7200
    _server_default = _ApplicationVersion()


class ChangeOfStateCount(_Property):
    pass
class ChangeOfStateTime(_Property):
    pass
class NotificationClass(_Property):
    pass
class CovIncrement(_Property):
    pass
class DaylightSavingsStatus(_Property):
    pass
class Deadband(_Property):
    pass
class Description(_Property):
    _server_attribute = 'description'
    _server_conversion = str
    def set(self, name):
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class DeviceAddressBinding(_Property):
    _node_def_id = '552'
    _server_conversion = eval
    _server_attribute = 'binding'
    _server_default = '[]'
    pass
class DeviceType(_Property):
    _default_ttl = 7200
    pass
class ElapsedActiveTime(_Property):
    pass
class EventEnable(_Property):
    pass
class EventState(_Property):
    _node_def_id = '557'
    _server_attribute = 'event_state'
    pass
class FeedbackValue(_Property):
    pass

def _MoeVersion():
    from mpx import properties as mp
    return mp.MOE_VERSION

#class FirmwareVersion(_Property):
    #_server_attribute = 'version'
    #_server_conversion = str
    #_default_ttl = 7200
    #_server_default = _MoeVersion()
    #pass
class FirmwareRevision(_Property):
    _node_def_id = '532'
    _server_attribute = 'revision'
    _server_conversion = str
    _default_ttl = 7200
    _server_default = _MoeVersion()
    pass

class HighLimit(_Property):
    _server_attribute = 'high_limit'
    _server_conversion = float
    def set(self, value):
        return self._set(value)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class InactiveText(_Property):
    _server_attribute = 'inactive_text'
    _server_conversion = str
    def set(self, name):
        try:
            self.parent.get_child('present_value')._bpv_enum_table = None
        except:
            pass
        try:
            self.parent.get_child('priority_array')._bpv_enum_table = None
        except:
            pass
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class LimitEnable(_Property):
    pass 
class ListOfSessionKeys(_Property):
    pass
class LocalDate(_Property): 
    def get(self, skipCache=1):
        return _Property.get(self, skipCache=1) 
class LocalTime(_Property):
    def get(self, skipCache=1):
        return _Property.get(self, skipCache=1)
class Location(_Property):
    _server_attribute = 'location'
    _server_conversion = str
    def set(self, name):
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class LowLimit(_Property):
    _server_attribute = 'low_limit'
    _server_conversion = float
    def set(self, value):
        return self._set(value)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class MaxAPDULengthSupported(_Property):
    _node_def_id = '541'
    _server_attribute = 'max_length'
    pass
class MaxPresValue(_Property):
    pass
class MinPresValue(_Property):
    pass
class ModelName(_Property):
    _node_def_id = '531'
    _server_attribute = 'model_name'
    _server_conversion = str
    pass
class NotifyType(_Property):
    pass
class NumberOfApduRetries(_Property):
    _node_def_id = '551'
    _server_attribute = 'retries'
    def set(self, value):
        return self._set(value)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
    pass
class ObjectIdentifier(_Property):
    _node_def_id = '523'
    _default_ttl = 7200
    def configure(self, cd):
        _Property.configure(self, cd)
        if self.discovered:
            self.instance = self.parent.instance
        else:
            set_attribute(self, 'instance', REQUIRED, cd, int)
    def configuration(self):
        cd = _Property.configuration(self)
        get_attribute(self, 'instance', cd, str)
        return cd
    def start(self):
        _Property.start(self)
        if self.is_server:
            self.bacnet_property.value = self.parent.object_identifier.id
class ObjectList(_Property):
    _node_def_id = '540'
    def get(self, skipCache=0):
        #@todo make lazy
        if self.is_server:
            self.bacnet_property.value = self._get_object_id_list()
        return _Property.get(self, skipCache)
        #return str(answer)
    def _get_object_id_list(self):
        answer = []
        nodes = self.parent.parent.children_nodes()
        for n in nodes:
            if n.has_child('object_identifier'):
                answer.append(n.object_identifier.id)
        return answer
    def as_tags(self, index=None): #update the current list of objects
        self.bacnet_property.value = self._get_object_id_list()
        return self.bacnet_property.as_tags(index)
class ObjectName(_Property):
    _node_def_id = '524'
    _server_conversion = str
    _server_attribute = 'obj_name'
    # ttl is a year 86400*365
    _default_ttl = 31536000
    def set(self, name):
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class ObjectType(_Property):
    _node_def_id = '527'
    def configure(self, cd):
        _Property.configure(self, cd)
        if self.discovered:
            self.obj_type = self.parent.obj_type
        else:
            set_attribute(self, 'obj_type', REQUIRED, cd, int)
    def configuration(self):
        cd = _Property.configuration(self)
        get_attribute(self, 'obj_type', cd, str)
        return cd
    def start(self):
        _Property.start(self)
        if self.is_server:
            self.bacnet_property.value = self.obj_type

class OutOfService(_Property):
    _node_def_id = '559'
    _server_attribute = 'service'
    pass
class Polarity(_Property):
    _node_def_id = '595'
    _server_attribute = 'polarity'
    def set(self, name):
        return self._set(name)
class PresentValue(_Property, AutoDiscoveredNode):
    _node_def_id = '522'  #this is 799 for commandable properties (AO,AV?,BO,BV?)
    _default_ttl = 1
    def __init__(self):
        _Property.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self._children_have_been_discovered = 1 #fool non-commandable pv 
        self.last_set_exception = None
        self._pa = None
        self.running = 0
        self.value = None
        self._is_binary_pv = None
        self._bpv_enum_table = None
    def configure(self, cd, identifier=None):
        _Property.configure(self, cd)
        if self.is_server:
            set_attribute(self, 'value', '0', cd, float)
    def configuration(self):
        cd = _Property.configuration(self)
        get_attribute(self, 'value', cd, str)
        get_attribute(self, 'last_set_exception', cd, str)
        return cd
    def start(self):
        # present value and priority array work together but may be created and started
        # in either order.  The
        _Property.start(self)
        #self.bacnet_property.value = self.value
        if self.is_server:
            self.bacnet_property.value = self.value
            self.set = self._set
        if (PriorityArray in self.parent._required_properties) or \
           (87 in self.parent._required_properties): #since we are a commandable pv
            self._node_def_id = '799' #commandable
            self._children_have_been_discovered = 0 #allow the children to be discovered
        self._is_binary_pv = self.bacnet_property.is_binary_pv()
        self.running = 1
    def write(self, value, priority=16):
        if debug: print 'PresentValue write method invoked'
        if self.pa():
            if debug: print 'Present Value priority array exists'
            if self.parent.is_proxy() and not self.parent.linked_node_has_set():
                raise EPermission('proxy linked node has no set method', self, 'PresentValue write')
            self._pa._write(value, priority)
            new_value = self._pa._highest_priority_value_for(self)
            self.bacnet_property.value = new_value
            if new_value is None:
                self.bacnet_property.value = self.parent.get_child('relinquish_default').bacnet_property.value
            if self.parent.is_proxy():
                self.parent.set(self.bacnet_property.value) #set the linked node
    def get(self, skipcache=0):
        if self.parent.is_proxy():
            answer = self.parent.get() #go get the linked value
            self.bacnet_property.value = answer
            #self.set_exception(None) # now done in proxy class
            return self.bacnet_property
        if self._is_binary_pv:
            if self._bpv_enum_table is None:
                try:
                    at = str(self.parent.get_child('active_text').get())
                    it = str(self.parent.get_child('inactive_text').get())
                    self._bpv_enum_table = {0:it, 1:at}
                    self.bacnet_property.enum_string_map = self._bpv_enum_table
                    self.bacnet_property._data = None #force creation on new one
                except: #they don't exist
                    self._is_binary_pv = 0 #don't try again
            else:
                self.bacnet_property.enum_string_map = self._bpv_enum_table
                self.bacnet_property._data = None #force recreation of data type
        return _Property.get(self, skipcache)
    def _set(self, value, priority=None, asyncOK=1):
        _Property._set(self,value, priority, asyncOK)
        self.set_exception(None)
        if self.parent.is_proxy():
            self.parent.set(self.bacnet_property.value) #set the linked node
    # below is handled by proxy class now but regular server still needs to support it
    def set_exception(self, exception):
        if self.parent.is_proxy(): return #allready handled, shouldn't be here
        if self.is_server:
            self.last_set_exception = exception
            self.parent.set_exception(exception)
    def pa(self):
        if not self.running:
            return None
        if self._pa:
            return self._pa
        if self.parent.has_child('priority_array', auto_discover=0): #don't discover
            self._pa = self.parent.get_child('priority_array')
        return self._pa
    def _discover_children(self):
        #_Property._discover_children(self)
        if self.running:
            if not self._children_have_been_discovered: #only commandble pv have children
                answer = {}
                for i in range(1, 17):
                    new_priority = Priority()
                    answer['%02d' % i] = new_priority
                    new_priority.priority = i
                self._nascent_children.update(answer)
                self._children_have_been_discovered = 1
        return self._nascent_children
    def as_tags(self, index=None):
        if self.parent.is_proxy():
            self.bacnet_property.value = self.parent.get() #which has been subverted
        return _Property.as_tags(self, index)
class PriorityArray(_Property):
    _node_def_id = '561'
    def __init__(self):
        _Property.__init__(self)
        self.priority_array = {}
        self.running = 0
        self._is_binary_pv = None
        self._bpv_enum_table = None
    def start(self):
        _Property.start(self) #get child array elements started (nothing happens now)
        if self.is_server:
            self.bacnet_property.value = self.get_result() #an array of Nones
        self._is_binary_pv = self.bacnet_property.is_binary_pv()
        self.running = 1
    def _write(self, value, priority):
        if debug: print 'write to priority array: ', value, priority
        if value is None: #clear override
            if self.priority_array.has_key(priority-1):
                del self.priority_array[priority-1]
        else:
            if debug:
                print 'set PA at / with: ', priority, value
            self.priority_array[priority-1] = value
        if debug: print 'update bacnet object'
        self.bacnet_property.value = self._get_value_array()
        if debug: print 'done with PA write'
    def _get_value_array(self):
        if debug: 
            print 'PA get value array'
        answer = []
        for i in range(0, 16):
            if self.priority_array.has_key(i):
                answer.append(self.priority_array[i])
            else:
                answer.append(None)
        if debug: print 'PA value array is: ', answer
        return answer
    def get_result(self, skipCache=0, **keywords):
        if self._is_binary_pv:
            if self._bpv_enum_table is None:
                try:
                    at = str(self.parent.get_child('active_text').get())
                    it = str(self.parent.get_child('inactive_text').get())
                    self._bpv_enum_table = {0:it, 1:at}
                    self.bacnet_property.enum_string_map = self._bpv_enum_table
                    #self.bacnet_property._data = None #force creation on new one
                except: #they don't exist
                    self._is_binary_pv = 0 #don't try again
            else:
                self.bacnet_property.enum_string_map = self._bpv_enum_table
                #self.bacnet_property._data = None #force recreation of data type
        if self.is_client:
            return _Property.get_result(self, skipCache, **keywords)
        #if we are a server object, the values are maintained here
        if debug: 
            print 'PA get result'
        answer = []
        for i in range(0, 16):
            if self.priority_array.has_key(i):
                answer.append(str(self.priority_array[i]))
            else:
                answer.append(None)
        if debug: print 'PA result is: ', answer
        return answer
    def _highest_priority_value_for(self, pv):
        if debug: print 'PA find highest priority value'
        for i in range(0, 16):
            if self.priority_array.has_key(i):
                if debug: print 'PA found value for key: ', i, self.priority_array[i]
                return self.priority_array[i]
        if debug: print 'PA highest priority not found, use: ', pv.parent.get_child('relinquish_default').bacnet_property.value
        return pv.parent.get_child('relinquish_default').bacnet_property.value
class ProtocolConformanceClass(_Property):
    _node_def_id = '537'
    pass
class ProtocolObjectTypesSupported(_Property):
    _node_def_id = '539'
    _default_ttl = 7200
    def start(self):
        _Property.start(self)
        if self.is_server:
            self.bacnet_property.value = (1,1,0,1,1,0,0,0,\
                                          1,0,0,0,0,0,0,0,\
                                          0,0,0,0,0,0,0)
class ProtocolServicesSupported(_Property):
    _node_def_id = '538'
    _default_ttl = 7200
    def start(self):
        _Property.start(self)
        if self.is_server:
            self.bacnet_property.value = (0,0,0,0,0,0,0,0,\
                                          0,0,0,0,1,0,1,1,\
                                          0,0,1,0,0,0,0,0,\
                                          0,0,1,0,0,0,0,0,\
                                          0,0,1,0,0,0,0,0)
#       12:'ReadProperty',
#       14:'ReadPropertyMultiple',
#       15:'WriteProperty',
#       26:'I_Am',
#       34:'Who_Is',
class ProtocolVersion(_Property):
    _node_def_id = '536'
    _default_ttl = 7200
    def start(self):
        _Property.start(self)
        if self.is_server:
            self.bacnet_property.value = 1
class Reliability(_Property):
    pass
class RelinquishDefault(_Property):
    _node_def_id = '562'
    _server_attribute = 'relinquish'
    _server_conversion = float
    _default_ttl = 1
    def set(self, v):
        return self._set(v)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class Resolution(_Property):
    pass
class SegmentationSupported(_Property):
    _node_def_id = '542'
    _server_attribute = 'segmentation'
    _default_ttl = 7200
    pass
class Setpoint(_Property):
    _node_def_id = '34c1bdcc-68f6-45b0-9d67-4d4bd6725888'
    _server_attribute = 'setpoint'
    _server_conversion = float
    def set(self, name):
        return self._set(name)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class StatusFlags(_Property):
    _node_def_id = '556'
    _default_ttl = 10
    def start(self):
        _Property.start(self)
        if self.is_server:
            self.bacnet_property.value = (0,0,0,0)
    pass
class SystemStatus(_Property):
    _node_def_id = '528'
    _default_ttl = 10
    _server_attribute = 'status'
class TimeDelay(_Property):
    pass
class TimeOfActiveTimeReset(_Property):
    pass
class TimeOfStateCountReset(_Property):
    pass
class TimeSynchronizationRecipients(_Property):
    pass
class Units(_Property):
    _node_def_id = '560'
    _server_attribute = 'units'
    _server_conversion = int
    def set(self, v):
        if debug: print 'Set RelinquishDefault to: ', str(v)
        return self._set(v)
    def write(self, value, priority=None):
        self._write_server_attribute(value)
class UpdateInterval(_Property):
    pass
class UtcOffset(_Property):
    pass
class VendorIdentifier(_Property):
    _node_def_id = '530'
    _server_attribute = 'vendor'
    _default_ttl = 7200
    pass
class VendorName(_Property):
    _node_def_id = '529'
    _server_attribute = 'vendor'
    _server_conversion = str
    _default_ttl = 7200
    pass
class VtClassesSupported(_Property):
    _default_ttl = 7200
    pass
class WeeklySchedule(_Property):
    pass
class AttemptedSamples(_Property):
    pass
class AverageValue(_Property):
    pass
class BufferSize(_Property):
    _default_ttl = 7200
    pass
class ClientCovIncrement(_Property):
    pass
class CovResubscriptionInterval(_Property):
    pass
class CurrentNotifyTime(_Property):
    pass
class EventTimeStamps(_Property):
    pass
class LogBuffer(_Property):
    pass
class LogDeviceObjectProperty(_Property):
    pass
class LogEnable(_Property):
    pass
class LogInterval(_Property):
    pass
class MaximumValue(_Property):
    pass
class MinimumValue(_Property):
    pass
class NotificationThreshold(_Property):
    pass
class PreviousNotifyTime(_Property):
    pass
class ProtocolRevision(_Property):
    pass
class RecordsSinceNotification(_Property):
    pass
class RecordCount(_Property):
    pass
class StartTime(_Property):
    pass
class StopTime(_Property):
    pass
class StopWhenFull(_Property):
    pass
class TotalRecordCount(_Property):
    pass
class ValidSamples(_Property):
    pass
class WindowInterval(_Property):
    pass
class WindowSamples(_Property):
    pass
class MaximumValueTimestamp(_Property):
    pass
class minimumValueTimestamp(_Property):
    pass
class VarianceValue(_Property):
    pass
class ActiveCovSubscriptions(_Property):
    pass
class BackupFailureTimeout(_Property):
    pass
class ConfigurationFiles(_Property):
    pass
class DatabaseRevision(_Property):
    _server_attribute = 'revision'
    _default_ttl = 7200
    pass
class DirectReading(_Property):
    pass
class LastRestoreTime(_Property):
    pass
class MaintenanceRequired(_Property):
    pass
class MemberOf(_Property):
    pass
class Mode(_Property):
    pass
class OperationExpected(_Property):
    pass
class Setting(_Property):
    pass
class Silenced(_Property):
    pass
class TrackingValue(_Property):
    pass
class ZoneMembers(_Property):
    pass
class LifeSafetyAlarmValues(_Property):
    pass
class MaxSegmentsAccepted(_Property):
    pass
class ProfileName(_Property):
    pass

###

class Priority(ConfigurableNode):
    def __init__(self):
        self.priority = 16
        self.__node_id__ = '798'
    def configure(self, cd):
        ConfigurableNode.configure(self, cd)
        set_attribute(self, 'priority', self.priority, cd, int)
        set_attribute(self, '__node_id__',self.__node_id__, cd, str)
        return
    def configuration(self):
        cd = ConfigurableNode.configuration(self)
        get_attribute(self, 'priority', cd, str)
        get_attribute(self, '__node_id__', cd, str)
        return cd
    def get(self, skipCache=1):
        if self.parent.parent.has_child('priority_array'):
            pa = self.parent.parent.get_child('priority_array')
            try: 
                return pa.get(skipCache).value[self.priority - 1]
            except:
                pass #try to just get the present value
        return self.parent.get(skipCache)
    def set(self, value, asyncOK=1):
        if value == 'None':
            value = None
        if self.parent.is_client:
            self.parent._set(value, self.priority)
        else:
            self.parent.write(value, self.priority)
        return
class ProperyArray(CompositeNode, AutoDiscoveredNode):
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.__array_discovered = 0
    def _discover_children(self):
        if not self.__array_discovered:
            try:
                a = self.parent.bacnet_property.get_array_length()
                if a > 0:
                    for i in range(a):
                        self._nascent_children[str(i+1)] = PropertyArrayElement(i)
                    self.__array_discovered = 1
            except:
                msglog.exception()
        return self._nascent_children
class PropertyArrayElement(CompositeNode):
    def __init__(self, index):
        self.index = index
        CompositeNode.__init__(self)
    def get_result(self, skip=0, **keywords):
        if keywords.has_key('callback'):
            keywords['callback'].callback(self.get_callback)
        r = self.parent.parent.get_result(skip, **keywords)
        if isinstance(r, Callback):
            return r
        answer = Result()
        answer.timestamp = r.timestamp
        answer.value = r.value.value[self.index]
        return answer
    def get_callback(self, result):
        try:
            answer = Result()
            answer.timestamp = result.timestamp
            if isinstance(result.value,Exception):
                answer.value = result.value
            else:
                answer.value = result.value.value[self.index]
            return answer
        except Exception, e: #any other exception
            return e
        except:
            return Exception(sys.exc_info()[0])
    def get(self, skip=0):
        return self.get_result(skip).value
    def get_batch_manager(self, prop=None):
        return None
    

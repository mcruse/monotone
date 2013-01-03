"""
Copyright (C) 2002 2003 2004 2005 2006 2010 2011 Cisco Systems

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
from mpx.lib.node import CompositeNode
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.bacnet.data import BACnetObjectIdentifier
from mpx.lib.exceptions import ENoSuchName, EInvalidCommand, ENotStarted
from mpx.ion.bacnet import property
from mpx.lib.threading import Lock
from mpx.lib import msglog
from mpx.lib.node.proxy import ProxyAbstractClass
from mpx.lib.bacnet.property import properties, prop_from_id
import types

COMMANDABLE_PV_NODE_ID = '799'
PRIORITY_ARRAY_NODE_ID = '561'

_module_lock = Lock()

DEBUG = 0

class _Object(CompositeNode, AutoDiscoveredNode, ProxyAbstractClass):
    _object_type = None
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType]
    _optional_properties = []
    _node_def_id = None
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        ProxyAbstractClass.__init__(self)
        self.instance = None
        self.object_identifier = None
        self.debug = DEBUG
        self._children_have_been_discovered = 0
        self.running = 0
        self._last_exception = None
        self.__node_id__ = self._node_def_id
        self._batch_managers = {}
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'discovered', self.discovered, cd, int)
        set_attribute(self, 'debug', self.debug, cd, int)
        set_attribute(self, '__node_id__',self.__node_id__, cd, str)
        set_attribute(self, 'instance',self.instance, cd, int)
        self._parent_device = self.parent
        if self.is_proxy():
            ProxyAbstractClass.configure(self, cd)
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'discovered', cd, str)
        get_attribute(self, '__node_id__', cd)
        get_attribute(self, 'debug', cd, str)
        get_attribute(self, 'instance', cd, int)
        if self._parent_device.is_proxy():
            ProxyAbstractClass.configuration(self, cd)
        return cd
    def start(self):
        if self.running == 0:
            self.cache = self.parent.cache
            self.obj_type = self._object_type
            if self.instance is None: #must not have been autodiscovered, get it from xml
               self.instance = self.get_child('object_identifier').instance
            self.object_identifier = BACnetObjectIdentifier(self.obj_type, self.instance)
            if (85 in self._required_properties) or \
               (property.PresentValue in self._required_properties):
                self.get = self._get
            CompositeNode.start(self)
            self.running = 1 #placed here to prevent CompositeNode.start from autodiscovering
            if self.is_proxy():
                ProxyAbstractClass.start(self) #take over the get and set methods

    def is_proxy(self):
        return self._parent_device.is_proxy()
    ##
    # get method normally refers gets to the present value
    # for proxied devices, this is replaced by get to linked device
    def _get(self, skipCache=0):
        if self.is_proxy():
            #we should not be here, we should have been overloaded
            self.set_exception(ENotStarted)
            self._start_exception()  #this may be why
            raise EInvalidCommand('proxy should not use its own get method', self.name)
        return self.get_child('present_value').get(skipCache)
    def find_property(self, property_identifier):
        if self.debug: print 'look for property: ', property_identifier
        for p in self.children_nodes():
            if p.identifier == property_identifier:
                if self.debug: print 'found property ', str(p)
                return p
        return None
    def set_exception(self, exception):
        flag = 0
        if exception: flag = 1
        if self._last_exception != exception:
            self._last_exception = exception
            if flag: print "msglog.log('bacnet server', exception, 'set_exception')", self.name, repr(exception) #msglog.log('bacnet server', exception, 'set_exception')
        sf = self.get_child('status_flags')
        v = list(sf.get()) #get the status flags as a list
        try:
            v[1]=0 #in case we have an exception in the next line
            self.get_child('reliability')._set(flag) #no_sensor
            v[1]=flag #fault
        except ENoSuchName:
            pass #optional property
        self.get_child('event_state')._set(flag) #fault
        v[0]=flag #fault
        sf._set(tuple(v))
    ##
    # Configure new children and turn off caching
    def _configure_nascent_node(self, node, name):
        if self.debug: print '_configure_nascent_node: ', name
        if type(node) == types.IntType:
            node = self.property_from_id(node)
        if type(node) == types.ClassType:
            node = node()
        elif type(node) == types.TypeType:
            node = node()
        try:
            if node._default_ttl < 1:
                node._default_ttl = 1
                if self.debug: print '_default_ttl =', str(node._default_ttl)
            node.configure({'name':name,
                            'parent':self,
                            'discovered':1})
            if self.debug: print 'node configured', node.name
        except:
            msglog.exception()
            if self.debug: print 'failed to configure node: ', node.__class__.__name__, name
        return node
    ##
    # Core of the discovery for this node
    # answer a dictionary of names and nascent (unconfigured or started) nodes
    # since the properities are static we only need to create answer once
    #
    def _discover_children_properties(self):
        if self.discovered and not self._children_have_been_discovered: #empty
            self._children_have_been_discovered = 1
            answer = {}
            for p in self._required_properties: #classes or ints
                if isinstance(p, int): #since table_based
                    #new_prop = self.property_from_id(p)
                    new_prop = p #save off just int and create object later on demand
                    if p == 85: #present value
                        self.get=self._get
                else: 
                    new_prop = p #class only () #nascent node
                    if p == property.PresentValue:
                        self.get=self._get
                answer[property.name_string(new_prop, new_prop)] = new_prop
                pass
            for p in self._optional_properties:
                #todo check to see if property actually exisits on this object and only include those that do
                if isinstance(p, int): #since table_based
                    new_prop = p # int only for now    self.property_from_id(p)
                else: 
                    new_prop = p #class only () #nascent node
                answer[property.name_string(new_prop, new_prop)] = new_prop
                pass
            return answer
        return self._nascent_children
    ##
    # discover only if we are running
    #
    def _discover_children(self):
        if self.running:
            return self._discover_children_properties()
        return {}
    # given an id number, look up the property class
    # this method is extened in subclasses to allow table generated properties
    def property_from_id(self, id):
        return property.from_id(id)
    #for BIN discoverty, return id and child name
    def child_ids_and_names(self, prop_module=property, props=properties):
        answer = {}
        for p in (self._required_properties + self._optional_properties):
            if isinstance(p, int): #since table_based
                answer[p] = prop_module.name_string(prop_module._Property,p)
            else:
                answer[props[p.__name__][0]] = prop_module.name_string(p, None)
        return answer
        
    def get_batch_manager(self, prop=None):
        return self.parent.get_batch_manager(prop)
    def is_array(self):
        return 0
    def get_obj_instance(self): #used by batch manager to group sibling properties
        return (self.obj_type, self.instance)
class BACnetDeviceProperties(_Object):
    _object_type = 8
    _node_def_id = '520'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.SystemStatus, 
                            property.VendorName, 
                            property.VendorIdentifier,
                            property.ModelName, 
                            property.FirmwareRevision, 
                            property.ApplicationSoftwareVersion,
                            property.ProtocolVersion, 
                            property.ProtocolRevision, 
                            property.ProtocolServicesSupported,
                            property.ProtocolObjectTypesSupported,
                            property.ObjectList,
                            property.MaxAPDULengthSupported,
                            property.SegmentationSupported,
                            property.ApduTimeout,
                            property.NumberOfApduRetries,
                            property.DeviceAddressBinding,
                            property.DatabaseRevision]
    _optional_properties = [property.Location,
                            property.Description,
                            property.LocalTime,
                            property.LocalDate,
                            property.UtcOffset,
                            property.DaylightSavingsStatus,
                            property.ApduTimeout]
    ##
    # discover even if we are not running yet
    #
    def _discover_children(self):
        return self._discover_children_properties()
    def get(self, skipCache=0):
        return self.get_child('system_status').get(skipCache)
    def is_proxy(self):
        return 0 #nope, never
class AnalogInput(_Object):
    _object_type = 0
    _node_def_id = '521'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.StatusFlags,
                            property.EventState,
                            property.OutOfService,
                            property.Units]
    def _discover_children_properties(self):
        answer = _Object._discover_children_properties(self)
        if answer.has_key('ObjectType'):
            answer['ObjectType'].__node_id__ = '596'
        return answer
class AnalogOutput(_Object):
    _object_type = 1
    _node_def_id = '563'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.StatusFlags,
                            property.EventState,
                            property.OutOfService,
                            property.Units,
                            property.PriorityArray,
                            property.RelinquishDefault]
    def _discover_children_properties(self):
        answer = _Object._discover_children_properties(self)
        if answer.has_key('PresentValue'):
            answer['PresentValue'].__node_id__ = COMMANDABLE_PV_NODE_ID
        if answer.has_key('ObjectType'):
            answer['ObjectType'].__node_id__ = '597'
        return answer
class AnalogValue(_Object):
    _object_type = 2
    _node_def_id = '1081'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.StatusFlags,
                            property.EventState,
                            property.OutOfService,
                            property.Units,
                            property.PriorityArray,  #@todo make this only if device has it
                            property.RelinquishDefault]
    def _discover_children_properties(self):
        answer = _Object._discover_children_properties(self)
        if answer.has_key('PresentValue'):
            answer['PresentValue'].__node_id__ = COMMANDABLE_PV_NODE_ID
        if answer.has_key('ObjectType'):
            answer['ObjectType'].__node_id__ = '1083'
        return answer
class BinaryInput(_Object):
    _object_type = 3
    _node_def_id = '593'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.StatusFlags,
                            property.EventState,
                            property.OutOfService,
                            property.Polarity]
    _optional_properties = [property.Description,
                            property.InactiveText,
                            property.ActiveText]
    def _discover_children_properties(self):
        answer = _Object._discover_children_properties(self)
        if answer.has_key('ObjectType'):
            answer['ObjectType'].__node_id__ = '598'
        return answer
class BinaryOutput(_Object):
    _object_type = 4
    _node_def_id = '594'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.StatusFlags,
                            property.EventState,
                            property.OutOfService,
                            property.Polarity,
                            property.PriorityArray,
                            property.RelinquishDefault]
    def _discover_children_properties(self):
        answer = _Object._discover_children_properties(self)
        if answer.has_key('PresentValue'):
            answer['PresentValue'].__node_id__ = COMMANDABLE_PV_NODE_ID
        if answer.has_key('ObjectType'):
            answer['ObjectType'].__node_id__ = '599'
        return answer
class BinaryValue(_Object):
    _object_type = 5
    _node_def_id = '1082'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.StatusFlags,
                            property.EventState,
                            property.OutOfService,
                            property.PriorityArray,
                            property.RelinquishDefault]
    def _discover_children_properties(self):
        answer = _Object._discover_children_properties(self)
        if answer.has_key('PresentValue'):
            answer['PresentValue'].__node_id__ = COMMANDABLE_PV_NODE_ID
        if answer.has_key('ObjectType'):
            answer['ObjectType'].__node_id__ = '1084'
        return answer
class Calendar(_Object):
    _object_type = 6
class Command(_Object):
    _object_type = 7
class Device(_Object):  # DO WE NEED THIS??
    _object_type = 8
    def get(self, skipCache=0):
        return str(self.get_child('system_status').get(skipCache))
class File(_Object):
    _object_type = 10
    def get(self, skipCache=0):
        return self.get_child('description').get(skipCache)
class Group(_Object):
    #todo the present value of this is a list, may need some cleaning up
    _object_type = 11
class Loop(_Object):
    _object_type = 12
class MultiStateInput(_Object):
    _object_type = 13
class MultiStateOuput(_Object):
    _object_type = 14
class NotificationClass(_Object):
    _object_type = 15
    def get(self, skipCache=0):
        return str(self.get_child('notification_class').get(skipCache))
class Program(_Object):
    _object_type = 16
    def get(self, skipCache=0):
        return str(self.get_child('program_state').get(skipCache))
class Schedule(_Object):
    _object_type = 17
    _node_def_id = 'TBD' #@FIXME: add correct number when nodedef is created

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
import time, string, types

from mpx.lib.node import CompositeNode
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.bacnet._bacnet import read_property_multiple_g3, read_property_g3
from mpx.lib.bacnet._exceptions import *
from mpx.ion import Result
from mpx.lib.bacnet.network import device_accepts_rpm
from mpx.lib.bacnet import sequence
from mpx.lib.bacnet.data import BACnetObjectIdentifier
from mpx.ion.bacnet import object, property
from mpx.lib.bacnet import network
from mpx.lib.threading import Lock
from mpx.ion.bacnet.batch_manager import BatchManager

_module_lock = Lock()

RIPENESS_THRESHOLD = 0.5
MAX_NODES_PER_REQUEST = 16
MIN_NODES_PER_REQUEST = 4
debug = 0


BACnetDeviceProperties = object.BACnetDeviceProperties
class BACnetDevice(CompositeNode, AutoDiscoveredNode, BatchManager):
    understood_objects = [object.AnalogInput, object.AnalogOutput, object.AnalogValue,
                          object.BinaryInput, object.BinaryOutput, object.BinaryValue]
    _node_def_id = '569'
    def __init__(self):
        self.cache = BACnetPropertyCache()
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.properties=None
        self.obj_type=8
        self.instance=None
        self.running = 0
        self._local_child_list = None
        self._understood_objects = None
        self.debug = debug
        self.device_info=None  #the presence of a device info object means this was a discovered device
        self._children_have_been_discovered = 0
        self._boids = None
        self.__node_id__ = self._node_def_id
        self._comm3_batch_manager = None
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'discovered', self.discovered, cd, int)
        set_attribute(self, '__node_id__','569', cd)
        set_attribute(self, 'instance',self.instance, cd, int)
        set_attribute(self, 'debug', self.debug, cd, int)
        if self.debug > 0:
            set_attribute(self, 'test_resp', 0, cd, int)
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'discovered', cd, str)
        get_attribute(self, '__node_id__',cd)
        get_attribute(self, 'device_info', cd, str)
        get_attribute(self, 'instance', cd, int)
        get_attribute(self, 'debug', cd, int)
        if self.debug > 0:
            get_attribute(self, 'test_resp', cd, int)
        return cd
    def start(self):
        if self.running == 0:
            if debug:
                print 'start called on BacnetDevice:', self.name
                print self._get_children()
            self._create_device_properties() #if required
            CompositeNode.start(self)
            self.running = 1
            if self.instance is None: # autodiscovered this device node, so autodiscover properties child:
                self.properties = self.get_child('BACnet_Device_properties')
                #self.obj_type = self.properties.obj_type
                self.instance = self.properties.instance
            self.cache.device = self.instance
    def get(self, skipCache=0):
        if self.running == 0: #need to start
            self.start()
        return self.properties.get(skipCache)
    def set(self, val): # does nothing except initiate a TestReq sequence, IF parent is MSTP:
        if ((self.debug > 0)  and (self.running > 0) and (hasattr(self.parent, 'do_test_req')) and (self.instance != None)):
            print 'BacnetDevice.set(): self.instance = %s' % str(self.instance)
            self.test_resp = self.parent.do_test_req(self.instance)
    def is_client(self):
        return 1
    def is_server(self):
        return 0
    def is_proxy(self):
        return 0

    ##
    # these functions perform bacnet reads of various properties
    #
    def _get_name_property(self, device, object, instance):
        prop = (object, instance, 77)
        r = read_property_g3(device, prop)
        answer = string.join(r.property_value[0].value.character_string.split())
        return answer.replace('-','_')
    def _get_device_name(self):
        # BEGIN: GetDeviceName hang HACK
        vendor_id = -1
        instance_number = -1
        if hasattr(self.device_info,'vendor_id'):
            vendor_id = self.device_info.vendor_id
        if hasattr(self.device_info,'instance_number'):
            instance_number = self.device_info.instance_number
        #if vendor_id == 2 and instance_number >= 80:
            #return "Tracer Summit Workstation"
        # END: GetDeviceName hang HACK
        device = self.device_info.instance_number
        return str(device)
        #return self._get_name_property(device, 8, device) + (' (%d)' % (device))
    def get_object_list(self):
        return get_object_list(self.instance)
    ##
    # auto discover helper functions
    #
    def _get_discovered_child_name(self, boid, default_name_for=None): 
        #default_name_for is a method to generate a name for the object
        for uo in self.understood_objects:
            if isinstance(uo, int):  #table defined
                if boid.object_type == uo:
                    if default_name_for:
                        return '%s_%02d' % (default_name_for(uo), boid.instance_number)
                    else:
                        raise EInvalidValue('default_name_for', default_name_for, 'BACnet object default_name_for() not supplied')
            else:
                if boid.object_type == uo._object_type: #we want to make an instance of the object
                    return '%s_%02d' % (uo.__name__, boid.instance_number)
                #try:
                    #name = self._get_name_property(self.instance, boid.object_type, boid.instance_number)
                    #name = string.join(name.split())
                #except:
                    #name = 'Unknown'
                #name = '%s (%s %d)' % (name, uo.__name__, boid.instance_number)
                #return name
        raise ENotImplemented, (boid.object_type, boid.instance_number)
    def _create_nascent_child_for(self, boid, factory=None):
        for uo in self.understood_objects:
            if isinstance(uo, int):  #table defined
                if boid.object_type == uo:
                    if factory:
                        new_obj = factory(uo)
                        new_obj.instance = boid.instance_number
                        return new_obj
                    else:
                        raise EInvalidValue('factory', factory, 'BACnet object factory() not supplied')
            else: #class defined
                if boid.object_type == uo._object_type: #we want to make an instance of the object
                    if self.debug: print 'boid obj_type found: ', str(boid.object_type)
                    new_obj = uo()
                    new_obj.instance = boid.instance_number
                    return new_obj
        if self.debug: print '_create_nascent_child_for did not find an understood object for: ', str(boid)
        raise ENotImplemented, str(boid)
    ##
    # need to create device properties group up front instead of along with other objects
    #
    def _create_device_properties(self):
        if self.discovered:
            if self.debug: print 'create discovered device properties'
            dp = BACnetDeviceProperties()
            dp.instance = self.device_info.instance_number
            dp.configure({'name':'BACnet_Device_properties',
                          'parent':self,
                          'discovered':1})
            #will get started by the method that called this one
    def _discover_children_boids(self):
        try:
            pv = get_object_list(self.device_info.instance_number)
            if self.debug: print str(pv)
            boids = []
            for a_tag in pv:
                boids.append(a_tag.value) #add in the BACnetObjectIdentifiers
        except:
            if self.debug: print '_discover_children_boids exception'
            boids = []
        if self.debug: print 'boids found: ', str(boids)
        self._boids = boids
        return boids  #all boids, regardless of type.
    ##
    # heart of discover process
    #
    def _discover_children(self):
        if self.running:
            try:
                if self.discovered and not self._children_have_been_discovered: #time to rediscover
                    answer = {} #start fresh
                    if self.debug: print 'Discover objects on device'
                    self.last_discovery = time.time()
                    boids = self._discover_children_boids()
                    if self.debug: print 'Got the boids'
                    existing_objects = self._existing_child_boids()
                    if self.debug: print 'existing objects', str(existing_objects)
                    if debug: 
                        print 'found objects: ', boids
                        print 'existing objects: ', existing_objects
                    for o in boids:
                        if o not in existing_objects:
                            try:
                                if self.debug: print 'create child for: ', str(o.object_type), str(o.instance_number)
                                new_object = self._create_nascent_child_for(o) #create new object node from this device
                                new_object.instance = o.instance_number
                                if self.debug: print 'created nascent child, get name'
                                name = self._get_discovered_child_name(o)
                                if self.debug: print 'name: ', name
                                self._nascent_children[name] = new_object
                            except:
                                if self.debug:
                                    print 'BOID not implemented: ', str(o.object_type), str(o.instance_number)
                                continue
                    #self._children_have_been_discovered = 1
                    return self._nascent_children
            except:
                if debug: print 'error during bacnet object discover'
        return self._nascent_children

    ##
    # Find an object on this bacnet device.  Add to node tree if found
    #
    # @param name, keyword dictionary
    # @return the new node if found
    # @throws ENoSuchName is node is not found
    
    # answer a list of current children's instance numbers
    def _existing_child_boids(self):
        answer = []
        for n in self._get_children().values():
            if hasattr(n, 'object_identifier'):
                answer.append(n.object_identifier)
        return answer

    def get_batch_manager(self, prop=None):
        if prop:
            c3 = prop._comm3segment()
            if c3:
                if self._comm3_batch_manager is None:
                    bm = BatchManager() #make seperate batch manager for all comm3 devices
                    bm.name = self.name + '_comm3_page'
                    bm.instance = self.instance #bacnet device instance number
                    self._comm3_batch_manager = bm
                return self._comm3_batch_manager
        return self #default batch manager is self
    def is_array(self):
        return 0
def child_instance_comparison(a, b):
    if a.instance_number < b.instance_number:
        return -1
    if a.instance_number > b.instance_number:
        return 1
    return 0

def ripeness_comparison(a, b):
    if a[0] < b[0]:
        return 1
    if a[0] > b[0]:
        return -1
    return 0

class CacheEntry(Result):

    def __init__(self):
        Result.__init__(self)
        self.node = None

class BACnetPropertyCache:

    def __init__(self, cache=None):
        if cache is None:
            cache = {}
        self.cache = cache
        self.groups = {}
        self.updated_cache = 0
        self.retrieved_from_cache = 0
        self.device = None

    def has_key(self, key):
        return self.cache.has_key(key)

    def result(self, key):
        return self.cache[key]

    def find_age_group_for(self, key):
        #if debug: print 'find age group'
        # is there a group for this property, if not create one and add the property to it
        if not self.groups.has_key(key.ttl):
            self.groups[key.ttl] = {key:key.property_tuple}
        # for the appropriate age group, get all the properties in the group
        group_list = self.groups[key.ttl]
        if not group_list.has_key(key): #add the new guy if he's never been there before
            group_list[key] = key.property_tuple
        return group_list #answer the age group for the property

    def predicted_next_nodes_to_expire(self, prop):
        if debug: print 'predict which nodes will expire next'
        self.find_age_group_for(prop) #put the prop in a group in case it wasn't there
        list_of_ripe_nodes = []
        keys = self.groups.keys()
        keys.sort()
        if debug: print 'keys: ', keys
        for x in keys: #search through each group
            if x > 60:
                break
            if debug: print 'search group: ', x
            for y in self.groups[x].keys(): #examine each node in the group
                ripe = y.ripeness()
                if debug: print 'r',
                if ripe > 0.2:
                    list_of_ripe_nodes.append((ripe, y, self.groups[x][y],))
        if debug: 
            print 'done'
            print 'sort ripe list of size: ', len(list_of_ripe_nodes)
        list_of_ripe_nodes.sort(ripeness_comparison)
        max_point_counter = 0
        answer = {}
        #if debug: print 'pick the most deserving from: ', list_of_ripe_nodes
        for x in list_of_ripe_nodes:
            #if debug:
                #print 'Predicted node: ', x[1]
                #print '      Ripeness: ', x[0]
            #put together the list for the read prop mult
            answer[x[1]] = x[2]
            #include from MIN (8) to MAX (16) points depending on how many are more than half ripe
            max_point_counter = max_point_counter + 1
            if max_point_counter > MIN_NODES_PER_REQUEST:
                if x[0] < RIPENESS_THRESHOLD:
                    break
            if max_point_counter > MAX_NODES_PER_REQUEST:
                break
        answer[prop] = prop.property_tuple  #ahh, make sure the requested property gets included
        #if debug: print 'answer: ', answer
        return answer

    def update_cache(self, prop):
        if debug: print 'update cache: ' #, prop, prop.ttl
        #age_group = self.find_age_group_for(prop)
        rpm = device_accepts_rpm(self.device)
        if debug: print 'does device RPM? :', str(rpm)
        if rpm:
            if debug: print 'device accepts rpm'
            age_group = self.predicted_next_nodes_to_expire(prop)
            keys = age_group.keys()
            properties = []
            for x in keys:  #go through this to guarentee having the same order in the results as the properties
                properties.append(age_group[x])
                if debug: print '    rpm: ', x

            if debug: print 'RPM for :', self.device, properties
            r = read_property_multiple_g3(self.device, properties)
            if debug: print ' RPM result: ', r
    
            now = time.time()
            for x in keys:
                result = Result()
                result.timestamp = now
                result.cached = 1
                v = r.pop(0)
                if debug: print ' RPM decode: ', v #, x
                try:
                    pv = v.list_of_results[0].property_value
                    x.decode(pv)
                    result.value = x._value
                except sequence.ETagMissing, e:
                    result.value = sequence.ETagMissing('ETagMissing():\n ' + \
                                                        str(e))
                if debug: print '         add to cache: ', result.value
                self.cache[x] = result
                x.last_result = result
        elif rpm is not None: #since it is not able to handle RPM
            if debug: print 'device does not accept rpm'
            self.get_rp(prop)

    def get(self, prop, skipCache, timeout=3.0): #get from the cache for the property
        if debug: print 'get from cache: %s %s %s' % (str(prop.property_tuple), str(skipCache), str(timeout))
        if skipCache:
            if debug: print 'skipping cache'
            return self.get_rp(prop)
        if prop.cache is None:
            prop.cache = self
        if self.has_key(prop):
            now = time.time()
            if (now - prop.ttl) < self.cache[prop].timestamp:
                self.retrieved_from_cache = self.retrieved_from_cache + 1
                if debug: 
                    print 'CACHE hit rate: ', 100 * self.retrieved_from_cache / self.updated_cache
                    print 'retreive from cache. '#, prop
                return self.cache[prop]
        self.updated_cache = self.updated_cache + 1
        #if debug: print 'CACHE hit rate: ', 100 * self.retrieved_from_cache / self.updated_cache
        #self.update_cache(prop)
        #if debug: print 'CACH has been updated, maybe'
        #if self.cache.has_key(prop):
            #return self.cache[prop]
        #raise EDeviceNotFound(self.device) #'property missing from cache!'
        return self.get_rp(prop, timeout)

    def get_rp(self, prop, timeout=3.0):
        if debug: print 'reading a property'
        now = time.time()
        result = Result()
        result.timestamp = now
        result.cached = 1
        try:
            if debug: print self.device, prop.property_tuple
            r = read_property_g3(self.device, prop.property_tuple, timeout)
            v = r.property_value
            self.v = v
            prop.decode(v)
        except BACnetError, e:
            prop._value = e
            result.timestamp = now - prop.ttl
        result.value = prop._value
        self.cache[prop] = result
        return result

def get_object_list(device):
        answer = []
        if debug: print 'ion.device.get_object_list from device'
        prop = (8, device, 76)
        try:
            r = read_property_g3(device, prop)
            answer = r.property_value #a list of tags
        except:
            if debug: print 'reading entire list did not work, try one element at a time'
            try:
                answer = []
                #get length of list
                len = read_property_g3(device, prop+(0,))
                len = len.property_value[0].value
                if len > 1:
                    for i in range(1, len):
                        obj_tag = read_property_g3(device, prop+(i,)).property_value[0]
                        answer.append(obj_tag)
            except:
                if self.debug: print 'unable to read individual list elements'
                answer = []
        return answer

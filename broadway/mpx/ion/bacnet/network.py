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
import time, string


from mpx.lib import msglog

from mpx.lib.bacnet import network
from mpx.lib.bacnet._bacnet import read_property_g3
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.exceptions import *
from mpx.lib.node import CompositeNode, as_node_url
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.threading import Lock, ImmortalThread

DEBUG = 1



default_discover_mode = 'new'  #should be never
default_discover_interval = 60   # should be 60

##
# Bootstrap Code For Adding Vendor-Specific Objects, Properties, and Datatypes:
# Define class to hold vendor_mods ("vendor module references") table entries:
class SuppVendorMods:
    def __init__(self, ion_prop, ion_obj, ion_dev, lib_prop, lib_obj, lib_dev = None):
        self.ion_prop = ion_prop
        self.ion_obj = ion_obj
        self.ion_dev = ion_dev
        self.lib_prop = lib_prop
        self.lib_obj = lib_obj
        self.lib_dev = lib_dev

# Once you have created vendor subdirs under lib.bacnet and ion.bacnet (both named
# '<vendor>'), add that same name to the following table, indexed by vendor_id:
vendors = { \
           2:'trane' \
          }
vendor_mods = {} # define empty vendor_mods table
for i in vendors.keys(): # import all vendor modules, and populate vendor_mods table:    
    n = vendors[i]
    ion_prop_str = n + '_iprop'
    ion_obj_str = n + '_iobj'
    ion_dev_str = n + '_idev'
    imp_ion_str = 'from mpx.ion.bacnet.' + n + ' import %s as %s'
    try:         
        exec imp_ion_str % ('property', ion_prop_str)
    except Exception, e:
        if DEBUG: 
            print '1: may be safe to ignore cannot import name exception: ', e
            msglog.exception()
        ion_prop_str = 'None'
    try:         
        exec imp_ion_str % ('object', ion_obj_str)
    except Exception, e:         
        if DEBUG: 
            print '2: may be safe to ignore cannot import name exception: ', e
            msglog.exception()
        ion_obj_str = 'None'
    try:         
        exec imp_ion_str % ('device', ion_dev_str)
    except Exception, e:         
        if DEBUG: 
            print '3: may be safe to ignore cannot import name exception: ', e
            msglog.exception()
        ion_dev_str = 'None'
    lib_prop_str = n + '_lprop'
    lib_obj_str = n + '_lobj'
    lib_dev_str = n + '_ldev'
    imp_lib_str = 'from mpx.lib.bacnet.' + n + ' import %s as %s'
    try:         
        exec imp_lib_str % ('property', lib_prop_str)
    except Exception, e:         
        if DEBUG: 
            print '4: may be safe to ignore cannot import name exception: ', e
            msglog.exception()
        lib_prop_str = 'None'
    try:         
        exec imp_lib_str % ('object', lib_obj_str)
    except Exception, e:         
        if DEBUG: 
            print '5: may be safe to ignore cannot import name exception: ', e
            msglog.exception()
        lib_obj_str = 'None'
    try:
        exec imp_lib_str % ('device', lib_dev_str)
    except Exception, e:         
        if DEBUG > 1: 
            print '6: may be safe to ignore cannot import name exception: ', e
            msglog.exception()
        lib_dev_str = 'None'
    vendor_mods[i] = SuppVendorMods(eval(ion_prop_str), eval(ion_obj_str), eval(ion_dev_str), \
                                    eval(lib_prop_str), eval(lib_obj_str), eval(lib_dev_str))

##
# Inherited by BACnetIP and BACnet Ethernet nodes
class _Network(CompositeNode, AutoDiscoveredNode):
    def __init__(self):
        AutoDiscoveredNode.__init__(self)
        self._who_is_thread = None
        self.found_devices = {}  #all devices on network
        self._lock = Lock()
        self.running = 0
        self._device_table_size = 0
        self.bcu_list = []
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'network', REQUIRED, config, int)
        set_attribute(self, 'discover', default_discover_mode, config, str)
        set_attribute(self, 'discover_interval', default_discover_interval, config, int)
        set_attribute(self, 'debug', DEBUG, config, int)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'network', config, str)
        get_attribute(self, 'discover', config, str)
        get_attribute(self, 'discover_interval', config, str)
        get_attribute(self, 'debug', config, int)
        get_attribute(self, 'bcu_list', config, str)
        if self.debug:
            get_attribute(self, 'found_devices', config, str)
        return config
    def start(self):
        CompositeNode.start(self)
        self.bcu_list = []
        self.running = 1
        if self._who_is_thread is None: #kick off who_is thread
            network._who_are_devices()
            self._who_is_thread = _WhoIsThread(self)
            self._who_is_thread.start()
    def stop(self):
        self.running = 0
        if self._who_is_thread:
            self._who_is_thread.should_die()
        CompositeNode.stop(self)
        
    ##
    # Discover any bacnet devices that are not part of the node tree
    #
    # @param None.
    # @return A dictionary of potential devices, keyed by name
    # @throws None
    #
    def _discover_children(self): #find any new devices
        ## disble discovery
        self.discover = 'never'
        ## disble discovery
        answer = {}
        if self.discover == 'never' or not self.running:
            return answer
        try:
            result = {} #start fresh
            if self.debug: print 'Discover network children'
            self.found_devices = dict(network._device_table)
            dts = len(self.found_devices)
            #if dts == self._device_table_size: #nothing new to discover
                #return answer #short circuit the search
            self._device_table_size = dts
            existing_devices = self._child_device_instance_numbers()
            existing_networks = self._existing_network_numbers()
            if self.debug: 
                print 'found devices: ', self.found_devices
                print 'existing devices: ', existing_devices
                print 'existing networks: ', existing_networks
            for d in self.found_devices.values():  #I would iterate by keys (device instance) but we may change to a different key
                if d.network == self.network: #new device on our network
                    if d.instance_number not in existing_devices:
                        if self.debug: 'new device found: ', str(d)
                        if (vendor_mods.has_key(d.vendor_id)): #vendor modules
                            dev_mod = vendor_mods[d.vendor_id].ion_dev
                            bn_dev = getattr(dev_mod, 'BACnetDevice')
                            new_device = bn_dev()
                        else:
                            from mpx.ion.bacnet import device
                            new_device = device.BACnetDevice() #create new device node from this device
                        new_device.device_info = d
                        try: # to get name of device
                            device_name = new_device._get_device_name()
                        except:
                            device_name = 'Unknown device (%d)' % d.instance_number
                        if d.vendor_id == 2: #trane
                            if self.bcu_list:
                                if d.instance_number not in self.bcu_list:
                                    continue #do not insert black listed work station
                            else: #we do not yet have the list
                                #try and read the list
                                try:
                                    #read site object work station list
                                    bculist = read_property_g3(d.instance_number, (132,1,1126)).property_value #site layout, ws list
                                    for bcu in bculist: #loop through tags
                                        self.bcu_list.append(bcu.value.instance_number)
                                    #must be bcu so add it
                                except:
                                    #only add devices we can talk with
                                    continue #better luck next time
                            #if device_name != 'Tracer Summit Workstation': #filter out the annoying workstations....
                        result[device_name] = new_device
                        continue #get next found device
                if d.network not in existing_networks:
                    if self.debug: print 'new network found: ', str(d.network)
                    #create new network node to hold this device
                    new_network = Network()
                    if self.debug: print 'nw 1'
                    new_network._network_number = d.network
                    if self.debug: print 'nw 2'
                    network_name = 'Network (%d)' % d.network
                    if self.debug: print 'nw 3'
                    result[network_name] = new_network
                    if self.debug: print 'nw 4'
                    continue
            answer = result
        except:
            msglog.exception()
            if self.debug: print 'error during bacnet network discover'
        return answer
    ##
    # Configures and starts a node
    #
    # @param node (a instatiated but unconfigured node.
    # @return nothing
    # @throws nothing (to prevent one bad node from blocking other's from starting)
    #
    def _configure_nascent_node(self, new_node, node_name):
        try:
            if new_node.__class__ == Network: #since new network discovered
                new_node.configure({'name':node_name,
                                    'parent': self,
                                    'network':new_node._network_number,
                                    'discover':self.discover,
                                    'discover_interval':self.discover_interval,
                                    'debug':self.debug})
                if self.debug:
                    print 'configure and start network:', node_name
            #if new_node.__class__ == device.BACnetDevice: #since a new device, add it to known devices
            else:
                new_node.configure({'name':node_name,
                                    'parent':self,
                                    'discovered':1,
                                    'debug':self.debug})
                if self.debug:
                    print 'configure and start device:', node_name
            #else:
            #    print 'attempt to configure and start an unknown node', str(new_node.__class__.__name__)
            #    return #don't start node that was not configured
        except:
            msglog.exception()
            if self.debug: print 'failed to configure bacnet device or network: ', node_name, new_node.__class__.__name__
        return new_node

    # answer a list of current children's instance numbers
    #@todo:  keep copy of last result and invalidate only if new device discovered
    def _child_device_instance_numbers(self):
        answer = []
        for n in self._get_children().values(): #_get_children allready discovered
            if hasattr(n, 'instance'): #filter out network children
                answer.append(n.instance)
        return answer
    def _existing_network_numbers(self):
        answer = [self.network,]
        for n in self._get_children().values():
            if hasattr(n, 'network'): #filter out device children
                answer.append(n.network)
        return answer
    def _all_child_networks(self):
        answer = []
        for n in self.children_nodes(): #trigger discovery
            if hasattr(n, 'network'): #filter out device children
                answer.append(n)
        return answer
    def _all_child_devices(self):
        answer = []
        for n in self.children_nodes():
            if hasattr(n, 'instance'): #filter out network children
                answer.append(n)
        return answer
    def _all_descendant_devices(self):
        answer = self._all_child_devices()
        for n in self._all_child_networks():
            answer.extend(n._all_descendant_devices())
        return answer
    # in node browser use: ?action=invoke&method=get_device_table
    def get_device_table(self):
        answer = ''
        for d in network._device_table.values():
            answer += str(d)+'\n'
        return answer
##
# child of a bacnet network to hold devices on networks other than the one
# the mediator is directly connected to.
class Network(_Network):
    def __init__(self):
        _Network.__init__(self)
        self._network_number = None
    def configure(self, config):
        _Network.configure(self, config)
        set_attribute(self, 'network', REQUIRED, config, int)
        
    def configuration(self):
        config = _Network.configuration(self)
        get_attribute(self, 'network', config, str)
        return config
    def start(self):
        self.interface = self.parent.interface
        _Network.start(self)
        return
    def _discover_children(self): #find any new devices
        ## disble discovery
        self.discover = 'never'
        ## disble discovery
        if self.discover == 'never' or not self.running:
            return {}
        try:
            answer = {} #start fresh
            if self.debug: print 'Discover network children'
            self.found_devices = dict(network._device_table)
            existing_devices = self._child_device_instance_numbers()
            if self.debug: 
                print 'found devices: ', self.found_devices
                print 'existing devices: ', existing_devices
            for d in self.found_devices.values():
                if d.network == self.network: #new device on our network
                    if d.instance_number not in existing_devices:
                        if self.debug: 'new device found: ', str(d)
                        if (vendor_mods.has_key(d.vendor_id)):
                            dev_mod = vendor_mods[d.vendor_id].ion_dev
                            bn_dev = getattr(dev_mod, 'BACnetDevice')
                            new_device = bn_dev()
                        else:
                            from mpx.ion.bacnet import device
                            new_device = device.BACnetDevice() #create new device node from this device
                        new_device.device_info = d
                        try: # to get name of device
                            device_name = new_device._get_device_name()
                        except:
                            device_name = 'Unknown device'
                        device_name = device_name + ' (%d)' % d.instance_number
                        answer[device_name] = new_device
        except:
            msglog.exception()
            if self.debug: print 'error during bacnet network discover'
        return answer

#
# This thread occasionally requests a who_is to find new devices.
#
class _WhoIsThread(ImmortalThread):

    def __init__(self, node):
        node_url = as_node_url(node)
        ImmortalThread.__init__(self, name='_WhoIsThread(%r)' % node_url)
        self.node = node
        self.debug = node.debug
        self.discover_interval = node.discover_interval
        if self.debug:
            print '%s.__init__()' % self.getName()
    def reincarnate(self):
        msglog.log('broadway',msglog.types.INFO,
                    '%s restarting' % self.getName())
        time.sleep(10)
        return
    def run(self):
        if self.node.running:
            if self.debug:
                print '%s.run()' % self.getName()
            self.listen()
        else:
            self.should_die()
    def listen(self): #called from immortal thread
        try:
            while self._continue_running:
                if self.debug:
                    print '%s.listen():  Broadcasting WHOIS' % self.getName()
                self.node._device_table_size = 0 #once a minute, force a full discovery
                network._who_are_devices()
                time.sleep(self.discover_interval)
        finally:
            if self.debug:
                print '%s.finally' % self.getName()

def factory():
    return Network()
#"""
#import telnetlib
#t=telnetlib.Telnet('localhost',6005)
#t.interact()

#t.close()



#import time
#from mpx.lib.node import as_node
#def test():
    #b=as_node('interfaces/eth0/BACnetIP')
    #devices = b.children_nodes()
    #print b.children_names()
    #t1 = time.time()
    #for c in b.children_nodes():
        #if not hasattr(c,'get'): #device
            #devices.extend(c.children_nodes())
            #print c.children_names()
    #t2 = time.time()
    #for d in devices:
        #print 'Device = ', d.name
        #for o in d.children_nodes():
            #print '  Object = ', o.name
            #for p in o.children_nodes():
                #print '     ', p.name
                #props.append(p)
    #t3 = time.time()
    #for p in props:
        #print p.name, str(p.get())
    #t4 = time.time()
    #print str(t2-t1), str(t3-t2), str(t4-t3)
#"""

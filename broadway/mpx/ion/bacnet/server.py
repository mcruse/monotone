"""
Copyright (C) 2002 2003 2004 2010 2011 Cisco Systems

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

from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.bacnet._exceptions import *
from mpx.lib.bacnet.server import create_server_device, destroy_server_device

debug = 0

class _TimeKeeper:
    factor = 50
    def __init__(self):
        self.min = 0
        self.max = 0
        self.avg = 0
        self.count = 0
        self._start = None
    def begin(self, start=None):
        if start is None:
            start = time.time()
        self._start = start
    def end(self, stop=None):
        self.count += 1
        if stop is None:
            stop = time.time()
        if self._start:
            duration = stop - self._start
            if self.min == 0:
                self.min = duration
            else:
                self.min = min(self.min, duration)
            if self.max == 0:
                self.max = duration
            else:
                self.max = max(self.max, duration)
            if self.avg == 0:
                self.avg = duration
            else:
                self.avg = ((self.avg * self.factor) + duration) / (self.factor + 1)
    def __str__(self):
        return "min: %f max: %f avg: %f count: %d" % (self.min, self.max, self.avg, self.count)
        
class BACnetDevice(CompositeNode):

    def __init__(self):
        CompositeNode.__init__(self)
        self.cache = None
        self.discovered = 0 #proxys are never discovered?
        self.device_info = None #to keep property start happy, there is no device_info
        self.running = 0
        self.lib_device = None  #added to hold reference to lib server device object
        self.time_rp = _TimeKeeper()
        self.time_rpm = _TimeKeeper()
        self.time_wp = _TimeKeeper()
        self.time_wpm = _TimeKeeper()
        self._obj_lookup_cache = {}

    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'proxy', 0, cd, int)
        set_attribute(self, '__node_id__','9d460040-6100-4c22-8830-092b231f1a64', cd)

    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'proxy', cd, str)
        get_attribute(self, '__node_id__',cd)
        get_attribute(self, 'device_info', cd, str)
        get_attribute(self, 'time_rp', cd, str)
        get_attribute(self, 'time_rpm', cd, str)
        get_attribute(self, 'time_wp', cd, str)
        get_attribute(self, 'time_wpm', cd, str)

        return cd

    def start(self):
        if self.running == 0:
            if debug:
                print 'start called on server.BacnetDevice'
                print self.children_names()
            CompositeNode.start(self)
            self.running = 1
            self.properties = self.get_child('BACnet_Device_properties')
            self.obj_type = self.properties.obj_type
            self.instance = self.properties.instance
            self.lib_device = create_server_device(self, self.parent.network)
            self._obj_lookup_cache = {}
            #when we emulate other vendors, set vendor id at this point

    def stop(self):
        if self.running:
            destroy_server_device(self.lib_device) #make it go away!
            self.lib_device = None
            CompositeNode.stop(self)
            self.running = 0
            
    def get(self, skipCache=0):
        return self.properties.get(skipCache)

    def is_client(self):
        return 0

    def is_server(self):
        return 1

    def is_proxy(self):
        if not hasattr(self, 'proxy'):
            self.proxy = 0
        return self.proxy > 0

    def find_bacnet_object(self, object_identifier):
        if debug: print 'look for object: ', object_identifier.id
        id = object_identifier.id
        if self._obj_lookup_cache.has_key(id):
            return self._obj_lookup_cache[id]
        for o in self.children_nodes():
            if o.object_identifier.id == id:
                if debug: print 'found object ', str(o)
                self._obj_lookup_cache[id] = o
                return o
        if debug: print 'object not found'
        return None

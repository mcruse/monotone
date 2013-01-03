"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import time, types
from mpx.lib.node import CompositeNode, ConfigurableNode, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.exceptions import *
from mpx.lib import EnumeratedDictionary
from mpx.lib.datetime import *
from mpx.lib import msglog
from mpx.componentry import implements
from interfaces import IScheduleHolder
from interfaces import ISchedule
from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.event import EventConsumerMixin
from mpx.service.schedule.scheduler import SchedulesSummary, ScheduleSummary

debug = 0

class Schedules(CompositeNode, AutoDiscoveredNode):
    _node_id='87e1e293-6a55-4541-ba19-12022790f863'
    implements(IScheduleHolder)
    
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self.running = 0
        self.discover_mode = 'never'
        self._been_discovered = 0
        self.source = 'broadway' #or 'bacnet'
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'source',self.source, cd, str)
        set_attribute(self, 'device_link', None, cd, str) #url of Devices node
        set_attribute(self, 'discover_mode', self.discover_mode, cd, str)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'bacnet_datatype', 'real', cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'source', config)
        get_attribute(self, 'device_link', config)
        get_attribute(self, 'discover_mode', config)
        get_attribute(self, 'bacnet_datatype', config)
        return config
    def start(self):
        CompositeNode.start(self)
        self.running = 1
    def stop(self):
        self.running = 0
        CompositeNode.stop(self)
    def _discover_children(self, force=0,**options):
        #search through bacnet devices for Schedule Objects
        #discover_mode: 0==none,  1==use numbers, 2==use name properties,  3==use both
        if self.discover_mode != 'never' and self.running == 1: # and self._been_discovered == 0:
            try:
                schedule_group = as_node(self.device_link).get_child('17')
                #since bacnet object groups do not agressively discover
                #children instances, this will force full discovery
                schedule_group._discover_children(1) #forced discovery
                schedules = schedule_group.children_nodes() #auto_discover=(self.discover_mode != 'never')) #schedules
                # add Calendar Objects as Schedules
                calendar_group = as_node(self.device_link).get_child('6')
                #since bacnet object groups do not agressively discover
                #children instances, this will force full discovery
                calendar_group._discover_children(1) #forced discovery
                schedules.extend(calendar_group.children_nodes()) #auto_discover=(self.discover_mode != 'never')) #schedules
                # filter out any existing nodes
                existing  = [as_node(c.link) for c in self.children_nodes(auto_discover=0)]
                existing += [as_node(c.link) for c in self._nascent_children.values()]
                schedules = filter(lambda d: d not in existing, schedules) #filter out any existing nodes
                for s in schedules:
                    name = s.name #default name will be the schedule ID
                    if self.discover_mode[:4] == 'name': #then we want name of schedule
                        try:
                            name = str(s.get_child('77').get())
                            if self.discover_mode == 'name_and_numeric': #use both ID and name
                                name += ' (' + s.name + ')'
                        except:
                            pass #if name is not available, use ID only
                    sr = Scheduler()
                    sr.link = s.as_node_url() #url of bacnet schedule object node
                    sr.source = self.source
                    self._nascent_children['RZSched_' + name]=sr
                #self._been_discovered = 1 #disabled to allow new objects to be discovered
            except ENoSuchName, e:
                if debug:
                    msglog.exception()
                pass
            except:
                msglog.exception()
        return self._nascent_children
    def get_summary(self):
        siblings = self.children_nodes()
        daily = []
        for s in siblings:
            if s.__class__ == Scheduler:
                x = s.get_summary()
                x.insert(0, s.name)
                daily.append(x)
        return daily
    def set_summary(self, value, save=1):
        if isinstance(value, basestring):
            value = eval(value)
        #Daily
        map = {}
        for n in value:
            map[n[0]] = n
        if debug: print map
        #trim away unused nodes
        siblings = self.children_nodes()
        for s in siblings:
            if s.__class__ == Scheduler:
                if s.name not in map:
                    if debug: print 'prune: ', s.name
                    s.prune()
        for n in map.keys():
            try:  #reuse any existing node with the same name
                de = self.get_child(n)
                if debug: print 'found existing entry', de.name
            except ENoSuchName:  #create one if needed
                de = Scheduler()
                de.configure({'name':n, 'parent':self})
                de.start()
            de.set_summary(map[n][1:], 0)
        if save:
            self.save_schedule()
            
    def has_summary_child(self, create_if_absent=None):
        try:
            self.get_child('summary', auto_discover=0)
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = SchedulesSummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0
    def save_schedule(self):
        pass
    def childtype(self):
        return None #adding and removing schedules not allowed for bacnet schedules, they are reflections of the devices on the network
    def children_nodes(self,**options):
        nodes = CompositeNode.children_nodes(self, **options)
        nodes.sort(lambda x,y: cmp(x.name, y.name))
        return nodes
class Scheduler(CompositeNode,EventConsumerMixin):
    _node_id='8ac6878d-8236-4658-8343-aae24816f963' 
    implements(ISchedule)
    
    def __init__(self):
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self, self._cov_event_handler)
        self._smid = None
        self._last_value = None
        self.link = None #url of bacnet schedule object
        self.source = 'broadway' #or 'bacnet'
        self._bacnet_datatype = 'auto'
        pass
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'source',self.parent.source, cd, str)
        #set_attribute(self, 'default',None, cd, str)
        set_attribute(self, 'link', self.link, cd, str)
        set_attribute(self, 'bacnet_datatype', 'auto', cd, str)
        set_attribute(self, 'force', False, cd, bool)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'source', config)
        #get_attribute(self, 'default', config)
        get_attribute(self, 'link', config)
        get_attribute(self, 'bacnet_datatype', config)
        get_attribute(self, 'force', config)
        return config
    def start(self):
        self._bacnet_datatype = self.bacnet_datatype
        if self.bacnet_datatype == 'auto': # check parent's datatype if we are not specific
            self._bacnet_datatype = self.parent.bacnet_datatype
        self.has_summary_child(self.parent.has_summary_child())
        CompositeNode.start(self)
    def stop(self):
        CompositeNode.stop(self)
        if self._smid:
            SM.destroy(self._smid)
            self._smid = None
    def get(self, skipcache=0):
        if self.link:
            if not self._smid:
                try:
                    value = self.as_node(self.link).get() #get it once to force autodiscovery
                    if hasattr(value, 'as_magnitude'):
                        value = value.as_magnitude()
                    self._last_value = value
                    self._smid = SM.create_delivered(self, {1:self.link}) #ID of subscription used for all descendent mpx_get templates
                except:
                    msglog.exception()
        return self._last_value
    def _cov_event_handler(self, cve):
        try:
            value = cve.results()[1]['value']
            if hasattr(value, 'as_magnitude'):
                value = value.as_magnitude()
            self._last_value = value
        except:
            msglog.exception()
            print 'bacnet_scheduler _cov_event_handler ', repr(cve)
            self._last_cve = cve

    def set(self, value):
        self.default = value  #set the name of the default element
    def get_summary(self):
        try:
            return self.as_node(self.link)._get_schedule_summary()
        except:
            msglog.exception()
        return [[],[],[],None]
    def set_summary(self, value, save=1):
        print 'set bacnet schedule: ', str(value)
        if isinstance(value, basestring):
            value = eval(value)
        if len(value) != 4:
            raise EInvalidValue()
        try:
            self.as_node(self.link)._set_schedule_summary(value, self._bacnet_datatype, self.force)
        except:
            msglog.exception()
    def save_schedule(self):
        self.parent.save_schedule()
    def has_summary_child(self, create_if_absent=None):
        try:
            self.get_child('summary', auto_discover=0)
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = ScheduleSummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0


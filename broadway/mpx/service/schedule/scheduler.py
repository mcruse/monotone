"""
Copyright (C) 2004 2006 2007 2008 2009 2010 2011 2012 Cisco Systems

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
from threading import RLock
from mpx.lib.node import CompositeNode, ConfigurableNode, as_node, as_internal_node, as_deferred_node, as_node_url
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.exceptions import *
from mpx.lib.thread_pool import ThreadPool
from mpx.lib.threading import Lock
from mpx.lib.event import EventProducerMixin
from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import ScheduleChangedEvent
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import ScheduleCreatedEvent
from mpx.lib.event import ScheduleRemovedEvent
from mpx.lib.event import ScheduleMovedEvent
from mpx.lib.uuid import UUID
from mpx.lib.scheduler import scheduler as sys_scheduler
from mpx.lib.rna import NodeFacade
#@fixme - _ChangeValueEvent, this should SM be internal only.
from mpx.service.subscription_manager._manager import _ChangeValueEvent 
from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib import EnumeratedDictionary
from mpx.lib.datetime import *
from mpx.lib import msglog
from mpx.componentry import implements
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from interfaces import IScheduleHolder
from interfaces import ISchedule

DFLT_SCHED_PRIO = 10

debug = 0
    
from mpx.lib.persistent import PersistentDataObject
class _PersistentSchedules(PersistentDataObject):
    def __init__(self, node, dmtype=None):
        self.summary = None
        PersistentDataObject.__init__(self, node, dmtype=dmtype)
        PersistentDataObject.load(self)
    def save(self):
        #print 'saving schedule'
        PersistentDataObject.save(self)
        msglog.log('service.time...Scheduler', msglog.types.INFO, 'Saved schedules to Persistent Storage')


class Schedules(CompositeNode, EventProducerMixin):
    _node_id='aa4e5046-6af7-4537-aee4-4c2cfeaf5502'
    implements(IScheduleHolder)
    
    def __init__(self, dmtype=None):
        self.persistant_schedule = None
        self.dmtype = dmtype
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'source','broadway', cd, str)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'source', config)
        if self.persistant_schedule:
            self.__pdo_filename__ = self.persistant_schedule._persistent.filename
            get_attribute(self, '__pdo_filename__', config, str)
        return config
    def start(self):
        CompositeNode.start(self)
        try:
            if self.persistant_schedule is None:
                self.persistant_schedule = _PersistentSchedules(self, self.dmtype)
            if self.persistant_schedule.summary:
                self.set_summary(self.persistant_schedule.summary, 0)  #assign value but don't save back
        except:
            msglog.exception()
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
            self.get_child('summary')
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = SchedulesSummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0
    def save_schedule(self):
        if self.persistant_schedule:
            self.persistant_schedule.summary = repr(self.get_summary())
            self.persistant_schedule.save()
            
class SchedulesSummary(CompositeNode):
    _node_id='ba976a27-c392-4cd6-9974-d9eb7c3021fe' 
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config
    def get(self, skipcache=0):
        return self.parent.get_summary()
    def set(self, value):
        self.parent.set_summary(value)
class Scheduler(CompositeNode):
    _node_id='3b0280b8-8835-44f8-9df0-8ab3990e799b' 
    implements(ISchedule)
    
    def __init__(self):
        CompositeNode.__init__(self)
        # cache related variables
        self._last_value = None
        self._next_value = None
        self._next_hms = None
        self._time_source = None
        self._time_of_last_get = None
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'source','broadway', cd, str)
        set_attribute(self, 'default',None, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'source', config)
        get_attribute(self, 'default', config)
        return config
    def start(self):
        self._last_value = None
        self._next_hms = None
        self.has_summary_child(self.parent.has_summary_child())
        if isinstance(self.parent, Schedules):
            evt = ScheduleCreatedEvent(self.parent, self)
            self.parent.event_generate(evt)
        CompositeNode.start(self)
    def prune(self, force=0):
        if isinstance(self.parent, Schedules):
            evt = ScheduleRemovedEvent(self.parent, self.as_node_url())
            self.parent.event_generate(evt)
        CompositeNode.prune(self, force)
    def get(self, skipcache=0):
        # current value from schedule is cached to speed response
        # cache is invalidated whenever a new schedule is saved
        # or when the time of the next entry has arrived
        # or at midnight
        # or if the time of the next entry cannot be determined
        try:
            # detect first read since midnight
            hms = self._get_hms() # now
            if self._time_of_last_get:
                # clock rolled over midnight or once an hour
                if (self._time_of_last_get > hms) or \
                    (self._time_of_last_get[0] != hms[0]):
                    # new day, force full update
                    # print 'midnight'
                    self._next_hms = None
            self._time_of_last_get = hms
            # see if we reached time of next entry
            if self._next_hms:
                if hms < self._next_hms:
                    if self._last_value is not None:
                        # print self.name, ' return cached value: ', self._last_value, self.get_next()
                        return self._last_value
        except:
            # tolerate exception, but report it
            msglog.exception()
            #print 'scheduler get exception'
            pass
        self._next_hms = None
        if self.default:
            default_node = self.as_node(self.default)
            self._last_value = default_node.get()
            self._next_value = default_node.get_next()
            if self._next_value:
                nxt_hms = self._next_value[0]
                ss = self._next_value[0].split(':')
                h = int(ss[0])
                m = int(ss[1])
                s = 0
                if len(ss) == 3:
                    s = int(ss[2])
                next_hms = (h,m,s)
                # handle next entry happening after midnight
                if next_hms < hms: # wrap around midnight
                    next_hms = (24,0,0) # allow cache until midnight
                self._next_hms = next_hms
            # print self.name, ' return fresh value: ', self._last_value, self._next_hms,
            # print ' next: ', self.get_next()
            return self._last_value
        # print 'no default'
        return None
    def get_next(self):
        if self._next_value:
            return self._next_value
        if self.default:
            self._next_value =  self.as_node(self.default).get_next()
        else:
            self._next_value = None
        return self._next_value # ('hh:mm:ss', 'value')
    def set(self, value):
        self.default = value  #set the name of the default element
        self._last_value = self._next_value = self._next_hms = None
    def get_summary(self):
        #example of value format:  (follow the brackets...[])
        #first the list of daily entries, each with following format:
        #['day name',['entry_name','time','value'],[next entry...]]
        #[[['sunday', ['1', '11:22:33', '74'], ['2', '12:34:56', '72']], 
        #  ['monday', ['1', '01:22:33', '72'], ['2', '22:34:56', '73']],
        #  ['tuesday', ['1', '01:22:33', '72'], ['2', '22:34:56', '73']], 
        #  ['wednesday', ['1', '01:22:33', '72'], ['2', '22:34:56', '73']], 
        #  ['thursday', ['1', '04:22:33', '71'], ['2', '22:34:56', '73']], 
        #  ['friday', ['1', '01:22:33', '74'], ['2', '22:34:56', '72']], 
        #  ['saturday', ['1', '01:22:33', '72'], ['2', '22:34:56', '73']], 
        # the daily entries can be in any order, usually in SMTWTFS order
        # the exception's Time Value schedules are peers of the week days
        # the order of days and exceptions is arbritary, here they are sorted
        #  ['exception_1', ['entry_1', '11:22:33', '44']], 
        #  ['exception_2', ['entry_1', '02:03:04', '55'], ['entry_2', '03:04:04', '44']], 
        #  ['exception_3', ['entry_1', '12:34:56', '78'], ['entry_2', '12:45:34', '57']], 
        #  ['exception_4', ['entry_1', '01:01:01', '11'], ['entry_2', '02:02:02', '22']]], 
        # Next is the list of Weekly Schedule node(s), this is fixed for bacnet:
        # [['name weekly_schedule', [list of seven schedule nodes to use for
        # each day of the week]], [next weekly schedule node (usually only one
        # exists)],]  In this examply there is only one
        #[['weekly_schedule', ['sunday', 'monday', 'tuesday', 'wednesday', 
        #                      'thursday', 'friday', 'saturday']]], 
        # Next are the exception nodes and their calendar entries:
        # [[name=exceptions, [list of exceptions,]],[next exceptions node (
        #  usually only one is used but more are allowed)],]
        # Exception calendar format is:
        # ['name', 'start_date', 'end_date', 'name of sched node to use']
        # In this example the name of the date range entry is the same
        # as the Daily schedule node.  This differs for BACnet Calendaor Object
        # type exception scheduels
        #[['exceptions', ['exception_1', '09/20/2008', '', 'exception_1'], 
        # ['exception_2', '11/20/2008', '12/20/2008', 'exception_2'], 
        # ['exception_3', '07/20/2008', '07/24/2008', 'exception_3'], 
        # ['exception_4', '05/27/2008', '', 'exception_4'], 
        # next follows the schedule to use on NON exception days:
        # 'weekly_schedule']], 
        # The final element is which node is the schedule object to use
        # for this schedule holder.  Almost always the Exception node:
        # 'exceptions']
        siblings = self.children_nodes()
        daily = []
        exceptions = []
        weekly = []
        for s in siblings:
            if s.__class__ == Daily:
                x = s.get_summary()
                x.insert(0, s.name)
                daily.append(x)
            elif s.__class__ == ExceptionSchedule:
                x = s.get_summary()
                x.insert(0, s.name)
                exceptions.append(x)
            elif s.__class__ == WeeklySchedule:
                x = s.get_summary()  #dict
                weekly.append([s.name,x])
        return [daily, weekly, exceptions, self.default]
    def set_summary(self, value, save=1):
        if isinstance(value, basestring):
            value = eval(value)
        if len(value) != 4:
            raise EInvalidValue()
        #Daily
        map = {}
        for n in value[0]:
            map[n[0]] = n
        if debug: print map
        #trim away unused nodes
        siblings = self.children_nodes()
        for s in siblings:
            if s.__class__ == Daily:
                if s.name not in map:
                    if debug: print 'prune: ', s.name
                    s.prune()
        for n in map.keys():
            try:  #reuse any existing node with the same name
                de = self.get_child(n)
                if debug: print 'found existing entry', de.name
            except ENoSuchName:  #create one if needed
                de = Daily()
                de.configure({'name':n, 'parent':self})
                de.start()
            de.set_summary(map[n][1:], 0)
        #Weekly
        map = {}
        for n in value[1]:
            map[n[0]] = n
        if debug: print map
        #trim away unused nodes
        siblings = self.children_nodes()
        for s in siblings:
            if s.__class__ == WeeklySchedule:
                if s.name not in map:
                    if debug: print 'prune: ', s.name
                    s.prune()
        for n in map.keys():
            try:  #reuse any existing node with the same name
                de = self.get_child(n)
                if debug: print 'found existing entry', de.name
            except ENoSuchName:  #create one if needed
                de = WeeklySchedule()
                de.configure({'name':n, 'parent':self})
                de.start()
            de.set_summary(map[n][1], 0)
        #Exceptions
        map = {}
        for n in value[2]:
            map[n[0]] = n
        if debug: print map
        #trim away unused nodes
        siblings = self.children_nodes()
        for s in siblings:
            if s.__class__ == ExceptionSchedule:
                if s.name not in map:
                    if debug: print 'prune: ', s.name
                    s.prune()
        for n in map.keys():
            try:  #reuse any existing node with the same name
                de = self.get_child(n)
                if debug: print 'found existing entry', de.name
            except ENoSuchName:  #create one if needed
                de = ExceptionSchedule()
                de.configure({'name':n, 'parent':self})
                de.start()
            de.set_summary(map[n][1:], 0)
        self.default = value[3]
        self._last_value = self._next_value = self._next_hms = None
        if save:
            self.save_schedule()
        pass
    def save_schedule(self):
        self.parent.save_schedule()
    def has_summary_child(self, create_if_absent=None):
        try:
            self.get_child('summary')
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = ScheduleSummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0
    def time_source(self):
        if self._time_source is None:
            if self.as_node_url().startswith('/services/time'):
                self._time_source = self.parent.parent
            else:
                self._time_source = as_node('/services/time/local')
        return self._time_source
    def _get_hms(self):
        return self.time_source().time_tuple()[3:6]
    
from persist import PERSISTANCE_MANAGER

Sched_Sync_TP = ThreadPool(2, name='ScheduleSyncService-ThreadPool')

class HierarchialScheduler(Scheduler, EventProducerMixin, EventConsumerMixin):
    immutable = False
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self):
        Scheduler.__init__(self)
        EventProducerMixin.__init__(self)
        EventConsumerMixin.__init__(self, self.change_of_value)
        self.__running = False
        self._retry_scheduled = None
        self.uuid = None
        self._property_list = []
        self._event_meta = {}
        self._overridden = None
        self._syncing = None
        self._sync_lock = Lock()
        self._failed_list = None
        self._sched_master = None
        self._nid = None
        self._sid = None
        
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'default',None, cd, str)
        if not cd.get('uuid') or cd.get('uuid') is 'None':
            # only needed if uuid does not exist in cd
            cd['uuid'] = UUID()
        set_attribute(self, 'uuid', REQUIRED, cd, str)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'default', cd)
        get_attribute(self, 'uuid', cd)
        return cd
    
    def start(self):
        self.__running = True
        self.watch_schedule()
        # setup_drivers will cause an initial cov event to be generated
        # and acted upon.  This will serve to drive all targets to the correct
        # present value
        self.setup_drivers()
        
        if self.syncing:
            Sched_Sync_TP.queue_noresult(
                self._synchronize_schedules, self.get_summary()
            )
        elif self.failed_list:
            self._schedule_failed()
            
    def stop(self):
        if self._sid:
            try:
                SM.destroy(self._sid)
            except:
                msglog.exception()
        if isinstance(self._sched_master, HierarchialScheduler):
            try:
                self._sched_master.event_unsubscribe(self, ScheduleChangedEvent)
            except:
                msglog.exception()
        self.__running = False
        
    def watch_schedule(self):
        if isinstance(self._sched_master, HierarchialScheduler):
            try:
                self._sched_master.event_unsubscribe(self, ScheduleChangedEvent)
            except:
                msglog.exception()
        if isinstance(self.parent, HierarchialScheduler):
            self._sched_master = self.parent
            self._sched_master.event_subscribe(self, ScheduleChangedEvent)
     
    def setup_drivers(self):
        if self._sid is not None:
            try:
                SM.destroy(self._sid)
            except:
                msglog.exception()
        else:
            self._nid = id(self)
        self._sid = SM.create_delivered(self, {self._nid:self})
               
    def get_uuid(self):
        return self.uuid
        
    # primarily intended for use over RNA
    def get_schedule_manager(self):
        sm = None
        try:
            sm = as_node('/services/Schedule Manager')
        except:
            from manager import ScheduleManager
            for service in as_node('/services').children_nodes():
                if isinstance(service, ScheduleManager):
                    sm = service
                    break
        return sm
      
    def children_schedules(self):
        scheds = []
        for x in self.children_nodes():
            if isinstance(x, (HierarchialScheduler,ProxiedHierarchialScheduler)):
                scheds.append(x)
        return scheds
    
    def children_schedule_names(self):
        scheds = []
        for x in self.children_nodes():
            if isinstance(x, (HierarchialScheduler,ProxiedHierarchialScheduler)):
                scheds.append(x.name)
        return scheds
    
    def change_of_value(self, event):
        if not self.__running:
            return
        if isinstance(event, (ChangeOfValueEvent, _ChangeValueEvent)):
            self.syncing_value = True
            action = self._drive_values
            value = event.results()[self._nid]['value']
        elif not self.overridden:
            # synchronize and update
            self._set_summary(event.new_schedule)
            self.syncing_schedule = True
            action = self._synchronize_schedules
            value = event.new_schedule
        else:
            return
        # either schedule synch or driving updates takes place
        # on threadpool.
        Sched_Sync_TP.queue_noresult(action, value)
      
    def save_schedule(self):
        PERSISTANCE_MANAGER.put_sched_summary(
            self.as_node_url(), self.get_summary()
        )
    
    def has_summary_child(self, create_if_absent=None):
        return 0
      
    def schedule_initialized(self):
        return bool(filter(lambda x: not isinstance(x, HierarchialScheduler), 
               self.children_nodes()))
        
    security.protect('set_summary', 'Configure') 
    def set_summary(self, value, save=1):
        self._set_summary(value, save)
        self.overridden = 1
    
    security.protect('_set_summary', 'Configure') 
    def _set_summary(self, value, save=1):
        Scheduler.set_summary(self, value, save)
        self.save_schedule()
        sched_event = ScheduleChangedEvent(self, value)
        self.event_generate(sched_event)
        self.syncing = True
        self._synchronize_schedules(value)
        
    security.protect('get_override', 'View')
    def get_override(self):
        return int(self.overridden)
    
    security.protect('set_override', 'Configure')
    def set_override(self, override):
        if not override and self.overridden:
            self.release_override()
        else:
            self.overridden = int(override)
    
    security.protect('release_schedule', 'Configure')
    def release_override(self):
        self.overridden = 0
        if isinstance(self.parent, HierarchialScheduler):
            self._set_summary(self.parent.get_summary())
            self.set_event_meta(self.parent.get_event_meta())
            
    security.protect('get_meta', 'View')
    def get_meta(self):
        return {'override':int(self.get_override()),
                'immutable':int(self.immutable)}
        
    ##
    # Get a list of the properties that this schedule is managing
    # 
    # 
    # @return [{"property":"/path/to/entity/prop",
    #           "type":"property_type",
    #           "priority":priority,
    #           "override":override,
    #           "valuemap":{"valuefromsched":"valuetodevice"}}]
    security.protect('get_properties', 'View') 
    def get_properties(self):
        return self._property_list
    
    ##
    # Set the list of properties that this schedule is managing.
    # 
    # @param properties   The list of properties to set:
    #                [{"entity":"/path/to/entity/prop",
    #                  "type":"property_type",
    #                  "name":"property_name",
    #                  "override":override,
    #                  "valuemap":{"valuefromsched":"valuetodevice"}}]
    #
    # @return  None
    security.protect('set_properties', 'Configure') 
    def set_properties(self, properties, save=1):
        '''setting properties on Schedule'''
        self._property_list = properties
        if save:
            PERSISTANCE_MANAGER.put_sched_props(
                self.as_node_url(), properties
            ) 
        try: 
            present_value = self.get()
        except:
            present_value = None
        if present_value is not None:
            # update properties
            self.syncing_value = True
            Sched_Sync_TP.queue_noresult(self._drive_values, present_value)
        
    ##
    # Retrieve the meta data associated with an event.
    # 
    # @return {1:{'name':'Occupied', 'color':'-1'}, 0:{'name':'Unoccupied',
    # 'color':'0x00ff00'}}
    security.protect('get_event_meta', 'View') 
    def get_event_meta(self):
        meta = {}
        master_schedule = self
        while 1:
            if master_schedule.get_override() or \
                not isinstance(master_schedule.parent,(HierarchialScheduler,ProxiedHierarchialScheduler)):
                meta = master_schedule._event_meta
                break
            else:
                master_schedule = master_schedule.parent
        return meta
   
    ##
    # Set the meta data associated with an event.
    # @param event_data {value:{'name':'eventname',
    #                     'color':'color'}}
    # 
    # @return None 
    security.protect('set_event_meta', 'Configure')
    def set_event_meta(self, meta, save=1):
        self._event_meta = meta
        if save:
            PERSISTANCE_MANAGER.put_sched_meta(
                self.as_node_url(), meta
            )
    
    security.protect('get_entity_root', 'View')
    def get_entity_root(self):
        return '/' + as_node('/services/Entity Manager').get_entities_name()[0]
        
    def _drive_values(self, value):
        failures = []        
        if value is None or not self.schedule_initialized():
            return
        self._sync_lock.acquire()
        try:
            set_list = []
            for prop in self._property_list:
                try:
                    prop_ref = as_internal_node(prop.get('entity')).get_property_ref(
                        prop['type'], prop['name']
                    )
                    if not hasattr(prop_ref, 'set_summary'):
                        set_list.append(prop)
                except:
                    msglog.log(
                        'Scheduler', 
                        msglog.types.WARN, 
                        'Error getting the property [%s] reference during drive schedule.' % (prop.get('name'))
                    )
                    msglog.exception()
            failed_list = self.failed_list[:]
            for prop in set_list:
                try:
                    # get a reference (nodepath) to actual node
                    prop_ref = as_internal_node(prop.get('entity')).get_property_ref(
                        prop['type'], prop['name']
                    )
                    # the purpose of the valuemap is to support a device
                    # that should have the same operating schedule, but requires
                    # a different parameter to the set command
                    valuemap = prop.get('valuemap')
                    if valuemap:
                        mapped_value = None
                        if valuemap.has_key(value):
                            mapped_value = valuemap.get(value)
                        elif valuemap.has_key(str(value)):
                            mapped_value = valuemap.get(str(value))
                        if mapped_value is not None:
                            try:
                                value = float(mapped_value)
                            except:
                                value = mapped_value
                    ovr_level = prop.get('override', DFLT_SCHED_PRIO)
                    ovr_key = str((prop_ref.as_node_url(), ovr_level))
                except:
                    msglog.log(
                        'Scheduler', 
                        msglog.types.WARN, 
                        'Error in computing property [%s] value during drive schedule.' % (prop.get('name')) 
                    )
                    msglog.exception()
                    continue
                try:
                    if hasattr(prop_ref, 'override'):
                        prop_ref.override(value, ovr_level)
                    else:
                        prop_ref.set(value)
                    if ovr_key in failed_list:
                        failed_list.remove(ovr_key)
                except:
                    msglog.log(
                        'Scheduler', 
                        msglog.types.WARN, 
                        'Error driving a schedule property: %s' % (prop_ref)
                    )
                    msglog.exception()
                    if not ovr_key in self.failed_list:
                        failures.append(ovr_key)
            if failures:
                self.failed_list = failures + failed_list
                self._notify_failed()
            else:
                self.syncing = False
        finally:
            self._sync_lock.release()
                
    def _synchronize_schedules(self, schedule):
        failures = []
        self._sync_lock.acquire()
        try:
            #set_list = [x for x in self._property_list if \
            #            isinstance(as_node(x.get('property')), Scheduler)]
            set_list = []
            for prop in self._property_list:
                try:
                    if prop['type'] != 'Sched':
                        continue
                    set_list.append(as_internal_node(prop.get('entity')).get_property_ref(
                        prop['type'], prop['name']
                    ))
                except:
                    msglog.log(
                        'Scheduler', 
                        msglog.types.WARN, 
                        'Error getting the schedule property [%s] reference during synchronize schedule.' % (prop.get('name'))
                    )
                    msglog.exception()
            failed_list = self.failed_list[:]
            for sched in set_list:
                sched_url = sched.as_node_url()
                try:
                    sched.set_summary(schedule)
                    if sched_url in failed_list:
                        failed_list.remove(sched_url)
                except:
                    msglog.log(
                        'Scheduler', 
                        msglog.types.WARN,
                        'Error setting schedule property: %s' % (sched.as_node_url())
                    )
                    msglog.exception()
                    if not sched_url in self.failed_list:
                        failures.append(sched_url)
            if failures:
                self.failed_list = failures + failed_list
                self._notify_failed()
            else:
                self.syncing = False
        finally:
            self._sync_lock.release()
        
    def _schedule_failed(self):
        self._retry_scheduled = sys_scheduler.seconds_from_now_do(
                60, self._notify_failed
            )

    def _notify_failed(self):
        Sched_Sync_TP.queue_noresult(self._sync_failed)
    
    def _sync_failed(self):
        #@fixme - add locking so that if a schedule changes
        failed = []
        self._sync_lock.acquire()
        try:
            while 1:
                try:
                    failed_prop = self.failed_list.pop()
                    try:
                        if not is_node_url(failed_prop):
                            property, ovr_level = eval(failed_prop)
                        else:
                            property = failed_prop
                        property = as_node(property)
                        if hasattr(property, 'set_summary'):
                            property.set_summary(self.get_summary())
                        else:
                            prop_ref, ovr_level = property
                            if hasattr(property, 'override'):
                                property.override(self.get(), ovr_level)
                            else:
                                property.set(self.get())
                    except:
                        #put it back
                        failed.append(failed_prop)
                except:
                    break
            self.failed_list = failed
            if failed:
                self._schedule_failed()
        finally:
            self._sync_lock.release()
        
    def _get_sync_status(self):
        if self._syncing is None:
            self._syncing = PERSISTANCE_MANAGER.get_sync_state(
                self.as_node_url()
            )
        return self._syncing
    
    def _set_sched_sync(self, value):
        self._syncing = value
        PERSISTANCE_MANAGER.put_sync_state(
            self.as_node_url(), self._syncing
        )
                
    syncing = property(_get_sync_status, _set_sched_sync)
    
    def _get_failed_list(self):
        if self._failed_list is None:
            self._failed_list = PERSISTANCE_MANAGER.get_fail_list(
                self.as_node_url()
            )
        return self._failed_list
    
    def _set_failed_list(self, failed_list):
        self._failed_list = failed_list
        PERSISTANCE_MANAGER.put_fail_list(
            self.as_node_url(), self._failed_list
        )
        
    failed_list = property(_get_failed_list, _set_failed_list)
    
    def _get_override(self):
        if self._overridden is None:
            self._overridden = PERSISTANCE_MANAGER.get_override(
                self.as_node_url()
            )
        return self._overridden
        
    def _set_override(self, value):
        self._overridden = value
        PERSISTANCE_MANAGER.put_override(
            self.as_node_url(), self._overridden
        )
    
    overridden = property(_get_override, _set_override)
   
#delegates to a local legacy schedule object. 
class DelegatedHierarchialScheduler(HierarchialScheduler):
    immutable = True
    def configure(self, cd):
        HierarchialScheduler.configure(self, cd)
        set_attribute(self, 'delegate', REQUIRED, cd, as_deferred_node)
        
    def configuration(self):
        cd = HierarchialScheduler.configuration(self)
        get_attribute(self, 'delegate', cd, as_node_url)
        return cd
    
    def get(self, skipcache=0):
        return self.delegate.get(skipcache)
    
    def set(self, value):
        self.delegate.set(value)
    
    def schedule_initialized(self):
        from bacnet_scheduler import Scheduler as BACScheduler
        return isinstance(self.delegate, BACScheduler) or \
            bool(filter(lambda x: not isinstance(x, HierarchialScheduler), \
            self.delegate.children_nodes()))               
    
    def get_summary(self):
        return self.delegate.get_summary()
        
    def _set_summary(self, value, save=1):
        try:
            self.delegate.set_summary(value, save)
        except:
            msglog.log(
                'Scheduler', 
                msglog.types.WARN,
                'Error setting schedule on: %s' % (self.delegate)
            )
            msglog.exception()
            #bail early
            return
        sched_event = ScheduleChangedEvent(self, value)
        self.event_generate(sched_event)
        self.syncing = True
        self.save_schedule()
        self._synchronize_schedules(value)
     
class CtlSvcDelegatedHierarchialScheduler(DelegatedHierarchialScheduler):
    pass

#delegates to a remote schedule via proxy.
class ProxiedHierarchialScheduler(CompositeNode, EventConsumerMixin):
    security = SecurityInformation.from_default()
    secured_by(security)  
    class RemoteScheduleWrapper(object):
        def __init__(self, parent, proxy):
            self.__dict__["parent"] = parent
            self.__dict__["_proxy"] = proxy
            object.__init__(self)
        def __getattr__(self, name):
            return getattr(self._proxy, name)
        def __setattr__(self, name, value):
            setattr(self._proxy, name, value)
        def children_names(self):
            return []
        def children_nodes(self):
            return []
        def children_schedules(self):
            return []
        def children_schedule_names(self):
            return []
        def as_node_url(self):
            return "%s/%s" % (self.parent.as_node_url(), self.name)
    def __init__(self):
        self._host = None
        self.synclock = RLock()
        self._sched_master = None
        self.caches_loaded = False
        self.cached_children_names = []
        self.cached_schedule_names = []
        self.proxy_url = ''
        self._proxy_node = None
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self, self.change_of_value)
        
    def configure(self, cd):
        # the proxy attr is special cased for
        # reverse compat. reasons and to allow 
        # proxy to evolve into a lazily evaluated property.
        proxy = cd.get('proxy', '')
        if isinstance(proxy, (CompositeNode, NodeFacade)):
            proxy = proxy.as_node_url()
        self.proxy_url = proxy
        set_attribute(self, 'host_url', '', cd, str)
        set_attribute(self, 'uuid', REQUIRED, cd, str)
        CompositeNode.configure(self, cd)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'host_url', cd)
        get_attribute(self, 'uuid', cd)
        cd['proxy'] = self.proxy_url
        return cd
        
    def start(self):
        self.watch_schedule()
            
    def stop(self):
        if isinstance(self._sched_master, HierarchialScheduler):
            try:
                self._sched_master.event_unsubscribe(self, ScheduleChangedEvent)
            except:
                msglog.exception()
        self.__running = False
    
    def watch_schedule(self):
        if isinstance(self._sched_master, HierarchialScheduler):
            try:
                self._sched_master.event_unsubscribe(self, ScheduleChangedEvent)
            except:
                msglog.exception()
        if isinstance(self.parent, HierarchialScheduler):
            self._sched_master = self.parent
            self._sched_master.event_subscribe(self, ScheduleChangedEvent)
            
    def get_uuid(self):
        return self.proxy.get_uuid()
    
    def get_schedule_manager(self):
        return self.proxy.get_schedule_manager()
      
    def change_of_value(self, event):            
        # push on to threadpool to avoid rna transactions in 
        # event_generate call chain.
        Sched_Sync_TP.queue_noresult(self._push_schedule, event)
    
    def _push_schedule(self, event):
        if hasattr(event, 'new_schedule') and not self.get_override():
            self._set_summary(event.new_schedule)
        
    security.protect('get', 'View')
    def get(self, skipCache=0):
        return self.proxy.get(skipCache)
    
    security.protect('get_summary', 'Configure')
    def get_summary(self):
      return self.proxy.get_summary()
  
    security.protect('set_summary', 'Configure') 
    def set_summary(self, value, save=1):
        self.proxy.set_summary(value, save)
    
    security.protect('_set_summary', 'Configure') 
    def _set_summary(self, value, save=1):
        self.proxy._set_summary(value, save)
        
    security.protect('get_override', 'View')
    def get_override(self):
        return int(self.proxy.get_override())
    
    security.protect('set_override', 'Configure')
    def set_override(self, override):
        if not override:
            self.release_override()
        else:
            self.proxy.set_override(override)
    
    security.protect('release_schedule', 'Configure')
    def release_override(self):
    	self.proxy.release_override()
        if isinstance(self.parent, HierarchialScheduler):
            self._set_summary(self.parent.get_summary())
            self.set_event_meta(self.parent.get_event_meta())
        
    security.protect('get_meta', 'View')
    def get_meta(self):
        return {'override':self.get_override(),'immutable':1}
        
    security.protect('get_properties', 'View') 
    def get_properties(self):
        return self.proxy.get_properties()

    security.protect('set_properties', 'Configure') 
    def set_properties(self, properties, save=1):
        existing_properties = self.get_properties()
        new_property_list = []
        for prop in properties:
            if prop not in existing_properties:
                try:
                    prop['entity'] = as_node(prop['entity']).as_remote_url()
                except:
                    msglog.exception()
                    continue
            new_property_list.append(prop)            
        self.proxy.set_properties(new_property_list, save)
    
    security.protect('get_event_meta', 'View') 
    def get_event_meta(self):
        return self.proxy.get_event_meta()
    
    security.protect('set_event_meta', 'Configure')
    def set_event_meta(self, meta, save=1):
        return self.proxy.set_event_meta(meta, save)
    
    security.protect('get_host', 'View')
    def get_host(self):
        if self._host is None:
            self._host = as_node(self.host_url)
        return self._host
    
    security.protect('set_host', 'Configure')
    def set_host(self, host):
        self._host = host
            
    security.protect('get_entity_root', 'View')
    def get_entity_root(self):
        return self.get_host().get_entity_root()
    
    def refresh_children_names(self, **options):
        self.synclock.acquire()
        try:
            self.cached_children_names = self.proxy.children_names()
            self.cached_schedule_names = self.proxy.children_schedule_names()
            self.caches_loaded = True
        finally:
            self.synclock.release()
        return (self.cached_children_names,self.cached_schedule_names)
    
    def children_names(self, **options):
        self.synclock.acquire()
        try:
            if not self.caches_loaded:
                self.refresh_children_names()
            names = list(self.cached_children_names)
        finally:
            self.synclock.release()
        return names
    
    def children_schedule_names(self):
        self.synclock.acquire()
        try:
            if not self.caches_loaded:
                self.refresh_children_names()
            names = list(self.cached_schedule_names)
        finally:
            self.synclock.release()
        return names
    
    def children_nodes(self, **options):
        names = self.children_names()
        return [self.get_child(name) for name in names]
    
    def children_schedules(self):
        names = self.children_schedule_names()
        return [self.get_child(name) for name in names]
    
    
    def get_child(self, name, **options):
        facade = self.proxy.get_child(name, **options)
        return ProxiedHierarchialScheduler.RemoteScheduleWrapper(self, facade)
    
    def has_child(self, name, **options):
        return name in self.children_names()
    
    def has_schedule(self, name):
        return name in self.children_schedule_names()
    
    def has_children(self):
        return bool(self.children_names())
    
    def has_schedules(self):
        return bool(self.children_schedule_names())
    
    def _get_proxy(self):
        if self._proxy_node is None:
            self._proxy_node = as_node(self.proxy_url)
        return self._proxy_node
    proxy = property(_get_proxy)
        
class ScheduleSummary(CompositeNode):
    _node_id='ee9083eb-a536-4b96-b00d-90afcc352ee1' 
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config
    def get(self, skipcache=0):
        return self.parent.get_summary()
    def set(self, value):
        self.parent.set_summary(value)
class Daily(CompositeNode):
    _node_id='64465216-cd37-4cec-ad05-1662284e255c' 
    def __init__(self):
        CompositeNode.__init__(self)
        self._schedule = {}
        self._sorted_list = None
        self._last_value = None
        self.next_entry = None
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config
    def start(self):
        self.has_summary_child(self.parent.has_summary_child())
        CompositeNode.start(self)
    def get(self, skipcache=0):
        # search schedule entry children for proper value for current time
        # return None if prior to first entry
        hms = self._get_hms()
        #get time sorted list of children hms's, search for best prior (with 24h wrap)
        if self._sorted_list is None:
            self.get_sorted_list_of_time_entries()
        found_node = self.search_sorted_list_for(hms)
        if found_node:
            # print ' get from day: ', self.name, found_node.get()
            try:
                if found_node.value.upper() == 'ON':
                    self._last_value = 1
                    return 1
                if found_node.value.upper() == 'OFF':
                    self._last_value = 0
                    return 0
            except:
                pass
            return eval(found_node.value)
        # print ' get from day: ', self.name, ' None'
        return None
    def get_last(self): # return last entry's value in this day's schedule
        if self._sorted_list is None:
            self.get_sorted_list_of_time_entries()
        if self._sorted_list:
            found_node = self._sorted_list[0][3]
            if found_node:
                try:
                    if found_node.value.upper() == 'ON':
                        return 1
                    if found_node.value.upper() == 'OFF':
                        return 0
                except:
                    pass
                return eval(found_node.value)
        return None # no schedule for today
    def get_next(self): # return tuple of next time and node or None
        # print ' get_next from: ', self.name
        if self.next_entry:
            return self.next_entry.get() 
        # the time is past the last entry for the day and there is no
        # next entry, make up a duplicate of the last one at midnight
        if self._sorted_list:
            found_node = self._sorted_list[0][3] # lasted entry in day
            return ('24:00:00', found_node.value) # make up entry at midnight
        return None
    def _get_hms(self):
        return self.parent._get_hms()
    def get_sorted_list_of_time_entries(self): # sorted into reverse order of time
        siblings = self.children_nodes()
        answer = []
        for s in siblings:
            if s.__class__ == DailyEntry:
                x = s._hms_as_int_tuple()  #(h,m,s,node)
                answer.append(x)
        answer.sort()
        answer.reverse()
        self._sorted_list = answer
        return answer
    def search_sorted_list_for(self, hms):
        next_entry = None #self._sorted_list[-1][3]
        if self._sorted_list:
            for hmsn in self._sorted_list:
                if hms >= hmsn[:3]:
                    self.next_entry = next_entry
                    return hmsn[3]
                next_entry = hmsn[3]
        self.next_entry = next_entry
        return None
    def search_sorted_list_for_next_entry(self, hms):
        if self._sorted_list:
            answer = self._sorted_list[-1]
            for hmsn in self._sorted_list:
                if hms >= hmsn[:3]:
                    break
                answer = hmsn
            return answer[3] #node
        return None
    def _reset_sorted_list(self):
        self._sorted_list = None #reset to force building of new sorted list        
    def get_summary(self, skipcache=0):
        siblings = self.children_nodes()
        answer = []
        for s in siblings:
            if s.__class__ == DailyEntry:
                x = s.get()
                x.insert(0, s.name)
                answer.append(x)
        return answer
    def set_summary(self, value, save=1):
        self._reset_sorted_list()
        if isinstance(value, basestring):
            value = eval(value)
        map = {}
        for n in value:
            map[n[0]] = n
        if debug: print map
        #trim away unused nodes
        siblings = self.children_nodes()
        for s in siblings:
            if s.__class__ == DailyEntry:
                if s.name not in map:
                    if debug: print 'prune: ', s.name
                    s.prune()
        for n in map.keys():
            try:  #reuse any existing node with the same name
                de = self.get_child(n)
                if debug: print 'found existing entry', de.name
            except ENoSuchName:  #create one if needed
                de = DailyEntry()
                de.configure({'name':n, 'parent':self})
                de.start()
            de.hms = map[n][1]
            de_value = map[n][2]
            if type(de_value) in types.StringTypes:
                if de_value.upper() == 'ON':
                    de_value = '1'
                elif de_value.upper() == 'OFF':
                    de_value = '0'
            de.value = de_value
        if save:
            self.save_schedule()
    def save_schedule(self):
        self.parent.save_schedule()
    def has_summary_child(self, create_if_absent=None):
        try:
            self.get_child('summary')
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = DailyEntrySummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0    

class DailyEntrySummary(CompositeNode):
    _node_id='cd97e8a5-a2f0-4fa3-87b0-a58445f11e15' 
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config
    def get(self, skipcache=0):
        return self.parent.get_summary()
    def set(self, value):
        self.parent.set_summary(value)

class DailyEntry(CompositeNode): # == BACnetTimeValue
    _node_id='5bead328-4527-4957-ab45-52c77af92ea6' 
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'hms','', cd, str)
        set_attribute(self, 'value',None, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'hms', config)
        get_attribute(self, 'value', config)
        return config
    def get(self, skipcache=0):
        return [self.hms, self.value]
    def set(self, value):
        self.parent._reset_sorted_list()
        if isinstance(value, basestring):
            value = eval(value)
        if len(value) == 3:
            n,t,v = value
            if n != self.name:
                raise EInvalidValue()
        else:
            t,v = value
        self.hms = t
        self.value = v
        self.parent.save_schedule()
    ##
    # answer the entry's time as a tuple of int or None values
    # None indicates wildcard
    def _hms_as_int_tuple(self):
        ss = self.hms.split(':')
        # print ss
        h = ss[0]
        m = ss[1]
        s = '*'
        if len(ss) > 2:
            s = ss[2]
        if h == '*':
            h = None
        else:
            h = int(h)
        if m == '*':
            m = None
        else:
            m = int(m)
        if s == '*':
            s = None
        else:
            s = int(s)
        # print (h,m,s)
        return (h,m,s,self)

class WeeklySchedule(CompositeNode):
    _node_id='5c653cd6-5af0-4026-bdcd-6f247205476b' 
    def __init__(self):
        CompositeNode.__init__(self)
        self._day_name_enumeration = EnumeratedDictionary({'sunday':6,'monday':0,'tuesday':1,'wednesday':2,
                                                           'thursday':3,'friday':4,'saturday':5})
        self._weekday_node = None
        self._last_daily_node = None
        self._last_value = None
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'sunday',None, cd, str)
        set_attribute(self, 'monday',None, cd, str)
        set_attribute(self, 'tuesday',None, cd, str)
        set_attribute(self, 'wednesday',None, cd, str)
        set_attribute(self, 'thursday',None, cd, str)
        set_attribute(self, 'friday',None, cd, str)
        set_attribute(self, 'saturday',None, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'sunday', config)
        get_attribute(self, 'monday', config)
        get_attribute(self, 'tuesday', config)
        get_attribute(self, 'wednesday', config)
        get_attribute(self, 'thursday', config)
        get_attribute(self, 'friday', config)
        get_attribute(self, 'saturday', config)
        return config
    def start(self):
        self.has_summary_child(self.parent.has_summary_child())
        CompositeNode.start(self)
    ##
    # get the value of the current day's schedule
    # the schedule's parent time node supplies the day of the week
    # the day of the week is used to determine which url to look up
    # return the get() value of whatever node the url points to.  
    # The url can poing to ANY node, not just schedule nodes
    def get(self, skipcache=0):
        if self._weekday_node is None:
            if self.as_node_url().startswith('/services/time'):
                self._weekday_node = self.parent.parent.parent.get_child('weekday')
            else:
                self._weekday_node = as_node('/services/time/local/weekday')
        day_number = self._weekday_node.get()
        day = self._day_name_enumeration[day_number]
        node_reference = getattr(self,str(day))
        self._last_daily_node = self.parent.as_node(node_reference)
        value_now = self._last_daily_node.get()
        if value_now is not None: 
            self._last_value = value_now
            return value_now
        # since before 1st entry
        # seach for last good entry from yesterday (and beyond)
        # print "look back to previous day's last entry"
        for i in range(6): # search backwards for last value
            day = self._day_name_enumeration[(day_number - 1 - i) % 7]
            node_reference = getattr(self,str(day))
            previous_daily_node = self.parent.as_node(node_reference)
            value_now = previous_daily_node.get_last() # last entry of the day
            if value_now is not None:
                # print ' day: ', day, ' value: ', value_now
                self._last_value = value_now
                return value_now
        self._last_value = None
        return None
    def get_next(self):
        answer = self._last_daily_node.get_next()
        if answer is not None:
            return answer
        # try to make a the next entry with current value for midnight
        if self._last_value is not None:
            return ('24:00:00', self._last_value)
        return None 
    ##
    # answer a dict of the days of the week and the url for each day
    #
    def get_summary(self):
        return [self.sunday, self.monday, self.tuesday, self.wednesday, self.thursday, self.friday, self.saturday]
        #answer = {}
        #for k in self._day_name_enumeration.string_keys():
            #answer[k] = getattr(self,k)
        #return answer
    ##
    # accept a dict or list of the url's for the days of the week
    # if dict, use names of days in value to determine which attributes to set
    # partial weeks ok
    # if list, must be 7 days long, sunday-saturday, with urls
    # URLs can be full, starting at / or simple string names of sibling nodes
    #
    def set_summary(self, value, save=1):
        if isinstance(value, basestring):
            value = eval(value)
        if type(value) == types.ListType:
            if len(value) == 7:
                self.sunday, self.monday, self.tuesday, self.wednesday, self.thursday, self.friday, self.saturday = value
                if save:
                    self.parent.save_schedule()
                return
            pass
        if type(value) == types.DictType:
            for k in value.keys():
                if k in self._day_name_enumeration.string_keys(): #only allow setting day url values
                    setattr(self, k, value[k])
            if save:
                self.parent.save_schedule()
            return
        raise EInvalidValue()
    def has_summary_child(self, create_if_absent=None):
        try:
            self.get_child('summary')
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = WeeklySummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0

class WeeklySummary(CompositeNode):
    _node_id='d5d2248c-d7cf-47fa-8428-0b6e722bf161' 
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config
    def get(self, skipcache=0):
        return self.parent.get_summary()
    def set(self, value):
        self.parent.set_summary(value)

class ExceptionSchedule(CompositeNode):
    _node_id='c9f75909-dd04-44d3-83b2-a2518b9cf875' 
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'normal',None, cd, str)
        self._schedule = {}
        self._sorted_list = None
        self._last_daily_node = None
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'normal', config)
        return config
    def start(self):
        self.has_summary_child(self.parent.has_summary_child())
        CompositeNode.start(self)
    def get(self, skipcache=0):
        #search self for proper value
        ymdw = self._get_ymdw()
        #get time sorted list of children hms's, search for best prior (with 24h wrap)
        if self._sorted_list is None:
            self.get_sorted_list_of_date_entries()
        found_node = self.search_sorted_list_for(ymdw)
        if found_node: # today is an exception day
            self._last_daily_node = self.parent.as_node(found_node.url)
            answer = self._last_daily_node.get()
            if answer is not None:
                return answer
            # if time prior to first entry, use normal schedule
            if self.normal:
                # use normal sched for current value but still use exception for next value
                return self.parent.as_node(self.normal).get()
        if self.normal:
            self._last_daily_node = self.parent.as_node(self.normal)
            return self._last_daily_node.get()
        self._last_daily_node = None
        return None
    def get_next(self):
        if self._last_daily_node:
            return self._last_daily_node.get_next()
        return None
    def _get_ymdw(self):
        # answer tuple with year, month, month_day, day_of_week
        # per time.stuct_time        
        tt = self.parent.time_source().time_tuple()
        return tt[:3]+tt[6:7]
    ##
    # @todo this currently just lists by the start date
    def get_sorted_list_of_date_entries(self):
        siblings = self.children_nodes()
        answer = []
        for s in siblings:
            if s.__class__ == ExceptionEntry:
                x = s._ymdw_as_int_tuple(s.start_mdyw)  #(y,m,d,w,  node)
                answer.append(x)
        answer.sort()
        answer.reverse()
        self._sorted_list = answer
        if debug: print answer
        return answer
    ##
    # this is where the action is for exception schedules
    # is current date within an exception period?
    # return the active exception node or None if an exception is not active
    def search_sorted_list_for(self, current_date): 
        current_year, current_month, current_day, current_week = current_date
        answer = None
        if self._sorted_list:
            for start_date in self._sorted_list:
                # start_date is ymdwn tuple.  (year, month, day, week, node)
                node = start_date[4] # node containing exception entry
                cmp_date = self._compare_dates(start_date, current_date)
                if debug: print 'compare result: ', cmp_date
                if cmp_date == 0:  # today matches start date exactly
                    return node # return node to indicate match
                # if date range, then check for within range
                if node.end_mdyw: # then this is a date-range
                    if cmp_date == 1: # currrent date is after start_date
                        end_date = node._ymdw_as_int_tuple(node.end_mdyw)
                        if self._compare_dates(end_date, current_date) < 1: #match
                            return node
        return None
    def _compare_dates(self, exception_date, current_date):
        # compare and exception date to the current date
        # return 0 is equal, 1 is current date after exception, -1 if before
        # handles regular dates, wild card dates and weekNDay matches
        # called twice for date ranges to compare start and end dates
        exception_year, exception_month, exception_day, exception_week = exception_date[:4]
        current_year, current_month, current_day, current_day_of_week = current_date
        # replace wild card entries with current values for year and month
        if exception_year is None:
            exception_year = current_year
        if exception_month is None:
            exception_month = current_month
        # !! hack to deal with CSCts62454.  WeekNDay not supported.
        if 1: #exception_week is None: # then normal date type entry
            if exception_day is None:
                exception_day = current_day
            # normal entry.  Compare
            exception = (exception_year, exception_month, exception_day)
            current = current_date[:3] # strip off day of week
            if exception == current: # exact match
                return 0
            if exception < current: # current date is after exception date
                return 1
            return -1 # current date is before exception date
        # handle WeekNDay entry. 
        # WND is never used in Date Range so return "before" if not exact match
        # to prevent date range and weekNDay from being mixed together
        if exception_day is None: # wild card assumes current value
            exception_day = current_day
        if exception_week != (current_day_of_week + 1): # not the right day of the week
            return -1
        if exception_year != current_year: return -1
        if exception_month != current_month: 
            if exception_month == 13: # match odd months
                if current_month % 2 == 0: return -1 # even month
            if exception_month != 14: return -1 # no match
            if current_month % 2 == 1: return -1 # odd month while looking for even
        # see if exception_week is match for the current week of the month
        if exception_week == 0: return 0  # match on any week (using 0 instead of None for wildcard)
        if exception_week == 6: # match on last week of month
            days_in_month = [None,31,28,31,30,31,30,31,31,30,31,30,31][current_month]
            if days_in_month == 28 and (current_year % 4 == 0): # February leap year
                days_in_month = 29
            if current_day > days_in_month - 7: return 0 # in last week
            return -1 # not in last week
        current_week = (( current_day - 1 ) / 7) + 1
        if current_week == exception_week: return 0 # match
        return -1 # no match
    def _reset_sorted_list(self):
        self._sorted_list = None #reset to force building of new sorted list        
    def get_summary(self, skipcache=0):
        siblings = self.children_nodes()
        answer = []
        for s in siblings:
            if s.__class__ == ExceptionEntry:
                x = s.get()
                x.insert(0,s.name)
                answer.append(x)
        answer.append(self.normal)
        return answer
    def set_summary(self, value, save=1):
        self._sorted_list = None
        if isinstance(value, basestring):
            value = eval(value)
        map = {}
        for n in value[:-1]:
            map[n[0]] = n
        self.normal = value[-1]
        #trim away unused nodes
        siblings = self.children_nodes()
        for s in siblings:
            if s.__class__ == ExceptionEntry:
                if s.name not in map:
                    s.prune()
        for n in map.keys():
            try:  #reuse any existing node with the same name
                de = self.get_child(n)
            except ENoSuchName:  #create one if needed
                de = ExceptionEntry()
                de.configure({'name':n,'parent':self})
                de.start()
            de.start_mdyw = map[n][1]
            de.end_mdyw = map[n][2]
            de.url = map[n][3]
        if save:
            self.save_schedule()
    def save_schedule(self):
        self.parent.save_schedule()
    def has_summary_child(self, create_if_absent=None):
        try:
            self.get_child('summary')
            return 1
        except ENoSuchName:
            if create_if_absent:
                ss = ExceptionEntrySummary()
                ss.configure({'name':'summary', 'parent':self})
                ss.start()
                return 1
        return 0
    
class ExceptionEntrySummary(CompositeNode):
    _node_id='b07158e1-3037-4b1d-a1a7-31b514dca7fd' 
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config
    def get(self, skipcache=0):
        return self.parent.get_summary()
    def set(self, value):
        self.parent.set_summary(value)

class ExceptionEntry(CompositeNode):
    _node_id='b6cd7c49-6f18-4dc6-9eec-e370201b13fe' 
    # The Exception logic generally follows the bacnet standard
    # An exception can be a single date, a date range or a weekNDay
    # A date or date range can be expressed using wild cards for different fields
    #
    # When W field not '*', then weekNDay format is used
    # BACnetWeekNDay ::= OCTET STRING (SIZE (3)) 
    #-- first octet month (1..14)            1 =January 
    #--      13 = odd months 
    #--      14 = even months 
    #--      X'FF' = any month   ( we use * in text, None in tuple )
    #-- second octet weekOfMonth where: 1 = days numbered 1-7 
    #--     2 = days numbered 8-14 
    #--     3 = days numbered 15-21 
    #--     4 = days numbered 22-28 
    #--     5 = days numbered 29-31 
    #--     6 = last 7 days of this month 
    #--     X'FF' = any week of this month   ( we use * in text, 0 in tuple (None means the entry is not WeekNDay) )
    #-- third octet dayOfWeek (1..7) where 1 = Monday  (we use four element)
    #--      7 = Sunday 
    #--      X'FF' = any day of week  ( we use * in text, None in tuple )
    #  
    # 1/1/2010 would be new years day in 2010
    # 1/1/*    would be new years day every year
    # 11/2/*/1 would be first tuesay in November
    # 11/4/*/4 would be Thanksgiving (4th Thursday of November)
    # */1/*/1 first monday of every month
    # 13/1/*/1 first monday of odd months
    # 14/5/*/2 second friday of even months
    # 1/1/*/6  last monday in January
    # */1/*/*  every monday  
    # 7/4/*    4th of July
    # 6/18/*   Fred's birthday
    # examples of valid date ranges:
    # 12/20/* - 12/31/*
    # 12/20/2010 - 1/4/2011
    # example of invalid date range:
    # 12/20/* - 1/4/*  (end date preceeds start date for any year)
    # 12/20/* - 1/4/2011  (wild card would be ok for <= 2010 only)
    
    #    An Exception_Schedule (Section 12.24.8) may include a BACnetDateRange in a 
    #    BACnetCalendarEntry, in which context the meaning is specified for a Date that is totally 
    #    unspecified. However no indication is given regarding the validity or meaning of other wildcard 
    #    combinations. A Schedule's Effective_Period (Section 12.24.6) is also a BACnetDateRange, but 
    #    the standard is silent on the issue of wildcard values. 
    #     
    #    Interpretation:  The BACnet standard [ANSI/ASHRAE Standard 135-2004] is open to multiple 
    #    interpretations regarding the meaning of wildcards in dates, especially when used to specify date 
    #    ranges. The following describes how wildcards are interpreted by the Andover Controls B-AAC 
    #    controllers, especially in the context of the Schedule properties Exception_Schedule and 
    #    Effective_Period, and the Calend property Date_List. 
    #    For purposes of comparing dates, the day-of-week fields are not used. That is, they are totally 
    #    redundant. When comparing dates, a wildcard field is considered equal to the corresponding 
    #    field in the date being compared. A date falls within the range if it is not before the StartDate and 
    #    not after the endDate. 
    #    Because the day-of-week field is redundant, its value must be either unspecified or consistent 
    #    with the other fields. Because it can be consistent with those fields only if they are specified, the 
    #    controllers allow the day-of-week to be specified only if the other three fields are specified as 
    #    well. 
    #    Accordingly, the following conditions in a date range are treated as errors and will prevent a 
    #    WriteProperty from completing: 
    #    1. A day-of-week is specified but two or fewer of the other fields in the Date are specified. 
    #    2. A day-of-week is specified, but is inconsistent with the Date specified by the other fields. 
    #    3. A year field is specified, which is outside the range limit of 1989 - 2105. 
    #    4. The endDate is earlier than the StartDate. 
    #    5. Any of the specified fields are out of range (e.g., 31st day of February).  
    #     
    #    This interpretation  has been implemented and was accepted by the BACnet Testing Laboratory. 
    #    It is included in the PIC Statement for certified B-AAC devices. It needs to be formally accepted 
    #    as the correct interpretation.
    def configure(self,cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, '__node_id__',self._node_id, cd, str)
        set_attribute(self, 'url',None, cd, str)
        set_attribute(self, 'start_mdyw',None, cd, str)
        set_attribute(self, 'end_mdyw',None, cd, str)
        set_attribute(self, 'duration', None, cd, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        get_attribute(self, 'url', config)
        get_attribute(self, 'start_mdyw', config)
        get_attribute(self, 'end_mdyw', config)
        get_attribute(self, 'duration', config)
        return config
    def get(self, skipcache=0):
        # ['12/20/*', '12/31/*', name_of_daily_schedule]
        # ['12/25/2010', '', name_of_daily_schedule]
        return [self.start_mdyw, self.end_mdyw, self.url]
    def set(self, value):
        self.parent._reset_sorted_list()
        if isinstance(value, basestring):
            value = eval(value)
        if len(value) == 4:
            n,s,e,v = value
            if n != self.name:
                raise EInvalidValue()
        else:
            s,e,v = value
        self.start_mdyw = s
        self.end_mdyw = e
        self.url = v
        self.parent.save_schedule()
    ##
    # answer the entry's date as a tuple of int or None values
    # Convert '*' to None to indicate wildcard    
    def _ymdw_as_int_tuple(self, mdyw):
        ss = mdyw.split('/')
        m = ss[0]
        d = ss[1]
        y = '*'
        if len(ss) >= 3:
            y = ss[2]
        w = None
        if len(ss) == 4:
            w = ss[3]
        if m == '*':
            m = None
        else:
            m = int(m)
        if d == '*':
            d = None
        else:
            d = int(d)
        if y == '*':
            y = None
        else:
            y = int(y)
        if w:
            w = int(w) # when w not None, then d is day of week. 1=mon,7=sun...
        return (y,m,d,w,self)

# """
# from mpx.service.schedule.scheduler import *

# s=Scheduler()
# t=as_node('/services/time/local')
# config={'name':'scheduler_1','parent':t,'default':'ex_1'}
# s.configure(config)

# ss=ScheduleSummary()
# config={'name':'summary','parent':s}
# ss.configure(config)

# d1=Daily()
# config={'name':'daily_1','parent':s}
# d1.configure(config)

# de1=DailyEntry()
# config={'name':'entry_1','parent':d1, 'hms':'08:00:00','value':'1'}
# de1.configure(config)

# d2=Daily()
# config={'name':'daily_2','parent':s}
# d2.configure(config)

# de2=DailyEntry()
# config={'name':'entry_1','parent':d2, 'hms':'08:00:00','value':'1'}
# de2.configure(config)

# des1=DailyEntrySummary()
# des1.configure({'name':'summary','parent':d1})

# des2=DailyEntrySummary()
# des2.configure({'name':'summary','parent':d2})

# w = WeeklySchedule()
# w.configure({'name':'week_1','parent':s,'sunday':'daily_2','monday':'daily_1','tuesday':'daily_1','wednesday':'daily_1','thursday':'daily_1','friday':'daily_1','saturday':'daily_2'})

# ws = WeeklySummary()
# ws.configure({'name':'summary','parent':w})

# ex = ExceptionSchedule()
# ex.configure({'name':'ex_1', 'parent':s, 'normal':'week_1'})

# des1=ExceptionEntrySummary()
# des1.configure({'name':'summary','parent':ex})

# ee = ExceptionEntry()
# ee.configure({'name':'xmas', 'parent':ex, 'url':'daily_2', 'start_mdyw':'12/25/*','end_mdyw':'12/25/*'})

# ee = ExceptionEntry()
# ee.configure({'name':'today', 'parent':ex, 'url':'daily_2', 'start_mdyw':'8/27/*','end_mdyw':'8/27/*'})


# s.start()



# s.prune()


# WeeklySchedule  
  # daily
    # hms  ##:##:##
    # value int
  # weekly_schedule
    
  
  # <mpxconfig node_version='LATEST'>
  # <node name='time_schedule_1' node_id='3b0280b8-8835-44f8-9df0-8ab3990e799b' module='mpx.service.schedule.generic.Scheduler'  config_builder=''  inherant='false' description='Time Schedule service'>
    # <node name='weekdays' node_id='64465216-cd37-4cec-ad05-1662284e255c' module='mpx.service.schedule.generic.Daily'  config_builder=''  inherant='false' description='Daily Schedule'>
      # <node name='summary' node_id='cd97e8a5-a2f0-4fa3-87b0-a58445f11e15' module='mpx.service.schedule.generic.DailyEntrySummary'  config_builder=''  inherant='true' description='Daily Schedule Entry Summary '>
      # </node>
      # <node name='morning' node_id='5bead328-4527-4957-ab45-52c77af92ea6' module='mpx.service.schedule.generic.DailyEntry'  config_builder=''  inherant='false' description='Daily Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='hms' value='08:00:00'/>
          # <property name='value' value='1'/>
        # </config>
      # </node>
      # <node name='evening' node_id='5bead328-4527-4957-ab45-52c77af92ea6' module='mpx.service.schedule.generic.DailyEntry'  config_builder=''  inherant='false' description='Daily Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='hms' value='17:00:00'/>
          # <property name='value' value='0'/>
        # </config>
      # </node>
    # </node>
    # <node name='weekends' node_id='64465216-cd37-4cec-ad05-1662284e255c' module='mpx.service.schedule.generic.Daily'  config_builder=''  inherant='false' description='Daily Schedule'>
      # <node name='summary' node_id='cd97e8a5-a2f0-4fa3-87b0-a58445f11e15' module='mpx.service.schedule.generic.DailyEntrySummary'  config_builder=''  inherant='true' description='Daily Schedule Entry Summary '>
      # </node>
      # <node name='all_the_time' node_id='5bead328-4527-4957-ab45-52c77af92ea6' module='mpx.service.schedule.generic.DailyEntry'  config_builder=''  inherant='false' description='Daily Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='hms' value='00:00:01'/>
          # <property name='value' value='0'/>
        # </config>
      # </node>
    # </node>
    # <node name='weekly_schedule' node_id='5c653cd6-5af0-4026-bdcd-6f247205476b' module='mpx.service.schedule.generic.WeeklySchedule'  config_builder=''  inherant='false' description='Weekly Schedule Entries'>
      # <config>
        # <property name='__type__' value='service'/>
        # <property name='friday' value='/services/time/time_schedule_1/weekdays'/>
        # <property name='tuesday' value='/services/time/time_schedule_1/weekdays'/>
        # <property name='thursday' value='/services/time/time_schedule_1/weekdays'/>
        # <property name='saturday' value='/services/time/time_schedule_1/weekends'/>
        # <property name='wednesday' value='/services/time/time_schedule_1/weekdays'/>
        # <property name='sunday' value='/services/time/time_schedule_1/weekends'/>
        # <property name='monday' value='/services/time/time_schedule_1/weekdays'/>
      # </config>
      # <node name='summary' node_id='d5d2248c-d7cf-47fa-8428-0b6e722bf161' module='mpx.service.schedule.generic.WeeklyEntrySummary'  config_builder=''  inherant='true' description='Weekly Schedule Entry Summary '>
      # </node>
    # </node>
    # <node name='exceptions' node_id='c9f75909-dd04-44d3-83b2-a2518b9cf875' module='mpx.service.schedule.generic.Exception'  config_builder=''  inherant='false' description='Exception Schedule'>
      # <config>
        # <property name='normal' value='/services/time/time_schedule_1/weekly_schedule'/>
      # </config>
      # <node name='summary' node_id='b07158e1-3037-4b1d-a1a7-31b514dca7fd' module='mpx.service.schedule.generic.ExceptionEntrySummary'  config_builder=''  inherant='true' description='Exception Schedule Entry Summary '>
      # </node>
      # <node name='new_years_day' node_id='b6cd7c49-6f18-4dc6-9eec-e370201b13fe' module='mpx.service.schedule.generic.ExceptionEntry'  config_builder=''  inherant='false' description='Exception Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='url' value='/services/time/time_schedule_1/weekends'/>
          # <property name='mdyw' value='01:01:*:*'/>
        # </config>
      # </node>
      # <node name='christmas' node_id='b6cd7c49-6f18-4dc6-9eec-e370201b13fe' module='mpx.service.schedule.generic.ExceptionEntry'  config_builder=''  inherant='false' description='Exception Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='url' value='/services/time/time_schedule_1/weekends'/>
          # <property name='mdyw' value='12:25:*:*'/>
        # </config>
      # </node>
      # <node name='fourth_monday_in_june' node_id='b6cd7c49-6f18-4dc6-9eec-e370201b13fe' module='mpx.service.schedule.generic.ExceptionEntry'  config_builder=''  inherant='false' description='Exception Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='url' value='/services/time/time_schedule_1/weekends'/>
          # <property name='mdyw' value='06:02:*:4'/>
        # </config>
      # </node>
      # <node name='thanksgiving' node_id='b3f4ae23-9256-4639-adc2-777d71de5ead' module='mpx.service.schedule.generic.ExceptionEntry'  config_builder=''  inherant='false' description='Exception Schedule Entry'>
        # <config>
          # <property name='__type__' value='service'/>
          # <property name='url' value='..'/>
          # <property name='mdyw' value='11:05:*:4'/>
        # </config>
      # </node>
    # </node>
  # </node>
# </mpxconfig>


# offset = dw - ((date-1) % 7)
# week=(date + offset - 1) / 7 + 1 
# daysinmonth(month) - date < 7: last week
# """


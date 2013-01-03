"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.lib import factory
from mpx.lib.node import CompositeNode
from mpx.lib.node import is_node
from mpx.lib.node import as_node
from mpx.lib.event import EventProducerMixin
from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import ScheduleCreatedEvent
from mpx.lib.event import ScheduleRemovedEvent
from mpx.lib.event import ScheduleMovedEvent
from mpx.lib.entity.entity import wrapped
from mpx.lib.uuid import UUID
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import REQUIRED
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import EImmutable
from mpx.lib.exceptions import EBatchedException
from mpx.lib.exceptions import current_exception
from mpx.lib.scheduler import scheduler as sys_scheduler
from mpx.lib.threading import Thread
from mpx.service.cloud.hosts import NBMManager
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from scheduler import HierarchialScheduler
from scheduler import DelegatedHierarchialScheduler
from scheduler import CtlSvcDelegatedHierarchialScheduler
from scheduler import ProxiedHierarchialScheduler
from scheduler import Schedules
import scheduler
from bacnet_scheduler import Schedules as BacnetSchedules
from persist import serialize_node
from persist import sched_sort
from persist import PERSISTANCE_MANAGER
import types
import urllib
    
def create_node(node_info):
    node = factory(node_info.get('factory'))
    node.configure(node_info.get('cfg'))
    return node
    
class _ProxiedScheduleManager(object):
    def __init__(self, manager):
        self._manager = manager
        self._persisted_scheds = {}
        self._active_scheds = {}
        self._new_scheds = {}
        
    def register_persisted(self, host_url, uuid, sched):
        if self._persisted_scheds.get(host_url) is None:
            self._persisted_scheds[host_url] = {}
        self._persisted_scheds[host_url][uuid] = sched
        
    def was_persisted(self, host_url, uuid):
        if self._persisted_scheds.get(host_url, {}).get(uuid):
            return True
        return False
    
    def get_persisted(self, host_url, uuid):
        return self._persisted_scheds.get(host_url, {}).get(uuid)
    
    def register_active(self, host_url, uuid, sched):
        if self._active_scheds.get(host_url) is None:
            self._active_scheds[host_url] = {}
        self._active_scheds[host_url][uuid] = sched
        
    def register_new(self, host_url, uuid, sched):
        if self._new_scheds.get(host_url) is None:
            self._new_scheds[host_url] = {}
        self._new_scheds[host_url][uuid] = sched
        
    def clear_active(self, host_url):
        self._active_scheds[host_url] = {}
        new_scheds = self._new_scheds.get(host_url, {})
        for uuid, sched in new_scheds.items():
            self.register_persisted(host_url, uuid, sched)
        self._new_scheds[host_url] = {}
        
    def prune_inactive(self, host_url):
        persisted = self._persisted_scheds.get(host_url, {})
        active_uuids = self._active_scheds.get(host_url, {}).keys()
        for uuid, sched in persisted.items():
            if uuid not in active_uuids:
                try:
                    dead_schedule = self._persisted_scheds.get(host_url).get(uuid)
                    self._manager.remove_schedule(dead_schedule.as_node_url(), 1)
                    del self._persisted_scheds[host_url][uuid]
                except:
                    msglog.exception()
                    
class ScheduleManager(CompositeNode, EventProducerMixin, EventConsumerMixin):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self,*args, **kw):
        super(ScheduleManager, self).__init__(*args, **kw)
        EventProducerMixin.__init__(self)
        EventConsumerMixin.__init__(self, self.event_handler)
        self.remotes_loaded = False
        self.__running = False
        self._hm = None
        self._ctlsvc = None
        self._hm_scheduled = None
        self._ph_scheduled = None
        self._ph_loader_scheduled = None
        self._ph_loaded = False
        self.__last_pruned = None
        self._proxied_manager = _ProxiedScheduleManager(self)
        self.__legacy_schedules = []
        self.__legacy_needs_pruning = []
        self.__ph_legacy_needs_pruning = []
        
    def configure(self, config):
        super(ScheduleManager, self).configure(config)
        # "hidden" configuration option that can be overridden if a user
        # installed schedules in an abnormal place.
        sched_holder = '/services/time/local'
        set_attribute(self, 'sched_holder', sched_holder, config)
        config['dflt_sched_prio'] = config.get('dflt_sched_prio', scheduler.DFLT_SCHED_PRIO)
        set_attribute(self, 'dflt_sched_prio', REQUIRED, config, int)
        scheduler.DFLT_SCHED_PRIO = self.dflt_sched_prio

    def configuration(self):
        config = super(ScheduleManager, self).configuration()
        get_attribute(self, 'sched_holder', config)
        get_attribute(self, 'dflt_sched_prio', config)
        return config
    
    def start(self):
        if self.is_running():
            return
        if as_node('/services').has_child('Entity Manager'):
            em = as_node('/services/Entity Manager')
            if not em.is_running():
                # see if this function is already wrapped.  If it is wrapped
                # im_self is not an attribute.
                if hasattr(em.do_start, 'im_self'):
                    em.do_start = wrapped(em.do_start, None, self.do_start)
                return
        self.do_start()
        
    def do_start(self):
        self.message('Schedule Manager starting.')
        schedule_ph_prune = False
        scheds = PERSISTANCE_MANAGER.get_scheds()
        proxy_prune_list = []
        for sched in scheds:
            node_info = {}
            try:
                node_info = PERSISTANCE_MANAGER.get_sched_cfg(sched)
               	if node_info.get('factory').count('ProxiedHierarchialScheduler'):
                    host_url = node_info.get('cfg').get('host_url')
                    try:
                        as_node(host_url)
                    except ENoSuchName:
                        proxy_prune_list.append(sched)
                        continue
                sched_node = create_node(node_info)
                uuid = node_info.get('cfg').get('uuid')
                if not uuid or uuid == 'None':
                    # uuid was added later - below code to deal with persisting
                    # of that property.
                    PERSISTANCE_MANAGER.put_sched(
                        sched_node.as_node_url(), serialize_node(sched_node)
                    )
            #except:
            #    msglog.exception()
            #    continue
                if not isinstance(sched_node, ProxiedHierarchialScheduler):
                    # proxied schedules store locally.  Restore summary, properties
                    # and meta for local.
                    url = sched_node.as_node_url()   
                    properties = PERSISTANCE_MANAGER.get_sched_props(url)
                    if properties:
                        sched_node.set_properties(properties, save=False)
                    meta = PERSISTANCE_MANAGER.get_sched_meta(url)
                    if meta:
                        sched_node.set_event_meta(meta)
                    if not isinstance(sched_node, 
                        (DelegatedHierarchialScheduler,
                         CtlSvcDelegatedHierarchialScheduler)):
                        sched_node._set_summary(
                           PERSISTANCE_MANAGER.get_sched_summary(url)
                        )    
                    sched_node.set_override(
                        PERSISTANCE_MANAGER.get_override(url)
                    )
                if isinstance(sched_node, DelegatedHierarchialScheduler):
                    # keep track of the "legacy" schedules we are delegating to
                    delegate = sched_node.configuration().get('delegate')
                    try:
                        # see if the target still exists.
                        as_node(delegate)
                        self.__legacy_schedules.append(delegate)
                    except:
                        # the legacy schedule disappeared on us.  
                        # schedule it for removal, iff it doesn't have children
                        if isinstance(sched_node, CtlSvcDelegatedHierarchialScheduler):
                            schedule_ph_prune = True
                            self.__ph_legacy_needs_pruning.append(sched_node)
                        else:
                            self.__legacy_needs_pruning.append(sched_node)
                elif isinstance(sched_node, ProxiedHierarchialScheduler):
                    host_url = sched_node.host_url
                    uuid = sched_node.configuration().get('uuid')
                    self._proxied_manager.register_persisted(host_url, uuid, sched_node)
                try:
                    sched_node.start()
                except:
                    msglog.exception()
            except:
                msglog.exception()
                #continue
            #LOOP ENDS
      	proxy_prune_list.sort(sched_sort)
        for sched in proxy_prune_list:
            msg = 'Removing schedule %s for non existent host.' % urllib.unquote(sched)
            self.message(msg, level=0)
            PERSISTANCE_MANAGER.remove_sched(sched)  
        self._load_schedules()
        self._prune_schedules(self.__legacy_needs_pruning)
        try:
            remote_hosts = self.host_manager.children_nodes()
        except:
            remote_hosts = []
        self.load_remote_hosts(remote_hosts)
        if schedule_ph_prune:
            # there's control service scheduled to care about.
            self._ph_scheduled = sys_scheduler.seconds_from_now_do(
                60, self._prune_legacy_ph_schedules
            )
        self.__running = True
        
    def is_running(self):
        return self.__running
    
    def event_handler(self, event):
        if isinstance(event, ScheduleCreatedEvent) and \
            event.source.name == 'TIM':
            schedule = event.schedule
            for sched_node in self.__ph_legacy_needs_pruning:
                if as_node(sched_node.configuration().get('delegate')) is schedule:
                    # we already have a reference to this schedule.  It's now
                    # been created by the control service.
                    self.__ph_legacy_needs_pruning.remove(sched_node)
                    self.__legacy_schedules.append(delegate)
                    return
            # create a new schedule if we don't have a reference already
            if not schedule.as_node_url() in self.__legacy_schedules:
                self._create_legacy_schedule(
                    schedule, CtlSvcDelegatedHierarchialScheduler
                    )  
                        
    def _load_schedules(self):
        self._load_legacy_schedules()
        self._load_bacnet_schedules()
        self._load_ctlsvc_schedules()
        
    def _load_legacy_schedules(self):
        sched_holders = []
        try:
            for child in as_node(self.sched_holder).children_nodes():
                if isinstance(child, Schedules) and child.name != 'TIM':
                    sched_holders.append(child)
        except ENoSuchName:
            pass
        for sched_holder in sched_holders:
            self._load_schedule_group(
                sched_holder, DelegatedHierarchialScheduler
                )
          
    def _load_bacnet_schedules(self):
        sched_holders = []
        try:
            for child in as_node(self.sched_holder).children_nodes():
                if isinstance(child, BacnetSchedules):
                    sched_holders.append(child)
        except ENoSuchName:
            pass
        for sched_holder in sched_holders:
            self._load_schedule_group(
                sched_holder, DelegatedHierarchialScheduler
                )
            
    def _load_ctlsvc_schedules(self):
        if self._ctl_svc_running():
            sched_holder = None
            try:
                sched_holder = as_node(self.sched_holder).get_child('TIM')
            except:
                self._ph_loaded = True
            if sched_holder:
                sched_holder.event_subscribe(self, ScheduleCreatedEvent)
                self._load_schedule_group(
                    sched_holder, CtlSvcDelegatedHierarchialScheduler
                    )
                self._ph_loaded = True
                return
        self._ph_loader_scheduled = sys_scheduler.seconds_from_now_do(
            60, self._load_ctlsvc_schedules
            )
        
    def _load_schedule_group(self, sched_holder, klass):
        for sched in sched_holder.children_nodes():
            try:
                self._create_legacy_schedule(sched, klass)
            except:
                msg = 'Error adding RZSchedule %s' % sched.as_node_url()
                self.message(msg)
                msglog.exception()
        
    def _create_legacy_schedule(self, sched, klass): 
        sched_path = sched.as_node_url()
        if sched_path not in self.__legacy_schedules:
            do_create = True
            for s in self.__legacy_needs_pruning:
                if sched_path == s.configuration().get('delegate'):
                    do_create = False
                    break
            if do_create:
                for s in self.__ph_legacy_needs_pruning:
                    if sched_path == s.configuration().get('delegate'):
                        do_create = False
                        break
            if do_create:
                new_sched = klass()
                name = sched.name.replace(':', '_')
                cd = {'name':name,
                      'parent':self,
                      'delegate':sched.as_node_url()}
                new_sched.configure(cd)
                nodepath = new_sched.as_node_url()
                PERSISTANCE_MANAGER.put_sched(
                    nodepath, serialize_node(new_sched)
                    )
                new_sched.set_override(True)
                new_sched.start()
            self.__legacy_schedules.append(sched_path)
                     
    def _prune_schedules(self, prune_list):
        while 1:
            try:
                sched_node = prune_list.pop()
                delegate = sched_node.configuration().get('delegate')
                if not delegate in self.__legacy_schedules and \
                    not sched_node.children_nodes():
                    # no children, it can be removed
                    msg = 'Removing abandoned legacy schedule %s' % delegate  
                    self.message(msg)
                    self.remove_schedule(sched_node, 1)
            except IndexError:
                break
            
    def _prune_legacy_ph_schedules(self):
        if not self._ph_scheds_loaded():
            self._ph_scheduled = sys_scheduler.seconds_from_now_do(
                60, self._prune_legacy_ph_schedules
            )
        else:
            self._prune_schedules(self.__ph_legacy_needs_pruning)
        
    def _ph_scheds_loaded(self):
        loaded = False
        if self._ctl_svc_running() and self._ph_loaded:
            loaded = True
        return loaded

    def _ctl_svc_running(self):
        running = True
        if not self.ctlsvc or self.ctlsvc.get().lower() != 'running':
            running = False
        return running
    
    def load_remote_hosts(self, remote_hosts):
        thread = Thread(
            name=self.name, 
            target=self._load_remote_hosts, 
            args=(remote_hosts,)
        )
        thread.start()
        
    def is_loading(self):
        return not self.remotes_loaded
    
    def is_loaded(self):
        return self.remotes_loaded
    
    def _load_remote_hosts(self, remote_hosts):
        failed = []
        for host in remote_hosts:
            try:
                sched_manager = host.as_remote_node('/services/Schedule Manager')
                self._load_remote_schedules(sched_manager, host)
            except:
                message = 'Unable to load remote schedules from host: %s' % host.name
                self.message(message)
                msglog.exception()
                failed.append(host)
        self.remotes_loaded = True
        #@fixme - convert to an event based approach, triggered by changes
        #downstream.
        if remote_hosts: #failed:
            #self._hm_scheduled = sys_scheduler.seconds_from_now_do(
            #    60, self.load_remote_hosts, failed
            #)
            self._hm_scheduled = sys_scheduler.seconds_from_now_do(
                300, self.load_remote_hosts, remote_hosts
            )
        
    def _load_remote_schedules(self, sched_manager, host): 
        hostname = host.name
        host_url = host.as_node_url()
        for sched_name in sched_manager.children_schedule_names():
            name = '[%s] %s' % (hostname, sched_name)
            try:
                schedule = sched_manager.get_child(sched_name)
                uuid = schedule.get_uuid()
                if self._proxied_manager.was_persisted(host_url, uuid):
                    persisted_sched = self._proxied_manager.get_persisted(host_url, uuid)
                    if persisted_sched.name != name:
                        from_path = persisted_sched.as_node_url()
                        fsplit = from_path.split('/')
                        fsplit[-1] = name
                        to_path = '/'.join(fsplit)
                        # update the link to the schedule that it proxies.
                        cd = persisted_sched.configuration()
                        cd['proxy'] = schedule
                        persisted_sched.configure(cd)
                        self.move_schedule(from_path, to_path, 1)
                    self._proxied_manager.register_active(host_url, uuid, schedule)
                else:
                    new_schedule = ProxiedHierarchialScheduler()
                    cd = {'name':name,
                          'parent':self,
                          'proxy':schedule,
                          'host_url':host_url,
                          'uuid':uuid}
                    new_schedule.configure(cd)
                    nodepath = new_schedule.as_node_url()
                    PERSISTANCE_MANAGER.put_sched(
                        nodepath, serialize_node(new_schedule)
                        )
                    new_schedule.start()
                    new_schedule.set_host(host)
                    self._proxied_manager.register_new(host_url, uuid, new_schedule)
                    persisted_sched = new_schedule
                persisted_sched.refresh_children_names()
            except:
                msglog.exception()
        self._proxied_manager.prune_inactive(host_url)
        self._proxied_manager.clear_active(host_url)
            
    def message(self, message, mtype=msglog.types.INFO, level=1):
        if self.debug >= level:
            msglog.log('Scheduler', mtype, message)
            
    ##
    # Create a new schedule
    # 
    # @param name   The schedules name
    # @param parent  The uri of the parent where this schedule should be attached.
    # @return  None
    security.protect('create_schedule', 'Configure') 
    def create_schedule(self, name, parent):
    	'''create a schedule'''
        parent = self._get_schedule_node(parent)
        schedule = HierarchialScheduler()
        cd = {'name':name,
              'parent':parent}
        schedule.configure(cd)
        nodepath = schedule.as_node_url()
        PERSISTANCE_MANAGER.put_sched(nodepath, serialize_node(schedule))
        if parent is not self:
            # do not change override status
            schedule._set_summary(parent.get_summary())
        else:
            schedule.set_override(True)
        schedule.start()
        PERSISTANCE_MANAGER.put_sched_summary(nodepath, schedule.get_summary())
        self.event_generate(
            ScheduleCreatedEvent(self, schedule)
            )
        
    ##
    # Removes a schedule from the scheduling hiearchy
    # 
    # @param schedule   The uri of the schedule to be removed.
    # @return  None 
    security.protect('remove_schedule', 'Configure')
    def remove_schedule(self, schedule, force=0):
        if type(schedule) is types.ListType:
            schedule.sort(sched_sort)
            schedule.reverse()
            exceptions = {}
            for sched in schedule:
                try:
                    sched = self._get_schedule_node(sched)
                    self.remove_schedule(sched, force)
                except Exception, e:
                    exceptions[sched.as_node_url()] = str(current_exception())
            if exceptions:
                raise EBatchedException('remove_schedule', exceptions)
            return
        schedule = self._get_schedule_node(schedule)
        # the order here matters, not force should be checked before 
        # get_meta() call.  This could be cleaning up b\c remote schedule is
        # gone.
        if not force and schedule.get_meta().get('immutable'):
            err_msg = 'Runtime removal of schedule %s is not supported' % schedule.name
            raise EImmutable(err_msg)
        if not isinstance(schedule, ProxiedHierarchialScheduler):
            for child_sched in schedule.children_schedules():
                # re-parent schedule
                self.move_schedule(child_sched, schedule.parent)
        schedule_url = schedule.as_node_url()
        self.__last_pruned = schedule
        try:
            PERSISTANCE_MANAGER.remove_sched(schedule.as_node_url())
        except:
            msglog.exception()
        schedule.prune()
        self.event_generate(
            ScheduleRemovedEvent(self, schedule_url)
            )
        
    ##
    # Move a schedule to a new parent within the scheduling hierarchy.  
    # By default this schedule will now be in the overridden state until 
    # explicitly releases so that it might inherit the new schedule.
    # 
    # @param source   The schedule to move
    # @param destination  The new parent.
    # @return  A dictionary, keyed by the name of the property, and the value 
    # being a ResultObject
    security.protect('move_schedule', 'Configure')
    def move_schedule(self, source, destination, force=0):
        if type(source) is types.ListType:
            source.sort(sched_sort)
            source.reverse()
            exceptions = {}
            for sched in source:
                try:
                    sched = self._get_schedule_node(sched)
                    self.move_schedule(sched, destination, force)
                except Exception, e:
                    exceptions[sched.as_node_url()] = str(current_exception())
            if exceptions:
                raise EBatchedException('remove_schedule', exceptions)
            return
        if self._is_rename(source, destination):
            return self._rename_schedule(source, destination, force)
        source_sched = self._get_schedule_node(source)
        source_sched.set_override(True)
        orig_sched_path = source_sched.as_node_url()
        dest_sched = self._get_schedule_node(destination)
        if dest_sched.has_child(source_sched.name):
            raise ENameInUse(source_sched.name)
        dest_sched_path = dest_sched.as_node_url()
        cd = source_sched.configuration()
        cd['parent'] = dest_sched
        source_sched.configure(cd)
        try:
            PERSISTANCE_MANAGER.move_sched(
                orig_sched_path, 
                dest_sched.as_node_url(), 
                serialize_node(source_sched)
                )
        except:
            msglog.exception()
        if dest_sched is self:
            source_sched.set_override(True)
        source_sched.stop()
        source_sched.start()
        self.event_generate(
            ScheduleMovedEvent(self, source_sched, orig_sched_path, dest_sched_path)
            )
            
    def _is_rename(self, source, destination):
        if is_node(source):
            return source is destination
        s_elements = source.split('/')
        d_elements = destination.split('/')
        if len(s_elements) == len(d_elements) and s_elements[:-1] == d_elements[:-1]:
            try:
                self._get_schedule_node(destination)
            except:
                return True
        return False
    
    def _rename_schedule(self, source, destination, force=0):
        source_sched = self._get_schedule_node(source)
        if not force and source_sched.get_meta().get('immutable'):
            err_msg = 'Runtime renaming of schedule %s is not supported' % source_sched.name
            raise EImmutable(err_msg)
        new_name = destination.split('/')[-1]
        orig_sched_path = source_sched.as_node_url()
        cd = source_sched.configuration()
        cd['name'] = new_name
        source_sched.configure(cd)
        try:
            PERSISTANCE_MANAGER.move_sched(
                orig_sched_path,
                source_sched.as_node_url(),
                serialize_node(source_sched),
                True
                )
        except:
            msglog.exception()
            
    def _get_schedule_node(self, schedule):
        if is_node(schedule):
            return schedule
        if not type(schedule) in types.StringTypes:
            raise EInvalidValue('schedule', schedule, 'expected node reference')
        schedule = urllib.unquote(schedule)
        if (not urllib.unquote(self.as_node_url()) in schedule) and \
            schedule.startswith('/') and len(schedule) > 1:
            # nodepath is relative.
            schedule = schedule[1:]
        if schedule == '/':
            # still relative - for schedules the ScheduleManager is the root.
            schedule = self
        return self.as_node(schedule)
    
    ##
    # Retrieve a list of children objects that are based in the 
    # HierarchialScheduler class.
    # 
    # @param parent   An optional parent that indicates the root
    # @return  A list of objects that are instances of HierarchialScheduler
    # objects 
    security.protect('children_schedules', 'View')
    def children_schedules(self, parent=None):
        if parent is None:
            parent = self
        else:
            parent = self._get_schedule_node(parent)
        scheds = []
        return [x for x in parent.children_nodes() if \
                isinstance(x, (HierarchialScheduler,ProxiedHierarchialScheduler))]

    ##
    # Retrieve a list of the names of the children of this node that are based 
    # on the HierarchialScheduler class.
    # 
    # @param parent   An optional parent that indicates the root
    # @return  A list of names that are instances of HierarchialScheduler
    # objects 
    security.protect('children_schedule_names', 'View')
    def children_schedule_names(self, parent=None):
        return [x.name for x in self.children_schedules(parent)]
    
    ##
    # The following methods are delegated to a schedule.  The api
    # matches that of the Scheduler class (or those derived from).
    security.protect('get_summary', 'View')
    def get_summary(self, schedule):
        return self._get_schedule_node(schedule).get_summary()
    
    security.protect('set_summary', 'Configure')
    def set_summary(self, schedule, value):
        self._get_schedule_node(schedule).set_summary(value)
        
    security.protect('get_override', 'View')
    def get_override(self, schedule):
        schedule = self._get_schedule_node(schedule)
        if schedule is self:
            return True
        return self._get_schedule_node(schedule).get_override()
    
    security.protect('set_override', 'Configure')
    def set_override(self, schedule, override):
        self._get_schedule_node(schedule).set_override(override)
    
    security.protect('release_override', 'Configure')
    def release_override(self, schedule):
        self._get_schedule_node(schedule).release_override()
        
    security.protect('get_meta', 'View')
    def get_meta(self, schedule):
        return self._get_schedule_node(schedule).get_meta()
        
    security.protect('get_properties', 'View')
    def get_properties(self, schedule):
        return self._get_schedule_node(schedule).get_properties()
    
    security.protect('set_properties', 'Configure')
    def set_properties(self, schedule, properties):
        self._get_schedule_node(schedule).set_properties(properties)
    
    security.protect('get_event_meta', 'View')
    def get_event_meta(self, schedule):
        return self._get_schedule_node(schedule).get_event_meta()

    security.protect('set_event_meta', 'Configure')
    def set_event_meta(self, schedule, event_data):
        self._get_schedule_node(schedule).set_event_meta(event_data)
        
    def get_entity_root(self, schedule):
        return self._get_schedule_node(schedule).get_entity_root()
    
    def _get_host_manager(self):
        if self._hm is None:
            for child in as_node('/services').children_nodes():
                if isinstance(child, NBMManager):
                    self._hm = child
                    break
        return self._hm
    
    host_manager = property(_get_host_manager)
    
    def _get_ctlsvc(self):
        from mpx.service.control.control import Control
        if self._ctlsvc is None:
            for service in as_node('/services').children_nodes():
                if isinstance(service, Control):
                    self._ctlsvc = service
                    break
        return self._ctlsvc
    
    ctlsvc = property(_get_ctlsvc)

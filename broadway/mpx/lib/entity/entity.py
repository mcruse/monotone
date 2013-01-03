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
from mpx.componentry import implements
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.node import is_node
from mpx.lib.node import Alias
from mpx.lib.node import NodeProxy
from mpx.lib.node.interfaces import IAliasNode
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import as_boolean

from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import EAttributeError
from mpx.lib.exceptions import ENotRunning
from mpx.lib.exceptions import ETimeout

from mpx.lib.threading import Lock

from mpx.lib.event import EventConsumerMixin

#for BACnet units enumeration
from mpx.lib.bacnet.datatype import BACnetEngineeringUnits 

from mpx.lib import threading
from mpx.lib import msglog
from mpx.lib import ReloadableSingletonFactory

from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation

from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM

from mpx.service.control.graphical import TemplateInstanceNode
from mpx.service.control.graphical import TimeScheduleInstanceNode
from mpx.service.control.graphical import TrendTemplateInstanceNode
from mpx.service.control.graphical import AlarmTemplateInstanceNode
from mpx.service.control.graphical import MacroTemplateInstanceNode

from mpx.service.network.bacnet.BIN import BACnet
from mpx.service.network.bacnet.BIN import BINObjectInstance 

from mpx.service.schedule.bacnet_scheduler import Scheduler as \
    BACnetSchedulerIface

from mpx.service.cloud.hosts import NBMManager

from overridable import OverrideMixin
from overridable import OverrideDict

from properties import PropertyDefinition
from properties import EntityProp
from properties import PTYPE_MAP
from properties import BAC_PTYPE_MAP
from properties import POINTS
from properties import COMMANDABLE
from properties import SCHEDULES
from properties import ALARMS
from properties import LOGS

from types import StringType 

import urllib
BAC_ACTIVE_TEXT = '4'
BAC_DESCRIPTION = '28'
BAC_INACTIVE_TEXT = '46'
BAC_NAME = '77'
BAC_PRIORITY_ARRAY = '87'
BAC_RELINQUISH_DFLT = '104'
BAC_UNITS = '117'

Defined = object()
Undefined = object()
debug = 0

def as_entity_url(node):
    alias_root = ENTITY_MANAGER.get_alias_root().as_node_url()
    url = urllib.unquote(node.as_node_url()[len(alias_root):])
    if not url.startswith('/'):
        url = '/' + url
    return url

def wrapped(func, pre, post):
    def wrapper(*args, **kwargs):
        if pre is not None:
            try:
                pre()
            except:
                msglog.exception()
        retval = func(*args, **kwargs)
        if post is not None:
            try:
                post()
            except:
                msglog.exception()
        return retval
    return wrapper

class Manager(CompositeNode):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self):
        CompositeNode.__init__(self)
        self._mount_points = []
        self._start_scheduler = None
        self._alias_root = None
        
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'manage_aliases', 1, cd, int)

    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'manage_aliases', cd)
        return cd
    
    # note: Manager starts entities that are located below the Aliases
    # branch.  Normally start is not called on nodes that are descendents of
    # /aliases.  To minimize start order 
    def start(self):
        self._alias_root = as_node('/aliases')
        # if the NBM supports BACnet, defer start up of entity infrastructure
        # until BACnet starts.
        for node in as_node('/services/network').children_nodes():
            if isinstance(node, BACnet):
                if not node.is_running():
                    # see if this function is already wrapped.  If it is wrapped
                    # im_self is not an attribute.
                    if hasattr(node.start, 'im_self'):
                        node.start = wrapped(node.start, None, self.do_start)
                    return
        self.do_start()
        
    def do_start(self):
        if not self.is_running():
            CompositeNode.start(self)
        
    security.protect('create_polled', 'View')
    def create_polled(self, node_reference_table=None, timeout=300):
        if node_reference_table is None:
            node_reference_table = {}
            for mount_point, nodepath in self.get_mount_points():
                try:
                    node_reference_table[nodepath] = mount_point.host
                except:
                    msg = 'Failed to establish presence monitoring for %s' % nodepath
                    msglog.log('Entity Manager', msglog.types.WARN, msg)
        return SM.create_polled(node_reference_table, timeout)
    
    def update_hosts_status(self):
        for mount_point, nodepath in self.get_mount_points():
            mount_point.host.skip_cache()
            
    def register_mount_point(self, mount_point, nodepath):
        self._mount_points.append((mount_point, nodepath))
        
    def get_mount_points(self):
        return self._mount_points
    
    def get_alias_root(self):
        return self._alias_root
    
    security.protect('destroy', 'View')
    def destroy(self, sid):
        return SM.destroy(sid)
        
    security.protect('poll_all', 'View')
    def poll_all(self, sid):
        return SM.poll_all(sid)
                
    security.protect('poll_changed', 'View')
    def poll_changed(self, sid):
        return SM.poll_changed(sid)
    
    def get_entities(self, root=None):
        if root == '/' or root is None:
            root = self
        elif root.startswith('/'):
            root = self.as_node(root[1:])
        else:
            root = self.as_node(root)
        return [x for x in root.children_nodes() if \
            isinstance(x, EntityTypes)]
            
    def get_entities_name(self, root=None):
        return [x.name for x in self.get_entities(root)]
    
    def get_entity_names_for_ui(self, root=None):
        return [entity.name for entity in self.get_entities(root)]

    # following methods are partially delegated to alias root
    def children_nodes(self, **options):
        return self._alias_root.children_nodes(**options) + \
            CompositeNode.children_nodes(self, **options)
    
    def children_names(self, **options):
        return self._alias_root.children_names(**options) + \
            CompositeNode.children_names(self, **options)
    
    def get_child(self, name, **options):
        try:
            return CompositeNode.get_child(self, name, **options)
        except:
            return self._alias_root.get_child(name, **options)
    
    def has_child(self, name, **options):
        return self._alias_root.has_child(name, **options) or \
            CompositeNode.has_child(self, name, **options)
            
    def has_children(self):
        return self._alias_root.has_children() or \
            CompositeNode.has_children(self)
            
    def resolve_mount_paths(self, entity_path):
        from_path = ''
        to_path = ''
        try:
            entity = as_node(entity_path)
            if isinstance(entity, EntityTypes) and entity.is_remote():
                mp = entity.get_mount_point()
                from_path = mp.configuration().get('mountpoint')
                if not from_path.endswith('/'):
                    # adding slash to avoid bad replaces.  They are urls
                    # so a trailing / is safer.
                    from_path += '/'
                to_path = mp.as_node_url()
                if not to_path.endswith('/'):
                    to_path += '/'
        except:
            pass
        return [from_path, to_path]
    
    def singleton_unload_hook(self):
        pass

ENTITY_MANAGER = ReloadableSingletonFactory(Manager)

def manager_factory():
    return ENTITY_MANAGER

class ProxyMixin(object):
    implements(IAliasNode)
    def __init__(self):
        self.__subject_url = None
        self.__subject = None
        self.__mount_point = None
        
    def set_mount_point(self, mount_point):
        self.__mount_point = mount_point
        
    def get_mount_point(self):
        if self.__mount_point is None:
            if hasattr(self.parent, 'get_mount_point'):
                self.set_mount_point(self.parent.get_mount_point())
        return self.__mount_point
    
    def is_remote(self):
        mp = None
        if isinstance(self, MountPoint):
            mp = self.get_mount_point()
        elif hasattr(self.parent, 'get_mount_point'):
            mp = self.parent.get_mount_point()
        if mp is None:
            return False
        self.set_mount_point(mp)
        return True
    
    def get_subject(self):
        if self.__subject is None:
            if self.is_remote():
                self.set_subject(as_node(self.as_remote_url()))
            else:
                self.set_subject(self)
        return self.__subject
    
    def dereference(self, recursive=True):
        return self.get_subject()
    
    def set_subject(self, subject):
        self.__subject = subject
        
    def set_remote_url(self, url):
        self.__subject_url = url
        
    def as_remote_url(self):
        if self.__subject_url is None:
            mp = self.parent.get_mount_point()
            if mp is not None:
                self.set_mount_point(mp)
                self.set_remote_url(self.parent.as_remote_url() +'/'+self.name)
            else:
                self.set_remote_url(self.as_node_url())
        return self.__subject_url
 
class EntityContainer(CompositeNode, ProxyMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        ProxyMixin.__init__(self)
        self._properties = []
        
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'display', '', cd)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'display', cd)
        return cd
    
    def start(self):
        if self.is_remote():
            e_prop = EntityProp(
                name='Entity', 
                type='Entity', 
                label='',
                description='',
                url=self.display,
                entity=as_entity_url(self)
            )
            self._properties = [e_prop.as_dict()]
        CompositeNode.start(self)
        
    def get_property_list(self):
        return self._properties
     
    def create_polled(self, node_reference_table=None, timeout=300):
        pass
        
    def destroy(self, sid):
        pass
        
    def poll_all(self, sid):
        return {}
                
    def poll_changed(self, sid):
        return {}
    
    def get_display(self):
        return self.display
        
    def get_entities(self):
        return [x for x in self.children_nodes() if \
            isinstance(x, EntityTypes)]
            
    def get_entities_name(self):
        return [x.name for x in self.get_entities()]

class MetaRegistry(dict):
    def __setitem__(self, name, value):
        self.register(name, value)
            
    def register(self, name, value):
        if not dict.has_key(self, name):
            dict.__setitem__(self, name, [])
        if not value in self[name]:
            if isinstance(value, (list, tuple)):
                self[name].extend(value)
            else:
                self[name].append(value)
        
    def get_registered_meta_names(self):
        return self.keys()
    
    def get_registered_meta_values(self, name):
        return self.get(name, [])
    
    def singleton_unload_hook(self):
        pass

META_REGISTRY = ReloadableSingletonFactory(MetaRegistry)

class MetaMixin(object):
    def __init__(self, *args, **kw):
        self.meta = {}
        super(MetaMixin, self).__init__(*args, **kw)
        
    def has_meta_value(self, name, value):
        if isinstance(value, str):
            value = value.lower()
        return value in self.get_meta_values(name, set())
    
    def get_meta_values(self, name, default=Undefined):
        name = name.lower()
        values = self.meta.get(name, default)
        if values is Undefined:
            raise KeyError(name)
        return values
    
    def set_meta_values(self, name, values):
        self.meta[name.lower()] = set(values)
        
    def add_meta_value(self, name, value):
        if isinstance(value, str):
            value = value.lower()
        name = name.lower()
        self.meta.setdefault(name, set()).add(value)
        META_REGISTRY.register(name, value)
        
    def pop_meta_value(self, name, value):
        values = self.get_meta_values(name, set())
        if isinstance(value, str):
            value = value.lower()
        popped = value in values
        values.discard(value)
        if not values:
            self.meta.pop(name.lower())
        return popped
    
    def configure_meta(self, meta):
        # Support both meta-dictionary and config-tool list types.
        self.clear_meta()
        try:
            if isinstance(meta, (list, tuple)):
                for item in meta:
                    self.add_meta_value(item["name"], item["value"])
            else:
                for name,values in meta.items():
                    self.set_meta_values(name, values)
        except:
            msglog.exception()
                
    def clear_meta(self):
        self.meta.clear()

class Entity(CompositeNode, ProxyMixin, MetaMixin):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self):
        CompositeNode.__init__(self)
        ProxyMixin.__init__(self)
        MetaMixin.__init__(self)
        # consideration: memory utilization.  This really is redundant,
        # since the properties are also mapped into the node tree.
        self._properties = {}
        self._properties_list = []
        self._properties_loaded = False
        self._load_lock = Lock()
        self.__security_manager = None
                
    def configure(self, cd):
        set_attribute(self, 'display', '', cd)
        set_attribute(self, 'visible', '1', cd,as_boolean)
        if "meta" in cd:
            self.configure_meta(cd["meta"])
        CompositeNode.configure(self, cd)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'display', cd)
        get_attribute(self,'visible',cd)
        return cd
        
    def start(self):
        # the entity property is a special case.  It should show up
        # in the property list, but isn't necessarily represented in the node
        # tree the way normal properties are.
        e_prop = EntityProp(
            name='Entity', 
            type='Entity', 
            label='',
            description='',
            url=self.display,
            entity=self.as_node_url()
        )
        self.add_property(e_prop)
        if not self.is_remote():
            self.set_subject(self)
            self._load_properties()
        else:
            mp = self.get_mount_point()
            try:
                subject = mp.as_remote_node(self.as_remote_url())
                self.set_subject(subject)
            except:
                msglog.exception()
        CompositeNode.start(self)
                    
    def get_entities(self):
        return [x for x in self.children_nodes() if \
            isinstance(x, EntityTypes)]
            
    def get_entities_name(self):
        return [x.name for x in self.get_entities()]

    def get_entity_names_for_ui(self, root=None):
        return [entity.name for entity in self.get_entities() if entity.visible]

    def get_display(self):
        return self.display
    
    def _load_properties(self):
        self._load_lock.acquire()
        try:
            if self._properties_loaded:
                return
            for prop_container in self.children_nodes():
                if not isinstance(prop_container, PropertyContainer):
                    continue
                for prop in prop_container.children_nodes():
                    as_prop = prop.as_property()
                    self._properties[(prop_container.ptype, prop.name)] = as_prop
                    as_prop_d = as_prop.as_dict()
                    if not as_prop_d in self._properties_list:
                        self._properties_list.append(as_prop_d)
            self._properties_loaded = True
        finally:
            self._load_lock.release()

    def get_property_containers(self):
        nodes = self.children_nodes()
        return [node for node in nodes if isinstance(node, PropertyContainer)]
    
    def get_property_count(self):
        return len(self._properties)
    
    def add_property(self, prop):
        self._properties[(prop.type, prop.name)] = prop
        self._properties_list.append(prop.as_dict())
        
    security.protect('get_property_list', 'View')
    def get_property_list(self):
        if not self._properties_loaded:
            self._load_properties()
        return self._properties_list
 
    def get_property_ref(self, ptype, name):
        if not self._properties_loaded:
            self._load_properties()
        return self._properties.get((ptype, name)).reference
        
    def get_property(self, ptype, name):
        return self.get_property_ref(ptype, name).get()
        
    def get_property_multiple(self, prop_list):
        result = {}
        for ptype, name in prop_list:
            try:
                result[(ptype, name)] = self.get_property(ptype, name)
            except Exception, e:
                result[(ptype, name)] = e
        return result
        
    def get_override(self, ptype, name):    
        return self.get_subject()._get_override(ptype, name)
    
    # only external (f.e, xml-rpc) callers should use this method
    def get_writeable_list(self, user=None):
        if not self._properties_loaded:
            self._load_properties()
        writeable = []
        for point in self._get_commandable():
            try:
                # the point parent is purposely interacted with to preserve
                # security context in the case where the property is referencing
                # a remote point.
                point_parent = self.security_manager.as_secured_node(
                    point.reference.parent, user=user
                    )
                point = point_parent.get_child(point.name)
            except:
                continue
            if hasattr(point, 'set'):
                writeable.append((point.type, point.name))
        return writeable
    
    def _get_override(self, ptype, name):
        # @fixme - tie into edtlib and remove as_dict.
        ovr = self.get_property_ref(ptype, name).get_override()
        if hasattr(ovr, 'as_dict'):
            ovr = ovr.as_dict()
        return ovr
    
    security.protect('override_property', 'Override')
    def override_property(self, ptype, name, override):
        return self.get_subject()._override_property(ptype, name, override)
    
    def _override_property(self, ptype, name, override):
        default = override.get('default')
        self.get_property_ref(ptype, name).override(
            OverrideDict(override, default)
        )
        
    security.protect('release_property', 'Override')
    def release_property(self, ptype, name, level):
        return self.get_subject()._release_property(ptype, name, level)
    
    def _release_property(self, ptype, name, level):
        self.get_property_ref(ptype, name).release(level)
                
    security.protect('create_polled', 'View')
    def create_polled(self, node_reference_table=None, timeout=300):
        if not self._properties_loaded:
            self._load_properties()
        if node_reference_table is None:
            node_reference_table = {}
            points = self._get_points()
            for point in points:
                node_reference_table[str((point.ptype, point.name))] = point.reference       
        return SM.create_polled(node_reference_table, timeout)
    
    security.protect('destroy', 'View')
    def destroy(self, sid):
        return SM.destroy(sid)
    
    security.protect('poll_all', 'View')
    def poll_all(self, sid):
        return SM.poll_all(sid)
    
    security.protect('poll_changed', 'View')
    def poll_changed(self, sid):
        return SM.poll_changed(sid)
    
    security.protect('get_alarm_summary', 'View')
    def get_alarm_summary(self):
        return [x.name for x in self._get_alarms() if x.reference.get()]
        
    def _get_points(self):
        return self._get_instances(POINTS)
    
    def _get_commandable(self):
        return [x for x in self._get_points() if type(x) in COMMANDABLE]
    
    def _get_schedules(self):
        return self._get_instances(SCHEDULES)
        
    def _get_alarms(self):
        return self._get_instances(ALARMS)
        
    def _get_logs(self):
        return self._get_instances(LOGS)
        
    def _get_names(self, obj_list):
        return [x.name for x in obj_list]
                
    def _get_instances(self, obj_type):
        return [x for x in self._properties.values() if \
                isinstance(x, obj_type)]
           
    def _public_interface(self):
        return self
    
    def _get_security_manager(self):
        if self.__security_manager is None:
            try:
                self.__security_manager = as_node('/services/Security Manager')
            except:
                msg = 'Error obtaining reference to Security Manager'
                msglog.log('Entity Manager', msglog.types.WARN, msg)
        return self.__security_manager
    
    security_manager = property(_get_security_manager)
    
class MountPoint(Entity):
    def __init__(self):
        Entity.__init__(self)
        self._nbm_manager = None
        self.__host = None
        
    def configure(self, cd):
        Entity.configure(self, cd)
        set_attribute(self, 'hostname', 'localhost', cd)
        set_attribute(self, 'mountpoint', '/aliases', cd)
        if self.mounts_remote():
            if self.mountpoint != '/' and self.mountpoint[-1] == '/':
                self.mountpoint = self.mountpoint[:-1]
            self.set_remote_url(self.mountpoint)
            self.set_mount_point(self)

    def configuration(self):
        cd = Entity.configuration(self)
        get_attribute(self, 'hostname', cd)
        get_attribute(self, 'mountpoint', cd)
        return cd
    
    def start(self):
        if self.mounts_remote():
            url = as_entity_url(self)
            self.host.set_entity_root(url)
            ENTITY_MANAGER.register_mount_point(self, url)
        Entity.start(self)
        
    def mounts_remote(self):
        return self.hostname and self.hostname != 'localhost'
            
    def as_remote_node(self, path):
        # delegates to NBM Manager service
        if self.mounts_remote():
            return self.host.as_remote_node(path)
        return None
        
    def get_entity_root(self):
        return self.__entity_root
        
    def _get_host(self):
        if self.__host is None:
            for service in as_node('/services').children_nodes():
                if isinstance(service, NBMManager):
                    self.__host = service.get_host(self.hostname)
                    break
            if self.__host is None:
                err_msg = 'Invalid configuration: NBM Manager is missing host %s' \
                % self.hostname
                raise EConfiguration(err_msg)
        return self.__host
    host = property(_get_host)
    
        
class PropertyContainer(CompositeNode, ProxyMixin):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self):
        CompositeNode.__init__(self)
        ProxyMixin.__init__(self)
            
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'ptype', REQUIRED, cd)
          
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'ptype', cd)
        return cd
    
    security.protect('get_properties', 'View')
    def get_properties(self, filters=()):
        """
            Get list of properties that have meta data matching 
            any of the values in the provided name/value pairs.
        """
        matches = []
        filters = dict(filters).items()
        properties = set(self.children_nodes())
        while properties and filters:
            name,values = filters.pop()
            for property in list(properties):
                metavalues = property.get_meta_values(name, set())
                if metavalues.intersection(values):
                    matches.append(property)
                    properties.remove(property)
        return matches
       
class Property(CompositeNode, ProxyMixin, MetaMixin):
    security = SecurityInformation.from_default()
    secured_by(security)
    def __init__(self, node_url=None):
        # initialize _children dict here to avoid __getattr__ sending it to
        # the linked node and then mixing the children of this property,
        # (ie. the Priority Array child) into the children of the linked node
        # also prevents unintended appearance of the linked node's children
        # under this Entity node
        self._children = {}  
        CompositeNode.__init__(self)        
        ProxyMixin.__init__(self)
        MetaMixin.__init__(self)
        self.node_url = node_url
        self._running = False
        self.__as_property = None
        self._outstanding_attributes = []
        self._configured = False #True
        self._subject = None
        self._entity = None
   
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        if self.is_remote():
            cd['node_url'] = self.as_remote_url()
            self.set_remote_url(cd['node_url'])
        if not cd.has_key('type'):
            cd['type'] = self.parent.ptype
        for attr in PTYPE_MAP.get(self.parent.ptype)().supported_attrs():
            set_attribute(self, attr, '', cd)
        if self.node_url:
            cd['node_url'] = self.node_url #auto-discover
        if "meta" in cd:
            self.configure_meta(cd["meta"])
        set_attribute(self, 'node_url', REQUIRED, cd)
        self._configured = True
    
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self, 'node_url', cd)
        if not self.is_remote():
            for attr in PTYPE_MAP.get(self.parent.ptype)().supported_attrs():
                get_attribute(self, attr, cd)            
        return cd
                
    def start(self):
        # We don't want to call start on remote, thus avoid calling superclasses
        # start.
        self._running = True
        
    def stop(self):
        self._running = False
        
    def is_running(self):
        return self._running
    
    def as_property(self):
        if self.__as_property is None:
            prop_map = {}
            prop_class = PTYPE_MAP.get(self.parent.ptype)
            for attr in prop_class().supported_attrs():
                prop_map[attr] = getattr(self, attr)
            prop_map['reference'] = self.as_node_url()
            self.__as_property = prop_class(**prop_map)
        return self.__as_property
    
    def get_child(self, name, **options):
        options['auto_discover'] = False
        return CompositeNode.get_child(self, name, **options)
        
    def has_child(self, name, **options):
        options['auto_discover'] = False
        return CompositeNode.has_child(self, name, **options)
    
    ##
    # @ fixme - this is a recipe for problems.  We should explicitly delegate
    # to subject rather than that being the default.
    def has_cov(self):
        supports_cov = False
        if not self.is_remote():
            try:
                sub = self.get_subject()
                if hasattr(sub, 'has_cov') and sub.has_cov():
                    supports_cov = True
            except:
                pass
        return supports_cov
    
    def changing_cov(self):
        changing_cov = False
        if not self.is_remote():
            try:
                sub = self.get_subject()
                if hasattr(sub, 'changing_cov') and sub.changing_cov():
                    changing_cov = True
            except:
                pass
        return changing_cov
    
    def _public_interface(self):
        return self
    
    def nodecmp(a,b):
        return cmp(a, b)
    
    def __getattr__(self, name):
        if self._configured:
            subject = self.get_subject()
            if hasattr(subject, name):
                return getattr(subject, name)
        raise AttributeError(name)
    
    def get_subject(self):
        if self._subject is None:
            mp = self.get_mount_point()
            if mp is not None:
                self._subject = mp.as_remote_node(self.node_url)
            else:
                self._subject = as_node(self.node_url)
                if isinstance(self._subject, BINObjectInstance):
                    if self._subject.parent.name == '17':
                        # a reference to a bacnet scheduled embedded
                        # in a device.
                        cd = {'name':'Scheduler', 
                              'parent':self, 
                              'source':'broadway', 
                              'link':self.node_url}
                        sched_instance = BACnetSchedulerIface()
                        sched_instance.configure(cd)
                        self._subject = sched_instance
            self.set_subject(self._subject)
        return self._subject
    
    def _get_entity(self):
        if self._entity is None:
            self._entity = self.parent.parent
        return self._entity
    
    entity = property(_get_entity)
    
    def nodebrowser_handler(self, nb, path, node, node_url):
        if self.node_url is None:
            return nb.get_default_view(node, node_url)
        #create html for link to nodebrowser node_url
        block = ['<div class="node-section node-link">']
        block.append('<h2 class="section-name">Node Link</h2>')
        block.append('<ul class="node-link">')
        block.append('<li>')
        s = 'nodebrowser' + self.node_url
        block.append('<a href="/%s">/%s</a><br>' %(s,s))
        block.append("</li>\n</ul>")
        block.append("</div>")
        node_link = "\n".join(block)
        # get default dict from node browser and add link
        dct = nb.get_default_presentation(node, node_url)
        dct['node-link'] = node_link
        # answer the html for the modified node browser page
        return '''    %(node-hierarchy)s
     %(node-name)s
     %(node-link)s
     %(node-children)s
     %(node-configuration)s
     %(node-persistence)s''' % dct

class BACnetProperty(Property):
    bacnet_attrs = ('name', 'description', 'units', 'enumeration')    
    def configure(self, cd):
        Property.configure(self, cd)
        if self.is_remote():
            return
        for attr in PTYPE_MAP.get(self.parent.ptype)().supported_attrs():
            value = ''
            if attr in bacnet_attrs:
                try:
                    value = self._get_bacnet_attr(attr)
                except:
                    pass
            set_attribute(self, attr, value, cd)
            
    def configuration(self):
        cd = Property.configuration(self)
        if not self.is_remote():
            for attr in PTYPE_MAP.get(self.parent.ptype)().supported_attrs():
                get_attribute(self, attr, cd)
        return cd
    
    def _get_bacnet_attr(self, attr):
        subject = self.get_subject()
        if attr == 'name':
            value = subject.get_child(BAC_NAME).get()
        elif attr == 'description':
            value = subject.get_child(BAC_DESCRIPTION).get()
        elif attr == 'units':
            units = subject.get_child(BAC_UNITS).get()
            value = BACnetEngineeringUnits._enumeration_string_map.get(units)
        elif attr == 'enumeration':
            inactive = subject.get_child(BAC_INACTIVE_TEXT)
            active = subject.get_child(BAC_ACTIVE_TEXT).get()
            value = (inactive, active)
        else:
            value = ''
        return value

class OverridableProperty(Property, OverrideMixin):
    security = SecurityInformation.from_default()
    secured_by(security)
    implements(IAliasNode)
    def __init__(self): 
        Property.__init__(self)
        OverrideMixin.__init__(self)
        self._start_failed = False
        
    def start(self):
        if not self.has_child('_status'):
            status = StatusNode()
            status.configure({'name':'_status', 'parent':self})
        if not self.is_remote():
            try:
                subject = self.get_subject()
            except:
                # we're unable to reference the subject - it could be a commandable
                # bacnet property - until we know for sure, raise ENotRunning
                self._start_failed = True
                return
            if isinstance(subject, BINObjectInstance): 
                try:
                    # confirm that it is in fact, commandable
                    subject.get_child('87').get()
                except:
                    self.restore_override()
                else:
                    self.__class__ = BACnetOverrideableProperty
                    BACnetOverrideableProperty.start(self)
            else:
                self.restore_override()
        self._start_failed = False
        Property.start(self)
                    
    def is_running(self):
        run_status = Property.is_running(self)
        if not run_status:
            if self._start_failed:
                self.start()
                run_status =  Property.is_running(self)  
        return run_status
    
    def set(self, value):
        if self.is_remote():
            self.get_subject().set(value)
        else:
            self.override(value, 16)
        
    def set_proxy(self, value):
        self.get_subject().set(value)
        
    security.protect('get_override', 'View')
    def get_override(self):
        if self.is_remote():
            return self.get_subject().get_override()
        if not self.is_running():
            raise ENotRunning()
        return OverrideMixin.get_override(self)
    
    security.protect('override', 'Override')
    def override(self, value, level=16):
        if self.is_remote():
            return self.get_subject().override(value, level)
        if not self.is_running():
            raise ENotRunning()
        return OverrideMixin.override(self, value, level)
        
    security.protect('release', 'Override')
    def release(self, level):
        if self.is_remote():
            return self.get_subject().release(level)
        if not self.is_running():
            raise ENotRunning()
        return OverrideMixin.release(self, level)
       
    security.protect('get_override_at', 'View')
    def get_override_at(self, level):
        if self.is_remote():
            return self.get_subject().get_override_at(level)
        if not self.is_running():
            raise ENotRunning()
        return OverrideMixin.get_override_at(self, level)
       
    security.protect('get_write_priority', 'View')
    def get_write_priority(self):
        if self.is_remote():
            return self.get_subject().get_write_priority(self)
        if not self.is_running():
            raise ENotRunning()
        return OverrideMixin.get_write_priority(self)
    
    security.protect('set_default', 'Override')
    def set_default(self, value):
        if self.is_remote():
            return self.get_subject().set_default(value)
        if not self.is_running():
            raise ENotRunning()
        return OverrideMixin.set_default(self, value)
    
    security.protect('get_default', 'View')
    def get_default(self):
        if self.is_remote():
            return self.get_subject().get_default()
        return OverrideMixin.get_default(self)
    
    def _get_override(self):
        if self.is_remote():
            return self.get_subject()._get_override()
        return OverrideMixin.get_override(self)
    
    def get_subject(self):
        if self._subject is None:
            self._subject = Property.get_subject(self)
        return self._subject
        
class BACnetOverrideableProperty(BACnetProperty):
    security = SecurityInformation.from_default()
    secured_by(security)
    implements(IAliasNode)
    def start(self):
        if not self.has_child('Priority Array'):
            pa = NodeProxy()
            cd = {'name':'Priority Array',
                  'parent':self,
                  'node_url':self.get_subject().get_child(BAC_PRIORITY_ARRAY).as_node_url()}
            pa.configure(cd)
            pa.start()
        self.priority_array = self.get_child('Priority Array')
        BACnetProperty.start(self)

    def set(self, value):
        self.get_subject().set(value)
        
    security.protect('get_override', 'View')
    def get_override(self):
        try:
            ovr = self.priority_array.get()
        except:
            msg = 'Unable to get override for device %s' % \
                (self.as_node_url())
            msglog.log('Entity Manager', msglog.types.WARN, msg)
            msglog.exception()
            raise 
        pa = {}
        for idx in range(16):
            value = ovr[idx]
            if hasattr(value, 'as_magnitude'):
                try:
                    value = value.as_magnitude()
                except:
                    pass
            pa[str(idx+1)] = value
        return OverrideDict(pa, self.get_default())
    
    security.protect('override', 'Override')
    def override(self, value, level=16):
        if not self.is_running():
            raise ENotRunning()
        if isinstance(value, dict):
            value = OverrideDict(value, self.get_default())
        override_list = []
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
            try:
                self.priority_array.get_child(str(level)).set(value)
            except:
                msg = 'Unable to override device %s at level %d' % \
                    (self.as_node_url(), level)
                msglog.log('Entity Manager', msglog.types.WARN, msg)
                msglog.exception()
                         
    security.protect('release', 'Override')
    def release(self, level):
        if not self.is_running():
            raise ENotRunning()
        try:
            self.priority_array.get_child(str(level)).set(None)
        except:
            msg = 'Unable to release property %s at level %d' % \
                (self.as_node_url(), level)
            msglog.log('Entity Manager', msglog.types.WARN, msg)
            msglog.exception()
    
    security.protect('get_write_priority', 'View')
    def get_write_priority(self):
        pa = self.priority_array.get()
        write_priority = None
        for idx in range(0, 16):
            if hasattr(pa[idx],'as_magnitude'):
                value = pa[idx].as_magnitude()
            else:
                value = pa[idx]
            if not value is None:
                write_priority = idx + 1
                break
        return write_priority
    
    security.protect('set_default', 'Override')
    def set_default(self, value):
        if not self.is_running():
            raise ENotRunning()
        self.get_subject().get_child(BAC_RELINQUISH_DFLT).set(value)
    
    security.protect('get_default', 'View')
    def get_default(self):
        try:
            default = self.get_subject().get_child(BAC_RELINQUISH_DFLT).get() # relinquish default
        except:
            default = None
        return default
       
class StatusNode(CompositeNode):
    implements(IAliasNode)
    def __init__(self):
        self._subject = None
        CompositeNode.__init__(self)
        
    def get(self, skipCache=0):
        sub = self.get_subject()
        if sub is None:
            raise ETimeout()
        if self.parent.is_remote():
            return sub.get(skipCache)
        if isinstance(sub, TemplateInstanceNode):
            ti_status = sub.get_child('_status').get().get('status', 0)
        else:
            ti_status = 0
        return {'value':self.parent.get(),
                'status':self.parent.get_write_priority() or ti_status}
    
    def get_subject(self):
        if self._subject is None:
            try:
                subject = self.parent.get_subject()
                if self.parent.is_remote():
                    subject = subject.get_child('_status')
                self._subject = subject
            except:
                msglog.exception()
        return self._subject
    
    def dereference(self, recursive=True):
        if not self.parent.is_remote():
            return self
        return self.get_subject()
    
EntityTypes = (MountPoint, Entity, EntityContainer)

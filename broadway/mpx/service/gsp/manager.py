"""
Copyright (C) 2010 2011 Cisco Systems

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
from mpx.lib import ReloadableSingletonFactory

from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node

from mpx.lib.entity.entity import META_REGISTRY
from mpx.lib.entity.entity import as_entity_url

from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import REQUIRED

from mpx.lib.exceptions import ENameInUse
from mpx.lib.exceptions import ENoSuchName

from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
    
from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM

from command import COMMAND_MANAGER
from command import CommandSet
from command import SetCommand
from command import OverrideCommand
from command import ReleaseCommand
from persist import PERSISTANCE_MANAGER
from persist import do_persist
from persist import deserialize_node
from datatypes import *

import types
import time

class GlobalSetpointManager(CompositeNode):
    security = SecurityInformation.from_default()
    secured_by(security)    
    def __init__(self):
        self._qm = None
        super(GlobalSetpointManager, self).__init__()
        
    def start(self):
        PERSISTANCE_MANAGER.disable_persist()
        count = 0
        start = time.time()
        for group_path in PERSISTANCE_MANAGER.get_gsp_groups():
            try:
                deserialize_node(PERSISTANCE_MANAGER.get_gsp_group(group_path))
                count += 1
            except:
                msglog.exception()
        PERSISTANCE_MANAGER.enable_persist()
        message = 'Global Setpoint Manager restored %d nodes in %f seconds.' % \
            (count, time.time() - start)
        msglog.log('Global Setpoint Manager', msglog.types.INFO, message)
        super(GlobalSetpointManager, self).start()

    security.protect('get_point_purposes', 'View')
    def get_point_purposes(self):
        return META_REGISTRY.get_registered_meta_values('purpose')
    
    security.protect('discover_by_name', 'View')
    def discover_by_name(self, entity_path, name='*'):
        if not entity_path.startswith(EM):
            entity_path = EM + entity_path
        matches = self.qm.fetch(
                {'query':{'name':name,'context':entity_path}}
                ).get('items')  
        matches.sort()
        return matches              
    
    security.protect('discover_by_type', 'View')
    def discover_by_type(self, entity_path, purposes):
        if not entity_path.startswith(EM):
            entity_path = EM + entity_path
        matches = self.qm.fetch(
            {"query": {"name": "*"}, "properties": {"purpose":purposes}}
            ).get('items')
        result = {}
        for property_url in matches:
            try:
                prop_ref = as_node(property_url)
                entity_path = as_entity_url(prop_ref.entity)
                if not result.has_key(entity_path):
                    result[entity_path] = {}
                prop_id = [prop_ref.type, prop_ref.name]
                for purpose in prop_ref.get_meta_values('purpose'):
                    if purpose in purposes:
                        if result[entity_path].has_key(purpose):
                            result[entity_path][purpose].append(prop_id)
                        else:
                            result[entity_path][purpose] = [prop_id]
            except:
                message = 'Error adding value to discover_by_type result set'
                msglog.log('Global Setpoint Manager', msglog.types.INFO, message) 
                msglog.exception()
        return result
                
    ##
    # Return a list of setpoint groups that are associated with a entity.
    # 
    # @param entity_path   The path to the entity.
    # @return  None
    security.protect('get_groups_names', 'View') 
    def get_groups_names(self, entity_path):
        return [grp.name for grp in self.get_group_instances(entity_path)]
    
    security.protect('get_groups_paths', 'View')
    def get_groups_paths(self, entity_path):
        return [grp.as_node_url() for grp in self.get_group_instances(entity_path)]
    
    def get_group_instances(self, entity_path):
        group_container = self._get_group_container(entity_path)
        if group_container is None:
            group_instances = []
        else:
            group_instances = [grp for grp in group_container.children_nodes() if \
                isinstance(grp, GlobalSetpointGroup)]
        return group_instances
    
    def get_group_instance(self, entity_path, group_name):
        group = None
        group_container = self._get_group_container(entity_path)
        if group_container and group_container.has_child(group_name):
            group = group_container.get_child(group_name)
        return group
    
    def _get_group_container(self, entity_path):
        group_container = None
        if not entity_path.startswith(EM):
            entity_path = EM + entity_path
        entity = as_node(entity_path)
        for child in entity.children_nodes():
            if isinstance(child, GlobalSetpointGroupContainer):
                group_container = child
                break
        return group_container
    ##
    # Save or update the group information associated with the referenced entity
    # with the specified configuration.  If the group does not exist, then a new
    # group is created.
    #
    # @param entity_path   The path to the entity.
    # @param group_name    The name of the group. 
    # @param config        The group configuration data.
    # @return  A dictionary providing information about the group configuration.
    security.protect('update_group', 'Configure')
    def update_group(self, entity_path, group_name, config):
        group = self.get_group_instance(entity_path, group_name)
        if not group:
            group = self._create_group(entity_path, group_name, config)
        group.update_group_config(config)
        return group.get_group_config()
                
    def _create_group(self, entity_path, group_name, config):
        group_container = self._get_group_container(entity_path)
        if group_container is None:
            if not entity_path.startswith(EM):
                entity_path = EM + entity_path
            group_container = GlobalSetpointGroupContainer()
            config = {'name':'Global Setpoints',
                      'parent':entity_path}
            group_container.configure(config)
        elif group_container.has_child(group_name):
            raise ENameInUse()
        group = GlobalSetpointGroup()
        config = {'name':group_name,
                  'parent':group_container,
                  'entity_path':entity_path}
        group.configure(config)
        group.start()
        return group

    ##
    # Remove a group at the specified entity path.  If the path points to a 
    # non-existent group, then no error is raised and the function returns
    # success.
    # 
    # @param entity_path   The path to the entity.
    # @param group_name    The name of the group. .
    # @return  None
    security.protect('remove_group', 'Configure')
    def remove_group(self, entity_path, group_name):
        group = self.get_group_instance(entity_path, group_name)
        if group:
            PERSISTANCE_MANAGER.remove_gsp_group(group.as_node_url())
            group.prune()
    
    ##
    # Move the group at the source path to the destination path.
    # 
    # @param entity_path   The path to the entity.
    # @param group_name    The name of the group. .
    # @return  None
    security.protect('move_group', 'Configure')
    def move_group(self, entity_path_src, entity_path_dst, group_name):
        pass
        
    ##
    # Get the configuration information of the group at the specified entity 
    # path
    #
    # @param entity_path   The path to the entity.
    # @param group_name    The name of the group. .
    # @return  A dictionary providing information about the group configuration.
    security.protect('get_group', 'View')
    def get_group(self, entity_path, group_name):
        group = self.get_group_instance(entity_path, group_name)
        if not group:
            raise ENoSuchName()
        return group.get_group_config()
    
    ## following methods are delegated to an instance of a GlobalSetpointGroup
    
    def update_group_config(self, entity_path, group_name, config):
        return self.get_group_instance(entity_path, group_name).update_group_config(config)
    
    def get_group_config(self, entity_path, group_name):
        return self.get_group_instance(entity_path, group_name).get_group_config()

    ##
    # Return a list of the entities managed by the group.
    # 
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @return  A list of paths to the entities that are managed by this node.
    security.protect('get_entities_paths', 'View') 
    def get_entities_paths(self, entity_path, group_name):
        return self.get_group_instance(entity_path, group_name).get_entities_paths()
    
    ##
    # Add or update one or more entities to the list of entities managed by this 
    # group and configure the mapping between the entities properties and setpoint
    # items.
    # 
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @param entity_map   A list of Entity Mapping's.
    # @return  A list of entity mappings that are managed by this node.
    security.protect('update_entity_mapping', 'Configure') 
    def update_entity_mapping(self, entity_path, group_name, entity_map):
        return self.get_group_instance(entity_path, group_name).update_entity_mapping(entity_map)
    
    ##
    # Retrieve the current entity map associated with this global setpoint group
    # 
    # @return  A list of entity mappings that are managed by this node.
    security.protect('get_entity_mapping', 'View')
    def get_entity_mapping(self, entity_path, group_name):
        return self.get_group_instance(entity_path, group_name).get_entity_mapping()
    
    ##
    # Delete a set of entity mappings from the entities managed by this 
    # Global Setpoint Group.
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @param entities  The list of Entity Mappings to be removed.
    # @return  A list of entity mappings that are managed by this node.
    security.protect('remove_entity_mapping', 'Configure') 
    def remove_entity_mapping(self, entity_path, group_name, entities):
        return self.get_group_instance(entity_path, group_name).remove_entity_mapping(entities)
    
    ##
    # Pushes the values of the setpoint items to the properties of the entities
    # mapped to each setpoint item.
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @return  An identifier for the transaction or process id that can be 
    # queried later to find out the progress of the process.  If a GSG controls
    # a large number of groups, then the call will take a long time to return.
    # This strategy avoids the possible HTTP network timeout that would occur if 
    # the framework took too long to set all of the entities.  Instead, the client
    # will being a poll to check for the process.
    security.protect('push_values', 'Override') 
    def push_values(self, entity_path, group_name):
        return self.get_group_instance(entity_path, group_name).push_values()

    ##
    # Releases the values of the setpoint items to the properties of the entities
    # mapped to each setpoint item.
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @return  An identifier for the transaction or process id that can be 
    # queried later to find out the progress of the process.  If a GSG controls
    # a large number of groups, then the call will take a long time to return.
    # This strategy avoids the possible HTTP network timeout that would occur if 
    # the framework took too long to set all of the entities.  Instead, the client
    # will being a poll to check for the process.
    security.protect('release_setpoint', 'Override')
    def release_setpoint(self, entity_path, group_name, setpoint_id, priority_level):
        return self.get_group_instance(entity_path, group_name).release_setpoint(
                 setpoint_id, priority_level
                 )
        
    ##
    # Requests the progress of the push values for the specified transaction_id
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @param transaction_id  An array of entity mappings.
    # @return  A transaction status object containing the following attributes.
    #    - completed: True if the process has completed, False otherwise.
    #    - success: Present only if "completed" is set to True.  True if the
    #      process managed to set all the properties, False otherwise.
    #    - report_items: Present only if completed is set to True.  An array of
    #      Error Report Items.
    security.protect('get_push_values_progress', 'View')
    def get_push_values_progress(self, entity_path, group_name, transaction_id):
        return self.get_group_instance(entity_path, group_name).get_push_values_progress(transaction_id)
    
    ##
    # Creates a poll group for the values of the properties of the managed entities
    # in the setpoint group.
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group. 
    # @return  A string value representing the identifer of the poll group.
    security.protect('create_polled', 'View') 
    def create_polled(self, entity_path, group_name, node_reference_table=None, timeout=300):
        return self.get_group_instance(entity_path, group_name).create_polled()
        
    ##
    # Destroys a poll group
    #
    # @param poll_id A string value representing the identifier of the poll group.
    # @return None
    security.protect('destroy', 'View') 
    def destroy(self, entity_path, group_name, poll_id):
        return self.get_group_instance(entity_path, group_name).destroy(poll_id)
    
    ##
    # Polls for the values of the entities managed by the setpoint group given the
    # poll_id
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @param poll_id  The string value representing the indentifier of the 
    # poll group, as returned from create_polled.
    # @return  A dictionary keyed by "(entity_path, property)", the value being a
    # result object.
    security.protect('poll_all', 'View') 
    def poll_all(self, entity_path, group_name, poll_id):
        return self.get_group_instance(entity_path, group_name).poll_all(poll_id)
    
    ##
    # Like poll_all but returns only those entity/property pairs whose values 
    # have changed since the last time poll_* was called, referencing a particular
    # poll_id
    #
    # @param entity_path  The entity that is the owner of this setpoint group.
    # @param group_name   The name of the group.
    # @param poll_id  The string value representing the indentifier of the 
    # poll group, as returned from create_polled.
    # @return  A dictionary keyed by "(entity_path, property)", the value being a
    # result object.
    security.protect('poll_changed', 'View') 
    def poll_changed(self, entity_path, group_name, poll_id):
        return self.get_group_instance(entity_path, group_name).poll_changed(poll_id)
    
    def singleton_unload_hook(self):
        pass
    
    def _get_qm(self):
        if self._qm is None:
            self._qm = as_node('/services/Query Manager')
        return self._qm
    
    qm = property(_get_qm)
    
GSP_MANAGER = ReloadableSingletonFactory(GlobalSetpointManager)
def manager_factory():
    return GSP_MANAGER

##
# The GlobalSetpointGroupContainer is a container\holder for instances of
# the GlobalSetpointGroup class.
class GlobalSetpointGroupContainer(CompositeNode):
    @do_persist
    def configure(self, config):
        super(GlobalSetpointGroupContainer, self).configure(config)
 
 ##
 # The GlobalSetpointGroup implements the Setpoint Group API
class GlobalSetpointGroup(CompositeNode):
    security = SecurityInformation.from_default()
    secured_by(security)   
    def __init__(self, **kw):
        # {k:v} ... k == gsp_identifer, v == [{'entity_path':'entity_prop', ...}]
        # f.e, {'unique_handle':[{'/path/to/entity':'(pt_type, pt_name)', ...}] 
        self._entity_map = {}
        self._group_cfg = GroupCfg()
        for name, value in kw.items():
            if hasattr(self, name):
                setattr(self, attr, value)
    @do_persist
    def configure(self, config):
        super(GlobalSetpointGroup, self).configure(config)
        set_attribute(self, 'entity_path', REQUIRED, config)
        
    def configuration(self):
        config = super(GlobalSetpointGroup, self).configuration()
        get_attribute(self, 'entity_path', config)
        return config
    
    @do_persist
    def update_group_config(self, config):
        self._group_cfg = GroupCfg()
        for setpoint_item in config:
            if not isinstance(setpoint_item, GroupSetpointItem):
                setpoint_item = GroupSetpointItem(setpoint_item)
            self._group_cfg.append(setpoint_item)
        
    def get_group_config(self):
        return self._group_cfg

    ##
    # Save or update the group information associated with the referenced entity
    # with the specified configuration.  
    #
    # @param config        The group configuration data.
    # @return  A dictionary providing information about the group configuration.
    security.protect('update_group', 'Configure')
    def update_group(self, config):
        self.update_group_config(config)
        return self.get_group_config()

    ##
    # Return a list of the entities managed by the group.
    # 
    # @return  A list of paths to the entities that are managed by this node.
    security.protect('get_entities_paths', 'View') 
    def get_entities_paths(self):
        paths = {} # dict used for uniqueness of keys
        for entity_maps in self._entity_map.values():
            for entity_map in entity_maps:
                paths[entity_map.entity_path] = None
        return paths.keys()
    
    ##
    # Add or update one or more entities to the list of entities managed by this 
    # group and configure the mapping between the entities properties and setpoint
    # items.
    # 
    # @param entities   A list of Entity Mapping's.
    # @return  A list of entity mappings that are managed by this node.
    security.protect('update_entity_mapping', 'Configure')
    @do_persist 
    def update_entity_mapping(self, entity_map):
        _entity_map = {}
        for setpoint_id, e_maps in entity_map.items():
            _entity_map[setpoint_id] = []
            for e_map in e_maps:
                if not isinstance(e_map, EntityMapping):
                    if not e_map.has_key('setpoint_id'):
                        e_map['setpoint_id'] = setpoint_id
                    e_map = EntityMapping(e_map)
                _entity_map[setpoint_id].append(e_map)
        self._entity_map = _entity_map
        return self._entity_map
    
    ##
    # Retrieve the current entity map associated with this global setpoint group
    # 
    # @return  A list of entity mappings that are managed by this node.
    security.protect('get_entity_mapping', 'View')
    def get_entity_mapping(self):
        return self._entity_map
    
    ##
    # Delete a set of entity mappings from the entities managed by this 
    # Global Setpoint Group.
    #
    # @param entity_map  The Entity Mappings that are to be removed.
    # @return  A list of entity mappings that are managed by this node.
    security.protect('remove_entity_mapping', 'Configure') 
    @do_persist
    def remove_entity_mapping(self, entity_map):
        for setpoint_id, e_maps in entity_map.items():
            if not self._entity_map.has_key(setpoint_id):
                continue
            for e_map in e_maps:
                if not isinstance(e_map, EntityMapping):
                    if not e_map.has_key('setpoint_id'):
                        emap['setpoint_id'] = setpoint_id
                    e_map = EntityMapping(e_map)
                for existing_emap in self._entity_map.get(setpoint_id):
                    if e_map == existing_emap:
                        self._entity_map[setpoint_id].remove(existing_emap)
            if not self._entity_map[setpoint_id]:
                # empty list, delete it
                del self._entity_map[setpoint_id]
        return self._entity_map

    ##
    # Pushes the values of the setpoint items to the properties of the entities
    # mapped to each setpoint item.
    #
    # @return  An identifier for the transaction or process id that can be 
    # queried later to find out the progress of the process.  If a GSG controls
    # a large number of groups, then the call will take a long time to return.
    # This strategy avoids the possible HTTP network timeout that would occur if 
    # the framework took too long to set all of the entities.  Instead, the client
    # will being a poll to check for the process.
    security.protect('push_values', 'Override') 
    def push_values(self):
        command_set = []
        for setpoint_item in self.get_group_config():
            setpoint_id = setpoint_item.setpoint_id
            value = setpoint_item.value
            priority = setpoint_item.priority
            for entity_map in self.get_entity_mapping().get(setpoint_id):
                try:
                    property = entity_map.get_property_reference()
                except:
                    message = 'Error pushing value to %s' % (entity_map.entity_path)
                    msglog.log('Global Setpoint Manager', msglog.types.INFO, message) 
                    msglog.exception()
                    continue
                if hasattr(property, 'override'):
                    command = OverrideCommand(property, value, priority)
                elif hasattr(property, 'set'):
                    command = SetCommand(property, value)
                else: 
                    continue
                command_set.append(command)
        command_set = CommandSet(command_set)
        COMMAND_MANAGER.enqueue(command_set)
        return command_set.get_transaction_id()
    
    ##
    # Releases the values of the setpoint items to the properties of the entities
    # mapped to each setpoint item.
    #
    # @return  An identifier for the transaction or process id that can be 
    # queried later to find out the progress of the process.  If a GSG controls
    # a large number of groups, then the call will take a long time to return.
    # This strategy avoids the possible HTTP network timeout that would occur if 
    # the framework took too long to set all of the entities.  Instead, the client
    # will being a poll to check for the process.
    security.protect('release_setpoint', 'Override')
    def release_setpoint(self, setpoint_id, priority_level):
        command_set = []
        if ((len(self.get_entity_mapping()) != 0) and (setpoint_id in self.get_entity_mapping().keys())):
            ##
            # Entity map is not empty and also contains an entry for the 
            # setpoint_id, proceed ...
            ##
            for entity_map in self.get_entity_mapping().get(setpoint_id):
                try:
                    property = entity_map.get_property_reference()
                except:
                    message = 'Error releasing override for %s' % (entity_map.entity_path)
                    msglog.log('Global Setpoint Manager', msglog.types.INFO, message) 
                    msglog.exception()
                    continue
                if not hasattr(property, 'release'):
                    continue
                command_set.append(ReleaseCommand(property, priority_level))
        command_set = CommandSet(command_set)
        COMMAND_MANAGER.enqueue(command_set)
        return command_set.get_transaction_id()
    
    ##
    # Requests the progress of the push values for the specified transaction_id
    #
    # @param transaction_id  An array of entity mappings.
    # @return  A transaction status object containing the following attributes.
    #    - completed: True if the process has completed, False otherwise.
    #    - success: Present only if "completed" is set to True.  True if the
    #      process managed to set all the properties, False otherwise.
    #    - report_items: Present only if completed is set to True.  An array of
    #      Error Report Items.
    security.protect('get_push_values_progress', 'View')
    def get_push_values_progress(self, transaction_id):
        return COMMAND_MANAGER.get_push_values_progress(transaction_id)
    
    ##
    # Creates a poll group for the values of the properties of the managed entities
    # in the setpoint group.
    #
    # @param 
    # @return  A string value representing the identifer of the poll group.
    security.protect('create_polled', 'View') 
    def create_polled(self, node_reference_table=None, timeout=300):
        if node_reference_table is None:
            node_reference_table = {}
            for setpoint_id in self._entity_map.keys():
                for entity_map in self._entity_map.get(setpoint_id, []):
                    try:
                        property = entity_map.get_property_reference()
                    except:
                        continue
                    entity_path = entity_map.entity_path
                    nrt_id = str([setpoint_id, entity_path])
                    node_reference_table[nrt_id] = property
        return SM.create_polled(node_reference_table, timeout)
   
    ##
    # Destroys a poll group
    #
    # @param poll_id A string value representing the identifier of the poll group.
    # @return None
    security.protect('destroy', 'View') 
    def destroy(self, poll_id):
        return SM.destroy(poll_id)
    
    ##
    # Polls for the values of the entities managed by the setpoint group given the
    # poll_id
    #
    # @param poll_id  The string value representing the identifier of the 
    # poll group, as returned from create_polled.
    # @return  A dictionary keyed by "(entity_path, property)", the value being a
    # result object.
    security.protect('poll_all', 'View') 
    def poll_all(self, poll_id):
        return SM.poll_all(poll_id)
    
    ##
    # Like poll_all but returns only those entity/property pairs whose values 
    # have changed since the last time poll_* was called, referencing a particular
    # poll_id
    #
    # @param poll_id  The string value representing the identifier of the 
    # poll group, as returned from create_polled.
    # @return  A dictionary keyed by "(entity_path, property)", the value being a
    # result object.
    security.protect('poll_changed', 'View') 
    def poll_changed(self, poll_id):
        return SM.poll_changed(poll_id)
    

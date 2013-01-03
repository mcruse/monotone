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
from mpx.lib import factory
from mpx.lib import msglog
from mpx.lib import ReloadableSingletonFactory

from mpx.lib.persistence.datatypes import PersistentDictionary
from datatypes import *

def do_persist(method):
    def _method(*args):
        result = method(*args)
        node = args[0]
        PERSISTANCE_MANAGER.put_gsp_group(
            node.as_node_url(), serialize_node(node)                              
            )
        return result
    return _method

def normalize_nodepath(nodepath):
    if not nodepath.endswith('/'):
        nodepath += '/'
    return nodepath

def deserialize_node(node_data):
    node_factory = node_data.get('node_factory')
    node_config = node_data.get('node_config')
    # recreate GlobalSetpointGroup instance
    gspg = factory(node_factory)
    gspg.configure(node_config)
    gspg.start()
    ##
    # restore group config data and entity mapping - 
    # if it's a GlobalSetpointGroup.  GlobalSetpointGroup have
    # a get_entity_mapping, while GlobalSetpointGroupContainer's do not.
    if hasattr(gspg, 'get_entity_mapping'):
        entity_map = {}
        _entity_map = eval(node_data.get('entity_map'))
        for setpoint_id in _entity_map.keys():
            entity_map[setpoint_id] = []
            for emap in _entity_map.get(setpoint_id, []):
                entity_map[setpoint_id].append(EntityMapping(emap))
        gspg.update_entity_mapping(entity_map)
        group_config = []
        for gsp_item in eval(node_data.get('group_config')):
            group_config.append(GroupSetpointItem(eval(gsp_item)))
        gspg.update_group(group_config)
    return gspg

def serialize_node(gspg):
    klass = str(gspg.__class__)
    klass = klass[klass.rfind('.')+1:-2]
    node_factory = gspg.__module__ + '.' + klass
    serialized = {'node_factory':node_factory, 'node_config':gspg.configuration()}
    if hasattr(gspg, 'get_entity_mapping'):
        serialized['entity_map'] = repr(gspg.get_entity_mapping())
        serialized['group_config'] = repr(gspg.get_group_config())
    return serialized
    
class PersistanceManager(object):
    def __init__(self):
        # {nodepath:{'node_config':node_config, 
        #            'group_config':group_config, 
        #            'entity_map':entity_map}}
        self._persisted_data = PersistentDictionary('GSPData')
        self.debug = 1
        self._persist_enabled = False
        
    def message(self, message, mtype=msglog.types.INFO, level=1):
        if self.debug >= level:
            msglog.log('Global Setpoint Manager', mtype, message)
        
    def persist_enabled(self):
        return self._persist_enabled
    
    def enable_persist(self):
        self._persist_enabled = True
        
    def disable_persist(self):
        self._persist_enabled = False
        
    def get_gsp_groups(self):
        groups = self._persisted_data.keys()
        groups.sort(lambda a,b: cmp(a.count('/'), b.count('/')))
        return groups
        
    def get_gsp_group(self, nodepath):
        return self._persisted_data[normalize_nodepath(nodepath)]
    
    def put_gsp_group(self, nodepath, nodedata):
        if not self.persist_enabled():
            return
        nodepath = normalize_nodepath(nodepath)
        if not self._persisted_data.has_key(nodepath):
            # create default configuration.
            data = {'node_config':{},
                    'group_config':[],
                    'entity_map':{},
                    'node_factory':''}
            self._persisted_data[nodepath] = data
        self.put_gsp_group_data(nodepath, nodedata)
        
    def remove_gsp_group(self, nodepath):
        nodepath = normalize_nodepath(nodepath)
        if self._persisted_data.has_key(nodepath):
            del self._persisted_data[nodepath]
            
    def get_gsp_group_data(self, nodepath):
        nodepath = normalize_nodepath(nodepath)
        return self._persisted_data[nodepath] 
    
    def put_gsp_group_data(self, nodepath, nodedata):
        nodepath = normalize_nodepath(nodepath)
        for data_key in self._persisted_data[nodepath].keys():
            value = nodedata.get(data_key)
            if value is not None:
                self._put_entry(nodepath, data_key, value)
    
    def get_gsp_group_nconfig(self, nodepath):
        # node configuration data
        return self._get_entry(nodepath, 'node_config')
    
    def put_gsp_group_nconfig(self, nodepath, value):
        # node configuration data
        self._put_entry(nodepath, 'node_config', value)
    
    def get_gsp_group_gconfig(self, nodepath):
        # gsp group configuration data
        return self._get_entry(nodepath, 'group_config')
    
    def putt_gsp_group_gconfig(self, nodepath, value):
        # gsp group configuration data
        self._put_entry(nodepath, 'group_config', value)
    
    def get_gsp_group_entity_map(self, nodepath):
        return self._get_entry(nodepath, 'entity_map')
    
    def put_gsp_group_entity_map(self, nodepath, value):
        self._put_entry(nodepath, 'entity_map', value)
        
    def _get_entry(self, nodepath, data_type):
        return self.get_gsp_group(normalize_nodepath(nodepath))[data_type]
        
    def _put_entry(self, nodepath, data_type, value):
        if not self.persist_enabled():
            return
        nodepath = normalize_nodepath(nodepath)
        group = self.get_gsp_group(nodepath)
        assert group, \
        'A group must exist before data can be stored against it.'
        group[data_type] = value
        self._persisted_data.notify_changed(nodepath)        
            
    def singleton_unload_hook(self):
        pass

PERSISTANCE_MANAGER = ReloadableSingletonFactory(PersistanceManager)

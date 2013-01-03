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
from mpx.lib import ReloadableSingletonFactory
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import is_node
from mpx.lib.persistence.datatypes import PersistentDictionary

def serialize_node(node):
    klass = str(node.__class__)
    klass = klass[klass.rfind('.')+1:-2]
    factory = node.__module__ + '.' + klass
    return {'factory':factory,
            'cfg':node.configuration()}
    
def sched_sort(sched_a, sched_b):
    if is_node(sched_a):
        sched_a = sched_a.as_node_url()
    if is_node(sched_b):
        sched_b = sched_b.as_node_url()
    sched_a_cnt = sched_a.count('/')
    sched_b_cnt = sched_b.count('/')
    if sched_a_cnt == sched_b_cnt:
        cmp(sched_a, sched_b)
    return cmp(sched_a_cnt, sched_b_cnt)

def normalize_nodepath(nodepath):
    if not nodepath.endswith('/'):
        nodepath += '/'
    return nodepath

class PersistanceManager(object):
    def __init__(self):
        # {nodepath:{'cfg':cfg, 
        #            'summary':summary, 
        #            'meta':meta, 
        #            'properties':properties,
        #            'fail_list':fail_list,
        #            'sync_state':sync_in_progress,
        #            'override':override}}
        self._persisted_data = PersistentDictionary('ScheduleData')
        self.debug = 1
        
    def message(self, message, mtype=msglog.types.INFO, level=1):
        if self.debug >= level:
            msglog.log('Scheduler', mtype, message)
        
    def get_scheds(self):
        scheds = self._persisted_data.keys()
        scheds.sort(sched_sort)
        return scheds
        
    def get_sched(self, nodepath):
        return self._persisted_data[normalize_nodepath(nodepath)]
    
    def put_sched(self, nodepath, cfg):
        nodepath = normalize_nodepath(nodepath)
        if not self._persisted_data.has_key(nodepath):
            # create default configuration.
            pdata = {'cfg':{},
                     'summary':[[], [], [], 'exceptions'],
                     'meta':{},
                     'properties':[],
                     'fail_list':[],
                     'sync_state':False,
                     'override':False}
            self._persisted_data[nodepath] = pdata
        self.put_sched_cfg(nodepath, cfg)
        
    def remove_sched(self, nodepath):
        nodepath = normalize_nodepath(nodepath)
        if self._persisted_data.has_key(nodepath):
            for sched in self.get_scheds():
                if sched.startswith(nodepath):
                    del self._persisted_data[sched]
        else:
            msg = 'Error removing non-existent schedule %s from persistent data.' \
                % nodepath
            self.message(msg)
                         
    def move_sched(self, source, destination, cfg, is_rename=False):
        source = normalize_nodepath(source)
        destination = normalize_nodepath(destination)
        for sched in self.get_scheds():
            if not sched.startswith(source):
                continue
            data = self._persisted_data[sched]
            del self._persisted_data[sched]
            if sched == source:
                # rename
                if is_rename:
                    newsched = destination
                else:
                    newsched = sched.replace(source, destination) + source.split('/')[-2] + '/'
                oldroot = sched
                newroot = newsched
                self._persisted_data[newsched] = data 
                # prior to persisting, the schedule should have been moved
                # within the nodetree.  We grab and persist the latest configuration.
                # This put call will also ensure sync to disk to takes place.
                self.put_sched_cfg(newsched, cfg)
            else:
                newsched = normalize_nodepath(sched.replace(oldroot, newroot)) #+ sched_name + '/'
                self._persisted_data[newsched] = data 
                self.put_sched_cfg(newsched, serialize_node(as_node(newsched)))
                    
    def get_sched_cfg(self, nodepath):
        return self._get_entry('cfg', nodepath)
    
    def put_sched_cfg(self, nodepath, cfg):
        self._put_entry('cfg', nodepath, cfg)
        
    def get_sched_summary(self, nodepath):
        return self._get_entry('summary', nodepath)
    
    def put_sched_summary(self, nodepath, summary):
        self._put_entry('summary', nodepath, summary)
        
    def get_sched_props(self, nodepath):
        return self._get_entry('properties', nodepath)
    
    def put_sched_props(self, nodepath, properties):
        self._put_entry('properties', nodepath, properties)
                    
    def get_sched_meta(self, nodepath):
        return self._get_entry('meta', nodepath)
    
    def put_sched_meta(self, nodepath, meta):
        self._put_entry('meta', nodepath, meta)
                
    def get_fail_list(self, nodepath):
        return self._get_entry('fail_list', nodepath)
    
    def put_fail_list(self, nodepath, fail_list):
        self._put_entry('fail_list', nodepath, fail_list)
        
    def get_sync_state(self, nodepath):
        return self._get_entry('sync_state', nodepath)
    
    def put_sync_state(self, nodepath, sync_state):
        self._put_entry('sync_state', nodepath, sync_state)
        
    def get_override(self, nodepath):
        return self._get_entry('override', nodepath)
    
    def put_override(self, nodepath, override):
        self._put_entry('override', nodepath, override)
        
    def _get_entry(self, ptype, nodepath):
        return self.get_sched(normalize_nodepath(nodepath))[ptype]
        
    def _put_entry(self, ptype, nodepath, value):
        nodepath = normalize_nodepath(nodepath)
        sched = self.get_sched(nodepath)
        assert sched, \
        'A schedule must exist before data can be stored against it.'
        sched[ptype] = value
        self._persisted_data.notify_changed(nodepath)        
            
    def singleton_unload_hook(self):
        pass

PERSISTANCE_MANAGER = ReloadableSingletonFactory(PersistanceManager)

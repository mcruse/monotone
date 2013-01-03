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
from time import time as now

from mpx.lib import Result

class BatchRecord(object):
    def __init__(self, sm_key, node):
        self.sm_key = sm_key
        self.node = node
        return

##
# @note Batch uses the Agent's cache_ttl, not the point's ttl.
class Batch(object):
    def __init__(self, agent, sm_node_map):
        self.agent = agent
        self.batch_map = {}
        self.oid_list = []
        self.results = None
        self.expires_at = 0
        self.ttl = agent.cache_ttl
        for k,n in sm_node_map.items():
            oid = n.as_oid()
            self.batch_map[oid] = BatchRecord(k,n)
            self.oid_list.append(oid)
        return
    def get_batch(self):
        timestamp = now()
        if timestamp >= self.expires_at:
            results = {}
            for oid, value in self.agent.snmp_get_multiple(*self.oid_list):
                result = Result(value, timestamp, 0)
                sm_key = self.batch_map[oid].sm_key
                results[sm_key] = result
            self.results = results
            self.expires_at = timestamp + self.ttl
        return self.results

def create_batches(agent, sm_node_map, max_batch_size=0):
    if max_batch_size and (len(sm_node_map) > max_batch_size):
        batches = []
        batch_map = {}
        for key,value in sm_node_map.items():
            batch_map[key] = value
            if len(batch_map) >= max_batch_size:
                batches.append(Batch(agent, batch_map))
                batch_map = {}
        if batch_map:
            batches.append(Batch(agent, batch_map))
            batch_map = {}
        return tuple(batches)
    return (Batch(agent, sm_node_map),)

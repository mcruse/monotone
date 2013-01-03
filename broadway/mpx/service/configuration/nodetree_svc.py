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
"""
nodetree_svc.py: Services requests for nested-dictionary representations of the
nodetree structure. First client to use this service is Sandbox Editor App, via
RNA.
"""

from mpx.lib.node import ServiceNode, as_node

class NodeTreeSvc(ServiceNode):
    def configure(self, cd):
        ServiceNode.configure(self, cd)
        self.name = 'nodetree_as_dict'
        return
    def get(self):
        nodetree_dict = {} # root dict
        root_node = as_node('/')
        self._get_node_names(root_node, nodetree_dict)
        return nodetree_dict
    def _get_node_names(self, cur_node, ntd):
        ntd[cur_node.name] = None
        if not hasattr(cur_node, 'children_nodes'):
            return
        children_nodes = cur_node.children_nodes()
        if len(children_nodes) == 0:
            return
        ntd[cur_node.name] = {}
        ntd_next = ntd[cur_node.name]
        for child_node in children_nodes:
            self._get_node_names(child_node, ntd_next)
        return
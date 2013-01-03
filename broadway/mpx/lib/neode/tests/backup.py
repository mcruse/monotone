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
from node import NodeSpace

from mpx.lib.node import as_node, as_node_url, as_internal_node
from mpx.lib.node import ConfigurableNode
class NodeSpaceAdapter(NodeSpace):
    # implements(INodeSpace)

    def __new__(klass, node, *args):
        if not isinstance(node, ConfigurableNode):
            raise ValueError('Adapts traditional nodes only')
        if not hasattr(node, '__nodespace'):
            adapter = super(NodeSpaceAdapter, klass).__new__(klass, *args)
            node.__nodespace = adapter
        return node.__nodespace

    def __init__(self, node, *args):
        self.node = node
        super(NodeSpaceAdapter, self).__init__(*args)
        self.nodetree = {}
        self.url = as_node_url(self.node)
        self.root = as_node('/')
        self.as_node = as_node
        self.as_internal_node = as_internal_node
        self.as_node_url = as_node_url

    def create_node(self, *args):
        raise Exception('Not available in adapted nodespace.')
    def add_node_url(self, *args):
        raise Exception('Not available in adapted nodespace.')
    def remove_node_url(self, *args):
        raise Exception('Not available in adapted nodespace.')

# Registering as default adapter.  Because NodeSpace
# implements INodeSpace, this adapter will be registered
# to adapt ANY object to the INodeSpace interface.
register_adapter(NodeNodeSpaceAdapter, [None])

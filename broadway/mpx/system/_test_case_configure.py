"""
Copyright (C) 2003 2006 2010 2011 Cisco Systems

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
import os

from mpx_test import DefaultTestFixture

from mpx.lib import msglog

from mpx import properties
from mpx.lib.node import as_node, as_internal_node, as_node_url
from mpx.lib.node import Node, ConfigurableNode, CompositeNode
from mpx.lib.node import as_internal_node, as_node
from mpx.service import ServiceNode

# Survive installation, or lack thereof, of the PyXML package.
try:
    from xml.sax import SAXException
except:
    class SAXException(Exception):
        pass

import system

class Leaf(ConfigurableNode):
    pass

class Bogus(Node):
    pass

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        return
    # @fixme Add ensure standalone.
    def test_1_empty(self):
        system.configure(os.path.join(properties.ROOT,
                                      'mpx/system/_test_1_empty.xml'))
        root = as_internal_node('/')
        if root.exception is None or isinstance(root.exception, SAXException):
            return
        raise root.exception
    def test_2_anchors_only(self):
        system.configure(os.path.join(properties.ROOT,
                                      'mpx/system/_test_2_anchors_only.xml'))
        root = as_internal_node('/')
        if root.exception is not None:
            args = []
            args.extend(root.exception.args)
            args.append('Unexpected exception instiating anchors only.')
            raise root.exception
        for node in root.children_nodes():
            if node.name not in ('services','interfaces', 'aliases'):
                raise 'Unexpected anchor node %s' % as_node_url(node)
        # Now add on the "required" services.
        system.ensure_minimal_configuration()
        return

"""
Copyright (C) 2001 2002 2003 2004 2006 2010 2011 Cisco Systems

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
##
# Defines the common node interfaces which can be used as mixins.
# Write extensive test cases.

#
# Functions that are now exposed as methods on all Nodes.
#
from _node import as_deferred_node
from _node import as_internal_node
from _node import as_node
from _node import as_node_url
from _node import is_enabled
from _node import is_configured

#
# Functions that are helpful but make little sense as Nodes.
#
from _node import is_node
from _node import is_node_url

#
# Functions/types that need some more thought before putting them to common
# use.
#
from _node import Alias
from _node import Aliases
from _node import PublicInterface
from _node import from_path
from _node import is_composite
from _node import is_configurable
from _node import is_gettable
from _node import is_runnable
from _node import is_settable
from _node import reload_node
from _node import ROOT
from _node import NodeProxy
from _node import CachingNodeProxy
from _node import NodeInterfaceProxy
from _node import CompositeNode, ConfigurableNode

from _node import _anchor_sort # For mpx.system...

##
# @fixme Soon to be deprecated...
from _node import ServiceInterface

##
# @fixme Soon to be deprecated...
from _node import ConfigurableNodePublicInterface

##
# @fixme Soon to be deprecated...
def factory():
    return CompositeNode()

def _print_node_states(node=None):
    if node is None:
        node = as_internal_node('/')
    print as_node_url(node), node._node_state
    try:
        for n in node.children_nodes():
            _print_node_states(n)
    except:
        return
    return

##
# Soon to be deprecated...
class SubServiceNode(CompositeNode):
    pass

##
# Soon to be deprecated...
class ServiceNode(CompositeNode):
    pass

##
# Soon to be rewritten as the 'real' base class.
class Node(CompositeNode):
    pass

from _node_decorator import NodeDecorator

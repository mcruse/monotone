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
from mpx.componentry import Interface
from mpx.componentry import Attribute
from mpx.lib.interfaces import IInspectable

class INode(Interface):
    name = Attribute("")
    parent = Attribute("")
    def as_node(path):
        """
        """
    def as_internal_node(path):
        """
        """
    def as_node_url(node):
        """
        """
    def prune(force=False):
        """
        """
    def is_pruned():
        """
            Boolean indicator whether node has been pruned or not.
        """

class IRunnable(Interface):
    enabled = Attribute("")
    def start():
        """
        """
    def stop():
        """
        """
    def is_enabled():
        """
        """
    def is_running():
        """
        """

class IConfigurable(Interface):
    debug = Attribute("")
    def configure(config):
        """
        """
    def configuration():
        """
        """
    def is_configured():
        """
        """

class IComposite(Interface):
    def get_child(name):
        """
        """
    def has_child(name):
        """
        """
    def has_children():
        """
        """
    def children_nodes():
        """
        """
    def children_names():
        """
        """
    def descendants_names():
        """
        """
    def get_children():
        """
        """
    def _add_child(node):
        """
        """
    def _remove_child(node):
        """
        """
    def _rename_child(node, newname):
        """
        """

class IRoot(Interface):
    def start(**kw):
        """
        """
    def stop(**kw):
        """
        """

class IConfigurableNode(INode, IInspectable, IConfigurable, IRunnable):
    """
    """

class ICompositeNode(IConfigurableNode, IComposite):
    def start_children():
        """
        """
    def stop_children():
        """
        """

class IRootNode(ICompositeNode, IRoot):
    """
    """

class IAliasNode(IConfigurableNode):
    """
    """
    def dereference(recursive=False):
        """
            Returns dereferenced target node.
            
            If 'recursive' provided and True, dereferencing 
            recurses until target does not provide IAliasNode.
        """

class IGettable(Interface):
    def get(asyncok):
        """
        """

class ISettable(Interface):
    def set(value):
        """
        """

class IDeferred(Interface):
    def get_deferred_url():
        """
        """   


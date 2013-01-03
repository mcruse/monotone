"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
import time
from os import path
import urllib
from mpx.lib.neode.interfaces import INode
from mpx.lib.neode.interfaces import IChildNode
from mpx.lib.neode.interfaces import IParentNode
from mpx.lib.neode.interfaces import IGettable
from mpx.lib.neode.interfaces import ISettable
from mpx.lib.neode.interfaces import IInspectable
from mpx.lib.neode.interfaces import IModifiable
from mpx.lib.neode.interfaces import IConfigurable
from mpx.lib.neode.interfaces import IEnableAble
from mpx.lib.neode.interfaces import IRunnable
from mpx.lib.neode.interfaces import INodeSpace
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.neode.interfaces import IDeferredNode
from mpx.lib.neode.interfaces import IService
from mpx.lib.neode.interfaces import IRootNode
from mpx.lib.neode.interfaces import IAlias
from mpx.lib.neode.interfaces import IAliases

from mpx.componentry import Interface
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry import provided_by
from mpx.componentry import directly_provides
from mpx.componentry import class_implements
from mpx.componentry import register_utility
from mpx.componentry import query_utility
from mpx.componentry.security.interfaces import IUser
from mpx.componentry.security.interfaces import ISecure
from interfaces import IConfigurableNode
from interfaces import ICompositeNode

from mpx.lib.node import as_node
from mpx.lib.node import as_node_url

class IOGConfigurableNode(Interface):
    """
        Marker interface applied to old nodes to facilitate adaptation.
    """

class IOGCompositeNode(IOGConfigurableNode):
    """
        Marker interface applied to old nodes to facilitate adaptation.
    """

class IOGRemoteNode(Interface):
    """
        Marker to enable adaptation for Node Facade instances.  
        This is an interrim solution to enable certain actions, 
        such as overriding default security adapter and using 
        node facade references within neode system.
    """

def setup_hybrid_architecture(nodespace):
    OGConfigurableNeodeAdapter.nodespace = nodespace
    from mpx.lib.node import ConfigurableNode
    from mpx.lib.node import CompositeNode
    from mpx.lib.rna import NodeFacade
    class_implements(ConfigurableNode, IOGConfigurableNode)
    class_implements(CompositeNode, IOGCompositeNode)
    class_implements(NodeFacade, IOGRemoteNode)
    class_implements(NodeFacade, IOGCompositeNode)
    NodeFacade.__conform__ = None

class IOGRemoteNodeSecurityAdapter(object):
    implements(ISecure)
    adapts(IOGRemoteNode, IUser)
    def __init__(self, facade, user):
        directly_provides(self, *tuple(provided_by(facade)))
        self.__dict__['facade'] = facade
        self.__dict__['user'] = user
    def __getattr__(self, name):
        return getattr(self.facade, name)
    def __setattr__(self, name, value):
        if name == '__provides__':
            return super(
                IOGRemoteNodeSecurityAdapter, self).__setattr__(name, value)
        return setattr(self.facade, name, value)

register_adapter(IOGRemoteNodeSecurityAdapter)

class OGConfigurableNeodeAdapter(object):
    implements(IConfigurableNode)
    adapts(IOGConfigurableNode)
    nodespace = None
    def __init__(self, node):
        directly_provides(self, *tuple(provided_by(node)))
        self.__dict__['node'] = node
    
    def get_nodespace(self):
        return OGConfigurableNeodeAdapter.nodespace
    
    def get_url(self):
        return as_node_url(self.node)
    url = property(get_url)
    absolute_url = url
    
    def __get_parent(self):
        parent = self.node.parent
        if parent is not None:
            parent = IConfigurableNode(parent)
        return parent
    parent = property(__get_parent)
    
    def __getattr__(self, name):
        return getattr(self.node, name)
    
    def __setattr__(self, name, value):
        if name == '__provides__':
            return super(OGConfigurableNeodeAdapter, self).__setattr__(name, value)
        return setattr(self.node, name, value)

register_adapter(OGConfigurableNeodeAdapter)

class OGCompositeNeodeAdapter(OGConfigurableNeodeAdapter):
    implements(ICompositeNode)
    adapts(IOGCompositeNode)

    def add_child(self, child):
        self.node._add_child(child)
        return path.join(self.url, child.name)

    def remove_child(self, childname):
        if not isinstance(childname, str):
            childname = childname.name
        del(self.node._children[childname])

    def children_nodes(self, *args, **kw):
        nodes = self.node.children_nodes(*args, **kw)
        nodes = map(IConfigurableNode, nodes)
        return nodes

    def get_child(self, name, *args, **kw):
        node = self.node.get_child(name, *args, **kw)
        return IConfigurableNode(node)

    def as_node(self, *args):
        node = self.node.as_node(*args)
        return IConfigurableNode(node)

register_adapter(OGCompositeNeodeAdapter, [IOGCompositeNode], ICompositeNode)

##
# Functions that can be attached to old nodes to enable neode-style navigation.
def _get_parent(self):
    return self.parent
def _get_name(self):
    return self.name
def _get_nodespace(self):
    return self.nodespace
def _get_url(self):
    if self.__url is None:
        self.__init_urls()
    return self.__url
def _get_absolute_url(self):
    if self.__absolute_url is None:
        self.__init_urls()
    return self.__absolute_url
def _init_urls(self):
    parent_url = ''
    parent_absolute = ''
    if self.parent:
        parent_url = self.parent.url
        parent_absolute = self.parent.absolute_url
    self.__url = path.join(parent_url, self.name)
    self.__absolute_url = path.join(parent_absolute, self.name)
def _get_index(self, child):
    names = self.children_names()
    names.sort()
    return names.index(child.name)
def _add_child(self, node):
    result = self.__add_child(node)
    nodeurl = path.join(self.url, node.name)
    self.nodespace.add_node(node, nodeurl)
    if not IConfigurableNode.providedBy(node):
        node.__url = node.__absolute_url = nodeurl
        neodify(self.nodespace, node)
    return nodeurl
def _remove_child(self, child):
    if not isinstance(child, str): child = child.name
    childnode = self._children[child]
    childurl = childnode.url
    del(self._children[child])
    self.nodespace.remove_node(childnode, childurl)
def _prune(self):
    result = self.__prune()
    self.__url = None
    self.__absolute_url = None
    self.nodespace.remove_node_url(urllib.unquote(self._pruned_url))
    return result
def _configure(self, config):
    self.__absolute_url = None
    self.__url = None
    return self.__configure(config)

def neodify(nodespace, node, url = None):
    """
        Add functions and properties to node object needed
        to facilitate neode-like navigation.  The following
        attributes will be added to node 'node':

        get_nodespace(), nodespace
        get_parent()
        get_name()
        get_url(), url
        get_absolute_url(), absolute_url
    """
    added = []
    nodetype = type(node)
    if not hasattr(node, 'nodespace'):
        setattr(node, 'nodespace', nodespace)
        added.append('nodespace')

    if not hasattr(node, '__url'):
        setattr(node, '__url', None)
        added.append('__url')

    if not hasattr(node, '__absolute_url'):
        setattr(node, '__absolute_url', None)
        added.append('__absolute_url')

    if not hasattr(node, 'get_nodespace'):
        setattr(nodetype, 'get_nodespace', _get_nodespace)
        added.append('get_nodespace')

    if not hasattr(node, 'get_parent'):
        setattr(nodetype, 'get_parent', _get_parent)
        added.append('get_parent')

    if not hasattr(node, 'get_name'):
        setattr(nodetype, 'get_name', _get_name)
        added.append('get_name')

    if not hasattr(node, 'get_index'):
        setattr(nodetype, 'get_index', _get_index)
        added.append('get_index')

    if not hasattr(node, '__init_urls'):
        setattr(nodetype, '__init_urls', _init_urls)
        added.append('__init_urls')

    if not hasattr(node, 'get_url'):
        setattr(nodetype, 'get_url', _get_url)
        setattr(nodetype, 'url', property(_get_url))
        added.append('get_url')
        added.append('url')

    if not hasattr(node, 'get_absolute_url'):
        setattr(nodetype, 'get_absolute_url', _get_absolute_url)
        setattr(nodetype, 'absolute_url', property(_get_absolute_url))
        added.append('get_absolute_url')
        added.append('absolute_url')

    if not hasattr(nodetype, '__prune') and hasattr(nodetype, 'prune'):
        setattr(nodetype, '__prune', nodetype.prune)
        setattr(nodetype, 'prune', _prune)
        added.append('wrapped prune')

    if not hasattr(nodetype, '__add_child') and hasattr(nodetype, '_add_child'):
        setattr(nodetype, '__add_child', nodetype._add_child)
        setattr(nodetype, '_add_child', _add_child)
        setattr(nodetype, 'add_child', _add_child)
        added.append('wrapped _add_child')
        added.append('add_child')

    if not hasattr(node, 'remove_child'):
        setattr(nodetype, 'remove_child', _remove_child)
        added.append('_remove_child')

    if not hasattr(nodetype, '__configure') and hasattr(nodetype, 'configure'):
        setattr(nodetype, '__configure', nodetype.configure)
        setattr(nodetype, 'configure', _configure)
        added.append('wrapped configure')

    print 'neodify("%s"): %s\n' % (url or node.url, added)

def timeit(function, args, iterations = 1000):
    iteration = 0
    t1 = time.time()
    while (iteration < iterations):
        function(*args)
        iteration += 1
    t2 = time.time()
    elapsed = t2 - t1
    print 'Timeit: %s invocations:' % iterations
    print '\tTotal time elapse: %s sec' % elapsed
    print '\tAverage time per invocation: %s sec.' % (elapsed/iterations)
    return elapsed

def is_configured(object):
    return object.is_configured()

def is_enabled(object):
    return object.is_enabled()

def node_id(object):
    """
        Return '__node_id__' attr if object has one,
        otherwise return None.
    """

def name(object):
    return object.name

def parent(object):
    return object.parent

def from_path(path, as_internal_node = 0, relative_to = None):
    """
        Get a reference to node specified by URL 'path.'
    """

def is_node_url(value):
    """
        Return 1 if value 'value' is string and
        contains a URL to an existing node.
    """

def as_node(value, relative_to = None):
    """
        Return node public interface referenced by value 'value.'

        Value of 'value' may be a URL or a node reference.
        If 'value' is a node reference, it will be returned
        as is.
    """

def as_internal_node(value, relative_to = None):
    """
        Return actual node reference following
        same semantics as 'as_node.'
    """

def as_deferred_node(value, relative_to = None):
    """
        Return deferred node object, following
        same semantics as 'as_node.'
    """

def reload_node(node):
    """
        Try stopping node 'node,' reloading
        source module of where node's class is
        defined, reistantiating and reconfiguring
        'node'.
    """


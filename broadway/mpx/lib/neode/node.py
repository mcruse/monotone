"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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
import urllib
from os import path
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.lib.configure import as_boolean
from mpx.lib.node import as_node as _og_as_node
from mpx.lib.exceptions import ENoSuchName
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import provided_by
from mpx.componentry import register_utility
from mpx.componentry import query_utility
from mpx.componentry.bases import OrderedCollection
from mpx.componentry.backports import WeakValueDictionary
from mpx.componentry.backports import Dictionary
from interfaces import INode
from interfaces import IConfigurableNode
from interfaces import ICompositeNode
from interfaces import IRootNode
from interfaces import INodeSpace
from interfaces import IParentNode
import tools

class NodeSpace(object):
    implements(INodeSpace)

    def __init__(self, location = '', *args, **kw):
        self.__nodetree = Dictionary()
        self.__url = location
        super(NodeSpace, self).__init__(*args, **kw)

    def __get_node_tree(self):
        return Dictionary(self.__nodetree)
    nodetree = property(__get_node_tree)

    def __get_url(self):
        return self.__url
    url = property(__get_url)

    def __get_root(self):
        return self.as_node('/')
    root = property(__get_root)

    def as_node(self, path):
        if not isinstance(path, str) and hasattr(path, 'url'):
            path = path.url
        node = self.__nodetree.get(path)
        if not node:
            node = IConfigurableNode(_og_as_node(path))
        return node

    def as_node_collection(self, paths):
        nodes = map(self.as_node, paths)
        return OrderedCollection(nodes)

    def as_internal_node(self, path):
        return self.as_node(path)

    def as_node_url(self, node):
        if isinstance(node, str) and self.__nodetree.has_key(node):
            return node
        else: return self.as_node(node).url

    def as_node_url_collection(self,nodes):
        urls = map(self.as_node_url, nodes)
        return OrderedCollection(urls)

    def create_node(self,factory):
        return factory(self)

    def add_node(self, node, url = None):
        if url is None:
            url = node.url
        assigned = self.__nodetree.setdefault(url, node)
        if assigned is not node:
            raise ValueError('URL "%s" already taken' % url)
        return url

    def remove_node(self, node, url = None):
        if url is None: url = self.as_node_url(node)
        elif self.as_node(url) is not node:
            raise ValueError('Node at %s is not node provided' % url)
        return self.__nodetree.pop(url)

class ConfigurableNode(object):
    implements(IConfigurableNode)
    enabled = 1
    debug = 0

    def __init__(self,nodespace = None,*args,**kw):
        self.__nodespace = nodespace
        self.__name = None
        self.__parent = None
        self.__url = None
        self.__absolute_url = None
        self.__running = False
        super(ConfigurableNode, self).__init__(*args, **kw)

    def configure(self, config):
        self.__nodespace = config.get('nodespace', self.nodespace)
        if not self.nodespace:
            self.__nodespace = rootspace
        self.enabled = as_boolean(config.get('enabled', self.enabled))
        self.debug = as_boolean(config.get('debug', self.debug))
        self.name = config.get('name', self.name)
        parent = config.get('parent')
        if parent is not None:
            parent = self.nodespace.as_node(parent)
            self.parent = parent
        return self.is_configured()

    def configuration(self):
        config = {}
        if self.parent:
            config['parent'] = self.parent.url
        if self.name:
            config['name'] = self.name
        config['debug'] = str(self.debug)
        config['enabled'] = str(self.enabled)
        return config

    def is_configured(self):
        return self.name and self.parent

    ##
    # Parent property management.
    def get_parent(self):
        return self.__parent
    def set_parent(self, parent):
        previous = self.parent
        if parent is not previous:
            if previous is not None:
                previous.remove_child(self)
                self.__url = None
            if parent is not None:
                self.__url = parent.add_child(self)
        self.__parent = parent
    parent = property(get_parent, set_parent)

    ##
    # Name property management.
    def get_name(self):
        return self.__name
    def set_name(self, name):
        previous = self.name
        self.__name = name
        if previous != name and self.parent:
            try: self.__url = self.parent.rename_child(self, previous)
            except:
                self.__name = previous
                raise
        return
    name = property(get_name, set_name)

    def get_nodespace(self):
        return self.__nodespace
    nodespace = property(get_nodespace)

    def get_url(self):
        return self.__url
    url = property(get_url)

    def get_absolute_url(self):
        if self.__absolute_url is None:
            self.__absolute_url = path.join(
                self.parent.absolute_url, self.name)
        return self.__absolute_url
    absolute_url = property(get_absolute_url)

    def enable(self): self.enabled = 1
    def disable(self): self.enabled = 0
    def is_enabled(self): return self.enabled
    def reset(self): raise Exception('"reset()" not implemented.')
    def start(self): 
        self.__running = True
    def stop(self): 
        self.__running = False
    def is_running(self):
        return self.__running

    def setattr(self,name,value,conversion=None):
        if conversion is not None:
            value = conversion(value)
        setattr(self,name,value)

    def delattr(self,name):
        delattr(self,name)

    def getattr(self,name,conversion=None):
        attr = getattr(self,name)
        if conversion is not None:
            attr = conversion(attr)
        return attr

    def hasattr(self,name):
        return hasattr(self,name)

    def has_method(self,name):
        if not self.hasattr(name):
            return False
        else:
            return callable(self.getattr(name))

    def get_method(self,name):
        if not self.has_function(name):
            raise AttributeError('No function named "%s".' % name)
        return self.getattr(name)
    
    def provides_interface(self, interface):
        if isinstance(interface, str):
            try:
                eval(interface)
            except NameError:
                module,sep,datatype = interface.rpartition(".")
                if not module:
                    raise
                exect("import " + module)
            interface = eval(interface)
        return interface.providedBy(self)
    
    def get_interfaces(self, named=False):
        interfaces = list(provided_by(self))
        if named:
            items = []
            for interface in interfaces:
                items.append((interface.__module__, interface.__name__))
                interfaces = [".".join(item) for item in items]
        return interfaces

    def prune(self):
        self.stop()
        self.disable()
        self.parent = None
        self.name = None

    ##
    # Only implemented so that NodeBrowser won't barf...
    def as_node(self, path = None):
        if path is None: node = self
        else: node = self.nodespace.as_node(path)
        return node
    def as_node_url(self):
        return self.url


class CompositeNode(ConfigurableNode):
    implements(ICompositeNode)
    STARTCHILDFAILURE = '"%s" failed to start child "%s".'
    STOPCHILDFAILURE = '"%s" failed to stop child "%s".'
    PRUNECHILDFAILURE = '"%s" failed to stop child "%s".'

    def __init__(self, *args, **kw):
        self.__children = Dictionary()
        self.__nameorder = []
        super(CompositeNode, self).__init__(*args, **kw)

    def __get_children(self):
        return self.__children.copy()
    children = property(__get_children)

    def children_nodes(self):
        return map(self.__children.get, self.__nameorder)

    def children_names(self):
        return self.__nameorder[:]

    def create_child(self, factory, name):
        if self.has_child(name):
            raise ValueError('Child named "%s" exists.' % name)
        child = factor(self.nodespace)
        child.configure({'name': name, 'parent': self})
        return self.get_child(name)

    def add_child(self,node):
        if not IConfigurableNode.providedBy(node):
            raise TypeError('node is not IConfigurableNode')
        child = self.__children.setdefault(node.name, node)
        if child is not node:
            raise ValueError('Child "%s" already exists.' % node.name)
        self.__nameorder.append(node.name)
        childurl = path.join(self.url, child.name)
        self.nodespace.add_node(child, childurl)
        return childurl

    def rename_child(self, child, oldname):
        if self.get_child(oldname) is not child:
            raise ValueError('Child with name %s it not same' % oldname)
        index = self.get_index(oldname)
        nodeurl = self.add_child(child)
        self.remove_child(child, oldname)
        # Preserve the child's position.
        self.__nameorder.remove(child.name)
        self.__nameorder.insert(index, child.name)
        return nodeurl

    def remove_child(self, node, name = None):
        if name is None:
            name = node.name
        self.__nameorder.remove(name)
        self.__children.pop(name)
        nodeurl = path.join(self.url, name)
        self.nodespace.remove_node(node, nodeurl)

    def prune(self):
        for child in self.children_nodes():
            try: child.prune()
            except:
                try: message = self.PRUNECHILDFAILURE % (self.url, child.name)
                except: msglog.exception(prefix = 'Handled')
                else: msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        return super(CompositeNode, self).prune()

    def prune_child(self, node):
        self.get_child(node).prune()

    def start(self):
        result = super(CompositeNode, self).start()
        for child in self.children_nodes():
            try: child.start()
            except:
                try: message = self.STARTCHILDFAILURE % (self.url, child.name)
                except: msglog.exception(prefix = 'Handled')
                else: msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        return result

    def stop(self):
        for child in self.children_nodes():
            try: child.stop()
            except:
                try: message = self.STOPCHILDFAILURE % (self.url, child.name)
                except: msglog.exception(prefix = 'Handled')
                else: msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        return super(CompositeNode, self).stop()

    def has_child(self, child):
        return self.__children.has_key(child) or (child in self.children_nodes())

    def get_index(self, child):
        if not isinstance(child, str):
            child = child.name
        return self.__nameorder.index(child)

    def get_child(self, child):
        if not isinstance(child, str):
            child = child.name
        c = self.__children
        if c.has_key(child):
            return c[child]
        raise ENoSuchName(child)

    def descendants_nodes(self):
        nodes = self.children_nodes()
        count = len(nodes)
        for child in nodes[0:count]:
            if IParentNode.providedBy(child):
                nodes.extend(child.descendants_nodes())
        return nodes

    def descendants_names(self):
        nodes = self.descendants_nodes()
        return [node.name for node in nodes]

class RootNode(CompositeNode):
    implements(IRootNode)

    def configure(self, config):
        if not config.has_key('name'):
            raise ValueError(
                'Configuration missing required "name": %s' % config)
        self.__name = config['name']
        self.__parent = None
        self.nodespace.add_node(self, self.url)
        return self.is_configured()

    def configuration(self):
        return {'name':self.name, 'parent':None}

    def is_configured(self):
        if not self.name: return False
        as_node = self.nodespace.as_node(self.url)
        return self is as_node

    def get_url(self):
        return self.url

    def __get_name(self):
        return '/'

    def __set_name(self,name):
        if name != '/':
            raise TypeError('Root Node name is always "/"')
        return

    url = name = property(__get_name,__set_name)

    def get_absolute_url(self):
        # Root NodeSpace has URL '', so we use
        #   self.name if NodeSpace URL is empty
        #   otherwise absolute_url doesn't start with '/'
        url = self.nodespace.url or self.name
        return path.join(url, '')
    absolute_url = property(get_absolute_url)

    def singleton_unload_hook(self):
        pass

rootspace = None
if not query_utility(INodeSpace, 'Root'):
    register_utility(NodeSpace(), INodeSpace, 'Root')
rootspace = query_utility(INodeSpace, 'Root')
tools.setup_hybrid_architecture(rootspace)

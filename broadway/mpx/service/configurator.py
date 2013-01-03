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
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.lib.persistence.datatypes import PersistentDictionary
Undefined = object()

def pathcompare(path1, path2):
    """
        Sort node URLs such that parents always come 
        before descendants.
    """
    return cmp(path1.count("/"), path2.count("/"))

class NodeConfigurator(CompositeNode):
    def __init__(self, *args, **kw):
        self.nodes = None
        super(NodeConfigurator, self).__init__(*args, **kw)
    def start(self):
        if self.nodes is None:
            dictname = "%s (%s)" % (type(self).__name__, self.name)
            self.nodes = PersistentDictionary(dictname)
            nodeurls = self.nodes.keys()
            nodeurls.sort(pathcompare)
            for nodeurl in nodeurls:
                nodedata = self.nodes[nodeurl]
                factory,configuration = nodedata
                self.create_node(factory, nodeurl, **configuration)
        super(NodeConfigurator, self).start()
    def get_managed_node(self, nodeurl):
        if not self.nodes.has_key(nodeurl):
            raise TypeError("cannot manipulate unmanaged node: %s" % nodeurl)
        return as_node(nodeurl)
    def node_children(self, nodeurl):
        node = self.get_managed_node(nodeurl)
        return node.children_names()
    def node_configuration(self, nodeurl):
        node = self.get_managed_node(nodeurl)
        return node.configuration()
    def start_node(self, nodeurl):
        node = self.get_managed_node(nodeurl)
        node.start()
    def stop_node(self, nodeurl):
        node = self.get_managed_node(nodeurl)
        node.stop()
    def node_attr(self, nodeurl, name, value=Undefined):
        node = self.get_managed_node(nodeurl)
        if value is not Undefined:
            setattr(node, name, value)
            self.updatepdo(nodeurl, node)
        return getattr(node, name)
    def configure_node(self, nodeurl, config):
        node = self.get_managed_node(nodeurl)
        node.stop()
        try:
            node.configure(config)
        except:
            msglog.log("broadway", msglog.types.WARN, 
                       "Error prevented reconfiguration of node: %s" % node)
            msglog.exception(prefix="handled")
            msglog.log("broadway", msglog.types.WARN, 
                       "Rolling back configuration.")
            try:
                node.configure(self.nodes[nodeurl])
            except:
                msglog.log("broadway", msglog.types.WARN, 
                           "Configuration rollback failed.")
                msglog.exception(prefix="handled")
            else:
                msglog.log("broadway", msglog.types.INFO, 
                           "Rollback of configuration succeeded.")
        else:
            msglog.log("broadway", msglog.types.INFO, 
                       "Node reconfigured: %s" % node)
            self.updatepdo(nodeurl, node)
        finally:
            node.start()
        return node.configuration()
    def create_node(self, factory, nodeurl, **config):
        try:
            as_node(nodeurl)
        except KeyError:
            pass
        else:
            raise TypeError("Node exists: %s" % nodeurl)
        if isinstance(factory, str):
            module,sep,name = factory.rpartition(".")
            if name:
                exec("import %s" % module)
            factory = eval(factory)
        parent,sep,name = nodeurl.rpartition("/")
        configuration = {"name": name, "parent": parent}
        configuration.update(config)
        node = factory()
        try:
            node.configure(configuration)
        except:
            msglog.log("broadway", msglog.types.WARN, 
                       "Error prevented configuration of new node: %s" % node)
            msglog.exception(prefix="handled")
            try:
                node.prune()
            except:
                msglog.exception(prefix="handled")
            else:
                msglog.log("broadway", msglog.types.INFO, 
                           "Node successfully pruned.")
        else:
            msglog.log("broadway", msglog.types.INFO, 
                       "New node created: %s" % node)
            self.updatepdo(nodeurl, node)
            node.start()
        return node.configuration()
    def remove_node(self, nodeurl):
        node = self.get_managed_node(nodeurl)
        node.prune()
        self.updatepdo(nodeurl, None)
    def updatepdo(self, nodeurl, node):
        if self.nodes.has_key(nodeurl):
            self.nodes.pop(nodeurl)
        if node:
            node = as_node(node)
            nodeurl = as_node_url(node)
            datatype = type(node)
            factory = "%s.%s" % (datatype.__module__, datatype.__name__)
            data = (factory, node.configuration())
            self.nodes[nodeurl] = (factory, node.configuration())
        return nodeurl


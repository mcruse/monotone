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
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.interfaces import IPickles
from mpx.componentry.bases import OrderedCollection
from interfaces import IInspectable
from interfaces import IModifiable
from interfaces import IExtendedModifiable
from interfaces import IExtendedInspectable
from interfaces import INodeSpace
from interfaces import IConfigurableNode
from interfaces import ICompositeNode
from tools import OGConfigurableNeodeAdapter
import node as _node

class ConfigurableNodePickler(object):
    implements(IPickles)
    adapts(IConfigurableNode)

    def __init__(self, node):
        self.node = node
    def __getstate__(self):
        node = self.node
        while isinstance(node, OGConfigurableNeodeAdapter):
            node = node.node
        state = {'class': type(node),
                 'url': self.node.url,
                 'config': self.node.configuration()}
        return state
    def __setstate__(self, state):
        self.node = None
        self.state = state
    def __call__(self):
        if self.node is None:
            try:
                self.node = _node.rootspace.as_node(self.state['url'])
            except KeyError: self.node = self.state.get('class')()
            else:
                try: self.node.stop()
                except: pass
            config = self.state['config']
            parent = _node.rootspace.as_node(config['parent'])
            config.setdefault('nodespace', parent.nodespace)
            self.node.configure(config)
            self.node.start()
        return self.node

register_adapter(ConfigurableNodePickler)


class ExtendedInspectableAdapter(object):
    implements(IExtendedInspectable)
    adapts(IInspectable)

    def __init__(self, inspectable):
        self.context = inspectable

    def getattr(self, name):
        return self.context.getattr(name)

    def hasattr(self, name):
        return self.context.has_attr(name)

    def has_method(self, name):
        return self.context.has_method(name)

    def get_method(self, name):
        return self.context.get_method(name)

    def getattrs(self,names,conversions=[]):
        if not conversions:
            conversions = [None] * len(names)
        return map(self.getattr,names,conversions)

    def hasattrs(self,names):
        return map(self.hasattr,names)

    def has_methods(self,names):
        return map(self.has_method,names)

    def get_methods(self,names):
        return map(self.get_method,names)

class ExtendedModifiableAdapter(object):
    implements(IExtendedModifiable)
    adapts(IModifiable)

    def __init__(self, inspectable):
        self.context = inspectable

    def setattr(self,name,value,conversion=None):
        self.context.setattr(name,value,conversion)

    def delattr(self,name):
        self.context.delattr(name)

    def setattrs(self,names,values,conversions=[]):
        if not conversions:
            conversions = [None] * len(names)
        map(self.setattr,names,values,conversions)

    def delattrs(self,names):
        map(self.delattr,names)

register_adapter(ExtendedInspectableAdapter)
register_adapter(ExtendedModifiableAdapter)

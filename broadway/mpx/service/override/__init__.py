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
import weakref
from mpx.componentry import implements
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.neode.interfaces import ISettable
from mpx.lib.neode.interfaces import IOverridable
from mpx.lib.neode.node import CompositeNode
from interfaces import IOverrideService
from adapters import OverridablePoint

class TimedOverrideService(CompositeNode):
    implements(IOverrideService)

    def __init__(self, *args):
        self._cache = weakref.WeakValueDictionary()
        super(TimedOverrideService, self).__init__(*args)

    def configure(self, config):
        super(TimedOverrideService, self).configure(config)

    def configuration(self):
        config = super(TimedOverrideService, self).configuration()
        return config

    def start(self):
        root = self.nodespace.as_node('/')
        self.lazyroot = AdaptOnUseNode(root, self.url, self.as_overridable_node)
        return super(TimedOverrideService, self).start()

    def stop(self):
        self.lazyroot = None
        self._cache.clear()
        return super(TimedOverrideService, self).stop()

    def as_overridable_node(self, node):
        node = self.nodespace.as_node(node)
        overridable = self._cache.get(node.url)
        if overridable is None:
            try:
                overridable = IOverridable(node)
            except TypeError:
                if hasattr(node, 'set'):
                    overridable = OverridablePoint(node, self.url)
                else:
                    message = 'Must provide IOverridable or have "set" method.'
                    raise TypeError(message)
        overridable = self._cache.setdefault(node.url, overridable)
        return overridable

    def has_child(self, name, **options):
        return self.lazyroot.has_child(name, **options)

    def get_child(self, name, **options):
        return self.lazyroot.get_child(name, **options)

class AdaptOnUseNode(object):
    implements(ICompositeNode)

    def __init__(self, context_node, virtual_root, adapt):
        self._context = context_node
        self._vroot = virtual_root
        self._adapt = adapt
        self._adapted = None
        self._urlbase = None

    def __get_name(self):
        return self._context.name
    name = property(__get_name)

    def __get_parent(self):
        parent = self._context.parent
        if parent is not None:
            parent = self.copy_for(parent)
        return parent
    parent = property(__get_parent)

    def __get_url(self):
        if self._urlbase is None:
            if isinstance(self._vroot, str):
                self._urlbase = self._vroot
            else:
                self._urlbase = self._vroot.url
        return self._urlbase + self._context.url
    url = property(__get_url)

    def __get_adapted_node(self):
        if self._adapted is None:
            self._adapted = self._adapt(self._context)
        return self._adapted
    adapted_node = property(__get_adapted_node)

    def has_child(self, name, **options):
        return self._context.has_child(name, **options)

    def get_child(self, name, **options):
        node = self._context.get_child(name, **options)
        return self.copy_for(node)

    def __getattr__(self, name):
        return getattr(self.adapted_node, name)

    def copy_for(self, context):
        return type(self)(context, self._vroot, self._adapt)
    
    def __eq__(self, other):
        return self.url == other.url

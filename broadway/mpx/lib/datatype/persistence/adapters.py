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
import inspect
import threading
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.lib.neode import node
from mpx.lib.node import as_node_url
from mpx.lib.node import as_internal_node
from mpx.componentry import Interface
from mpx.componentry import register_adapter
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import ComponentLookupError
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.datatype.persistence.interfaces import IPersistent
from mpx.lib.datatype.persistence.interfaces import IPickleable
from mpx.lib.datatype.persistence.interfaces import IPersistentObject
from mpx.lib.neode.tools import OGConfigurableNeodeAdapter
from mpx.lib.neode.tools import IOGConfigurableNode
from mpx.lib.neode.tools import IOGCompositeNode
from mpx.lib.datatype.utility import DeferredObject
from mpx.service.alarms2.interfaces import IAlarm

class PersistentAdapter(object):
    implements(IPersistentObject)
    adapts(None)
    
    def __new__(klass, instance):
        adapter = getattr(instance, '__persistenceAdapter__', None)
        if not adapter:
            isclass = inspect.isclass(instance)
            if not isclass and not IPersistent.providedBy(instance):
                raise ComponentLookupError(
                    '%s must povide IPersistent.' % (instance))
            adapter = super(PersistentAdapter, klass).__new__(klass, instance)
            adapter.initialize(instance)
            if not isclass:
                instance.__persistenceAdapter__ = adapter
        return adapter
    def initialize(self, instance):
        self.loaded = None
        self.saved = None
        self.persistent = None
        self.instance = instance
        self.enable_persistence()
    def get_manager(self):
        return getattr(self.instance, '__persistenceManager__', None)
    def set_manager(self, manager):
        current = self.get_manager()
        if not ((current is None) or (current is manager)):
            raise TypeError('Manager cannot be changed unles cleared.')
        self.instance.__persistenceManager__ = manager
    def clear_manager(self):
        if self.get_manager():
            if not self.is_saved():
                raise TypeError('Cannot clear manager for unsaved instance.')
            self.instance.__persistenceManager__ = None
        self.disable_persistence()
    def get_oid(self):
        return getattr(self.instance, '__persistenceOID__', None)
    def set_oid(self, oid):
        current = self.get_oid()
        if not ((current is None) or (current == oid)):
            raise TypeError('Persistent OID cannot be changed.')
        self.instance.__persistenceOID__ = oid
    def set_loaded(self): 
        self.loaded = True
    def set_unloaded(self): 
        self.loaded = False
    def set_saved(self): 
        self.saved = True
    def set_unsaved(self): 
        self.saved = False
    def enable_persistence(self):
        self.persistent = True
    def disable_persistence(self):
        self.persistent = False
    def is_saved(self):
        return self.saved
    def is_loaded(self):
        return self.loaded
    def is_persistent(self):
        return self.persistent
    def get_object(self):
        return self.instance
    def note_change(self):
        self.set_unsaved()
        if self.is_persistent():
            self.get_manager().note_modified(self)
        return

class Pickleable(object):
    implements(IPickleable)
    adapts(IPersistent)
    
    excludes = {'__dict__':None, '__weakref__': None}
    context = None
    
    def __init__(self, context):
        self.contexttype = type(context)
        self.contextstate = context.__dict__
        self.context = context
    def __getstate__(self):
        names = filter(self.should_persist, self.contextstate.keys())
        values = map(self.contextstate.get, names)
        return {'type': self.contexttype, 'state': dict(zip(names, values))}
    def __setstate__(self, state):
        print 'Pickleable.__setstate__'
        contexttype = state['type']
        contextstate = state['state']
        print '\tContext type: %s' % (contexttype,)
        print '\tState: %s' % (contextstate,)
        context = self.instantiate(contexttype)
        context.__dict__.update(contextstate)
        self.contexttype = contexttype
        self.contextstate = context.__dict__
        self.context = context
        print 'Pickleable instantiated %s' % self.context.name
    def instantiate(self, contexttype):
        return contexttype.__new__(contexttype)
    def write_object(self):
        return self
    def read_object(self):
        print 'Pickleable %s read object %s' % (self, self.context)
        return self.context
    def should_persist(self, key):
        return not (self.excludes.has_key(key) or 
                    key.startswith('__persistence'))

class PickleableConfigurableNode(Pickleable):
    adapts(IConfigurableNode)
    privatevars = ['_ConfigurableNode__name', 
                   '_ConfigurableNode__parent', 
                   '_ConfigurableNode__url', 
                   '_ConfigurableNode__absolute_url']
    excludevars = ['name', 'parent', 'url']
    
    def __init__(self, context):
        print 'Pickleable type %s being used for %s' % (self, as_node_url(context))
        while isinstance(context, OGConfigurableNeodeAdapter):
            context = context.node
        super(PickleableConfigurableNode, self).__init__(context)
    def __getstate__(self):
        nodeurl = as_node_url(self.context)
        configstate = self.context.configuration()
        for varname in self.excludevars:
            if configstate.has_key(varname):
                del(configstate[varname])
        privatestate = dict([(varname, getattr(self.context, varname)) 
                             for varname in self.privatevars])
        return {'type': self.contexttype, 
                'state': privatestate, 
                'nodeconfig': configstate, 
                'nodeurl': nodeurl}
    def __setstate__(self, statedict):
        self.context = None
        self.statedict = statedict
    def instantiate(self, contenttype):
        return contenttype()
    ###
    # Note, there is some overlap here that I'm not fond of.
    # This method is called when a DeferredObject attempts 
    # to initialize itself with the instance it represents.
    #            
    # References to the DeferredObject itself are in things 
    # like the children nodes of other nodes.
    #            
    # The context instance created by this method is the actual 
    # instance, and not the DeferredObject representing it.
    #            
    # The problem is that, because we are doing a configure here, 
    # we are calling configure on the actual instance and not 
    # the DeferredObject.  This can be problematic when, say, 
    # a child being configured goes to add itself to its parent, 
    # which already has a child with that name that refers to the 
    # DeferredObject, does an identity check to determine whether 
    # the child being added IS the child that already exists.
    #             
    # I believe the solution will be related to separating the 
    # call to configure from the reading of the object performed here.
    def read_object(self):
        if self.context is None:
            nodeurl = self.statedict['nodeurl']
            print '%s read_object for %s' % (self, nodeurl)
            try:
                context = as_internal_node(nodeurl)
                if isinstance(context, DeferredObject):
                    raise KeyError(nodeurl)
                self.context = context
            except KeyError: 
                print '\tcreating node'
                super(PickleableConfigurableNode, self).__setstate__(self.statedict)
            else:
                print '\tnode already existed, setting up'
                contextstate = self.statedict['state']
                # Ugly inefficient hack to work with ReloadableSingleton, 
                # which wraps the ROOT node and delegates getattr and 
                # setattr to the wrapped node.  This, of course, fails 
                # if the instance's __dict__ is used directly to modify 
                # the state.
                for name,value in contextstate.items():
                    setattr(self.context, name, value)
            nodeconfig = self.statedict['nodeconfig']
            print '\tcofigure node with %s' % nodeconfig
            try:
                self.context.configure(nodeconfig)
            except:
                msglog.exception()
        return self.context

class PickleableAlarm(PickleableConfigurableNode):
    adapts(IAlarm)
    privatevars = PickleableConfigurableNode.privatevars[:]
    privatevars += ['events']

class PickleableOGConfigurableNode(PickleableConfigurableNode):
    adapts(IOGConfigurableNode)
    privatevars = ['name', 'parent']
    excludevars = ['name', 'parent']

class PickleableCompositeNode(PickleableConfigurableNode):
    adapts(ICompositeNode)
    privatevars = PickleableConfigurableNode.privatevars[:]
    privatevars += ['_CompositeNode__children', '_CompositeNode__nameorder']

class PickleableOGCompositeNode(PickleableOGConfigurableNode):
    adapts(IOGCompositeNode)
    privatevars = PickleableOGConfigurableNode.privatevars[:]
    privatevars += ['_children']
    def __init__(self, context):
        super(PickleableOGCompositeNode, self).__init__(context)
        context._children = getattr(context, '_children', {})

register_adapter(Pickleable)
register_adapter(PersistentAdapter)
register_adapter(PickleableConfigurableNode, IConfigurableNode, IPickleable)
register_adapter(PickleableOGConfigurableNode, IOGConfigurableNode, IPickleable)
register_adapter(PickleableCompositeNode, ICompositeNode, IPickleable)
register_adapter(PickleableOGCompositeNode, IOGCompositeNode, IPickleable)
register_adapter(PickleableAlarm, IAlarm, IPickleable)

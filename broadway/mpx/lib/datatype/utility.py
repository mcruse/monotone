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
import weakref
from mpx.lib import msglog
##
#  Stand-in object for lazily initialized instances.  
#  Take factory function and arguments as parameter(s) 
#  for initialization.  Object then captures any attempt 
#  to access or modify an attribute, any attribute, and 
#  uses the factory function to create instance of desired 
#  object.  DeferredObject then "morphs" into instance returned 
#  by factory by assigning the instance's type as its own, and 
#  replacing it's own dictionary with that of the instance.
class DeferredObject(object):
    def __init__(self, factory, *arguments):
        initdata = {'factory': factory, 
                    'arguments': arguments, 
                    'initializing': False}
        object.__setattr__(self, 'initdata', initdata)
    def initialize(self, instance = None):
        initdata = object.__getattribute__(self, 'initdata')
        if initdata.get('initializing'):
            raise TypeError('DeferredObject initializing, may cause infinite loop.')
        initdata['initializing'] = True
        try:
            if instance is None:
                factory = initdata.get('factory')
                arguments = initdata.get('arguments')
                instance = factory(*arguments)
        finally:
            initdata['initializing'] = False
        object.__setattr__(self, '__class__', instance.__class__)
        object.__setattr__(self, '__dict__', instance.__dict__)
        initdata.clear()
    def __getattribute__(self, name):
        print 'Initializing DeferredObject(%s) to get %s' % (id(self), name)
        object.__getattribute__(self, 'initialize')()
        return getattr(self, name)
    def __setattribute__(self, name, value):
        print 'Initializing DeferredObject(%s) to set %s to %s' % (id(self), name, value)
        object.__getattribute__(self, 'initialize')()
        return setattr(self, name, value)

class ObjectCache(object):
    def __init__(self, initcache = {}):
        self._cache = weakref.WeakValueDictionary()
        self._cache.update(initcache)
    def has_instance(self, oid):
        return self._cache.has_key(oid)
    def get_instance(self, oid, default = None):
        return self._cache.get(oid, default)
    def as_instance(self, oid):
        return self._cache[oid]
    def add_instance(self, oid, instance):
        self._cache[oid] = instance
    def delete_instance(self, oid):
        del(self._cache[oid])
    def discard_instance(self, oid):
        try: self.delete_instance(oid)
        except KeyError: 
            return False
        else: 
            return True
    def clear(self):
        self._cache.clear()

class CollectionIterator(object):
    def __init__(self, collection, asqueue = 0):
        self.collection = collection
        if asqueue: self.poparg = 0
        else: self.poparg = -1
    def __iter__(self):
        return self
    def next(self):
        if self.collection:
            return self.collection.pop(self.poparg)
        else: 
            raise StopIteration

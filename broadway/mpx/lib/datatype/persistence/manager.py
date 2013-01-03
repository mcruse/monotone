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
import types
import weakref
import inspect
from mpx.componentry import implements
from mpx.componentry import class_implements
from mpx.componentry import directly_provides
from mpx.lib.datatype.utility import ObjectCache
from mpx.lib.datatype.utility import DeferredObject
from mpx.lib.datatype.persistence.interfaces import IPersistenceManager
from mpx.lib.datatype.persistence.interfaces import IPersistentObject
from mpx.lib.datatype.persistence.interfaces import IStoragePolicy
from mpx.lib.datatype.persistence.interfaces import IPersistent
from mpx.lib.datatype.persistence.interfaces import IStorage
from mpx.lib.datatype.persistence.policy import StoragePolicy

_never_persistent = (type, int, float, 
                     long, tuple, 
                     types.ClassType, 
                     types.NoneType, 
                     types.FunctionType, 
                     types.MethodType) + types.StringTypes

class PersistenceManager(object):
    implements(IPersistenceManager)
    _UNIQUE = object()
    
    def __init__(self):
        self.__storage = None
        self.__policies = []
        self._transformation_reader = None
        self.reader_factory = None
        self.writer_factory = None
        self.add_policy(StoragePolicy())
        self.cache = ObjectCache()
    def get_cache(self):
        return self.cache
    def get_storage(self):
        return self.__storage
    def get_policy(self):
        return self.__policies[0]
    def get_policies(self):
        return self.__policies[:]
    def get_reader_factory(self):
        return self.reader_factory
    def get_writer_factory(self):
        return self.writer_factory
    def set_reader_factory(self, factory):
        self.reader_factory = factory
        self._transformation_reader = factory()
        self._transformation_reader.set_manager(self)
    def set_writer_factory(self, factory):
        self.writer_factory = factory
    def set_storage(self, storage):
        if not IStorage.providedBy(storage):
            raise TypeError('Storage instance must provide IStorage.')
        if self.storage is not None:
            self.storage.commit()
        self.__storage = storage
        storage.set_manager(self)
    def add_policy(self, policy):
        if not IStoragePolicy.providedBy(policy):
            raise TypeError('Policy instance must provide IStoragePolicy.')
        if policy in self.__policies:
            raise TypeError('Policy already exists in manager.')
        policy.set_manager(self)
        self.__policies.append(policy)
    def remove_policy(self, policy):
        if policy is self.__policies[0]:
            raise TypeError('Cannot remove default policy.')
        self.__policies.remove(policy)
    storage = property(get_storage, set_storage)    
    policy = property(get_policy)
    policies = property(get_policies)
    def new_oid(self):
        return self.storage.generate_oid()
    def get_oid(self, instance):
        print 'get_oid(%s)' % (instance,)
        if isinstance(instance, _never_persistent):
            print '\t-> None, is instance of _never_persistent'
            return None
        if type(instance) in (dict, list):
            print '\t-> None, type in dict, list'
            return None
        if not IPersistent.providedBy(instance):
            print '\t-> None, IPersistent not provided by instance'
            return None
        persistent = IPersistentObject(instance)
        if persistent.get_oid() is None:
            self._configure_persistence(persistent)
            persistent.set_loaded()
            persistent.set_unsaved()
        elif not persistent.is_persistent():
            print '\t-> None, not persistent.is_persistent()'
            return None
        oid = persistent.get_oid()
        print '\t%s OID => %s' % (instance, oid)
        return oid
    def _configure_persistence(self, persistent, oid = None):
        manager = persistent.get_manager()
        if manager is None:
            persistent.set_manager(self)
        elif manager is not self:
            raise TypeError('Object has different manager')
        if persistent.get_oid() is None:
            if oid is None:
                oid = self.new_oid()
            persistent.set_oid(oid)
        persistent.enable_persistence()
    def get_object(self, oid):
        print 'Getting %s' % oid
        if not self.cache.has_instance(oid):
            print '\tcreating deferred for %s' % oid
            deferred = DeferredObject(self.load, oid)
            self.cache.add_instance(oid, deferred)
        instance = self.cache.as_instance(oid)
        print '\tget_object(%s) -> %s' % (oid, instance)
        return instance
    def load(self, oid):
        print 'Loading %s' % oid
        instance = self.cache.get_instance(oid, None)
        if instance is None or isinstance(instance, DeferredObject):
            transformation = self.storage.load_record(oid)
            instance = self._transformation_reader.read(transformation)
            persistent = IPersistentObject(instance)
            self._configure_persistence(persistent, oid)
            persistent.set_loaded()
            persistent.set_saved()
            instance = persistent.get_object()
        else: 
            print '\tloaded from cache!'
        print '\tload(%s) -> %s' % (oid, instance)
        return instance
    def store(self, instance):
        written = {}
        persistent = IPersistentObject(instance)
        oid = persistent.get_oid()
        instance = persistent.get_object()
        print 'Store %s with OID %s' % (instance, oid)
        transformation_writer = self.writer_factory(instance)
        transformation_writer.set_manager(self)
        for instance in transformation_writer:
            persistent = IPersistentObject(instance)
            oid = persistent.get_oid()
            if written.has_key(oid):
                continue
            if persistent.is_persistent() and not persistent.is_saved():
                instance = persistent.get_object()
                transformation = transformation_writer.write(instance)
                print '\t-> storing %s with OID %s' % (instance, oid)
                self.storage.store_record(oid, transformation)
                written[oid] = None
                persistent.set_saved()
                self.cache.add_instance(oid, instance)
            else: print '\t-> not storing %s with OID %s' % (instance, oid)
    def make_persistent(self, instance):
        print 'Make persistent called with %s' % (instance,)
        if not IPersistent.providedBy(instance):
            print '\tIPersistent not provided, directly providing'
            directly_provides(instance, IPersistent)
        persistent = IPersistentObject(instance)
        self._configure_persistence(persistent)
        persistent.set_unsaved()
        self.notify_modified(instance)
    def make_persistent_type(self, klass):
        if not inspect.isclass(klass):
            raise TypeError('Argument must be class.')
        if not IPersistent.implementedBy(klass):
            class_implements(klass, IPersistent)
    def make_transient(self, instance):
        persistent = IPersistentObject(instance)
        persistent.disable_persistence()
        persistent.clear_manager()
    def commit_changes(self):
        for policy in self.policies:
            policy.commit()
    def commit_storage(self):
        self.storage.commit()
    def commit(self):
        self.commit_changes()
        self.commit_storage()
    def terminate(self):
        for policy in self.policies:
            policy.terminate()
        self.storage.terminate()
    def notify_modified(self, instance):
        persistent = IPersistentObject(instance)
        self.policy.note_modified(persistent)

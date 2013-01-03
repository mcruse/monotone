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
from mpx.componentry import Interface
from mpx.componentry import Attribute

class IPersistent(Interface):
    """
        Marker-interface indicating providers are first-class 
        persistence objects.
    """

class IPersistentObject(Interface):
    def set_oid(oid):
        """
            Set persistent object ID
        """
    
    def get_oid():
        """
            Get pesrsistent object ID.  Returns None if 
            not assigned.
        """
    
    def set_manager(manager):
        """
            Set persistent object manager.  Manager 'manager' 
            provides IPersistenceManager.  Manager may only be 
            set once; attempting to set a secon time raises TypeError.
        """
    
    def clear_manager():
        """
            Clear assigned manager.
        """
    
    def get_manager():
        """
            Get persistent object's persistence manager.
        """
    
    def note_change():
        """
            Note that the object's state has somehow been modified, meaning 
            the storage no longer reflects all of object's state.
            
            NOTE: normally this method will set the state to unsaved and 
            notify manager of modification.
        """
    
    def enable_persistence():
        """
            Turn on persistence mechanism.
        """
    
    def disable_persistence():
        """
            Turn off persistence mechanism.
        """
    
    def set_saved():
        """
            Set object's persistence status to saved, indicating 
            no modifications have been made since last written to 
            storage.
        """
    
    def set_unsaved():
        """
            Set object's persistence status to unsaved, indicating 
            a change has been made to the object that is not reflected 
            in storage; change is not yet persistent.
        """
    
    def set_loaded():
        """
            Set object's persistent status to loaded, indicating the 
            object's state has not been loaded from storage yet.
        """
    
    def set_unloaded():
        """
            Set object's persistent status to restored, indicating 
            the object's state has been loaded from storage.
        """
    
    def is_persistent():
        """
            Return boolean indication of whether or not instance 
            is actively persisting.
        """
    
    def is_saved():
        """
        """
    
    def is_loaded():
        """
        """

    def get_object():
        """
            Return reference to persistent object.  This method returns 
            self if the object provides this interface directly, otherwise
            it may be reference to adapted object.
        """

class IPersistenceManager(Interface):
    """
        Manages persistence mechanism.  Coordinates set 
        of pluggable components to build full-fledged 
        persistence mechanism.
    """
    storage = Attribute("""
        Reference to manager's IStorage provider.""")
    policy = Attribute("""
        Referene to manager's default IStoragePolicy provider.""")
    policies = Attribute("""
        Reference to list of policies in use by manager.""")
    cache = Attribute("""
        Reference to manager's object cache.""")
    writer_factory = Attribute("""
        Reference to manager's object writer factory""")
    reader_factory = Attribute("""
        Reference to manager's object reader factory.""")
    
    def get_storage():
        """
            Return current IStorage instance.
        """
    
    def get_policy():
        """
            Return default IPolicy instance.
        """
    
    def get_policies():
        """
            Return list of policies.
        """
    
    def get_cache():
        """
            Return current object cache.
        """
    
    def get_reader_factory():
        """
            Return current object reader factory.
        """
    
    def get_writer_factory():
        """
            Return current object writer factory.
        """
    
    def set_storage(storage):
        """
            Set current IStorage instance.
        """
    
    def add_policy(policy):
        """
            Set current IPolicy instance.
        """
    
    def remove_policy(policy):
        """
            Remove policy 'policy' if it exists.
        """
    
    def set_reader_factory(factory):
        """
            Set current factory for IObjectReader providing instances.
        """
    
    def set_writer_factory(factory):
        """
            Set current factory for IObjectWriter providing instances.
        """
    
    def new_oid():
        """
            Return unused OID value.  Generally delegates this 
            to storage instance's generate_oid method.
        """
    
    def get_object(oid):
        """
            Return object identified by OID 'oid'.
            
            Note: this method is meant to be called by clients 
            of the manager object; load is called internally.  The 
            object returned by this call may be a deferred type object 
            if the object does not yet exist in cache.
        """
    
    def get_oid(instance):
        """
            Return OID of object 'instance.'  Raise TypeError 
            if instance does not provide IPeristent.
            
            If no default value is provided, raise TypeError if 
            instance has no OID, otherwise, return default.  Note, 
            None may be provided as default.
        """
    
    def load(oid):
        """
            Return object with OID 'oid'.
        """
    
    def store(instance):
        """
            Add instance 'instance' to storage for persistent 
            storage from this point forward.
        """
    
    def note_modified(instance):
        """
            Notify policy of modified instance.
        """
    
    def make_persistent(instance):
        """
            Mark object 'instance' as persistent and track as modified.
        """
    
    def make_persistent_type(klass):
        """
            Mark class as persistent, thereby making all instances of 
            that class, and sub-classes, persistent.
        """
    
    def make_transient(instance):
        """
            Mark object 'instance' as transient and stop tracking.
        """
    
    def commit_changes():
        """
            Delegate to policy to commit modifications track since 
            last commit.
        """
    
    def commit_storage():
        """
            Cause storage to commit all pending changes to physical storage.
        """
    
    def commit():
        """
            Commit changes and store them.
        """
    
    def terminate():
        """
            Terminate entire persistence mechanism.  This may be useful if, 
            for example, a persistence mechanism were associated with startup 
            or a certain stage of operation only.
        """

class IStoragePolicy(Interface):
    """
        Object tracks changes to persistent objects.
        Manages timing and content of commitments to storage.
    """
    def note_modified(instance):
        """
            Notify policy of changes to instance 'instance'.
            Flag 'modified' used to indicate with modiifed or not.
            
            NOTE: method _add_instance(instance) will be used to 
            add instance to list of changes.
            
            NOTE: method _delete_instance(instance) will be used 
            to remove instance from list of changes.
        """
    
    def set_manager(manager):
        """
            Set IManager instance this policy is working with.
        """
    
    def get_manager():
        """
            Return IManager policy is working with.
        """
    
    def commit():
        """
            Tell manager which instances are to be written to storage.
            This is done by calling 'store' on manager for each instance.
        """
    
    def terminate():
        """
            Called by manager at manager termination.  See manager method.
        """

class IStorage(Interface):
    """
        Object representing persistent storage.
    """
    def set_manager(manager):
        """
            Assign IPersistenceManager controlling this storage.
        """
    
    def load_record(oid):
        """
            Return record associated with OID 'oid'.
        """
    
    def load_records(oids):
        """
        """
    
    def store_record(oid, record):
        """
            Stored record 'record' associated with key 'oid'.
        """
    
    def store_records(recordmap):
        """
            Store all objects found in map.  Key of map should 
            be OID, value is record data.
        """
    
    def generate_oid():
        """
            Return new, unused OID.
        """
    
    def has_oid(oid):
        """
            Return True if OID 'oid' exists in physical storage.
        """
    
    def commit():
        """
            Commit changes to underlying physical storage.
        """
    
    def terminate():
        """
            Called by manager at manager termination.  See manager method.
            Termination causes closure inherently.
        """
    
    def close():
        """
            Close connection/handles to physical resources.
        """

class ITransformationWriter(Interface):
    """
        Transforms objects into different formats for storing.
    """
    def set_manager(manager):
        """
            Assign manager for OID lookups.
        """
    
    def write_object(instance):
        """
            Return transformed representation of instance.
        """
    
    def __iter__():
        """
            Get iterator to iterate through object 
            graph performing transformations.
        """

class ITransformationReader(Interface):
    """
        Re-creates instance from transformation.
    """
    def set_manager(manager):
        """
           Assign manager for object by OID lookups.
        """
    
    def read_object(transformation):
        """
            Return object represented by tranformation.
        """

class ITransformable(ITransformationWriter, ITransformationReader):
    """
        Marker-class for transformable type tranformations.  Transformables 
        establish that an instance can be transformed.  Transformables 
        are always bidirectional, where "write" returns an object that may 
        be transformed into something, and "read" returns the object that 
        is would be transformed into something.
        
        Assuming ITransformable is done via an adapter, the write function 
        likely return 'self', being the adapter that may be transformed; 
        and the read function may return the adapter's context.
    """

class IPickleable(ITransformable):
    """
        Pickle-able marker-interface.
    """



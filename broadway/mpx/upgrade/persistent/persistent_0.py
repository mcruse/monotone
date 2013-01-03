"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import gc
import md5
import os
import string
import types
import weakref

from mpx import properties

from mpx.lib import threading
from mpx.lib.node import as_node_url
from mpx.lib.exceptions import ENameInUse
from mpx.lib.security import RExec

def _package_dict(dict):
    for key in dict.keys():
        dict[key] = repr(dict[key])
    return dict

def _unpackage_dict(dict):
    r = RExec()
    for key in dict.keys():
        dict[key] = r.r_eval(dict[key])
    return dict

##
# Built-In locks do not support weak references.
class Lock(object):
    def __init__(self,*args,**kw):
        self.__lock = threading.Lock()
        return
    def acquire(self,*args,**kw):
        return self.__lock.acquire(*args,**kw)
    def acquire_lock(self,*args,**kw):
        return self.__lock.acquire_lock(*args,**kw)
    def locked(self,*args,**kw):
        return self.__lock.locked(*args,**kw)
    def locked_lock(self,*args,**kw):
        return self.__lock.locked_lock(*args,**kw)
    def release(self,*args,**kw):
        return self.__lock.release(*args,**kw)
    def release_lock(self,*args,**kw):
        return self.__lock.release_lock(*args,**kw)

class LockMap(weakref.WeakValueDictionary):
    pass

_locks = LockMap()
_locks_lock = Lock()

##
# Class for facilitating storage of persistent data.
#
class _PersistentStorage_0:
    ##
    # @param name  Then name that will be used to
    #              uniquely identify storage.
    # @throws ENameInUse
    #
    def __init__(self, name, hash_it=1):
        self._md5 = name
        if hash_it:
            self._md5 = md5.new(name).hexdigest()
        self.path = properties.PDO_DIRECTORY
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        self.filename = os.path.join(self.path, self._md5 + '.dat')
        _locks_lock.acquire()
        try:
            # There should only be one lock object for pdo's using this name:
            if _locks.has_key(self._md5):
                # The use of the WeakValueDict to track name use in PDOs can be
                # susceptable to circular references.  Force a gc.collect() IFF
                # there is a name in use collision, which will break any
                # circular references.  THIS IS A BIG HAMMER, BUT IN THE REAL
                # WORLD IT SHOULD BE SUPER RARE.
                gc.collect()
                if _locks.has_key(self._md5):
                    # OK, the LockMap still has an entry, the name REALLY is in
                    # use.
                    raise ENameInUse(name)
            self._lock = Lock()
            _locks[self._md5] = self._lock
        finally:
            _locks_lock.release()
        self._delete = []
    
    def destroy(self):
        self._lock.acquire()
        try:
            if os.path.exists(self.filename):
                os.remove(self.filename)
        finally:
            self._lock.release()
    ##
    # @param name  The name of the value to store.
    # @param value  The values to store.
    #
    def store_value(self, name, value):
        self.store_values({name:value})
    ##
    # @param name  The name of the value to get.
    # @return The stored value for <code>name</code>.
    # @throws ENoSuchName
    #
    def get_value(self, name):
        return self.get_values([name])[name]
    ##
    # @param name  The name of the value to check.
    # @return Boolean indicating if <code>name</code>
    #         has a value stored for it.
    #
    def has_stored_value(self, name):
        raise ENotImplemented()
    ##
    # @param names  List of names whose values should
    #               be retrieved.
    # @return Dictionary of name:value pairs for each
    #         name in <code>names</code>.
    #
    def get_values(self, names):
        dict = self._read()
        dict = _unpackage_dict(dict)
        response = {}
        for key in dict.keys():
            if key in names:
                response[key] = dict[key]
        return response
    ##
    # @param dict  Dictionary of name:value pairs
    #              to store.
    #
    def store_values(self, dict):
        current_dict = self._read()
        for item in self._delete:
            if current_dict.has_key(item):
                del(current_dict[item])
        self._delete = []
        dict = _package_dict(dict)
        current_dict.update(dict)
        self._write(current_dict)
    ##
    # Mark an value for deleting the next time that a
    #  store_values is called.
    #
    # @param name  The name of the value to mark for
    #              removal.
    #
    def remove_value(self, name):
        self._delete.append(name)
    ##
    # @param dict  Dictionary of name:value pairs
    #              to store.
    #
    def _write(self, dict):
        self._lock.acquire()
        file = None
        try:
            file = open(self.filename, 'w')
            file.write(repr(dict))
        finally:
            if file: file.close()
            self._lock.release()
    ##
    # @return Dictionary that was written to file.
    #
    def _read(self):
        if not os.path.exists(self.filename):
            return {}
        self._lock.acquire()
        file = None
        try:
            file = open(self.filename, 'r')
            dict = RExec().r_eval(file.read())
        finally:
            if file: file.close()
            self._lock.release()
        return dict

_PersistentStorage = _PersistentStorage_0

##
# Base class for all persistent Data objects.  Subclasses
#  need only implement an __init__, creating instance variables
#  for values to be stored and assigning default values to them.
#  It is then important to call the base classes __init__ passing
#  the url for or a reference to the node that the data is for.
#
class PersistentDataObject:
    ##
    # @param node  The node (or url) that the persistent data
    #              is stored for.
    # @param auto_load  Flag to automatically load stored
    #                   values for node at start up.
    #
    def __init__(self, node, auto_load = 0, **keywords):
        if type(node) == types.StringType:
            name = node
        else:
            name = as_node_url(node)
        hash_it = 1
        if keywords.has_key('hash_it'):
            hash_it = keywords['hash_it']
        self._persistent = _PersistentStorage(name, hash_it)
        self._loaded = []
        self._delete = []
        if auto_load:
            self.load()
    
    def destroy(self):
        self._persistent.destroy()
        del(self._persistent)
    
    ##
    # Load all stored variables for the node into the
    # PersistentData object.
    #
    # @param name Optional param specifying which var to
    #             be loaded.
    # @default None  Will load all stored params.
    #
    def load(self, name = None):
        if name:
            names = [names]
        else:
            names = self._subclass_instance_names()
        # add whatever has been deleted but not saved.
        names.extend(self._delete)
        self._delete = []
        value_dict = self._persistent.get_values(names)
        self._loaded = value_dict.keys()
        self.__dict__.update(value_dict)
    ##
    # Save values for all members of <code>self<code> that are
    # not member hidden with '_' at front.
    #
    # @param name Optional param specifying which variable to save.
    # @default None  Save all public variables.
    #
    def save(self, name = None):
        if name:
            names = [name]
        else:
            names = self._subclass_instance_names()
        self._delete = []
        value_dict = {}
        for name in names:
            value_dict[name] = self.__dict__[name]
        self._persistent.store_values(value_dict)
        self._saved = names
    ##
    # Remove an item from ourselves and from the stored
    #  data.
    #
    def __delattr__(self, name):
        del(self.__dict__[name])
        self._delete.append(name)
        self._persistent.remove_value(name)
    ##
    # Get list of variable names that had data loaded
    # with last call to <code>load()</code>.
    #
    # @return List of names who were loaded.
    #
    def loaded(self):
        return self._loaded
    ##
    # Get list of all variable names that were saved
    # with last call to <code>save()</code>.
    #
    # @return List of name who were saved.
    #
    def saved(self):
        return self._saved
    ##
    # Get list of data members that are not hidden by
    # '_' char at beginning of name.
    #
    # @return List of names of vars that were
    #         not hidden.
    #
    def _subclass_instance_names(self):
        names = []
        for key in self.__dict__.keys():
            if not key.startswith('_'):
                names.append(key)
        return names


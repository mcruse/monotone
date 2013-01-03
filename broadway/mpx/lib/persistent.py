"""
Copyright (C) 2001 2002 2003 2004 2006 2010 2011 Cisco Systems

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
import md5
import gc
import os
import re
import string
import types
import weakref

from mpx.lib import threading
from mpx import properties
from mpx.lib.exceptions import ENameInUse
from mpx.lib.security import RExec
from mpx.lib.node import as_node_url
from mpx.lib.node import is_node_url

import msglog

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

def _package_dict(dict):
    for key in dict.keys():
        dict[key] = repr(dict[key])
    return dict

def _unpackage_dict(dict, context):
    r = RExec()
    r.update_global_names(context)
    for key in dict.keys():
        dict[key] = r.r_eval(dict[key])
    return dict

def _prior_version_exists(name, path, hash_it=1):
    if hash_it:
        if os.path.exists(os.path.join(path,md5.new(name).hexdigest() +
                                       '.dat')):
            return 1
    if os.path.exists(os.path.join(path,name + '.dat')):
        return 1
    return 0


##
# Class for facilitating storage of persistent data.
#
class _PersistentStorage_1:
    ##
    # @param name  Then name that will be used to
    #              uniquely identify storage.
    # @param path  String which specifies the directory in which
    #              the data will be stored.
    # @default PDO_DIRECTORY from mpx.lib.properties
    # @throws ENameInUse
    #
    def __init__(self, name, locker=None, hash_it=1, context=None,
                 path=None):
        if context is None:
            context={}
        if path is None:
            self.path = properties.PDO_DIRECTORY
        else:
            self.path = path
        self._name = name
        self._context=context
        if hash_it:
            self._name = md5.new(self._name).hexdigest()
        self._name = self._name + '.dat.1'
        if not os.path.isdir(self.path):
            os.makedirs(self.path)
        self.filename = os.path.join(self.path, self._name)
        _locks_lock.acquire()
        try:
            # There should only be one lock object for pdo's using this name:
            if not locker and _locks.has_key(self._name):
                # The use of the WeakValueDict to track name use in PDOs can be
                # susceptable to circular references.  Force a gc.collect() IFF
                # there is a name in use collision, which will break any
                # circular references.  THIS IS A BIG HAMMER, BUT IN THE REAL
                # WORLD IT SHOULD BE SUPER RARE.
                gc.collect()
                if _locks.has_key(self._name):
                    # OK, the LockMap still has an entry, the name REALLY is in
                    # use.
                    raise ENameInUse(name)
            if locker:
                self._lock = locker
            else:
                new_lock = Lock()
                self._lock = new_lock
            _locks[self._name] = self._lock
            # if our version does not exist, but a previous
            # version of this persistent data does, do an
            # upgrade by instaciating previous version.
            if not os.path.exists(self.filename) and \
               _prior_version_exists(name, self.path, hash_it):
                from mpx.upgrade.persistent.persistent_0 import \
                     _PersistentStorage_0
                old = _PersistentStorage_0(name, hash_it)
                old_name = old.filename
                os.rename(old_name, self.filename)
                old.destroy()
                del(old)
        finally:
            _locks_lock.release()
        self._delete = []
        return
    def destroy(self):
        self._lock.acquire()
        try:
            if os.path.exists(self.filename):
                os.remove(self.filename)
        finally:
            self._lock.release()
        _locks_lock.acquire()
        try:
            if _locks.has_key(self._name):
                del(_locks[self._name])
        finally:
            _locks_lock.release()
        return
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
        dict = _unpackage_dict(dict, self._context)
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
            r = RExec()
            r.update_global_names(self._context)
            dict = r.r_eval(file.read())
        finally:
            if file: file.close()
            self._lock.release()
        return dict

_PersistentStorage = _PersistentStorage_1

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
    # @param **keywords
    # @value hash_it  Boolean indicating whether or not the
    #                 name passed in should be hashed for the
    #                 file.
    # @default 1 Hash the name.
    # @value path     String which specifies the directory in which
    #                 the data will be stored.
    # @default None Allow PersistentStorage to use it's default.
    def __init__(self, node, auto_load = 0, lock=None, dmtype=None,
                 **keywords):
        if type(node) == types.StringType:
            name = node
        else:
            name = as_node_url(node)
        hash_it = 1
        self.__meta__ = {'name':name}
        if keywords.has_key('hash_it'):
            hash_it = keywords['hash_it']
        if not hash_it:
            self.__meta__ = {'name':None,'file':name}
        self.__path = keywords.get('path')
        self.__name = name
        self.__lock = lock
        self.__hash_it = hash_it
        self._persistent = _PersistentStorage(name,lock,hash_it,
                                              context=self.global_context(),
                                              path=self.__path)
        # If we are persisting data for a node, then register the relevant
        # information with the Garbage Collector.
        self.__deferred_register = None
        self.__register(name, self._persistent.filename, dmtype)
        self._loaded = []
        self._delete = []
        if auto_load:
            self.load()
        return
    def __register(self, name=None, file=None, dmtype=None):
        if name is None:
            assert file is None and dmtype is None, (
                "If name is None, file, and dmtype must be as well."
                )
            if not self.__deferred_register:
                # Already registerred.
                return
            name = self.__deferred_register['name']
            file = self.__deferred_register['file']
            dmtype = self.__deferred_register['dmtype']
            self.__deferred_register = None
        else:
            assert file is not None, (
                "If name is not None, file must not be as well."
                )
            assert self.__deferred_register is None, (
                "If name is not None, self.__deferred_register must be None."
                )
        if is_node_url(name):
            try:
                from mpx.service.garbage_collector import GARBAGE_COLLECTOR
                GARBAGE_COLLECTOR.register(name, file, dmtype)
            except:
                self.__deferred_register = {"name":name, "file":file,
                                            "dmtype":dmtype}
        return
    ##
    # @return A dictionary of name value pairs that will be added to the
    #         persistent data objects restricted evaluation context.
    def global_context(self):
        return {}
    def destroy(self):
        self._persistent.destroy()
        del(self.__dict__['_persistent'])
        self._persistent = _PersistentStorage(self.__name,self.__lock,
                                              self.__hash_it,
                                              context=self.global_context(),
                                              path=self.__path)
    def __reset(self):
        PersistentDataObject.destroy(self)
    def add_meta(self, name, value):
        self.__meta__[name] = value
        return
    def get_meta(self):
        return self.__meta__
    ##
    # Load all stored variables for the node into the
    # PersistentData object.
    #
    # @param name Optional param specifying which var to
    #             be loaded.
    # @default None  Will load all stored params.
    #
    def load(self, name=None):
        if name:
            names = [name]
        else:
            names = self._subclass_instance_names()
        # add whatever has been deleted but not saved.
        names.extend(self._delete)
        names.append('__meta__')
        self._delete = []
        try:
            value_dict = self._persistent.get_values(names)
        except:
            file = open(self._persistent.filename,'r')
            data = file.read()
            file.close()
            if string.find(self.__name,'msglog') == -1:
                try:
                    from mpx.lib import msglog
                    msglog.log('broadway',msglog.types.WARN,
                               'Deleting corrupted persistent data: %s' % data)
                    msglog.exception()
                except:
                    print 'Warning, unable to log PDO load failure: %s' % data
            else:
                print 'Failure while loading msglog PDO: %s' % data
            self.__reset()
        else:
            self._loaded = value_dict.keys()
            self.__dict__.update(value_dict)
        
    ##
    # Save values for all members of <code>self<code> that are
    # not member hidden with '_' at front.
    #
    # @param name Optional param specifying which variable to save.
    # @default None  Save all public variables.
    #
    def save(self, name=None):
        self.__register() # Handles possible deferred registration.
        if name:
            names = [name]
        else:
            names = self._subclass_instance_names()
        names.append('__meta__')
        self._delete = []
        value_dict = {}
        for name in names:
            value_dict[name] = self.__dict__[name]
        self._persistent.store_values(value_dict)
        self._saved = names
    ##
    # Return a dictionary representation of the persistant data.
    def as_dict(self):
        names = self._subclass_instance_names()
        names.append('__meta__')
        dict = {}
        for name in names:
            dict[name] = self.__dict__[name]
        return dict
    ##
    # Remove an item from ourselves and from the stored
    #  data.
    #
    def __delattr__(self, name):
        names = self._subclass_instance_names()
        del(self.__dict__[name])
        if name in names:
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

# @note  Need to make func thread safe because of mods
#        to the pdofile property.
# @todo  May be overkill to allow a logs 
#        directory to be passed in.
    def filename(self):
        return self._persistent.filename

def all_pdos_info(dir=None):
    _info_lock.acquire()
    try:
        if dir == None:
            dir = properties.PDO_DIRECTORY
            reset = 0
        else:
            original_path = properties.PDO_DIRECTORY
            reset = 1
            properties.set('PDO_DIRECTORY', dir)
        pdos = []
        delete = []
        for filename in os.listdir(dir):
            match = _regex.match(filename)
            if match:
                name = match.group(2)
                key = match.group(1)
                lock = None
                if _locks.has_key(key):
                    lock = _locks[key]
                pdo = PersistentDataObject(name,0,lock,hash_it=0)
                if not lock:
                    delete.append(pdo)
                pdo.load()
                pdos.append(pdo.get_meta())
    finally:
        if reset:
            properties.set('PDO_DIRECTORY', original_path)
        for pdo in delete:
            del(pdo)
        _info_lock.release()
    return pdos

##
# Initialize all of the modules constants/singletons.
def _init():
    global _locks
    global _locks_lock
    global _info_lock
    global _regex
    _locks = LockMap()
    _locks_lock = Lock()
    _info_lock = Lock()
    _regex = re.compile('((.*)\.dat(\..*|$))')

##
# Hooks for preogramatic tests.
def _reinit():
    _init()

#
# Invoke the "one-time" module inititalization.
#
_init()


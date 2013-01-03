"""
Copyright (C) 2008 2009 2010 2011 Cisco Systems

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
from threading import RLock
from storage import FileStorage
from storage import MapStorage
from mpx import properties
from mpx.lib import msglog
PDODIR = properties.PDO_DIRECTORY
UNDEFINED = object()

class Persistent(object):
    def __init__(self, name, **kw):
        super(Persistent, self).__init__()
        self.name = name
        self.storage = None
        self.synclock = RLock()
        self.path = kw.get('path', PDODIR)
        self.encode = kw.get('encode', repr)
        self.decode = kw.get('decode', eval)
        self.extension = kw.get('extension', 'dat')
        self.autopersist = kw.get('autopersist', True)
        if self.autopersist:
            self.load()
    def open(self):
        self.synclock.acquire()
        try:
            self.storage = FileStorage(self.path, self.name, self.extension)
            self.storage.open()
        finally:
            self.synclock.release()
    def close(self):
        self.synclock.acquire()
        try:
            self.storage.close()
            self.storage = None
        finally:
            self.synclock.release()
    def closed(self):
        storage = self.storage
        if storage is None:
            return True
        elif storage.closed():
            return True
        return False
    def update_storage(self):
        """
            Serialize and data associated with object and 
            update storage record to match serialization.
        """
        self.synclock.acquire()
        try:
            data = self.getencoded()
            self.storage.set(data)
        finally:
            self.synclock.release()
    def update_data(self):
        self.synclock.acquire()
        try:
            data = self.storage.getdata()
            self.setencoded(data)
        finally:
            self.synclock.release()
    def commit(self):
        """
            Update storage with most recent data, then 
            commit changes.
        """
        self.synclock.acquire()
        try:
            self.update_storage()
            self.storage.commit()
            self.notify_committed()
        finally:
            self.synclock.release()
    def load(self):
        """
            Load most recently stored data, then update 
            current data with loaded content.
        """
        self.synclock.acquire()
        try:
            if self.storage is None:
                self.open()
            self.storage.load()
            self.update_data()
            self.notify_loaded()
        finally:
            self.synclock.release()
    def serialize(self, data):
        if self.encode is not None:
            data = self.encode(data)
        return data
    def unserialize(self, data):
        if self.decode is not None:
            data = self.decode(data)
        return data
    def getencoded(self):
        """
            Return encoded representation of current data object.
            
            This method must be overridden in type-specific 
            subclasses.
        """
        raise TypeError("Method must be overridden")
    def setencoded(self, data):
        """
            Use encoded representation of persisted data object 
            to update current data object.
            
            This method must be overridden in type-specific 
            subclasses.
        """
        raise TypeError("Method must be overridden")
    def notify_committed(self):
        pass
    def notify_loaded(self):
        pass

class PersistentDictionary(Persistent, dict):
    def __init__(self, name, initdata=(), **kw):
        self.removed = set()
        self.modified = set()
        kw.setdefault('extension', 'dict')
        self.keyencode = kw.get('keyencode', None)
        self.keydecode = kw.get('keydecode', None)
        Persistent.__init__(self, name, **kw)
        dict.__init__(self, initdata)
    def open(self):
        self.synclock.acquire()
        try:
            self.storage = MapStorage(self.path, self.name, 
                                      self.extension, 
                                      encode=None, decode=None)
            self.storage.open()
        finally:
            self.synclock.release()
    def getmodified(self):
        self.synclock.acquire()
        try:
            modkeys = self.modified.copy()
        finally:
            self.synclock.release()
        return modkeys
    def getremoved(self):
        self.synclock.acquire()
        try:
            rmkeys = self.removed.copy()
        finally:
            self.synclock.release()
        return rmkeys
    def update_storage(self):
        """
            Serialize and data associated with object and 
            update storage record to match serialization.
            
            Overridden here to insert efficiency code which 
            only changes those items which have been modified 
            or removed, instead of hammer-method used by super.
        """
        self.synclock.acquire()
        try:
            for key in self.getremoved():
                self.storage.remove(self.encodedkey(key))
                self.removed.remove(key)
            for key in self.getmodified():
                self.storage[self.encodedkey(key)] = self.encodedvalue(key)
                self.modified.remove(key)
        finally:
            self.synclock.release()
    def encodedkey(self, key):
        return self.serializekey(key)
    def encodedvalue(self, key):
        self.synclock.acquire()
        try:
            value = self[key]
        finally:
            self.synclock.release()
        return self.serialize(value)
    def encodeditem(self, key):
        return (self.encodedkey(key), self.encodedvalue(key))
    def getencoded(self):
        self.synclock.acquire()
        try:
            items = [self.encodeditem(key) for key in self.keys()]
        finally:
            self.synclock.release()
        return dict(items)
    def setencoded(self, data):
        decodeditems = []
        self.synclock.acquire()
        try:
            for key,value in data.items():
                try:
                    decodedkey = self.unserializekey(key)
                    decodedvalue = self.unserialize(value)
                except:
                    msglog.log("broadway", msglog.types.WARN, 
                               "Failed to decoded: (%s, %s)" % (key, value))
                    msglog.exception()
                else:
                    decodeditems.append((decodedkey, decodedvalue))
            dict.update(self, decodeditems)
        finally:
            self.synclock.release()
    def notify_changed(self, keys):
        if not isinstance(keys, (set, list, tuple)):
            keys = [keys]
        self.synclock.acquire()
        try:
            map(self.modified.add, keys)
            map(self.removed.discard, keys)
            if self.autopersist:
                self.commit()
        finally:
            self.synclock.release()
    def notify_removed(self, keys):
        if not isinstance(keys, (set, list, tuple)):
            keys = [keys]
        self.synclock.acquire()
        try:
            map(self.removed.add, keys)
            map(self.modified.discard, keys)
            if self.autopersist:
                self.commit()
        finally:
            self.synclock.release()
    def clear(self):
        self.synclock.acquire()
        try:
            keys = set(self)
            dict.clear(self)
            self.notify_removed(keys)
        finally:
            self.synclock.release()
    def popitem(self):
        self.synclock.acquire()
        try:
            (key,value) = dict.popitem(self)
            self.notify_removed(key)
        finally:
            self.synclock.release()
        return (key,value)
    def update(self, value):
        # By doing the dict(items) we ensure the value is a 
        # dictionary type, even if a list of tuples was passed in. 
        valuedict = dict(value)
        self.synclock.acquire()
        try:
            dict.update(self, valuedict)
            self.notify_changed(valuedict.keys())
        finally:
            self.synclock.release()
    def pop(self, key):
        self.synclock.acquire()
        try:
            value = dict.pop(self, key)
            self.notify_removed(key)
        finally:
            self.synclock.release()
        return value
    def setdefault(self, name, value):
        self.synclock.acquire()
        try:
            if not self.has_key(name):
                self[key] = value
                self.notify_changed(key)
        finally:
            self.synclock.release()
        return self[key]
    def serializekey(self, key):
        if self.keyencode is not None:
            key = self.keyencode(key)
        return key
    def unserializekey(self, key):
        if self.keydecode is not None:
            key = self.keydecode(key)
        return key
    def __delitem__(self, key):
        self.pop(key)
    def __setitem__(self, key, value):
        self.synclock.acquire()
        try:
            dict.__setitem__(self, key, value)
            self.notify_changed(key)
        finally:
            self.synclock.release()

class PDO(object):
    def __init__(self, name, *args, **kw):
        self._datastore = PersistentDictionary(name, *args, **kw)
        super(PDO, self).__init__()
    def __getattr__(self, name, default=UNDEFINED):
        value = self._datastore.get(name, default)
        if value is UNDEFINED:
            message = "'%s' object has no attribute '%s'."
            raise AttributeError(message % (type(self).__name__, name))
        return value
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(PDO, self).__setattr__(name, value)
        else:
            self._datastore[name] = value
    def __delattr__(self, name):
        if name.startswith('_'):
            super(PDO, self).__delattr__(name)
        else:
            try:
                del(self._datastore[name])
            except KeyError:
                message = "'%s' object has no attribute '%s'."
                raise AttributeError(message % (type(self).__name__, name))
    def close(self):
        return self._datastore.close()
    def closed(self):
        return self._datastore.closed()


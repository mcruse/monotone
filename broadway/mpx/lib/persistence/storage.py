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
import os
import md5
import anydbm
from whichdb import whichdb
from threading import Lock
from threading import RLock
from threading import Event
from mpx import properties
from mpx.lib import msglog
DEBUG = False

class Storage(object):
    filesysmap = {}
    filesyslock = Lock()
    def __new__(klass, path, name, *args, **kw):
        klass.filesyslock.acquire()
        try:
            pathmap = klass.filesysmap.setdefault(path, {})
            if name in pathmap:
                existing = pathmap[name]
                if not existing.closed():
                    errormsg = 'FileStorage "%s" already in path "%s"'
                    raise TypeError(errormsg % (name, path))
                else:
                    pathmap.pop(name)
            superclass = super(Storage, klass)
            pathmap[name] = superclass.__new__(klass, path, name, *args, **kw)
        finally:
            klass.filesyslock.release()
        return pathmap[name]
    def __init__(self, path, name, encode=repr, decode=eval):
        self.name = name
        self.path = path
        self.encode = encode
        self.decode = decode
        self._opened = Event()
        self._closed = Event()
        self.storagelock = RLock()
        super(Storage, self).__init__()
    def open(self):
        raise TypeError("Method must be overridden in subclass")
    def close(self):
        raise TypeError("Method must be overridden in subclass")
    def load(self):
        raise TypeError("Method must be overridden in subclass")
    def commit(self):
        raise TypeError("Method must be overridden in subclass")
    def destroy(self):
        raise TypeError("Method must be overridden in subclass")
    def getdata(self):
        raise TypeError("Method must be overridden in subclass")
    def setdata(self, encoded):
        raise TypeError("Method must be overridden in subclass")
    def opened(self):
        self.storagelock.acquire()
        try:
            opened = self._opened.isSet()
        finally:
            self.storagelock.release()
        return opened
    def closed(self):
        self.storagelock.acquire()
        try:
            closed = self._closed.isSet()
        finally:
            self.storagelock.release()
        return closed
    def serialize(self, data):
        if self.encode is not None:
            data = self.encode(data)
        return data
    def unserialize(self, data):
        if self.decode is not None:
            data = self.decode(data)
        return data

class FileStorage(Storage):
    """
        Create a file-storage object which wraps a file on 
        disk and manages updating and loading data to and 
        from that file.
        
        Uses the following keyword arguments:
            encode - defaults to repr
            decode - defaults to eval
            path - defaults to PDO DIR from properties
            hashname - defaults to False
            suffix - default to 'dat'
    """
    def __init__(self, path, name, extension, encode=repr, decode=eval):
        super(FileStorage, self).__init__(path, name, encode, decode)
        self.extension = extension
        self.filehandle = None
        # Decoded data is data set by client, 
        # or result of decoding data read from storage.
        self.decoded_data = None
        # Encoded data is data read from storage, or 
        # result of encoding data set by client. 
        self.encoded_data = None
        self.filename = '%s.%s' % (self.name, self.extension)
        self.filepath = os.path.join(self.path, self.filename)
    def open(self):
        self.storagelock.acquire()
        try:
            if self.opened():
                raise TypeError("Storage already opened")
            if os.path.exists(self.filepath):
                self.filemode = 'r+'
            else:
                self.filemode = 'w'
                if not os.path.isdir(self.path):
                    os.makedirs(self.path)
            self.filehandle = open(self.filepath, self.filemode)
        except:
            raise
        else:
            self._opened.set()
            self._closed.clear()
        finally:
            self.storagelock.release()
    def close(self):
        self.storagelock.acquire()
        try:
            if not self.opened():
                raise TypeError("Storage has not been opened")
            elif self.closed():
                raise TypeError("Storage already closed")
            else:
                self.filehandle.close()
        except:
            raise
        else:
            self._closed.set()
            self._opened.clear()
        finally:
            self.storagelock.release()
    def load(self):
        self.encoded_data = self._read()
        self.decoded_data = self.unserialize(self.encoded_data)
    def commit(self):
        self.encoded_data = self.serialize(self.decoded_data)
        self._write(self.encoded_data)
    def setdata(self, data):
        self.decoded_data = data
        self.encoded_data = None
    def getdata(self):
        return self.decoded_data
    def _read(self):
        self.storagelock.acquire()
        try:
            if not self.opened():
                raise TypeError("Cannot read from unopened storage")
            elif self.closed():
                raise TypeError("Cannot read from closed storage")
            self.filehandle.seek(0)
            data = self.filehandle.read()
        finally:
            self.storagelock.release()
        return data
    def _write(self, data):
        self.storagelock.acquire()
        try:
            if not self.opened():
                raise TypeError("Cannot write to unopened storage")
            elif self.closed():
                raise TypeError("Cannot write to closed storage")
            self.filehandle.seek(0)
            bytecount = self.filehandle.write(data)
            self.filehandle.truncate()
        finally:
            self.storagelock.release()
        return bytecount
    def destroy(self):
        self.storagelock.acquire()
        try:
            self.close()
            if self.filepath and os.path.exists(self.filepath):
                os.remove(self.filepath)
        finally:
            self.storagelock.release()

class MapStorage(Storage):
    """
        Storage which exposes a dictionary like interface 
        for making changes to data being read/written.
    """
    # Flag turns on and off compaction.
    COMPACT = True
    # Invoke GDBM-based DB's reorganize when DB is opened?
    COMPACT_ON_OPEN = True
    # Update operations before GDBM-based DB's reorganize.
    COMPACT_AFTER_UPDATES = 1000 
    # Deletions before invoking GDBM-based DB's reorganize.
    COMPACT_AFTER_DELETES = 1000
    def __init__(self, path, name, extension, encode=repr, decode=eval):
        super(MapStorage, self).__init__(path, name, encode, decode)
        self.datacache = {}
        self.dbmtype = None
        self.database = None
        self.extension = extension
        self.unpacked_updates = 0
        self.unpacked_deletions = 0
        self.filename = '%s.%s' % (self.name, self.extension)
        self.filepath = os.path.join(self.path, self.filename)
    def logdebug(self, message, *args, **kw):
        if kw.get("level", 1) <= DEBUG:
            if args:
                message = message % args
            typename = type(self).__name__
            msglog.debug("%s(%r): %s." % (typename, self.filename, message))
    def whichdb(self):
        if not self.dbmtype:
            self.dbmtype = whichdb(self.filepath)
        return self.dbmtype
    def commit(self):
        if self.database: 
            if hasattr(self.database, "sync"):
                self.database.sync()
            if self.should_compact():
                self.logdebug("commit running compact.")
                self.compact()
        return
    def compact(self):
        self.storagelock.acquire()
        try:
            if hasattr(self.database, "reorganize"):
                # GDB DBM databases provide 'reorganize()' method 
                # to reclaim space freed by record deletions or 
                # supplanted by record updates.  
                self.logdebug("compact calling database reorganize().")
                self.database.reorganize()
            elif self.whichdb() == "dumbdbm":
                # Dumb DBM databases never reclaim space freed 
                # by record deletions or updates, and do not provide 
                # a mechanism for reclaiming this space like GDB DBM 
                # provides with 'reorganize'.
                # 
                # To reclaim freed space we must replace existing 
                # database with new database populated by current 
                # record content.  Although 'anydbm.open()' with 
                # mode 'n' is supposed to always create a new, 
                # empty database, it appears the newly created 
                # database picks up existing database file, and 
                # then clears it, rather than wiping out the existing 
                # file first.  The consequence of this is that 
                # creating a new database doesn't reduce the existing 
                # database's file size.   
                self.logdebug("compact handling dumbdbm database.")
                dirfile = self.database._dirfile
                datfile = self.database._datfile
                bakfile = self.database._bakfile
                tempfile = self.filepath + ".temp"
                tempdb = anydbm.open(tempfile, "n")
                # Populate temporary DB with DB items.
                for key in self.database.keys():
                    tempdb[key] = self.database[key]
                if hasattr(tempdb, "sync"):
                    tempdb.sync()
                self.database.close()
                # Account for possibility that grand fathered 
                # in 'dumbdbm' database exists in system where 
                # GDBM, or other DBM is now supported.  If it 
                # is a dumbdbm database, move temp DB's files 
                # to database name.  
                if whichdb(tempfile) == "dumbdbm":
                    self.logdebug("temporary database also dumbdbm.") 
                    files = [(tempdb._dirfile, dirfile), 
                             (tempdb._datfile, datfile), 
                             (tempdb._bakfile, bakfile)]
                    tempdb.close()
                    for srcpath,dstpath in files:
                        if os.path.exists(srcpath):
                            os.rename(srcpath, dstpath)
                        elif os.path.exists(dstpath):
                            os.remove(dstpath)
                    self.database = anydbm.open(self.filepath, "w")
                else:
                    self.logdebug("temp DB is type %r.", whichdb(tempfile))
                    # Apparently existing databases aren't overwritten, 
                    # even when reopened using 'n' to create new, empty.  
                    # Remove database files so newly created, empty 
                    # database starts with clean slate.   
                    if os.path.exists(dirfile):
                        os.remove(dirfile)
                    if os.path.exists(datfile):
                        os.remove(datfile)
                    if os.path.exists(bakfile):
                        os.remove(bakfile)
                    self.database = anydbm.open(self.filepath, "n")
                    # Populate newly created empty database with 
                    # items from temporary DB.  Note that newly 
                    # created database could potentially be non-GDBM 
                    # database since existing DB files were deleted 
                    # and new database was created from scratch.  
                    # This approach should be compatible with such 
                    # migration. 
                    for key in tempdb.keys():
                        self.database[key] = tempdb[key]
                    if hasattr(self.database, "sync"):
                        self.database.sync()
                    tempdb.close()
                    # Resent DBM type in case newly created database 
                    # is a different DBM type than previous database. 
                    self.dbmtype = None
            elif self.whichdb():
                # Set this *instance's* compaction 
                # to None, so it doesn't continue 
                # checking non-GDBM DB for reorganize.  
                # Note which=DB check ensures compaction 
                # isn't disabled because compact() was run 
                # before any content was saved to disk. 
                self.COMPACT = False
                self.logdebug("compact disabled: %r type DB.", self.whichdb())
            else:
                self.logdebug("compact ignored: DB type is NULL.")
            self.unpacked_updates = 0
            self.unpacked_deletions = 0
        finally:
            self.storagelock.release()
    def should_compact(self):
        # None or "" DBM type indicates DBM database files 
        # are empty, and therefore compaction is unnecessary.
        if self.COMPACT and self.whichdb():
            if self.unpacked_updates > self.COMPACT_AFTER_UPDATES:
                return True
            if self.unpacked_deletions > self.COMPACT_AFTER_DELETES:
                return True
        return False
    def load(self):
        self.logdebug("loading.")
        self.storagelock.acquire()
        try:
            self.datacache.clear()
            keys = self.database.keys()
            values = [self[key] for key in keys]
        finally:
            self.storagelock.release()
    def __getitem__(self, name):
        self.storagelock.acquire()
        try:
            if not self.datacache.has_key(name):
                encoded = self.database[name]
                self.datacache[name] = self.unserialize(encoded)
            value = self.datacache[name]
        finally:
            self.storagelock.release()
        return value
    def __setitem__(self, name, decoded):
        self.storagelock.acquire()
        try:
            self.database[name] = self.serialize(decoded)
        except:
            raise
        else:
            # Assume compacted on-open, and only increment 
            # unpacked updates value if value has already 
            # been set during this runtime, by only checking 
            # cache for its key, for performance reasons. 
            if self.datacache.has_key(name):
                self.unpacked_updates += 1
            self.datacache[name] = decoded            
        finally:
            self.storagelock.release()
    def __delitem__(self, name):
        return self.remove(name)
    def getitems(self):
        return [(key, self[key]) for key in self.database.keys()]
    def getdata(self):
        return dict(self.getitems())
    def setdata(self, decoded):
        decoded = dict(decoded)
        self.storagelock.acquire()
        try:
            modifying = set(decoded)
            existing = set(self.database.keys())
            map(self.remove, existing - modifying)
            self.update(decoded)
        finally:
            self.storagelock.release()
    def remove(self, name):
        self.storagelock.acquire()
        try:
            del(self.database[name])
        except:
            raise
        else:
            if name in self.datacache:
                self.datacache.pop(name)
            self.unpacked_deletions += 1
        finally:
            self.storagelock.release()
    def update(self, data):
        items = dict(data).items()
        self.storagelock.acquire()
        try:
            for name,value in items:
                self[name] = value
        finally:
            self.storagelock.release()
    def open(self):
        self.storagelock.acquire()
        try:
            if self.opened():
                raise TypeError("Storage already opened")
            if not os.path.isdir(self.path):
                # No need to compact newly created DB.
                os.makedirs(self.path)
            dbexisted = whichdb(self.filepath)
            self.database = anydbm.open(self.filepath, "c")
            self.dbmtype = None
            self._opened.set()
            self._closed.clear()
            # Only compact on open if whichdb() indicated dataabase 
            # existing DB was opened; if new DB was created, there's 
            # no need to compact. 
            if dbexisted and self.COMPACT and self.COMPACT_ON_OPEN:
                self.compact()
        finally:
            self.storagelock.release()
    def close(self):
        self.storagelock.acquire()
        try:
            if not self.opened():
                raise TypeError("Storage has not been opened")
            elif self.closed():
                raise TypeError("Storage already closed")
            else:
                self.database.close()
        except:
            raise
        else:
            self._closed.set()
            self._opened.clear()
        finally:
            self.storagelock.release()

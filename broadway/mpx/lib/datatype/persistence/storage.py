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
import cPickle
import anydbm
from mpx.lib.uuid import UUID
from mpx.componentry import implements
from mpx.lib.datatype.persistence.interfaces import IStorage

class Storage(object):
    implements(IStorage)
    def set_manager(self, manager):
        self.manager = manager
    def load_records(self, oids):
        return map(self.load_record, oids)
    def store_records(self, recordmap):
        for oid, record in recordmap.items():
            self.store_record(oid, record)
    def generate_oid(self):
        return str(UUID())
    def has_oid(self, oid):
        try: 
            self.load_record(oid)
        except: 
            return False
        else: 
            return True
    def load_record(self, oid):
        raise Exception('Not implemented')
    def store_record(self, oid, record):
        raise Exception('Not implemented')
    def close(self):
        raise Exception('Not implemented')
    def commit(self):
        pass

class MemoryStorage(Storage):
    def __init__(self):
        self.records = {}
    def load_record(self, oid):
        return self.records[oid]
    def store_record(self, oid, record):
        self.records[oid] = record
    def has_oid(self, oid):
        return self.records.has_key(oid)
    def close(self):
        self.records.clear()

class SimpleFileStorage(MemoryStorage):
    def __init__(self, filename):
        super(SimpleFileStorage, self).__init__()
        self.filename = filename
        try: 
            self._load(self.filename)
        except IOError, EOFError: 
            pass
    def commit(self):
        self._dump(self.filename)
    def _load(self, filename):
        file = open(filename, 'rb')
        self.records = cPickle.load(file)
        file.close()
    def _dump(self, filename):
        file = open(filename, 'wb')
        cPickle.dump(self.records, file)
        file.close()
    def close(self):
        self.commit()
        super(SimpleFileStorage, self).close()

class DBMStorage(Storage):
    def __init__(self, filename, *args, **kw):
        self.filename = filename
        self.dbm = anydbm.open(filename, 'c')
    def load_record(self, oid):
        return self.dbm[oid]
    def store_record(self, oid, record):
        self.dbm[oid] = record
    def has_oid(self, oid):
        return self.dbm.has_key(oid)
    def commit(self):
        self.dbm.sync()
    def close(self):
        self.dbm.close()

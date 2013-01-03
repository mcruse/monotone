"""
Copyright (C) 2008 2010 2011 Cisco Systems

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

from threading import RLock
from storage import FileStorage
from mpx import properties
PDODIR = properties.PDO_DIRECTORY

class IPersistent(Interface):
    def __init__(name, path=PDODIR, ext='dat', encode=repr, decode=str):
        """
        """
    def open():
        """
        """
    def close():
        """
        """
    def closed():
        """
        """
    def update_storage():
        """
            Update persistent data stored by storage from 
            data current in memory.  Method synchronizes data 
            on disk, with data in memory; it is how changes are 
            persisted.
        """
    def update_data():
        """
            Update data in memory from data read from storage.
            This method does not load data from disk in storage, 
            but does data synchronize data in memory with data 
            that has been loaded from memory.  The sychronization 
            is sub-type specific; it may mean data from storage 
            replaces that in memory, or that data is memory is 
            updated with data read from disk.
        """
    def commit():
        """
            Update storage with data from memory, the instruct 
            storage to commit the data so it is persisted.
        """
    def load():
        """
            Instruct storage to get most recent data from disk, 
            then update data in memory with data loaded.
        """
    def getencoded():
        """
            Return encoded representation of data in memory.
            Encoded representations are those representations 
            prepared to be written to storage.  By default, 
            the encoding used by persisted data types is a 
            simple repr/eval combination.
        """
    def setencoded(data):
        """
            Update data in memory from encoded representation.
            Data passed in an encoded representation of data 
            read from storage. 
        """
    def notify_committed():
        """
            Notify subclass that data has been committed to storage.
        """
    def notify_loaded():
        """
            Notify subclass that data has been loaded from storage.
        """
    def serialize(data):
        """
            Return encoded version of data.  If encoding is None, 
            return data unchanged.
        """
    def unserialize(data):
        """
            Return decoded version of data.  If decode is None, 
            return data unchanged.
        """

class IPersistentMap(IPersistent):
    def getadded():
        """
            Return keys for all entries that have been added 
            since the last commit.
        """
    def getremoved():
        """
            Return keys for all entries that have been removed 
            since the last commit.
        """
    def getmodified():
        """
            Return keys for all entries that have been modified 
            since the last commit.
        """
    def encodedkey(key):
        """
            Return coded version of key.  If key encoding is 
            disabled, return key as is.
        """
    def encodedvalue(key):
        """
            Return value corresponding to key in its encoded 
            format.
        """
    def encodeditem(key):
        """
            Return (key, value) pair where key matches key 
            passed in, and value is encoded.
        """
    def notify_changed(keys):
        """
        """
    def notify_removed(keys):
        """
        """
    def clear():
        """
        """
    def popitem():
        """
        """
    def update(value):
        """
        """
    def pop(key):
        """
        """
    def setdefault(name, value):
        """
        """
    def __delitem__(key):
        """
        """
    def __setitem__(key, value):
        """
        """

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
import cStringIO
from mpx.componentry import implements
from mpx.lib.datatype.persistence.interfaces import IPickleable
from mpx.lib.datatype.persistence.interfaces import IPersistent
from mpx.lib.datatype.persistence.interfaces import IPersistentObject
from mpx.lib.datatype.persistence.interfaces import ITransformationWriter
from mpx.lib.datatype.persistence.interfaces import ITransformationReader
from mpx.lib.datatype.persistence.utility import CollectionIterator

class PickleTransformationWriter(object):
    implements(ITransformationWriter)
    
    def __init__(self, instance = None):
        self.manager = None
        self._instances = []
        if instance is not None:
            self._instances.append(instance)
        self._sio = cStringIO.StringIO()
        self._pickler = cPickle.Pickler(self._sio, 1)
        self._pickler.persistent_id = self._persistent_id
    def set_manager(self, manager):
        self.manager = manager
    def _persistent_id(self, instance):
        if self._writing is instance:
            return None
        oid = self.manager.get_oid(instance)
        if oid is not None:
            self._instances.append(instance)
        return oid
    def write(self, instance):
        pickleable = IPickleable(instance)
        print 'IPickles(%s) -> %s' % (instance.name, pickleable)
        self._writing = pickleable
        self._sio.seek(0)
        self._pickler.clear_memo()
        self._pickler.dump(pickleable.write_object())
        self._sio.truncate()
        return self._sio.getvalue()
    def __iter__(self):
        return CollectionIterator(self._instances, 1)

class PickleTransformationReader(object):
    implements(ITransformationReader)
    
    def __init__(self):
        self.manager = None
    def _persistent_load(self, oid):
        return self.manager.get_object(oid)
    def set_manager(self, manager):
        self.manager = manager
    def read(self, transformation):
        sio = cStringIO.StringIO(transformation)
        unpickler = cPickle.Unpickler(sio)
        unpickler.persistent_load = self._persistent_load
        pickleable = IPickleable(unpickler.load())
        #print 'read(transformation) => %s (%s)' % (pickleable, pickleable.read_object().name)
        return pickleable.read_object()

class TransformationReaderChain(list):
    implements(ITransformationReader)
    
    def read(self, transformation):
        for reader in self:
            transformation = reader.read(transformation)
        return transformation

class TransformationWriterChain(list):
    implements(ITransformationWriter)
    
    def write(self, transformation):
        for writer in self:
            transformation = writer.write(transformation)
        return transformation


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
from mpx.lib.uuid import UUID
from mpx.lib.metadata.interfaces import IMetaDataProvider
from mpx.lib.metadata.adapters import MetaDataProvider
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry import Interface
from mpx.lib.uuid.interfaces import IUniquelyIdentified

class IdentifierRegistry(weakref.WeakValueDictionary): pass
identifier_registry = IdentifierRegistry()

class UniquelyIdentified(object):
    implements(IUniquelyIdentified)
    adapts(Interface)

    def get_identifier(obj, default = None, create = False):
        uuid = MetaDataProvider.get_subject_meta(obj, 'identifier', default)
        if uuid is None and create:
            uuid = UniquelyIdentified(obj).identifier
        return uuid
    get_identifier = staticmethod(get_identifier)

    def get_identified(uuid, default = None):
        return identifier_registry.get(uuid, default)
    get_identified = staticmethod(get_identified)

    def __new__(klass, context):
        adapter = super(UniquelyIdentified, klass).__new__(klass)
        meta_context = IMetaDataProvider(context)
        uuid = meta_context.setdefault_meta('identifier', UUID())
        identifier_registry.setdefault(uuid, context)
        adapter.initialize(meta_context)
        return adapter

    def initialize(self, context):
        self.context = context

    def __get_id(self):
        return self.context['identifier']

    def __set_id(self, id):
        self.context['identifier'] = id

    identifier = property(__get_id, __set_id)

register_adapter(UniquelyIdentified)

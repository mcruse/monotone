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
# Refactor 2/11/2007
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import Interface
from mpx.componentry import register_adapter
from interfaces import IMetaDataProvider

class MetaDataProvider(object):
    __doc__ = IMetaDataProvider.__doc__

    implements(IMetaDataProvider)
    adapts(Interface)

    def get_subject_meta(subject, predicate, default = None):
        return subject.__dict__.get('__meta', {}).get(predicate, default)
    get_subject_meta = staticmethod(get_subject_meta)

    def get_subject_meta_state(subject):
        state = {}
        meta = subject.__dict__.get('__meta', None)
        if meta is not None:
            state['__meta'] = meta
        return state
    get_subject_meta_state = staticmethod(get_subject_meta_state)

    def __init__(self, context):
        self.context = context
        self.__meta = self.context.__dict__.setdefault('__meta',{})
        super(MetaDataProvider, self).__init__()

    def __getitem__(self, predicate):
        return self.__meta[predicate]

    def get_meta(self, predicate, default = None):
        return self.__meta.get(predicate, default)

    def __setitem__(self, predicate, value):
        self.__meta[predicate] = value

    def add_meta(self, predicate, value):
        meta = self.__meta.setdefault(predicate, value)
        if meta is not value:
            raise TypeError('Context already has meta-data with predicate')
        return meta

    def update_meta(self, predicate, value):
        self.__meta.update({predicate: value})

    def setdefault_meta(self, predicate, default):
        return self.__meta.setdefault(predicate, default)

    def get_predicates(self):
        return self.__meta.keys()

    def get_values(self):
        return self.__meta.values()

    def get_items(self):
        return self.__meta.items()

    def get_triples(self):
        predicates, values = self.__meta.keys(), self.__meta.values()
        return zip([self.context] * len(predicates), predicates, values)

    def get_meta_dictionary(self):
        return self.__meta.copy()

register_adapter(MetaDataProvider)

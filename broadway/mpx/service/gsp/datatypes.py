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
from mpx.lib import factory
from mpx.lib import edtlib
from mpx.lib.node import as_node
#@fixme xmlrpclib marshaller can be removed once edtlib is tied in.
from mpx.lib.xmlrpclib import register_marshaller
from mpx.lib.xmlrpclib import AsDictMarshaller
import types

EM = '/services/Entity Manager'

class EdtDataType(object):
    def __init__(self, value_map=None):
        if value_map is not None:
            if type(value_map) in types.StringTypes:
                value_map = eval(value_map)
            for attr in self.__slots__:
                setattr(self, attr, value_map.get(attr))
                
    @classmethod
    def edt_encode(cls, obj):
        if not isinstance(obj, cls):
            obj = cls(obj)
        edt_map = {'edt__typ':'object',
                   'edt__cls':obj.edt__cls}
        for attr in cls.__slots__:
            edt_map[attr] = getattr(obj, attr, None)
        return edt_map
        
    @classmethod
    def edt_decode(cls, edt_map, obj=None):
        module = edt_map['edt__cls']
        del edt_map['edt__cls']
        del edt_map['edt__typ']
        if obj is None:
            obj = factory(module)
        for attr in obj.__slots__:
            setattr(obj, attr, edt_map.get(attr))
        return obj

    def as_dict(self):
        return self.edt_encode(self)
    
    def __repr__(self):
        return repr(self.as_dict())
    from_dict = edt_decode
    
# consists of an array of GroupSetpointItem
class GroupCfg(list):
    edt__cls = 'mpx.service.gsp.datatypes.GroupCfg'
    @classmethod
    def edt_encode(cls, obj):
        if not isinstance(obj, cls):
            obj = cls(obj)
        edt_map = {'edt__typ':'object',
                   'edt__cls':obj.edt__cls,
                   'value':obj[:]} # obj[:] returns copy of list.
        return edt_map
    
    @classmethod
    def edt_decode(cls, edt_map, obj=None):
        module = edt_map['edt__cls']
        del edt_map['edt__cls']
        del edt_map['edt__typ']
        if obj is None:
            obj = factory(module)
        obj.extend(edt_map.get('value'))
        return obj
    
    def as_dict(self):
        return self.edt_encode(self)
    
    def __repr__(self):
        gcfg = []
        for element in self:
            gcfg.append(repr(element))
        return(repr(gcfg))
           
edtlib.register_class(GroupCfg)
#register_marshaller(GroupCfg, AsDictMarshaller())

class GroupSetpointItem(EdtDataType):
    edt__cls = 'mpx.service.gsp.datatypes.GroupSetpointItem'
    __slots__ = ['setpoint_id', 'name', 'data_type', 'point_type', 'value', 'priority']
    def __init__(self, *args, **kw):
        super(GroupSetpointItem, self).__init__(*args, **kw)
        if self.priority is None:
            self.priority = 16 #defaults to lowest priority
            
edtlib.register_class(GroupSetpointItem)
register_marshaller(GroupSetpointItem, AsDictMarshaller())

class EntityMapping(EdtDataType):
    edt__cls = 'mpx.service.gsp.datatypes.EntityMapping'
    __slots__ = ['setpoint_id', 'property', 'config', 'entity_path'] 
    def __init__(self, *args, **kw):
        super(EntityMapping, self).__init__(*args, **kw)
        if isinstance(self.property, str):
            self.property = eval(self.property)
                           
    def get_property_reference(self):
        if not self.entity_path.startswith('/aliases') and \
            not self.entity_path.startswith(EM):
            entity_path = EM + self.entity_path
        else:
            entity_path = self.entity_path
        entity = as_node(entity_path)
        prop_type, prop_name = self.property
        return entity.get_property_ref(prop_type, prop_name)
    
    def __eq__(self, other):
        if isinstance(other, EntityMapping):
            return self.property == other.property and \
                self.entity_path == other.entity_path
        return NotImplemented
                
edtlib.register_class(EntityMapping)
register_marshaller(EntityMapping, AsDictMarshaller())

class ErrorReport(EdtDataType):
    edt__cls = 'mpx.service.gsp.datatypes.ErrorReport'
    __slots__ = ['severity', 'description', 'custom']
    def __init__(self, *args, **kw):
        super(ErrorReport, self).__init__(*args, **kw)

edtlib.register_class(ErrorReport)
register_marshaller(ErrorReport, AsDictMarshaller())

class TransactionStatus(EdtDataType):
    edt__cls = 'mpx.service.gsp.datatypes.TransactionStatus'
    __slots__ = ['completed', 'success', 'report_items', \
                 'transaction_id', 'percent_complete']
    def __init__(self, *args, **kw):
        super(TransactionStatus, self).__init__(*args, **kw)
  
edtlib.register_class(TransactionStatus)
register_marshaller(TransactionStatus, AsDictMarshaller())  
    

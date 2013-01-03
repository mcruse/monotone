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
Undefined = object()

class TypeSpec(str):
    def tolist(self):
        return self.split(".")
    def fromlist(cls, typenames):
        typenames = filter(None, typenames)
        return cls(".".join(typenames))
    fromlist = classmethod(fromlist)

class MessageType(type):
    def __init__(cls, name, bases, dictionary):
        super(MessageType, cls).__init__(name, bases, dictionary)
        # The next two steps avoid exlicit use of bases and MRO 
        # by performing the steps prior to masking superclass attributes.
        # Use super's registry to register subtype before masking.
        cls.add_subtype(cls)
        cls.REGISTRY = dict()
        # Use super's typespec to build typespec before masking.
        cls.TYPESPEC = TypeSpec.fromlist([cls.typespec(), cls.typename()])

class MessageBase(object):
    __metaclass__ = MessageType
    TYPESPEC = ""
    TYPENAME = ""
    REGISTRY = {}
    def add_subtype(cls, subtype):
        if subtype.typename() in cls.REGISTRY:
            registered = cls.get_subtype(subtype.typename())
            if ((registered.__name__ != subtype.__name__) or 
                (registered.__module__ != subtype.__module__)):
                errormsg = "'%s' already has subtype '%s'"
                raise TypeError(errormsg % (cls.__name__, subtype.typename()))
            else:
                print "Warning, replacing %s with %s" % (registered, subtype)
        cls.REGISTRY[subtype.typename()] = subtype
    add_subtype = classmethod(add_subtype)
    def get_subtype(cls, typename, default=Undefined):
        subtype = cls.REGISTRY.get(typename, default)
        if subtype is Undefined:
            raise KeyError("no such subtype: %s" % typename)
        return subtype
    get_subtype = classmethod(get_subtype)
    def has_subtype(cls, typename):
        return bool(cls.get_subtype(typename, None))
    has_subtype = classmethod(has_subtype)
    def find_subtype(cls, typespec):
        typename,sep,typespec = typespec.partition(".")
        subtype = cls.get_subtype(typename)
        if typespec:
            subtype = subtype.find_subtype(typespec)
        return subtype
    find_subtype = classmethod(find_subtype)
    def find_type(typespec):
        return MessageBase.find_subtype(typespec)
    find_type = staticmethod(find_type)
    def typename(cls):
        return cls.TYPENAME
    typename = classmethod(typename)
    def typespec(cls):
        return cls.TYPESPEC
    typespec = classmethod(typespec)







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
from exceptions import EAbstract

##
# Functions and classes to simplify advanced object techniques.

def as_private_name(klass, attr_name):
    if isinstance(klass, str):
        return "_%s__%s" % (klass, attr_name)
    return "_%s__%s" % (klass.__name__, attr_name)

class GetDescriptorInterface(object):
    def __get__(self, instance, owner_class):
        raise EAbstract

class SetDescriptorInterface(object):
    def __set__(self, instance, value):
        raise EAbstract

class DeleteDescriptorInterface(object):
    def __set__(self, instance):
        raise EAbstract

class ReadonlyPrivateDescriptor(object):
    def __init__(self, klass, attr_name):
        self.name = as_private_name(klass, attr_name)
        return
    def __get__(self, instance, klass):
        return getattr(instance, self.name)

class AbstractDescriptorInterface(object):
    def __init__(self, klass, name):
        self.__class = klass
        self.__name = name
        return
    def __text(self):
        module = ''
        dot = ''
        if hasattr(self.__class, '__module__'):
            module = self.__class.__module__
            dot = '.'
        return (
            "%r is an abstract attribute of %s%s%s which must be overridden." %
            (self.__name, module, dot, self.__class.__name__)
            )
    def __get__(self, instance, owner_class):
        raise EAbstract(self.__text())
    def __set__(self, instance, value):
        raise EAbstract(self.__text())

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
from mpx.componentry import implements
from interfaces import ICounter

class Counter(object):
    implements(ICounter)
    def __init__ (self, initial_value=0):
        self.__initvalue = initial_value
        self.__value = long(initial_value)
    def increment (self, delta = 1):
        return self.post_increment(delta)
    def decrement(self, delta = 1):
        return self.post_decrement(delta)
    def post_increment(self, delta = 1):
        result = self.__value
        self.__value = self.__value + abs(delta)
        return result
    def pre_increment(self, delta = 1):
        self.__value = self.__value + abs(delta)
        return self.__value
    def post_decrement(self, delta = 1):
        result = self.__value
        self.__value = self.__value - abs(delta)
        return result
    def pre_decrement(self, delta = 1):
        self.__value = self.__value - abs(delta)
        return self.__value
    def reset(self):
        self.__value = long(self.__initvalue)
    def __get_value(self):
        return self.__value
    value = property(__get_value)
    def __nonzero__ (self):
        return self.__value != 0
    def __repr__ (self):
        return '<Counter value=%s at %x>' % (self.__value, id(self))
    def __str__ (self):
        return str(self.__value)[:-1]

"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
import string
from mpx.lib.exceptions import EInvalidValue

class Response:
    def __init__(self, request):
        self.request = request
    
    def add_cookie(self, cookie):
        self.request.add_cookie(cookie)
    
    def set_header(self, name, value):
        self.request[name] = value
    
    def get_header(self, name):
        return self.request[name]
    
    def __setitem__(self, name, value):
        self.set_header(name, value)
    
    def __getitem__(self, name):
        return self.request[name]
    
    def push(self, value):
        self.request.push(value)
    
    def send(self, value=None):
        if value:
            self.push(value)
        self.done()
    
    def send_error(self, code, message=None):
        self.request.error(code, message)
    
    def done(self):
        self.request.done()

_attributes = {'comment':'Comment', 
               'domain':'Domain',
               'max-age':'Max-Age', 
               'path':'Path', 
               'secure':'Secure', 
               'version':'Version', 
               'expires':'expires'}

class Cookie:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.attributes = []
    ##
    # Output string to be added to header to set this
    # cookie.
    #
    # @return Header line.
    def output(self):
        header = 'Set-Cookie: %s=%s' % \
                 (self.name, self.value)
        for attribute in self.attributes:
            if attribute[0] != 'Secure':
                header += '; %s=%s' % \
                          (attribute[0], attribute[1])
            elif str(attribute[1]) != '0':
                header += '; Secure'
        return header
    ##
    # Get the value of this cookie.
    #
    # @return The value associated with this 
    #         cookie.
    def get_value(self):
        return self.value
    ##
    # Get the name of this cookie.
    #
    # @return The name of this cookie.
    def get_name(self):
        return self.name
    ##
    # Adds attribute with name, value to list of
    # cookie attributes to be put on this cookies 
    # header line.
    #
    # @param name  The name of the attribute to
    #              add.
    # @param value  The value to assign to the
    #               attribute.
    # @note This is acheives the same thing as
    #       calling cookie[name] = value.
    # @note The parameter name is not case-sensitive.
    def add_attribute(self, name, value):
        self.__setitem__(name, value)
    ##
    # @see add_attribute.
    def __setitem__(self, name, value):
        name = string.lower(name)
        if name not in _attributes:
            raise EInvalidValue('name', name, 
                                'Attribute must be defined')
            
        self.attributes.append((_attributes[name], value))
    ##
    # Get the value of an attribute.
    #
    # @param name  The name of the attribute
    #              whose value is to be fetched.
    # @return The value associated with attribute.
    def get_attribute(self, name):
        return self.__getitem__(name)
    ##
    # @see get_attribute.
    def __getitem__(self, name):
        name = string.lower(name)
        for attribute in self.attributes:
            if string.lower(attribute[0]) == name:
                return attribute[1]
        return None


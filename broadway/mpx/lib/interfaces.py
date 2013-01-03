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
from mpx.componentry import Interface
Undefined = object()

class IInspectable(Interface):
    """
        Provides methods for invocation based 
        inspection and manipulation.
    """
    def attr(name, value=Undefined):
        """
            Get/set attribute 'name'.
            
            If 'value' is provided, attribute 'name' 
            will be set to provided value.
            
            Attribute's value prior to setting (if 'value' provided), 
            is returned from invocation.  If 'value' is set as part 
            of call, then returned value is previous value.
            
            Undefined is returned if attribute does not exist.
        """
    def hasattr(name):
        """
            Returns True if attribute 'name' exists.
        """
    def getattr(name, default=Undefined):
        """
            Get value of attribute 'name' if it exists.
            
            If attribute does not exist and default value 
            is provided, returned default; otherwise raise 
            AttributeError exception.
        """
    def setattr(name, value):
        """
            Set value of attribute 'name' to 'value'.
        """
    def has_method(name):
        """
            Returns True if attribute 'name' exists and 
            its value is callable.
        """
    def get_method(name, default=Undefined):
        """
            Get method named 'name'.
            
            If property does not exist and default is provided, 
            return default; otherwise raise AttributeError.
            
            If property exists but is not callable, raise 
            TypeError. 
        """
    def invoke_method(name, *args, **kw):
        """
            Invoke method named 'name' passing it variable 
            number of arguments and/or keywords.
            
            Invoke result is returned.
        """
    def provides_interface(interface):
        """
            Returns True if interface 'interface' 
            is provided.
            
            Provided interface may be Interface type 
            reference, or fully qualified path specification 
            for interface reference.
        """
    def get_interfaces(named=False):
        """
            Get list of interfaces object supports.
            
            If parameter 'named' provided and True, 
            return list of full-qualified class-paths 
            instead of interface types.
        """


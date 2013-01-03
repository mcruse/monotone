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

class IProxy(Interface):
    """
        Generic object proxy.
        
        Proxy types are generic object wrappers.  Proxies 
        provide a simple API which supports the setting, 
        getting, deleting, and invoking of object attributes.
    """
    def get(name, default=Undefined):
        """
            Get object attribute with name 'name'.
            
            If a default value is provided, this value 
            will be returned if object has no attribute 
            with provided name.  If no default is provided, 
            the method will raise an Attribute Error instead.
        """
    def set(name, value):
        """
            Set object attribute with name 'name' to value 'value'.
        """
    def has(name):
        """
            Check whether object has attribute with name 'name'.
        """
    def call(name, *args, **kw):
        """
            Call method named 'name'.
            
            Variable length arguments and keywords may be 
            provided, and will be passed to invocation.
            
            Result of invocation will be returned.
        """
    def invoke(name, args=(), kw={}):
        """
            Invoke method named 'name'.
            
            Arguments and keywords are not variable as 
            they are in 'call' method.  This is the only 
            difference between this method and 'call'.
        """

class IAsyncProxy(IProxy):
    """
        Extend all IProxy methods to return deferreds 
        instead of direct results.
        
        Every invocation on an IAsyncProxy returns a Deferred 
        instance.  The caller may then use the Deferred instance 
        to get the actual result.
    """









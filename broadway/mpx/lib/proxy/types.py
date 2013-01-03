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
from mpx.componentry import implements
from mpx.lib.proxy.interfaces import Undefined
from mpx.lib.proxy.interfaces import IProxy
from mpx.lib.proxy.interfaces import IAsyncProxy
from mpx.lib.proxy.tools import AsynchronousCallable

class Proxy(object):
    """
        Generic object proxy.
        
        Proxy objects wrap any object and provide access 
        to all that object's attributes via a fixed set 
        of proxy methods.
        
        The primary advantage of proxy objects is that 
        they allow data attribute getting and setting 
        via a method invocation, always.  This makes 
        them a useful tool for RMI type solutions which 
        only support method invocations, and not data 
        attribute manipulation. 
    """
    implements(IProxy)
    def __init__(self, instance):
        self.proxied = instance
        super(Proxy, self).__init__()
    def get(self, name, default=Undefined):
        value = getattr(self.proxied, name, default)
        if value is Undefined:
            typename = type(self.proxied).__name__
            errormsg = "'%s' object has no attribute '%s'"
            raise AttributeError(errormsg % (typename, name))
        return value
    def set(self, name, value):
        return setattr(self.proxied, name, value)
    def has(self, name):
        return hasattr(self.proxied, name)
    def call(self, name, *args, **kw):
        method = getattr(self.proxied, name)
        return method(*args, **kw)
    def invoke(self, name, args=(), kw=()):
        kw = dict(kw)
        return self.call(name, *args, **kw)

class AsyncProxy(Proxy):
    """
        Extends the Proxy type such that all 
        proxy invocations immediately return 
        a Deferred instance, through which the 
        caller may retrieve the results.
    """
    implements(IAsyncProxy)
    get = AsynchronousCallable(Proxy.get)
    set = AsynchronousCallable(Proxy.set)
    has = AsynchronousCallable(Proxy.has)
    call = AsynchronousCallable(Proxy.call)













































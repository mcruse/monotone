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
"""
    Define several utility functions to simplify and centralize 
    common tasks and patterns used when extending built-in or 
    subclass of built-in types.  The following functions are 
    defined:
    
    - locked_method(lockgetter, unboundmethod)
        This function should be called at the class level, passing 
        to it a method which returns a lock used by intances of that 
        class to synchronize state changes, and an unbound method 
        reference which provided *unlocked* functionality desired.
    - coerced_operation(operation)
        This function returns a callable which wraps another 
        callable.  The returned callable casts the return value 
        of the wrapped function to be of the same type as the instance 
        upon which the operation was invoked.  For example, when 
        extending the built-in type list, the default behaviour of 
        '__getslice__' is to return a list which is a subset of the 
        instance upon which the operation was invoked.  The type of 
        the returned value is, by default, the built-in list, and *not* 
        the type of the instance upon which it was invoked.  Use this 
        method to return instances of the subclass type instead.
    - unsupported_operation(name)
        Use this function to override operation named 'name' of 
        superclass, for the sole purpose of masking that method 
        and making it unavailable to users of subclass instances.

    Example uses:
    
    class LockedList(list):
        def __init__(self, *args):
            self._lock = Lock()
            super(LockedList, self).__init__(*args)
        def _getlock(self):
            return self._lock
        __getitem__ = locked_method(_getlock, list.__getitem__)
        __getslice__ = locked_method(_getlock, list.__getslice__)
        __setitem__ = locked_method(_getlock, list.__setitem__)
        append = locked_method(_getlock, list.append)
        pop = locked_method(_getlock, list.pop)
    
    class WierdList(list):
        pop = unsupported_operation('pop')
        __mul__ = coerced_operation(list.__mul__)
        __add__ = coerced_operation(list.__add__)
        __getslice__ = coerced_operation(list.__getslice__)
    
    
    wl = WierdList(range(100))
    wl.append(0)
    wl.pop()
    wl.append = super(type(wl), wl).append
    wl.append(0)
    wl.pop()
    wl.pop = super(type(wl), wl).pop
"""

def locked_method(lockgetter, unboundmethod):
    def invoker(self, *args, **kw):
        invocationlock = lockgetter(self)
        invocationlock.acquire()
        try:
            return unboundmethod(self, *args, **kw)
        finally:
            invocationlock.release()
    return invoker

def coerced_operation(operation):
    def invoke(self, other):
        return type(self)(operation(self, other))
    return invoke

def unsupported_operation(name):
    def getter(self, *args):
        typename = type(self).__name__
        raise AttributeError('%s not supported by type %s' % (name, typename))
    return property(getter)

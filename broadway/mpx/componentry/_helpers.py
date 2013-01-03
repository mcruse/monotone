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
    Utility module providing various helper objects 
    to be used by componentry package only.
"""

class DelayedFactory(object):
    """
        Allows deferred instantiation of an object, 
        instanctating the object upon configurable number 
        of invocations, and returning instanciated object 
        upon configurable number of invocations.
        
        Constructor takes: 
            - 'factory', which will be used for delayed instantiation.
            - 'calls_before_instanciate', which specifies how many times 
                this object will be inoked before instanciating delayed object.
            - 'call_before_return', which specifies how many times this object 
                will be invoked before returning the instanciated object, rather 
                than itself.
        
        For example: 'delayed_error = DelayedFactory(AttributeError, 1, 2)' 
        will return a DelayedFactory object, 'delayed_error', with the 
        following characteristics:
            - First invocation of delayed_error, 
                'delayed_error(*args, **kewords)', will call factory, 
                'factory(*args, **keywords), and save result; invocation 
                will return 'delayed_error' object.
            - Second invocation of delayed_error, 
                'delayed_error(*args, **keywords)', will return 
                result of previous factory call.
            - All future calls of 'delayed_error' object will 
                return result of instanctiated factory.
    """
    def __init__(self, factory, calls_before_instantiate = 1, calls_before_return = 1):
        self.object = None
        self.factory = factory
        self.until_instantiate = calls_before_instantiate
        self.until_return = calls_before_return
    def __call__(self, *args, **keywords):
        self.until_instantiate -= 1
        self.until_return -= 1
        if self.object is None and self.until_instantiate <= 0:
            self.object = self.factory(*args,**keywords)
        if self.until_return <= 0: return self.object
        return self

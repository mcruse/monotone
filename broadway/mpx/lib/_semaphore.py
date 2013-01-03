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
##
# Provide more effecient, possibly platform specific, implementations of
# of the semaphore (Semaphore).

import sys

from mpx._python import threading as _threading
from _condition import Condition as _Condition

_Semaphore = _threading.Semaphore

_version = sys.version_info
del sys

if _version[0:2] == (2, 2):
    class _ModifiedSemaphore_2_2:
        def __init__(self, *args, **kwargs):
            s = _Semaphore(*args, **kwargs)
            s._Semaphore__cond = \
                               _Condition(s._Semaphore__cond._Condition__lock)
            for attr in dir(s):
                if not hasattr(self, attr):
                    setattr(self, attr, getattr(s, attr))
            self._s = s
    _ModifiedSemaphore = _ModifiedSemaphore_2_2
else:
    _ModifiedSemaphore = _Semaphore

##
# Returns a modified instance of Python's threading.Semaphore.
def ModifiedSemaphore(*args, **kwargs):
    m = _ModifiedSemaphore(*args, **kwargs)
    return m

del _version

##
# Set via platform checks, properties, and god knows what...
Semaphore = ModifiedSemaphore

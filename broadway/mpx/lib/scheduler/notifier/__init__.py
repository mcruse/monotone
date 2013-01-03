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
    Package defines multiple versions of Condition classes, where
    Condition classes are types providing same interface as 
    built-in threading.Condition() instances.
    
    Original Python Condition instances relied on busy-loop testing 
    with increasing test-delay and were, therefore, very innefficient 
    implementations likely driven by a need for cross-platform support 
    above performance.
    
    A faster Condition type has is defined by mpx.lib.threading, which 
    relies on support of poll() I/O operations to provide a much more 
    efficient implementation.  Timeout functionality for instances of 
    this Condition use built-in scheduler to provide callback timeout.
    
    Scheduler instances therefore cannot use instances of these Conditions
    because the dependence would be circular.  This package therefore 
    defines an efficient Condition implementation which is not dependent 
    upon those provided by mpx.lib.threading.
    
    The package determines whether or not the system supports poll() and, 
    if it does, uses one of two Condition implementations as the Condition 
    for the system.  The 'PIPEBASED' attribute determines which of the 
    two types are used.  When True, the package uses a pipe-based Condition; 
    otherwise a Unix-type socket-based Condition is used.
"""

PIPEBASED = True

import select
try:
    select.poll()
except:
    supportspoll = False
else:
    supportspoll = True
del(select)

if supportspoll:
    if PIPEBASED:
        from pipebased import Condition
    else:
        from socketbased import Condition
else:
    from mpx.lib.threading import Condition
del(supportspoll)

"""
Copyright (C) 2011 Cisco Systems

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
try:
    from _uptime import *
except:
    # The uptime module won't load in a cross-compile build environment.  The
    # build system relies on some of the built modules which pull this in.
    # These stubs are a hack so the module will load.
    import time
    _t0 = time.time()
    def secs(*args):
        return time.time()-_t0
    def override_secs(*args):
        raise Exception("uptime module failed to load.")
    def raw_secs(*args):
        raise Exception("uptime module failed to load.")
    def max_uptime(*args):
        raise Exception("uptime module failed to load.")
    def tics_per_sec(*args):
        raise Exception("uptime module failed to load.")

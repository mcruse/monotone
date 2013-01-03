"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
from mpx.lib.exceptions import EInvalidValue

class RegisterDescription:
    def __init__(self, offset, count, name, unbound_read,
                 unbound_write=None):
        self.offset  = offset
        self.count   = count
        self.name    = name
        self.read    = unbound_read	    # self == response.ReadHoldingRegisters
        self.write   = unbound_write    # self == CacheWriter

def ResetAccumulator(cache_writer, offset, value, orders=0):
    # According to the spec, you are only aloud to set
    # the KWH accumulator to zero.  Furthermore, this
    # is achieved by setting the INTEGER accumulator
    # to zero.
    if value != 0:
        raise EInvalidValue, ('accumulator', value)
    cache_writer.write_word(0, 0, orders) # Clear the LSW first,
    cache_writer.write_word(1, 0, orders) # then the MSW.
    return

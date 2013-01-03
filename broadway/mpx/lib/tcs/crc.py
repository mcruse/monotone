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
# Compute the CRC of a Tracer 100 packet

class Crc:
    def __init__(self, aValue=0xFFFF, **keywords):
        self.lo = aValue & 255
        self.hi = ( aValue >> 8 ) & 255
        if keywords.has_key('check'):
            byte_array = keywords['check']
            for c in byte_array:
                self.compute(c)

                
    
    def compute(self, aByte):
        tmp = self.lo
        self.lo = self.hi
        self.hi = tmp ^ aByte
        self.lo = (self.lo ^ ((((self.hi >> 4) ^ self.hi ) & 15) ^ \
                  (self.hi << 3) ^ (self.hi << 7))) & 255
        self.hi = (self.hi ^ ((((self.hi >> 5) ^ (self.hi >> 1)) & 7) ^ \
                  (self.hi << 4))) & 255

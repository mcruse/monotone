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
##
# @fixme Password modes need work.  (Base vs. Logged in, USER vs. ADMIN).

import array

SOH = '\001'
EOT = '\004'

class PromptType:
    def __init__(self, is_base, is_user):
        self._is_u = is_user
        self._is_b = is_base
    def on_user_port(self): return self._is_u
    def on_maintenance_port(self): return not self._is_u
    def protected_level(self): return not self._is_b
    def base_level(self): return self._is_b

BASEUSER = PromptType(1,1)
BASEMAINTENANCE = PromptType(1,0)
PROTECTEDUSER = PromptType(0,1)
PROTECTEDMAINTENANCE = PromptType(0,0)

def calc_crc(cmd):
    crc_reg = 0xFFFF
    for c in cmd:
        crc_reg = crc_reg ^ ord(c)
        for i in range(0,8):
            if crc_reg & 1:
                crc_reg = (crc_reg >> 1) ^ 0xA001
            else:
                crc_reg = crc_reg >> 1
    return crc_reg

def append_crc(b):
    crc = calc_crc(b)
    b.append(chr(crc & 0xFF))
    b.append(chr(crc >> 8))

def as_capstone_float(value):
    value = float(value)
    return "%.4e" % value

#
# Response argument convertion routines.
#

NIBBLE_0 = ord('0') # 48
NIBBLE_A = ord('A') # 65
NIBBLE_a = ord('a') # 97

##
# Convert an ascii character representation of a 'nibble' to an int.
# @param char A character representation of a 'nibble'
# @value '0'-'9','a'-'f','A'-'F'
# @return An int.
# @value 0-15
# @fixme Add validation.
def from_nibble(char):
    c = ord(char)
    if c >= NIBBLE_a:
        return c - NIBBLE_a + 10
    if c >= NIBBLE_A:
        return c - NIBBLE_A + 10
    return c - NIBBLE_0

##
# Convert a string representation of an unsigned hex value to an int.
# @param value A string representation of an unsigned hex value.
# @return A long.
def from_h(value):
    i = 0L
    for c in value:
        i = i * 16
        i = i + from_nibble(c)
    return i

##
# Convert a string representation of a signed hex value to an int.
# @param value A string representation of a signed hex value.
# @return A long.
# @fixme Handle negative numbers.  May require a size hint (1, 2, and 4 bytes).
def from_sh(value):
    i = 0L
    for c in value:
        i = i * 16
        i = i + from_nibble(c)
    return i

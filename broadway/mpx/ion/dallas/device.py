"""
Copyright (C) 2001 2009 2010 2011 Cisco Systems

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
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.exceptions import EInvalidValue
from crc import crc_of

##
# Converts hex string representation of a dallasbus address
# to a actual dallasbus address.
#
# @param value  The hes string representation of the address.
# @return The converted dallasbus address.
#
def asciihex_to_address(value):
    # There may be a much easier way to do this.
    nibble_map = {'0':0,  '1':1,  '2':2,  '3':3,  '4':4,
                  '5':5,  '6':6,  '7':7,  '8':8,  '9':9,
                  'a':10, 'b':11, 'c':12, 'd':13, 'e':14, 'f':15,
                  'A':10, 'B':11, 'C':12, 'D':13, 'E':14, 'F':15}
    addr = ''
    for i in range(0,len(value),2):
        addr += chr((nibble_map[value[i]] << 4) +
                    nibble_map[value[i+1]])
    if crc_of(addr) != 0:
        # CRC does not pass, try the reverse byte order instead
        addr = ''
        for i in range(len(value),0,-2):
            addr += chr((nibble_map[value[i-2]] << 4) +
                    nibble_map[value[i-1]])
    return addr

##
# Converts a dallasbus address into an ascii string of
# hex values.
#
# @param address  The dallas address to convert.
# @return Hex string representation of address.
#
def address_to_asciihex(address):
    # There may be a much easier way to do this.
    nibble_list = '0123456789ABCDEF'
    ascii = ''
    for b in address:
        ascii += nibble_list[ord(b) >> 4]
        ascii += nibble_list[ord(b) & 0x0F]
    return ascii

##
# Convert any correct representation of a dallasbus
# address to the actual dallasbus address.
#
# @param value  The value to convert.
# @return Dallasbus address.
# @throws EInvalidValue  If the value cannot be converted.
#
def value_to_address(value):
    # FIXME:  Obviously belongs in a DALLASDEVICE base class, or in the
    # DallasBus module.  There may be a much easier way to do this.
    if len(value) == 8:
        address = value
    elif len(value) == 16:
        address = asciihex_to_address(value)
    else:
        raise EInvalidValue, ('address', value)
    return address

##
# Base Class for Dallas Devices.
#
class Device(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
    ##
    # Configure object.
    #
    # @param config  Configuration dictionary.
    # @key address  Dallasbus address for this device.
    # @required
    #
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'address', REQUIRED, config, value_to_address)

    ##
    # Get configuration of this object.
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'address', config, address_to_asciihex)
        return config

def factory():
    return Device()

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
import array
from mpx.lib.exceptions import EIOError

class EWriteError(EIOError):
    pass

def calc_sum(str):
    """
    Calculate sum of the elements of the passed data
    """
    sum = 0
    for i in str:
    	sum = sum + ord(i)	
    return sum

def format_address(strAddr):
    """
    convert meter reading to proper format writable over the serial port
    """
    bytes = array.array('B')
    #Append 0 if address if the sring is less than 12 bytes
    if len(strAddr) < 12:
        strAddr = '0' * (12 - len(strAddr)) +  strAddr
    #Truncate to 12 bytes if the address is more that 12
    strAddr = strAddr[:12]
    strAddr = ''.join( strAddr.split(" ") )
    for i in range(0, len(strAddr), 2):
        #convert to a binary string
        bytes.append(int(strAddr[i:i+2], 16))
    #Reverse the order since the protocol needs LSB first
    bytes.reverse()
    return bytes.tostring()

def format_rt_reading(reading):
    return  "%02X%02X%02X.%02x"% (ord(reading[3]), 
                                  ord(reading[2]), 
                                  ord(reading[1]), 
                                  ord(reading[0])) 


def format_reading(reading):
    return  "%02X%02X%02X.%02x"% (ord(reading[3]) - 0x33, 
                                  ord(reading[2]) - 0x33, 
                                  ord(reading[1]) - 0x33, 
                                  ord(reading[0]) - 0x33) 
def format_password(strAddr):
    """Copied from format_address

    format_address wanted string length to be exact 12 characters long
    """
    bytes = array.array('B')
    for i in range(0, len(strAddr), 2):
        #convert to a binary string
        bytes.append(int(strAddr[i:i+2], 16) + 0x33)
    #Reverse the order since the protocol needs LSB first
    bytes.reverse()
    return bytes.tostring()

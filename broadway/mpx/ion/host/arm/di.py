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
from node import ARMNode

##
# Class for digital input on AVR board.
#
class Contact(ARMNode):
    ##
    # Get current value for digital input.
    #
    # @param skipCache  Use cached value.
    # @value 0  May use cached value.
    # @value 1  May not use cached value.
    # @return Current value.
    #
    def get(self, skipCache=0):
        channel = self.id
        if channel < 1 or channel > 4:
            raise Exception('channel must be between 1 and 4')
        command = 'di\r'
        dict = self.read_response(command)
        if dict['command'] != 'di':
            raise Exception('command mismatch: %s' % (dict['command'],))
        if (dict['inputs'] & (1 << (channel - 1))) != 0:
            return 0
        return 1

def factory():
    return Contact()

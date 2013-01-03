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
from mpx.lib.configure import as_boolean

##
# Class for Relays on AVR.
#

DOs = 0

class Relay(ARMNode):
    ##
    # Get the current value of the relay.
    #
    # @param skipCache  Use cached value.
    # @value 0  May use cached value.
    # @value 1  May not use cached value.
    # @default 0
    # @return Current value of relay.
    #
    def get(self, skipCache=0):
        channel = self.id
        if channel < 1 or channel > 2:
            raise Exception('channel must be between 1 and 2')
        bit = 1 << (channel - 1)
        if DOs & bit:
            return 1
        return 0

    ##
    # Set the value of the relay.
    #
    def set(self, value, asyncOK=1):
        global DOs
        channel = self.id
        if channel < 1 or channel > 2:
            raise Exception('channel must be between 1 and 2')
        # regardless of the name, the next line
        # converts various words and values to int 0,1
        value = as_boolean(value) 
        bit = 1 << (channel - 1)
        if value:
            DOs |= bit
        else:
            DOs &= ~bit
        command = 'do %d\r' % (DOs)
        dict = self.read_response(command)
        if dict is None:
            raise Exception('no response')
        error = dict.get('error')
        if error:
            raise Exception(str(dict['error']))
        if dict['command'] != 'do':
            raise Exception('command mismatch: %s' % (dict['command'],))
        if dict['outputs'] != DOs:
            raise Exception('outputs do not match')

def factory():
    return Relay()

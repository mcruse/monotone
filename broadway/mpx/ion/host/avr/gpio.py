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
from node import AVRNode
from mpx.lib.configure import as_boolean
import types

##
# Class for Relays on AVR.
#
class GPIO(AVRNode):
    base_get_cmd = '\x1D\x00\x01'
    base_set_cmd = '\x1C\x00\x03'

    def __init__(self):
        AVRNode.__init__(self)
        self.last_value = [3,255,0]

    def configure(self, config):
        AVRNode.configure(self, config)
        self.get_cmd = self.base_get_cmd + chr(self.id)
        return
    def start(self):
        self.set(self.last_value)
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
        return self.last_value

    ##
    # Set the value of the relay.
    #
    # @param value  tuple with mode, rate, pattern.
    # @mode 3  output bit pattern.
    # @rate    milliseconds between bit shifts.
    # @pattern bit pattern to shift out, ex 0x55, 0xF0, 0x10
    # @param asyncOK  Wait for confirmation of command receipt.
    # @value 1  Do not wait for confirmation.
    # @value 0  Wait for confirmation.
    # @default 1
    #
    def set(self, value, asyncOK=1):
        if type(value) == types.StringType:
            value = eval(value)
        mode, rate, pattern = value
        self.last_value = value
        self.avr.invoke_message(self.base_set_cmd + chr(mode) + chr(rate) + chr(pattern))

def factory():
    return GPIO()
     
        
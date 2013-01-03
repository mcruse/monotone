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
from node import AVRNode

##
# Class for counters on the AVR.
#
class Counter(AVRNode):
    base_get_cmd = '\x13\x00\x01'
    base_set_cmd = '\x12\x00\x01'

    def __init__(self):
        AVRNode.__init__(self)

    def configure(self, config):
        AVRNode.configure(self, config)
        self.get_cmd = self.base_get_cmd + chr(self.id)
        self.set_cmds = [self.base_set_cmd + chr(self.id)]
        return

    ##
    # Get the current value of the counter.
    #
    # @param skipCache  Use cached value.
    # @value 0  May use cached value.
    # @value 1  May not use cached value.
    # @default 0
    #
    def get(self, skipCache=0):
        result = self.avr.invoke_message(self.get_cmd)
        return ord(result[0]) +		\
               (ord(result[1]) << 8) +	\
               (ord(result[2]) << 16) +	\
               (ord(result[3]) << 24)

    ##
    # Set the value of the counter.
    #
    # @param value  The new value to set counter to.
    # @param asyncOK  Wait for result.
    # @value 1  Do not wait for acknowledgement.
    # @value 0  Wait for acknowledgement.
    # @default 1
    #
    # @note The only value that one would usually set a
    #       counter to is 0, to reset the counter.
    #
    def set(self, value, asyncOK=1):
        self.avr.invoke_message(self.set_cmds[int(value)])

def factory():
    return Counter()

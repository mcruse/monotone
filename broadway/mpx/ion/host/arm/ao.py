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
from arm import calibration_index as index
from arm import calibration_items as k

##
# Class for digital input on AVR board.
#
class AnalogOutput(ARMNode):
    def __init__(self):
        ARMNode.__init__(self)
        self.value = 0

    def configure(self, cd):
        ARMNode.configure(self, cd)
        if self.id < 1 or self.id > 3:
            self.id = None
            raise EInvalidValue('AO channel must be between 1 and 3.  %d is invalid' % self.id)
    def start(self):
        calibration = self.coprocessor.calibration['ai%d' % self.id][:len(k)]
        self.calibration = dict(zip(k, calibration))
        self._max_ao = self.calibration['ao_max_out']
    ##
    # Get current value for analog output.
    #
    def get(self, skipCache=0):
        return self.value
    ##
    # Set current value for analog output.
    #
    def set(self, value):
        value = float(value)
        if value < 0: value = 0
        if value > 10: value = 10
        self.value = value
        value = int(value * self._max_ao / 10.0)
        command = 'ao %d %d\r' % (self.id, value)
        dict = self.read_response(command)
        if dict['command'] != 'ao':
            raise Exception('command mismatch: %s' % (dict['command'],))
        if dict['channel'] != self.id:
            raise Exception('channel mismatch: %s %d' % (str(dict['channel']), self.id,))
        if dict['value'] != value:
            raise Exception('value mismatch: %s %d' % (str(dict['value']), value,))

def factory():
    return AnalogOutput()

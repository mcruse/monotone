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
# @todo  If the bitopt dictionaries are not modified after creation, then they
# should be moved outside the init so there is a single shared dictionary.

import mpx.lib
from mpx.ion.ranges import *
from module import *
from bitopt import bitopt

class ADAM4021(Module):

    format_attribute = 'data format'
    slew_attribute = 'slew rate'
    range_attribute = 'output range'

    def __init__(self, name, version, configuration_dict, activate):
        Module.__init__(self)
        self.dataformat = bitopt(self.format_attribute,
                                 0x3,0,'Engineering units',
                                 {0:'Engineering units',
                                  1:'% of FSR',
                                  2:'hexadecimal'})
        self.slew = bitopt(self.slew_attribute,
                           0x3c,2,'2.0 V/sec 4.0mA/sec',
                           {1:'0.0625 V/sec 0.125mA/sec',
                            2:'0.125 V/sec 0.25mA/sec',
                            3:'0.25 V/sec 0.5mA/sec',
                            4:'0.5 V/sec 1.0mA/sec',
                            5:'1.0 V/sec 2.0mA/sec',
                            6:'2.0 V/sec 4.0mA/sec',
                            7:'4.0 V/sec 8.0mA/sec',
                            8:'8.0 V/sec 16.0mA/sec',
                            9:'16.0 V/sec 32.0mA/sec',
                            10:'32.0 V/sec 64.0mA/sec',
                            11:'64.0 V/sec 128.0mA/sec'})
        self.output = bitopt(self.range_attribute,
                             0xff,0,Range.four_to_twenty_mA,
                             {0x30:Range.zero_to_twenty_mA,
                              0x31:Range.four_to_twenty_mA,
                              0x32:Range.zero_to_ten_V})
        self.attrdict.update({self.dataformat:7,self.slew:7,self.output:3})

    def configure(self, config):
        Module.configuration(self, config)
        if not config.has_key(self.range_attribute):
            # If the 'output range' isn't explicitly configured, query the device
            # for its current setting.
            temp = self.ConfigurationStatus()
            config[self.range_attribute] = temp[self.range_attribute]
        # Add the 4021's analog output
        ion = mpx.lib.factory('mpx.ion.adam.analog_out')
        ion.configure({'name':'VOUT', 'parent':self, 'id':0,
                       self.range_attribute:config[self.range_attribute]})

    def AnalogDataOut(self,val):
        chop(self.validate(val,prefix='#',vchar='>'))

    def Calibration4mA(self):
        self.validate('0')

    def Calibration20mA(self):
        self.validate('1')

    def TrimCalibration(self,count):
        self.validate('3'+hexb(count))

    def StartUpConfiguration(self):
        self.validate('4')

    def ResetStatus(self):
        return chop(self.validate('5'))

    def LastValueReadback(self):
        return chop(self.validate('6'))

    def CurrentReadback(self):
        return chop(self.validate('8'))

def factory():
    return ADAM4021()

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
# @todo If the bitopt dictionaries are not modified after creation, then they
# should be moved outside the init so there is a single shared dictionary.

import mpx.lib
from mpx.ion.ranges import *
from module import *
from bitopt import bitopt

class ADAM4017(Module):
    format_attribute = 'data format'
    range_attribute = 'input range'
    integration_attribute = 'integration time'

    ai_list = ('Vin0', 'Vin1', 'Vin2', 'Vin3', 'Vin4', 'Vin5', 'Vin6', 'Vin7')

    def __init__(self):
        Module.__init__(self)
        self.dataformat = bitopt(self.format_attribute,
                                 0x3,0,'Engineering units',
                                 {0:'Engineering units'})

        self.inputrange = bitopt(self.range_attribute,
                                 0xff,0,Range.pm_1V,
                                 {0x08:Range.pm_10V,
                                  0x09:Range.pm_5V,
                                  0x0a:Range.pm_1V,
                                  0x0b:Range.pm_500mV,
                                  0x0c:Range.pm_150mV,
                                  0x0d:Range.pm_20mA})

        self.integration = bitopt(self.integration_attribute,
                                  0x80,7,'50 ms',
                                  {0:'50 ms',
                                   1:'60 ms'})

        self.attrdict.update({self.dataformat:7, self.inputrange:3,
                              self.integration:7})

    def configure(self, config):
        Module.configuration(self, config)
        if not config.has_key(self.range_attribute):
            # If the 'input range' isn't explicitly configured, query the device
            # for its current setting.
            temp = self.ConfigurationStatus()
            config[self.range_attribute] = temp[self.range_attribute]
        # Add the 4017's Analog Inputs.
        id = 0
        for ai in self.ai_list:
            ion = mpx.lib.factory('mpx.ion.adam.analog_out')
            ion.configure({'name':ai, 'parent':self, 'id':0,
                           self.range_attribute:config[self.range_attribute]})
            id += 1

    def ReadChannelStatus(self):
        val = int(chop(self.validate('6')),16)
        b = ()
        for i in range (0,8):
            if (val&0x80):
                b = b + (1,)
            else:
                b = b + (0,)
            val = val << 1
        return b

    def AnalogDataIn(self):
        b = self.validate('',prefix='#',vchar='>')
        return b[1:8],b[8:15],b[15:22],b[22:29],b[29:36], \
               b[36:43],b[43:50],b[50:57]

    def ReadAnalogChannelN(self,channel):
        return self.validate(str(channel),prefix='#',vchar='>')[1:8]

    def EnableMultiplexing(self,c0,c1,c2,c3,c4,c5,c6,c7):
        b = (c0,c1,c2,c3,c4,c5,c6,c7)
        w = 0
        for i in b:
            if (i):
                w = w | 0x100
            w = w >> 1
        self.validate('5'+hexb(w))

    def SpanCalibration(self):
        self.validate('0')
        
    def OffsetCalibration(self):
        self.validate('1')

    def SynchronizedSampling(self):
        self.inf.bus.write('#**'+CR)

def factory():
    return ADAM4017()

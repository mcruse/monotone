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
#
# $Id: adam7013.py 20101 2011-03-06 16:02:15Z bhagn $
#
# Author: Magnus Heino, magnus.heino@rivermen.se
#
# Description: Driver for the ICP CON 7013 module
#

import mpx.lib
from mpx.ion.ranges import *
from module import *
from bitopt import bitopt

class ADAM7013(Module):
    format_attribute = 'data format'
    range_attribute = 'input range'

    def __init__(self):
        Module.__init__(self)
        self.dataformat = bitopt(self.format_attribute,
                                 0x3,0,'Engineering units', 
                                 {0:'Engineering units', 
                                  1:'% of FSR',  
                                  2:'hexadecimal'})
        self.inputrange = bitopt(self.range_attribute,
                                 0xff,0,Range.plat_0_to_100,
                                 {0x20:Range.plat_m_100_to_100,
                                  0x21:Range.plat_0_to_100,
                                  0x22:Range.plat_0_to_200})
        self.attrdict.update({self.dataformat:7,self.inputrange:3})

    def configure(self, config):
        Module.configuration(self, config)
        if not config.has_key(self.range_attribute):
            # If the 'input range' isn't explicitly configured, query the device
            # for its current setting.
            temp = self.ConfigurationStatus()
            config[self.range_attribute] = temp[self.range_attribute]
        # Add the 7013's analog input.
        ion = mpx.lib.factory('mpx.ion.adam.analog_in')
        ion.configure({'name':'SENSE0', 'parent':self, 'id':0,
                       self.range_attribute:config[self.range_attribute]})

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
        return self.AnalogDataIn()[channel]

    def SpanCalibration(self):                                                 
        self.validate('0')

    def OffsetCalibration(self):
        self.validate('1')

    def SynchronizedSampling(self):
        self.inf.bus.write('#**'+CR)

def factory(name, version, configuration_dict, activate): 
    return ADAM7013(name, version, configuration_dict, activate)

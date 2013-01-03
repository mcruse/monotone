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
# @todo See DigitalOut TODO 3!  We may need to *properly* initialize the digital
# out!  Although this is probably the related IOPoint's job.

import mpx.lib
from bitopt import bitopt
from module import Module

class ADAM4050(Module):
    di_list = ('DI0', 'DI1', 'DI2', 'DI3', 'DI4', 'DI5', 'DI6')
    do_list = ('DO0', 'DO1', 'DO2', 'DO3', 'DO4', 'DO5', 'DO6', 'DO7')

    def __init__(self):
        Module.__init__(self)
        self.type = bitopt("type code",0xff,0,'40XX',
                         {0x40:'40XX'})
        self.id = bitopt("module identification",0x07,0,'ADAM-4050',
                         {0:'ADAM-4050'})
        self.attrdict.update({self.type:3,self.id:7})

        # Add the 4050's Digital Inputs.
        id = 0
        for di in self.di_list:
            di_ion = mpx.lib.factory('mpx.ion.adam.digital_in')
            di_ion.configure({'parent':self, 'name':di, 'id':id})
            id += 1
        # Add the initial output status, see TODO 1!
        self.do_status = [0,0,0,0,0,0,0,0]
        # Add the 4050's Digital Outputs.
        id = 0
        for do in self.do_list:
            do_ion = mpx.lib.factory('mpx.ion.adam.digital_out')
            do_ion.configure({'parent':self, 'name':do, 'id':id})
            id += 1

    def DigitalDataIn(self):
        w = chop(self.validate('6'))
        return getbits(int(w[0:2],16)),getbits(int(w[2:4],16))

    def DigitalDataOut(self,c0,c1,c2,c3,c4,c5,c6,c7):
        b = (c0,c1,c2,c3,c4,c5,c6,c7)
        w = 0
        for i in b:
            if (i):
                w = w | 0x100
            w = w >> 1
        self.validate('00'+hexb(w),prefix='#',vchar='>')

    def DigitalDataBit(self,channel,bit):
        self.validate('1'+str(channel)+hexb(bit),
                      prefix='#',vchar='>')

    def SynchronizedSampling(self):
        self.line_handler.bus.write('#**'+CR)

    def ReadSynchoronizedData(self):
        l = chop(self.validate('4'))
        return l[0:1],l[1:5]


def factory():
    return ADAM4050()

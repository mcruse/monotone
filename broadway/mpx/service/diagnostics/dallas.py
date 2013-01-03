"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import sys

from avr_lib import *
from test import Test
from mpx import properties

from ion import Factory

class DallasTester(Test):
    def __init__(self, **kw):
        self._num_dallas_busses = 4
        if properties.HARDWARE_CODENAME == "Megatron":
            self._num_dallas_busses = 2
        super(DallasTester, self).__init__(**kw)
        self._test_name = 'DallasTester'
        self._avr = get_avr()
        return
        
    def runtest(self):
        self.log('Testing Dallas temperature sensors.')
        for bus in range(1, (self._num_dallas_busses + 1)):
            if properties.HARDWARE_CODENAME == "Megatron":
                a = as_node('/interfaces/dallas%d' % bus).findall()[1][0]
            else:
                a = self._avr.dallas_readrom(bus)
            address = self._avr.tohex(a)
            if address == 'ffffffffffffffff':
                self.log('ERROR: Bus %d, bad address.' % bus)
                self._nerrors += 1
        self.log('Dallas temp sensors, found %d errors and %d warnings.' %
            (self._nerrors, self._nwarnings))
        return self.passed()
        
f = Factory()
f.register('DallasTester', (DallasTester,))


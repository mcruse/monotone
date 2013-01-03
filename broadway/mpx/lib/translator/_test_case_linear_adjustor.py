"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import random

from mpx_test import DefaultTestFixture, main

from mpx.lib.node import CompositeNode
from mpx.lib.translator.linear_adjustor import LinearAdjustor

class FakeION(CompositeNode):
    def __init__(self,start_value = 1):
        self.current_value = start_value
    
    def get(self, skipCache=0):
        rtvalue = self.current_value
        self.current_value += 1
        return rtvalue

    def set(self,value):
        self.current_value = value
        
class TestCase(DefaultTestFixture):
                
    def get_fake_ion(self,start_value = 1):
        config = {'parent':None,'name':'fake_ion'}
        fake_ion = FakeION(start_value)
        fake_ion.configure(config)
        return fake_ion
    
    def test_get_1(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(),
                  'name':'linear_adjustor',
                   'multiplier':2.0}
        la.configure(config)
        value = la.get()
        if value != 2.0:
            self.fail('wrong value returned from get. Value returned: '
                      + str(value))

    def test_get_2(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(100),
                  'name':'linear_adjustor',
                   'multiplier':2.0}
        la.configure(config)
        value = la.get()
        if value != 200.0:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value))

    def test_get_3(self):
        la = LinearAdjustor()
        random_multiplier = random.uniform(1.0,100.00)

        config = {'parent':self.get_fake_ion(100),'name':'linear_adjustor',
                  'multiplier':random_multiplier}
        la.configure(config)
        value = la.get()
        if value != 100*random_multiplier:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value) + '\n' +
                      'Multipler: ' + str(random_multiplier))
    
    def test_get_with_offset_1(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(),
                  'name':'linear_adjustor',
                  'multiplier':2.0,
                  'offset':25.0}
        la.configure(config)
        value = la.get()
        if value != 27:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value))

    def test_get_with_offset_2(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(100),
                  'name':'linear_adjustor',
                  'multiplier':2.0,
                  'offset':25.0}
        la.configure(config)
        value = la.get()
        if value != 225.0:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value))

    def test_get_with_offset_3(self):
        random_offset = random.uniform(1.0,100.00)
        la = LinearAdjustor()
        random_multiplier = random.uniform(1.0,100.00)

        config = {'parent':self.get_fake_ion(100),
                  'name':'linear_adjustor',
                  'multiplier':3.0,
                  'offset':random_offset}
        la.configure(config)
        value = la.get()        
        if value != 100*3 + random_offset:
            self.fail('wrong value returned from get. Value returned: ' 
                       + str(value) + '\n' +
                      'Multipler: ' + str(random_multiplier))

    def test_get_with_just_offset_1(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(1),
                  'name':'linear_adjustor',                  
                  'offset':25.0}
        la.configure(config)
        value = la.get()
        if value != 26:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value))

    def test_get_with_just_offset_2(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(100),
                  'name':'linear_adjustor',                  
                  'offset':25.0}
        la.configure(config)
        value = la.get()
        if value != 125.0:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value))

    def test_get_with_just_offset_3(self):
        random_offset = random.uniform(1.0,100.00)
        la = LinearAdjustor()
        random_multiplier = random.uniform(1.0,100.00)

        config = {'parent':self.get_fake_ion(100),
                  'name':'linear_adjustor',
                  'offset':random_offset}
        la.configure(config)
        value = la.get()        
        if value != 100 + random_offset:
            self.fail('wrong value returned from get. Value returned: ' 
                       + str(value) + '\n' +
                      'Multipler: ' + str(random_multiplier))
            
            
    def test_set_1(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(1),
                  'name':'linear_adjustor',
                  'multiplier':2.0}
        la.configure(config)
        la.set(200)
        value = la.get()
        if value != 200.0:
            self.fail('wrong value returned from get. Value returned: ' 
                       + str(value))

    def test_set_2(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(1),
                  'name':'linear_adjustor',
                  'multiplier':2.0}
        la.configure(config)
        la.set(23.3)
        value = la.get()
        if value != 23.3:
            self.fail('wrong value returned from get. Value returned: ' + str(value))

    def test_set_with_offset_1(self):
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(1),
                  'name':'linear_adjustor',
                  'multiplier':2.0,
                  'offset':25}
        la.configure(config)
        la.set(200)
        value = la.get()
        if value != 200.0:
            self.fail('wrong value returned from get. Value returned: ' 
                       + str(value))

    def test_set_with_offset_2(self):
        random_offset = random.uniform(1.0,100.00)
        la = LinearAdjustor()
        config = {'parent':self.get_fake_ion(1),
                  'name':'linear_adjustor',
                  'multiplier':2.0,
                  'offset':random_offset}
        la.configure(config)
        la.set(23.3)
        value = float('%.1f' % la.get())        
        if value != 23.3:
            self.fail('wrong value returned from get. Value returned: ' + str(value))

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

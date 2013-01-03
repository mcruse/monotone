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
from mpx_test import DefaultTestFixture, main

import random
import time

from mpx.lib.node import CompositeNode
from mpx.lib.translator.calculator import Calculator, \
     PeriodicAverageColumn, PeriodicDeltaColumn
from mpx.lib.exceptions import EInvalidValue, ENotStarted

debug = 0

class FakeION(CompositeNode):
    def __init__(self,start_value = 1, step_size = 1):
        self.current_value = start_value
        self.last_value = self.current_value - step_size
        self.step_size = step_size
    
    def get(self, skipCache=0):
        self.last_value = self.current_value
        self.current_value += self.step_size
        return self.current_value
    def set(self,value):
        self.current_value = value
    def attach_variable(self, name):
        if   name == 'now':
            return time.time
        elif name == 'value':
            return self._current_value_
        elif name == 'last_value':
            return self._last_value_
        elif name == 'last_time':
            return self._last_time_
        elif name == 'period':
            return self._period_
        else:
            return self._bad_attach_
    def _current_value_(self):
        return self.get()
    def _last_value_(self):
        if debug: print 'Get last value of :', self.last_value
        return self.last_value
    def _last_time_(self):
        if debug: print 'Get last time of :', time.time() - 5.0
        return time.time() - 5.0
    def _period_(self):
        if debug: print 'Get period of : 900'
        return 900
    def _bad_attach_(self):
       raise EAttributeError('attempt to attach to non-existant variable',
                             self)

class TestCase(DefaultTestFixture):
    def get_fake_ion(self,start_value = 1):
        config = {'parent':None,'name':'fake_ion'}
        fake_ion = FakeION(start_value)
        fake_ion.configure(config)
        return fake_ion
    def test_get_1(self):
        la = Calculator()
        config = {'parent':self.get_fake_ion(),
                  'name':'linear_adjustor',
                  'statement':'(x+y)/z',
                  'variables':[{'vn':'x','node_reference':'1.0'}, 
                               {'vn':'y','node_reference':'2'},
                               {'vn':'z','node_reference':'3'}]}
        la.configure(config)
        la.start()
        value = la.get()
        if value != 1.0:
            self.fail('wrong value returned from simple get. Value returned: '
                      + str(value))
        return
    def test_get_2(self):
        la = Calculator()
        config = {'parent':self.get_fake_ion(100),
                  'name':'linear_adjustor',
                  'statement':'(x+y)/z',
                  'variables':[{'vn':'x','node_reference':'0.0'}, 
                               {'vn':'y','node_reference':'2'},
                               {'vn':'z','node_reference':'3'}]}
        la.configure(config)
        la.start()
        c = {'x':self.variable_x}
        value = la.evaluate(c)
        if value != 1.0:
            self.fail('wrong value returned from get. Value returned: ' 
                      + str(value))
    def test_get_3(self):
        la = PeriodicAverageColumn()
        config = {'parent':self.get_fake_ion(100),
                  'name':'average'}
        la.configure(config)
        la.start()
        c = {}
        for i in range(100):
            value = la.evaluate(c)
            if abs(value - 0.40) > 0.01:  
                self.fail('wrong value returned from get. Value returned: ' 
                          + str(value))
    def test_get_4(self):
        la = PeriodicDeltaColumn()
        config = {'parent':self.get_fake_ion(100),
                  'name':'average'}
        la.configure(config)
        la.start()
        c = {}
        for i in range(100):
            value = la.evaluate(c)
            if abs(value - 2.0) > 0.01:  
                self.fail('wrong value returned from get. Value returned: ' 
                          + str(value))
    def test_negative_const(self):
        la = self._create_calculator('(x+y)/z',{'x':'1.0','y':'2','z':'-3'})
        la.start()
        value = la.get()
        if value != -1.0:
            self.fail('wrong value returned from simple get. Value returned: '
                      + str(value))
    def test_subtraction(self):
        la = self._create_calculator('x - y',{'x':'-1.0','y':'-2.0'})
        la.start()
        value = la.get()
        if value != 1.0:
            self.fail('wrong value returned from simple get. Value returned: '
                      + str(value))
    def test_failure_to_start(self):
        la = self._create_calculator('x - y',{'x':None,'y':'-2.0'})
        try:
            la.start()
        except EInvalidValue:
            pass
        else:
            self.fail('calculator start: Should have raised exception.')
        try:
            value = la.get()
        except ENotStarted:
            pass
        else:
            self.fail('ENotStart exception should have been raised')
        return
    def _create_calculator(self,statement,variables,start=1):
        config = {'name':'test','parent':self.get_fake_ion(start),
                  'statement':statement,'variables':[]}
        for name in variables.keys():
            variable = {'vn':name,'node_reference':variables[name]}
            config['variables'].append(variable)
        calc = Calculator()
        calc.configure(config)
        return calc
    def test_with_space(self):
        calc = self._create_calculator('a + b',{'a':' 5 ', 'b':' -5'})
        calc.start()
        value = calc.get()
        self.failUnless(value == 0,'Calc created with spaces' 
                        ' returned: %s should have return: 0' % value)
    def variable_x(self):
        return 1.0

if __name__ == '__main__':
    main()

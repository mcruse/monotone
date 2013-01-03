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

import time

from mpx.service.time import Time

class TestCase(DefaultTestFixture):
    def test_Time(self):
        t = time.time()
        t2 = Time().get()
        upper_limit = t + .05
        lower_limit = t - .05
        # Getting 2 different times so as long as we are close!
        self.failUnless(t2 < upper_limit and t2 > lower_limit, 'Time did not match' + 
        ' time.time()=' + str(t) + ' and Time().get()=' + str(t2) )
    
    def test_for_UTC_child(self):
        t = Time()
        t.configure({'name':'time','parent':None})
        self.failUnless(t.has_child('UTC'),'No UTC child!')
       
    def test_for_local_child(self):
        t = Time()
        t.configure({'name':'time','parent':None})
        self.failUnless(t.has_child('local'),'No local child!')
    
    def test_UTC_year(self):
        self.check_attribute('UTC','year')
    
    def test_local_year(self):
        self.check_attribute('local','year')
    
    def test_UTC_month(self):
        self.check_attribute('UTC','month')
    
    def test_local_month(self):
        self.check_attribute('local','month')
    
    def test_UTC_day(self):
        self.check_attribute('UTC','day')
    
    def test_local_day(self):
        self.check_attribute('local','day')

    def test_UTC_hour(self):
        self.check_attribute('UTC','hour')
    
    def test_local_hour(self):
        self.check_attribute('local','hour')
        
    def test_UTC_minute(self):
        self.check_attribute('UTC','minute')
    
    def test_local_minute(self):
        self.check_attribute('local','minute')
    
    def test_UTC_second(self):
        self.check_attribute('UTC','second')
    
    def test_local_second(self):
        self.check_attribute('local','second')

    def test_UTC_weekday(self):
        self.check_attribute('UTC','second')
    
    def test_local_weekday(self):
        self.check_attribute('local','second')
        
    def test_UTC_milliseconds(self):
        self.check_attribute('UTC','milliseconds')
    
    def test_local_milliseconds(self):
        self.check_attribute('local','milliseconds')
        
    def check_attribute(self,child,attribute):
        t = Time()
        t.configure({'name':'time','parent':None})
        c = t.get_child(child)
        c_value = c.get_child(attribute).get()
        
        if attribute != 'milliseconds':
            attributes = {'year':0,'month':1,
                          'day':2,'hour':3,
                          'weekday':6,'minute':4,
                          'second':5}
        
            if child == 'UTC':
                tuple = time.gmtime()
            elif child == 'local':
                tuple = time.localtime()            
            
            real_value = tuple[attributes[attribute]]
            if c_value != real_value:
                self.fail(child + '  "' + attribute +'" is not correct\n' +
                          child + ' ' + attribute + ' came back as: ' + str(c_value) + '\n' +
                          'Correct value: ' + str(real_value))
        else:
            t = time.time()
            real_value = (t - int(t)) *1000
            if c_value < (real_value +.5) and c_value > (real_value -.5):
                pass
            else:
                self.fail(child + ' "' + attribute +'" is not correct\n' +
                          child + ' ' + attribute + ' came back as: ' + str(c_value) + '\n' +
                          'Correct value: ' + str(real_value))

    
    def test_UTC_children(self):
        children = ['year','month','day','hour','minute','weekday','second','milliseconds']
        t = Time()
        t.configure({'name':'time','parent':None})
        u = t.get_child('UTC')
        for c in children:   
            if c not in u.children_names():
                msg = 'Child "' + str(c) + '" was not found in UTC children ' 
                for x in u.children_names():
                    msg += str(x) + ','
                msg = msg[:-1] + '\n'
                msg = msg + 'Child "' + str(c) + '" should be an inherent child of UTC' 
                self.fail(msg)
        if len(children) != len(u.children_names()):
            msg = 'UTC has a different amount of inherent children then I know about!\n'
            msg += 'I think it should have only:\n'
            for c in children:
                msg += c + '\n'
            msg += '\nUTC has Children:\n'
            for c in u.children_names():
                msg += c + '\n'
            self.fail(msg)
            
    def test_local_children(self):
        children = ['year','day','month','hour','minute','weekday','second','milliseconds']
        t = Time()
        t.configure({'name':'time','parent':None})
        l = t.get_child('local')
        for c in children:   
            if c not in l.children_names():
                msg = 'Child "' + str(c) + '" was not found in Local children ' 
                for x in l.children_names():
                    msg += str(x) + ','
                msg = msg[:-1] + '\n'
                msg = msg + 'Child "' + str(c) + '" should be an inherent child of Local' 
                self.fail(msg)      
                
        if len(children) != len(l.children_names()):
            msg = 'Local has a different amount of inherent children then I know about!\n'
            msg += 'I think it should have only:\n'
            for c in children:
                msg += c + '\n'
            msg += '\nLocal has Children:\n'
            for c in l.children.names():
                msg += c + '\n'
            self.fail(msg)
                
        
if(__name__ == '__main__'):    
    main()

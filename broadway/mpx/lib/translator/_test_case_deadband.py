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

from deadband import SimpleDeadband

class Cycle:
    def __init__(self, cycle=None):
        self.name = '/'
        self.parent = None
        if cycle is None:
            cycle = range(0,20)
            cycle.extend(range(20,0,-1))
        self.cycle = cycle
        self.current = []
        self.current.extend(self.cycle)
    def get(self, skipCache=0):
        if not self.current:
            self.current = []
            self.current.extend(self.cycle)
        return self.current.pop(0)
    def _add_child(*args):
        pass
class TestCase(DefaultTestFixture):
    VERBOSE = 0
    def output(self, fmt, *args):
        if self.VERBOSE:
            print fmt % args
    def test_SimpleDeadband(self):
        db = SimpleDeadband()
    def test_SimpleDeadband_config(self):
        db = SimpleDeadband()
        db.configure({'parent':Cycle(), 'name':'test',
                      'activation':14.0, 'deactivation':7.0})
        return db
    def test_SimpleDeadband_cycle(self):
        db = self.test_SimpleDeadband_config()
        db.start()
        for i in range(0,100):
            value = db.ion.get()
            result = db.evaluate(value)
            self.output("A: %s, D: %s, I: %s, O: %s",
                        db.activation, db.deactivation,value, result)
        return
    def test_SimpleDeadband_threshhold(self):
        db = self.test_SimpleDeadband_config()
        db.start()
        value = db.threshold()
        self.output("threshhold: %s", value)
        db.threshold(9.0)
        value = db.threshold()
        self.output("threshhold: %s", value)
        return
    def test_SimpleDeadband_deadband(self):
        db = self.test_SimpleDeadband_config()
        db.start()
        value = db.deadband()
        self.output("deadband: %s", value)
        db.deadband(1.0)
        value = db.deadband()
        self.output("deadband: %s", value)
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    TestCase.VERBOSE = 1
    main()

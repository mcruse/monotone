"""
Copyright (C) 2002 2004 2010 2011 Cisco Systems

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
# Test cases to exercise the PeriodicAverageColumn class.

from mpx_test import DefaultTestFixture, main

import random

from mpx.lib.node import CompositeNode
from mpx.service.logger.periodic_log import PeriodicLog
from mpx.service.logger.periodic_average_column import PeriodicAverageColumn
from mpx.lib.exceptions import EConfigurationIncomplete

class TestCase(DefaultTestFixture):
    class Seq:
        def __init__(self):
            self.value = 0
        def next(self):
            v = self.value
            self.value += 1
            return v

    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.seq = self.Seq()
        return
    def tearDown(self):
        try:
            if hasattr(self, 'seq'):
                del self.seq
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def _random(self):
        return random.uniform(0,100)
    def _next(self):
        return self.seq.next()
    def test_configure_random(self):
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':1})
        h = CompositeNode()
        h.configure({'name':'columns','parent':p})
        c = PeriodicAverageColumn()
        c.configure({'position':0, 'name':'0', 'parent':h,
                     'function':self._random, 'args':()})
        p.start()
        try:
            for i in range(0,1000):
                c.function()
        finally:
            p.stop()
        return
    def test_configure_context_random(self):
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':1})
        h = CompositeNode()
        h.configure({'name':'columns','parent':p})
        c = PeriodicAverageColumn()
        c.configure({'position':0, 'name':'1', 'parent':h,
                     'context':'import random', 'function':'random.uniform',
                     'args':'(0,100)'})
        p.start()
        try:
            for i in range(0,1000):
                c.function()
        finally:
            p.stop()
        return
    def test_configure_sequence(self):
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':1})
        h = CompositeNode()
        h.configure({'name':'columns','parent':p})
        c = PeriodicAverageColumn()
        c.configure({'position':0, 'name':'2', 'parent':h,
                     'function':self._next})
        p.start()
        try:
            l = []
            v = []
            for i in range(0,100):
                l.append(c._evaluate())
                v.append(i-0.5)
            if l.pop(0) != None:
                raise 'First delta not None.'
            v.pop(0)
            for i in l:
                j = v.pop(0)
                if i != j:
                    raise 'Incorrect average of %s should be %s.' % (i, j)
        finally:
            p.stop()
        return

# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

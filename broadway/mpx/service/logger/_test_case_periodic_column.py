"""
Copyright (C) 2001 2002 2003 2006 2010 2011 Cisco Systems

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
# Test cases to exercise the PeriodicColumn class.

from mpx_test import DefaultTestFixture, main

import random

from mpx.lib.node import CompositeNode

from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.service.logger.periodic_log import PeriodicLog

class TestCase(DefaultTestFixture):
    def _random(self):
        return random.uniform(0,100)     
    def test_configure_1(self):
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':1})
        h = CompositeNode()
        h.configure({'name':'columnholder','parent':p})
        c = PeriodicColumn()
        c.configure({'position':0, 'name':'0', 'parent':h,
                     'function':self._random, 'args':()})
        c.start()
        try:
            c.function()
        finally:
            c.stop()
        return
    def test_configure_2(self):
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':1})
        h = CompositeNode()
        h.configure({'name':'columnholder','parent':p})
        c = PeriodicColumn()
        c.configure({'position':1, 'name':'1', 'parent':h,
                     'context':'import random', 'function':'random.uniform',
                     'args':'(0,100)'})
        c.start()
        try:
            c.function()
        finally:
            c.stop()
        return
    def test_configure_3(self):
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':1})
        h = CompositeNode()
        h.configure({'name':'columnholder','parent':p})
        c = PeriodicColumn()
        c.configure({'position':2, 'name':'2', 'parent':h,
                     'context':'',
                     'function':'mpx.lib.node.as_node("/").configuration',
                     'args':'()','conversion':'none'})
        c.start()
        try:
            c.function()
        finally:
            c.stop()
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

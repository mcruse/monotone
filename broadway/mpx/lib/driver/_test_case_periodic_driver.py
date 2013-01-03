"""
Copyright (C) 2010 2011 Cisco Systems

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

from mpx.lib import pause
from mpx.lib.node import as_internal_node
from mpx.lib.node import CompositeNode
from mpx.lib.node import Alias
from mpx.lib.node import Aliases
from mpx.lib.node.simple_value import SimpleValue

from __init__ import PeriodicDriver

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.root = as_internal_node('/')
        self.input = CompositeNode()
        self.output = CompositeNode()
        self.input.configure({'parent':self.root, 'name':'input'})
        self.output.configure({'parent':self.root, 'name':'output'})
        self.input_value = SimpleValue()
        self.output_value = SimpleValue()
        self.input_value.configure({'parent':self.input, 'name':'value'})
        self.output_value.configure({'parent':self.output, 'name':'value'})
        self.aliases = Aliases()
        self.aliases.configure({'parent':self.root, 'name':'aliases'})
        self.alias_input = Alias()
        self.alias_input.configure({'parent':self.aliases, 'name':'input',
                                    'node_url':'/input/value'})
        self.alias_output = Alias()
        self.alias_output.configure({'parent':self.aliases, 'name':'output',
                                    'node_url':'/output/value'})
        self.input_value.set(1)
        self.output_value.set(0)
        return
    def tearDown(self):
        try:
            self.root.prune()
            self.root = None
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_simple_case(self):
        driver = PeriodicDriver()
        driver.configure({'name':'driver','parent':self.output_value,
                          'input':self.input_value})
        self.assert_(self.output_value.get() == 0,
                     "Output already non-zero, bogus test...")
        driver.start()
        timeout_at = time.time() + 1.0
        while self.output_value.get() == 0:
            if time.time() > timeout_at:
                self.fail("self.output_value never driven to 1.")
            pause(0.01)
        return
    def test_alias_input(self):
        driver = PeriodicDriver()
        driver.configure({'name':'driver','parent':self.output_value,
                          'input':self.alias_input})
        self.assert_(self.output_value.get() == 0,
                     "Output already non-zero, bogus test...")
        driver.start()
        timeout_at = time.time() + 1.0
        while self.output_value.get() == 0:
            if time.time() > timeout_at:
                self.fail("self.output_value never driven to 1.")
            pause(0.01)
        return
    def test_alias_output(self):
        driver = PeriodicDriver()
        driver.configure({'name':'driver','parent':self.output,
                          'input':self.input_value, 'output':self.alias_output,
                          })
        self.assert_(self.output_value.get() == 0,
                     "Output already non-zero, bogus test...")
        driver.start()
        timeout_at = time.time() + 1.0
        while self.output_value.get() == 0:
            if time.time() > timeout_at:
                self.fail("self.output_value never driven to 1.")
            pause(0.01)
        return
    def test_deferred_input(self):
        driver = PeriodicDriver()
        driver.configure({'name':'driver','parent':self.output_value,
                          'input':'/aliases/deferred_input',
                          'period':0.01})
        self.assert_(self.output_value.get() == 0,
                     "Output already non-zero, bogus test...")
        driver.start()
        pause(0.1)
        Alias().configure({'parent':self.aliases, 'name':'deferred_input',
                           'node_url':'/input/value'})
        timeout_at = time.time() + 1.0
        while self.output_value.get() == 0:
            if time.time() > timeout_at:
                self.fail("self.output_value never driven to 1.")
            pause(0.01)
        return

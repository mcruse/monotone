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
from mpx_test import DefaultTestFixture

from mpx.lib.node import CompositeNode
from mpx.lib.node import NodeDecorator

class NoPrefix(NodeDecorator):
    pass

class NoUnderbarPrefix(NodeDecorator):
    _PREFIX = 'nounderbar'

class ValidPrefix(NodeDecorator):
    _PREFIX = 'test_'

class UnsuspectingParentNode(CompositeNode):
    pass

class InvalidAttributeDecorator(NodeDecorator):
    _PREFIX = 'ia_'
    def test_configure(self):
        self.set_attribute('wrongattr_one', 1, {}, int)
        return

class AttributeDecorator(NodeDecorator):
    _PREFIX = 'attr_'
    VALID_CD = {'attr_one': 1, 'attr_two': 2}
    def test_configure(self):
        self.set_attribute('attr_one', 1, {}, int)
        self.set_attribute('attr_two', self.REQUIRED, {'attr_two':2}, int)
        return
    def configuration(self, cd):
        self.get_attribute('attr_one', cd, int)
        self.get_attribute('attr_two', cd, int)
        return cd

class TestCase(DefaultTestFixture):
    def __init__(self, *args, **kw):
        DefaultTestFixture.__init__(self, *args, **kw)
        self.assertions_enabled = 0
        try:
            assert False
        except AssertionError:
            self.assertions_enabled = 1
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.unsuspecting_parent_node = UnsuspectingParentNode()
        return
    def tearDown(self):
        try:
            pass
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_no_prefix(self):
        if self.assertions_enabled:
            try:
                NoPrefix()
            except AssertionError:
                # We should get an assertion.
                return
            else:
                self.fail("Did not get expected no _PREFIX assertion.")
        return
    def test_no_underbar_prefix(self):
        if self.assertions_enabled:
            try:
                NoUnderbarPrefix()
                pass
            except AssertionError:
                # We should get an assertion.
                return
            else:
                self.fail("Did not get expected _PREFIX missing underbar"
                          " assertion.")
        return
    def test_valid_prefix(self):
        ValidPrefix()
        return
    def test_invalid_attr(self):
        ia = InvalidAttributeDecorator()
        if self.assertions_enabled:
            try:
                ia.test_configure()
                pass
            except AssertionError:
                # We should get an assertion.
                return
            else:
                self.fail("Did not get expected attributes must start with"
                          " 'ia_' assertion.")
        return
    def test_valid_attr(self):
        a = AttributeDecorator()
        a.configure({'parent':self.unsuspecting_parent_node,
                     'name':'test_valid_attr'})
        a.test_configure()
        cd = {}
        a.configuration(cd)
        self.failIf(cd != AttributeDecorator.VALID_CD,
                    "Unexpected configuration(): %r" % cd)
        for key, value in cd.items():
            self.failIf(not hasattr(self.unsuspecting_parent_node, key),
                        "Parent missing %r attribute." % key)
            self.failIf(getattr(self.unsuspecting_parent_node, key) != value,
                        "Parent has incorrect %r value.  Expected %r, got %r"
                        % (key, value,
                           getattr(self.unsuspecting_parent_node, key)))
        return

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
from mpx_test import main

def function_asserts():
    assert 0, "function_asserts asserted."
    return

def function_does_not_assert():
    assert 1, "function_does_not_assert asserted."
    return

class TestCase(DefaultTestFixture):
    klass_one_int = 1
    klass_two_str = '2'
    klass_three_text = 'three'
    def method_one_int(self):
        return self.klass_one_int
    def method_two_str(self):
        return self.klass_two_str
    def method_three_text(self):
        return self.klass_three_text
    def method_asserts(self):
        assert 0, "method_asserts asserted."
        return
    def method_does_not_assert(self):
        assert 1, "method_does_not_assert asserted."
        return
    def test_assert_comparison(self):
        self.assert_comparison(
            repr(self.klass_one_int), '==', 'self.method_one_int()'
            )
        self.assert_comparison(
            'self.method_one_int()', '==', '1'
            )
        self.assert_comparison(
            repr(self.klass_two_str), '==', 'self.method_two_str()'
            )
        self.assert_comparison(
            'self.method_two_str()', '==', "'2'"
            )
        self.assert_comparison(
            repr(self.klass_three_text), '==', 'self.method_three_text()'
            )
        self.assert_comparison(
            'self.method_three_text()', '==', "'three'"
            )
        return
    def test_assert_comparison_fails(self):
        try:
            self.assert_comparison(
                repr(self.klass_one_int), '!=', 'self.method_one_int()'
                )
        except AssertionError, e:
            pass
        else:
            self.fail("Failed to raise AssertionError.")
        return
    def test_assert_hasattr(self):
        self.assert_hasattr(self, 'klass_three_text')
        class X:
            def __init__(self):
                self.valid_attribute = 1
        x = X()
        self.assert_hasattr(x, 'valid_attribute')
        try:
            self.assert_hasattr(x, 'invalid_attribute')
        except AssertionError:
            pass
        else:
             self.fail('self.assert_hasattr() of a non-existant attribute'
                       ' failed to raise an AssertionError.')
        return
    def test_should_raise_assertion(self):
        self.should_raise_assertion("assert 0")
        self.should_raise_assertion("self.method_asserts()")
        self.should_raise_assertion("function_asserts()")
        try:
            assert 0
        except:
            try: self.should_raise_assertion("function_does_not_assert()")
            except AssertionError: pass
            else: self.fail(
                'self.should_raise_assertion("function_does_not_assert()")'
                ' did not raise the expected assertion'
            )
            try: self.should_raise_assertion("self.method_does_not_assert()")
            except AssertionError: pass
            else: self.fail(
                'self.should_raise_assertion("self.method_does_not_assert()")'
                ' did not raise the expected assertion'
            )
        return

"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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

from mpx.lib.exceptions import *

# Purpose: Check to see if at least some of the MPX Exceptions have reasonable
#          __str__ and __repr__ implementations.
class TestCase(DefaultTestFixture):
    def _quotify(self, str):
        return '"%s"' % str
    # Test a basic MpxException with a few keywords args
    def test_a(self):
        a = MpxException("Test", foo="bar", bar='foo')
        s = str(a)
        t = repr(a)
        s_exp = "Test"   # @fixme This doesn't seem right, shouldn't the keywords go here too?
        #t_exp = "mpx.lib.exceptions.MpxException('Test', foo='bar', bar='foo')"
        #t_exp = self._quotify(t_exp)
        t_exp = "{'keywords': {'foo': 'bar', 'bar': 'foo'}, 'str': 'Test', '__base__': 'Exception', '__class__': 'mpx.lib.exceptions.MpxException', 'args': ('Test',)}"
        if s != s_exp:
            raise "Str of MpxException doesn't match expected value (%s!=%s)." % (s, s_exp)
        if t != t_exp:
            raise "Repr of MpxException doesn't match expected value (%s!=%s)." % (t, t_exp)

    # Test an EInvalidValue with a text argument
    def test_b(self):
        x = 'BadVal'
        text = 'X is a bad, no, a very bad value'
        a = EInvalidValue('x', x, text)
        s = str(a)
        t = repr(a)
        s_exp = "('x', 'BadVal', '%s')" % text
        #t_exp = "mpx.lib.exceptions.EInvalidValue('x', 'BadVal', '%s')" % text
        #t_exp = self._quotify(t_exp)
        t_exp = "{'keywords': {}, 'str': \"('x', 'BadVal', 'X is a bad, no, a very bad value')\", '__base__': 'Exception', '__class__': 'mpx.lib.exceptions.EInvalidValue', 'args': ('x', 'BadVal', 'X is a bad, no, a very bad value')}"
        if s != s_exp:
            raise "Str of EInvalidValue doesn't match expected value (%s!=%s)." % (s, s_exp)
        if t != t_exp:
            raise "Repr of EInvalidValue doesn't match expected value (%s!=%s)." % (t, t_exp)

    # Test an EInvalidValue without a text argument
    def test_c(self):
        y = 'WeryBadVal'
        a = EInvalidValue('y', y)
        s = str(a)
        t = repr(a)
        s_exp = "('y', 'WeryBadVal')"
        #t_exp = "mpx.lib.exceptions.EInvalidValue('y', 'WeryBadVal')"
        #t_exp = self._quotify(t_exp)
        t_exp = "{'keywords': {}, 'str': \"('y', 'WeryBadVal')\", '__base__': 'Exception', '__class__': 'mpx.lib.exceptions.EInvalidValue', 'args': ('y', 'WeryBadVal')}"
        if s != s_exp:
            raise "Str of EInvalidValue doesn't match expected value (%s!=%s)." % (s, s_exp)
        if t != t_exp:
            raise "Repr of EInvalidValue doesn't match expected value (%s!=%s)." % (t, t_exp)

    # Test case where text parameter of an EInvalidValue exception is a dictionary
    def test_d(self):
        y = 'SuperBadVal'
        d = {'c':'C', 'a':'A', 'b':'B'}
        a = EInvalidValue('y',y,text=d)
        s = str(a)
        t = repr(a)
        s_exp = "('y', 'SuperBadVal', %s)" % d
        #t_exp = "mpx.lib.exceptions.EInvalidValue('y', 'SuperBadVal', %s)" % d
        #t_exp = self._quotify(t_exp)
        t_exp = "{'keywords': {}, 'str': \"('y', 'SuperBadVal', {'a': 'A', 'c': 'C', 'b': 'B'})\", '__base__': 'Exception', '__class__': 'mpx.lib.exceptions.EInvalidValue', 'args': ('y', 'SuperBadVal', {'a': 'A', 'c': 'C', 'b': 'B'})}"
        if s != s_exp:
            raise "Str of EInvalidValue doesn't match expected value (%s!=%s)." % (s, s_exp)
        if t != t_exp:
            raise "Repr of EInvalidValue doesn't match expected value (%s!=%s)." % (t, t_exp)
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()


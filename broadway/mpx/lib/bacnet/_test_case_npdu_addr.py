"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
# Test cases to exercise the npdu.Addr() psuedo class.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib.exceptions import EOverflow
from mpx.lib.bacnet.npdu import Addr

class TestCase(DefaultTestFixture):
    def test_empty(self):
        Addr()
    def test_invalid_types(self):
        for arg, arg_type in ((1, 'integer'), ((1,2,3), 'tuple'), ([1], 'list')):
            try:
                Addr(arg)
            except: # @fixme Detect (i.e. raise) an MpxException.
                continue
            raise 'Failed to detect an invalid %s argument.' % arg_type
    def test_valid_types(self):
        for arg, arg_type in (('1234567890', 'string'),
                              (Addr('1234567890'), 'Addr')):
            try:
                Addr(arg)
            except: # @fixme Detect (i.e. raise) an MpxException.
                raise 'Failed to use a valid %s argument.' % arg_type
    def test_boundaries(self):
        Addr('123456789012345678901234567890')
        Addr('1234567890123456789012345678901')
        try:
            Addr('12345678901234567890123456789012')
            raise 'Failed to detect too long of an address.'
        except EOverflow: # @fixme Detect (i.e. raise) an MpxException.
            pass
        except:
            raise 'Unexpected exception when using too long of an address.'
    def test_repr(self):
        import mpx.lib.bacnet.npdu
        a = Addr('1234')
        r = repr(a)
        b = eval(r)
        # @fixme Add direct support for the comparision operator.
        if a.address != b.address:
            raise 'eval(Repr(a)) failed to generate a reasonable clone.'
    def test_str(self):
        s = "Addr: 74 68 69 73 20 69 73 20 61 20 73 74 72 69 6e 67\n" + \
            "      20 74 65 73 74"
        a = Addr('this is a string test')
        if str(a) != s:
            raise 'An unexpected string was generated.'
    def test_len(self):
        for s in ('', '1', '12345', '1234567890',
                  '12345678901234567890',
                  '123456789012345678901234567890',
                  '1234567890123456789012345678901'):
            a = Addr(s)
            if len(s) != len(a):
                raise 'Incorrect len() calculated.'
    def test_slice(self):
        s = '012345'
        Addr(s)[:]
        Addr(s)[0:]
        Addr(s)[1:]
        Addr(s)[:6]
        Addr(s)[:5]
        Addr(s)[-1000000000000L:]
        Addr(s)[:1000000000000L]
        Addr(s)[-1000000000000L:1000000000000L]
        Addr(s)[1000000000000L:-1000000000000L]
        Addr(s)[0:6]
        Addr(s)[1:-1]
        Addr(s)[-1:1]
    def test_item(self):
        s = '012345'
        for i in range(0,len(s)):
            if s[i] != Addr(s)[i]:
                raise 'Positive index mismatch.'
            if s[-i] != Addr(s)[-i]:
                raise 'Negative index mismatch.'
        try:
            Addr(s)[len(s)]
            raise 'Failed to detect index out of range.'
        except IndexError:
            pass
        except:
            raise 'Wrong exception raised for index out of range.'
    def test_getattr(self):
        s = '1234567890'
        a = Addr(s)
        if len(s) != a.length:
            raise 'Incorrect length attribute value.'
        if s != a.address:
            raise 'Incorrect address arribute value.'
    def test_setattr(self):
        s = '1234567890'
        a = Addr()
        a.address = s
        if len(s) != a.length:
            raise 'Incorrect length attribute value.'
        if s != a.address:
            raise 'Incorrect address arribute value.'
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

"""
Copyright (C) 2003 2005 2010 2011 Cisco Systems

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

from mpx.lib.magnitude import *
from mpx.lib import EnumeratedValue
from mpx.lib.exceptions import ETypeError

int_type = type(1)
long_type = type(1L)
float_type = type(Float(1.0))

def check_type(obj, desired_type):
    cur_type = type(obj)
    assert cur_type is desired_type, (
            "%s is not %s" % (cur_type, desired_type)
            )

class TestCase(DefaultTestFixture):
    def test_from_enum(self):
        m = as_object(EnumeratedValue(1,"one"))
        n = m.as_magnitude()
        check_type(n, int_type)
        return
    def test_from_int(self):
        m = as_object(1)
        n = m.as_magnitude()
        check_type(n, int_type)
        return
    def test_from_long(self):
        m = as_object(1L)
        n = m.as_magnitude()
        check_type(n, long_type)
        return
    def test_from_float(self):
        m = as_object(1.0)
        n = m.as_magnitude()
        check_type(n, float_type)
        return
    def test_from_string_int(self):
        m = as_object("1")
        n = m.as_magnitude()
        check_type(n, int_type)
        return
    def test_from_string_long(self):
        m = as_object("1L")
        n = m.as_magnitude()
        check_type(n, long_type)
        return
    def test_from_string_float(self):
        m = as_object("1.0")
        n = m.as_magnitude()
        check_type(n, float_type)
        return
    def test_from_unicode_int(self):
        m = as_object(u"1")
        n = m.as_magnitude()
        check_type(n, int_type)
        return
    def test_from_unicode_long(self):
        m = as_object(u"1L")
        n = m.as_magnitude()
        check_type(n, long_type)
        return
    def test_from_unicode_float(self):
        m = as_object(u"1.0")
        n = m.as_magnitude()
        check_type(n, float_type)
        return
    def test_to_int(self):
        valid_list = (1, 1L, 1.0,
                      EnumeratedValue(1,"one"),
                      "1", 1L, 1.0)
        for item in valid_list:
            n = int(as_object(item))
            check_type(n, int_type)
        return
    def test_to_long(self):
        valid_list = (1, 1L, 1.0,
                      EnumeratedValue(1,"one"),
                      "1", 1L, 1.0)
        for item in valid_list:
            m = long(as_object(item))
            check_type(m, long_type)
        return
    def test_to_float(self):
        valid_list = (1, 1L, 1.0,
                      # Note: The following case doesn't work because EnumeratedValues return
                      #       a simple integer from as_magnitude rather than a full
                      #       MagnitudeInterface object.
                      #EnumeratedValue(1,"one"), 
                      "1", 1L, 1.0)
        for item in valid_list:
            m = float(as_object(item))
            check_type(m, float_type)
        return
    def test_invalid_types(self):
        bogus_list = (None, "None", (), [], {},)
        for item in bogus_list:
            try:
                m = as_object(item)
            except ETypeError, e:
                pass
            else:
                assert 0, (
                    "Failed to detect an invalid type %s." % type(item)
                    )
        return
    def test_is_magnitude(self):
        bogus_list = (None, "None", (), [], {},)
        valid_list = (1, 1L, 1.0)
        for item in bogus_list:
            assert not is_magnitude(item), (
                "Failed to detect an invalid number %s." % item
                )
        for item in valid_list:
            assert is_magnitude(item), (
                "Rejected a valid number %s." % item
                )
        return
    def test_is_object(self):
        bogus_list = (1, 1L, 1.0, "1.0")
        valid_list = (EnumeratedValue(1,"one"),
                      as_object(1),
                      as_object(1L),
                      as_object(1.0))
        for item in bogus_list:
            assert not is_object(item), (
                "Failed to detect a non-magnitude %s." % item
                )
        for item in valid_list:
            assert is_object(item), (
                "Rejected a valid magnitude %s." % item
                )
        return
    def test_as_magnitude(self):
        bogus_list = (None, "None", (), [], {},)
        valid_list = (1, 1L, 1.0)
        for item in bogus_list:
            try:
                as_magnitude(item)
                assert 0, (
                    "Failed to reject an invalid magnitude %s." % item
                    )
            except ETypeError, e:
                pass
        for item in valid_list:
            try:
                as_magnitude(item)
            except:
                assert 0, (
                    "Failed to accept a valid magnitude %s." % item
                    )
        return
    def test_as_object(self):
        bogus_list = (None, "None", (), [], {},)
        valid_list = (1, 1L, 1.0,
                      "1", "1L", "1.0",
                      EnumeratedValue(1,"one"),
                      as_object(1), as_object(1L), as_object(1.0))
        for item in bogus_list:
            try:
                as_object(item)
                assert 0, (
                    "Failed to reject an invalid magnitude %s." % item
                    )
            except ETypeError, e:
                pass
        for item in valid_list:
            as_magnitude(item)
        return
    # The following are a bunch of tests for fancy_stringer() which isn't
    # really very related to the magnitude stuff.
    def check_str(self, str1, str2):
        assert str1 == str2, "%s and %s are not equal" % (str1, str2)
    #
    def test_stringer_simple_list(self):
        _list = ['a', 'b', 'c']
        exp_str = str(_list)
        ret_str = fancy_stringer(_list)
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_short_list(self):
        _list = ['a']
        exp_str = str(_list)
        ret_str = fancy_stringer(_list)
        self.check_str(ret_str, exp_str)    
    #
    def test_stringer_simple_float_1(self):
        _float = .333333
        exp_str = '0.33'
        ret_str = fancy_stringer(_float, float_format='%.2f')
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_simple_float_2(self):
        _float = .333333
        exp_str = '0.333333'
        ret_str = fancy_stringer(_float)
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_simple_int_1(self):
        _int = 33
        exp_str = '033'
        ret_str = fancy_stringer(_int, int_format='%.3d')
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_simple_int_2(self):
        _int = 333
        exp_str = '333'
        ret_str = fancy_stringer(_int)
        self.check_str(ret_str, exp_str)    
    #
    def test_stringer_float_list(self):
        _list = [.331, .332, .334, .335]
        exp_str = '[0.33, 0.33, 0.33, 0.34]'
        ret_str = fancy_stringer(_list, float_format='%.2f')
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_simple_dict(self):
        _dict = {'a':1, 'b':2, 'c':3}
        exp_str = str(_dict)
        ret_str = fancy_stringer(_dict)
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_short_dict(self):
        _dict = {'a':1}
        exp_str = str(_dict)
        ret_str = fancy_stringer(_dict)
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_float_dict(self):
        _dict = {'a':.331, 'b':.332, 'c':.334, 'd':.335}
        exp_str = "{'a': 0.33, 'c': 0.33, 'b': 0.33, 'd': 0.34}"
        ret_str = fancy_stringer(_dict, float_format='%.2f')
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_simple_tuple(self):
        _list = ('a', 'b', 'c')
        exp_str = str(_list)
        ret_str = fancy_stringer(_list)
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_short_tuple(self):
        _list = ('a',)
        exp_str = str(_list)
        ret_str = fancy_stringer(_list)
        self.check_str(ret_str, exp_str)
    #
    def test_stringer_float_tuple(self):
        _list = (.331, .332, .334, .335)
        exp_str = '(0.33, 0.33, 0.33, 0.34)'
        ret_str = fancy_stringer(_list, float_format='%.2f')
        self.check_str(ret_str, exp_str)    

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

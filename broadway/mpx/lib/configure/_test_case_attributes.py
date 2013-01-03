"""
Copyright (C) 2001 2002 2003 2005 2010 2011 Cisco Systems

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
# Test cases to exercise the _attribute module.
# @todo lots more code to exercise.

from mpx_test import DefaultTestFixture, main

import os
import types

from mpx.lib.exceptions import EConfigurationIncomplete, EInvalidValue
from mpx.lib.configure._attributes import set_attribute, REQUIRED, as_formatted
from mpx.lib.configure._attributes import get_attribute, as_float_formatted
from mpx.lib.configure._attributes import as_int_formatted, as_long_formatted

class Object:
    pass

class TestCase(DefaultTestFixture):
    def test_set_attribute(self):
        object = Object()
        dictionary = {'an_int':'1', 'bad_int':'NFG'}
        # Test setting a simple integer
        set_attribute(object, 'an_int', REQUIRED, dictionary, int)
        if object.an_int != 1:
            raise 'Failed to set a simple integer.'
        # Test updating an attribute.
        set_attribute(object, 'an_int', REQUIRED, {'an_int':2}, int)
        if object.an_int != 2:
            raise 'Failed to update an attribute.'
        # Test detecting that a REQUIRED attribute is set on the object and
        # therefore no longer required in the configuration dictionary.
        set_attribute(object, 'an_int', REQUIRED, {}, int)
        # Test reporting a missing REQUIRED attribute.
        set_attribute(object, 'required', REQUIRED, dictionary)
        if not object._outstanding_attributes:
            raise 'Failed to detect outstanding REQUIRED attribute.'
        # Test reporting a failed conversion as an EInvalidValue.
        try: set_attribute(object, 'bad_int', REQUIRED, dictionary, int)
        except EInvalidValue: pass
        else: raise 'Failed to report failed conversion as an EInvalidValue.'
        # Test setting a default.
        set_attribute(object, 'default', -1, dictionary)
        if object.default != -1:
            raise 'Failed to set a default value.'
        # Test ignoring a default for an existing attribute.
        old_value = object.an_int
        set_attribute(object, 'an_int', old_value+1000, {}, int)
        if old_value != object.an_int:
            raise 'Applied a default value to an existing attribute.'
        # Test not applying a conversion to a default
        set_attribute(object,'missing','1',dictionary,int)
        self.failUnless(object.missing == '1',('May have applied conversion ' + 
                                               'to a default attribute'))
        return

    def test_get_attribute(self):
        _data1 = (('0xDEADBEEF', (long(0xDE) << 24) + 0x00ADBEEF),
                  ('0x0000BEEF',                      0x0000BEEF),
                  ('0x0000BEEF', 48879),
                 )
        _data2 = (('0xDEADBEEF', '0xDEADBEEF'),
                  ('0xDEADBEEF', (long(0xDE) << 24) + 0x00ADBEEF),
                  ('0x0000BEEF', '0x0000BEEF'),
                  ('0x0000BEEF', 0x0000BEEF),
                  ('0x0000BEEF', '48879'),
                  ('0x0000BEEF', 48879),
                 )
        _data3 = (('0x0EADBEEF', '0x0EADBEEF'),
                  ('0x0EADBEEF', (long(0x0E) << 24) + 0x00ADBEEF),
                  ('0x0000BEEF', '0x0000BEEF'),
                  ('0x0000BEEF', 0x0000BEEF),
                  ('0x0000BEEF', '48879'),
                  ('0x0000BEEF', 48879),
                  
                 )
        _data4 = (('3.00', 3, '%.2f'),
                  ('3.00', '3', '%.2f'),
                  ('3.30', '3.3', '%.2f'),
                  ('3.33', '3.33', '%.2f'),
                  ('3.33', '3.333', '%.2f'),
                  ('3.34', '3.336', '%.2f'),
                 )
        #
        object = Object()
        #
        # Test as_formatted
        for x in _data1:
            exp_val,val = x
            dictionary = {}
            object.hexval = val
            get_attribute(object,'hexval',dictionary,as_formatted,'0x%.8X')
            self.failUnless(dictionary['hexval'] == exp_val,
                            "as_long_formatted did not return " \
                            "expected value (%s vs %s)." % (dictionary['hexval'],
                                                            exp_val))
        #
        # Test as_long_formatted
        for x in _data2:
            exp_val,val = x
            dictionary = {}
            object.hexval = val
            get_attribute(object,'hexval',dictionary,as_long_formatted,'0x%.8X')
            self.failUnless(dictionary['hexval'] == exp_val,
                            "as_formatted did not return " \
                            "expected value (%s vs %s)." % (dictionary['hexval'],
                                                            exp_val))
        #
        # Test as_int_formatted
        for x in _data3:
            exp_val,val = x
            dictionary = {}
            object.hexval = val
            get_attribute(object,'hexval',dictionary,as_int_formatted,'0x%.8X')
            self.failUnless(dictionary['hexval'] == exp_val,
                            "as_formatted did not return " \
                            "expected value (%s vs %s)." % (dictionary['hexval'],
                                                            exp_val))
        #    
        # Test as_float_formatted
        for x in _data4:
            exp_val,val,format = x
            dictionary = {}
            object.hexval = val
            get_attribute(object,'hexval',dictionary,as_float_formatted,format)
            #print exp_val,val,dictionary
            self.failUnless(dictionary['hexval'] == exp_val,
                            "as_formatted did not return " \
                            "expected value (%s vs %s)." % (dictionary['hexval'],
                                                            exp_val))
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

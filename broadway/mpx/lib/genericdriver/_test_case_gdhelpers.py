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
import os
import sys
import struct

import gdhelpers as gd
import gdutil as util

from mpx_test import DefaultTestFixture, main

class MockNode:
    def __init__(self):
        self.value = None
        self.last_read_time = None
    #
    def _setValue(self, new_value):
        self.value = new_value
        self.last_read_time = util.get_time()

class TestCase(DefaultTestFixture): 
    def test_base_item(self):

        # Test base item with all default values.
        x = gd.BaseItem()

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() is None, "getWidth should be None"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() is None, "packSpec should be None"
        assert x.getType() is None, "getType should be None"
        assert x.getName() is None, "getName should be None"
        assert x._getValue('\33', 0) is None, "_getValue should be None"

        # Test base item with all default values except for name.
        x = gd.BaseItem(name='TestName')
        
        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() is None, "getWidth should be None"
        assert x.packSpec() is None, "packSpec should be None"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == "TestName", "getName should be TestName"
        assert x._getValue('\33', 0) is None, "_getValue should be None"

        # Test base item with a few parameters set to 1, plus
        # packspec of <B. 
        x = gd.BaseItem(ispack=1, width=1, packspec='<B')
        
        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '<B', "packSpec should be <B"
        assert x.getType() is None, "getType should be None"
        assert x.getName() is None, "getName should be None"
        retvalue = x._getValue(chr(0x33), 0)
        # Note: Even though everything else is in order, because isFixedWidth is 0,
        #       base item can't interpret the value.
        assert retvalue == None, "_getValue should be None not %s" % str(retvalue)

        # Test base item with a few parameters set to 1, plus
        # packspec of <B. 
        x = gd.BaseItem(ispack=1, width=1, packspec='<B', isfixedwidth=1)
        
        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '<B', "packSpec should be <B"
        assert x.getType() is None, "getType should be None"
        assert x.getName() is None, "getName should be None"
        retvalue = x._getValue(chr(0x33), 0)
        assert retvalue == 0x33, "_getValue should be 0x33 not %s" % str(retvalue)
        
        # Test base item with width set to 0, plus packspec of <b.
        x = gd.BaseItem(ispack=1, width=0, packspec='<b')
        
        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 0, "getWidth should be 0"
        assert x.packSpec() == '<b', "packSpec should be <b"
        assert x.getType() is None, "getType should be None"
        assert x.getName() is None, "getName should be None"
        #retvalue = x._getValue(chr(0x33), 0)
        #assert retvalue == 0x33, "_getValue should be 0x33 not %s" % str(retvalue)

        # Test base item with all parameters set to None.
        x = gd.BaseItem(name=None, type=None, width=None, value=None, packspec=None, ispack=None)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == None, "getWidth should be None"
        assert x.packSpec() == None, "packSpec should be None"
        assert x.getType() is None, "getType should be None"
        assert x.getName() is None, "getName should be None"
        #retvalue = x._getValue(chr(0x33), 0)
        #assert retvalue == 0x33, "_getValue should be 0x33 not %s" % str(retvalue)

        # Test base item type of int8 and width of 10.        
        x = gd.BaseItem(type='int8', width=10, value=100)
        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 10, "getWidth should be 10"
        assert x.packSpec() == None, "packSpec should be None"
        assert x.getType() is 'int8', "getType should be int8"
        assert x.getName() is None, "getName should be None"
        #retvalue = x._getValue(chr(0x33), 0)
        #assert retvalue == 0x33, "_getValue should be 0x33 not %s" % str(retvalue)

        x = gd.BaseItem(name='TestName', isfixedwidth=1, width=1)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == None, "packSpec should be None"
        assert x.getType() is None, "getType should be None"
        assert x.getName() is 'TestName', "getName should be TestName"
        #retvalue = x._getValue(chr(0x33), 0)
        #assert retvalue == 0x33, "_getValue should be 0x33 not %s" % str(retvalue)

        # Notes: Parameters are name, type, width, value, packspec and ispack
        # @fixme: Add tests for isEnoughData(), setValue(), dumpStr().
          
    def test_case_int_objects(self):

        #
        ##
        ###   8 - B I T   I N T   V A L U E S
        ##
        #

        # 
        ## Test signed 8-bit int (aka, int8) with high bit unset.               
        #
        x = gd.IntItem(name='int8', width=1, packspec='<b', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() == '<b', "packSpec should be <b"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int8', "getName should be int8"
        retvalue = x._getValue(chr(0x23), 0)
        assert retvalue == 0x23, "_getValue should be 0x23 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(33)
        buffer = x.dumpStr()
        expbuffer = chr(33)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 33, "retval should be 33, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0x33), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x33, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x33, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x33, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x33, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x34), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x34, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x34, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x34, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x34, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x35), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0x35, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x35, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x35, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0x35, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xA0)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xA0) + chr(0xA1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"

        #
        ## Test signed 8-bit int (aka, int8) with high bit set.               
        #
        x = gd.IntItem(name='int8', width=1, packspec='<b', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '<b', "packSpec should be <b"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int8', "getName should be int8"
        retvalue = x._getValue(chr(0xF3), 0)
        assert retvalue == -13, "_getValue should be -13 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(-13)
        buffer = x.dumpStr()
        expbuffer = chr(0xF3)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == -13, "retval should be -13, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0xF0), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xF0, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF0, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF0, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xF0, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xF1), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xF1, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF1, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF1, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xF1, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xF2), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0xF2, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF2, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF2, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0xF2, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 1 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xB0)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xB0) + chr(0xB1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"

        #
        ## Test big endian signed 8-bit int (aka, beint8) with high bit unset.                  
        #
        x = gd.IntItem(name='beint8', width=1, packspec='>b', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '>b', "packSpec should be >b"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint8', "getName should be beint8"
        retvalue = x._getValue(chr(0x69), 0)
        assert retvalue == 0x69, "_getValue should be 0x69 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(42)
        buffer = x.dumpStr()
        expbuffer = chr(42)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 42, "retval should be 42, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0x70), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x70, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x70, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x70, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x70, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x71), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x71, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x71, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x71, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x71, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x72), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0x72, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x72, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x72, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0x72, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xC0)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xC0) + chr(0xC1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"


        #
        ## Test big endian signed 8-bit int (aka, beint8) with high bit set.                 
        #
        x = gd.IntItem(name='beint8', width=1, packspec='>b', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '>b', "packSpec should be >b"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint8', "getName should be beint8"
        retvalue = x._getValue(chr(0xF4), 0)
        assert retvalue == -12, "_getValue should be -12 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(-12)
        buffer = x.dumpStr()
        expbuffer = chr(0xF4)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == -12, "retval should be -12, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0xF5), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xF5, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF5, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF5, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xF5, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xF6), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xF6, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF6, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF6, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xF6, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xF7), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0xF7, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF7, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF7, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0xF7, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xD0)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xD0) + chr(0xD1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"


        #
        ## Test unsigned 8-bit int (aka, uint8) with high bit unset.                 
        #
        x = gd.IntItem(name='uint8', width=1, packspec='<B', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '<B', "packSpec should be <B"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint8', "getName should be uint8"
        retvalue = x._getValue(chr(0x13), 0)
        assert retvalue == 0x13, "_getValue should be 0x13 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(69)
        buffer = x.dumpStr()
        expbuffer = chr(69)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 69, "retval should be 69, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0x14), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x14, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x14, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x14, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x14, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x15), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x15, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x15, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x15, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x15, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x16), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0x16, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x16, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x16, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0x16, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xE0)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xE0) + chr(0xE1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"

        #
        ## Test unsigned 8-bit int (aka, uint8) with high bit set.                
        #
        x = gd.IntItem(name='uint8', width=1, packspec='<B', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '<B', "packSpec should be <B"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint8', "getName should be uint8"
        retvalue = x._getValue(chr(0xFC), 0)
        assert retvalue == 0xFC, "_getValue should be 0xFC not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(17)
        buffer = x.dumpStr()
        expbuffer = chr(17)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 17, "retval should be 17, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0xFD), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xFD, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xFD, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xFD, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xFD, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xFE), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xFE, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xFE, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xFE, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xFE, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xFF), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0xFF, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xFF, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xFF, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0xFF, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xF0)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xF0) + chr(0xF1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"


        #
        ## Test big endian unsigned 8-bit int (aka, beuint8) with high bit unset.                 
        #
        x = gd.IntItem(name='beuint8', width=1, packspec='>B', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '>B', "packSpec should be >B"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint8', "getName should be beuint8"
        retvalue = x._getValue(chr(0x56), 0)
        assert retvalue == 0x56, "_getValue should be 0x56 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(39)
        buffer = x.dumpStr()
        expbuffer = chr(39)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 39, "retval should be 39, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0x57), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x57, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x57, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x57, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x57, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x58), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0x58, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x58, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x58, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0x58, 0 should be 1"

        ismatchobj = x.isMatch(chr(0x59), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0x59, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0x59, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0x59, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0x59, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x0A)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x0A) + chr(0x0B)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"


        #
        ## Test big endian unsigned 8-bit int (aka, beuint8) with high bit set.                  
        #
        x = gd.IntItem(name='beuint8', width=1, packspec='>B', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '>B', "packSpec should be >B"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint8', "getName should be beuint8"
        retvalue = x._getValue(chr(0xF0), 0)
        assert retvalue == 0xF0, "_getValue should be 0xF0 not %s" % str(retvalue)

        # Test setValue() and dumpStr().
        x.setValue(58)
        buffer = x.dumpStr()
        expbuffer = chr(58)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 58, "retval should be 58, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        ismatchobj = x.isMatch(chr(0xF1), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xF1, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF1, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF1, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xF1, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xF2), 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of 0xF2, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF2, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF2, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed() of 0xF2, 0 should be 1"

        ismatchobj = x.isMatch(chr(0xF3), 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of 0xF3, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of 0xF3, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of 0xF3, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of 0xF3, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Now do a similar test with an initial value.
        x = gd.IntItem(name='int8', width=1, packspec='<b', ispack=1, value=0x33)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 1, "getWidth should be 1"
        assert x.packSpec() == '<b', "packSpec should be <b"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int8', "getName should be int8"
        retvalue = x._getValue(chr(0x33), 0)
        assert retvalue == 0x33, "_getValue should be 0x33 not %s" % str(retvalue)

        assert x.isMatch(chr(0x34), 0).isNotMatch() == 1, "isNotMatch of 0x34, 0 should be 1"
        assert x.isMatch(chr(0x33), 0).isMatch() ==  1, "isMatch of 0x33, 0 should be 1"
        assert x.isMatch(chr(0x33), 1).isMatch() ==  0, "isMatch of 0x33, 1 should be 0"
        assert x.isMatch(chr(0x33)*3, 0).isMatch() ==  1, "isMatch of 0x33*3, 0 should be 1"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        testbuff = chr(0x32) + chr(0x33) + chr(0x34)
        assert x.isMatch(testbuff, 0).isNotMatch() == 1, "isNotMatch of testbuff, 0 should be 1"
        assert x.isMatch(testbuff, 0).isMatch() == 0, "isMatch of testbuff, 0 should be 0"
        assert x.isMatch(testbuff, 0).isPotentialMatch() == 0, "isPotentialMatch of testbuff, 0 should be 0"
        assert x.isMatch(testbuff, 1).isMatch() ==  1, "isMatch of testbuff, 1 should be 1"
        assert x.isMatch(testbuff, 1).isNotMatch() == 0, "isNotMatch of testbuff, 1, should be 0"
        assert x.isMatch(testbuff, 1).isPotentialMatch() == 1, "isPotentialMatch of testbuff, 1, should be 1"
        assert x.isMatch(testbuff, 2).isNotMatch() == 1, "isNotMatch of testbuff, 2 should be 1"
        assert x.isMatch(testbuff, 2).isMatch() == 0, "isMatch of testbuff, 2 should be 0"
        assert x.isMatch(testbuff, 2).isPotentialMatch() == 0, "isPotentialMatch of testbuff, 2 should be 0"
        assert x.isMatch(testbuff, 3).isMatch() ==  0, "isMatch of testbuff, 3 should be 0"
        assert x.isMatch(testbuff, 3).isNotMatch() ==  0, "isNotMatch of testbuff, 3 should be 0"
     
        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x0B)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x0B) + chr(0x0C)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 1, "_isEnoughData(0) should be 1"

        #
        ##
        ###   1 6 - B I T   I N T   V A L U E S
        ##
        #

        # 
        ## Test signed 16-bit int (aka, int16) with high bit unset.                
        #
        x = gd.IntItem(name='int16', width=2, packspec='<h', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '<h', "packSpec should be <h"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int16', "getName should be int16"
        buffer = chr(0x01) + chr(0x02)
        expval = 0x0201
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x0102)
        buffer = x.dumpStr()
        expbuffer = chr(0x02) + chr(0x01)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x0102, "retval should be 0x0102, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x03) + chr(0x04)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x05) + chr(0x06)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x07) + chr(0x08)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Now do a similar test with an initial value.
        x = gd.IntItem(name='int16', width=2, packspec='<h', ispack=1, value=0x3433)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '<h', "packSpec should be <h"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int16', "getName should be int16"
        buffer1 = chr(0x33) + chr(0x34)
        buffer2 = chr(0x34) + chr(0x35)
        buffer3 = chr(0x33) + chr(0x34) + chr(0x35)
        retvalue = x._getValue(buffer1, 0)
        expval1 = 0x3433
        assert retvalue == expval1, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of 0x3435, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of 0x3334, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of 0x3334, 1 should be 0"
        assert x.isMatch(buffer3, 0).isMatch() ==  1, "isMatch of 0x333435, 0 should be 1"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        testbuff = chr(0x32) + chr(0x33) + chr(0x34)
        assert x.isMatch(testbuff, 0).isNotMatch() == 1, "isNotMatch of testbuff, 0 should be 1"
        assert x.isMatch(testbuff, 0).isMatch() == 0, "isMatch of testbuff, 0 should be 0"
        assert x.isMatch(testbuff, 0).isPotentialMatch() == 0, "isPotentialMatch of testbuff, 0 should be 0"
        assert x.isMatch(testbuff, 1).isMatch() ==  1, "isMatch of testbuff, 1 should be 1"
        assert x.isMatch(testbuff, 1).isNotMatch() == 0, "isNotMatch of testbuff, 1, should be 0"
        assert x.isMatch(testbuff, 1).isPotentialMatch() == 1, "isPotentialMatch of testbuff, 1, should be 1"
        assert x.isMatch(testbuff, 2).isMatch() == 0, "isMatch of testbuff, 2 should be 0"
        assert x.isMatch(testbuff, 2).isNotMatch() == 0, "isNotMatch of testbuff, 2 should be 0"
        assert x.isMatch(testbuff, 2).isPotentialMatch() == 1, "isPotentialMatch of testbuff, 2 should be 1"
        assert x.isMatch(testbuff, 3).isMatch() ==  0, "isMatch of testbuff, 3 should be 0"
        assert x.isMatch(testbuff, 3).isNotMatch() ==  0, "isNotMatch of testbuff, 3 should be 0"
        assert x.isMatch(testbuff, 3).isPotentialMatch() == 1, "isPotentialMatch of testbuff, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xA0) + chr(0xA1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xA0) + chr(0xA1) + chr(0xA2) + chr(0xA3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s" % str(retval)


        # 
        ## Test signed 16-bit int (aka, int16) with high bit set.               
        #
        x = gd.IntItem(name='int16', width=2, packspec='<h', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '<h', "packSpec should be <h"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int16', "getName should be int16"
        buffer = chr(0xF0) + chr(0xF1)
        expval = -3600
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))
        # Test setValue() and dumpStr().
        x.setValue(-3600)
        buffer = x.dumpStr()
        expbuffer = chr(0xF0) + chr(0xF1)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == -3600, "retval should be -3600, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF2) + chr(0xF3)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xF4) + chr(0xF5)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xF6) + chr(0xF7)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xB0) + chr(0xB1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xB0) + chr(0xB1) + chr(0xB2) + chr(0xB3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s" % str(retval)

        # 
        ## Test big endian signed 16-bit int (aka, beint16) with high bit unset.                 
        #
        x = gd.IntItem(name='beint16', width=2, packspec='>h', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '>h', "packSpec should be >h"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint16', "getName should be beint16"
        buffer = chr(0x55) + chr(0x56)
        expval = 0x5556
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x5556)
        buffer = x.dumpStr()
        expbuffer = chr(0x55) + chr(0x56)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x5556, "retval should be 0x5556, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x57) + chr(0x58)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x59) + chr(0x60)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x61) + chr(0x62)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xC0) + chr(0xC1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s." % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xC0) + chr(0xC1) + chr(0xC2) + chr(0xC3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s." % str(retval)

        # 
        ## Test big endian signed 16-bit int (aka, beint16) with high bit set.                 
        #
        x = gd.IntItem(name='beint16', width=2, packspec='>h', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '>h', "packSpec should be >h"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint16', "getName should be beint16"
        buffer = chr(0xF0) + chr(0x42)
        expval = -4030
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(-4030)
        buffer = x.dumpStr()
        expbuffer = chr(0xF0) + chr(0x42)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == -4030, "retval should be -4030, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF1) + chr(0x43)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xF2) + chr(0x44)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xF3) + chr(0x45)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xD0) + chr(0xD1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s." % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xD0) + chr(0xD1) + chr(0xD2) + chr(0xD3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2, not %s." % str(retval)

        # 
        ## Test unsigned 16-bit int (aka, uint16) with high bit unset.                
        #
        x = gd.IntItem(name='uint16', width=2, packspec='<H', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '<H', "packSpec should be <H"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint16', "getName should be uint16"
        buffer = chr(0x91) + chr(0x92)
        expval = 0x9291
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x9192)
        buffer = x.dumpStr()
        expbuffer = chr(0x92) + chr(0x91)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x9192, "retval should be 0x9192, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x93) + chr(0x94)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x95) + chr(0x96)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x97) + chr(0x98)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xE0) + chr(0xE1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xE0) + chr(0xE1) + chr(0xE2) + chr(0xE3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"

        # 
        ## Test unsigned 16-bit int (aka, uint16) with high bit set.                  
        #
        x = gd.IntItem(name='uint16', width=2, packspec='<H', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '<H', "packSpec should be <H"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint16', "getName should be uint16"
        buffer = chr(0xF0) + chr(0xAA)
        expval = 0xAAF0
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x2342)
        buffer = x.dumpStr()
        expbuffer = chr(0x42) + chr(0x23)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x2342, "retval should be 0x2342, got %s instead." % str(retval)



        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF1) + chr(0xAB)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xF2) + chr(0xAC)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xF3) + chr(0xAD)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xF0) + chr(0xF1)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"

        # 
        ## Test big endian unsigned 16-bit int (aka, beuint16) with high bit unset.                   
        #
        x = gd.IntItem(name='beuint16', width=2, packspec='>H', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '>H', "packSpec should be >H"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint16', "getName should be beuint16"
        buffer = chr(0x0A) + chr(0x80)
        expval = 0x0A80
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x1970)
        buffer = x.dumpStr()
        expbuffer = chr(0x19) + chr(0x70)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x1970, "retval should be 0x1970, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x0B) + chr(0x81)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x0C) + chr(0x82)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0x0D) + chr(0x83)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x5C) + chr(0x5D)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x5C) + chr(0x5D) + chr(0x5E) + chr(0x5F)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"

        # 
        ## Test big endian unsigned 16-bit int (aka, beuint16) with high bit set.                 
        #
        x = gd.IntItem(name='beuint16', width=2, packspec='>H', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 2, "getWidth should be 2"
        assert x.packSpec() == '>H', "packSpec should be >H"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint16', "getName should be beuint16"
        buffer = chr(0xFA) + chr(0xD0)
        expval = 0xFAD0
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x2000)
        buffer = x.dumpStr()
        expbuffer = chr(0x20) + chr(0x00)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x2000, "retval should be 0x2000, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xFB) + chr(0xD1)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xFC) + chr(0xD2)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed() of buffer, 0 should be 2"

        buffer = chr(0xFD) + chr(0xD3)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x6C) + chr(0x6D)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x6C) + chr(0x6D) + chr(0x6E) + chr(0x6F)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 2, "_isEnoughData(0) should be 2"

        #
        ##
        ###   3 2 - B I T   I N T   V A L U E S
        ##
        #

        # 
        ## Test signed 32-bit int (aka, int32) with high bit unset.               
        #
        x = gd.IntItem(name='int32', width=4, packspec='<l', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '<l', "packSpec should be <l"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int32', "getName should be int32"
        buffer = chr(0x07) + chr(0x08) + chr(0x09) + chr(0x10)
        expval = 0x10090807 
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))


        # Test setValue() and dumpStr().
        x.setValue(0x07080910)
        buffer = x.dumpStr()
        expbuffer = chr(0x10) + chr(0x09) + chr(0x08) + chr(0x07)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x07080910, "retval should be 0x07080910, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x11) + chr(0x12) + chr(0x13) + chr(0x14)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0x15) + chr(0x16) + chr(0x17) + chr(0x18)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xA0) + chr(0xAB) + chr(0xAC) + chr(0xAD)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x03) + chr(0x04) + chr(0x05) + chr(0x06)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x07) + chr(0x08) + chr(0x09) + chr(0x0A) + chr(0x0B) + chr(0x0C)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # 
        ## Test signed 32-bit int (aka, int32) with high bit set.                
        #
        x = gd.IntItem(name='int32', width=4, packspec='<l', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '<l', "packSpec should be <l"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int32', "getName should be int32"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3) 
        expval = -202182160 
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(-202182160)
        buffer = x.dumpStr()
        expbuffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == -202182160, "retval should be -202182160, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF4) + chr(0x01) + chr(0x11) + chr(0x21)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF5) + chr(0x02) + chr(0x12) + chr(0x22)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF6) + chr(0x03) + chr(0x13) + chr(0x23)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x11) + chr(0x12) + chr(0x13) + chr(0x14)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x15) + chr(0x16) + chr(0x17) + chr(0x18) + chr(0x19) + chr(0x1A)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"


        # 
        ## Test big endian signed 32-bit int (aka, beint32) with high bit unset.                 
        #
        x = gd.IntItem(name='beint32', width=4, packspec='>l', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '>l', "packSpec should be >l"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint32', "getName should be beint32"
        buffer = chr(0x41) + chr(0x42) + chr(0x43) + chr(0x44)
        expval = 0x41424344
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x41424344)
        buffer = x.dumpStr()
        expbuffer = chr(0x41) + chr(0x42) + chr(0x43) + chr(0x44)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x41424344, "retval should be 0x41424344, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x45) + chr(0x46) + chr(0x47) + chr(0x48)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0x49) + chr(0x50) + chr(0x51) + chr(0x52)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0x53) + chr(0x54) + chr(0x55) + chr(0x56)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x2C) + chr(0x3C) + chr(0x4C) + chr(0x5C)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x2C) + chr(0x3C) + chr(0x4C) + chr(0x5C) + chr(0x6C) + chr(0x7C)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # 
        ## Test big endian signed 32-bit int (aka, beint32) with high bit set.                  
        #
        x = gd.IntItem(name='beint32', width=4, packspec='>l', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '>l', "packSpec should be >l"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint32', "getName should be beint32"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3)
        expval = -252579085 
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x15253545)
        buffer = x.dumpStr()
        expbuffer = chr(0x15) + chr(0x25) + chr(0x35) + chr(0x45)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x15253545, "retval should be 0x15253545, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF4) + chr(0x60) + chr(0x61) + chr(0x62)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF5) + chr(0x63) + chr(0x64) + chr(0x65)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF6) + chr(0x66) + chr(0x67) + chr(0x68)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xA6) + chr(0xB6) + chr(0xC6) + chr(0xD6)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xA6) + chr(0xB6) + chr(0xC6) + chr(0xD6) + chr(0xE6) + chr(0xF6)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # 
        ## Test unsigned 32-bit int (aka, uint32) with high bit unset.                
        #
        x = gd.IntItem(name='uint32', width=4, packspec='<L', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '<L', "packSpec should be <L"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint32', "getName should be uint32"
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04)
        expval = 0x04030201
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x01020304)
        buffer = x.dumpStr()
        expbuffer = chr(0x04) + chr(0x03) + chr(0x02) + chr(0x01)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x01020304, "retval should be 0x01020304, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x2A) + chr(0x2B) + chr(0x2C) + chr(0x2D)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0x4C) + chr(0x4D) + chr(0x4E) + chr(0x4F)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0x6A) + chr(0x6B) + chr(0x6C) + chr(0x6D)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x12) + chr(0x34) + chr(0x56) + chr(0x78)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x12) + chr(0x34) + chr(0x56) + chr(0x78) + chr(0x9A) + chr(0xBC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # 
        ## Test unsigned 32-bit int (aka, uint32) with high bit set.                
        #
        x = gd.IntItem(name='uint32', width=4, packspec='<L', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '<L', "packSpec should be <L"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint32', "getName should be uint32"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3)
        expval = 4092785136   # 0xF3F2F1F0
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        testval = (long(0x88) << 24) + 0x00227711   # 0x88227711 - Encoded to work with older Python versions
        x.setValue(testval)
        buffer = x.dumpStr()
        expbuffer = chr(0x11) + chr(0x77) + chr(0x22) + chr(0x88)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == testval, "retval should be 0x88227711 (%d), got %s instead." % (testval, 
                                                                                         str(retval))



        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF4) + chr(0x0A) + chr(0x0B) + chr(0x0C)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF5) + chr(0x1A) + chr(0x1B) + chr(0x1C)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF6) + chr(0x2A) + chr(0x2B) + chr(0x2C)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xA0) + chr(0xB1) + chr(0xC2) + chr(0xD3)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xA0) + chr(0xB1) + chr(0xC2) + chr(0xD3) + chr(0xE4) + chr(0xF5)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # 
        ## Test big endian unsigned 32-bit int (aka, beuint32) with high bit unset.                 
        #
        x = gd.IntItem(name='beuint32', width=4, packspec='>L', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '>L', "packSpec should be >L"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint32', "getName should be beuint32"
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04)
        expval = 0x01020304
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x01020304)
        buffer = x.dumpStr()
        expbuffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x01020304, "retval should be 0x01020304, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x05) + chr(0x06) + chr(0x07) + chr(0x08)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xA5) + chr(0xA6) + chr(0xA7) + chr(0xA8)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xB5) + chr(0xB6) + chr(0xB7) + chr(0xB8)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x0A) + chr(0x1B) + chr(0x2C) + chr(0x3D)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x0A) + chr(0x1B) + chr(0x2C) + chr(0x3D) + chr(0x4E) + chr(0x5F)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # 
        ## Test big endian unsigned 32-bit int (aka, beuint32) with high bit set.                    
        #
        x = gd.IntItem(name='beuint32', width=4, packspec='>L', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '>L', "packSpec should be >L"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint32', "getName should be beuint32"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3) 
        expval = 4042388211  # 0xF0F1F2F3
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x42434445)
        buffer = x.dumpStr()
        expbuffer = chr(0x42) + chr(0x43) + chr(0x44) + chr(0x45)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x42434445, "retval should be 0x42434445, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF4) + chr(0xF3) + chr(0xF2) + chr(0xF1)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF5) + chr(0xF4) + chr(0xF3) + chr(0xF2)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed() of buffer, 0 should be 4"

        buffer = chr(0xF6) + chr(0xF5) + chr(0xF4) + chr(0xF3)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Now do a similar test with an initial value.
        x = gd.IntItem(name='int32', width=4, packspec='<l', ispack=1, value=0x36353433)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.packSpec() == '<l', "packSpec should be <l"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int32', "getName should be int32"
        buffer1 = chr(0x33) + chr(0x34) + chr(0x35) + chr(0x36) + chr(0x37)
        buffer2 = chr(0x32) + chr(0x33) + chr(0x34) + chr(0x35) + chr(0x36)
        retvalue = x._getValue(buffer1, 0)
        expval1 = 0x36353433
        assert retvalue == expval1, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of 0x32333435, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of 0x33343536, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of 0x33343536, 1 should be 0"
        assert x.isMatch(buffer2, 1).isMatch() ==  1, "isMatch of 0x32333435, 1 should be 1"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        testbuff = chr(0x32) + chr(0x33) + chr(0x34) + chr(0x35) + chr(0x36) + chr(0x37) 
        assert x.isMatch(testbuff, 0).isNotMatch() == 1, "isNotMatch of testbuff, 0 should be 1"
        assert x.isMatch(testbuff, 0).isMatch() == 0, "isMatch of testbuff, 0 should be 0"
        assert x.isMatch(testbuff, 0).isPotentialMatch() == 0, "isPotentialMatch of testbuff, 0 should be 0"
        assert x.isMatch(testbuff, 1).isMatch() ==  1, "isMatch of testbuff, 1 should be 1"
        assert x.isMatch(testbuff, 1).isNotMatch() == 0, "isNotMatch of testbuff, 1, should be 0"
        assert x.isMatch(testbuff, 1).isPotentialMatch() == 1, "isPotentialMatch of testbuff, 1, should be 1"
        assert x.isMatch(testbuff, 2).isMatch() == 0, "isMatch of testbuff, 2 should be 0"
        assert x.isMatch(testbuff, 2).isNotMatch() == 1, "isNotMatch of testbuff, 1 should be 1"
        assert x.isMatch(testbuff, 2).isPotentialMatch() == 0, "isPotentialMatch of testbuff, 2 should be 1"
        assert x.isMatch(testbuff, 3).isMatch() ==  0, "isMatch of testbuff, 3 should be 0"
        assert x.isMatch(testbuff, 3).isNotMatch() == 0, "isNotMatch of testbuff, 3 should be 0"
        assert x.isMatch(testbuff, 3).isPotentialMatch() == 1, "isPotentialMatch of testbuff, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0xAA) + chr(0x00) + chr(0xBB) + chr(0x11)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0xAA) + chr(0x00) + chr(0xBB) + chr(0x11) + chr(0xCC) + chr(0x22)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        #
        ##
        ###   6 4 - B I T   I N T   V A L U E S
        ##
        #

        # 
        ## Test signed 64-bit int (aka, int64) with high bit unset.               
        #
        x = gd.IntItem(name='int64', width=8, packspec='<q', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '<q', "packSpec should be <q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int64', "getName should be int64"
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04) + \
                 chr(0x0A) + chr(0x0B) + chr(0x0C) + chr(0x0D) 
        expval = 0x0D0C0B0A04030201
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x0102030405060708)
        buffer = x.dumpStr()
        expbuffer = chr(0x08)+chr(0x07)+chr(0x06)+chr(0x05)+chr(0x04)+chr(0x03)+chr(0x02)+chr(0x01)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x0102030405060708, "retval should be 0x0102030405060708, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xF4) + chr(0xF3) + chr(0xF2) + chr(0xF1) + chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0xE5) + chr(0xE4) + chr(0xE3) + chr(0xE2) + chr(0x11) + chr(0x12) + chr(0x13) + chr(0x14)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0xF6) + chr(0xF5) + chr(0xF4) + chr(0xF3) + chr(0x21) + chr(0x22) + chr(0x23) + chr(0x24)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04) + chr(0xFF) + chr(0xFE) + chr(0xFD) + chr(0xFC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04) + chr(0xFF) + chr(0xFE) + chr(0xFD) + chr(0xFC) \
               + chr(0xFB) + chr(0xFA)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"

        # 
        ## Test signed 64-bit int (aka, int64) with high bit set.                
        #
        x = gd.IntItem(name='int64', width=8, packspec='<q', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '<q', "packSpec should be <q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int64', "getName should be int64"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3) + \
                 chr(0x0A) + chr(0x0B) + chr(0x0C) + chr(0x0D) 
        expval = 0x0D0C0B0AF3F2F1F0
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x0102030405060708)
        buffer = x.dumpStr()
        expbuffer = chr(0x08)+chr(0x07)+chr(0x06)+chr(0x05)+chr(0x04)+chr(0x03)+chr(0x02)+chr(0x01)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x0102030405060708, "retval should be 0x0102030405060708, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0xD4) + chr(0xD3) + chr(0xD2) + chr(0xD1) + chr(0x31) + chr(0x32) + chr(0x33) + chr(0x34)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0xD5) + chr(0xD4) + chr(0xD3) + chr(0xD2) + chr(0x41) + chr(0x42) + chr(0x43) + chr(0x44)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0xD6) + chr(0xD5) + chr(0xD4) + chr(0xD3) + chr(0x51) + chr(0x52) + chr(0x53) + chr(0x54)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x11) + chr(0x12) + chr(0x13) + chr(0x14) + chr(0xEF) + chr(0xEE) + chr(0xED) + chr(0xEC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x11) + chr(0x12) + chr(0x13) + chr(0x14) + chr(0xEF) + chr(0xEE) + chr(0xED) + chr(0xEC) \
               + chr(0xEB) + chr(0xEA)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"

        # 
        ## Test big endian signed 64-bit int (aka, beint64) with high bit set.                    
        #
        x = gd.IntItem(name='beint64', width=8, packspec='>q', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '>q', "packSpec should be >q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beint64', "getName should be beint64"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3) + \
                 chr(0xF4) + chr(0xF5) + chr(0xF6) + chr(0xF7) 
        expval = -1084818905618843913L
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x0102030405060708)
        buffer = x.dumpStr()
        expbuffer = chr(0x01)+chr(0x02)+chr(0x03)+chr(0x04)+chr(0x05)+chr(0x06)+chr(0x07)+chr(0x08)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x0102030405060708, "retval should be 0x0102030405060708, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x04) + chr(0x03) + chr(0x02) + chr(0x01) + chr(0xAA) + chr(0xAB) + chr(0xAC) + chr(0xAD)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x05) + chr(0x04) + chr(0x03) + chr(0x02) + chr(0xBB) + chr(0xBC) + chr(0xBD) + chr(0xBE)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x06) + chr(0x05) + chr(0x04) + chr(0x03) + chr(0xCC) + chr(0xCD) + chr(0xCE) + chr(0xCF)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x21) + chr(0x22) + chr(0x23) + chr(0x24) + chr(0xDF) + chr(0xDE) + chr(0xDD) + chr(0xDC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x21) + chr(0x22) + chr(0x23) + chr(0x24) + chr(0xDF) + chr(0xDE) + chr(0xDD) + chr(0xDC) \
               + chr(0xDB) + chr(0xDA)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"


        # 
        ## Test unsigned 64-bit int (aka, uint64) with high bit unset.               
        #
        x = gd.IntItem(name='uint64', width=8, packspec='<Q', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '<Q', "packSpec should be <Q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint64', "getName should be uint64"
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04) + \
                 chr(0x0A) + chr(0x0B) + chr(0x0C) + chr(0x0D) 
        expval = 0x0D0C0B0A04030201
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x0102030405060708)
        buffer = x.dumpStr()
        expbuffer = chr(0x08)+chr(0x07)+chr(0x06)+chr(0x05)+chr(0x04)+chr(0x03)+chr(0x02)+chr(0x01)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x0102030405060708, "retval should be 0x0102030405060708, got %s instead." % str(retval)

        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x20) + chr(0x21) + chr(0x22) + chr(0x23) + chr(0xC0) + chr(0xC1) + chr(0xC2) + chr(0xC3)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x30) + chr(0x31) + chr(0x32) + chr(0x33) + chr(0xD0) + chr(0xD1) + chr(0xD2) + chr(0xD3)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x40) + chr(0x41) + chr(0x42) + chr(0x43) + chr(0xE0) + chr(0xE1) + chr(0xE2) + chr(0xE3)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x31) + chr(0x32) + chr(0x33) + chr(0x34) + chr(0xCF) + chr(0xCE) + chr(0xCD) + chr(0xCC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x31) + chr(0x32) + chr(0x33) + chr(0x34) + chr(0xCF) + chr(0xCE) + chr(0xCD) + chr(0xCC) \
               + chr(0xCB) + chr(0xCA)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"

        # 
        ## Test unsigned 64-bit int (aka, uint64) with high bit set.                
        #
        x = gd.IntItem(name='uint64', width=8, packspec='<Q', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '<Q', "packSpec should be <Q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'uint64', "getName should be uint64"
        buffer = chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04) + \
                 chr(0x0A) + chr(0x0B) + chr(0x0C) + chr(0x0D) 
        expval = 0x0D0C0B0A04030201
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x4041424344454647)
        buffer = x.dumpStr()
        expbuffer = chr(0x47)+chr(0x46)+chr(0x45)+chr(0x44)+chr(0x43)+chr(0x42)+chr(0x41)+chr(0x40)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x4041424344454647, "retval should be 0x4041424344454647, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x5A) + chr(0x5B) + chr(0x5C) + chr(0x5D) + chr(0x01) + chr(0x02) + chr(0x03) + chr(0x04)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x6A) + chr(0x6B) + chr(0x6C) + chr(0x6D) + chr(0x11) + chr(0x12) + chr(0x13) + chr(0x14)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x7A) + chr(0x7B) + chr(0x7C) + chr(0x7D) + chr(0x21) + chr(0x22) + chr(0x23) + chr(0x24)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x41) + chr(0x42) + chr(0x43) + chr(0x44) + chr(0xBF) + chr(0xBE) + chr(0xBD) + chr(0xBC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x41) + chr(0x42) + chr(0x43) + chr(0x44) + chr(0xBF) + chr(0xBE) + chr(0xBD) + chr(0xBC) \
               + chr(0xBB) + chr(0xBA)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"


        #
        ## Test big endian unsigned 64-bit int (aka, beuint64) with high bit set.                    
        #
        x = gd.IntItem(name='beuint64', width=8, packspec='>Q', ispack=1)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '>Q', "packSpec should be >Q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'beuint64', "getName should be beuint64"
        buffer = chr(0xF0) + chr(0xF1) + chr(0xF2) + chr(0xF3) + \
                 chr(0xF4) + chr(0xF5) + chr(0xF6) + chr(0xF7) 
        expval = 17361925168090707703L
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue should be %s not %s" % (str(expval),
                                                                    str(retval))

        # Test setValue() and dumpStr().
        x.setValue(0x4041424344454647)
        buffer = x.dumpStr()
        expbuffer = chr(0x40)+chr(0x41)+chr(0x42)+chr(0x43)+chr(0x44)+chr(0x45)+chr(0x46)+chr(0x47)
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 0x4041424344454647, "retval should be 0x4041424344454647, got %s instead." % str(retval)


        # Test the isMatch, isNotMatch, bytesConsumed, and isPotentialMatch methods.  
        # Anything should match (as long at it is long enough) because no initial 
        # value was specified.
        buffer = chr(0x8A) + chr(0x8B) + chr(0x8C) + chr(0x8D) + chr(0x31) + chr(0x32) + chr(0x33) + chr(0x34)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0x9A) + chr(0x9B) + chr(0x9C) + chr(0x9D) + chr(0x41) + chr(0x42) + chr(0x43) + chr(0x44)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch() of buffer, 0 should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 0 should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed() of buffer, 0 should be 8"

        buffer = chr(0xAA) + chr(0xAB) + chr(0xAC) + chr(0xAD) + chr(0x51) + chr(0x51) + chr(0x51) + chr(0x51)
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch() of buffer, 1 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of buffer, 1 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of buffer, 1 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of buffer, 1 should be None"

        ismatchobj = x.isMatch('', 0)
        assert ismatchobj.isMatch() == 0, "isMatch() of '', 0 should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch() of '', 0 should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch() of '', 0 should be 1"
        assert ismatchobj.bytesConsumed() == None, "bytesConsumed() of '', 0 should be None"

        # Now do a similar test with an initial value.
        x = gd.IntItem(name='int64', width=8, packspec='<q', ispack=1, value=0x4039383736353433)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.packSpec() == '<q', "packSpec should be <q"
        assert x.getType() is None, "getType should be None"
        assert x.getName() == 'int64', "getName should be int64"
        buffer1 = chr(0x33) + chr(0x34) + chr(0x35) + chr(0x36) + chr(0x37) + chr(0x38) + chr(0x39) + chr(0x40)
        buffer2 = chr(0x32) + chr(0x33) + chr(0x34) + chr(0x35) + chr(0x36) + chr(0x37) + chr(0x38) + chr(0x39)
        retvalue = x._getValue(buffer1, 0)
        expval1 = 0x4039383736353433
        assert retvalue == expval1, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of 0x3233343536373839, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of 0x3334353637383940, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of 0x3334353637383940, 1 should be 0"
        assert x.isMatch(buffer2, 1).isMatch() ==  0, "isMatch of 0x3233343536373839, 1 should be 0"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        buff3=chr(0x32)+chr(0x33)+chr(0x34)+chr(0x35)+chr(0x36)+chr(0x37)+chr(0x38)+chr(0x39)+chr(0x40)+chr(0x41)
        assert x.isMatch(buff3, 0).isNotMatch() == 1, "isNotMatch of buff3, 0 should be 1"
        assert x.isMatch(buff3, 0).isMatch() == 0, "isMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 0).isPotentialMatch() == 0, "isPotentialMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 1).isMatch() ==  1, "isMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 1).isNotMatch() == 0, "isNotMatch of buff3, 1, should be 0"
        assert x.isMatch(buff3, 1).isPotentialMatch() == 1, "isPotentialMatch of buff3, 1, should be 1"
        assert x.isMatch(buff3, 2).isMatch() == 0, "isMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 2).isNotMatch() == 1, "isNotMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 2).isPotentialMatch() == 0, "isPotentialMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 3).isMatch() ==  0, "isMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isNotMatch() == 0, "isNotMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isPotentialMatch() == 1, "isPotentialMatch of buff3, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = chr(0x51) + chr(0x52) + chr(0x53) + chr(0x54) + chr(0xAF) + chr(0xAE) + chr(0xAD) + chr(0xAC)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = chr(0x51) + chr(0x52) + chr(0x53) + chr(0x54) + chr(0xAF) + chr(0xAE) + chr(0xAD) + chr(0xAC) \
               + chr(0xAB) + chr(0xAA)
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"

        # @fixme: Need test for setBytesConsumed.
        
    def test_case_float_objects(self):

        #
        ##
        ###   F L O A T   V A L U E S
        ##
        #

        # NOTE: We used the IEEE-754 Floating-Point Conversion calculator at 
        #       http://babbage.cs.qc.edu/IEEE-754/Decimal.html to come up 
        #       with test data in HEX.

        float_allowable_diff = .0001

        #   P O S I T I V E   V A L U E   

        x = gd.FloatItem(name='float1', type='float', width=4, packspec='f', ispack=1, value=33.33)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() == 'f', "packSpec should be f"
        assert x.getType() is 'float', "getType should be 'float'"
        assert x.getName() == 'float1', "getName should be float1"

        hexval1 = 0x420551EC                 # This is a representation of 33.33 stored in IEEE-754
        buffer1 = struct.pack('<L', hexval1) # Pack it into a buffer.

        hexval2 = 0x420661ED                # This something that is not a representation of 33.33
        buffer2 = struct.pack('<L', hexval2) # Pack it into a buffer.
        
        retvalue = x._getValue(buffer1, 0)
        expval1 = 33.33
        assert abs(retvalue - expval1) < float_allowable_diff, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of buffer2, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of buffer1, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch(buffer2, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        buff3=' '+buffer1+' '
        assert x.isMatch(buff3, 0).isNotMatch() == 1, "isNotMatch of buff3, 0 should be 1"
        assert x.isMatch(buff3, 0).isMatch() == 0, "isMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 0).isPotentialMatch() == 0, "isPotentialMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 1).isMatch() ==  1, "isMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 1).isNotMatch() == 0, "isNotMatch of buff3, 1, should be 0"
        assert x.isMatch(buff3, 1).isPotentialMatch() == 1, "isPotentialMatch of buff3, 1, should be 1"
        assert x.isMatch(buff3, 2).isMatch() == 0, "isMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 2).isNotMatch() == 1, "isNotMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 2).isPotentialMatch() == 0, "isPotentialMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 3).isMatch() ==  0, "isMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isNotMatch() == 0, "isNotMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isPotentialMatch() == 1, "isPotentialMatch of buff3, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = ' ' * 4
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = ' ' * 8
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # Test setValue() and dumpStr().
        hexval = 0x420551EC
        buffer1 = struct.pack('<L', hexval) # Pack it into a buffer.
        x.setValue(33.33)
        buffer2 = x.dumpStr()
        assert buffer1 == buffer2, "dumpStr() result did not match expected result."

        #   N E G A T I V E   V A L U E    

        x = gd.FloatItem(name='float2', type='float', width=4, packspec='f', ispack=1, value=-0.426923)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 4, "getWidth should be 4"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() == 'f', "packSpec should be f"
        assert x.getType() is 'float', "getType should be 'float'"
        assert x.getName() == 'float2', "getName should be float2"

        # 0xBEDA95A7 - Encoded to work with older Python versions
        hexval1 = (long(0xBE) << 24) + 0x00DA95A7  # This is a representation of -0.426923 stored in IEEE-754
        buffer1 = struct.pack('<L', hexval1) # Pack it into a buffer.

        hexval2 = 0x08D07567                 # This something that is not a representation of -0.426923 
        buffer2 = struct.pack('<L', hexval2) # Pack it into a buffer.
        
        retvalue = x._getValue(buffer1, 0)
        expval1 = -0.426923 
        assert abs(retvalue - expval1) < float_allowable_diff, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of buffer2, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of buffer1, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch(buffer2, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        buff3=' '+buffer1+' '
        assert x.isMatch(buff3, 0).isNotMatch() == 1, "isNotMatch of buff3, 0 should be 1"
        assert x.isMatch(buff3, 0).isMatch() == 0, "isMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 0).isPotentialMatch() == 0, "isPotentialMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 1).isMatch() ==  1, "isMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 1).isNotMatch() == 0, "isNotMatch of buff3, 1, should be 0"
        assert x.isMatch(buff3, 1).isPotentialMatch() == 1, "isPotentialMatch of buff3, 1, should be 1"
        assert x.isMatch(buff3, 2).isMatch() == 0, "isMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 2).isNotMatch() == 1, "isNotMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 2).isPotentialMatch() == 0, "isPotentialMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 3).isMatch() ==  0, "isMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isNotMatch() == 0, "isNotMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isPotentialMatch() == 1, "isPotentialMatch of buff3, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = ' ' * 4
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = ' ' * 8
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"

        # Test setValue() and dumpStr().
        # 0xBEDA95A7 - Encoded to work with older Python versions
        hexval = (long(0xBE) << 24) + 0x00DA95A7  # This is a representation of -0.426923 stored in IEEE-754
        buffer1 = struct.pack('<L', hexval) # Pack it into a buffer.
        x.setValue(-0.426923)
        buffer2 = x.dumpStr()

        #print 'buffer1', util.dump_binary_str(buffer1)
        #print 'buffer2', util.dump_binary_str(buffer2)
        
        assert buffer1 == buffer2, "dumpStr() result did not match expected result."

        #
        ##
        ###   D O U B L E   V A L U E S
        ##
        #

        # NOTE: We used the IEEE-754 Floating-Point Conversion calculator at 
        #       http://babbage.cs.qc.edu/IEEE-754/Decimal.html to come up 
        #       with test data in HEX.

        float_allowable_diff = .0001

        #   P O S I T I V E   V A L U E   

        x = gd.FloatItem(name='double1', type='double', width=8, packspec='d', ispack=1, value=33.33)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() == 'd', "packSpec should be d"
        assert x.getType() is 'double', "getType should be 'double'"
        assert x.getName() == 'double1', "getName should be double1"

        hexval1 = 0x4040AA3D70A3D70A                 # This is a representation of 33.33 stored in IEEE-754
        buffer1 = struct.pack('<Q', hexval1)         # Pack it into a buffer.

        hexval2 = 0x4037000000000000                 # This something that is not a representation of 33.33
        buffer2 = struct.pack('<Q', hexval2)         # Pack it into a buffer.
        
        retvalue = x._getValue(buffer1, 0)
        expval1 = 33.33
        assert abs(retvalue - expval1) < float_allowable_diff, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of buffer2, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of buffer1, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch(buffer2, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        buff3=' '+buffer1+' '
        assert x.isMatch(buff3, 0).isNotMatch() == 1, "isNotMatch of buff3, 0 should be 1"
        assert x.isMatch(buff3, 0).isMatch() == 0, "isMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 0).isPotentialMatch() == 0, "isPotentialMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 1).isMatch() ==  1, "isMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 1).isNotMatch() == 0, "isNotMatch of buff3, 1, should be 0"
        assert x.isMatch(buff3, 1).isPotentialMatch() == 1, "isPotentialMatch of buff3, 1, should be 1"
        assert x.isMatch(buff3, 2).isMatch() == 0, "isMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 2).isNotMatch() == 1, "isNotMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 2).isPotentialMatch() == 0, "isPotentialMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 3).isMatch() ==  0, "isMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isNotMatch() == 0, "isNotMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isPotentialMatch() == 1, "isPotentialMatch of buff3, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = ' ' * 8
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = ' ' * 8
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"

        # Test setValue() and dumpStr().
        hexval = 0x4040AA3D70A3D70A
        buffer1 = struct.pack('<Q', hexval) # Pack it into a buffer.
        x.setValue(33.33)
        buffer2 = x.dumpStr()
        assert buffer1 == buffer2, "dumpStr() result did not match expected result."

        #   N E G A T I V E   V A L U E    

        x = gd.FloatItem(name='double2', type='double', width=8, packspec='d', ispack=1, value=-0.426923)

        assert x.isPackCompatible() == 1, "isPackCompatible should be 1"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() == 'd', "packSpec should be d"
        assert x.getType() is 'double', "getType should be 'double'"
        assert x.getName() == 'double2', "getName should be double2"

        # 0xBFDB52B4D8BA40D9 - Encoded to work with older Python versions
        #hexval1 = (long(0xBF) << 24) + 0xDB52B4D8BA40D9  # This is a representation of -0.426923 stored in IEEE-754
        hexval1 = 0xBFDB52B4D8BA40D9                      
        buffer1 = struct.pack('<Q', hexval1)              # Pack it into a buffer.
        hexval2 = 0xBEDB52B4D8BA4242                      # This something that is not a representation of -0.426923 
        buffer2 = struct.pack('<Q', hexval2)              # Pack it into a buffer.
        
        retvalue = x._getValue(buffer1, 0)
        expval1 = -0.426923 
        diff = abs(retvalue - expval1)
        assert abs(retvalue - expval1) < float_allowable_diff, "_getValue should be expval1 not %s" % str(retvalue)

        assert x.isMatch(buffer2, 0).isNotMatch() == 1, "isNotMatch of buffer2, 0 should be 1"
        assert x.isMatch(buffer1, 0).isMatch() ==  1, "isMatch of buffer1, 0 should be 1"
        assert x.isMatch(buffer1, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch(buffer2, 1).isMatch() ==  0, "isMatch of buffer1, 1 should be 0"
        assert x.isMatch('', 0).isMatch()        ==  0, "isMatch of '', 0 should be 0"

        buff3=' '+buffer1+' '
        assert x.isMatch(buff3, 0).isNotMatch() == 1, "isNotMatch of buff3, 0 should be 1"
        assert x.isMatch(buff3, 0).isMatch() == 0, "isMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 0).isPotentialMatch() == 0, "isPotentialMatch of buff3, 0 should be 0"
        assert x.isMatch(buff3, 1).isMatch() ==  1, "isMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 1).isNotMatch() == 0, "isNotMatch of buff3, 1, should be 0"
        assert x.isMatch(buff3, 1).isPotentialMatch() == 1, "isPotentialMatch of buff3, 1, should be 1"
        assert x.isMatch(buff3, 2).isMatch() == 0, "isMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 2).isNotMatch() == 1, "isNotMatch of buff3, 1 should be 1"
        assert x.isMatch(buff3, 2).isPotentialMatch() == 0, "isPotentialMatch of buff3, 2 should be 0"
        assert x.isMatch(buff3, 3).isMatch() ==  0, "isMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isNotMatch() == 0, "isNotMatch of buff3, 3 should be 0"
        assert x.isMatch(buff3, 3).isPotentialMatch() == 1, "isPotentialMatch of buff3, 3 should be 1"

        # Test the isEnoughData method.  As long as the buffer is the expected length
        # or longer, it should pass.
        buffer = ' ' * 8
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        buffer = ' ' * 8
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"

        # Test setValue() and dumpStr().
        # 0xBFDB52B4D8BA40D9 - Encoded to work with older Python versions
        #hexval = (long(0xBE) << 24) + 0x00DA95A7  # This is a representation of -0.426923 stored in IEEE-754
        hexval = 0xBFDB52B4D8BA40D9
        buffer1 = struct.pack('<Q', hexval) # Pack it into a buffer.
        x.setValue(-0.426923)
        buffer2 = x.dumpStr()
        assert buffer1 == buffer2, "dumpStr() result did not match expected result."

        

    def test_case_pad_objects(self):

        #
        ##
        ###   P A D   O B J E C T   W I D T H   8                 
        ##
        #
        x = gd.PadItem(name='pad8', type='pad', width=8)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.packSpec() is None, "packSpec should be None"
        assert x.getType() == 'pad', "getType should be pad"
        assert x.getName() == 'pad8', "getName should be pad8"
        
        buffer = chr(0xFF) * 8
        expval = chr(0x00) * 8
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(0) should be 8"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None"
        
        buffer = chr(0xFE) * 7
        retval = x._getValue(buffer, 0)
        assert retval is None, "_getValue() did not return None"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0, "_isEnoughData(0) should be 0"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"

        buffer = chr(0xFF) * 9
        expval = chr(0x00) * 8
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8, not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 8, "_isEnoughData(1) should be 8 not %s" % str(retval)
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(0) should be 8"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(1) should be 8"

        # Test setValue() and dumpStr().
        didcatch = 0
        try:
            x.setValue(buffer)
        except:
            didcatch = 1
        if not didcatch:
            raise "setValue() for PadItem did not raise an exception"
        #
        buffer = x.dumpStr()
        expbuffer = chr(0x00) * 8
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == chr(0x00) * 8, "retval should be chr(0x00) * 8, got %s instead." % str(retval)

        #
        ##
        ###   P A D   O B J E C T   W I D T H   4 2                
        ##
        #
        x = gd.PadItem(name='pad42', type='pad', width=42)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 42, "getWidth should be 42"
        assert x.getType() == 'pad', "getType should be pad"
        assert x.getName() == 'pad42', "getName should be pad42"
        
        buffer = chr(0xFF) * 42
        expval = chr(0x00) * 42
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 42, "_isEnoughData(0) should be 42"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 42, "bytesConsumed(0) should be 42"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None"
        
        buffer = chr(0xFE) * 41
        retval = x._getValue(buffer, 0)
        assert retval is None, "_getValue() did not return None"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0, "_isEnoughData(0) should be 0"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"

        buffer = chr(0xFF) * 43
        expval = chr(0x00) * 42
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 42, "_isEnoughData(0) should be 42, not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 42, "_isEnoughData(1) should be 42 not %s" % str(retval)
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 42, "bytesConsumed(0) should be 42"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 42, "bytesConsumed(1) should be 42"
        
        # Test dumpStr().
        buffer = x.dumpStr()
        expbuffer = chr(0x00) * 42
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == chr(0x00) * 42, "retval should be chr(0x00) * 42, got %s instead." % str(retval)

        
    def test_case_fbuffer_objects(self):

        #
        ##
        ###  F B U F F E R   O B J E C T   W I D T H   8
        ##
        #

        x = gd.BufferItem(name='fbuffer8', type='fbuffer', width=8, isfixedwidth=1)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.getType() == 'fbuffer', "getType should be fbuffer"
        assert x.getName() == 'fbuffer8', "getName should be fbuffer8"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=0, 0) should be 0"

        buffer = ' '
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=1, 0) should be 0"

        buffer = ' ' * 8
        assert x._isEnoughData(buffer, 0) == 8, "_isEnoughData(len=8, 0) should be 8"

        buffer = ' ' * 9
        assert x._isEnoughData(buffer, 0) == 8, "_isEnoughData(len=9, 0) should be 8"
        
        buffer = chr(0xFF) * 8
        expval = buffer
        retval = x._getValue(buffer, 0)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)
        
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8 not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(0) should be 8"
        
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None"
        
        buffer = chr(0xFE) * 7
        retval = x._getValue(buffer, 0)
        assert retval is None, "_getValue() did not return None"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0, "_isEnoughData(0) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"
        
        buffer = chr(0xFF) * 9
        expval = chr(0xFF) * 8
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 8, "_isEnoughData(1) should be 8"
         
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(0) should be 8"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(1) should be 8"

        # Test setValue() and dumpStr().
        buffer = chr(0xAA) * 8
        x.setValue(buffer)
        buffer = x.dumpStr()
        expbuffer = chr(0xAA) * 8
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == chr(0xAA) * 8, "retval should be chr(0xAA) * 8, got %s instead." % str(retval)

        #
        ##
        ###  F B U F F E R   O B J E C T   W I D T H   4 2
        ##
        #

        x = gd.BufferItem(name='fbuffer42', type='fbuffer', width=42, isfixedwidth=1)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 42, "getWidth should be 42"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.getType() == 'fbuffer', "getType should be fbuffer"
        assert x.getName() == 'fbuffer42', "getName should be fbuffer42"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=0, 0) should be 0"

        buffer = ' '
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=1, 0) should be 0"

        buffer = ' ' * 42
        assert x._isEnoughData(buffer, 0) == 42, "_isEnoughData(len=42, 0) should be 42"

        buffer = ' ' * 43
        assert x._isEnoughData(buffer, 0) == 42, "_isEnoughData(len=43, 0) should be 42"
        
        buffer = chr(0xFF) * 42
        expval = buffer
        retval = x._getValue(buffer, 0)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)
        
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 42, "_isEnoughData(0) should be 42 not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 42, "bytesConsumed(0) should be 42"
        
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None"
        
        buffer = chr(0xFE) * 41
        retval = x._getValue(buffer, 0)
        assert retval is None, "_getValue() did not return None"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0, "_isEnoughData(0) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"
        
        buffer = chr(0xFF) * 43
        expval = chr(0xFF) * 42
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 42, "_isEnoughData(0) should be 42"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 42, "_isEnoughData(1) should be 42"
         
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 42, "bytesConsumed(0) should be 42"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 42, "bytesConsumed(1) should be 42"

        # Test setValue() and dumpStr().
        buffer = chr(0xAA) * 42
        x.setValue(buffer)
        buffer = x.dumpStr()
        expbuffer = chr(0xAA) * 42
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == chr(0xAA) * 42, "retval should be chr(0xAA) * 42, got %s instead." % str(retval)

        
    def test_case_string_objects(self):

        #
        ##
        ###  S T R I N G  O B J E C T   W I D T H   8
        ##
        #

        x = gd.BufferItem(name='string8', type='string', width=8, isfixedwidth=1)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 1, "isFixedWidth should be 1"
        assert x.getWidth() == 8, "getWidth should be 8"
        assert x.getWidthIsPack() is None, "getWidthIsPack should be None"
        assert x.getWidthPackSpec() is None, "getWidthPackSpec should be None"
        assert x.getWidthPackLen() is None, "getWidthPackLen should be None"
        assert x.getType() == 'string', "getType should be string"
        assert x.getName() == 'string8', "getName should be string8"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=0, 0) should be 0"

        buffer = ' '
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=1, 0) should be 0"

        buffer = ' ' * 8
        assert x._isEnoughData(buffer, 0) == 8, "_isEnoughData(len=8, 0) should be 8"

        buffer = ' ' * 9
        assert x._isEnoughData(buffer, 0) == 8, "_isEnoughData(len=9, 0) should be 8"
        
        buffer = 'hello' + chr(0) * 3
        expval = 'hello'
        retval = x._getValue(buffer, 0)

        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8 not %s" % str(retval)
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(0) should be 8"
        
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None"
        
        buffer = chr(0xFE) * 7
        retval = x._getValue(buffer, 0)
        assert retval is None, "_getValue() did not return None"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0, "_isEnoughData(0) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"
        
        buffer = chr(0xFF) * 9
        expval = chr(0xFF) * 8
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 8, "_isEnoughData(0) should be 8"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 8, "_isEnoughData(1) should be 8"
         
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(0) should be 8"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 8, "bytesConsumed(1) should be 8"

        # Test setValue() and dumpStr().
        buffer = 'test'
        x.setValue(buffer)
        buffer = x.dumpStr()
        expbuffer = 'test' + chr(0x00) * 4
        assert expbuffer == buffer, "dumpStr() result did not match expected result."
        retval = x._getValue(buffer, 0)
        assert retval == 'test', "retval should be 'test', got %s instead." % str(retval)

        buffer = 'testtesttest'
        didcatch = 0
        try:
            x.setValue(buffer)
        except:
            didcatch = 1
        if not didcatch:
            raise "Called setValue for string item with too large a value, should have gotten an exception"
    #
    def test_case_vbuffer1_objects(self):

        #
        ##
        ###  V B U F F E R   O B J E C T   V B U F F E R 1                    
        ##
        #

        x = gd.BufferItem(name='vbuffer1', type='vbuffer1', widthispack=1, widthpackspec="B", widthpacklen=1)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 1, "getWidth should be 1, not %s" % str(x.getWidth())
        assert x.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert x.getWidthPackSpec() is 'B' , "getWidthPackSpec should be 'B'"
        assert x.getWidthPackLen() is 1, "getWidthPackLen should be 1"
        assert x.getType() == 'vbuffer1', "getType should be vbuffer1"
        assert x.getName() == 'vbuffer1', "getName should be vbuffer1"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"

        buffer = chr(3) + ' ' * 2
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=3+1, len=3, 0) should be 0"
        
        buffer = chr(3) + ' ' * 3
        assert x._isEnoughData(buffer, 0) == 4, "_isEnoughData(clen=3+1, len=4, 0) should be 4"

        buffer = chr(3) + ' ' * 4
        assert x._isEnoughData(buffer, 0) == 4, "_isEnoughData(clen=3+1, len=4, 0) should be 4"

        buffer = ' ' + chr(3) + ' ' * 3
        assert x._isEnoughData(buffer, 1) == 4, "_isEnoughData(clen=3+1, len=4, 1) should be 4"

        buffer = '  ' + chr(3) + ' ' * 2
        assert x._isEnoughData(buffer, 2) == 0, "_isEnoughData(clen=3+1, len=4, 2) should be 0"
       
        buffer = chr(3) + ' ' * 3
        expval = '   '
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 4, "_isEnoughData(0) should be 4"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(1) should be 0"
         
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4"
        
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None"
        
        buffer = chr(255) + ' ' * 254
        retval = x._getValue(buffer, 0)
        assert retval is None, "_getValue() did not return None"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0, "_isEnoughData(0) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"
       
        buffer = ' ' + chr(255) + ' ' * 256
        expval = ' ' * 255
        retval = x._getValue(buffer, 1)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 1)
        assert retval == 256, "_isEnoughData(1) should be 256"
 
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 256, "bytesConsumed(1) should be 256"

        # Test setValue() and dumpStr().
        buffer = ' ' * 255
        x.setValue(buffer)
        retval = x.dumpStr()
        expbuffer = chr(255) + ' ' * 255       
        assert expbuffer == retval, "dumpStr() result did not match expected result."
        retval = x._getValue(expbuffer, 0)
        assert retval == ' ' * 255, "retval should be ' ' * 255, got %s instead." % str(retval)
    #
    def test_case_non_fixed_vbuffer1(self):
    #
        class testvbuffer1(gd.BaseGDClass):
            def __init__(self):
                gd.BaseGDClass.__init__(self)
                #
                self.name = 'testvbuffer1'
                self._isFixed = 0
                self._width = 0
                self._num_items = 1
                self._isPackCompatible = 0
                self._packSpec = None
                #
                # Code to create item objects.
                self.items = []
                #
                x = gd.BufferItem(name="vbuffer1", ispack=0, widthispack=1, widthpackspec="B", widthpacklen=1, type="vbuffer1")
                self.items.append(x)

        x = testvbuffer1()

        y = x.findChildByName('vbuffer1')

        print 'x', x
        print 'y', y

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 0, "getWidth should be 0, not %s" % str(x.getWidth())
        assert x.getName() == 'testvbuffer1', "getName should be testvbuffer1"

        assert y.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert y.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert y.getWidth() == 1, "getWidth should be 1, not %s" % str(x.getWidth())
        assert y.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert y.getWidthPackSpec() is 'B' , "getWidthPackSpec should be 'B'"
        assert y.getWidthPackLen() is 1, "getWidthPackLen should be 1"
        assert y.getType() == 'vbuffer1', "getType should be vbuffer1"
        assert y.getName() == 'vbuffer1', "getName should be vbuffer1"
        
        #buffer = ''
        #assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"
        #
        #buffer = chr(3) + ' ' * 2
        #assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=3+1, len=3, 0) should be 0"
        #
        #buffer = chr(3) + ' ' * 3
        #assert x._isEnoughData(buffer, 0) == 4, "_isEnoughData(clen=3+1, len=4, 0) should be 4"
        #
        #buffer = chr(3) + ' ' * 4
        #assert x._isEnoughData(buffer, 0) == 4, "_isEnoughData(clen=3+1, len=4, 0) should be 4"
        #
        #buffer = ' ' + chr(3) + ' ' * 3
        #assert x._isEnoughData(buffer, 1) == 4, "_isEnoughData(clen=3+1, len=4, 1) should be 4"
        #
        #buffer = '  ' + chr(3) + ' ' * 2
        #assert x._isEnoughData(buffer, 2) == 0, "_isEnoughData(clen=3+1, len=4, 2) should be 0"
        #
        buffer = chr(3) + ' ' * 3
        #expval = '   '
        #retval = x._getValue(buffer, 0)
        #assert retval == expval, "_getValue() did not return expected result"
        #retval = x._isEnoughData(buffer, 0)
        #assert retval == 4, "_isEnoughData(0) should be 4"
        #retval = x._isEnoughData(buffer, 1)
        #assert retval == 0, "_isEnoughData(1) should be 0"
         
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4"
        
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 0, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(1) should be None not %s." % ismatchobj.bytesConsumed()
        
        buffer = chr(255) + ' ' * 254
        #retval = x._getValue(buffer, 0)
        #assert retval is None, "_getValue() did not return None"
        #retval = x._isEnoughData(buffer, 0)
        #assert retval == 0, "_isEnoughData(0) should be 0"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None"
       
        buffer = ' ' + chr(255) + ' ' * 256
        #expval = ' ' * 255
        #retval = x._getValue(buffer, 1)
        #assert retval == expval, "_getValue() did not return expected result"
        #retval = x._isEnoughData(buffer, 1)
        #assert retval == 256, "_isEnoughData(1) should be 256"
 
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 256, "bytesConsumed(1) should be 256"

        # Test setValue() and dumpStr().
        #buffer = ' ' * 255
        #x.setValue(buffer)
        #retval = x.dumpStr()
        #expbuffer = chr(255) + ' ' * 255       
        #assert expbuffer == retval, "dumpStr() result did not match expected result."
        #retval = x._getValue(expbuffer, 0)
        #assert retval == ' ' * 255, "retval should be ' ' * 255, got %s instead." % str(retval)

        #
        ##
        ###  V B U F F E R   O B J E C T   L E V B U F F E R 2                    
        ##
        #

        x = gd.BufferItem(name='levbuffer2', type='levbuffer2', widthispack=1, widthpackspec="<H", widthpacklen=2)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 2, "getWidth should be 2, not %s" % str(x.getWidth())
        assert x.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert x.getWidthPackSpec() is '<H' , "getWidthPackSpec should be '<H'"
        assert x.getWidthPackLen() is 2, "getWidthPackLen should be 2"
        assert x.getType() == 'levbuffer2', "getType should be levbuffer2"
        assert x.getName() == 'levbuffer2', "getName should be levbuffer2"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"

        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0101
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=0x0102+2, len=0x0101+2, 0) should be 0"
        
        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0102
        assert x._isEnoughData(buffer, 0) == 0x0102 + 2, "_isEnoughData(clen=0x0102+2, len=0x0102+2, 0) should be 0x0102 + 2"
        
        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0102 + ' '
        assert x._isEnoughData(buffer, 0) == 0x0102 + 2, "_isEnoughData(clen=0x0102+2, len=0x0102+2, 0) should be 0x0102 + 2"

        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0102 + ' ' * 2  
        assert x._isEnoughData(buffer, 0) == 0x0102 + 2, "_isEnoughData(clen=0x0102+2, len=0x0102+2, 0) should be 0x0102 + 2"

        buffer = ' ' + chr(0x02) + chr(0x01) + ' ' * 0x0102
        assert x._isEnoughData(buffer, 1) == 0x0102 + 2, "_isEnoughData(clen=0x0102+2, len=0x0102+2, 1) should be 0x0102 + 2"

        buffer = '  ' + chr(0x02) + chr(0x01) + ' ' * 0x0102
        assert x._isEnoughData(buffer, 2) == 0x0102 + 2, "_isEnoughData(clen=0x0102+2, len=0x0102+2, 2) should be 0x0102 + 2"
      
        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0102
        expval = ' ' * 0x0102     
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0x0102 + 2, "_isEnoughData(0) should be 0x0102 + 2"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 0x0102 + 2, "bytesConsumed(0) should be 0x0102 + 2"
        
        buffer = ' ' + chr(0x02) + chr(0x01) + ' ' * 0x0102
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0x0102 + 2, "_isEnoughData(1) should be 0x0102 + 2"

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 0"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 0x0102 + 2, "bytesConsumed(1) should be 0x0102 + 2"

        buffer = chr(0xFF) + chr(0x01) + ' ' * 0x01FF
        expval = ' ' * 0x01FF     
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expval"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0x01FF + 2, "_isEnoughData(0) should be 0x01FF + 2"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 0x01FF + 2, "bytesConsumed(0) should be 0x01FF + 2"
       
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0, "_isEnoughData(0) should be 0"

        # Test setValue() and dumpStr().
        buffer = ' ' * 0x01FF
        x.setValue(buffer)
        retval = x.dumpStr()
        expbuffer = chr(0xFF) + chr(0x01) + ' ' * 0x01FF       
        assert expbuffer == retval, "dumpStr() result did not match expected result."
        retval = x._getValue(expbuffer, 0)
        assert retval == ' ' * 0x01FF, "retval should be ' ' * 0x01FF, got %s instead." % str(retval)

        #
        ##
        ###  V B U F F E R   O B J E C T   B E V B U F F E R 2                    
        ##
        #

        x = gd.BufferItem(name='bevbuffer2', type='bevbuffer2', widthispack=1, widthpackspec=">H", widthpacklen=2)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 2, "getWidth should be 2, not %s" % str(x.getWidth())
        assert x.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert x.getWidthPackSpec() is '>H' , "getWidthPackSpec should be '>H'"
        assert x.getWidthPackLen() is 2, "getWidthPackLen should be 2"
        assert x.getType() == 'bevbuffer2', "getType should be bevbuffer2"
        assert x.getName() == 'bevbuffer2', "getName should be bevbuffer2"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"

        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0200
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=0x0201+2, len=0x0200+2, 0) should be 0"
        
        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0201
        assert x._isEnoughData(buffer, 0) == 0x0201 + 2, "_isEnoughData(clen=0x0201+2, len=0x0201+2, 0) should be 0x0102 + 2"
        
        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0201 + ' '
        assert x._isEnoughData(buffer, 0) == 0x0201 + 2, "_isEnoughData(clen=0x0201+2, len=0x0201+2, 0) should be 0x0102 + 2"

        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0201 + ' ' * 2  
        assert x._isEnoughData(buffer, 0) == 0x0201 + 2, "_isEnoughData(clen=0x0201+2, len=0x0201+2, 0) should be 0x0102 + 2"

        buffer = ' ' + chr(0x02) + chr(0x01) + ' ' * 0x0201
        assert x._isEnoughData(buffer, 1) == 0x0201 + 2, "_isEnoughData(clen=0x0201+2, len=0x0201+2, 1) should be 0x0102 + 2"

        buffer = '  ' + chr(0x02) + chr(0x01) + ' ' * 0x0201
        assert x._isEnoughData(buffer, 2) == 0x0201 + 2, "_isEnoughData(clen=0x0201+2, len=0x0201+2, 2) should be 0x0201 + 2"
     
        buffer = chr(0x02) + chr(0x01) + ' ' * 0x0201
        expval = ' ' * 0x0201     
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expected result"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0x0201 + 2, "_isEnoughData(0) should be 0x0201 + 2"

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 0x0201 + 2, "bytesConsumed(0) should be 0x0201 + 2"
        
        buffer = ' ' + chr(0x02) + chr(0x01) + ' ' * 0x0201
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0x0201 + 2, "_isEnoughData(1) should be 0x0201 + 2"
         
        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(1) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(1) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(1) should be 1"
        assert ismatchobj.bytesConsumed() == 0x0201 + 2, "bytesConsumed(1) should be 0x0201 + 2"

        buffer = chr(0xFF) + chr(0x01) + ' ' * 0xFF01
        expval = ' ' * 0x0FF01    
        retval = x._getValue(buffer, 0)
        assert retval == expval, "_getValue() did not return expval"
        retval = x._isEnoughData(buffer, 0)
        assert retval == 0xFF01 + 2, "_isEnoughData(0) should be 0xFF01 + 2"
        
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1"
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 0xFF01 + 2, "bytesConsumed(0) should be 0xFF01 + 2"

        buffer = ' ' + chr(0xFF) + chr(0x01) + ' ' * 0xFF01
        retval = x._isEnoughData(buffer, 1)
        assert retval == 0xFF01 + 2, "_isEnoughData(0) should be 0xFF01 + 2"

        # Test setValue() and dumpStr().
        buffer = ' ' * 0xFF01
        x.setValue(buffer)
        retval = x.dumpStr()
        expbuffer = chr(0xFF) + chr(0x01) + ' ' * 0xFF01       
        assert expbuffer == retval, "dumpStr() result did not match expected result."
        retval = x._getValue(expbuffer, 0)
        assert retval == ' ' * 0xFF01, "retval should be ' ' * 0xFF01, got %s instead." % str(retval)

    def test_case_fixed_buffer_with_child(self):
        class singlebyte(gd.BaseGDClass):
            def __init__(self):
                gd.BaseGDClass.__init__(self)
                #
                self._isFixed = 1
                self._width = 3
                self._num_items = 3
                self._isPackCompatible = 1
                self._packSpec = '<B<B<B'
                self.name = 'singlebyte'
                self.debug = 0
                #
                # Code to create item objects.
                self.items = []
                x = gd.IntItem(name="preamble", width=1, value=0xAA, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="data", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="postamble", width=1, value=0xFF, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)

        child_obj = singlebyte()

        x = gd.BufferItem(name="fbuffer01", width=3, isfixedwidth=1, ispack=0, widthispack=0, type="fbuffer", child_object=child_obj)

        assert x.isFixedWidth() == 1, "isFixedWidth() should return 1"
        assert x.getWidth() == 3, "getWidth() should return 3"
        assert x.isPackCompatible() == 0, "isPackCompatible() should return 0"
        assert x.packSpec() is None, "packSpec() should return None"

        assert x.findChildByName('fbuffer01') != None, "Should have been able to find fbuffer01"
        assert x.findChildByName('preamble') != None, "Should have been able to find preamble"
        assert x.findChildByName('data') != None, "Should have been able to find data"
        assert x.findChildByName('postamble') != None, "Should have been able to find postamble"

        assert x.findChildByName('bogus') == None, "Should not have been able to find bogus"

        data_obj = x.findChildByName('data')

        data_node = MockNode()

        data_obj.setNode(data_node)

        assert data_node.value is None, "data node's value should be None instead of %s" % str(data_node.value)
        assert data_node.last_read_time is None, "data node's last_read_time should be None"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=0, 0) should be 0"

        buffer = ' '
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=1, 0) should be 0"

        buffer = ' ' * 3
        assert x._isEnoughData(buffer, 0) == 3, "_isEnoughData(len=3, 0) should be 3"

        buffer = ' ' * 4
        assert x._isEnoughData(buffer, 0) == 3, "_isEnoughData(len=4, 0) should be 3"

        # Too short, no match
        buffer = chr(0xFF) * 2

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Right length, but no match
        buffer = chr(0xFF) * 3

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be 0 not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(0xAA)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed(0) should be 1 not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(0xAA) + chr(5)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed(0) should be 2 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 5, "getValue() should be 5 not %s" % str(data_obj.getValue())

        # @fixme: Probably the node values should not be updated until the whole response is matched.
        assert data_node.value == 5, "data node's value should be 5 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match
        buffer = chr(0xAA) + chr(6) + chr(0xFF)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"
        
        # A full match with an offset
        buffer = chr(0x00) + chr(0xAA) + chr(6) + chr(0xFF)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() is None, "getValue() should be None not %s" % str(data_obj.getValue())

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        # Test setValue() and dumpStr().
        res = x.dumpStr()
        exp_res = chr(0xAA) + chr(6) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."

        data_obj.setValue(0x33)
        
        res = x.dumpStr()
        exp_res = chr(0xAA) + chr(0x33) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."
    #
    def test_case_fixed_vbuffer1_with_child(self):
        class singlebyte(gd.BaseGDClass):
            def __init__(self):
                gd.BaseGDClass.__init__(self)
                #
                self._isFixed = 1
                self._width = 3
                self._num_items = 3
                self._isPackCompatible = 1
                self._packSpec = '<B<B<B'
                self.name = 'singlebyte'
                self.debug = 0
                #
                # Code to create item objects.
                self.items = []
                x = gd.IntItem(name="preamble", width=1, value=0xAA, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="data", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="postamble", width=1, value=0xFF, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)

        child_obj = singlebyte()

        x = gd.BufferItem(name='vbuffer1', type='vbuffer1', widthispack=1, widthpackspec="B", widthpacklen=1, child_object=child_obj)

        assert x.isFixedWidth() == 0, "isFixedWidth() should return 0"
        assert x.getWidth() == 1, "getWidth should be 1, not %s" % str(x.getWidth())
        assert x.isPackCompatible() == 0, "isPackCompatible() should return 0"
        assert x.packSpec() is None, "packSpec() should return None"
        assert x.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert x.getWidthPackSpec() is 'B' , "getWidthPackSpec should be 'B'"
        assert x.getWidthPackLen() is 1, "getWidthPackLen should be 1"

        assert x.findChildByName('vbuffer1') != None, "Should have been able to find vbuffer1"
        assert x.findChildByName('preamble') != None, "Should have been able to find preamble"
        assert x.findChildByName('data') != None, "Should have been able to find data"
        assert x.findChildByName('postamble') != None, "Should have been able to find postamble"
        assert x.findChildByName('bogus') == None, "Should not have been able to find bogus"

        data_obj = x.findChildByName('data')

        data_node = MockNode()

        data_obj.setNode(data_node)

        assert data_node.value is None, "data node's value should be None instead of %s" % str(data_node.value)
        assert data_node.last_read_time is None, "data node's last_read_time should be None"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"

        buffer = chr(3) + ' ' * 2
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=3+1, len=3, 0) should be 0"

        buffer = chr(3) + ' ' * 3
        assert x._isEnoughData(buffer, 0) == 4, "_isEnoughData(clen=3+1, len=4, 0) should be 4"

        buffer = chr(3) + ' ' * 4
        assert x._isEnoughData(buffer, 0) == 4, "_isEnoughData(clen=3+1, len=4, 0) should be 4"

        buffer = ' ' + chr(3) + ' ' * 3
        assert x._isEnoughData(buffer, 1) == 4, "_isEnoughData(clen=3+1, len=4, 1) should be 4"

        buffer = '  ' + chr(3) + ' ' * 2
        assert x._isEnoughData(buffer, 2) == 0, "_isEnoughData(clen=3+1, len=4, 2) should be 0"

        # Too short, no match
        buffer = chr(3) + chr(0xFF) * 2
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Right length, but no match.                                       
        buffer = chr(3) + chr(0xFF) * 3
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match 
        buffer = chr(3) + chr(0xAA)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed(0) should be 2 not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(3) + chr(0xAA) + chr(5)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 5, "getValue() should be 5 not %s" % str(data_obj.getValue())

        # @fixme: Probably the node values should not be updated until the whole response is matched.
        assert data_node.value == 5, "data node's value should be 5 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"


        # A full match
        buffer = chr(3) + chr(0xAA) + chr(6) + chr(0xFF)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match with more in the buffer afterwards
        buffer = chr(3) + chr(0xAA) + chr(6) + chr(0xFF) + chr(5) + chr(6) + chr(7)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match with an offset
        buffer = chr(0x01) + chr(3) + chr(0xAA) + chr(6) + chr(0xFF)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() is None, "getValue() should be None not %s" % str(data_obj.getValue())

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        # Test setValue() and dumpStr().
        res = x.dumpStr()
        exp_res = chr(3) + chr(0xAA) + chr(6) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."

        data_obj.setValue(0x33)
    
        res = x.dumpStr()
        exp_res = chr(3) + chr(0xAA) + chr(0x33) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."


    def test_case_levbuffer2_with_child(self):
        class singlebyte(gd.BaseGDClass):
            def __init__(self):
                gd.BaseGDClass.__init__(self)
                #
                self._isFixed = 1
                self._width = 3
                self._num_items = 3
                self._isPackCompatible = 1
                self._packSpec = '<B<B<B'
                self.name = 'singlebyte'
                self.debug = 0
                #
                # Code to create item objects.
                self.items = []
                x = gd.IntItem(name="preamble", width=1, value=0xAA, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="data", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="postamble", width=1, value=0xFF, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)

        child_obj = singlebyte()

        x = gd.BufferItem(name='levbuffer2', type='levbuffer2', widthispack=1, widthpackspec="<H", widthpacklen=2, child_object=child_obj)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.packSpec() is None, "packSpec() should return None"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 2, "getWidth should be 2, not %s" % str(x.getWidth())
        assert x.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert x.getWidthPackSpec() is '<H' , "getWidthPackSpec should be '<H'"
        assert x.getWidthPackLen() is 2, "getWidthPackLen should be 2"
        assert x.getType() == 'levbuffer2', "getType should be levbuffer2"
        assert x.getName() == 'levbuffer2', "getName should be levbuffer2"

        assert x.findChildByName('levbuffer2') != None, "Should have been able to find levbuffer2"
        assert x.findChildByName('preamble') != None, "Should have been able to find preamble"
        assert x.findChildByName('data') != None, "Should have been able to find data"
        assert x.findChildByName('postamble') != None, "Should have been able to find postamble"
        assert x.findChildByName('bogus') == None, "Should not have been able to find bogus"

        data_obj = x.findChildByName('data')

        data_node = MockNode()

        data_obj.setNode(data_node)

        assert data_node.value is None, "data node's value should be None instead of %s" % str(data_node.value)
        assert data_node.last_read_time is None, "data node's last_read_time should be None"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"

        buffer = chr(3) + chr(0) + ' ' * 2
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=2+2, len=4, 0) should be 0"

        buffer = chr(3) + chr(0) + ' ' * 3
        assert x._isEnoughData(buffer, 0) == 5, "_isEnoughData(clen=3+2, len=5, 0) should be 5"

        buffer = chr(3) + chr(0) + ' ' * 4
        assert x._isEnoughData(buffer, 0) == 5, "_isEnoughData(clen=3+2, len=5, 0) should be 5"

        buffer = ' ' + chr(3) + chr(0) + ' ' * 3
        assert x._isEnoughData(buffer, 1) == 5, "_isEnoughData(clen=3+2, len=5, 1) should be 5"

        buffer = '  ' + chr(3) + chr(0) + ' ' * 2
        assert x._isEnoughData(buffer, 2) == 0, "_isEnoughData(clen=2+2, len=4, 2) should be 0"

        # Too short, no match
        buffer = chr(3) + chr(0) + chr(0xFF) * 2
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Right length, but no match.                                       
        buffer = chr(3) + chr(0) + chr(0xFF) * 3
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(3) + chr(0) + chr(0xAA)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(3) + chr(0) + chr(0xAA) + chr(5)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 5, "getValue() should be 5 not %s" % str(data_obj.getValue())

        # @fixme: Probably the node values should not be updated until the whole response is matched.
        assert data_node.value == 5, "data node's value should be 5 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"


        # A full match
        buffer = chr(3) + chr(0) + chr(0xAA) + chr(6) + chr(0xFF)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 5, "bytesConsumed(0) should be 5 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match with more in the buffer afterwards
        buffer = chr(3) + chr(0) + chr(0xAA) + chr(6) + chr(0xFF) + chr(5) + chr(6) + chr(7)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 5, "bytesConsumed(0) should be 5 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match with an offset
        buffer = chr(0x01) + chr(3) + chr(0) + chr(0xAA) + chr(6) + chr(0xFF)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() is None, "getValue() should be None not %s" % str(data_obj.getValue())

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 5, "bytesConsumed(0) should be 5 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        # Test setValue() and dumpStr().
        res = x.dumpStr()
        exp_res = chr(3) + chr(0) + chr(0xAA) + chr(6) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."

        data_obj.setValue(0x33)
   
        res = x.dumpStr()
        exp_res = chr(3) + chr(0) + chr(0xAA) + chr(0x33) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."


    def test_case_bevbuffer2_with_child(self):
        class singlebyte(gd.BaseGDClass):
            def __init__(self):
                gd.BaseGDClass.__init__(self)
                #
                self._isFixed = 1
                self._width = 3
                self._num_items = 3
                self._isPackCompatible = 1
                self._packSpec = '<B<B<B'
                self.name = 'singlebyte'
                self.debug = 0
                #
                # Code to create item objects.
                self.items = []
                x = gd.IntItem(name="preamble", width=1, value=0xAA, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="data", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="postamble", width=1, value=0xFF, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)

        child_obj = singlebyte()

        x = gd.BufferItem(name='bevbuffer2', type='bevbuffer2', widthispack=1, widthpackspec=">H", widthpacklen=2, child_object=child_obj)

        assert x.isPackCompatible() == 0, "isPackCompatible should be 0"
        assert x.packSpec() is None, "packSpec() should return None"
        assert x.isFixedWidth() == 0, "isFixedWidth should be 0"
        assert x.getWidth() == 2, "getWidth should be 2, not %s" % str(x.getWidth())
        assert x.getWidthIsPack() is 1, "getWidthIsPack should be 1"
        assert x.getWidthPackSpec() is '>H' , "getWidthPackSpec should be '>H'"
        assert x.getWidthPackLen() is 2, "getWidthPackLen should be 2"
        assert x.getType() == 'bevbuffer2', "getType should be bevbuffer2"
        assert x.getName() == 'bevbuffer2', "getName should be bevbuffer2"

        assert x.findChildByName('bevbuffer2') != None, "Should have been able to find levbuffer2"
        assert x.findChildByName('preamble') != None, "Should have been able to find preamble"
        assert x.findChildByName('data') != None, "Should have been able to find data"
        assert x.findChildByName('postamble') != None, "Should have been able to find postamble"
        assert x.findChildByName('bogus') == None, "Should not have been able to find bogus"

        data_obj = x.findChildByName('data')

        data_node = MockNode()

        data_obj.setNode(data_node)

        assert data_node.value is None, "data node's value should be None instead of %s" % str(data_node.value)
        assert data_node.last_read_time is None, "data node's last_read_time should be None"

        buffer = ''
        assert x._isEnoughData(buffer, 0) == -1, "_isEnoughData(len=0, 0) should be -1"

        buffer = chr(0) + chr(3) + ' ' * 2
        assert x._isEnoughData(buffer, 0) == 0, "_isEnoughData(clen=2+2, len=4, 0) should be 0"

        buffer = chr(0) + chr(3) + ' ' * 3
        assert x._isEnoughData(buffer, 0) == 5, "_isEnoughData(clen=3+2, len=5, 0) should be 5"

        buffer = chr(0) + chr(3) + ' ' * 4
        assert x._isEnoughData(buffer, 0) == 5, "_isEnoughData(clen=3+2, len=5, 0) should be 5"

        buffer = ' ' + chr(0) + chr(3) + ' ' * 3
        assert x._isEnoughData(buffer, 1) == 5, "_isEnoughData(clen=3+2, len=5, 1) should be 5"

        buffer = '  ' + chr(0) + chr(3) + ' ' * 2
        assert x._isEnoughData(buffer, 2) == 0, "_isEnoughData(clen=2+2, len=4, 2) should be 0"

        # Too short, no match
        buffer = chr(0) + chr(3) + chr(0xFF) * 2
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Right length, but no match.                                       
        buffer = chr(0) + chr(3) + chr(0xFF) * 3
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(0) + chr(3) + chr(0xAA)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(0) + chr(3) + chr(0xAA) + chr(5)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 4, "bytesConsumed(0) should be 4 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 5, "getValue() should be 5 not %s" % str(data_obj.getValue())

        # @fixme: Probably the node values should not be updated until the whole response is matched.
        assert data_node.value == 5, "data node's value should be 5 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"


        # A full match
        buffer = chr(0) + chr(3) + chr(0xAA) + chr(6) + chr(0xFF)
        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 5, "bytesConsumed(0) should be 5 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match with more in the buffer afterwards
        buffer = chr(0) + chr(3) + chr(0xAA) + chr(6) + chr(0xFF) + chr(5) + chr(6) + chr(7)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 5, "bytesConsumed(0) should be 5 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match with an offset
        buffer = chr(0x01) + chr(0) + chr(3) + chr(0xAA) + chr(6) + chr(0xFF)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)

        ismatchobj = x.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() is None, "getValue() should be None not %s" % str(data_obj.getValue())

        ismatchobj = x.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 5, "bytesConsumed(0) should be 5 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        # Test setValue() and dumpStr().
        res = x.dumpStr()
        exp_res = chr(0) + chr(3) + chr(0xAA) + chr(6) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."

        data_obj.setValue(0x33)
   
        res = x.dumpStr()
        exp_res = chr(0) + chr(3) + chr(0xAA) + chr(0x33) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."
    
    def test_case_fixed_compound_objects(self):
        class singlebyte(gd.BaseGDClass):
            def __init__(self):
                gd.BaseGDClass.__init__(self)
                #
                self._isFixed = 1
                self._width = 3
                self._num_items = 3
                self._isPackCompatible = 1
                self._packSpec = '<B<B<B'
                self.name = 'singlebyte'
                self.debug = 0
                #
                # Code to create item objects.
                self.items = []
                x = gd.IntItem(name="preamble", width=1, value=0xAA, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="data", width=1, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)
                #
                x = gd.IntItem(name="postamble", width=1, value=0xFF, packspec="<B", ispack=1, widthispack=0, type="uint8", debug=0)
                self.items.append(x)

        # Manually build up a compound object.
        compound_obj = gd.BaseGDClass()

        compound_obj.name = 'CompoundObject'
        compound_obj._isFixed = 1
        compound_obj._width = 3
        compound_obj._num_items = 1
        compound_obj._isPackCompatible = 0
        compound_obj._packSpec = None
        #
        # Code to create item objects.
        compound_obj.items = []
        child_obj = singlebyte()

        #print 'dir of singlebyte'
        #print dir(singlebyte)

        x = gd.BufferItem(name="fbuffer01", width=3, isfixedwidth=1, ispack=0, widthispack=0, type="fbuffer", child_object=child_obj)
        compound_obj.items.append(x)

        #print 'dir of compound_obj'
        #print dir(compound_obj)

        #print 'str of compound_obj'
        #print str(compound_obj)

        assert compound_obj.isFixedWidth() == 1, "isFixedWidth() should return 1"
        assert compound_obj.getWidth() == 3, "getWidth() should return 3"
        assert compound_obj.isPackCompatible() == 0, "isPackCompatible() should return 0"
        assert compound_obj.packSpec() is None, "packSpec() should return None"
        assert compound_obj.getNumItems() == 1, "getNumItems() should return 1"

        assert compound_obj.findChildByName('fbuffer01') != None, "Should have been able to find fbuffer01"
        assert compound_obj.findChildByName('preamble') != None, "Should have been able to find preamble"
        assert compound_obj.findChildByName('data') != None, "Should have been able to find data"
        assert compound_obj.findChildByName('postamble') != None, "Should have been able to find postamble"

        assert compound_obj.findChildByName('bogus') == None, "Should not have been able to find bogus"

        data_obj = compound_obj.findChildByName('data')

        data_node = MockNode()

        data_obj.setNode(data_node)

        assert data_node.value is None, "data node's value should be None instead of %s" % str(data_node.value)
        assert data_node.last_read_time is None, "data node's last_read_time should be None"

        buffer = ''
        assert compound_obj._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=0, 0) should be 0"

        buffer = ' '
        assert compound_obj._isEnoughData(buffer, 0) == 0, "_isEnoughData(len=1, 0) should be 0"

        buffer = ' ' * 3
        assert compound_obj._isEnoughData(buffer, 0) == 3, "_isEnoughData(len=3, 0) should be 3"

        buffer = ' ' * 4
        assert compound_obj._isEnoughData(buffer, 0) == 3, "_isEnoughData(len=4, 0) should be 3"

        # Too short, no match
        buffer = chr(0xFF) * 2

        ismatchobj = compound_obj.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Right length, but no match
        buffer = chr(0xFF) * 3

        ismatchobj = compound_obj.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0"
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(0xAA)

        ismatchobj = compound_obj.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 1, "bytesConsumed(0) should be 1 not %s" % str(ismatchobj.bytesConsumed())

        # Too short, start of a match
        buffer = chr(0xAA) + chr(5)

        ismatchobj = compound_obj.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 2, "bytesConsumed(0) should be 2 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 5, "getValue() should be 5 not %s" % str(data_obj.getValue())

        # @fixme: Probably the node values should not be updated until the whole response is matched.
        assert data_node.value == 5, "data node's value should be 5 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"

        # A full match
        buffer = chr(0xAA) + chr(6) + chr(0xFF)

        ismatchobj = compound_obj.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        assert data_node.value == 6, "data node's value should be 6 instead of %s" % str(data_node.value)
        assert data_node.last_read_time is not None, "data node's last_read_time should not be None"
        
        # A full match with an offset
        buffer = chr(0x00) + chr(0xAA) + chr(6) + chr(0xFF)

        #print 'expval', util.dump_binary_str(expval)
        #print 'retval', util.dump_binary_str(retval)

        ismatchobj = compound_obj.isMatch(buffer, 0)
        assert ismatchobj.isMatch() == 0, "isMatch(0) should be 0 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 1, "isNotMatch(0) should be 1"
        assert ismatchobj.isPotentialMatch() == 0, "isPotentialMatch(0) should be 0"
        assert ismatchobj.bytesConsumed() is None, "bytesConsumed(0) should be None not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() is None, "getValue() should be None not %s" % str(data_obj.getValue())

        ismatchobj = compound_obj.isMatch(buffer, 1)
        assert ismatchobj.isMatch() == 1, "isMatch(0) should be 1 not %s" % str(ismatchobj)
        assert ismatchobj.isNotMatch() == 0, "isNotMatch(0) should be 0"
        assert ismatchobj.isPotentialMatch() == 1, "isPotentialMatch(0) should be 1"
        assert ismatchobj.bytesConsumed() == 3, "bytesConsumed(0) should be 3 not %s" % str(ismatchobj.bytesConsumed())

        assert data_obj.getValue() == 6, "getValue() should be 6 not %s" % str(data_obj.getValue())

        # Test setValue() and dumpStr().
        res = compound_obj.dumpStr()
        exp_res = chr(0xAA) + chr(6) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."

        data_obj.setValue(0x33)
        
        res = compound_obj.dumpStr()
        exp_res = chr(0xAA) + chr(0x33) + chr(0xFF)
        assert exp_res == res, "dumpStr() result did not match expected result."
        
 
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        

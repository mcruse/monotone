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
from mpx_test import DefaultTestFixture, main

import time
import array
import array
import struct
import random

from mpx.lib.exceptions import EOverflow
from mpx.lib.exceptions import EInvalidValue

from mpx.lib.modbus.conversions import ConvertRegister, ConvertValue, ConvertBitField
from mpx.lib.modbus.base import buffer as _buffer

rand = random.Random(42)

class TestCase(DefaultTestFixture):
    def _test_register_conversions(self, orders, limit=6500):
        for i in range(0,limit):
            ir = rand.randrange(0, 65535)
            cv = ConvertValue()
            cv.convert_ushort(ir, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_word(0, 0, orders)
            if ir != j:
                raise 'WORD conversion failed'

            ir = rand.randrange(-32767, 32767)
            cv = ConvertValue()
            cv.convert_short(ir, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_int(0,0, orders)
            if ir != j:
                raise 'INT conversions failed'
            
            irh = rand.randrange(-127,127)
            cvh = ConvertValue()
            cvh.convert_hiint(irh, orders)
            irl = rand.randrange(-127,127)
            cvl = ConvertValue()
            cvl.convert_loint(irl, orders)

            for k in [0,1]:
                cvh.buffer[k] |= cvl.buffer[k]

            cr = ConvertRegister(cvh.buffer)
            j = cr.register_as_loint(0,0, orders)
            if irl != j:
                raise 'LO INT conversion failed'
            j = cr.register_as_hiint(0,0, orders)
            if irh != j:
                raise 'HI INT conversion failed'

            irh = chr(rand.randrange(0,255))
            cvh = ConvertValue()
            cvh.convert_hichar(irh, orders)
            irl = chr(rand.randrange(0,255))
            cvl = ConvertValue()
            cvl.convert_lochar(irl, orders)

            for k in [0,1]:
                cvh.buffer[k] |= cvl.buffer[k]

            cr = ConvertRegister(cvh.buffer)
            j = cr.register_as_lochar(0,0, orders)
            if irl != j:
                raise 'LO CHR conversion failed'
            j = cr.register_as_hichar(0,0, orders)
            if irh != j:
                raise 'HI CHR conversion failed'
            
            fr = rand.random()
            cv = ConvertValue()
            cv.convert_float(fr, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_float(0,0, orders)
            if abs(fr - j) > 0.0001:
                raise 'FLOAT conversions failed'

            fr = rand.random()
            cv = ConvertValue()
            cv.convert_float8(fr, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_float8(0,0, orders)
            if abs(fr - j) > 0.0000001:
                raise 'FLOAT8 conversions failed'

            ir = long(fr * float(4294967296))
            cv = ConvertValue()
            cv.convert_ulong(ir, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_ulong(0, 0, orders)
            if ir != j:
                raise 'ULONG conversion failed'

            ir = ir - 2147483648
            cv = ConvertValue()
            cv.convert_long(ir, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_long(0,0, orders)
            if ir != j:
                raise 'LONG conversions failed ' + str(ir) + '  ' + str(j)
            
            fr = rand.random()
            cv = ConvertValue()
            cv.convert_encorp_real_2(fr, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_encorp_real_2(0, 0, orders)
            if abs(fr - j) > 0.0001:
                raise 'ENCORP REAL conversions failed (v1=%r,v2=%r)' % (fr,j)
           
            fr = rand.random()
            cv = ConvertValue()
            t = time.time()
            t = t + (1000000 * fr)
            
            cv.convert_time_6(t, orders)
            cr = ConvertRegister(cv.buffer)
            j = cr.register_as_time_6(0, 0, orders)
            if abs(int(t) - j) > 1:
                raise 'TIME 6 conversions failed (v1=%r,v2=%r)' % (t,j)

    def test_normal_order_conversions(self):
        self._test_register_conversions(0)
    def test_reversed_byte_order_conversions(self):
        self._test_register_conversions(1, 3200)
    def test_reversed_word_order_conversions(self):
        self._test_register_conversions(2, 3200)
    def test_reversed_word_and_byte_order_conversions(self):
        self._test_register_conversions(3, 1000)
    def test_reversed_bit_order_conversions(self):
        self._test_register_conversions(4, 3200)
        self._test_register_conversions(7, 1000)

    def test_bit_field_conversions(self):
        ibl = []
        cv = ConvertValue()
        for i in range(0,32):
            ib = rand.randrange(0, 2)
            cv.convert_bits(ib)
            ibl.append(ib)
        cr = ConvertBitField(_buffer(cv.collapsed_buffer()))
        for i in range(0,32):
            j = cr.status(i)
            if ibl[i] != j:
                raise 'BIT conversion failed'
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

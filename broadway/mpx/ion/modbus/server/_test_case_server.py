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

##
# Test cases to exercise the property classes.
#

from mpx.lib.exceptions import EOverflow
from mpx.lib.exceptions import EInvalidValue

import array
import struct
import server
from mpx.ion.modbus import generic
from mpx.ion.modbus.server import server
from mpx.lib.modbus.base import buffer as _buffer
from mpx.ion.host import eth
from mpx.ion.host.eth import ip
import random

rand = random.Random(42)

class TestCase(DefaultTestFixture):
    def __init__(self, other):
        DefaultTestFixture.__init__(self, other)
        self.eth0 = None
        self.ip = None
        self.server = None
        self.client = None
    
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.eth0 = eth.factory()
        self.eth0.configure({'name':'eth0', 'parent':None, 'dev':'eth0'})
        self.ip = ip.factory()
        self.ip.configure({'name':'ip', 'parent':self.eth0})
        self.server = server.ServerDevice()
        self.server.configure({'name':'server', 'parent':self.ip,
                               'address':255})
        return
    def tearDown(self):
        try:
            if hasattr(self,'server'):
                del self.server
            if hasattr(self,'client'):
                del self.client
            if hasattr(self,'ip'):
                del self.ip
            if hasattr(self,'eth0'):
                del self.eth0
        finally:
            DefaultTestFixture.tearDown(self)
        return

    def test_create_server_device(self):
        return
    def test_add_holding_register_1(self):
        hr = server.HoldingRegister()
        hr.configure({'name':'eth0',
                      'parent':self.server,
                      'register':'40001',
                      'type':'int', 
                      'length':'1',
                      'read_only':'0'})
        self.eth0.start()
        for v in (0,1,-1,555,-555, 32767, -32767):
            hr.set(v)
            b = hr.read(0)
            bv = b[0] * 256 + b[1]
            if bv >= 32768:
                bv = ((bv ^ 0xFFFF) + 1) * -1
            if v != bv:
                raise 'bad value conversion for int holding register'

        for v in (0,1,-1,555,-555, 32767, -32767):
            bv = v
            if bv < 0:
                bv = (bv ^ 0xFFFF + 1) & 0xFFFF
            b[0] = bv / 256
            b[1] = bv % 256
            hr.buffer = b
            hr.write(0, b.tostring())
            if v != hr.get():
                raise 'bad buffer conversion for int holding register'
    def test_add_holding_register_2(self):
        hr = server.HoldingRegister()
        hr.configure({'name':'eth0',
                      'parent':self.server,
                      'register':'40001',
                      'type':'int', 
                      'length':'2',
                      'read_only':'0'})
        self.eth0.start()
        for v in (0,1,-1,555,-555, 32767, -32767, 65535, -65535, 65536, -65536,
                  0x7FFFFFFF, -1):
            hr.set(v)
            b = hr.read(0)+hr.read(1)
            bv = struct.unpack('!l',b.tostring())[0]
            if v != bv:
                raise (
                    "bad value conversion for int holding register"
                    " (expected %r, got %r)" % (v, bv)
                    )
        for v in (0,1,-1,555,-555, 32767, -32767, 65535, -65535, 65536, -65536,
                  0x7FFFFFFF, -1):
            bv = v
            b = array.array('l', struct.pack('!l', bv))
            hr.write(0, b.tostring())
            hv = hr.get()
            if v != hv:
                raise (
                    "bad buffer conversion for int holding register"
                    " (expected %r, got %r)" % (v, hv)
                    )
    def test_holding_register_float_4(self):
        hr = server.HoldingRegister()
        hr.configure({'name':'eth0',
                      'parent':self.server,
                      'register':'40001',
                      'type':'IEEE float', 
                      'length':'2',
                      'read_only':'0'})
        self.eth0.start()
        for i in range(0,100):
            v = rand.random()
            hr.set(v)
            b = hr.read(0)+hr.read(1)
            bv = struct.unpack('!f',b.tostring())[0]
            if abs(v - bv) >  0.0001:
                print v, bv
                raise 'bad value conversion for float holding register'

        for i in range(0,100):
            v = rand.random()
            b = array.array('f', struct.pack('!f', v))
            hr.write(0, b.tostring())
            if abs(v - hr.get()) >  0.0001:
                raise 'bad buffer conversion for float holding register'

    def test_holding_register_float_8(self):
        hr = server.HoldingRegister()
        hr.configure({'name':'eth0',
                      'parent':self.server,
                      'register':'40001',
                      'type':'IEEE float', 
                      'length':'4',
                      'read_only':'0'})
        self.eth0.start()
        for i in range(0,100):
            v = rand.random()
            hr.set(v)
            b = hr.read(0)+hr.read(1)+hr.read(2)+hr.read(3)
            bv = struct.unpack('!d',b.tostring())[0]
            if abs(v - bv) >  0.00000001:
                print v, bv
                raise 'bad value conversion for float holding register'

        for i in range(0,100):
            v = rand.random()
            b = array.array('d', struct.pack('!d', v))
            hr.write(0, b.tostring())
            if abs(v - hr.get()) >  0.00000001:
                raise 'bad buffer conversion for float holding register'

# @fixme Why is this commented block here?            
#'hibyte' :{1:(ConvertRegister.register_hibyte, ConvertValue.convert_hibyte)},
#'lobyte' :{1:(ConvertRegister.register_lobyte, ConvertValue.convert_lobyte)},
#'loint'  :{1:(ConvertRegister.register_as_loint, ConvertValue.convert_loint)},
#'hiint'  :{1:(ConvertRegister.register_as_hiint, ConvertValue.convert_hiint)},
#'lochar' :{1:(ConvertRegister.register_as_lochar, ConvertValue.convert_lochar)},
#'hichar' :{1:(ConvertRegister.register_as_hichar, ConvertValue.convert_hichar)},
#'word'   :{1:(ConvertRegister.register_as_word, ConvertValue.convert_ushort)},
#'dword'  :{2:(ConvertRegister.register_as_ulong, ConvertValue.convert_ulong)},
#'string' :{0:(ConvertRegister.register_as_string, ConvertValue.convert_string)},
#'zstring':{0:(ConvertRegister.register_as_zstring, ConvertValue.convert_zstring)},
#'modulo' :{1:(ConvertRegister.register_as_modulo_10000_1, ConvertValue.convert_modulo_1),
#2:(ConvertRegister.register_as_modulo_10000_2, ConvertValue.convert_modulo_2),
#3:(ConvertRegister.register_as_modulo_10000_3, ConvertValue.convert_modulo_3),
#4:(ConvertRegister.register_as_modulo_10000_4, ConvertValue.convert_modulo_4)},
#'PowerLogic Energy':{3:(ConvertRegister.register_as_power_logic_3, ConvertValue.convert_power_logic_3),
#4:(ConvertRegister.register_as_power_logic_4, ConvertValue.convert_power_logic_4)},
#'time'   :{3:(ConvertRegister.register_as_time_3, ConvertValue.convert_time_3),
#6:(ConvertRegister.register_as_time_6, ConvertValue.convert_time_6)}}

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

"""
Copyright (C) 2002 2004 2007 2010 2011 Cisco Systems

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
# TODO:
# 1. Add the remaining write_types.

import struct, time
from command import PresetSingleRegister, ReadHoldingRegisters, ForceSingleCoil, PresetMultipleRegisters
from conversions import ConvertValue

class CacheWriter:
    def __init__(self, cache):
        self.cache = cache

    def write_hibyte(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        value  &= 0xFF
        cache   = self.cache
        slave_address = cache.slave_address
        lh      = cache.lh
        rsp     = lh.command(ReadHoldingRegisters(slave_address, reg, 1))
        word    = (rsp.register_lobyte(0,0,orders) & 0x00FF) | (value << 8)
        self.write_word(reg, word, orders)

    def write_lobyte(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        value  &= 0xFF
        cache   = self.cache
        slave_address = cache.slave_address
        lh      = cache.lh
        rsp     = lh.command(ReadHoldingRegisters(slave_address, reg, 1))
        word    = (rsp.register_hibyte(0,0,orders) << 8) | value
        self.write_word(reg, word, orders)

    def write_loint(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        if value < 0: #convert to twos complement
            value = -value
            value = (value - 1) ^ 0xFF
        self.write_lobyte(reg, value, orders)
        
    def write_hiint(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        if value < 0: #convert to twos complement
            value = -value
            value = (value - 1) ^ 0xFF
        self.write_hibyte(reg, value, orders)
        
    def write_word(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        cache   = self.cache
        slave_address = cache.slave_address
        lh      = cache.lh
        if orders & 1: #swap bytes
            temp = value & 0xFF00
            value = (value << 8) + (temp >> 8)
        value &= 0x0FFFF
        lh.command(PresetSingleRegister(slave_address, reg, value))

    def write_int(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        if value < 0: #convert to twos complement
            value = -value
            value = (value - 1) ^ 0xFFFF
        self.write_word(reg, value, orders)

    def write_dword(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        if orders & 2: #reverse
            self.write_word(reg, value & 0xFFFF, orders)
            self.write_word(reg+1, value>>16 & 0xFFFF, orders)
        else:
            self.write_word(reg, value>>16 & 0xFFFF, orders)
            self.write_word(reg+1, value & 0xFFFF, orders)

    def write_long(self, reg, value, orders=0):
        if not isinstance(value, long):
            value = long(value)
        if value < 0: #convert to twos complement
            value = -value
            value = (value - 1) ^ 0xFFFFFFFFL
        self.write_dword(reg, value, orders)
        
    def write_float(self, reg, value, orders=0):
        if not isinstance(value, float):
            value = float(value)
        s = struct.pack('!f', value)
        h = struct.unpack('!HH', s)
        b = (orders >> 1) & 1
        self.write_word(reg, h[b], orders)
        self.write_word(reg+1, h[b^1], orders)

    def write_double(self, reg, value, orders=0):
        if not isinstance(value, float):
            value = float(value)
        s = struct.pack('!d', value)
        h = struct.unpack('!HHHH', s)
        b = 0
        if (orders >> 1) & 1:
            b = 3
        self.write_word(reg,   h[b], orders)
        self.write_word(reg+1, h[b^1], orders)
        self.write_word(reg+2, h[b^2], orders)
        self.write_word(reg+3, h[b^3], orders)

    def write_coil(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        cache = self.cache
        slave_address = cache.slave_address
        lh = cache.lh
        lh.command(ForceSingleCoil(slave_address, reg, value))

    def write_modulo_1(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        self.write_int(reg, value % 10000L, orders)

    def write_modulo_2(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        self.write_modulo_1(reg, value / 10000L, orders)
        self.write_modulo_1(reg + 1, value, orders)

    def write_modulo_3(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        self.write_modulo_2(reg, value / 10000L, orders)
        self.write_modulo_1(reg + 2, value, orders)

    def write_modulo_4(self, reg, value, orders=0):
        if not isinstance(value, int):
            value = int(value)
        self.write_modulo_3(reg, value / 10000L, orders)
        self.write_modulo_1(reg + 3, value, orders)

    def write_power_logic_3(self, reg, value, orders=0):
        if not isinstance(value, long):
            value = long(value)
        self.write_modulo_3(reg, long(value * 1000), orders)

    def write_power_logic_4(self, reg, value, orders=0):
        if not isinstance(value, long):
            value = long(value)
        self.write_modulo_4(reg, long(value * 1000), orders)

    def write_time_3(self, reg, time_value, orders=0):
        tt = time.localtime(time_value)
        self.write_word(reg,    tt[1]*256 + tt[2], orders)
        self.write_word(reg+1, (tt[0]-1900)*256 + tt[3], orders)
        self.write_word(reg+2,  tt[4]*256 + tt[5], orders)

    def write_time_6(self, reg, time_value, orders=0):
        #tt = time.localtime(time_value)
        ##print 'write_time_6 ', tt
        #self.write_word(reg,   tt[5], orders)
        #self.write_word(reg+1, tt[4], orders)
        #self.write_word(reg+2, tt[3], orders)
        #self.write_word(reg+3, tt[2], orders)
        #self.write_word(reg+4, tt[1], orders)
        #self.write_word(reg+5, tt[0], orders)

        cv = ConvertValue()
        cv.convert_time_6(time_value, orders)

        cache   = self.cache
        slave_address = cache.slave_address
        lh      = cache.lh
        lh.command(PresetMultipleRegisters(slave_address, reg, cv.buffer))

    def write_dl06_energy_4(self, reg, value, orders=0):
        self.write_dword(reg, long(value) / 1000L, orders)
        self.write_float(reg+2, value % 1000.0, orders)

    def write_encorp_real_2(self, reg, value, orders=0):
        whole = int(value)
        self.write_int(reg, whole, orders)
        fraction = abs(value)
        fraction = fraction - int(fraction)
        fraction = int(fraction * 65536.0)
        self.write_word(reg+1, fraction, orders)
        return
    def write_string(self, reg, value, orders=0):
        cv = ConvertValue()
        cv.convert_string(value, orders)
        cache   = self.cache
        slave_address = cache.slave_address
        lh      = cache.lh
        lh.command(PresetMultipleRegisters(slave_address, reg, cv.buffer))
    def write_zstring(self, reg, value, orders=0):
        cv = ConvertValue()
        cv.convert_zstring(value, orders)
        cache   = self.cache
        slave_address = cache.slave_address
        lh      = cache.lh
        lh.command(PresetMultipleRegisters(slave_address, reg, cv.buffer))
    



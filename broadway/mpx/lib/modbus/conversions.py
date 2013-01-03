"""
Copyright (C) 2002 2004 2008 2010 2011 Cisco Systems

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
# 2.  register_as_dword is currently treated as a signed value...

import array, struct, time

from mpx.lib.debug import dump_ints_tostring, dump_tostring, dump
from mpx.lib.modbus.base import buffer as _buffer

def bytes_outstanding(response, header):
    # header[2] - (len(header) - 3) + 2
    # reduces to: (NOTE: len(header) is USUALLY 5,
    #              so "return header[2]" is ALMOST right)
    n = response.byte_count = header[2]
    return n - len(header) + 5

class ConvertBuffer:
    def __init__(self, buffer, offset=0):
        self.buffer = buffer
        self.data = self.buffer
        self.offset = offset
        return
    def get_byte(self, offset, buffer=None):
        if not buffer:
            buffer = self.buffer
        return buffer[offset]
    def get_word(self, offset, buffer=None):
        if not buffer:
            buffer = self.buffer
        result = buffer[offset] << 8
        result += buffer[offset+1]
        return result

class ConvertRegister(ConvertBuffer):
    def __init__(self, buffer, offset=0):
        ConvertBuffer.__init__(self, buffer, offset=0)
        data = []
        for i in range(0, len(self.buffer)/2):
            data.append(self.get_word(i*2))
        self.data = data
        return
    def __str__(self):
        result = array.array('c')
        if self.data:
            result.fromstring(dump_ints_tostring(self.data, 'data:       '))
        return result.tostring()
    def data_index(self, reg, start, orders=0):
        return reg-start
    def buffer_offset(self, reg, start, orders=0):
        return (reg-start)*2 #0 based indexing
    def register(self, reg, start=0, orders=0):
        return register_as_word(reg, start, orders)
    def byte_to_int(self, byte):
        #"Converts an unsigned byte to a signed value."
        result = byte
        if result & 0x80:
            result = (result ^ 0xFF) + 1
            return -result
        return result
    def register_as_word(self, reg, start=0, orders=0):
        #"Return a single register as a positive integer."
        answer = self.data[self.data_index(reg,start)]
        if orders & 1: answer = swap_bytes(answer) 
        return answer
    def register_as_int(self, reg, start=0, orders=0):
        #"Return a single register as a signed integer value."
        answer = self.register_as_word(reg, start, orders)
        if answer & 0x8000:
            answer = (answer ^ 0xFFFF) + 1
            return -answer
        return answer
    def register_as_ulong(self, reg, start=0, orders=0):
        "Return two consecutive registers as a positive integer."
        l1 = self.register_as_word(reg, start, orders)
        l2 = self.register_as_word(reg + 1, start, orders)
        if orders & 2:
            long = l2 << 16L
            long |= l1
        else:
            long = l1 << 16L
            long |= l2
        return long & 0x00000000FFFFFFFFL
    def register_as_long(self, reg, start=0, orders=0):
        "Return two consecutive registers as a signed integer."
        answer = self.register_as_ulong(reg, start, orders)
        if answer & 0x80000000L:
            answer = (answer ^ 0x00000000FFFFFFFFL) + 1
            return -answer
        return answer
    def register_hibyte(self, reg, start=0, orders=0):
        answer = self.register_as_word(reg, start, orders)
        return answer >> 8
    def register_lobyte(self, reg, start=0, orders=0):
        answer = self.register_as_word(reg, start, orders)
        return answer & 255
    def register_as_loint(self, reg, start=0, orders=0):
        return self.byte_to_int(self.register_lobyte(reg, start, orders))
    def register_as_hiint(self, reg, start=0, orders=0):
        return self.byte_to_int(self.register_hibyte(reg, start, orders))
    def register_as_lochar(self, reg, start=0, orders=0):
        return chr(self.register_lobyte(reg, start, orders))
    def register_as_hichar(self, reg, start=0, orders=0):
        return chr(self.register_hibyte(reg, start, orders))
    def register_as_float(self, reg, start=0, orders=0):
        # No doubt there is a better way to do this...
        s = self.register_as_string(reg, 4, start, orders)
        return struct.unpack('!f', s)[0]
    def register_as_float8(self, reg, start=0, orders=0):
        # No doubt there is a better way to do this...
        s = self.register_as_string(reg, 8, start, orders)
        return  struct.unpack('!d', s)[0]
#
# change bit assignments to allow xor to auto fix address

    def register_as_string(self, reg, byte_count, start=0, orders=0):
        string = array.array('c')
        istart = self.buffer_offset(reg,start)
        buffer = self.buffer
        #for i in range(istart, istart+byte_count):
        for i in range(0, byte_count):
            string.append(chr(buffer[istart + (i ^ (orders & 3))]))
        return string.tostring()
    def register_as_zstring(self, reg, byte_count, start=0, orders=0):
        string = array.array('c')
        istart = self.buffer_offset(reg,start)
        buffer = self.buffer
        #for i in range(istart, istart+byte_count):
        for i in range(0, byte_count):
            x = buffer[istart + (i ^ (orders & 3))]
            if x == 0:
                return string.tostring()
            string.append(chr(x))
        return string.tostring()
    def register_as_modulo_10000_1(self, reg, start=0, orders=0):
        return long(self.register_as_word(reg, start, orders) % 10000L)
    def register_as_modulo_10000_2(self, reg, start=0, orders=0):
        return (
            (self.register_as_modulo_10000_1(reg + 1, start, orders) * 10000L) +
            self.register_as_modulo_10000_1(reg, start, orders))
    def register_as_modulo_10000_3(self, reg, start=0, orders=0):
        return (
            (self.register_as_modulo_10000_2(reg + 1, start, orders) * 10000L) +
            self.register_as_modulo_10000_1(reg , start, orders))
    def register_as_modulo_10000_4(self, reg, start=0, orders=0):
        return (
            (self.register_as_modulo_10000_3(reg + 1, start, orders) * 10000L) +
            self.register_as_modulo_10000_1(reg, start, orders))
    def register_as_power_logic_3(self, reg, start=0, orders=0):
        return (
            float(self.register_as_modulo_10000_3(reg, start, orders)) / 1000.0
            )
    # The return statement isn't pretty, but allows us to deal with large
    # values, ie. 9,999,999,999,999,999 - that are cooerced to floats
    def register_as_power_logic_4(self, reg, start=0, orders=0):
        answer = self.register_as_modulo_10000_4(reg, start, orders)
        return float('%d.%03d' % (answer // 1000, answer % 1000))
    def register_as_time_3(self, reg, start=0, orders=0):
        md = self.register_as_word(reg, start, orders)
        month = md / 256
        day = md & 255
        yh = self.register_as_word(reg + 1, start, orders)
        year = yh / 256
        hour = yh & 255
        ms = self.register_as_word(reg + 2, start, orders)
        minute = ms / 256
        second = ms & 255
        time_tuple=(year + 1900, month, day, hour, minute, second, 0,0,-1)
        #print 'register_as_time_3 ', time_tuple
        return time.mktime(time_tuple)        
    def register_as_time_6(self, reg, start=0, orders=0):
        second = self.register_as_word(reg,     start, orders)
        minute = self.register_as_word(reg + 1, start, orders)
        hour   = self.register_as_word(reg + 2, start, orders)
        day    = self.register_as_word(reg + 3, start, orders)
        month  = self.register_as_word(reg + 4, start, orders)
        year   = self.register_as_word(reg + 5, start, orders)
        time_tuple=[year, month, day, hour, minute, second]
        if orders & 2:
            time_tuple.reverse()
        time_tuple.extend([0,0,-1])
        time_tuple = tuple(time_tuple)
        #print 'register_as_time_6 ', time_tuple
        return time.mktime(time_tuple)
    def register_as_dl06_energy_4(self, reg, start=0, orders=0):
        megawatts = self.register_as_ulong(reg, start, orders)
        kilowatts = self.register_as_float(reg + 2, start, orders)
        return (megawatts * 1000.0) + kilowatts
    def register_as_encorp_real_2(self, reg, start=0, orders=0):
        whole = self.register_as_int(reg, start, orders)
        fraction = self.register_as_word(reg + 1, start, orders)
        result = whole + (fraction / 65536.0)
        return result

class ConvertBitField(ConvertBuffer):
    def __init__(self, buffer):
        ConvertBuffer.__init__(self, buffer)
        self.buffer = buffer
        return
    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:    0x%02X\nfunction:   0x%02X\n' %
                          (self.slave_address, self.function))
        result.fromstring('byte_count: 0x%02X\n' % self.byte_count)
        result.fromstring('crc:        0x%04X\n' % self.crc)
        return result.tostring()
    def status_offset(self, reg, start, orders=0):
        return ((reg-start)/8)
    def status_bit(self, reg, start, orders=0):
        return (reg-start)%8
    ##
    # @note For a single value, use status(0, status_offset)
    #       (status_offset == command.start)
    def status(self, offset, start=0, orders=0):
        byte = self.buffer[self.status_offset(offset, start)]
        bit  = (1 << self.status_bit(offset, start))
        return (bit & byte) == bit
    def status_bits(self):
        raise "Not implemented"
        return (1,1,1,1,1)

class ConvertValue:
    def __init__(self, buffer=None):
        if buffer is None:
            buffer = _buffer()
        self.buffer = buffer
        return
    def __str__(self):
        result = array.array('c')
        data = self.buffer
        if data:
            result.fromstring(dump_tostring(data, 'data:     '))
        return result.tostring()
    def int_to_byte(self, value):
        value = int(value)
        if value < 0:
            value = -value
            value = (value - 1) ^ 0xFF
        return value & 0xFF
    def append_byte(self, byte, orders=0):
        # @todo bit ordering for orders & 4 = true
        self.buffer.append(byte & 0xFF)
        return
    def append_word(self, word, orders=0):
        if orders & 1: #byte order
            self.append_byte(word & 0xFF, orders)
            self.append_byte(word >> 8, orders)
        else:
            self.append_byte(word >> 8, orders)
            self.append_byte(word & 0xFF, orders)
        return
    def convert_ushort(self, value, orders=0):
        value = int(value)
        self.append_word(value, orders)
        return self.buffer
    def convert_short(self, value, orders=0):
        #convert a signed integer value to a buffer"
        value = int(value)
        if value < 0: #convert to twos complement
            value = -value
            value = (value - 1) ^ 0xFFFF
        self.convert_ushort(value, orders)
        return self.buffer
    def convert_ulong(self, value, orders=0):
        value = long(value)
        #Return two consecutive registers as a signed integer."
        if orders & 2:
            self.convert_ushort(value & 0xFFFF, orders)
            self.convert_ushort(value >> 16, orders)
        else:
            self.convert_ushort(value >> 16, orders)
            self.convert_ushort(value & 0xFFFF, orders)
        return self.buffer
    def convert_long(self, value, orders=0):
        value = long(value)
        #convert signed long
        if value < 0:
            value = -value
            value = (value - 1) ^ 0xFFFFFFFFL
        self.convert_ulong(value, orders)
        return self.buffer
    def convert_hibyte(self, value, orders=0):
        value = int(value)
        return self.convert_ushort(value << 8, orders)
    def convert_lobyte(self, value, orders=0):
        return self.convert_ushort(int(value) & 0xFF, orders)
    def convert_hiint(self, value, orders=0):
        return self.convert_ushort(self.int_to_byte(value) << 8, orders)
    def convert_loint(self, value, orders=0):
        return self.convert_ushort(self.int_to_byte(value), orders)
    def convert_lochar(self, value, orders=0):
        return self.convert_ushort(ord(value), orders)
    def convert_hichar(self, value, orders=0):
        return self.convert_ushort(ord(value) << 8, orders)
    def convert_float(self, value, orders=0):
        return self.convert_string(struct.pack('!f', float(value)), orders)
    def convert_float8(self, value, orders=0):
        return self.convert_string(struct.pack('!d', float(value)), orders)
    def convert_modulo_1(self, value, orders=0):
        value = long(value)
        return self.convert_short(value % 10000L, orders)
    def convert_modulo_2(self, value, orders=0):
        value = long(value)
        self.convert_modulo_1(value / 10000L, orders)
        self.convert_modulo_1(value % 10000L, orders)
        return self.buffer
    def convert_modulo_3(self, value, orders=0):
        value = long(value)
        self.convert_modulo_2(value / 10000L, orders)
        self.convert_modulo_1(value % 10000L, orders)
        return self.buffer
    def convert_modulo_4(self, value, orders=0):
        value = long(value)
        self.convert_modulo_3(value / 10000L, orders)
        self.convert_modulo_1(value % 10000L, orders)
        return self.buffer
    def convert_power_logic_3(self, value, orders=0):
        return self.convert_modulo_3(long(float(value) * 1000), orders)
    def convert_power_logic_4(self, value, orders=0):
        return self.convert_modulo_4(long(float(value) * 1000), orders)
    def convert_time_3(self, time_value, orders=0):
        tt = time.localtime(time_value)
        self.convert_ushort(tt[1]*256 + tt[2], orders)
        self.convert_ushort((tt[0]-1900)*256 + tt[3], orders)
        self.convert_ushort(tt[4]*256 + tt[5], orders)
        return self.buffer
    def convert_time_6(self, time_value, orders=0):
        tt = time.localtime(time_value)[:6]
        tt = list(tt)
        if orders & 2:
            tt.reverse()  #reverse word order
        self.convert_ushort(tt[5],orders) #sec (or year if reversed)
        self.convert_ushort(tt[4],orders) #min
        self.convert_ushort(tt[3],orders) #hour
        self.convert_ushort(tt[2],orders) #day
        self.convert_ushort(tt[1],orders) #month
        self.convert_ushort(tt[0],orders) #year (or sec if reversed)
        return self.buffer
    def convert_dl06_energy_4(self, value, orders=0):
        self.convert_ulong( long(value) / 1000L, orders)
        self.convert_float( float(value) % 1000.0, orders)
        return self.buffer
    def convert_encorp_real_2(self, value, orders=0):
        whole = int(value)
        self.convert_short(whole, orders)
        fraction = abs(value)
        fraction = fraction - int(fraction)
        fraction = int(fraction * 65536.0)
        self.convert_ushort(fraction, orders)
        return self.buffer
#
# change bit assignments to allow xor to auto fix address

    def convert_string(self, value, orders=0):
        string = array.array('B', value)
        for i in range(0, len(value)):
            string[i]=ord(value[i ^ (orders & 3)])
        self.buffer.extend(string)
        return self.buffer
    def convert_zstring(self, value, orders=0):
        return self.convert_string(value+chr(0), orders)
##
# Writes to 00001-09999
    def convert_bits(self, value):
        value = int(value)
        if value is None: value = 0
        if (value != 0) and (value != 1):
            #raise ValueError, 'Coils must be 0 or 1, not: ' + str(value)
            value = 0
        self.append_byte(value) #convert to bit string later
        return self.buffer
    def collapsed_buffer(self):
        #answer a bit field version of the buffer
        bits = self.buffer.tostring()
        unused = 8 - (len(bits) % 8)
        if unused == 8:
            unused = 0
        bytes = ''
        shift = 0
        byte = 0
        for bit in bits + '\x00'*unused:
            byte = byte | (ord(bit) << shift)
            if shift >= 7:
                bytes += chr(byte)
                byte = 0
                shift = 0
            else:
                shift += 1
        return bytes
##
# Writes to 40001-49999

def swap_bytes(i):
    return ((i & 0xFF) << 8) + ((i & 0xFF00) >> 8)

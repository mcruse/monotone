"""
Copyright (C) 2004 2010 2011 Cisco Systems

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

import array
import struct

from mpx.lib.debug import dump_ints_tostring, dump_tostring, dump
from conversions import ConvertBuffer, ConvertRegister, ConvertBitField
from base import buffer, crc
from exception import EModbusCRC

def bytes_outstanding(response, header):
    # header[2] - (len(header) - 3) + 2
    # reduces to: (NOTE: len(header) is USUALLY 5,
    #              so "return header[2]" is ALMOST right)
    n = response.byte_count = header[2]
    return n - len(header) + 5

class Response:
    def __init__(self, line, header, timeout):
        self.line = line
        self.port = self.line.port
        self.timeout = timeout
        self.slave_address = header[0]
        self.function = header[1]

    def set_crc(self):
        b = self.buffer
        if len(b) < 2:
            self.crc = 0
            return
        self.crc = (b[-2] << 8) + b[-1]

class ReadHoldingRegisters(ConvertRegister, Response):
    """Generic ReadHoldingRegisters response.

    Personallity modules can override the command's response factory
    and parse self.data accordingly."""
    def __init__(self, line, header, timeout):
        Response.__init__(self, line, header, timeout)

        n = bytes_outstanding(self, header)
        self.port.read(header, n, timeout)
        ConvertRegister.__init__(self,header[3:])
        if self.line.crc(header):
            raise EModbusCRC
        self.set_crc()

    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:    0x%02X\nfunction:   0x%02X\n' %
                          (self.slave_address, self.function))
        result.fromstring('byte_count: 0x%02X\n' % self.byte_count)
        if self.data:
            result.fromstring(dump_ints_tostring(self.data, 'data:       '))
        result.fromstring('crc:        0x%04X\n' % self.crc)
        return result.tostring()

    def register_as_dword(self, reg, start=0, orders=0):
        return self.register_as_ulong(reg, start, orders)

#
# change bit assignments to allow xor to auto fix address

class ReadStatus(ConvertBitField,Response):
    def __init__(self, line, header, timeout):
        Response.__init__(self, line, header, timeout)
        n = bytes_outstanding(self, header)
        self.port.read(header, n, timeout)
        ConvertBitField.__init__(self,header[3:])
        #self.buffer = header
        if self.line.crc(header):
            raise EModbusCRC
        self.set_crc()
    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:    0x%02X\nfunction:   0x%02X\n' %
                          (self.slave_address, self.function))
        result.fromstring('byte_count: 0x%02X\n' % self.byte_count)
        result.fromstring('crc:        0x%04X\n' % self.crc)
        return result.tostring()

    #def status_offset(self, reg, start, orders=0):
        #return ((reg-start)/8) + 3

    #def status_bit(self, reg, start, orders=0):
        #return (reg-start)%8

    ###
    ## @note For a single value, use status(0, status_offset)
    ##       (status_offset == command.start)
    def status(self, response_offset, start=0, orders=0):
        return ConvertBitField.status(self, response_offset, start, orders)
    #def status(self, response_offset, start=0, orders=0):
        #byte = self.buffer[self.status_offset(response_offset, start)]
        #bit  = (1 << self.status_bit(response_offset, start))
        #return (bit & byte) == bit

    #def status_bits(self):
        #raise "Not implemented"
        #return (1,1,1,1,1)

class ReadCoilStatus(ReadStatus):
    pass

class ReadInputStatus(ReadStatus):
    pass

class ReadInputRegisters(ReadHoldingRegisters):
    pass

class WriteSingleWord(Response, ConvertBuffer):
    def __init__(self, line, header, timeout):
        Response.__init__(self, line, header, timeout)

        self.buffer = header
        n = 8 - len(header)
        self.port.read(header, n, timeout)
        if self.line.crc(header):
            raise EModbusCRC
        self.data_address = self.get_word(2)
        self.value = self.get_word(4)
        self.set_crc()

    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:   0x%02X\nfunction: 0x%02X\n' %
                          (self.slave_address, self.function))
        result.fromstring('data_address:  0x%04X\nvalue:    0x%04X\n' %
                          (self.data_address, self.value))
        result.fromstring('crc:      0x%04X\n' % self.crc)
        return result.tostring()

class ForceSingleCoil(WriteSingleWord):
    def __init__(self, line, header, timeout):
        WriteSingleWord.__init__(self, line, header, timeout)
        if self.value == 0xff00:
            self.value == 1

class PresetSingleRegister(WriteSingleWord):
    pass

##
# @fixme
class PresetMultipleRegisters(ConvertBuffer, Response):
    def __init__(self, line, header, timeout):
        Response.__init__(self, line, header, timeout)
        #self.buffer = header
        n = 8 - len(header)
        self.port.read(header, n, timeout)
        ConvertBuffer.__init__(self, header)        
        if self.line.crc(header):
            raise EModbusCRC
        self.start = self.get_word(2)
        self.count = self.get_word(4)
        self.set_crc()

    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:  0x%02X\nfunction: 0x%02X\n' %
                          (self.slave_address, self.function))
        result.fromstring('start:    0x%04X\ncount:    0x%04X\n' %
                          (self.start, self.count))
        result.fromstring('crc:      0x%04X\n' % self.crc)
        return result.tostring()

class ReportSlaveID(Response):
    """Generic ReportSlaveID response.

    Personallity modules can override the command's response factory
    and parse self.data accordingly."""

    bogus_id     = 0x00
    bogus_status = 0xA5
    bogus_data   = 'Unknown device, exception response.'

    def __init__(self, line, header, timeout):
        Response.__init__(self, line, header, timeout)

        self.buffer = header
        n = bytes_outstanding(self, header)
        self.port.read(header, n, timeout)
        if self.line.crc(header):
            raise EModbusCRC
        self.slave_id = header[3]
        self.run_status = header[4]
        self.data = header[5:-2]
        self.set_crc()

    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:    0x%02X\nfunction:   0x%02X\n' %
                          (self.slave_address, self.function))
        result.fromstring('byte_count: 0x%02X\nslave_id:   0x%02X\n' %
                          (self.byte_count, self.slave_id))
        result.fromstring('run_status: 0x%02X\n' % self.run_status)
        if self.data:
            result.fromstring(dump_tostring(self.data, 'data:       '))
        result.fromstring('crc:        0x%04X\n' % self.crc)
        return result.tostring()

def swap_bytes(i):
    return ((i & 0xFF) << 8) + ((i & 0xFF00) >> 8)

map = {0x01:ReadCoilStatus,
       0x02:ReadInputStatus,
       0x03:ReadHoldingRegisters,
       0x04:ReadInputRegisters,
       0x05:ForceSingleCoil,
       0x06:PresetSingleRegister,
       0x10:PresetMultipleRegisters,
       0x11:ReportSlaveID
       }

def factory(line, header, timeout):
    c = map[header[1]]
    r = c(line, header, timeout)
    return r

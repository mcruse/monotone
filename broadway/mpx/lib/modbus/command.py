"""
Copyright (C) 2002 2007 2010 2011 Cisco Systems

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
import array, types

from mpx.lib.debug import dump_tostring
from base import buffer
from base import crc
from mpx.lib.exceptions import *

class Command:
    def __init__(self, slave_address, function):
        self.slave_address = slave_address
        self.function = function
        b = buffer()
        b.append(slave_address)
        b.append(function)
        self.buffer = b

    def __str__(self):
        result = array.array('c')
        result.fromstring('slave_address:  0x%02X\nfunction: 0x%02X\n' %
                          (self.slave_address, self.function))
        data = self.buffer[2:-2]
        if data:
            result.fromstring(dump_tostring(data, 'data:     '))
        result.fromstring('crc:      0x%04X\n' % self.crc)
        return result.tostring()

    def append_byte(self, byte):
        self.buffer.append(byte)

    def append_word(self, word):
        b = self.buffer
        b.append(word >> 8)
        b.append(word & 0xFF)

    def append_crc(self):
        b = self.buffer
        x = crc(b)
        b.append(x & 0xFF)
        b.append(x >> 8)
        self.crc = x
    def timeout(self, timeout):
        "Hook so commands can return custom timeouts."
        return timeout
    def exception(self,factory):
        "Hook so commands can return custom exception factories."
        return factory
    def response(self,factory):
        "Hook so commands can return custom response factories."
        return factory

##
# Writes to 40001-49999
class ReadHoldingRegisters(Command):
    def __init__(self, slave_address, start, count, function=0x03):
        Command.__init__(self, slave_address, function)
        self.append_word(start)
        self.append_word(count)
        self.append_crc()

##
# Writes to 30001-39999
class ReadInputRegisters(ReadHoldingRegisters):
    def __init__(self, slave_address, start, count):
        ReadHoldingRegisters.__init__(self, slave_address, start, count, 0x04)

##
# Reads to 00001-09999
class ReadCoilStatus(ReadHoldingRegisters):
    def __init__(self, slave_address, start, count):
        ReadHoldingRegisters.__init__(self, slave_address, start, count, 0x01)

##
# Reads to 10001-19999
class ReadInputStatus(ReadHoldingRegisters):
    def __init__(self, slave_address, start, count):
        ReadHoldingRegisters.__init__(self, slave_address, start, count, 0x02)

class WriteSingleWord(Command):
    def __init__(self, slave_address, data_address, value, function):
        Command.__init__(self, slave_address, function)
        self.append_word(data_address)
        self.append_word(value)
        self.append_crc()

##
# Writes to 00001-09999
class ForceSingleCoil(WriteSingleWord):
    def __init__(self, slave_address, data_address, value, orders=0):
        value = int(value)
        if (value != 0) and (value != 1):
            msg = 'Coils must be 0 or 1'
            raise EInvalidValue('ForceSingleCoil', str(value), msg)
        if value:
            value = 0xff00
        WriteSingleWord.__init__(self, slave_address, data_address, value, 0x5)

##
# Writes to 40001-49999
class PresetSingleRegister(WriteSingleWord):
    def __init__(self, slave_address, register, value):
        WriteSingleWord.__init__(self, slave_address, register, value, 0x6)

##
# Writes to 40001-49999
class PresetMultipleRegisters(Command):
    def __init__(self, slave_address, start, values_or_bytearray):
        Command.__init__(self, slave_address, 0x10)
        self.append_word(start)
        if type(values_or_bytearray) == types.ListType:
            values = values_or_bytearray
            count = len(values)
            self.append_word(count)
            self.append_byte(count*2)
            for i in range(0,count):
                self.append_word(values[i])
        else:
            count = len(values_or_bytearray)
            self.append_word(count / 2)
            self.append_byte(count)
            self.buffer.extend(values_or_bytearray)
        self.append_crc()

class ReportSlaveID(Command):
    def __init__(self, slave_address):
        Command.__init__(self, slave_address, 0x11)
        self.append_crc()

    def timeout(self, timeout):
        return 0.1

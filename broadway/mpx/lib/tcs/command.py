"""
Copyright (C) 2003 2011 Cisco Systems

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
import array

from mpx.lib.exceptions import *
from mpx.lib.debug import dump_tostring
import response

debug = 0

def _position_from_int(i):
    if i < 0 or i > 15:
        raise EInvalidValue
    answer = 1
    return answer << i

def buffer(initializer=None):
    # The usual code path is quite simple.  This method
    # tries really hard to except reasonable data types
    # that array.array('B') does not (i.e. Tuples of
    # integers or characters, lists of characters and
    # strings.
    buffer =  array.array('B')
    if initializer:
        t = type(initializer)
        if not t is types.ListType:
            if t is types.StringType:
                buffer.fromstring(initializer)
                return buffer
            tmp = []
            tmp.extend(initializer)
            initializer = tmp
        try:
            buffer.fromlist(initializer)
        except TypeError, error:
            for i in xrange(0,len(initializer)):
                x = initializer[i]
                if type(x) is types.StringType:
                    initializer[i] = ord(x)
                elif type(x) is types.IntType:
                    pass
                else:
                    raise ETypeError
            buffer.fromlist(initializer)
    return buffer

class _Command:
    def __init__(self, function):
        if debug: print 'init _Command ' + str(function)
        self.function = function
        b = buffer()
        self.buffer = b
        self.positions = None
        self.response_class = None
        if debug:
            print 'init done'
            print str(self)
    def __str__(self):
        result = array.array('c')
        result.fromstring('function: %s\n' %
                          (self.function))
        data = self.buffer[1:]
        if data:
            result.fromstring(dump_tostring(data, 'data:     '))
        return result.tostring()
    def append_byte(self, byte):
        self.buffer.append(byte)
    def append_bytes(self, bytes):
        self.buffer.extend(bytes)
    def append_word(self, word):
        b = self.buffer
        b.append(word >> 8)
        b.append(word & 0xFF)
    def append_tcs_value(self, value):
        i = int(value)
        if i >= 0:
            if i > 32767:
                raise EInvalidValue
            self.append_word(0x8000 + i)
        else:
            i = abs(i)
            if i > 32767:
                raise EInvalidValue
            self.append_word(i)
    def tostring(self):
        answer = array.array('c')
        for b in self.buffer:
            answer.fromstring('%02X' % b)
        return self.function + answer.tostring()
        

#address command position|data checksum

# Record read request from a remote
#function is a letter code from "a" to "z"
#positions is a list of numbers of desired tcs "positions"
#upto 16 positions are available
#positions need to be sorted
class GetValue(_Command):
    def __init__(self, function, positions):
        if debug: print 'init GetValue'
        function = function.lower()
        if function == 'l' or function == 'k' or function == 'm' or function == '{l' :
            function = function.upper() #read only commands
        _Command.__init__(self, function)
        self.response_class = response.GetValueReply
        self.positions = positions
        position_bits = 0
        data_list = []
        
        for p in positions:
            position_bits = position_bits | _position_from_int(p)

        self.append_word(position_bits)
        if debug: print 'GetValue command init: ' + str(self)
class GetType(GetValue):
    def __init__(self):
        if debug: print 'init GetTypeAndVersion'
        GetValue.__init__(self, 'a', [0])
        self.response_class = response.GetTypeReply
        if debug: print str(self)
class GetVersion(GetValue):
    def __init__(self):
        if debug: print 'init GetTypeAndVersion'
        GetValue.__init__(self, 'a', [1])
        self.response_class = response.GetVersionReply
        if debug: print str(self)
class GetTimeOfDayValue(GetValue):
    def __init__(self, function, positions):
        GetValue.__init__(self, function, positions)
        self.response_class = response.GetTimeOfDayReply
#read a single value from the holiday parameter
#only one value can be read at a time due to the different encoding of the position bits
class GetHolidayValue(_Command):
    def __init__(self, function, index, position):
        if debug: print 'init GetValue'
        if not function.isalpha():
            raise EInvalidValue
        function = function.lower()
        if function != 'h':
            raise EInvalidValue
        _Command.__init__(self, function)
        self.response_class = response.GetHolidayReply
        self.positions = None
        position_bits = index << 8
        position_bits = position_bits | position
        self.append_word(position_bits)
        if debug: print 'GetHoldayValue command init: ' + str(self)
##
# Write a value to one or more posistions of a parameter
#function is a letter code from "A" to "Z"
#positions is a list of pairs of number|values of desired tcs "positions"
#upto 16 positions are available
#element 0 of a number|value pair is the position number
#element 1 is the int value to be written to it
class SetValue(_Command):
    def __init__(self, function, positions):
        if not function.isalpha():
            raise EInvalidValue
        function = function.upper()
        if function == 'L' or function == 'K' or function == 'M' or function == '{L':
            raise EPermission('read only', function, 'not set-able')
        _Command.__init__(self, function)
        self.response_class = response.SetValueReply
        position_bits = 0
        data_list = []
        
        for p in positions:
            position_bits = position_bits | _position_from_int(p[0])
            data_list.append(p[1])

        self.append_word(position_bits)
        for d in data_list:
            self.append_tcs_value(d)

class SetTimeOfDayValue(_Command):
      def __init__(self, function, positions):
        function = function.upper()
        if function == 'L' or function == 'K' or function == 'M' or function == '{L':
            raise EPermission('read only', function, 'not set-able')
        _Command.__init__(self, function)
        self.response_class = response.SetTimeOfDayReply
        position_bits = 0
        data_list = []
        
        for p in positions:
            position_bits = position_bits | _position_from_int(p[0])
            data_list.append(p[1])

        self.append_word(position_bits)
        for d in data_list:
            self.append_tcs_value(int(d))
  
class SetHolidayValue(_Command):
    def __init__(self, function, index, position, value):
        if debug: print 'init GetValue'
        if not function.isalpha():
            raise EInvalidValue
        function = function.upper()
        if function != 'H':
            raise EInvalidValue
        _Command.__init__(self, function)
        self.response_class = response.SetHolidayReply
        self.positions = None
        position_bits = index << 8
        position_bits = position_bits | position
        if debug: print 'set holiday position bits: ', str(position_bits)
        self.append_word(position_bits)
        if debug: print 'append value: ', str(value)
        self.append_tcs_value(value)
        if debug: print 'SetHoldayValue command init: ' + str(self)

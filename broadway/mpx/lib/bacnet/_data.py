"""
Copyright (C) 2002 2006 2007 2010 2011 Cisco Systems

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
# @fixme Get consistent with EInvalidValue and EParseFailure

import array
import types

from mpx.lib.exceptions import ENotImplemented, ETypeError, EInvalidValue, \
     EParseFailure

ANSI_X3dot4 = 0
DBCS = 1
JIS_C_6226 = 2
ISO_10646_UCSdash4 = 3
ISO_10646_UCSdash2 = 4
ISO_8859dash1 = 5

_character_set_names = ("ANSI X3.4", "IBM/Microsoft DBCS", "JIS C 6226",
                        "ISO 10646 (UCS-4)", "ISO 10646 (UCS-2)",
                        "ISO 8859-1")
##
# Interface that BACnet specific objects support.
class Data:
    class _Doc:
        pass
    ##
    # @param *args Call <code>self.encode(*args)</code>
    # @param **keywords
    # @key decode Call <code>self.decode(keywords['decode'])</code>
    # @see decode
    # @see encode
    # @note *args and **keywords are mutually exclusive.
    def __init__(self, *arg, **keywords):
        ##
        # READONLY attribute that returns the BACnet encoding of the object.
        self.encoding = self._Doc()
        ##
        # @param *args Object specific arguments used to to update the
        # object's encoding.
    def encode(self, *arg):
        pass
    def __str__(self):
        pass
    def __eq__(self, other):
        pass
    def __ne__(self, other):
        pass

def character_set_name(character_set):
    if character_set >= 0 and character_set <= 5:
        return _character_set_names[character_set]
    return "Unknown (%d)" % character_set

##
# @implements Data
class CharacterString:
    def __init__(self, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            self.character_set = None
            self.character_string = ''
    def __str__(self):
        return self.character_string
    def __eq__(self, other):
        if hasattr(other, 'character_set') and \
           hasattr(other, 'character_string'):
            return self.character_set == other.character_set and \
                   self.character_string == other.character_string
        if type(other) is types.StringType:
            return self.character_string == other
        return 0
    def __ne__(self, other):
        if hasattr(other, 'character_set') and \
           hasattr(other, 'character_string'):
            return self.character_set != other.character_set or \
                   self.character_string != other.character_string
        if type(other) is types.StringType:
            return self.character_string != other
        return 1
    def __getattr__(self, attribute):
        if attribute == "encoding":
            return self._encoding()
        try: 
            return self.__dict__[attribute]
        except KeyError: 
            raise AttributeError(attribute)
    def __setattr__(self, attribute, value):
        if attribute == "encoding":
            raise ETypeError, 'encoding is READONLY'
        self.__dict__[attribute] = value
    def _encoding(self):
        raise ENotImplemented('Only concrete CharacterString instances ' +
                              'can provide an encoding')
    def description(self):
        return "BACnet Character String using %s encoding." % \
               character_set_name(self.character_set)
    def _decode_to_ansi(self, buffer):
        if ord(buffer[0]) != ANSI_X3dot4:
            raise EInvalidValue('buffer', buffer, 'Not an ANSI X3.4 encoding')
        self.character_set = ord(buffer[0])
        self.character_string = buffer[1:]
        self.__class__ = ANSI_String
    def _decode_to_dbcs(self, buffer):
        if ord(buffer[0]) != DBCS:
            raise EInvalidValue('buffer', buffer, 'Not a DBCS encoding')
        if len(buffer) < 3:
            raise EInvalidValue('buffer length must be at least' +
                                ' three bytes long')
        self.character_set = ord(buffer[0])
        self.code_page = (ord(buffer[1]) << 8) + ord(buffer[2])
        self.character_string = buffer[3:]
        self.__class__ = DBCS_String
    def decode(self, buffer):
        if type(buffer) is array.ArrayType:
            buffer = buffer.tostring()
        if len(buffer) < 1:
            raise EInvalidValue('buffer length must be at least one byte long')
        character_set = ord(buffer[0])
        if character_set == ANSI_X3dot4:
            self._decode_to_ansi(buffer)
        elif character_set == DBCS:
            self._decode_to_dbcs(buffer)
        else:
            raise ENotImplemented(character_set_name(self.character_set))
        return
    def encode(self):
        raise ENotImplemented('Only concrete CharacterString instances ' +
                              'can provide an encoding')

##
# @implements Data
    def __repr__(self):
        return repr(str(self))
class ANSI_String(CharacterString):
    def __init__(self, character_string=None, **keywords):
        if character_string != None:
            if keywords.has_key('decode'):
                raise ETypeError('character_string and decode keyword ' +
                                 'are mutually exclusive')
            self.encode(character_string)
        elif keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            raise ETypeError('character_string or decode keyword required')
    def _encoding(self):
        return chr(self.character_set) + self.character_string
    def encode(self, character_string):
        if type(character_string) is array.ArrayType:
            character_string  = character_string.tostring()
        self.character_set = ANSI_X3dot4
        self.character_string = character_string
    def decode(self, buffer):
        if type(buffer) is array.ArrayType:
            buffer = buffer.tostring()
        self._decode_to_ansi(buffer)

##
# @implements Data
class DBCS_String(CharacterString):
    def __init__(self, character_string=None, code_page=850, **keywords):
        if character_string != None:
            if keywords.has_key('decode'):
                raise ETypeError('character_string and decode keyword ' +
                                 'are mutually exclusive')
            self.encode(character_string, code_page)
        elif keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            raise ETypeError('character_string or decode keyword required')
    def __eq__(self, other):
        if not CharacterString.__eq__(self, other):
            return 0
        if hasattr(other, 'code_page'):
            return self.code_page == other.code_page
        return 1
    def __ne__(self, other):
        if CharacterString.__ne__(self, other):
            return 1
        if hasattr(other, 'code_page'):
            return self.code_page != other.code_page
        return 0
    def _encoding(self):
        return chr(self.character_set) + \
               chr(self.code_page >> 8) + chr(self.code_page & 0xff) + \
               self.character_string
    def decode(self, buffer):
        if type(buffer) is array.ArrayType:
            buffer = buffer.tostring()
        self._decode_to_dbcs(buffer)
    def encode(self, character_string, code_page=850):
        self.character_set = DBCS
        self.code_page = code_page
        if type(character_string) is array.ArrayType:
            character_string  = character_string.tostring()
        self.character_string = character_string

##
# @implements Data
class BitString:
    def __init__(self, bits=None, **keywords):
        if keywords.has_key('decode'):
            if bits != None:
                raise EInvalidValue('The decode keyword is mutually ' +
                                    'exclusive with the bits parameter')
            self.decode(keywords['decode'])
        elif bits != None:
            self.encode(bits)
        else:
            self.bits = ()
    def __eq__(self, other):
        if not hasattr(other, 'bits'):
            return 0
        return self.bits == other.bits
    def __ne__(self, other):
        if not hasattr(other, 'bits'):
            return 1
        return self.bits != other.bits
    def __str__(self):
        bit_string = array.array('c')
        for b in self.bits:
            if b:
                bit_string.append('1')
            else:
                bit_string.append('0')
        return bit_string.tostring()
    def __getattr__(self, attribute):
        if attribute == "encoding":
            return self._encoding()
        elif attribute == "unused":
            used = (len(self.bits) % 8)
            if used:
                return 8 - used
            return 0
        try: 
            return self.__dict__[attribute]
        except KeyError: 
            raise AttributeError(attribute)
    def __setattr__(self, attribute, value):
        if attribute == "encoding":
            raise ETypeError, 'encoding is READONLY'
        if attribute == "unused":
            raise ETypeError, 'unused is READONLY'
        self.__dict__[attribute] = value
    def _encoding(self):
        unused = 8 - (len(self.bits) % 8)
        if unused == 8:
            unused = 0
        bytes = chr(unused)
        shift = 7
        byte = 0
        for bit in self.bits + (0,)*unused:
            byte = byte | (bit << shift)
            if not shift:
                bytes += chr(byte)
                byte = 0
                shift = 7
            else:
                shift -= 1
        return bytes
    def decode(self, buffer):
        if type(buffer) is array.ArrayType:
            if buffer.typecode == 'c':
                as_byte = ord
            elif buffer.typecode == 'B':
                def as_byte(value):
                    return value
            else:
                raise EInvalidType("Unsupported array type %s, use 'c' or 'B'")
        elif type(buffer) is types.StringType:
            as_byte = ord
        else:
            raise EInvalidType('decode only supports array and string objects')
        unused = as_byte(buffer[0])
        if unused < 0 or unused > 7:
            raise EParseFailure('Invalid number of unused bits (%d).' % unused)
        nbits = 0
        bytes = array.array('B')
        for i in xrange(1,len(buffer)):
            bytes.append(as_byte(buffer[i]))
            nbits += 8
        nbits -= unused
        bits = []
        next_bit = 0
        for byte in bytes:
            for shift in range(7,-1,-1):
                if next_bit >= nbits:
                    break
                bits.append((byte >> shift) & 1)
                next_bit += 1
        self.bits = tuple(bits)
        return self
    def bit(self, bit):
        return self.bits[bit]
    def description(self):
        return "BACnet BitString"
    def encode(self, bits):
        self.bits = bits
    def __repr__(self):
        return repr(str(self))
        
def decode_character_string(buffer):
    """##
    # Return the Python native representation of the BACnet character string
    # encoded in the octets of <code>buffer</code>.
    # @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').
    # @return An appropriate CharacterString instance."""
    character_set =  ord(buffer[0])
    if character_set == ANSI_X3dot4:
        return ANSI_String(decode=buffer)
    elif character_set == DBCS:
        return DBCS_String(decode=buffer)
    raise ENotImplemented("%s character set is not supported." % \
                          character_set_name(character_set))

def encode_character_string(value):
    """##
    # Return a Python string that contains the BACnet encoded octets for the
    # supplied CharacterString.
    # @param A CharacterString derived class that describes the character string
    #        to encode.
    # @returns A Python string containing the encoded octets."""
    if not isinstance(value, CharacterString):
        msg = 'Object must be derived from mpx.lib.bacnet.CharacterString'
        raise ETypeError(msg)
    return value.encoding

def decode_bit_string(buffer):
    """##
    # Return the object representating the BACnet bit string
    # encoded in the octets of <code>buffer</code>.
    # @param buffer A string or array of bytes (types \'c\', \'b\', or \'B\').
    # @return An appropriate BitString instance."""
    return BitString(decode=buffer)

def encode_bit_string(value):
    """##
    # Return a Python string that contains the BACnet encoded octets for the
    # supplied BitString.
    # @param A BitString instance that describes the bit string
    #        to encode.
    # @returns A Python string containing the encoded octets."""
    if not isinstance(value, BitString):
        msg = 'Object must be derived from mpx.lib.bacnet.BitString'
        raise ETypeError(msg)
    return value.encoding

"""
Copyright (C) 2002 2003 2004 2010 2011 Cisco Systems

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
# Test cases to exercise the data encoders and decoders.
#

from mpx_test import DefaultTestFixture

import math
import copy

from mpx.lib.exceptions import EOverflow, ENotImplemented, EInvalidValue
from mpx.lib.exceptions import ETypeError
from mpx.lib.bacnet.data import *

class TestCase(DefaultTestFixture):
    PI_AS_REAL   = '\x40\x49\x0f\xdb'
    REAL_PI      = 3.1415927410125732
    PI_AS_DOUBLE = '\x40\x09\x21\xfb\x54\x44\x2d\x18'
    DOUBLE_PI    = 3.1415926535897931

    def test_decode_null(self):
        decode_null('\x00')
        for e in ('\x01','\x02','\xfe','\xff','','die die die'):
            try: decode_null(e)
            except EInvalidValue:
                pass
            else:
                self.fail(
                    'Failed to detect an invalid value.'
                    )
        return
    def test_encode_null(self):
        if encode_null() != '\x00':
            self.fail(
                'Failed to encode BACnet NULL.'
                )
        return
    def test_decode_boolean(self):
        decode_boolean('\x00')
        decode_boolean('\x01')
        for e in ('\x02','\xfe','\xff','','pop!'):
            try: decode_boolean(e)
            except EInvalidValue:
                pass
            else:
                self.fail(
                    'Failed to detect an invalid value.'
                    )
        return
    def test_encode_boolean(self):
        encode_boolean(0)
        encode_boolean(1)
        for e in (2,-1):
            try: encode_boolean(e)
            except EInvalidValue:
                pass
            else:
                self.fail(
                    'Failed to detect an invalid value.'
                    )
        for e in (0L,1L,1.0,'1'):
            try: encode_boolean(e)
            except ETypeError:
                pass
            else:
                self.fail(
                    'Failed to detect a type error.'
                    )
        return
    def test_decode_unsigned_integer(self):
        for i in range(0,255):
            if decode_unsigned_integer(chr(i)) != i:
                self.fail(
                    'Simple byte decode of %s failed.' % repr(chr(i))
                    )
        for e,d in (('\xff\xff\xff\xff\xff\xff\xff\xff', 0xFFFFFFFFFFFFFFFFL),
                    ('\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f', 0x7F7F7F7F7F7F7F7FL),
                    ('\xa5\xa5\xa5\xa5\xa5\xa5\xa5\xa5', 0xA5A5A5A5A5A5A5A5L),
                    ('\x5a\x5a\x5a\x5a\x5a\x5a\x5a\x5a', 0x5A5A5A5A5A5A5A5AL)):
            if decode_unsigned_integer(e) != d:
                self.fail(
                    'Failed to decode %s.' % hex(d)
                    )
        return
    def test_encode_unsigned_integer(self):
        for i in range(0,255):
            if encode_unsigned_integer(i) != chr(i):
                self.fail(
                    'Failed to encode simple byte value %02x.' % i
                    )
        for e,d in (('\xff\xff\xff\xff\xff\xff\xff\xff', 0xFFFFFFFFFFFFFFFFL),
                    ('\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f', 0x7F7F7F7F7F7F7F7FL),
                    ('\xa5\xa5\xa5\xa5\xa5\xa5\xa5\xa5', 0xA5A5A5A5A5A5A5A5L),
                    ('\x5a\x5a\x5a\x5a\x5a\x5a\x5a\x5a', 0x5A5A5A5A5A5A5A5AL)):
            if encode_unsigned_integer(d) != e:
                self.fail(
                    'Failed to encode %s.' % hex(d)
                    )
        return
    def test_decode_signed_integer(self):
        for i in range (0,128):
            if decode_signed_integer(chr(i)) != i:
                self.fail(
                    'Simple byte decode of %s failed.' % repr(chr(i))
                    )
        for i in range (128,256):
            if decode_signed_integer(chr(i)) != (i - 256):
                self.fail(
                    'Simple negative byte decode of %s failed.' % repr(chr(i))
                    )
        for i in range(1,9):
            if decode_signed_integer('\xff'*i) != -1:
                self.fail(
                    'Did not decode %s as -1.' % repr('\xff'*i)
                    )
        return
    def test_encode_signed_integer(self):
        for i in range (0,128):
            if encode_signed_integer(i) != chr(i):
                self.fail(
                    'Simple byte encode of 0x%02x failed.' % i
                    )
        for i in range (128,256):
            if encode_signed_integer(i) != '\x00' + chr(i):
                self.fail(
                    'Simple negative byte decode of 0x%02x failed.' % i
                    )
        if encode_signed_integer(0x0fffffffffffffffL) != \
           '\x0f\xff\xff\xff\xff\xff\xff\xff':
            self.fail(
                'Failed proper encode of 0x0fffffffffffffffL.'
                )
        return
    def test_decode_real(self):
        pi = decode_real(self.PI_AS_REAL)
        if pi != self.REAL_PI:
            self.fail(
                'Failed to decode 4 byte pi.  Expected %.16f got %.16f ' %
                (self.REAL_PI, pi)
                )
        return
    def test_encode_real(self):
        if encode_real(self.DOUBLE_PI) != self.PI_AS_REAL:
            self.fail(
                'Failed to encode DOUBLE_PI'
                )
        return
    def test_decode_double(self):
        if decode_double(self.PI_AS_DOUBLE) != self.DOUBLE_PI:
            self.fail(
                'Failed to decode DOUBLE_PI'
                )
        return
    def test_encode_double(self):
        if encode_double(self.DOUBLE_PI) != self.PI_AS_DOUBLE:
            self.fail(
                'Failed to encode DOUBLE_PI'
                )
        return
    def test_decode_octet_string(self):
        for s in ('', 'This is a test.', '\x00\x01\x02\x03'):
            if s != decode_octet_string(s):
                self.fail(
                    'Failed to decode octect string %s.' % repr(s)
                    )
        return
    def test_encode_octet_string(self):
        for s in ('', 'This is a test.', '\x00\x01\x02\x03'):
            if s != encode_octet_string(s):
                self.fail(
                    'Failed to encode octect string %s.' % repr(s)
                    )
        return
    def test_decode_character_string(self):
        test_string = 'This is a test.'
        d = decode_character_string('\x00' + test_string)
        if not isinstance(d, ANSI_String):
            self.fail(
                'Failed to instantiate an ANSI_String object.'
                )
        if d.character_set != ANSI_X3dot4:
            self.fail(
                'Failed to decode the ANSI X3.4 character set value.'
                )
        if str(d) != test_string:
            self.fail(
                'Failed to decode the ANSI X3.4 data.'
                )
        d = decode_character_string('\x01\x03\x25' + test_string)
        if not isinstance(d, DBCS_String):
            self.fail(
                'Failed to instantiate a DBCS_String object.'
                )
        if d.character_set != DBCS:
            self.fail(
                'Failed to decode the DBCS character set value.'
                )
        if d.code_page != 805:
            self.fail(
                'Failed to decode the DBCS code page.'
                )
        if str(d) != test_string:
            self.fail(
                'Failed to decode the DBCS data.'
                )
        return
    def test_encode_character_string(self):
        test_string = 'This is a test.'
        try: encode_character_string(ANSI_String(decode='\x01'))
        except EInvalidValue:
            pass
        else:
            self.fail(
                'Failed to detect an invalid value.'
                )
        try: encode_character_string(DBCS_String(decode='\x00'))
        except EInvalidValue:
            pass
        else:
            self.fail(
                'Failed to detect an invalid value.'
                )
        e = encode_character_string(ANSI_String(decode='\x00' + test_string))
        if e[1:] != test_string:
            self.fail(
                'Failed to encode test string.'
                )
        e = encode_character_string(DBCS_String(decode='\x01\x03\x25' +
                                                test_string))
        if e[3:] != test_string:
            self.fail(
                'Failed to encode test string.'
                )
        return
    def test_decode_bit_string(self):
        b = decode_bit_string('\x03\xa8')
        if b.unused != 3:
            self.fail(
                'Incorrect number of unused bits decoded.'
                )
        if len(b.bits) != 5:
            self.fail(
                'Incorrect number of bits decoded.'
                )
        if b.bits != (1,0,1,0,1):
            self.fail(
                'Incorrect bits decoded.'
                )
        return
    def test_encode_bit_string(self):
        b = BitString((1,0,1,0,1))
        s = encode_bit_string(b)
        if s != '\x03\xa8':
            self.fail(
                'Encoded (1,0,1,0,1) incorrectly'
                )
        return
    def test_decode_enumerated(self):
        for i in range(0,255):
            if decode_enumerated(chr(i)) != i:
                self.fail(
                    'Simple byte decode of %s failed.' % repr(chr(i))
                    )
        for e,d in (('\xff\xff\xff\xff\xff\xff\xff\xff', 0xFFFFFFFFFFFFFFFFL),
                    ('\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f', 0x7F7F7F7F7F7F7F7FL),
                    ('\xa5\xa5\xa5\xa5\xa5\xa5\xa5\xa5', 0xA5A5A5A5A5A5A5A5L),
                    ('\x5a\x5a\x5a\x5a\x5a\x5a\x5a\x5a', 0x5A5A5A5A5A5A5A5AL)):
            if decode_enumerated(e) != d:
                self.fail(
                    'Failed to decode %s.' % hex(d)
                    )
        return
    def test_encode_enumerated(self):
        for i in range(0,255):
            if encode_enumerated(i) != chr(i):
                self.fail(
                    'Failed to encode simple byte value %02x.' % i
                    )
        for e,d in (('\xff\xff\xff\xff\xff\xff\xff\xff', 0xFFFFFFFFFFFFFFFFL),
                    ('\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f', 0x7F7F7F7F7F7F7F7FL),
                    ('\xa5\xa5\xa5\xa5\xa5\xa5\xa5\xa5', 0xA5A5A5A5A5A5A5A5L),
                    ('\x5a\x5a\x5a\x5a\x5a\x5a\x5a\x5a', 0x5A5A5A5A5A5A5A5AL)):
            if encode_enumerated(d) != e:
                self.fail(
                    'Failed to encode %s.' % hex(d)
                    )
        return
    def test_decode_date(self):
        d = decode_date('\x41\x04\x18\x06')
        if d.year != 1965:
            self.fail(
                'Decoded year incorrectly'
                )
        if d.month != 4:
            self.fail(
                'Decoded month incorrectly'
                )
        if d.day != 24:
            self.fail(
                'Decoded day incorrectly'
                )
        if d.day_of_week != 6:
            self.fail(
                'Decoded day_of_week incorrectly'
                )
        d = decode_date('\x64\x01\x01\xff')
        if d.year != 2000:
            self.fail(
                'Decoded year incorrectly'
                )
        if d.month != 1:
            self.fail(
                'Decoded month incorrectly'
                )
        if d.day != 1:
            self.fail(
                'Decoded day incorrectly'
                )
        if d.day_of_week != None:
            self.fail(
                'Did not decode "don\'t care" day_of_week'
                )
        for s in ('\x41\x0d\x18\x06', '\x41\x0c\x20\x06', '\x41\x0c\x18\x08'):
            try:
                decode_date(s)
            except EParseFailure:
                pass
            else:
                self.fail(
                    'Failed to detect a parse failure'
                    )
        return
    def test_encode_date(self):
        if encode_date(Date()) != '\xff\xff\xff\xff':
            self.fail(
                'Encoded default date wrong'
                )
        if encode_date(Date(1965,4,24,6)) != '\x41\x04\x18\x06':
            self.fail(
                'Encoded an auspicious date incorrectly'
                )
        return
    def test_decode_time(self):
        d = decode_time('\x11\x23\x2d\x11')
        if d.hour != 17:
            self.fail(
                'Decoded hour incorrectly'
                )
        if d.minute != 35:
            self.fail(
                'Decoded minute incorrectly'
                )
        if d.second != 45:
            self.fail(
                'Decoded second incorrectly'
                )
        if d.hundredths != 17:
            self.fail(
                'Decoded hundredths incorrectly'
                )
        d = decode_time('\x01\x01\x01\xff')
        if d.hour != 1:
            self.fail(
                'Decoded hour incorrectly'
                )
        if d.minute != 1:
            self.fail(
                'Decoded minute incorrectly'
                )
        if d.second != 1:
            self.fail(
                'Decoded second incorrectly'
                )
        if d.hundredths != None:
            self.fail(
                'Did not decode "don\'t care" hundredths'
                )
        for s in ('\x18\x3b\x3b\x63', '\x17\x3c\x3b\x63',
                  '\x17\x3b\x3c\x63', '\x17\x3b\x3b\x64',):
            try:
                decode_time(s)
            except EParseFailure:
                pass
            else:
                self.fail(
                    'Failed to detect a parse failure'
                    )
        return
    def test_encode_time(self):
        if encode_time(Time()) != '\xff\xff\xff\xff':
            self.fail(
                'Encoded default time wrong'
                )
        if encode_time(Time(23,58,0,0)) != '\x17\x3a\x00\x00':
            self.fail(
                'Encoded a scary time incorrectly'
                )
        return
    def test_decode_bacnet_object_identifier(self):
        b = decode_bacnet_object_identifier('\x00\x40\x00\x01')
        if (b.id != 0x00400001):
            self.fail(
                'Decoded id incorrectly'
                )
        if (b.object_type != 1):
            self.fail(
                'Decoded object_type incorrectly'
                )
        if (b.instance_number != 1):
            self.fail(
                'Decoded object_type incorrectly'
                )
        return
    def test_encode_bacnet_object_identifier(self):
        b = BACnetObjectIdentifier(0x00400001)
        s = encode_bacnet_object_identifier(b)
        if (s != '\x00\x40\x00\x01'):
            self.fail(
                'Encoded incorrectly'
                )
        return
    def test_Date(self):
        d = Date()
        if d.year != None or d.month != None or d.day != None or \
           d.day_of_week != None:
            self.fail(
                'Defaults wrong'
                )
        d.encode(1999,12,31,5)
        if d.year != 1999:
            self.fail(
                'Re-encode of year failed'
                )
        if d.month != 12:
            self.fail(
                'Re-encode of month failed'
                )
        if d.day != 31:
            self.fail(
                'Re-encode of day failed'
                )
        if d.day_of_week != 5:
            self.fail(
                'Re-encode of day_of_week failed'
                )
        if d.encoding != '\x63\x0c\x1f\x05':
            self.fail(
                'Encoding failed'
                )
        d.decode('\x64\x01\x01\x06')
        if d.year != 2000:
            self.fail(
                'Re-decode of year failed'
                )
        if d.month != 1:
            self.fail(
                'Re-decode of month failed'
                )
        if d.day != 1:
            self.fail(
                'Re-decode of day failed'
                )
        if d.day_of_week != 6:
            self.fail(
                'Re-decode of day_of_week failed'
                )
        if d.encoding != '\x64\x01\x01\x06':
            self.fail(
                'Decoding failed'
                )
    def test_Time(self):
        t = Time()
        if t.hour != None or t.minute != None or t.second != None or \
           t.hundredths != None:
            self.fail(
                'Defaults wrong'
                )
        t.encode(23,59,59,99)
        if t.hour != 23:
            self.fail(
                'Re-encode of hour failed'
                )
        if t.minute != 59:
            self.fail(
                'Re-encode of minute failed'
                )
        if t.second != 59:
            self.fail(
                'Re-encode of second failed'
                )
        if t.hundredths != 99:
            self.fail(
                'Re-encode of hundredths failed'
                )
        if t.encoding != '\x17\x3b\x3b\x63':
            self.fail(
                'Encoding failed'
                )
        t.decode('\x00\x00\x00\x00')
        if t.hour != 0:
            self.fail(
                'Re-decode of hour failed'
                )
        if t.minute != 0:
            self.fail(
                'Re-decode of minute failed'
                )
        if t.second != 0:
            self.fail(
                'Re-decode of day failed'
                )
        if t.hundredths != 0:
            self.fail(
                'Re-decode of hundredths failed'
                )
        if t.encoding != '\x00\x00\x00\x00':
            self.fail(
                'Decoding failed'
                )
    def test_BACnetObjectIdentifier(self):
        b = [BACnetObjectIdentifier(0x00400001),
             BACnetObjectIdentifier(1,1),
             BACnetObjectIdentifier(decode='\x00\x40\x00\x01')]
        for i in b:
            if (i.id != 0x00400001):
                self.fail(
                    'id incorrect'
                    )
            if (i.object_type != 1):
                self.fail(
                    'object_type incorrect'
                    )
            if (i.instance_number != 1):
                self.fail(
                    'object_type incorrect'
                    )
        try: BACnetObjectIdentifier()
        except ETypeError: pass
        else: self.fail(
            'failed to detect no arguments'
            )
        try: BACnetObjectIdentifier(decode='')
        except EInvalidValue: pass
        else: self.fail(
            'failed to detect incorrect length decode string'
            )
        try: BACnetObjectIdentifier(1,1,decode='1234')
        except ETypeError: pass
        else: self.fail(
            'failed to detect conflicting arguments'
            )
        try: BACnetObjectIdentifier(0x400,1)
        except EOverflow: pass
        else: self.fail(
            'failed to detect object_type overflow'
            )
        try: BACnetObjectIdentifier(1,0x400000)
        except EOverflow: pass
        else: self.fail(
            'failed to detect instance_number overflow'
            )
        b = BACnetObjectIdentifier(0x3ff,0x3fffff)
        if b.id != -1:
            self.fail(
                'Failed encoding of 0x3ff, 0x3fffff'
                )
        b.encode(0, 0)
        if b.id != 0:
            self.fail(
                'Failed re-decode'
                )
        b.decode('\x00\x40\x00\x04')
        if b.object_type != 1:
            self.fail(
                'Failed re-decode of object_type'
                )
        if b.instance_number != 4:
            self.fail(
                'Failed re-decode of instance_number'
                )

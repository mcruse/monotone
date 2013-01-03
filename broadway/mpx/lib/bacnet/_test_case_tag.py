"""
Copyright (C) 2002 2010 2011 Cisco Systems

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

import mpx.lib
from mpx.lib.bacnet import tag, data
from mpx.lib.exceptions import EParseFailure

class TestCase(DefaultTestFixture):
    def test_empty(self):
        t = tag.Tag()
        return
    def test_decode_null(self):
        for factory in (tag.Tag, tag.Null):
            t = factory(decode='\x00')
            if t.name != 'Null':
                raise 'Decoded BACnet Null incorrectly as', t.name
            if t.value != None:
                raise "Decoded BACnet Null as '%s' instead of None." % t.value
        for factory in (tag.Tag, tag.Null):
            try:
                t = factory(decode='\x01')
            except EParseFailure:
                pass
            else:
                raise 'Failed to detect bad BACnet Null encoding.'
    def test_encode_null(self):
        n = tag.Null()
        if n.name != 'Null':
            raise 'Encoded BACnet Null incorrectly as', n.name
        if n.value != None:
            raise "Decoded BACnet Null as '%s' instead of None." % t.value
    def test_decode_boolean(self):
        for data,value in (('\x10',0),('\x11',1)):
            for factory in (tag.Tag, tag.Boolean):
                t = factory(decode=data)
                if t.name != 'Boolean':
                    raise 'Decoded BACnet Boolean incorrectly as', t.name
                if t.value != value:
                    raise 'Decoded 0x%x as 0x%x' % (value, t.value)
        for factory in (tag.Tag, tag.Boolean):
            try:
                t = factory(decode='\x12')
                value = t.value
            except EParseFailure:
                pass
            else:
                raise 'Failed to detect bad BACnet Boolean encoding.'
    def test_encode_boolean(self):
        for boolean,encoding,value in ((tag.Boolean(0),'\x10', 0),
                                       (tag.Boolean(1),'\x11', 1)):
            if boolean.name != 'Boolean':
                raise 'Encoded BACnet Boolean incorrectly as', boolean.name
            if boolean.value != value:
                raise 'Encoded 0x%x as 0x%x' % (value, boolean.value)
            if boolean.encoding != encoding:
                raise 'Encoding failed'
    def test_decode_unsigned_integer(self):
        for data,value in (('\x21\x48',72), ('\x21\x00',0),
                           ('\x25\x08\x01\x02\x03\x04\x05\x06\x07\x08',
                            0x0102030405060708L)):
            for factory in (tag.Tag, tag.UnsignedInteger):
                t = factory(decode=data)
                if t.name != 'Unsigned Integer':
                    raise 'Decoded BACnet Unsigned Integer incorrectly as', \
                          t.name
                if t.value != value:
                    raise 'Decoded 0x%x as 0x%x' % (value, t.value)
    def test_encode_unsigned_integer(self):
        for unsigned,encoding,value in (
            (tag.UnsignedInteger(72),'\x21\x48',72),
            (tag.UnsignedInteger(0),'\x21\x00',0),
            (tag.UnsignedInteger(0x0102030405060708L),
             '\x25\x08\x01\x02\x03\x04\x05\x06\x07\x08',
             0x0102030405060708L)):
            if unsigned.name != 'Unsigned Integer':
                raise 'Decoded BACnet Unsigned Integer incorrectly as', t.name
            if unsigned.value != value:
                raise 'Decoded 0x%x as 0x%x' % (value, unsigned.value)
            if unsigned.encoding != encoding:
                raise 'Encoding failed'
    def test_decode_signed_integer(self):
        for data,value in (('\x31\x48',72), ('\x31\x00',0),
                           ('\x35\x08\x01\x02\x03\x04\x05\x06\x07\x08',
                            0x0102030405060708L),
                           ('\x31\xff', -1), ('\x32\x00\xff', 255)):
            for factory in (tag.Tag, tag.SignedInteger):
                t = factory(decode=data)
                if t.name != 'Signed Integer':
                    raise 'Decoded BACnet Signed Integer incorrectly as',t.name
                if t.value != value:
                    raise 'Decoded 0x%x as 0x%x' % (value, t.value)
    def test_encode_signed_integer(self):
        for signed,encoding,value in (
            (tag.SignedInteger(72),'\x31\x48',72),
            (tag.SignedInteger(0),'\x31\x00',0),
            (tag.SignedInteger(0x0102030405060708L),
             '\x35\x08\x01\x02\x03\x04\x05\x06\x07\x08',
             0x0102030405060708L),
            (tag.SignedInteger(-1),'\x31\xff', -1),
            (tag.SignedInteger(255),'\x32\x00\xff', 255)):
            if signed.name != 'Signed Integer':
                raise 'Decoded BACnet Signed Integer incorrectly as',signed.name
            if signed.value != value:
                raise 'Decoded 0x%x as 0x%x' % (value, signed.value)
            if signed.encoding != encoding:
                raise 'Encoding failed'
    def test_decode_real(self):
        for data,value in (('\x44\x42\x90\x00\x00', 72.0),
                           ('\x44\x00\x00\x00\x00', 0.0),
                           ('\x44\x3f\x80\x00\x00', 1.0),
                           ('\x44\xbf\x80\x00\x00', -1.0)):
            for factory in (tag.Tag, tag.Real):
                t = factory(decode=data)
                if t.name != 'Real':
                    raise 'Decoded BACnet Real incorrectly as', t.name
                if t.value != value:
                    raise 'Decoded %s as %s' % (value, t.value)
    def test_encode_real(self):
        for real,encoding,value in ((tag.Real(72.0),
                                     '\x44\x42\x90\x00\x00',72.0),
                                    (tag.Real(0.0),'\x44\x00\x00\x00\x00', 0.0),
                                    (tag.Real(1.0),'\x44\x3f\x80\x00\x00', 1.0),
                                    (tag.Real(-1.0),
                                     '\x44\xbf\x80\x00\x00', -1.0)):
            if real.name != 'Real':
                raise 'Decoded BACnet Real incorrectly as', t.name
            if real.value != value:
                raise 'Decoded %s as %s' % (value, real.value)
            if real.encoding != encoding:
                raise 'Encoding failed'
    def test_decode_double(self):
        for data,value in (('\x55\x08\x40\x52\x00\x00\x00\x00\x00\x00', 72.0),
                           ('\x55\x08\x00\x00\x00\x00\x00\x00\x00\x00', 0.0),
                           ('\x55\x08\x3f\xf0\x00\x00\x00\x00\x00\x00', 1.0),
                           ('\x55\x08\xbf\xf0\x00\x00\x00\x00\x00\x00', -1.0)):
            for factory in (tag.Tag, tag.Double):
                t = factory(decode=data)
                if t.name != 'Double':
                    raise 'Decoded BACnet Double incorrectly as', t.name
                if t.value != value:
                    raise 'Decoded %s as %s' % (value, t.value)
    def test_encode_double(self):
        for double,encoding,value in (
            (tag.Double(72.0),'\x55\x08\x40\x52\x00\x00\x00\x00\x00\x00', 72.0),
            (tag.Double(0.0),'\x55\x08\x00\x00\x00\x00\x00\x00\x00\x00', 0.0),
            (tag.Double(1.0),'\x55\x08\x3f\xf0\x00\x00\x00\x00\x00\x00', 1.0),
            (tag.Double(-1.0),
             '\x55\x08\xbf\xf0\x00\x00\x00\x00\x00\x00', -1.0)):
            if double.name != 'Double':
                raise 'Decoded BACnet Double incorrectly as', double.name
            if double.value != value:
                raise 'Decoded %s as %s' % (value, double.value)
    def test_decode_octet_string(self):
        for data,value in (('\x63\x12\x34\xff', '\x12\x34\xff'),):
            for factory in (tag.Tag, tag.OctetString):
                t = factory(decode=data)
                if t.name != 'Octet String':
                    raise 'Decoded BACnet Octet String incorrectly as', t.name
                if t.value != value:
                    raise 'Decoded %s as %s' % (value, t.value)
    def test_encode_octet_string(self):
        for octet_string,encoding,value in \
            ((tag.OctetString('\x12\x34\xff'), '\x63\x12\x34\xff',
              '\x12\x34\xff'),):
            if octet_string.name != 'Octet String':
                raise 'Encoded BACnet Octet String incorrectly as', \
                      octet_string.name
            if octet_string.value != value:
                raise 'Encoded value %s as %s' % (value, octet_string.value)
            if octet_string.encoding != encoding:
                raise 'Encoded %s as %s' % (value, octet_string.value)
    def test_decode_character_string(self):
        for data,value in (('\x75\x19\x00This is a BACnet string!',
                            'This is a BACnet string!'),
                           ('\x75\x1B\x01\x03\x25This is a BACnet string!',
                            'This is a BACnet string!')):
            for factory in (tag.Tag, tag.CharacterString):
                t = factory(decode=data)
                if t.name != 'Character String':
                    raise 'Decoded BACnet Character String incorrectly as', \
                          t.name
                if str(t.value) != value:
                    raise 'Decoded %s as %s' % (value, t.value)
    def test_encode_character_string(self):
        for character_string,encoding,value in (
            (tag.CharacterString(data.ANSI_String('This is a BACnet string!')),
             '\x75\x19\x00This is a BACnet string!',
             'This is a BACnet string!'),
            (tag.CharacterString(data.DBCS_String('This is a BACnet string!',
                                                  805)),
             '\x75\x1B\x01\x03\x25This is a BACnet string!',
             'This is a BACnet string!')):
            if character_string.name != 'Character String':
                raise 'Encoded BACnet Character String incorrectly as', \
                      character_string.name
            if str(character_string.value) != value:
                raise 'Decoded %s as as %s' % (value, character_string.value)
            if encoding != character_string.encoding:
                raise 'Encoding failed'
    def test_decode_bit_string(self):
        for data,bits in (('\x82\x03\xa8', (1,0,1,0,1)),):
            t = tag.Tag(decode=data)
            if t.name != 'Bit String':
                raise 'Decoded BACnet Bit String incorrectly as', t.name
            if t.value.bits != bits:
                raise 'Decoded %s as %s' % (bits, t.value.bits)
    def test_encode_bit_string(self):
        for bit_string,encoding,bits in (
            (tag.BitString(data.BitString((1,0,1,0,1))),
             '\x82\x03\xa8', (1,0,1,0,1)),):
            if bit_string.name != 'Bit String':
                raise 'Encoded BACnet Bit String incorrectly as', t.name
            if bit_string.value.bits != bits:
                raise 'Encoded %s as %s' % (bits, t.value.bits)
            if bit_string.encoding != encoding:
                raise 'Encoding failed.'
    def test_decode_enumerated(self):
        for data,value in (('\x91\x00',0),):
            for factory in (tag.Tag, tag.Enumerated):
                t = factory(decode=data)
                if t.name != 'Enumerated':
                    raise 'Decoded BACnet Enumerated incorrectly as', t.name
                if t.value != value:
                    raise 'Decoded 0x%x as 0x%x' % (value, t.value)
    def test_encode_enumerated(self):
        for enumerated,encoding,value in ((tag.Enumerated(0),'\x91\x00',0),):
            if enumerated.name != 'Enumerated':
                raise 'Decoded BACnet Enumerated incorrectly as', \
                      enumerated.name
            if enumerated.value != value:
                raise 'Decoded 0x%x as 0x%x' % (value, enumerated.value)
            if enumerated.value != value:
                raise 'Decoded %s as %s' % (value, enumerated.value)
    def test_decode_date(self):
        for factory in (tag.Tag, tag.Date):
            t = factory(decode='\xa4\x5b\x01\x18\x04')
            if t.name != 'Date':
                raise 'Decoded BACnet Date incorrectly as', t.name
            d = t.value
            if d.year != 1991:
                raise 'Decoded year incorrectly'
            if d.month != 1:
                raise 'Decoded month incorrectly'
            if d.day != 24:
                raise 'Decoded day incorrectly'
            if d.day_of_week != 4:
                raise 'Decoded day_of_week incorrectly'
    def test_encode_date(self):
        t = tag.Date(data.Date(1991,1,24,4))
        if t.name != 'Date':
            raise 'Encoded BACnet Date incorrectly as', t.name
        if t.encoding != '\xa4\x5b\x01\x18\x04':
            raise 'Encoded date tag incorrectly'
        d = t.value
        if d.year != 1991:
            raise 'Encoded year incorrectly'
        if d.month != 1:
            raise 'Encoded month incorrectly'
        if d.day != 24:
            raise 'Encoded day incorrectly'
        if d.day_of_week != 4:
            raise 'Encoded day_of_week incorrectly'
        if d.encoding != '\x5b\x01\x18\x04':
            raise 'Encoded date object incorrectly'
    def test_decode_time(self):
        for factory in (tag.Tag, tag.Time):
            t = factory(decode='\xb4\x11\x23\x2d\x11')
            t = t.value
            if t.hour != 17:
                raise 'Decoded hour incorrectly'
            if t.minute != 35:
                raise 'Decoded minute incorrectly'
            if t.second != 45:
                raise 'Decoded second incorrectly'
            if t.hundredths != 17:
                raise 'Decoded hundredths incorrectly'
    def test_encode_time(self):
        t = tag.Time(data.Time(17,35,45,17))
        if t.name != 'Time':
            raise 'Encoded BACnet Time incorrectly as', t.name            
        if t.encoding != '\xb4\x11\x23\x2d\x11':
            raise 'Encoded time tag incorrectly'
        t = t.value
        if t.hour != 17:
            raise 'Encoded hour incorrectly'
        if t.minute != 35:
            raise 'Encoded minute incorrectly'
        if t.second != 45:
            raise 'Encoded second incorrectly'
        if t.hundredths != 17:
            raise 'Encoded hundredths incorrectly'
        if t.encoding != '\x11\x23\x2d\x11':
            raise 'Encoded time incorrectly'
    def test_decode_bacnet_object_identifier(self):
        for factory in (tag.Tag, tag.BACnetObjectIdentifier):
            t = factory(decode='\xc4\x00\xc0\x00\x0f')
            if t.name != 'BACnetObjectIdentifier':
                raise 'Decoded BACnetObjectIdentifier incorrectly as', t.name
            b = t.value
            if b.id != 0xc0000f:
                raise 'Incorrect BACnetObjectIdentifier id'
            if b.object_type != 0x3:
                raise 'Incorrect BACnetObjectIdentifier object_type'
            if b.instance_number != 0xf:
                raise 'Incorrect BACnetObjectIdentifier instance_number'
    def test_encode_bacnet_object_identifier(self):
        t = tag.BACnetObjectIdentifier(data.BACnetObjectIdentifier(0x3,0xf))
        if t.name != 'BACnetObjectIdentifier':
            raise 'Encoded BACnetObjectIdentifier incorrectly as', t.name
        b = t.value
        if b.id != 0xc0000f:
            raise 'Incorrect BACnetObjectIdentifier id'
        if b.object_type != 0x3:
            raise 'Incorrect BACnetObjectIdentifier object_type'
        if b.instance_number != 0xf:
            raise 'Incorrect BACnetObjectIdentifier instance_number'
    def test_decode_context_tag(self):
        for encoding, data in (('\x69\x00','\x00'), ('\x08', '')):
            for factory in (tag.Tag, tag.Context):
                c = factory(decode=encoding)
                if c.data != data:
                    raise 'Encoded data incorrectly using', factory
                if c.encoding != encoding:
                    raise 'Rencoded incorrectly using', factory
    def test_encode_context_tag(self):
        for c, encoding, data in ((tag.Context(6, '\x00'),'\x69\x00','\x00'),
                                  (tag.Context(0, ''),'\x08', '')):
            if c.data != data:
                raise 'Encoded data incorrectly'
            if c.encoding != encoding:
                raise 'Rencoded incorrectly'
    def test_decode_open(self):
        for data, number in (('\x1e', 1), ('\x0e', 0), ('\xfe\x18', 24)):
            for factory in (tag.Tag, tag.Open):
                o = factory(decode=data)
                if o.name != 'Open':
                    raise 'Decoded Open as %s using %s' % (o.name, factory)
                if o.number != number:
                    raise 'Decoded tag number %s as %s using %s' % \
                          (number, o.number, factory)
                if not o.is_context:
                    raise 'Decoded as not context using %s' % factory
                if not o.is_open:
                    raise 'Decoded as not open using %s' % factory
                if o.is_close:
                    raise 'Decoded as close using %s' % factory
                if o.data != '':
                    raise 'Decode invented %s as data' % o.data
    def test_encode_open(self):
        for o, encoding, number in ((tag.Open(1), '\x1e', 1),
                                    (tag.Open(0), '\x0e', 0),
                                    (tag.Open(24), '\xfe\x18', 24)):
            if o.name != 'Open':
                raise 'Encoded Open as %s'
            if o.number != number:
                raise 'Encoded tag number %s' % (number, o.number)
            if not o.is_context:
                raise 'Encoded as not context'
            if not o.is_open:
                raise 'Encoded as not open'
            if o.is_close:
                raise 'Encoded as close'
            if o.data != '':
                raise 'Encode invented %s as data' % o.data
            if o.encoding != encoding:
                raise 'Encoded %s as %s' % (encoding, o.encoding)
    def test_decode_close(self):
        for data, number in (('\x1f', 1), ('\x0f', 0), ('\xff\x18', 24)):
            for factory in (tag.Tag, tag.Close):
                c = factory(decode=data)
                if c.name != 'Close':
                    raise 'Decoded Close as %s using %s' % (c.name, factory)
                if c.number != number:
                    raise 'Decoded tag number %s as %s using %s' % \
                          (number, c.number, factory)
                if not c.is_context:
                    raise 'Decoded as not context using %s' % factory
                if c.is_open:
                    raise 'Decoded as open using %s' % factory
                if not c.is_close:
                    raise 'Decoded as not close using %s' % factory
                if c.data != '':
                    raise 'Decode invented %s as data' % c.data
    def test_encode_close(self):
        for o, encoding, number in ((tag.Close(1), '\x1f', 1),
                                    (tag.Close(0), '\x0f', 0),
                                    (tag.Close(24), '\xff\x18', 24)):
            if o.name != 'Close':
                raise 'Encoded Close as %s'
            if o.number != number:
                raise 'Encoded tag number %s' % (number, o.number)
            if not o.is_context:
                raise 'Encoded as not context'
            if o.is_open:
                raise 'Encoded as open'
            if not o.is_close:
                raise 'Encoded as not close'
            if o.data != '':
                raise 'Encode invented %s as data' % o.data
            if o.encoding != encoding:
                raise 'Encoded %s as %s' % (encoding, o.encoding)

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

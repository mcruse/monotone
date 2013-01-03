"""
Copyright (C) 2002 2003 2005 2007 2008 2009 2010 2011 Cisco Systems

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
# This module assists with the encoding and decoding of BACnet ASN.1
# SEQUENCEs.  A SEQUENCE is decoded from a list of <code>Tag</code>s
# and encoded into a list <code>Tag</code>s.
# @todo Support CHOICEs.
# @note It's all symetrical...
# @note Context sequences require the use of KEYWORD arguments
#       Application sequence arguments are POSITIONAL, since there
#       are no optional arguments in the middle of the list

# @fixme Add encoding into a list of tags.

import copy
import string
import array
import struct

from mpx.lib import exceptions, EnumeratedValue
import tag
from data import decode_bacnet_object_identifier, \
     decode_bit_string, \
     encode_bit_string, \
     decode_date, \
     decode_enumerated, \
     encode_enumerated, \
     decode_real, \
     encode_real, \
     decode_signed_integer, \
     encode_signed_integer, \
     decode_time, \
     encode_time, \
     decode_unsigned_integer, \
     encode_unsigned_integer, \
     decode_octet_string, \
     encode_octet_string
import mpx.lib.debug as _debug

def application_encode_enumerated(value):
    return tag.Enumerated(value)
def application_encode_real(value):
    return tag.Real(value)
def application_encode_boolean(value):
    return tag.Boolean(value)
def application_encode_bacnet_object_identifier(boid):
    return tag.BACnetObjectIdentifier(boid)
def application_encode_unsigned_integer(value):
    return tag.UnsignedInteger(value)
def application_encode_unsigned_integer8(value):
    if value > 255 or value < 0:
        raise EInvalidValue, 'must be 8 bit value'
    return application_encode_unsigned_integer(value)
def application_encode_unsigned_integer16(value):
    if value > 65535 or value < 0:
        raise EInvalidValue, 'must be 16 bit value'
    return application_encode_unsigned_integer(value)
def application_encode_unsigned_integer32(value):
    if value < 0:
        raise EInvalidValue, 'must be positive value'
    return application_encode_unsigned_integer(value)
def application_encode_octet_string(value):
    return tag.OctetString(value)
##
# Decode any application tag.
# @param tag An application tag (A <code>Tag</code> where
#            tag.is_application != 0)
# @return A Python instance representing the encoded value.
def application_encode_bacnet_address(value):
    v=value
    return value.encoding
def application_decode(tag):
    #define BACNET_NULL 0
    #define BOOLEAN 1
    #define UNSIGNED_INTEGER 2
    #define SIGNED_INTEGER 3    // (2's complement notation)
    #define REAL 4		    // (ANSI/IEEE-754 floating point)
    #define DOUBLE 5	    // (ANSI/IEEE-754 double precision floating port)
    #define OCTET_STRING 6
    #define CHARACTER_STRING 7
    #define BIT_STRING 8
    #define ENUMERATED 9
    #define DATE 10
    #define TIME 11
    #define BACNETOBJECTIDENTIFIER 12
    try:
        if tag.number == 1: #"Boolean":
            return bool(tag.value)
        if tag.number == 9: #"Enumerated":
            return EnumeratedValue(tag.value, str(tag.value))
    except:
        pass
    return tag.value
def application_encode_sequence_of(number, list):
    result = []
    for tags in list:
        result.extend(tags)
    return result
##
# Decode a context tag containing an encoded BACnetObjectIdentifer.
# @param tag A context tag containing an encoded BACnetObjectIdentifer.
# @return A BACnetObjectIdentifer instance representing the encoded value.
def context_decode_bacnet_object_identifier(tag):
    return decode_bacnet_object_identifier(tag.data)

##
# Decode a context tag containing an Octet String.
# @param tag A context tag containing an encoded Unsigned Integer.
# @return A  Python string representing the encoded value.
def context_decode_octet_string(tag):
    return decode_octet_string(tag.data)

def context_encode_octet_string(number, value):
    return tag.Context(number, encode_octet_string(value))

##
# Decode a context tag containing an encoded Unsigned Integer.
# @param tag A context tag containing an encoded Unsigned Integer.
# @return A positive Python integer representing the encoded value.
def context_decode_unsigned_integer(tag):
    return decode_unsigned_integer(tag.data)

def context_encode_unsigned_integer(number, value):
    return tag.Context(number, encode_unsigned_integer(value))

##
# Decode a context tag containing an encoded Unsigned Integer.
# @param tag A context tag containing an encoded Unsigned Integer.
# @return A positive Python integer representing the encoded value.
# @fixme Raise exception if value > 8 bits.
def context_decode_unsigned_integer8(tag):
    return decode_unsigned_integer(tag.data)

##
# @fixme Raise exception if value > 8 bits.
def context_encode_unsigned_integer8(number, value):
    return tag.Context(number, encode_unsigned_integer(value))

##
# Decode a context tag containing an encoded BACnetDateRange.
# @param tag A context tag containing an encoded BACnetDateRange.
# @return A BACnetDateRange instance representing the encoded value.
def context_decode_bacnet_date_range(construct_tag):
    return BACnetDateRange(decode=construct_tag.value)

def context_decode_bacnet_date_range_list(tag):
    return ContextDecodeSequenceOf(context_decode_bacnet_date_range)(tag)

def context_encode_bacnet_date_range(number, date_range):
    return tag.Construct(number, date_range.encoding)

##
# Decode a context tag containing an encoded BACnetDate.
# @param tag A context tag containing an encoded BACnetDate.
# @return A BACnetDate instance representing the encoded value.
def context_decode_date(tag):
    return decode_date(tag.data)
def context_encode_date(number, date):
    #print "context_encode_date: ", date.year, date.month, date.day
    answer = tag.Context(number, date.encoding)
    #print "   context_encode_date encoding: ", repr(answer)
    return answer

##
# Decode a context tag containing an encoded BACnetTime.
# @param tag A context tag containing an encoded BACnetTime.
# @return A BACnetTime instance representing the encoded value.
def context_decode_time(tag):
    return decode_time(tag.data)

def context_encode_time(number, time):
    return tag.Context(number, time.encoding)

##
# Decode a context tag containing an encoded BACnetBitString.
# @param tag A context tag containing an encoded BACnetBitString.
# @return A BACnetBitString instance representing the encoded value.
def context_decode_bit_string(tag):
    return decode_bit_string(tag.data)

def context_encode_bit_string(number, bit_string):
    return tag.Context(number, bit_string.encoding)

##
# Decode a context tag containing an encoded Enumerated.
# @param tag A context tag containing an encoded Enumerated.
# @return A positive Python integer representing the encoded value.
def context_decode_enumerated(tag):
    return decode_enumerated(tag.data)

def context_encode_enumerated(number, value):
    return tag.Context(number, encode_enumerated(value))

##
# Decode a context tag containing an encoded Signed Integer.
# @param tag A context tag containing an encoded Signed Integer.
# @return A Python integer representing the encoded value.
def context_decode_signed_integer(tag):
    return decode_signed_integer(tag.data)

def context_encode_signed_integer(number, value):
    return tag.Context(number, encode_signed_integer(value))

##
# Decode a context tag containing an encoded Null.
# @param tag A context tag containing an encoded Null.
# @return <code>None</code> (the Python representation of Null).
# @note This is not coverred in the BACnet specification, but exists in some
#       systems.
def context_decode_null(tag):
    return None

def context_encode_null(number, value):
    return tag.Context(number, '')

##
# Decode a context tag containing an encoded Real.
# @param tag A context tag containing an encoded Real.
# @return A Python float representing the encoded value.
def context_decode_real(tag):
    return decode_real(tag.data)

def context_encode_real(number, real):
    return tag.Context(number, encode_real(real))

##
# Decode a construct containing...
def application_tag_from_simple_construct(tag):
    return tag.value[0]

def application_tag_as_simple_construct(number, apptag):
    return tag.Construct(number, [apptag])

##
# Decode a construct containing and single application value.
def application_decode_simple_construct(tag):
    return tag.value[0].value

##
# Encode a BACnetDate into an application tag.
# @param date The BACnetDate instance to encode into an application tag.
# @return The encoded <code>Date</code> application tag.
def application_encode_date(date):
    t = tag.Date(date)
    return t

##
# Encode a BACnetTime into an application tag.
# @param time The BACnetTime instance to encode into an application tag.
# @return The encoded <code>Time</code> application tag.
def application_encode_time(time):
    return tag.Time(time)

##
#Encode any kind of primitive datatype (within limits) used by TimeValue
tag_types = (tag.NullType,tag.BooleanType,tag.UnsignedIntegerType,
        tag.SignedIntegerType,tag.RealType,tag.DoubleType,
        tag.OctetStringType,tag.CharacterStringType,tag.BitStringType,
        tag.EnumeratedType,tag.DateType,tag.TimeType,
        tag.BACnetObjectIdentifierType)

def application_encode_abstract(value):
    if type(value) in tag_types: #any tag object will just pass through
        return value
    if value is None:
        return tag.Null()
    if isinstance(value, EnumeratedValue):
        return application_encode_enumerated(value)
    if isinstance(value, float):
        return application_encode_real(value)
    if isinstance(value, bool):
        return application_encode_boolean(value)
    if isinstance(value, int):
        if value >= 0:
            return application_encode_unsigned_integer(value)
        return application_encode_signed_integer(value)
    return tag.encode(value) #let tag module figure it out
##
# Encode a BACnetObjectIdentifier as a <code>Context</code> tag with
# a tag number of <code>context</code>.
# @param context An integer value that is the tag's context number.
# @param boid A BACnetObjectIdentifier.
# @return A Context tag.
def context_encode_bacnet_object_identifier(context, boid):
    return tag.Context(context, boid)

class ETagMissing(exceptions.MpxException):
    pass

class _REQUIRED:
    def __str__(self):
        return 'REQUIRED'
    def __repr__(self):
        return self.__module__ + '.REQUIRED'

class _OPTIONAL:
    def __str__(self):
        return 'OPTIONAL'
    def __repr__(self):
        return self.__module__ + '.OPTIONAL'

class _CHOICE:
    def __str__(self):
        return 'CHOICE'
    def __repr__(self):
        return self.__module__ + '.CHOICE'

REQUIRED = _REQUIRED()
OPTIONAL = _OPTIONAL()
CHOICE   = _CHOICE()

debug = 0

##
# Describes the decoder and default value for a relative tag in a
# <code>ApplicationSequence</code>.
class ApplicationSequenceEntry:
    ##
    # @param name A string representing the name of the attribute.
    # @param decoder A function that will decode the tag into a value.
    # @param encoder A function that will encode an attribute into
    #                a tag.
    # @param default The default value to use if the tag is not in the
    #                SEQUENCE being decoded.  There are
    #                two special values:  REQUIRED and OPTIONAL.  REQUIRED
    #                will cause the the ApplicationSequence.decode() method
    #                to raise an exception if the SEQUENCE does not
    #                contain this entry.  OPTIONAL provides a
    #                unique object to identify attributes that were not
    #                in the construct.
    # @param choice_key Optional value used to group choices.  Only required
    #                   if a SEQUENCE contains more than one choice.
    # @todo Establish OPTIONAL rules.  Does BACnet allow non-trailing tags
    #       to be OPTIONAL.  I hope not...
    def __init__(self, name, decoder, encoder, default, choice_key=None):
        self.name = name
        self.decoder = decoder
        self.encoder = encoder
        self.default = default
        self.choice_key = choice_key

##
# A ApplicationSequence maps an ANS.1 SEQUENCE definition into an
# object with attributes that match the SEQUENCE's attribute names.
# It is a SEQUENCE of APPLICATION tags.
# @note This base class is used for SEQUENCES based on a tag's position
#       in the list.
# @note Implementation relies on OPTIONAL tags residing at the end
#       of the list.
# @todo Consider lazy decoding via __getattr__.
class ApplicationSequence:
    _sequence_map = []
    def __init__(self, *args, **keywords):
        self.tag_count = 0
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            apply(self.encode, args)
    def __str__(self):
        result = array.array('c', self.__class__.__name__)
        result.fromstring(':')
        for entry in self._sequence_map:
            if hasattr(self, entry.name):
                next_str = str(getattr(self, entry.name))
            else:
                next_str = str(getattr(self, entry.default))
            next_str = string.join(string.split(next_str, '\n'),'\n  ')
            result.fromstring('\n  %s = %s' % (entry.name, next_str))
        return result.tostring()
    def __getattr__(self, attribute):
        if attribute == "encoding":
            return self._encoding()
        try: 
            return self.__dict__[attribute]
        except KeyError: 
            raise AttributeError(attribute)
    def decode(self, tag_list):
        self.tag_count = 0
        map = copy.copy(self._sequence_map)
        for tag in tag_list:
            if not map:
                if debug: print 'Exiting:  Map empty'
                break
            entry = map.pop(0)
            if debug: print 'Setting:  %s to %s' % (entry.name,
                                                    entry.decoder(tag))
            setattr(self, entry.name, entry.decoder(tag))
            self.tag_count += 1
        for entry in map:
            if entry.default == REQUIRED:
                raise ETagMissing(entry.name)
            setattr(self, entry.name, entry.default)
    def encode(self, *args):
        if len(args) == 0:
            for entry in self._sequence_map:
                setattr(self, entry.name, entry.default)
        elif len(args) > len(self._sequence_map):
            raise exceptions.ETypeError('Too many arguments.')
        else:
            for i in range(0,len(args)):
                setattr(self, self._sequence_map[i].name, args[i])
            for i in range(len(args),len(self._sequence_map)):
                entry = self._sequence_map[i]
                if (entry.default == REQUIRED):
                    raise exceptions.ETypeError('Too few arguments.')
                setattr(self, entry.name, entry.default)
    def _encoding(self):
        encoding = []
        for entry in self._sequence_map:
            if hasattr(self, entry.name):
                encoding.append(entry.encoder(getattr(self, entry.name)))
            elif entry.default == OPTIONAL:
                pass
            elif entry.default == REQUIRED:
                raise exceptions.EAttributeError(entry.name)
            else:
                encoding.append(entry.encoder(entry.default))
        return encoding

##
# Describes the decoder and default value for a context tag in a
# <code>ContextSequence</code>.
    def __repr__(self):
        return repr(self.as_dict())
    def as_dict(self):
        d = {}
        d['__base__'] = 'ApplicationSequence'
        d['__class__'] = exceptions.class_path_of(self)
        d['str'] = self.__str__()
        for entry in self._sequence_map:
            if hasattr(self, entry.name):
                d[entry.name] = getattr(self, entry.name)
            else:
                d[entry.name] = getattr(self, entry.default)
        return d
        
class ContextSequenceEntry:
    ##
    # @param name A string representing the name of the attribute.
    # @param decoder A function that will convert a <code>Context</code> tag
    #                to the appropriate data type.
    # @param encoder A function that will encode an attribute into
    #                a context tag.
    # @param default The default value to use if the <code>Context</code>
    #                tag is not in the construct being decoded.  There are
    #                two special values:  REQUIRED and OPTIONAL.  REQUIRED
    #                will cause the the ContextSequence.decode() method
    #                to raise an exception if the construct does not
    #                contain this entry's context.  OPTIONAL provides a
    #                unique object to identify attributes that were not
    #                in the construct.
    # @param choice_key Optional value used to group choices.  Only required
    #                   if a SEQUENCE contains more than one choice.
    def __init__(self, name, decoder, encoder, default, choice_key=None):
        self.name = name
        self.decoder = decoder
        self.encoder = encoder
        self.default = default
        self.choice_key = choice_key

##
# A ContextSequence maps an ANS.1 SEQUENCE definition into an
# object with attributes that match the SEQUENCE's attribute names.
# It is a SEQUENCE of CONTEXT tags.
# @note This base class is used for SEQUENCES based on context tags,
#       not position.
# @todo Consider lazy decoding via __getattr__.
class ContextSequence:
    _sequence_map = {}
    def __init__(self, *args, **keywords):
        if not hasattr(self.__class__, '_attribute_map'):
            self.__class__._attribute_map = {}
            for context, entry in self._sequence_map.items():
                entry.context = context # Context tag number.
                self.__class__._attribute_map[entry.name] = entry
        self.tag_count = 0
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            apply(self.encode, args, keywords)
    def __str__(self):
        result = array.array('c', self.__class__.__name__)
        result.fromstring(':')
        for entry in self._sequence_map.values():
            if hasattr(self, entry.name):
                next_str = str(getattr(self, entry.name))
            else:
                next_str = str(getattr(self, entry.default))
            next_str = string.join(string.split(next_str, '\n'),'\n  ')
            result.fromstring('\n  %s = %s' % (entry.name, next_str))
        return result.tostring()
    def __getattr__(self, attribute):
        if attribute == "encoding":
            return self._encoding()
        try: 
            return self.__dict__[attribute]
        except KeyError: 
            raise AttributeError(attribute)
    def decode(self, tag_list):
        self.tag_count = 0
        map = copy.copy(self._sequence_map)
        choices = {}
        for tag in tag_list:
            if not map:
                if debug: print 'Exiting:  Map empty'
                break
            if tag.is_context and map.has_key(tag.number):
                entry = map[tag.number]
                if entry.default == CHOICE:
                    if choices.has_key(entry.choice_key):
                        if debug: print 'Exiting:  Choice already used. (%s)'\
                           % entry.choice_key
                        break
                    else:
                        choices[entry.choice_key] = entry
                del map[tag.number]
                if debug: print 'Setting:  %s to %s from context %d' % \
                   (entry.name, entry.decoder(tag), tag.number)
                setattr(self, entry.name, entry.decoder(tag))
                self.tag_count += 1
            else:
                if debug:
                    print 'Exiting:  Unknown tag #%d' % tag.number
                    print 'Map: ', map
                    print 'Tag number:', tag.number
                    print 'Tag data:', repr(tag.data)
                break
        for entry in map.values():
            if entry.default == REQUIRED:
                raise ETagMissing(entry.name)
            setattr(self, entry.name, entry.default)
    def encode(self, *args, **keywords):
        if len(args) != 0:
            raise exceptions.ETypeError(
                'ContextSequence only expects keyword arguments.')
        if len(keywords) == 0:
            for entry in self._sequence_map.values():
                setattr(self, entry.name, entry.default)
        else:
            map = copy.copy(self._attribute_map)
            for attribute,value in keywords.items():
                if map.has_key(attribute):
                    entry = map[attribute]
                    del map[attribute]
                    setattr(self, attribute, value)
                else:
                    raise exceptions.ETypeError('Unknown keyword ' + attribute)
            for entry in map.values():
                if entry.default is REQUIRED:
                    raise exceptions.EAttributeError(
                        'missing required attribute ' + repr(entry.name))
                setattr(self, entry.name, entry.default)
    def _encoding(self):
        encoding = []
        keys = self._sequence_map.keys()
        keys.sort()
        for key in keys:
            entry = self._sequence_map[key]
            if hasattr(self, entry.name):
                value = getattr(self, entry.name)
                if value is REQUIRED:
                    raise exceptions.EAttributeError(entry.name)
                elif value is not OPTIONAL and value is not CHOICE:
                    encoding.append(entry.encoder(entry.context, value))
            elif entry.default is OPTIONAL:
                pass
            elif entry.default is REQUIRED:
                raise exceptions.EAttributeError(entry.name)
            else:
                encoding.append(entry.encoder(entry.default))
        return encoding

##
# Decodes a SEQUENCE of a SEQUENCE.
    def __repr__(self):
        return repr(self.as_dict())
    def as_dict(self):
        d = {}
        d['__base__'] = 'ContextSequence'
        d['__class__'] = exceptions.class_path_of(self)
        d['str'] = self.__str__()
        for entry in self._sequence_map.values():
            if hasattr(self, entry.name):
                d[entry.name] = getattr(self, entry.name)
            else:
                d[entry.name] = getattr(self, entry.default)
        return d
class ContextDecodeSequenceOf:
    class DecoderTag:
        def __init__(self, list):
            self.value = list
    def __init__(self, decode_function):
        self.decode = decode_function
    def __call__(self, construct_tag):
        tag_count = 0
        result = []
        while tag_count < len(construct_tag.value):
            tag = self.DecoderTag(construct_tag.value[tag_count:])
            seq = self.decode(tag)
            tag_count += seq.tag_count
            result.append(seq)
        return result
#class ContextEncodeSequenceOf:
    #class EncoderTag:
        #def __init__(self, list):
            #self.value = list
    #def __init__(self, encode_function):
        #self.encode = encode_function
    #def __call__(self, number, list):
        #tag_count = 0
        #result = []
        #while tag_count < len(list):
            #value = list[tag_count]
            #seq = self.encode(value)
            #tag_count += 1
            #result.append(seq)
        #return tag.Construct(number, result)
class BACnetDateRange(ApplicationSequence):
    _sequence_map = [
        ApplicationSequenceEntry('start_date',
                              application_decode,
                              application_encode_date,
                              REQUIRED),
        ApplicationSequenceEntry('end_date',
                              application_decode,
                              application_encode_date,
                              REQUIRED)
        ]
class BACnetAddress(ApplicationSequence):
    _sequence_map = [
        ApplicationSequenceEntry('network_number',
                              application_decode,
                              application_encode_unsigned_integer16,
                              REQUIRED),
        ApplicationSequenceEntry('mac_address',
                              application_decode,
                              application_encode_octet_string,
                              REQUIRED)
        ]
def context_decode_bacnet_address(tag):    
    return BACnetAddress(decode=tag.value)
def context_decode_bacnet_address_list(tag):
    return ContextDecodeSequenceOf(context_decode_bacnet_address)(tag)
def context_encode_bacnet_address(number, addr):
    return tag.Context(number, addr.encoding)    

class BACnetAddressBinding(ApplicationSequence):
    _sequence_map = [
        ApplicationSequenceEntry('device_object_identifier',
                              application_decode,
                              application_encode_bacnet_object_identifier,
                              REQUIRED),
        ApplicationSequenceEntry('network_number',
                              application_decode,
                              application_encode_unsigned_integer16,
                              REQUIRED),
        ApplicationSequenceEntry('mac_address',
                              application_decode,
                              application_encode_octet_string,
                              REQUIRED)
        ]
def context_decode_address_binding(tag):    
    return BACnetAddressBinding(decode=tag.value)
def context_decode_address_binding_list(tag):
    return ContextDecodeSequenceOf(context_decode_address_binding)(tag)
class BACnetIAm(ApplicationSequence):
    _sequence_map = [
        ApplicationSequenceEntry('device_object_identifier',
                              None,
                              application_encode_bacnet_object_identifier,
                              REQUIRED),
        ApplicationSequenceEntry('max_apdu_length_accepted',
                              None,
                              application_encode_unsigned_integer16,
                              REQUIRED),
        ApplicationSequenceEntry('segmentation_supported',
                              None,
                              application_encode_enumerated,
                              REQUIRED),
        ApplicationSequenceEntry('vendor_id',
                              None,
                              application_encode_unsigned_integer,
                              REQUIRED)
        ]
                     
class BACnetDateTime(ApplicationSequence):
    _sequence_map = [
        ApplicationSequenceEntry('date',
                                 application_decode,
                                 application_encode_date,
                                 REQUIRED),
        ApplicationSequenceEntry('time',
                                 application_decode,
                                 application_encode_time,
                                 REQUIRED)
        ]
def context_decode_date_time(tag):
    return BACnetDateTime(decode=tag.value)
def context_decode_date_time_list(tag):
    return ContextDecodeSequenceOf(context_decode_date_time)(tag)
class BACnetTimeValue(ApplicationSequence):
    _sequence_map = [
        ApplicationSequenceEntry('time',
                                 application_decode,
                                 application_encode_time,
                                 REQUIRED),
        ApplicationSequenceEntry('value',
                                 application_decode,
                                 application_encode_abstract,
                                 REQUIRED),
        ]
def context_decode_bacnet_time_value(tag):
    return BACnetTimeValue(decode=tag.value)
def context_decode_bacnet_time_value_list(tag):
    return ContextDecodeSequenceOf(context_decode_bacnet_time_value)(tag)
def context_encode_bacnet_time_value(number, tv):
    return tag.Context(number, tv.encoding)
def context_encode_bacnet_time_value_list(number, tvs):
    return context_encode_sequence_of(number, [tv.encoding for tv in tvs])
def context_decode_bacnet_daily_schedule(tag):
    return BACnetDailySchedule(decode=tag.value)
def context_decode_bacnet_daily_schedule_list(tag):
    return ContextDecodeSequenceOf(context_decode_bacnet_daily_schedule)(tag)
class Error(ApplicationSequence):
    _error_class_map = {
        0:'device',
        1:'object',
        2:'property',
        3:'resources',
        4:'security',
        5:'services',
        6:'vt'
        }
    _error_code_map = {
        0:'other',
        1:'authentication-failed',
        41:'character-set-not-supported',
        2:'configuration-in-progress',
        3:'device-busy',
        4:'dynamic-creation-not-supported',
        5:'file-access-denied',
        6:'incompatible-security-levels',
        7:'inconsistent-parameters',
        8:'inconsistent-selection-criterion',
        42:'invalid-array-index',
        46:'invalid-configuration-data',
        9:'invalid-data-type',
        10:'invalid-file-access-method',
        11:'invalid-file-start-position',
        12:'invalid-operator-name',
        13:'invalid-parameter-data-type',
        14:'invalid-time-stamp',
        15:'key-generation-error',
        16:'missing-required-parameter',
        17:'no-objects-of-specified-type',
        18:'no-space-for-object',
        19:'no-space-to-add-list-element',
        20:'no-space-to-write-property',
        21:'no-vt-sessions-available',
        23:'object-deletion-not-permitted',
        24:'object-identifier-already-exists',
        25:'operational-problem',
        45:'optional-functionality-not-supported',
        26:'password-failure',
        22:'property-is-not-a-list',
        27:'read-access-denied',
        28:'security-not-supported',
        29:'service-request-denied',
        30:'timeout',
        31:'unknown-object',
        32:'unknown-property',
        33:'this enumeration was removed',
        34:'unknown-vt-class',
        35:'unknown-vt-session',
        36:'unsupported-object-type',
        37:'value-out-of-range',
        38:'vt-session-already-closed',
        39:'vt-session-termination-failure',
        40:'write-access-denied',
        43:'cov-subscription-failed',
        44:'not-cov-property'
        }
    _sequence_map = [
        ApplicationSequenceEntry('error_class',
                                 application_decode,
                                 application_encode_enumerated,
                                 REQUIRED),
        ApplicationSequenceEntry('error_code',
                                 application_decode,
                                 application_encode_enumerated,
                                 REQUIRED)
        ]
    def __str__(self):
        if self._error_class_map.has_key(self.error_class):
            error_class = self._error_class_map[self.error_class]
        else:
            error_class = "unknown"
        if self._error_code_map.has_key(self.error_code):
            error_code = self._error_code_map[self.error_code]
        else:
            error_code = "unknown"
        return "Error:\n  error-class: %s (%s)\n  error-code: %s (%s)" % \
               (error_class, self.error_class, error_code, self.error_code)
    def error_class_str(self, error_class=None):
        if error_class is None:
            error_class = self.error_class
        if self._error_class_map.has_key(error_class):
            return self._error_class_map[error_class]
        return "unknown"
    def error_code_str(self, error_code=None):
        if error_code is None:
            error_code = self.error_code
        if self._error_code_map.has_key(error_code):
            return self._error_code_map[error_code]
        return "unknown"

def context_decode_abstract_type(tag):
    return tag.value

def context_encode_abstract_type(number, list):
    return tag.Construct(number, list)
def context_encode_sequence_of(number, list):
    result = []
    for tags in list:
        result.extend(tags)
    return tag.Construct(number, result)

def context_decode_access_error(tag):
    return Error(decode=tag.value)

def context_encode_access_error(number, value):
    return tag.Construct(number, tag.encode(value))

def context_decode_read_property_multiple_result(construct):
    return _ReadPropertyMultipleResult(decode=construct.value)
def context_decode_read_property_reference(construct):
    return BACnetPropertyReference(decode=construct.value)
def context_decode_write_property_value(construct):
    return BACnetPropertyValue(decode=construct.value)
def context_decode_cov_property_value_list(construct):
    return BACnetPropertyValue(decode=construct.value) 
def context_decode_action_command(construct):
    #untested
    return BACnetActionCommand(decode=construct.value)
def context_encode_action_command(number, list):
    #untested
    return tag.Construct(number, list)

def context_encode_write_property_value(number, pv):
    return tag.Construct(number, pv.encoding)
def context_encode_write_property_value_list(number, list):
    construct = tag.Construct(number)
    for item in list:
        construct.value.extend(context_encode_write_property_value\
                               (None,item).value)
    return construct

class WritePropertyRequest(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        2:ContextSequenceEntry('property_array_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        3:ContextSequenceEntry('property_value',
                               context_decode_abstract_type,
                               context_encode_abstract_type,
                               REQUIRED),
        4:ContextSequenceEntry('priority',
                               context_decode_unsigned_integer8,
                               context_encode_unsigned_integer8,
                               OPTIONAL)
        }

class ReadPropertyRequest(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        2:ContextSequenceEntry('property_array_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL)
        }

class CovNotification(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('pid',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               REQUIRED),
        1:ContextSequenceEntry('device_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        2:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        3:ContextSequenceEntry('time_remaining',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               REQUIRED),
        4:ContextSequenceEntry('list_of_property_values',
                               ContextDecodeSequenceOf\
                               (context_decode_cov_property_value_list),
                               None,
                               REQUIRED)
}

class ReadPropertyACK(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        2:ContextSequenceEntry('property_array_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        3:ContextSequenceEntry('property_value',
                               context_decode_abstract_type,
                               context_encode_abstract_type,
                               REQUIRED)
        }

class _ReadPropertyMultipleResult(ContextSequence):
    _sequence_map = {
        2:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        3:ContextSequenceEntry('property_array_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        4:ContextSequenceEntry('property_value',
                               context_decode_abstract_type,
                               context_encode_abstract_type,
                               OPTIONAL),
        5:ContextSequenceEntry('property_access_error',
                               context_decode_access_error,
                               context_encode_access_error,
                               OPTIONAL),
        }

class ReadAccessResult(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('list_of_results',
                               ContextDecodeSequenceOf\
                               (context_decode_read_property_multiple_result),
                               context_encode_sequence_of,
                               OPTIONAL)
        }
class ReadAccessSpecification(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('list_of_specs',
                               ContextDecodeSequenceOf\
                               (context_decode_read_property_reference),
                               None,
                               OPTIONAL)
        }
class WriteAccessSpecification(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('list_of_properties',
                               ContextDecodeSequenceOf\
                               (context_decode_write_property_value),
                               context_encode_write_property_value_list,
                               REQUIRED)
        }

class ConfirmedPrivateTransferRequest(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('vendor_id',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               REQUIRED),
        1:ContextSequenceEntry('service_number',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               REQUIRED),
        2:ContextSequenceEntry('service_parameters',
                               context_decode_abstract_type,
                               context_encode_abstract_type,
                               OPTIONAL)
        }

class BACnetObjectPropertyReference(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        2:ContextSequenceEntry('property_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL)
        }
class BACnetPropertyReference(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        1:ContextSequenceEntry('property_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL)
        }
class BACnetDeviceObjectPropertyReference(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        1:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        2:ContextSequenceEntry('property_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        3:ContextSequenceEntry('device_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               OPTIONAL),
        }
def context_decode_device_object_property_reference(tag):
    return BACnetDeviceObjectPropertyReference(decode=tag.value)
def context_decode_object_property_reference_list(tag):
    return ContextDecodeSequenceOf(context_decode_device_object_property_reference)(tag)
def context_encode_object_property_reference(number, ce):
    #print "context_encode_calendar_entry: ", repr(ce),
    #print repr(ce.encoding)
    return tag.Construct(number, ce.encoding)
class BACnetActionCommand(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('device_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               OPTIONAL),
        1:ContextSequenceEntry('object_identifier',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               REQUIRED),
        2:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        3:ContextSequenceEntry('property_array_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        4:ContextSequenceEntry('property_value',
                               context_decode_abstract_type,
                               context_encode_abstract_type,
                               REQUIRED),
        5:ContextSequenceEntry('priority',
                               context_decode_unsigned_integer8,
                               context_encode_unsigned_integer8,
                               OPTIONAL),
        6:ContextSequenceEntry('post_delay',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        7:ContextSequenceEntry('quit_on_failure',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        8:ContextSequenceEntry('write_successful',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED)
        }
class BACnetActionList(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('action',
                               ContextDecodeSequenceOf\
                               (context_decode_action_command),
                               context_encode_sequence_of,
                               REQUIRED)
        }
    #looks like ContextDecodeSequenceOf will work for encoding too
class BACnetCalendarEntry(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('date',
                               context_decode_date,
                               context_encode_date,
                               CHOICE),
        1:ContextSequenceEntry('date_range',
                               context_decode_bacnet_date_range,
                               context_encode_bacnet_date_range,
                               CHOICE),
        2:ContextSequenceEntry('week_n_day',
                               context_decode_octet_string, 
                               context_encode_octet_string,
                               CHOICE)
        }
def context_decode_calendar_entry(tag):
    return BACnetCalendarEntry(decode=tag.value)
def context_decode_calendar_entry_list(tag):
    return ContextDecodeSequenceOf(context_decode_calendar_entry)(tag)
def context_encode_calendar_entry(number, ce):
    #print "context_encode_calendar_entry: ", repr(ce),
    #print repr(ce.encoding)
    return tag.Construct(number, ce.encoding)
class BACnetSpecialEvent(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('calendar_entry',
                               context_decode_calendar_entry,
                               context_encode_calendar_entry,
                               CHOICE),
        1:ContextSequenceEntry('calendar_reference',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               CHOICE),
        2:ContextSequenceEntry('time_values',
                               ContextDecodeSequenceOf\
                               (context_decode_bacnet_time_value),
                               context_encode_bacnet_time_value_list,
                               REQUIRED),
        3:ContextSequenceEntry('event_priority',
                               context_decode_unsigned_integer8,
                               context_encode_unsigned_integer8,
                               REQUIRED),
        }
def context_decode_special_event(tag):
    return BACnetSpecialEvent(decode=tag.value)
def context_decode_special_event_list(tag):
    return ContextDecodeSequenceOf(context_decode_special_event)(tag)

class BACnetPropertyValue(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('property_identifier',
                               context_decode_enumerated,
                               context_encode_enumerated,
                               REQUIRED),
        1:ContextSequenceEntry('property_array_index',
                               context_decode_unsigned_integer,
                               context_encode_unsigned_integer,
                               OPTIONAL),
        2:ContextSequenceEntry('value',
                               context_decode_abstract_type,
                               context_encode_abstract_type,
                               REQUIRED),
        3:ContextSequenceEntry('priority',
                               context_decode_unsigned_integer8,
                               context_encode_unsigned_integer8,
                               OPTIONAL),
        }
class BACnetDailySchedule(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('time_values',
                               ContextDecodeSequenceOf\
                               (context_decode_bacnet_time_value),
                               context_encode_bacnet_time_value_list,
                               REQUIRED)
        }
def context_read_access_result(tag):
    return ReadAccessResult(decode=tag.value)
def context_read_access_result_list(tag):
    return ContextDecodeSequenceOf(context_read_access_result)(tag)
def context_read_access_specification(tag):
    return ReadAccessSpecification(decode=tag.value)
def context_read_access_specification_list(tag):
    return ContextDecodeSequenceOf(context_read_access_specification)(tag)
def context_write_access_specification(tag):
    return WriteAccessSpecification(decode=tag.value)
def context_write_access_specification_list(tag):
    return ContextDecodeSequenceOf(context_write_access_specification)(tag)

class BACnetRecipient(ContextSequence):
    _sequence_map = {
        0:ContextSequenceEntry('device',
                               context_decode_bacnet_object_identifier,
                               context_encode_bacnet_object_identifier,
                               CHOICE),
        1:ContextSequenceEntry('address',
                               context_decode_bacnet_address,
                               context_encode_bacnet_address,
                               CHOICE),
        }
def context_decode_bacnet_recipient(tag):
    return BACnetRecipient(decode=tag.value)
def context_decode_bacnet_recipient_list(tag):
    return ContextDecodeSequenceOf(context_decode_bacnet_recipient)(tag)
def context_encode_bacnet_recipient(number, recip):
    return tag.Construct(number, recip.encoding)

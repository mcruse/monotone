"""
Copyright (C) 2001 2002 2003 2005 2006 2010 2011 Cisco Systems

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
import types
import re
import mpx
from mpx import properties

from mpx.lib.exceptions import EConfigurationIncomplete
from mpx.lib.exceptions import EConfigurationInvalid
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import EUnreachableCode

from mpx.lib import UniqueToken

_value_dict = {'no':0,'yes':1,
               'n':0,'y':1,
               'false':0,'true':1,
               'off':0, 'on':1,
               '0':0, '1':1,
               '0.0':0, '1.0':1}

_secs_dict = {'days':86400, 'day':86400, 
              'hours':3600, 'hour':3600, 'hrs':3600, 'hr':3600, 
              'minutes':60, 'minute':60, 'mins':60,'min':60,  
              'seconds':1, 'second':1, 'secs':1, 'sec':1, 
              'milliseconds':.001, 'millisecond':.001, 'ms':.001}

##
# Converts a dictionary of time unit, number pairs into a the number of
# seconds the entire dictionary represents.
# @param map A dictionary of time unit, number pairs.
# @key 'days' The number of days to convert to seconds.  The key 'day'
#             also works.
# @default 0
# @key 'hours' The number of hours to convert to seconds.  The keys 'hour',
#              'hrs', and 'hr' also work.
# @default 0
# @key 'minutes' The number of minutes to convert to seconds.  The keys
#                'minute', 'mins', and 'min' also work.
# @default 0
# @key 'seconds' The number of seconds to convert to seconds.  The keys
#                'second', 'secs', and 'sec' also work.
# @default 0
# @default 0
# @key 'milliseconds' The number of milliseconds to convert to seconds.
#                     The keys 'millisecond' and 'ms' also work.
# @default 0
# @return A real value indicating the total number of seconds represented
#         in the map.
def map_to_seconds(map):
    secs = 0
    found_value = None
    for key in _secs_dict.keys():
        conversion = int
        if map.has_key(key):
            if type(_secs_dict[key]) == types.FloatType:
                conversion = float
            secs += conversion(map[key]) * _secs_dict[key]
            found_value = 1
    if not found_value:
        raise EInvalidValue, ('map', map)
    return secs

##
# Converts a real number representing seconds into a dictionary of
# time unit, number pairs.
# @param secs The number of seconds to normalize into unit name, value pairs.
# @return A dictionary keyed by time units.
# @key days
# @key hours
# @key minutes
# @key seconds
# @key milliseconds
def map_from_seconds(secs):
    map = {}
    map['days'] = int(secs) / _secs_dict['days']
    secs -= map['days'] * _secs_dict['days']
    map['hours'] = int(secs) / _secs_dict['hours']
    secs -= map['hours'] * _secs_dict['hours']
    map['minutes'] = int(secs) / _secs_dict['minutes']
    secs -= map['minutes'] * _secs_dict['minutes']
    map['seconds'] = int(secs) / _secs_dict['seconds']
    secs -= map['seconds'] * _secs_dict['seconds']
    map['milliseconds'] = secs / _secs_dict['milliseconds']
    secs -= map['milliseconds'] * _secs_dict['milliseconds']
    for key in map.keys():
        map[key] = str(map[key])
    return map

##
# Get the 1 or 0 representation of a value.
#
# @param value  Representation of boolean value.
# @value 0;1;'yes';'no';'n';'y';'false';'true';'off';'on';'1';'0'
# @return 0 or 1 as specified by <code>value</code>
#
def as_boolean(value):
    if type(value) == types.StringType:
        try:
            value = _value_dict[value.lower()]
        except KeyError:
            pass
    try:    value = int(value)
    except: pass
    if value in (0,1):
        return value
    raise EInvalidValue, ('value', value)

##
# Get the on or off representation of a value.
#
# @param value  Representation of boolean value.
# @value 0;1;yes;no;n;y;false;true;off;on
# @return on or off as specified by <code>value</code>
#
def as_onoff(value):
    value = as_boolean(value)
    if value:
        return 'on'
    else:
        return 'off'

##
# Get the yes or no representation of a value.
#
# @param value  Representation of boolean value.
# @value 0;1;yes;no;n;y;false;true;off;on
# @return on or off as specified by <code>value</code>
#
def as_yesno(value):
    value = as_boolean(value)
    if value:
        return 'yes'
    else:
        return 'no'

##
# @see as_boolean
# @return 'true' or 'false'
#
def as_truefalse(value):
    value = as_boolean(value)
    if value:
        return 'true'
    else:
        return 'false'
##
# @see as_boolean
# @param value  Value to be evaluated for truth.
# @param trueval  What to return if <code>value</code>
#                 is true.
# @param falseval  What to return if <code>value</code>
#                  is false.
#
def as_specified(value, trueval, falseval):
    value = as_boolean(value)
    if value:
        return trueval
    else:
        return falseval

##
# Get the formatted representation of a value given the format.
#
# @param value  Representation of a value
# @param format Format string to be applied to the value.
#               Note:  The type of value must be appropriate for
#                      the specified format.
# @return <code>value</code> as formatted by <code>format</code>
#
def as_formatted(value, format):
    return format % value

##
# Get the formatted representation of a value given the format.
#
# @param value  Representation of a float value
# @param format Format string to be applied to the value.  (Assumed
#               to be a format string appropriate for numeric values).
# @return <code>value</code> as formatted by <code>format</code>
#
def as_float_formatted(value, format):
    try:
        # @note Python 2.5 float() no longer supports converting hex strings
        #       that start with '0x' so this section has been rewritten.
        #       Since '0x' is the uncommon encoding in configuration strings,
        #       use exception to check for '0x' representations.
        return format % float(value)
    except ValueError:
        if isinstance(value,types.StringTypes):
            value = value.strip()
            if value[0:2] == '0x' or value[-1] == 'L':
                return format % float(long(value,16))
        raise
    raise EUnreachableCode()

##
# Get the formatted representation of a value given the format.
#
# @param value  Representation of an integer value
# @param format Format string to be applied to the value.  (Assumed
#               to be a format string appropriate for numeric values).
# @return <code>value</code> as formatted by <code>format</code>
#
def as_int_formatted(value, format):
    try:
        # @note Python 2.5 float() no longer supports converting hex strings
        #       that start with '0x' so this section has been rewritten.
        #       Since '0x' is the uncommon encoding in configuration strings,
        #       use exception to check for '0x' representations.
        return format % int(value)
    except ValueError:
        if isinstance(value,types.StringTypes):
            value = value.strip()
            if value[0:2] == '0x':
                return format % int(value,16)
            elif value[-1] == 'L':
                return format % int(long(value))
        raise
    raise EUnreachableCode()

##
# Get the formatted representation of a value given the format.
#
# @param value  Representation of a long integer value
# @param format Format string to be applied to the value.  (Assumed
#               to be a format string appropriate for numeric values).
# @return <code>value</code> as formatted by <code>format</code>
#
def as_long_formatted(value, format):
    try:
        # @note Python 2.5 float() no longer supports converting hex strings
        #       that start with '0x' so this section has been rewritten.
        #       Since '0x' is the uncommon encoding in configuration strings,
        #       use exception to check for '0x' representations.
        return format % long(value)
    except ValueError:
        if isinstance(value,types.StringTypes):
            value = value.strip()
            if value[0:2] == '0x':
                return format % long(value,16)
        raise
    raise EUnreachableCode()

##
# Functions used to exchange values between dictionaries and object
# attributes.

class _Token:
    ##
    # @fixme support __get__ on self?
    def __init__(self, name, value):
        self._name = name
        self._value = value
    ##
    # They are always sortable, comparable and uniquely identifiable.
    def __cmp__(self, other):
        if hasattr(other, '_value'):
            other = other._value
        return cmp(id(self._value), id(other))
    ##
    # The string representation of the constants name.
    def __str__(self):
        return str(self._name)
    ##
    # 
    def __repr__(self):
        return "%s(%s,%s)" % (self.__class__,
                              repr(self._name),
                              repr(self._value))
    ##
    #
    def __hash__(self):
        return id(self)

##
# Unique identity used to specify an attribute must be set from the
# dictionary.
REQUIRED = UniqueToken('REQUIRED')

##
# Token to handle 'None'
NONE = _Token('None', None)

##
# Do nothing conversion function.
#
# @param value.
# @returns <code>value</code>.
def _no_conversion(value):
    return value

##
# @return <code>value</code> or a unique instance.
##
# @return If the <code>value</code> string is a token (e.g. 'None',
#         'REQUIRED'), then return the object represented by that keyword.
#         Otherwise, convert the <code>value<code> string to the appropriate
#         object via the <code>conversion</code> function.
def _string_to_token(value, conversion):
    for token in (NONE, REQUIRED):
        if value == str(token):
            if hasattr(token, '_value'):  # Hack...
                return token._value
            return token
    return conversion(value)

##
# @return If the <code>value</code> object is a token (e.g. None, REQUIRED),
#         then return the string representation of that keyword.  Otherwise,
#         convert the <code>value<code> to a string via the
#         <code>conversion</code> function.
def _token_to_string(conversion, *vargs):
    # value is the first argument, so vargs must always be at least 1 long
    value = vargs[0]
    for token in (NONE, REQUIRED):
        if hasattr(token, '_value'):  # Hack...
            token = token._value
        if value is token:
            return str(token)
    return conversion(*vargs)

def _outstanding_attribute(object, name):
    if not hasattr(object, '_outstanding_attributes'):
        object._outstanding_attributes = []
    if name not in object._outstanding_attributes:
        object._outstanding_attributes.append(name)
    return

def _remove_outstanding_attribute(object, name):
    if not hasattr(object, '_outstanding_attributes'):
        return
    if name in object._outstanding_attributes:
        object._outstanding_attributes.remove(name)
        if not object._outstanding_attributes:
            del object._outstanding_attributes

def outstanding_attributes(object):
    if not hasattr(object, '_outstanding_attributes'):
        return ()
    return object._outstanding_attributes

# Pattern to be used for the following function, makes
# it faster if we compile it.
_re  = r"(.*?[^\\]|^)(\${(\w+?\.properties\.[A-Z0-9_]+)})"
_pattern = re.compile(_re)

def _expand_properties(string):
    # m.groups()[0] # all text (if any) prior ${<variable>}
    # m.groups()[1] # equals ${<variable>} with $  & brackets
    # m.groups()[2] # just <variable>
    m = None
    if type(string) in types.StringTypes:
        m = _pattern.match(string)
        if m:
            while m:
                s = '%s%s'%(m.groups()[0],eval(m.groups()[2]))
                string = _pattern.sub(s,string)
                m = _pattern.match(string)
    return string
    
##
# Sets an <code>object</code>'s attribute from a dictionary.  The default
# value is only used if the dictionary does not contain the attribute and
# and the <code>object</code> does not have the either.  If the
# <code>object</code> already has the attribute and the dictionary does
# not, then the <code>object</code>'s attribute is left unchanged.  If the
# dictionary contains the attribute, then the <code>object</code>'s attribute
# will be updated accordingly.
#
# @param object     Object to update.
# @param name       The name is used as the <code>object</code>'s attribute
#                   to set and the <code>dictionary</code>'s key.
# @param default    The  default value to apply to the attribute.  If the value
#                   is required, then the dictionary must contain the named
#                   key.
# @param dictionary Used to extract the attribute values.
# @param conversion Function to convert a dictionary value to an attribute
#                   value.
# @default _no_conversion No conversion is applied to the value.
# @throws EConfigurationIncomplete  If a <code>REQUIRED</code> attribute is
#                                   not in the dictionary and has not already
#                                   been set on the <code>object</code>.
# @throws EInvalidValue If the conversion of the value fails.
# @note If default value is used, the conversion function is not applied.
def set_attribute(object, name, default, dictionary,
                  conversion=_no_conversion):
    if (dictionary.has_key(name) and 
        _string_to_token(dictionary[name], str) is not REQUIRED):
        try:
            value = _expand_properties(dictionary[name])
            value = _string_to_token(value,conversion)
        except Exception,e:
            raise EInvalidValue(name,dictionary[name])
    elif default is not REQUIRED:
        # There is a default value.
        if hasattr(object, name) and (getattr(object, name) is not REQUIRED):
            # Do NOT use the default if the attribute already exists (unless
            # its value is REQUIRED and we are supplying a default.)
            return        
        value = _expand_properties(default)
    else:
        if not hasattr(object, name) or getattr(object, name) is REQUIRED:
            # No key in the dictionary, no default and no valid value...
            _outstanding_attribute(object, name)
        return
    _remove_outstanding_attribute(object, name)
    setattr(object, name, value)
    return

##
# Sets an <code>object</code>'s attributes from a dictionary.
#
# @param object     Object to update.
# @param list       List of (name, value) tuples.  The name is used as the
#                   <code>object</code>'s attribute and the
#                   <code>dictionary</code>'s key.  The value is used as the
#                   default value to apply to the attribute.  If the value
#                   is required, then the dictionary must contain the named
#                   key.
# @param dictionary Used to extract the attribute values.
# @param conversion Function to convert a dictionary value to an attribute
#                   value.
# @throws EConfigurationIncomplete  If a <code>REQUIRED</code> attribute is
#                                   not in the dictionary and has not already
#                                   been set on the <code>object</code>.
# @throws EInvalidValue If the conversion of the value fails.
def set_attributes(object, list, dictionary, conversion=_no_conversion):
    for name,default in list:
        set_attribute(object, name, default, dictionary, conversion)

##
# Sets an attribute from a dictionary of values using a conversion
# function.  If the dictionary does not contain the appropriate data
# and the default is required and the attribute is not already set,
# then the attribute is set to the default without applying the conversion
# function.
#
# @param object  Object to update.
# @param default  The default value for the attribute.
# @param dictionary  Used to get values needed by conversion function.
# @param conversion  Conversion function to apply to dictionary.
# @throws EConfigurationIncomplete  If the attribute was required, it was
#                                   not previously set, and the dictionary
#                                   did not contain entries needed for
#                                   conversion function.
#
def map_to_attribute(object, name, default, dictionary, conversion):
    try:
        setattr(object, name, conversion(dictionary))
    except EInvalidValue:
        if default != REQUIRED:
            if not hasattr(object, name):
                setattr(object, name, default)
        else:
            raise EConfigurationIncomplete, name

##
# Adds an <code>object</code>'s attribute to a <code>dictionary</code>.
#
# @param object     Object to locate attributes.
# @param name       The name of the attribute to copy to the
#                   <code>dictionary</code>.
# @param dictionary Dictionary where attributes are copied.
# @param conversion Function to convert an attribute value to a dictionary
#                   value.
# @throws AttributeError  If a name is not an existing attribute of the
#                         <code>object</code>.
def get_attribute(object, name, dictionary, conversion=_no_conversion, *vargs):
    if hasattr(object, name):
        value = getattr(object, name)
        _args = (conversion, value) + vargs
        dictionary[name] = _token_to_string(*_args)

##
# Adds an <code>object</code>'s attributes to a <code>dictionary</code>.
#
# @param object     Object to locate attributes.
# @param names      List of attribute names to copy to the
#                   <code>dictionary</code>.
# @param dictionary Dictionary where attributes are copied.
# @param conversion Function to convert an attribute value to a dictionary
#                   value.
# @throws AttributeError  If a name is not an existing attribute of the
#                         <code>object</code>.
def get_attributes(object, names, dictionary, conversion=_no_conversion):
    for name in names:
        get_attribute(object, name, dictionary, conversion)

##
# Add all entries in dictionary returned from conversion
# for Attribute <code>name</code> of <code>object</code> to
# <code>dictionary</code>.
#
# @param object  Object that contains given attribute.
# @param name  Name of attribute.
# @param dictionary  Dictionary to put converted attribute into.
# @param conversion  Conversion function to turn attribute into dictinary.
# @throws AttributeError
#
def map_from_attribute(object, name, dictionary, conversion):
    att_dict = conversion(getattr(object, name))
    dictionary.update(att_dict)

def flatten_attributes(dictionary):
    if (not dictionary.has_key('attributes') or
        type(dictionary['attributes']) is not types.ListType):
            return dictionary
    attributes = dictionary['attributes']
    del(dictionary['attributes'])
    try:
        for entry in attributes:
            dictionary[entry['name']] = entry['definition']
    except KeyError:
        dictionary['attributes'] = attributes
        return dictionary
    return dictionary
    
##
# Simple helper that functions like str() except that leading and trailing
# whitespace are removed.  Handy for text fields where leading and trailing
# whitespace don't make sense and that are optional (ignored when blank).
#
# @param s Object to convert to a stripped string.
# @return A stripped string.
def stripped_str(s):
    return str(s).strip()

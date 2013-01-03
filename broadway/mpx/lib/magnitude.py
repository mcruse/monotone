"""
Copyright (C) 2003 2005 2010 2011 Cisco Systems

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
import types as _types
from mpx.lib.exceptions import ETypeError as _ETypeError
from mpx.lib import deprecated as _deprecated

class _ValueAsPrimitive:
    def __init__(self, conversion, magnitude):
        self._conversion = conversion
        self._magnitude = magnitude
        return
    def __call__(self):
        return self._conversion(self._magnitude.value)

class Float(float):
    def __repr__(self):
        r = float.__repr__(self)
        if r == "nan":
            return repr(FloatingPointError("NaN"))
        return r

##
# Provides the MagnitudeInterface to complex objects that can also be treated
# as a simple built-in Python numeric object.  Objects that implement the
# MagnitudeInterface can be used anywhere a built-in Python numeric object can
# be used.
class MagnitudeInterface:
    def __init__(self, value=None):
        self._has_magnitude_interface = 1 # Implementation detail.
        self.value = value
        # One time "magic" so the base class can be used as a wrapper for
        # primitive int, long, float objects and Strings and Unicode objects
        # that evaluate as int, long or float objects (in that order of
        # precedence).
        #
        # WARNING:  This code does not execute in derived classes.  This is
        #           intentional.
        if self.__class__ is MagnitudeInterface:
            if isinstance(value,int):
                self.as_magnitude = _ValueAsPrimitive(int, self)
                return
            elif isinstance(value,long):
                self.as_magnitude = _ValueAsPrimitive(long, self)
                return
            elif isinstance(value,float):
                self.as_magnitude = _ValueAsPrimitive(Float, self)
                return
            elif isinstance(value, basestring):
                try:
                    int(value)
                    self.as_magnitude = _ValueAsPrimitive(int, self)
                    return
                except:
                    pass
                try:
                    long(value)
                    self.as_magnitude = _ValueAsPrimitive(long, self)
                    return
                except:
                    pass
                try:
                    float(value)
                    self.as_magnitude = _ValueAsPrimitive(Float, self)
                    return
                except:
                    pass
            else:
                pass
            self._can_not_convert(value)
        return
    ##
    # Helper that raises ETypeError.
    def _can_not_convert(self, value):
        raise _ETypeError("Can't convert %s to a Magnitude object" %
                          type(value))
    def _reinit(self, value): #called when math operation complete
        self.value = value
    def _get_value(self): #normally reimplemented by subclass
        return self.value
    def __str__(self):
        return str(self.as_magnitude())
    def __int__(self):
        return int(self.as_magnitude())
    def __long__(self):
        return long(self.as_magnitude())
    def __float__(self):
        return Float(self.as_magnitude())
    ##
    # @return A built-in Python numeric object that best represents the complex
    #         object's value.  This will be either an int, long or float.
    def as_magnitude(self):
        return int(self.value)
    ##
    # Don't use...
    def _default_numeric_value(self):
        _deprecated("MagnitudeInterface._default_numeric_value() has been"
                    " deprecated, please MagnitudeInterface.as_magnitude().")
        return self.as_magnitude()
    def __add__(self, o):
        return self.__class__(self.as_magnitude() + o)
    def __sub__(self, o):
        return self.__class__(self.as_magnitude() - o)
    def __mul__(self, o):
        return self.__class__(self.as_magnitude() * o)
    def __div__(self, o):
        return self.__class__(self.as_magnitude() / o)
    def __mod__(self, o):
        return self.__class__(self.as_magnitude() % o)
    def __divmod__(self, o):
        return self.__class__(divmod(self.as_magnitude(), o))
    def __pow__(self, o):
        return self.__class__(self.as_magnitude() ** o)
    def __and__(self, o):         
        return self.__class__(self.as_magnitude() & o)
    def __xor__(self, o):
        return self.__class__(self.as_magnitude() ^ o)
    def __or__(self, o):
        return self.__class__(self.as_magnitude() | o)
    def __lshift__(self, o):
        return self.__class__(self.as_magnitude() << o)
    def __rshift__(self, o):
        return self.__class__(self.as_magnitude() >> o)
    def __nonzero__(self): # (used in boolean testing)
        return self.as_magnitude() != 0
    def __cmp__(self, o):
        return cmp(self.as_magnitude(), o)
    def __neg__(self):
        return self.__class__(-self.as_magnitude())
    def __pos__(self):
        return self.__class__(self.as_magnitude())
    def __abs__(self):
        return self.__class__(abs(self.as_magnitude()))
    def __invert__(self): #(bitwise)
        return self.__class__(self.as_magnitude()) #huh?
    def __long__(self):
        return long(self.as_magnitude())
    def __oct__(self):
        return oct(self.as_magnitude())
    def __hex__(self):
        return hex(self.as_magnitude())
    def __radd__(self, o):
        return o + self.as_magnitude()
    def __rsub__(self, o):
        return o - self.as_magnitude()
    def __rmul__(self, o):
        return o * self.as_magnitude()
    def __rdiv__(self, o):
        return o / self.as_magnitude()
    def __rmod__(self, o):
        return o % self.as_magnitude()
    def __rdivmod__(self, o):
        return divmod(o, self.as_magnitude())
    def __rpow__(self, o):
        return o ** self.as_magnitude()
    def __rlshift__(self, o):
        return o << self.as_magnitude()
    def __rrshift__(self, o):
        return o >> self.as_magnitude()
    def __rand__(self, o):         
        return o & self.as_magnitude()
    def __rxor__(self, o):
        return o ^ self.as_magnitude()
    def __ror__(self, o):
        return o | self.as_magnitude()

class Magnitude(MagnitudeInterface):
    def __init__(self, *args, **kw):
        _deprecated("mpx.lib.magnitude.Magnitude has been deprecated,"
                    " please use mpx.lib.magnitude.MagnitudeInterface")
        MagnitudeInterface.__init__(self, *args, **kw)

##
# @return True iff the <code>value</code> supports the MagnitudeInterface.
# @note All values that derive from mpx.lib.EnumeratedValue and
#       mpx.lib.magnitude.Magnitude implement the MagnitudeInterface.
def is_object(value):
    if hasattr(value, '_has_magnitude_interface'):
        return value._has_magnitude_interface
    return 0

##
# @return An instance of the <code>value</code> implements the
#         MagnitudeInterface.
# @throws mpx.lib.ETypeError if the <code>value</code> is not a built-in Python
#         numeric object (int, long, float) and it is not an object that
#         implements the MagnitudeInterface (mpx.lib.EnumeratedValue,
#         mpx.lib.magnitude.Magnitude and their derivatives).
def as_object(value):
    if is_object(value):
        return value
    return MagnitudeInterface(value)

##
# @return True iff the <code>object</code> is a built-in Python numeric
#         object.
# @note Only int, long, and float are considered built-in Python numeric
#       objects (not their derivatives).
def is_magnitude(object):
    for klass in (int, float, long):
        if isinstance(object,klass):
            return 1
    return 0

##
# @return A built-in Python numeric object that best represents the
#         <code>object</code>'s magnitude.
# @throws mpx.lib.ETypeError if the <code>object</code> is not a built-in
#         Python numeric object *and* if <code>object</code> does not implement
#         the MagnitudeInterface.
def as_magnitude(object):
    if is_magnitude(object):
        return object
    try:
        return as_object(object).as_magnitude()
    except _ETypeError,e:
        pass
    int_value = None
    float_value = None
    try:
        int_value = int(object)
    except:
        pass
    try:
        float_value = Float(object)
    except:
        if int_value is not None:
            return int_value
    else:
        if int_value == float_value:
            return int_value
        return float_value
    raise e



# Note: fancy_stringer() has been copied into epssms/iconnmgr/iconnmgr.py .  If it is updated
#       here, please update it there also.

##
# @return A string representation of the dict, list or tuple of simple objects
#         (ints, floats, strs, lists, dicts, or tuples) with any floats formatted
#         with the specified format string.
def fancy_stringer(obj, **kwargs):
    if kwargs.has_key('float_format'):
        float_format = kwargs['float_format']
    else:
        float_format = '%f'
    if kwargs.has_key('int_format'):
        int_format = kwargs['int_format']
    else:
        int_format = '%d'
    if isinstance(obj, list) or isinstance(obj, tuple):
        if isinstance(obj, list):
            bstr = '['
            estr = ']'
        else:
            bstr = '('
            estr = ')'
        retstr = bstr 
        lenlist = len(obj)
        for i in range(0, lenlist):
            cur_item = obj[i]
            item_str = fancy_stringer(cur_item, **kwargs)
            if i != lenlist-1:
                suffix_str = ', '
            else:
                if isinstance(obj, tuple) and lenlist == 1:
                    suffix_str = ',)'
                else:
                    suffix_str = estr
            retstr += '%s%s' % (item_str, suffix_str)
        return retstr
    
    if isinstance(obj, dict):
        itemslist = obj.items()
        lenlist = len(itemslist)
        retstr = '{'
        for i in range(0, lenlist):
            cur_key,cur_val = itemslist[i]
            key_str = fancy_stringer(cur_key, **kwargs)
            val_str = fancy_stringer(cur_val, **kwargs)
            if i != lenlist-1:
                suffix_str = ', '
            else:
                suffix_str = '}'
            retstr += '%s: %s%s' % (key_str, val_str, suffix_str)
        return retstr
    if isinstance(obj, str):
        return "'%s'" % obj
    if isinstance(obj, float):
        return float_format % obj
    if isinstance(obj, int):
        return int_format % obj
    # Fall back on the built in str()
    return str(obj)
            

"""
Copyright (C) 2003 2004 2008 2009 2010 2011 Cisco Systems

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
# Extensions/fixes to Python's built-in xmlrpclib.  Ultimately, this may be
# re-implemented as a more pure extension, but I knew this implementation would
# work and that I could support it into the future.
#
# @see <a href=http://python.org/doc/current/lib/module-xmlrpclib.html>
#      The Python xmlrpclib</a> documentation for details.
#
# CDATA SUPPORT:
#   All marshaling of strings now recognize the XML &lt;![CDATA[..]]&gt; tag
#   and DO NOT escape mark-up text.
#
#   LIMITATIONS:
#     If the initial non-whitespace text is '&lt;![CDATA[', then it is assumed
#     that the entire text is enclosed in the &lt;![CDATA[..]]&gt;, otherwise
#     it is assumed that none of the text is enclosed in a &lt;![CDATA[..]]&gt;
#     section.
#
#     Specifically, mixing &lt;![CDATA[..]]&gt; sections and standard XML
#     character text IS NOT SUPPORTED, NOR IS IT RECOGNIZED.
#
# REGISTRATION OF CUSTOM MARSHALLING:
#   Support for registerring class based marshalling support without having to
#   modify our implementation of xmlrpclib.
#
#   @todo Implement cooresponding Unmarshaller changes.  Should be easy.

import base64 as _base64
import math as _math
import time as _time
import types as _types
import warnings as _warnings

from mpx.lib.exceptions import EUnreachableCode
# @fixme from mpx.ion.aerocomm.csafe import CSafeUnitData
from mpx.lib.httplib import HTTP as _HTTP
# Import all the public references in the built-in xmlrpclib module.
from mpx._python.xmlrpclib import *

#
# Avoid modifiying the underlying Python xmlrpclib by creating a copy of the
# original Marshaller class.
#
def clone_func(f):
    from types import FunctionType
    from copy import copy
    assert type(f) is FunctionType
    n = FunctionType(f.func_code, copy(f.func_globals), f.func_name,
                     copy(f.func_defaults))
    return n
Marshaller_orig = Marshaller
class Marshaller(Marshaller_orig):
    dispatch = {}
    for k,v in Marshaller_orig.dispatch.items():
        dispatch[k]=clone_func(v)

_orig_escape = escape
_cdata_pattern = re.compile("\s*<!\[CDATA\[")

##
# Replacement for the original xmlrpclib.escape function that is used
# internally to convert "&" to "&amp;", "&lt;" to "&lt;" and "&gt;" to "&gt;",
# specifically to conform to the simplest implementation that supports
# the XMLRPC spec.  This version is extended to recognize &lt;![CDATA[..]]&gt;
# strings and to skip escaping the mark-up for such strings.
#
def escape(s, replace=string.replace):
    if not _cdata_pattern.match(s):
        return _orig_escape(s, replace)
    return s

##
# Pythons xmlrpclib module uses blocking sockets, so if
# the target XML-RPC server hangs - so do we.  Add timeout
# capability
Server_orig = Server
def Server(uri, *args, **kwargs):
    t = TimeoutTransport()
    t.timeout = kwargs.get('timeout', 20)
    if 'timeout' in kwargs:
        del kwargs['transport']
    kwargs['transport'] = t
    return Server_orig(uri, *args, **kwargs)

class TimeoutTransport(Transport):
    def make_connection(self, host):
        http = _HTTP(host, timeout=self.timeout)
        return http
        
# @fixme from mpx.lib.magnitude import is_object as _is_object
# @fixme from mpx.lib.magnitude import as_magnitude as _as_magnitude

#
# Base classes from which custom marshaller's can be implemented.
#
class ObjectMarshaller:
    ##
    # Encode the object as XMLRPC, writing the result on xmlrpc_marshaller.
    # @note This is the method invoked by the XMLRPC_Marshaller to
    #       marshal each parameter as an XMLRPC 'snipet.'  Typically,
    #       implementors will not override this method, as the encode()
    #       method is easier to replace.
    def encode_on(self, xmlrpc_marshaller, object, write, *args):
        write(self.encode(object), *args)
        return
    ##
    # @return The XMLRPC encoding of the object as a String.
    def encode(self, object):
        raise ENotImplemented
    def decode_on(self, xmlrpc_unmarshaller, object):
        xmlrpc_unmarshaller.append(self.decode(object))
        return
    ##
    # @return The object decoded from the XMLRPC text.
    def decode(self, text):
        raise ENotImplemented

##
# Implements all &lt;![CDATA[..]]&gt; rules, so you don't have to!
#
# WARNING:
# If the text starts with "&lt;![CDATA[" or "&lt;string&gt;", we assume you
# know what you are doing, but also raise a UserWarning (come on, we'll handle
# it for you!).
#
# I would like to remove the the special "&lt;![CDATA[" and "&lt;string&gt;"
# handling, but first we must ensure that all users of this marshaller
# understand that no extra data handling is required!
class StringMarshaller(ObjectMarshaller):
    _string_pattern = re.compile("^\s*<string>")
    _string_tag_re = re.compile("^\s*<string>\s*(.*)\s*</string>\s*\Z")
    _cdata_tag_re = re.compile("^\s*<!\[CDATA\[.*]]>*\Z")
    ##
    # @fixme Remove checks for "&lt;![CDATA[" and "&lt;string&gt;" ASAP, see
    #        WARNING above.
    def encode(self, text):
        global _cdata_pattern
        if self._string_pattern.match(text):
            # @fixme Remove this if clause ASAP (see WARNING).
            _warnings.warn(
                "<string> tag is overriding all marshalling",
                UserWarning, 3)
            return text
        if not _cdata_pattern.match(text):
            if text.find("]]>") >= 0:
                # Can not include in &lt;![CDATA[..]]&gt;, use pesky escaping.
                text = _orig_escape(text)
            else:
                # We could scan for markup text to determin if the
                # &lt;![CDATA[..]]&gt; is really required, but what's the point?
                return "<value><string>%s%s%s</string></value>" % (
                    "<![CDATA[", text, "]]>"
                    )
        else:
            # @fixme Remove this else clause ASAP (see WARNING).
            _warnings.warn(
                "<![CDATA[..]]> tag is overriding markup marshalling",
                UserWarning, 3)
        return "<value><string>%s</string></value>" % text
    ##
    # Removes optional &lt;![CDATA[..]]&gt; tag.
    def decode(self, text):
        # @fimxe If xmlrpclib strips off the &lt;![CDATA[..]]&gt; tag, then
        #        modify this method to simply return text.
        result = _cdata_tag_re.match(text)
        if result:
            # Strip off the &lt;![CDATA[..]]&gt; tag.
            text = result.groups()[0]
        return text

class ArrayMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_array(*args)
        return

class DictMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_struct(*args)
        return

class IntMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_int(*args)
        return

class LongMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_long(*args)
        return

class FloatMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_double(*args)
        return

class AsDictMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_struct(args[0].as_dict(), *args[1:])
        return

class ExceptionMarshaller(StringMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        try:
            e = args[0]
            s = "error: %s%r" % (e.__class__.__name__, e.args)
        except:
            s = 'error: ExceptionMarshaller'
        xmlrpc_marshaller.dump_string(s, *args[1:])
        return

##
# This class actually replaces the dispatcher table of the base Marshaller
# class, which is a bit dirty but effective.
#
# After loading this module, using the standard public names in built-in
# xmlrpclib module will result in executing the Envenergy specific extensions,
# by default.
class XMLRPC_Marshaller(Marshaller):
    ##
    # Helper class to support registerred marshaller.
    class _KlassMarshaller:
        def __init__(self, klass, marshaller):
            self._klass = klass
            self._marshaller = marshaller
            return
        def klass(self):
            return self._klass
        def marshaller(self):
            return self._marshaller
        def match(self, object):
            return isinstance(object, self._klass)
        def is_ancestor_of(self, klass):
            return issubclass(klass, self._klass)
    Marshaller.string_marshaller = StringMarshaller()
    ##
    # Globally registerred marshallers that effect all Marshaller instances.
    _registerred_marshallers = []
    def __init__(self, *args, **kw):
        Marshaller.__init__(self, *args, **kw)
        self._local_marshallers = 0
        return
    ##
    # Register a global marshaller (aka XMLish encoder/decoder).
    def register_marshaller(klass, marshaller):
        if not hasattr(self, '_local_marshallers'):
            ##
            # Marshallers registerred on this specific instance.
            self._registerred_marshallers = []
            self._local_marshallers = 1
            # "Inherit" the global marshallers.
            for klass_marshaller in (XMLRPC_Marshaller.
                                     _registerred_marshallers):
                # Use global function to share code...
                register_marshaller(klass_marshaller.klass,
                                    klass_marshaller.marshaller,
                                    self._registerred_marshallers)
        # Use global function to share code...
        register_marshaller(klass, marshaller, self._registerred_marshallers)
        return
    ##
    # Replace the "core" marshaller for StringType with a version that
    # recognizes &lt;![CDATA[..]]&gt; and does not escape it.
    def dump_string(self, value, write):
        write(self.string_marshaller.encode(value))
        return
    Marshaller.dump_string = dump_string
    Marshaller.dispatch[StringType] = dump_string
    if unicode:
        ##
        # Replace the "core" marshaller for UnicodeType with a version that
        # recognizes &lt;![CDATA[..]]&gt; and does not escape it.
        def dump_unicode(self, value, write):
            Marshaller.dump_string(self, value, write)
            return
        Marshaller.dump_unicode = dump_unicode
        Marshaller.dispatch[UnicodeType] = dump_unicode
    ##
    # Replace the "core" marshaller for IntType with one that coerces values
    # that are too large into float()s.
    def dump_int(self, value, write):
        # in case ints are > 32 bits
        if value > MAXINT or value < MININT:
            self.dump_double(float(value), write)
            return
        write("<value><int>%s</int></value>\n" % value)
        return
    Marshaller.dump_int = dump_int
    Marshaller.dispatch[IntType] = dump_int
    ##
    # Replace the "core" marshaller for LongType with one that coerces values
    # that are too large into float()s.
    dump_long = dump_int
    Marshaller.dump_long = dump_long
    Marshaller.dispatch[LongType] = dump_long
    ##
    # Replace the "core" marshaller for InstanceType with a version that
    # is more extensible then built-in version's reliance on value.__class__
    # (by allowing isinstance() support that is wieghted to the "closest"
    # registerred parent class).
    #
    # If no valid marshallers are installed, try using "simple" marshallers
    # on the repr() of the value, and the str() of the value (in that
    # order).
    #
    # @see register_marshaller below to use this extension.
    def dump_instance(self, value, write):
        # @fixme - is_enum check temporary hack until our
        # node data model fleshes out - scheduled for 1.5.4
        # at which point this can be ripped out with extreme
        # predjudice.
        if hasattr(value, 'is_enum'):
            value = value.enum()
        marshaller = lookup_marshaller(value)
        if marshaller is not None:
            marshaller.encode_on(self, value, write)
            return
        # check for xmlrpclib DateTime, Binary or Boolean
        if isinstance(value, WRAPPERS):
            value.encode(self)
            return
        #
        # See if the object supports the MagnitudeInterface.  If so, then
        # convert it to it's preferred "simple" datatype and marshal that.\
        #
        ##
        # Hack to return [value,units] for Precor Web Application
        # until as_magnitude and other items are ironed out not to 
        # lose unit information when sent...or something.
        # @fixme if isinstance(value,CSafeUnitData):
        # @fixme     value = [value.value,str(value.units)]
        # @fixme     Marshaller.dispatch[type(value)](self, value)
        # @fixme     return
        #
        # UGLY Repr/Str fallbacks...
        #
        try:
            value = str(value)
        except:
            value = repr(value)
        Marshaller.dispatch[type(value)](self, value, write)
        return
    Marshaller.dump_instance = dump_instance
    Marshaller.dispatch[InstanceType] = dump_instance
    ##
    # Signature changed between Python 2.2 and 2.3, support both:
    #   Python 2.2,    __dump(self, value):
    #   Python 2.3 on, __dump(self, value, write)
    #
    # Also fallsback to encode new style objects as well.
    def __dump(self, *args):
        value = args[0]
        encoder = self.dispatch.get(type(value), self.dispatch[InstanceType])
        encoder(self, *args)
        return
    Marshaller._Marshaller__dump_orig = Marshaller._Marshaller__dump
    Marshaller._Marshaller__dump = __dump

##
# Register a global marshaller (aka XMLish encoder/decoder).
def lookup_marshaller(object,
                      _registerred_marshallers=
                      XMLRPC_Marshaller._registerred_marshallers):
    for klass_marshaller in _registerred_marshallers:
        if klass_marshaller.match(object):
            return klass_marshaller.marshaller()
    return None

##
# Register a global marshaller (aka XMLish encoder/decoder).
def register_marshaller(klass, marshaller,
                        _registerred_marshallers=
                        XMLRPC_Marshaller._registerred_marshallers):
    klass_marshaller = XMLRPC_Marshaller._KlassMarshaller(klass, marshaller)
    # Insert klass in the list before any more general class that klass is
    # derived from.
    before = 0
    for before in range(0,len(_registerred_marshallers)):
        if _registerred_marshallers[before].klass() is klass:
            # Special "replace" case.
            _registerred_marshallers.pop(before)
            break
        if _registerred_marshallers[before].is_ancestor_of(klass):
            # klass is more specialized than
            # _registerred_marshallers[before].klass().
            break
    _registerred_marshallers.insert(before, klass_marshaller)
    return

##
# Scary function that replaces the default argument for a function.
def _replace_func_default(func, old_default, new_default):
    scratch_defaults = []
    if func.func_defaults:
        for value in func.func_defaults:
            if value is old_default:
                scratch_defaults.append(new_default)
            else:
                scratch_defaults.append(value)
        func.func_defaults = tuple(scratch_defaults)
    return

##
# Mega-scary function that replaces the default escape() argument for all the
# methods in the xmlrpclib.Marshaller.dispatch map.  Then, in case that wasn't
# a big enough hack, it replaces the xmlrpclib.escape() function as well.
#
# Why?  Because xmlrpclib.dumps() does NOT offer a clean way to replace the
# escape() function and we NEED escape() to support CDATA.
def _fixup_xmlrpclib_escape(new_escape):
    import xmlrpclib
    keys = Marshaller.dispatch.keys()
    for key in keys:
        _replace_func_default(Marshaller.dispatch[key],
                              xmlrpclib.escape,
                              new_escape)
    xmlrpclib.escape = new_escape
    return

##
# @voodoo Runtime hack of the Python xmlrpclib module to replace it's escape()
#         logic to support CDATA which is used in string responses that may
#         contain '<' or '>'.
_fixup_xmlrpclib_escape(escape)

#
# The following will supersede the default implementation.
#

##
# Encode an <code>object</code> into it's RNA over XMLRPC representation.
# @return A string that is the XMLRPC representation of the object,
#         following RNAv3 conventions.
def encode_value(object):
    pass

##
# Decode an <code>text</code> XMLRPC representation of an object.
# @return The most appropriate object for the XMLRPC <code>text</code>.
def decode_value(text):
    pass

def encode_i4(value):
    assert isinstance(value, int)
    return "<value><i4>" + str(value) + "</i4></value>\n"

def encode_int(value):
    assert isinstance(value, int)
    return "<value><int>" + str(value) + "</int></value>\n"

def encode_boolean(value):
    assert isinstance(value, int)
    return "<value><boolean>" + str(value) + "</boolean></value>\n"

def encode_double(value):
    assert isinstance(value, float)
    abs_val = _math.fabs(value)
    # Work around repr()'s propensity to use exponential format
    # for doubles with really large or really small absolute values.
    # This extra work is because XML-RPC explicitly DOES NOT support
    # exponential format, just decimal digits separated by a single
    # period.
    if value and (abs_val < 0.0001):
        # Scary magic for small numbers, split the float into it's
        # mantissa and exponent components and use the exponent to
        # guess reasonable format.
        m, e = _math.frexp(abs_val)
        decimal_places = int(e/-3) + 17 # Derived at by pure, old-fashon,
                                        # trail and error.
        if decimal_places > 109:
            # "%.110f" causes an OverflowError.
            min_value = "0." + "0"*108 + "1"
            if abs_val < eval(min_value):
                value = min_value
            else:
                value = "%1.109f" % value
                value = value.rstrip('0')
        else:
            value = "%1.*f" % (decimal_places, value)
            value = value.rstrip('0')
    elif value and (abs_val > 99999999999999984.0):
        value = "%.1f" % value
    else:
        value = repr(value)
    return "<value><double>" + value + "</double></value>\n"

def encode_string(value):
    assert isinstance(value, str) or isinstance(value, unicode)
    # As per the XML-RPC specification (http://www.xmlrpc.com/spec), all
    # characters are valid in a string, except '&' and '<' which must be
    # encoded as '&amp;' and '&lt;' respectively.
    value = value.replace('&','&amp;')
    value = value.replace('<','&lt;')
    return "<value><string>" + value + "</string></value>\n"

def encode_base64(value):
    assert isinstance(value, str) or isinstance(value, unicode)
    return ("<value>\n<base64>\n" +
            _base64.encodestring(value) +
            "</base64>\n</value>\n")

##
# Generate a string that represents time-point, encoded like the "broken"
# example in the XML-RPC spec.  The example is broken in that it is
# half basic format and half extended format.  This may be a valid
# representation (I'm not sure), the real concern is that some client
# library implemented their parser based on the XML-RPC spec, without
# checking ISO 8601.
def encode_iso8601_broken(value):
    assert isinstance(value,int) or isinstance(value,float)
    decomposed = _time.gmtime(value)
    value = "%04d%02d%02dT%02d:%02d:%02d" % (
        decomposed.tm_year,
        decomposed.tm_mon,
        decomposed.tm_mday,
        decomposed.tm_hour,
        decomposed.tm_min,
        decomposed.tm_sec
        )
    return "<value><dateTime.iso8601>" + value + "</dateTime.iso8601></value>\n"

##
# Generate a string that represents an ISO 8601:2000(E) compliant time-point.
def encode_iso8601_utc_time_point(value):
    assert isinstance(value,int) or isinstance(value,float)
    decomposed = _time.gmtime(value)
    subseconds = value - int(value)
    if subseconds:
        value = "%04d-%02d-%02dT%02d:%02d:%02d,%02dZ" % (
            decomposed.tm_year,
            decomposed.tm_mon,
            decomposed.tm_mday,
            decomposed.tm_hour,
            decomposed.tm_min,
            decomposed.tm_sec,
            subseconds * 100
            )
    else:
        value = "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
            decomposed.tm_year,
            decomposed.tm_mon,
            decomposed.tm_mday,
            decomposed.tm_hour,
            decomposed.tm_min,
            decomposed.tm_sec
            )
    return "<value><dateTime.iso8601>" + value + "</dateTime.iso8601></value>\n"

def encode_array(array):
    result = "<array><data>\n"
    for value in array:
        result += encode_value(value)
    result += "</data></array>\n"
    return result

def encode_struct(struct):
    result = "<struct>\n"
    for name, value in struct.items():
        assert isinstance(name, str) or isinstance(name, unicode)
        result += "<member>\n<name>" + name + "</name>\n"
        result += encode_value(value) + "<member>\n"
    result += "</struct>\n"
    return result

def encode_xmlprc_value(value):
    return value

def compile_method_encoder_map(method_encoder_map):
    encoders = []
    key_map = []
    for key, value in method_encoder_map.items():
        index = (value['priority'], key)
        assert index not in key_map
        key_map.append(index)
    key_map.sort()
    for priority, key in key_map:
        encoders.append((key, method_encoder_map[key]['encoder']))
    return tuple(encoders)

_default_type_encoders = {
    _types.DictProxyType:encode_struct,
    _types.DictType:encode_struct,
    _types.FloatType:encode_double,
    _types.IntType:encode_int,
    _types.ListType:encode_array,
    _types.LongType:encode_int,
    _types.SliceType:encode_array,
    _types.StringType:encode_string,
    _types.TupleType:encode_array,
    _types.UnicodeType:encode_string,
    _types.XRangeType:encode_array,
    }
#    _types.ComplexType:encode_
#    _types.FileType:encode_
#    _types.GeneratorType:encode_
#    _types.NoneType:encode_
#    _types.ObjectType:encode_
#    _types.TracebackType:encode_
#    _types.InstanceType:encode_


_default_method_encoder_map = {
    'xmlrpc_value':{'encoder':encode_xmlprc_value,
                    'priority':1},
    'rna_dict':{'encoder':encode_struct,
                'priority':2},
    }

_default_method_encoders = compile_method_encoder_map(
    _default_method_encoder_map
    )

_default_class_encoders = (
    (Exception),
    )

#_default_class_encoders = compile_class_encoders(
#    _default_type_encoders
#    )

def lookup_method_encoder(object, method_encoders=_default_method_encoders):
    for priority, method in method_encoders:
        if hasattr(object, method):
            return getattr(object,method)
    return None

def lookup_class_encoder(object, class_encoders=_default_class_encoders):
    for klass, encoder in class_encoders:
        if isinstance(object, klass):
            return encoder
    return None

def lookup_type_encoder(object, type_encoders=_default_type_encoders):
    if _default_type_encoders.has_key(type(object)):
        return _default_type_encoders[type(object)]
    return None

##
# Convert a Python tuple or a Fault instance to an XML-RPC packet.
#
# @def dumps(params, **options)
# @param params A tuple or Fault instance.
# @keyparam methodname If given, create a methodCall request for
#     this method name.
# @keyparam methodresponse If given, create a methodResponse packet.
#     If used with a tuple, the tuple must be a singleton (that is,
#     it must contain exactly one element).
# @keyparam encoding The packet encoding.
# @return A string containing marshalled data.

def dumps(params, methodname=None, methodresponse=None, encoding=None,
          allow_none=0):
    """data [,options] -> marshalled data

    Convert an argument tuple or a Fault instance to an XML-RPC
    request (or response, if the methodresponse option is used).

    In addition to the data object, the following options can be given
    as keyword arguments:

        methodname: the method name for a methodCall packet

        methodresponse: true to create a methodResponse packet.
        If this option is used with a tuple, the tuple must be
        a singleton (i.e. it can contain only one element).

        encoding: the packet encoding (default is UTF-8)

    All 8-bit strings in the data structure are assumed to use the
    packet encoding.  Unicode strings are automatically converted,
    where necessary.
    """

    assert isinstance(params, TupleType) or isinstance(params, Fault),\
           "argument must be tuple or Fault instance"

    if isinstance(params, Fault):
        methodresponse = 1
    elif methodresponse and isinstance(params, TupleType):
        assert len(params) == 1, "response tuple must be a singleton"

    if not encoding:
        encoding = "utf-8"

    if FastMarshaller:
        m = FastMarshaller(encoding)
    else:
        m = Marshaller(encoding, allow_none)

    data = m.dumps(params)

    if encoding != "utf-8":
        xmlheader = "<?xml version='1.0' encoding='%s'?>\n" % str(encoding)
    else:
        xmlheader = "<?xml version='1.0'?>\n" # utf-8 is default

    # standard XML-RPC wrappings
    if methodname:
        # a method call
        if not isinstance(methodname, StringType):
            methodname = methodname.encode(encoding)
        data = (
            xmlheader,
            "<methodCall>\n"
            "<methodName>", methodname, "</methodName>\n",
            data,
            "</methodCall>\n"
            )
    elif methodresponse:
        # a method response, or a fault structure
        data = (
            xmlheader,
            "<methodResponse>\n",
            data,
            "</methodResponse>\n"
            )
    else:
        return data # return as is
    return string.join(data, "")

##
# Convert an XML-RPC packet to a Python object.  If the XML-RPC packet
# represents a fault condition, this function raises a Fault exception.
#
# @param data An XML-RPC packet, given as an 8-bit string.
# @return A tuple containing the unpacked data, and the method name
#     (None if not present).
# @see Fault

def loads(data, use_datetime=0):
    """data -> unmarshalled data, method name

    Convert an XML-RPC packet to unmarshalled data plus a method
    name (None if not present).

    If the XML-RPC packet represents a fault condition, this function
    raises a Fault exception.
    """
    p, u = getparser(use_datetime=use_datetime)
    p.feed(data)
    p.close()
    return u.close(), u.getmethodname()

"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from __future__ import absolute_import # Keep as first python statement.
"""
A Broadway extension to the standard Python xmlrpclib module.

The primary purpose is to:
1. Provide a mechanism to replace or add new encoders and decoders.
2. To enable marshaling of derived classes, and new style objects.
3. To hook into the Elemental Data Type library (mpx.lib.edtlib).
   This is to support the encoding/decoding data-types and objects
   that XML-RPC does not support using common object abstractions.
"""
if __name__ == '__main__':
    import os
    import sys
    os.chdir(os.path.dirname(sys.argv[0]))
    exit(os.system("run_test_modules -v 2 _test_case_xmlrpclib2.pyc"))

import xmlrpclib as _pyxmlrpc

from base64 import standard_b64decode
from base64 import standard_b64encode
from string import replace
from types import DictType
from types import InstanceType
from types import LongType
from types import NoneType
from types import ObjectType
from types import StringType
from types import TupleType
from types import UnicodeType

from mpx.lib import EnumeratedValue

from .edtlib import BinaryString
from .edtlib import ClassHierarchyDict
from .edtlib import ElementalIntegerType
from .edtlib import ElementalNoneType
from .edtlib import ElementalEnumeratedType
from .edtlib import edt_decode
from .edtlib import edt_encode

MAXINT = _pyxmlrpc.MAXINT
MININT = _pyxmlrpc.MININT

Fault = _pyxmlrpc.Fault

# NBM Implementation Specific Error Constants.  Conformant with Dan Libby's
# specification at http://xmlrpc-epi.sourceforge.net/specs/rfc.fault_codes.php)
# which reserves faultCodes in range -32099 .. -32000 specifically for such
# use:

RAISE_EXCEPTION = -32099

class SortedDict(dict):
    """
    Return keys and items in a consistant order.  Used to simplify comparing
    XML generated from a dictionary.  THIS IS FOR TESTING PURPOSES ONLY.

    IMPLIMENTATION IS JUST ENOUGH FOR THE UNDERLYING XMLRPCLIB MARSHALLER.
    """
    def keys(self):
        k = dict.keys(self)
        k.sort()
        return k
    def items(self):
        l = []
        for k in self.keys():
            l.append((k,self[k],))
        return l

class Marshaller(_pyxmlrpc.Marshaller):
    base_dispatch = _pyxmlrpc.Marshaller.dispatch
    dispatch = ClassHierarchyDict(base_dispatch)
    def __init__(self, encoding=None, allow_none=0, allow_cdata=0):
        _pyxmlrpc.Marshaller.__init__(self, encoding, allow_none)
        # Crazy default over loading.
        if allow_cdata:
            self.dump_edt.im_func.func_defaults = (self.cdata_escape,)
            self.dump_edt_sorted.im_func.func_defaults = (self.cdata_escape,)
            self.dump_string.im_func.func_defaults = (self.cdata_escape,)
            self.dump_struct.im_func.func_defaults = (self.cdata_escape,)
            self.dump_struct_sorted.im_func.func_defaults = (self.cdata_escape,)
            self.dump_unicode.im_func.func_defaults = (self.cdata_escape,)
        else:
            self.dump_edt.im_func.func_defaults = (self.basic_escape,)
            self.dump_edt_sorted.im_func.func_defaults = (self.basic_escape,)
            self.dump_string.im_func.func_defaults = (self.basic_escape,)
            self.dump_struct.im_func.func_defaults = (self.basic_escape,)
            self.dump_struct_sorted.im_func.func_defaults = (self.basic_escape,)
            self.dump_unicode.im_func.func_defaults = (self.basic_escape,)
        return
    def enable_sorted_struct(cls):
        """
        Globalliy enable dumping structs in a predictable order.  FOR TESTING
        PURPOSES ONLY.
        """
        _pyxmlrpc.Marshaller.dispatch[DictType] = cls.dump_struct_sorted
        cls.dispatch[DictType] = cls.dump_struct_sorted
        cls.dispatch[ObjectType] = cls.dump_edt
        cls.dispatch[InstanceType] = cls.dump_edt
        return
    enable_sorted_struct = classmethod(enable_sorted_struct)
    def disable_sorted_struct(cls):
        _pyxmlrpc.Marshaller.dispatch[DictType] = (
            _pyxmlrpc.Marshaller.dump_struct
            )
        cls.dispatch[DictType] = cls.dump_struct_sorted
        cls.dispatch[ObjectType] = cls.dump_edt_sorted
        cls.dispatch[InstanceType] = cls.dump_edt_sorted
        return
    disable_sorted_struct = classmethod(disable_sorted_struct)
    def basic_escape(self, s, replace=replace):
        s = replace(s, "&", "&amp;")
        s = replace(s, "<", "&lt;")
        return replace(s, ">", "&gt;",)
    def cdata_escape(self, s, replace=replace):
        if s.find("<![CDATA[") >= 0:
            return self.basic_escape(s, replace)
        return s
    def dump_hook(self, value, write):
        try:
            f = self.dispatch[value] # Dispatch based on value, rather than
                                     # type which loses specificity.
        except KeyError:
            raise TypeError, "cannot marshal %s objects" % type(value)
        else:
            f(self, value, write)
        return
    _Marshaller__dump = dump_hook
    def dump_nil (self, value, write):
        if self.allow_none:
            write("<value><nil/></value>")
            return
        self.dump_struct(ElementalNoneType(value).edt_dump(), write)
        return
    dispatch[NoneType] = dump_nil
    def dump_long(self, value, write):
        if value > MAXINT or value < MININT:
            self.dump_struct(ElementalIntegerType(value).edt_dump(), write)
            return
        _pyxmlrpc.Marshaller.dump_long(self, value, write)
        return
    dispatch[LongType] = dump_long
    def dump_string(self, value, write, escape=None):
        _pyxmlrpc.Marshaller.dump_string(self, value, write, escape)
        return
    dispatch[StringType] = dump_string
    def dump_unicode(self, value, write, escape=None):
        _pyxmlrpc.Marshaller.dump_unicode(self, value, write, escape)
        return
    dispatch[UnicodeType] = dump_unicode
    def dump_struct(self, value, write, escape=None):
        _pyxmlrpc.Marshaller.dump_struct(self, value, write, escape)
        return
    dispatch[DictType] = dump_struct
    def dump_base64(self, value, write):
        write("<value><base64>\n")
        write(standard_b64encode(value))
        write("</base64></value>\n")
        return
    dispatch[BinaryString] = dump_base64
    def dump_edt(self, value, write, escape=None):
        self.dump_struct(edt_encode(value), write, escape)
        return
    dispatch[ObjectType] = dump_edt
    dispatch[InstanceType] = dump_edt
    dispatch[ElementalEnumeratedType] = dump_edt
    dispatch[EnumeratedValue] = dump_edt
    # Sorted methods to help test-cases.
    def dump_struct_sorted(self, value, write, escape=None):
        _pyxmlrpc.Marshaller.dump_struct(self, SortedDict(value),write, escape)
        return
    def dump_edt_sorted(self, value, write, escape=None):
        self.dump_struct_sorted(edt_encode(value), write, escape)
        return
    # FIXME: Change to support native DateTime.  IS THAT AN ELEMENTAL TYPE?
    # FIXME: Add dispatchers for other "Binary" data-types
    def dump_wrappers(self, value, write):
        class O:
            def __init__(self,write):
                self.write = write
        value.encode(O(write))
        return
    dispatch[_pyxmlrpc.Binary] = dump_wrappers   # encodes -> BinaryString
    dispatch[_pyxmlrpc.DateTime] = dump_wrappers

# Python/third-party classes (any class we create should register itself.)

class Unmarshaller(_pyxmlrpc.Unmarshaller):
    base_dispatch = _pyxmlrpc.Unmarshaller.dispatch
    dispatch = dict(base_dispatch)
    def __init__(self, use_datetime=0):
        _pyxmlrpc.Unmarshaller.__init__(self, use_datetime=0)
        return
    def end_struct(self, data):
        mark = self._marks.pop()
        # map structs to Python dictionaries
        d = {}
        items = self._stack[mark:]
        for i in range(0, len(items), 2):
            d[_pyxmlrpc._stringify(items[i])] = items[i+1]
        if d.get('edt__typ',None):
            # Hook for ElementalDataType support.
            d = edt_decode(d)
        self._stack[mark:] = [d]
        self._value = 0
    dispatch["struct"] = end_struct
    def end_base64(self, data):
        self.append(BinaryString(standard_b64decode(data)))
        self._value = 0
    dispatch["base64"] = end_base64

def getparser(use_datetime=0):
    """getparser() -> parser, unmarshaller (derived from python's xmlrpclib)

    Create an instance of the fastest available parser, and attach it
    to an Unmarshalling object.  Return both objects.
    """
    if use_datetime and not _pyxmlrpc.datetime:
        raise ValueError, "the datetime module is not available"
    target = Unmarshaller(use_datetime=use_datetime)
    if _pyxmlrpc.FastParser:
        parser = _pyxmlrpc.FastParser(target)
    elif _pyxmlrpc.SgmlopParser:
        parser = _pyxmlrpc.SgmlopParser(target)
    elif _pyxmlrpc.ExpatParser:
        parser = _pyxmlrpc.ExpatParser(target)
    else:
        parser = _pyxmlrpc.SlowParser(target)
    return parser, target

# FIXME: I wonder if I could "clone" Python's loads and then replace
#        globals() with this module.
def loads(data, use_datetime=0, return_fault=False):
    """data -> unmarshalled data, method name (derived from python 2.5.2
                                               xmlrpclib)

    Convert an XML-RPC packet to unmarshalled data plus a method
    name (None if not present).

    If the XML-RPC packet represents a fault condition, this function
    raises a Fault exception.
    """
    # FIXME: Do we really need to instantiate a new unmarshaller every time?
    try:
        p, u = getparser(use_datetime)
        p.feed(data)
        p.close()
        return u.close(), u.getmethodname()
    except Fault, f:
        if return_fault:
            # Caller requested returning the fault rather than raising a
            # Fault exception.
            return (f,), None
        if f.faultCode == RAISE_EXCEPTION:
            # Fault is an envelope for a raised exception.  Decode the exception
            # and raise it.
            t, n = loads(f.faultString)
            e = t[0]
            if isinstance(e,Exception):
                raise e
            # Something went amiss in decoding the exception.  Re-raise the
            # original fault (FIXME: probably should raise an explanatory
            # exception.)
            raise
        # It's really an XMLRPC fault, and the caller really wants it raised.
        raise

# FIXME: I wonder if I could "clone" Python's dumps and then replace
#        globals() with this module.
def dumps(params, methodname=None, methodresponse=None, encoding=None,
          allow_none=0, allow_cdata=0):
    """data [,options] -> marshalled data (derived from python 2.5.2 xmlrpclib)

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

    #if FastMarshaller:
    #    m = FastMarshaller(encoding)
    #else:
    # FIXME: Do we really need to instanciate a new Marshaller every time?
    m = Marshaller(encoding, allow_none, allow_cdata)

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
    return "".join(data)

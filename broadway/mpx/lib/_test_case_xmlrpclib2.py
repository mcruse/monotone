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
from __future__ import absolute_import # Keep as first python statement
from mpx_test import DefaultTestFixture, main

import errno

from base64 import standard_b64decode
from base64 import standard_b64encode

from xmlrpclib import Binary
from xmlrpclib import DateTime

from mpx.lib import EnumeratedValue
from mpx.lib.node import as_internal_node

from .edtlib import BinaryString
from .edtlib import ElementalEnumeratedType
from .edtlib import ElementalNodeType
from .edtlib import class_name
from .edtlib import default_attr_names
from .edtlib import edt_decode
from .edtlib import load_from_map
from .edtlib import noarg
from .edtlib import register_class

from .xmlrpclib2 import Fault
from .xmlrpclib2 import Marshaller
from .xmlrpclib2 import RAISE_EXCEPTION
from .xmlrpclib2 import dumps
from .xmlrpclib2 import loads

#
# WARNING:  Invoking global sorting of dumped "structs" to simplify comparing
#           generated XML.
#
Marshaller.enable_sorted_struct()

def compare_default_attributes(expected, received, fail=False):
    expected_names = default_attr_names(expected)
    received_names = default_attr_names(received)
    expected_names.sort()
    received_names.sort()
    if expected_names != received_names:
        if fail:
            raise AssertionError("""Different Attributes:
Expected: %r
Got:      %r""" % (expected_names, received_names))
        return False
    for k in expected_names:
        expected_value = getattr(expected,k)
        if expected_value != getattr(received, k, not expected_value):
            if fail:
                raise AssertionError("""Attribute Mismatch:
Expected: %s = %r
Got:      %s = %r""" % (k, expected_value, k, getattr(received, k, noarg)))
            return False
    return True

class OldStyle:
    def __init__(self,**kw):
        for k,v in kw.items():
            setattr(self,k,v)
        return
    def __eq__(self,other):
        return compare_default_attributes(self,other)

class EdtRegisteredOldStyle(OldStyle):
    @classmethod
    def edt_decode(cls,enc,obj=None):
        if obj is None:
            obj = cls()
        return load_from_map(obj,enc)
register_class(EdtRegisteredOldStyle)

class NewStyle(object):
    def __init__(self,**kw):
        for k,v in kw.items():
            setattr(self,k,v)
        return
    def __eq__(self,other):
        return compare_default_attributes(self,other)

class EdtRegisteredNewStyle(NewStyle):
    @classmethod
    def edt_decode(cls,enc,obj=None):
        if obj is None:
            obj = cls()
        return load_from_map(obj,enc)
register_class(EdtRegisteredNewStyle)

def simple_xml(x):
    l = x.split('\n')
    l = map(lambda s: s.strip(), l)
    l = ''.join(l).split('\r')
    l = map(lambda s: s.strip(), l)
    return ''.join(l)

class TestCase(DefaultTestFixture):
    def assert_eq(self, a, b):
        self.failUnless(simple_xml(a) == simple_xml(b), (
        """XML Mismatch:
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
%s
=========================== DOES NOT MATCH =============================
%s
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
""" % (a,b)))
        return
    def test_dumps_array(self):
        self.assert_eq(
            dumps(([12,"Egypt",False,-31],)),
            "<params><param><value><array><data>"
            "<value><int>12</int></value>"
            "<value><string>Egypt</string></value>"
            "<value><boolean>0</boolean></value>"
            "<value><int>-31</int></value>"
            "</data></array></value></param></params>"
            )
        return
    def test_dumps_base64(self):
        self.assert_eq(
            dumps((Binary("you can't read this!"),)),
            "<params><param><value><base64>"
            "eW91IGNhbid0IHJlYWQgdGhpcyE="
            "</base64></value></param></params>"
            )
        return
    def test_dumps_binary_string(self):
        bytstr = ''.join(map(chr,range(0,256))) # '\x00\x01...\xff'
        b64str = standard_b64encode(bytstr)
        self.assert_eq(
            dumps((BinaryString(bytstr),)),
            ''.join(("<params><param><value><base64>",
                     b64str,
                     "</base64></value></param></params>"))
            )
        return
    def test_dumps_boolean(self):
        self.assert_eq(
            dumps((False,)),
            "<params>"
            "<param><value><boolean>0</boolean></value></param>"
            "</params>"
            )
        self.assert_eq(
            dumps((True,)),
            "<params>"
            "<param><value><boolean>1</boolean></value></param>"
            "</params>"
            )
        return
    def test_dumps_complex(self):
        self.assert_eq(
            dumps((complex(1.0,2.0),)),
            "<params><param><value><struct><member><name>real</name><value>"
            "<double>1.0</double></value></member><member><name>imag</name>"
            "<value><double>2.0</double></value></member><member><name>"
            "edt__typ</name><value><string>complex</string></value></member>"
            "</struct></value></param></params>"
            )
        return
    def test_dumps_datetime(self):
        self.assert_eq(
            dumps((DateTime("19980717T14:08:55"),)),
            "<params><param><value><dateTime.iso8601>"
            "19980717T14:08:55"
            "</dateTime.iso8601></value></param></params>"
            )
        return
    def test_dumps_double(self):
        self.assert_eq(
            dumps((-12.214,)),
            "<params>"
            "<param><value><double>-12.214</double></value></param>"
            "</params>"
            )
        self.assert_eq(
            dumps((float('inf'),)),
            "<params>"
            "<param><value><double>inf</double></value></param>"
            "</params>"
            )
        self.assert_eq(
            dumps((float('-inf'),)),
            "<params>"
            "<param><value><double>-inf</double></value></param>"
            "</params>"
            )
        return
    def test_dumps_enumerated_type(self):
        self.assert_eq(
            dumps((ElementalEnumeratedType(11,'eleven'),)),
            "<params><param><value><struct>"
            "<member><name>num</name><value><int>11</int></value></member>"
            "<member><name>str</name><value><string>eleven</string></value>"
            "</member><member>"
            "<name>edt__typ</name><value><string>enumerated</string></value>"
            "</member></struct></value></param></params>"
            )
        return
    def test_dumps_enumerated_value(self):
        print "\n", 60*"-"
        print dumps((EnumeratedValue(12,'twelve'),))
        print 60*"-"
    def test_dumps_exception(self):
        try: 1/0
        except Exception, e: pass
        self.assert_eq(
            dumps((e,)),
            "<params><param><value><struct>"
            "<member><name>edt__cls</name>"
            "<value><string>exceptions.ZeroDivisionError</string></value>"
            "</member>"
            "<member>"
            "<name>message</name>"
            "<value><string>integer division or modulo by zero</string></value>"
            "</member>"
            "<member><name>args</name><value><array><data>"
            "<value><string>integer division or modulo by zero</string></value>"
            "</data></array></value></member>"
            "<member><name>edt__typ</name>"
            "<value><string>exception</string></value></member>"
            "</struct></value></param></params>"
            )
        return
    def test_dumps_fault(self):
        self.assert_eq(
            dumps(Fault(1, "It's not my fault!")),
            "<?xml version='1.0'?>"
            "<methodResponse><fault><value><struct>"
            "<member><name>faultCode</name><value><int>1</int></value></member>"
            "<member><name>faultString</name>"
            "<value><string>It's not my fault!</string></value></member>"
            "</struct></value></fault></methodResponse>"
            )
        return
    def test_dumps_fault_exception(self):
        try: open("/there/ain't/no/such/file",'r')
        except Exception, e: pass
        else:
            raise Exception(
            'Did not catch expected OSError exception'
            )
        self.assert_eq(
            dumps(Fault(RAISE_EXCEPTION, dumps((e,)))),
            "<?xml version='1.0'?>"
            "<methodResponse>"
            "<fault><value><struct><member><name>faultCode</name>"
            "<value><int>-32099</int></value></member>"
            "<member><name>faultString</name>"
            "<value><string>&lt;params&gt;&lt;param&gt;&lt;value&gt;"
            "&lt;struct&gt;&lt;member&gt;&lt;name&gt;errno&lt;/name&gt;"
            "&lt;value&gt;&lt;int&gt;2&lt;/int&gt;&lt;/value&gt;"
            "&lt;/member&gt;&lt;member&gt;&lt;name&gt;args&lt;/name&gt;"
            "&lt;value&gt;&lt;array&gt;&lt;data&gt;&lt;value&gt;&lt;int&gt;2"
            "&lt;/int&gt;&lt;/value&gt;&lt;value&gt;"
            "&lt;string&gt;No such file or directory&lt;/string&gt;"
            "&lt;/value&gt;&lt;/data&gt;&lt;/array&gt;&lt;/value&gt;"
            "&lt;/member&gt;&lt;member&gt;&lt;name&gt;strerror&lt;/name&gt;"
            "&lt;value&gt;&lt;string&gt;No such file or directory"
            "&lt;/string&gt;&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;filename&lt;/name&gt;&lt;value&gt;"
            "&lt;string&gt;/there/ain't/no/such/file&lt;/string&gt;"
            "&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;edt__cls&lt;/name&gt;&lt;value&gt;"
            "&lt;string&gt;exceptions.IOError&lt;/string&gt;"
            "&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;message&lt;/name&gt;&lt;value&gt;&lt;string&gt;"
            "&lt;/string&gt;&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;edt__typ&lt;/name&gt;&lt;value&gt;"
            "&lt;string&gt;exception&lt;/string&gt;&lt;/value&gt;"
            "&lt;/member&gt;&lt;/struct&gt;&lt;/value&gt;"
            "&lt;/param&gt;&lt;/params&gt;"
            "</string></value></member></struct></value></fault>"
            "</methodResponse>"
            )
        return
    def test_dumps_instance(self):
        o = OldStyle(a=1,b=2,c=3)
        self.assert_eq(
            dumps((o,)),
            "<params><param><value><struct>"
            "<member><name>a</name><value><int>1</int></value></member>"
            "<member><name>c</name><value><int>3</int></value></member>"
            "<member><name>b</name><value><int>2</int></value></member>"
            "<member><name>edt__typ</name>"
            "<value><string>object</string></value></member>"
            "</struct></value></param></params>"
            )
        return
    def test_dumps_instance_registered(self):
        o = EdtRegisteredOldStyle(a=1,b=2,c=3)
        self.assert_eq(
            dumps((o,)),
            "<params><param><value><struct><member>"
            "<name>a</name><value><int>1</int></value></member><member>"
            "<name>edt__cls</name><value><string>"
            "mpx.lib._test_case_xmlrpclib2.EdtRegisteredOldStyle"
            "</string></value></member><member>"
            "<name>c</name><value><int>3</int></value></member><member>"
            "<name>b</name><value><int>2</int></value></member><member>"
            "<name>edt__typ</name><value><string>object</string></value>"
            "</member></struct></value></param></params>"
            )
        return
    def test_dumps_int(self):
        self.assert_eq(
            dumps((1,)),
            "<params><param><value><int>1</int></value></param></params>"
            )
        self.assert_eq(
            dumps((-2,)),
            "<params><param><value><int>-2</int></value></param></params>"
            )
        self.assert_eq(
            dumps((10L,)),
            "<params><param><value><int>10</int></value></param></params>"
            )
        self.assert_eq(
            dumps((-30L,)),
            "<params><param><value><int>-30</int></value></param></params>"
            )
        self.assert_eq(
            dumps((4294967295L,)),
            ("<params>"
             "<param>"
             "<value><struct>"
             "<member>"
             "<name>bytes</name>"
             "<value><array><data>"
             "<value><int>0</int></value>"
             "<value><int>255</int></value>"
             "<value><int>255</int></value>"
             "<value><int>255</int></value>"
             "<value><int>255</int></value>"
             "</data></array></value>"
             "</member>"
             "<member>"
             "<name>edt__typ</name>"
             "<value><string>integer</string></value>"
             "</member>"
             "</struct></value>"
             "</param>"
             "</params>")
            )
        return
    def test_dumps_list(self):
        self.assert_eq(
            dumps(([1,'b',3.0,],)),
            "<params><param><value><array><data>"
            "<value><int>1</int></value>"
            "<value><string>b</string></value>"
            "<value><double>3.0</double></value>"
            "</data></array></value></param></params>"
            )
        return
    def test_dumps_map(self):
        self.assert_eq(
            dumps(({'a':'one','b':'B','c':6,},)),
            "<params><param><value><struct>"
            "<member><name>a</name><value><string>one</string></value></member>"
            "<member><name>b</name><value><string>B</string></value></member>"
            "<member><name>c</name><value><int>6</int></value></member>"
            "</struct></value></param></params>"
            )
        # FIXME: ? print dumps(({1:'one','b':'B',5.6:7,},))
        # FIXME: ? print 60*"-"
        raise Exception("Implement list based maps (hash?)...")
        return
    def test_dumps_method(self):
        self.assert_eq(
            dumps((-2,), methodname="negative_two"),
            "<?xml version='1.0'?>"
            "<methodCall><methodName>negative_two</methodName>"
            "<params><param><value><int>-2</int></value></param></params>"
            "</methodCall>"
            )
        return
    def test_dumps_node(self):
        self.assert_eq(
            dumps((as_internal_node('/'),)),
            "<params><param><value><struct><member>"
            "<name>path</name><value><string>/</string></value></member>"
            "<member><name>edt__typ</name><value><string>node</string></value>"
            "</member></struct></value></param></params>"
            )
        return
    def test_dumps_none(self):
        self.assert_eq(
            dumps((None,)),
            "<params><param><value><struct>"
            "<member><name>edt__typ</name>"
            "<value><string>none</string></value>"
            "</member></struct></value></param></params>"
            )
        return
    def test_dumps_object(self):
        n = NewStyle(a=1,b=2,c=3)
        self.assert_eq(
            dumps((n,)),
            "<params><param><value><struct>"
            "<member><name>a</name><value><int>1</int></value></member>"
            "<member><name>c</name><value><int>3</int></value></member>"
            "<member><name>b</name><value><int>2</int></value></member>"
            "<member><name>edt__typ</name>"
            "<value><string>object</string></value></member>"
            "</struct></value></param></params>"
            )
        return
    def test_dumps_object_registered(self):
        n = EdtRegisteredNewStyle(a=1,b=2,c=3)
        self.assert_eq(
            dumps((n,)),
            "<params><param><value><struct><member>"
            "<name>a</name><value><int>1</int></value></member><member>"
            "<name>edt__cls</name><value><string>"
            "mpx.lib._test_case_xmlrpclib2.EdtRegisteredNewStyle"
            "</string></value></member><member>"
            "<name>c</name><value><int>3</int></value></member><member>"
            "<name>b</name><value><int>2</int></value></member><member>"
            "<name>edt__typ</name><value><string>object</string></value>"
            "</member></struct></value></param></params>"
            )
        return
    def test_dumps_response(self):
        self.assert_eq(
            dumps((-3,), methodresponse=True),
            "<?xml version='1.0'?>"
            "<methodResponse>"
            "<params><param><value><int>-3</int></value></param></params>"
            "</methodResponse>"
            )
        return
    def test_dumps_string(self):
        self.assert_eq(
            dumps(("hello world!",)),
            "<params>"
            "<param><value><string>hello world!</string></value></param>"
            "</params>"
            )
        return
    def test_dumps_unicode(self):
        self.assert_eq(
            dumps(("\u00A1hello world!",)),
            "<params>"
            "<param><value><string>\u00A1hello world!</string></value></param>"
            "</params>"
            )
        return
    def test_dumps_struct(self):
        self.assert_eq(
            dumps(({"lowerBound":1,"upperBound":9},)),
            "<params>"
            "<param><value><struct>"
            "<member>"
            "<name>lowerBound</name><value><int>1</int></value>"
            "</member>"
            "<member>"
            "<name>upperBound</name><value><int>9</int></value>"
            "</member>"
            "</struct></value></param>"
            "</params>"
            )
        return
    def confirm_loads_map(self, loads_map):
        for key, result in loads_map.items():
            tmp = loads(key)
            self.failUnless(
                tmp == result,
                """Decode Mismatch
Parsed:   %r
Expected: %r
Got:      %r""" % (key, result, tmp)
                )
        return
    def confirm_loads_object(self,loads_map,use_datetime=0,return_fault=False,
                             same_class=True):
        for key, result in loads_map.items():
            tmp = loads(key, use_datetime, return_fault)
            etmp = tmp[0][0]
            eresult = result[0][0]
            if same_class:
                self.failUnless(eresult.__class__ == etmp.__class__,
                                "Wrong Class Decoded\n"
                                "Expected: %r\n"
                                "Got:      %r" %
                                (class_name(eresult.__class__),
                                 class_name(etmp.__class__)))
            compare_default_attributes(eresult, etmp)
        return
    def test_loads_array(self):
        loads_map = {
            ("<params><param><array><data>"
             "<value><i4>12</i4></value>"
             "<value><string>Egypt</string></value>"
             "<value><boolean>0</boolean></value>"
             "<value><i4>-31</i4></value>"
             "</data></array></param></params>"):
                (([12,"Egypt",False,-31],),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_base64(self):
        loads_map = {
            ("<params>"
             "<param><value><base64>"
             "eW91IGNhbid0IHJlYWQgdGhpcyE="
             "</base64></value></param>"
             "</params>"):((BinaryString("you can't read this!"),),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_binary_string(self):
        bytstr = ''.join(map(chr,range(0,256))) # '\x00\x01...\xff'
        b64str = standard_b64encode(bytstr)
        loads_map = {
            ''.join(("<params><param><value><base64>",
                     b64str,
                     "</base64></value></param></params>")):
                ((BinaryString(bytstr),),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_boolean(self):
        loads_map = {
            ("<params>"
             "<param><value><boolean>0</boolean></value></param>"
             "</params>"):((False,),None),
            ("<params>"
             "<param><value><boolean>1</boolean></value></param>"
             "</params>"):((True,),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_dumps_complex(self):
        loads_map = {
            ("<params><param><value><struct><member><name>real</name><value>"
             "<double>1.0</double></value></member><member><name>imag</name>"
             "<value><double>2.0</double></value></member><member><name>"
             "edt__typ</name><value><string>complex</string></value></member>"
             "</struct></value></param></params>"):((complex(1.0,2.0),),None),
            }
        return
    def test_loads_datetime(self):
        loads_map = {
            ("<params><param><value><dateTime.iso8601>"
             "19980717T14:08:55"
             "</dateTime.iso8601></value></param></params>"):
                ((DateTime("19980717T14:08:55"),),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_double(self):
        loads_map = {
            ("<params>"
             "<param><value><double>-12.214</double></value></param>"
             "</params>"):((-12.214,),None),
            ("<params>"
             "<param><value><double>inf</double></value></param>"
             "</params>"):((float('inf'),),None),
            ("<params>"
             "<param><value><double>-inf</double></value></param>"
             "</params>"):((float('-inf'),),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_enumerated_type(self):
        loads_map = {
            ("<params><param><value><struct>"
             "<member><name>num</name><value><int>11</int></value></member>"
             "<member><name>str</name><value><string>eleven</string></value>"
             "</member><member>"
             "<name>edt__typ</name><value><string>enumerated</string></value>"
             "</member></struct></value></param></params>"):
                ((ElementalEnumeratedType(11,'eleven'),),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_exception(self):
        try: 1/0
        except Exception, e: pass
        loads_map = {
            ("<params><param><value><struct>"
             "<member><name>edt__cls</name>"
             "<value><string>exceptions.ZeroDivisionError</string></value>"
             "</member>"
             "<member>"
             "<name>message</name>"
             "<value><string>integer division or modulo by zero</string>"
             "</value></member>"
             "<member><name>args</name><value><array><data><value>"
             "<string>integer division or modulo by zero</string>"
             "</value></data></array></value></member>"
             "<member><name>edt__typ</name>"
             "<value><string>exception</string></value></member>"
             "</struct></value></param></params>"):((e,),None),
            }
        self.confirm_loads_object(loads_map)
        return
    def test_loads_fault_value(self):
        loads_map = {
            ("<?xml version='1.0'?>"
             "<methodResponse><fault><value><struct>"
             "<member><name>faultCode</name><value><int>1</int></value>"
             "</member><member><name>faultString</name>"
             "<value><string>It's not my fault!</string></value></member>"
             "</struct></value></fault></methodResponse>"):
                ((Fault(1, "It's not my fault!"),),None),
        }
        self.confirm_loads_object(loads_map, return_fault=True)
        return
    def test_loads_fault(self):
        try:
            loads("<?xml version='1.0'?>"
                  "<methodResponse><fault><value><struct>"
                  "<member><name>faultCode</name><value><int>1</int></value>"
                  "</member><member><name>faultString</name>"
                  "<value><string>It's not my fault!</string></value></member>"
                  "</struct></value></fault></methodResponse>")
        except Fault, f:
            compare_default_attributes(Fault(1, "It's not my fault!"), f,
                                       fail=True)
        else:
            self.fail("loads(...fault...) failed to raise a Fault exception.")
        return
    def test_loads_fault_exception(self):
        loads_xml = (
            "<?xml version='1.0'?>"
            "<methodResponse>"
            "<fault><value><struct><member><name>faultCode</name>"
            "<value><int>-32099</int></value></member>"
            "<member><name>faultString</name>"
            "<value><string>&lt;params&gt;&lt;param&gt;&lt;value&gt;"
            "&lt;struct&gt;&lt;member&gt;&lt;name&gt;errno&lt;/name&gt;"
            "&lt;value&gt;&lt;int&gt;2&lt;/int&gt;&lt;/value&gt;"
            "&lt;/member&gt;&lt;member&gt;&lt;name&gt;args&lt;/name&gt;"
            "&lt;value&gt;&lt;array&gt;&lt;data&gt;&lt;value&gt;&lt;int&gt;2"
            "&lt;/int&gt;&lt;/value&gt;&lt;value&gt;"
            "&lt;string&gt;No such file or directory&lt;/string&gt;"
            "&lt;/value&gt;&lt;/data&gt;&lt;/array&gt;&lt;/value&gt;"
            "&lt;/member&gt;&lt;member&gt;&lt;name&gt;strerror&lt;/name&gt;"
            "&lt;value&gt;&lt;string&gt;No such file or directory"
            "&lt;/string&gt;&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;filename&lt;/name&gt;&lt;value&gt;"
            "&lt;string&gt;/there/ain't/no/such/file&lt;/string&gt;"
            "&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;edt__cls&lt;/name&gt;&lt;value&gt;"
            "&lt;string&gt;exceptions.IOError&lt;/string&gt;"
            "&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;message&lt;/name&gt;&lt;value&gt;&lt;string&gt;"
            "&lt;/string&gt;&lt;/value&gt;&lt;/member&gt;&lt;member&gt;"
            "&lt;name&gt;edt__typ&lt;/name&gt;&lt;value&gt;"
            "&lt;string&gt;exception&lt;/string&gt;&lt;/value&gt;"
            "&lt;/member&gt;&lt;/struct&gt;&lt;/value&gt;"
            "&lt;/param&gt;&lt;/params&gt;"
            "</string></value></member></struct></value></fault>"
            "</methodResponse>"
            )
        try:
            loads(loads_xml) # Parsing a RAISE_EXCEPTION Fault will raise
                             # the encoded exception (unless return_fault=True.)
        except IOError, e:
            self.assert_(e.args == (2, 'No such file or directory'))
            self.assert_(e.errno == errno.ENOENT)
            self.assert_(e.filename == "/there/ain't/no/such/file")
            self.assert_(e.strerror == 'No such file or directory')
            self.assert_(e.message == '')
        else:
            self.fail("loads(...exception...) failed to raise the exception.")
        return
    def test_loads_instance(self):
        loads_map = {
            ("<params><param><value><struct>"
             "<member><name>a</name><value><int>1</int></value></member>"
             "<member><name>c</name><value><int>3</int></value></member>"
             "<member><name>b</name><value><int>2</int></value></member>"
             "<member><name>edt__typ</name>"
             "<value><string>object</string></value></member>"
             "</struct></value></param></params>"):
                ((OldStyle(a=1,b=2,c=3),),None),
            }
        self.confirm_loads_object(loads_map, same_class=False)
        return
    def test_loads_instance_registered(self):
        loads_map = {
            ("<params><param><value><struct><member>"
             "<name>a</name><value><int>1</int></value></member><member>"
             "<name>edt__cls</name><value><string>"
             "mpx.lib._test_case_xmlrpclib2.EdtRegisteredOldStyle"
             "</string></value></member><member>"
             "<name>c</name><value><int>3</int></value></member><member>"
             "<name>b</name><value><int>2</int></value></member><member>"
             "<name>edt__typ</name><value><string>object</string></value>"
             "</member></struct></value></param></params>"):
                ((EdtRegisteredOldStyle(a=1,b=2,c=3),),None),
            }
        self.confirm_loads_object(loads_map) # Must load same class too.
        return
    def test_loads_int(self):
        loads_map = {
            "<params><param><value><int>1</int></value></param></params>":
                ((1,),None),
            "<params><param><value><int>-2</int></value></param></params>":
                ((-2,),None),
            "<params><param><value><int>10</int></value></param></params>":
                ((10,),None),
            "<params><param><value><int>-30</int></value></param></params>":
                ((-30,),None),
            "<params><param><value><i4>4</i4></value></param></params>":
                ((4,),None),
            ("<params>"
             "<param>"
             "<value><struct>"
             "<member>"
             "<name>bytes</name>"
             "<value><array><data>"
             "<value><int>0</int></value>"
             "<value><int>255</int></value>"
             "<value><int>255</int></value>"
             "<value><int>255</int></value>"
             "<value><int>255</int></value>"
             "</data></array></value>"
             "</member>"
             "<member>"
             "<name>edt__typ</name>"
             "<value><string>integer</string></value>"
             "</member>"
             "</struct></value>"
             "</param>"
             "</params>"):((4294967295L,),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_list(self):
        load_map = {
            ("<params><param><value><array><data>"
             "<value><int>1</int></value>"
             "<value><string>b</string></value>"
             "<value><double>3.0</double></value>"
             "</data></array></value></param></params>"):
                (([1,'b',3.0,],),None),
            }
        return
    def test_loads_map(self):
        load_map = {
            ("<params><param><value><struct>"
             "<member><name>a</name><value><string>one</string></value>"
             "</member>"
             "<member><name>b</name><value><string>B</string></value></member>"
             "<member><name>c</name><value><int>6</int></value></member>"
             "</struct></value></param></params>"
            ):(({'a':'one','b':'B','c':6,},),None),
            }
        # FIXME: ? print dumps(({1:'one','b':'B',5.6:7,},))
        # FIXME: ? print 60*"-"
        raise Exception("Implement list based maps (hash?)...")
        return
    def test_loads_method(self):
        loads_map = {
            ("<?xml version='1.0'?>"
             "<methodCall><methodName>negative_two</methodName>"
             "<params><param><value><int>-2</int></value></param></params>"
             "</methodCall>"):((-2,),"negative_two"),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_node(self):
        loads_maps = {
            ("<params><param><value><struct><member>"
             "<name>path</name><value><string>/</string></value></member>"
             "<member><name>edt__typ</name><value><string>node</string></value>"
             "</member></struct></value></param></params>"):
                ElementalNodeType('/')
            }
        return
    def test_loads_none(self):
        loads_map = {
            ("<params><param><value><struct>"
             "<member><name>edt__typ</name>"
             "<value><string>none</string></value>"
             "</member></struct></value></param></params>"):((None,),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_object(self):
        loads_map = {
            ("<params><param><value><struct>"
             "<member><name>a</name><value><int>1</int></value></member>"
             "<member><name>c</name><value><int>3</int></value></member>"
             "<member><name>b</name><value><int>2</int></value></member>"
             "<member><name>edt__typ</name>"
             "<value><string>object</string></value></member>"
             "</struct></value></param></params>"):
                ((NewStyle(a=1,b=2,c=3),),None),
            }
        self.confirm_loads_object(loads_map, same_class=False)
        return
    def test_loads_object_registered(self):
        loads_map = {
            ("<params><param><value><struct><member>"
             "<name>a</name><value><int>1</int></value></member><member>"
             "<name>edt__cls</name><value><string>"
             "mpx.lib._test_case_xmlrpclib2.EdtRegisteredNewStyle"
             "</string></value></member><member>"
             "<name>c</name><value><int>3</int></value></member><member>"
             "<name>b</name><value><int>2</int></value></member><member>"
             "<name>edt__typ</name><value><string>object</string></value>"
             "</member></struct></value></param></params>"):
                ((EdtRegisteredNewStyle(a=1,b=2,c=3),),None),
            }
        self.confirm_loads_object(loads_map) # Class must be the same.
        return
    def test_loads_response(self):
        loads_map = {
            ("<?xml version='1.0'?>"
             "<methodResponse>"
             "<params><param><value><int>-3</int></value></param></params>"
             "</methodResponse>"):((-3,),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_string(self):
        loads_map = {
            ("<params>"
             "<param><value><string>hello world</string></value></param>"
             "</params>"):(("hello world",),None),
            }
        self.confirm_loads_map(loads_map)
        return
    def test_loads_struct(self):
        loads_map = {
            ("<params>"
             "<param><value><struct>"
             "<member><name>lowerBound</name><value><i4>1</i4></value></member>"
             "<member><name>upperBound</name><value><i4>9</i4></value></member>"
             "</struct></value></param>"
             "</params>"):(({"lowerBound":1,"upperBound":9},),None),
            }
        self.confirm_loads_map(loads_map)
        return

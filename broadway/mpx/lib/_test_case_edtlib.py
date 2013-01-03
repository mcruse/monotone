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
from mpx_test import DefaultTestFixture, main

import base64
import math
import os

import mpx.lib.exceptions as mpxexc

from mpx.lib import BinaryString
from mpx.lib.edtlib import ClassHierarchyDict
from mpx.lib.edtlib import ElementalBooleanType
from mpx.lib.edtlib import ElementalComplexType
from mpx.lib.edtlib import ElementalDataType
from mpx.lib.edtlib import ElementalEnumeratedType
from mpx.lib.edtlib import ElementalExceptionType
from mpx.lib.edtlib import ElementalIntegerType
from mpx.lib.edtlib import ElementalListType
from mpx.lib.edtlib import ElementalMapType
from mpx.lib.edtlib import ElementalNodeType
from mpx.lib.edtlib import ElementalNoneType
from mpx.lib.edtlib import ElementalObjectType
from mpx.lib.edtlib import ElementalRealType
from mpx.lib.edtlib import ElementalTextType
from mpx.lib.edtlib import ObjDict
from mpx.lib.edtlib import class_name
from mpx.lib.edtlib import default_encoding
from mpx.lib.edtlib import edt_decode
from mpx.lib.edtlib import edt_encode
from mpx.lib.edtlib import register_class

from mpx.lib.node import as_internal_node
from mpx.lib.node import as_node

class TestCase(DefaultTestFixture):
    def assert_lookup(self, c, o, r):
        self.assert_(
            c.lookup(o) == r,
            "got %r for <inst of %r>, expecct %r" % (c.lookup(o),
                                                     o.__class__.__name__, r)
            )
        return
    def test_ElementalListType(self):
        """
        At this time, there is no fallback implementation for lists.  JSON,
        XML-RPC and 5150 all have lists of arbitrary length and implementing
        a generic fallback seems interesting but pointless at this time...
        """
        return
    def test_ElementalMapType(self):
        assert ElementalMapType().edt_get() == ({})
        encoded_one = [('edt__map', 4),
                       ('joy', 'is'), ((2, 2), 'twotwo'),
                       (1.0, 'x'), ('cheese', 'please')]
        decoded_one = {'joy':'is','cheese':'please',1.0:'x',
                       (2,2):'twotwo'}
        assert ElementalMapType(encoded_one).edt_get() == decoded_one
        class A(object):
            def __init__(self,**kw):
                for k,v in kw.items():
                    setattr(self,k,v)
                return
        a = A(a=1,b=2,c='c')
        e = ElementalObjectType(a).edt_dump()
        e = ElementalMapType(e).edt_dump()
        o = edt_decode(e)
        assert a.a == o.a
        assert a.b == o.b
        assert a.c == o.c
        try:
            1/0
        except Exception, ex:
            pass
        e = ElementalMapType(edt_encode(ex)).edt_dump()
        o = edt_decode(e)
        assert isinstance(o,ex.__class__)
        assert ex.args == o.args
        assert ex.message == ex.message
        return
    def test_ElementalObjectType(self):
        # Test "standalone" functionality:
        assert isinstance(ElementalObjectType().edt_get(), ElementalObjectType)
        assert ElementalObjectType().edt__typ is 'object'
        assert not hasattr(ElementalObjectType(),'edt__cls')
        # Test marshaling an old-style class.
        class A:
            cls_var='class variable'
            _no_cls='hide me please!'
            def __init__(self, **kw):
                self.__dict__.update(kw)
                return
        an_obj = A(a=1, b='b',c=None,_d="don't do it!",
                   f=lambda : "this either!")
        e = default_encoding(an_obj)
        encoded_attrs=('edt__typ', 'cls_var','a','b','c')
        assert not filter(lambda k: k not in encoded_attrs, e.keys())
        ignored_attrs=('_d','f','no_cls_')
        assert not filter(lambda k: k in ignored_attrs, e.keys())
        # Test unmarshaling it inplace via constructor.
        a=ElementalObjectType(e)
        assert not hasattr(a, 'edt__cls')
        assert a.edt__typ == 'object'
        assert a.cls_var == 'class variable'
        assert a.a == 1
        assert a.b == 'b'
        assert a.c is None
        assert not e # Map is consumed in decoding.
        # Test unmarshaling it in a new object via the decode factory.
        e = default_encoding(an_obj)
        edt_decode(ObjDict(e))
        a=ElementalObjectType.edt_decode(e)
        assert not hasattr(a, 'edt__cls')
        assert a.edt__typ == 'object'
        assert a.cls_var == 'class variable'
        assert a.a == 1
        assert a.b == 'b'
        assert a.c is None
        # Test reinstanciating a 'named' class (but not registered).
        a.edt__cls = class_name(A)
        e = default_encoding(a)
        a = ElementalObjectType.edt_decode(e)
        assert a.edt__cls == class_name(A)        # Class type conveyed.
        assert isinstance(a,ElementalObjectType)  # But not used.
        # Test reinstanciating the actual class with edt_decode().
        class B(A):
            @classmethod
            def edt_decode(cls,edt_map,obj=None):
                assert obj is None # Supporting obj == None is not important.
                # How the class uses edt_map is 'a local matter'.  Could
                # be passed in toto to __init__, could use load_from_map(),
                # another factory.  Whatever.
                edt_map.pop('edt__typ') # Don't need this.
                edt_map.pop('edt__cls') # Or this.
                return cls(**edt_map) # Can't reference B in B, but cls == B.
        register_class(B)
        b = B(a='b',b=2,c=math.pi)
        e = default_encoding(b)
        b = ElementalObjectType.edt_decode(e)
        assert isinstance(b,B)
        # assert b.edt__typ == 'object'
        assert b.edt__cls == class_name(b.__class__)
        assert b.cls_var == 'class variable'
        assert b.a == 'b'
        assert b.b == 2
        assert b.c == math.pi
        # Test ability to override cls_name (dangerous, but may be
        # required for reverse compatibility after refactors that move
        # data classes.)
        class C(B):
            edt__typ = 'object' # Not required by edtlib, but OK.
        register_class(C, cls_name='_test_ElementalObjectType.C')
        c = C(a='c',b=3,c=math.e)
        e = default_encoding(c)
        c = ElementalObjectType.edt_decode(e)
        assert isinstance(c,C)
        assert c.edt__typ == 'object'
        assert c.edt__cls == '_test_ElementalObjectType.C'
        assert c.cls_var == 'class variable'
        assert c.a == 'c'
        assert c.b == 3
        assert c.c == math.e
        # Test "integrated" marshalling
        assert edt_encode(a) == default_encoding(a)
        assert edt_encode(b) == default_encoding(b)
        assert edt_encode(c) == default_encoding(c)
        return
    def test_ElementalNoneType(self):
        # Test "standalone" functionality:
        assert ElementalNoneType().edt_get() is None
        assert ElementalNoneType(1).edt_get() is None # Constructor 
        assert ElementalNoneType(True).edt_get() is None
        assert ElementalNoneType('hi!').edt_get() is None
        assert ElementalNoneType({}).edt_get() is None
        assert ElementalNoneType({'value':0}).edt_get() is None
        assert ElementalNoneType(ObjDict({'value':1})).edt_get() is None
        assert ElementalNoneType.edt_decode({'value':1}) is None
        assert ElementalNoneType.edt_decode({'value':0}) is None
        assert ElementalNoneType().edt_dump() == {'edt__typ': 'none'}
        # Test "integrated" unmarshalling (should be to native Python bool)
        assert edt_decode({'edt__typ': 'none'}) is None
        # Test "integrated" marshalling
        assert edt_encode(None) == {'edt__typ': 'none'}
        return
    def test_ElementalBooleanType(self):
        # FIXME: confirm that edt_set,edt_load
        # Test "standalone" functionality representing values:
        assert ElementalBooleanType().edt_get() is False
        assert ElementalBooleanType(False).edt_get() is False
        assert ElementalBooleanType(True).edt_get() is True
        assert ElementalBooleanType(None).edt_get() is False
        assert ElementalBooleanType(0).edt_get() is False
        assert ElementalBooleanType(1).edt_get() is True
        assert ElementalBooleanType(0L).edt_get() is False
        assert ElementalBooleanType(1L).edt_get() is True
        assert ElementalBooleanType(0.0).edt_get() is False
        assert ElementalBooleanType(math.pi).edt_get() is True
        assert ElementalBooleanType(-math.pi).edt_get() is True
        assert ElementalBooleanType('').edt_get() is False # Empty string.
        assert ElementalBooleanType('False').edt_get() is True # Not empty.
        assert ElementalBooleanType({}).edt_get() is False # Empty dict.
        assert ElementalBooleanType({'value':0}).edt_get() is True # Not empty.
        # Test "standalone" functionality decoding values:
        assert ElementalBooleanType(ObjDict({'value':0})).edt_get() is False
        assert ElementalBooleanType(ObjDict({'value':1})).edt_get() is True
        assert ElementalBooleanType.edt_decode({'value':1}) is True
        assert ElementalBooleanType.edt_decode({'value':0}) is False
        # Test "standalone" functionality encoding values:
        assert ElementalBooleanType(False).edt_dump() == (
            {'value': 0, 'edt__typ': 'bool'}
            )
        assert ElementalBooleanType(True).edt_dump() == (
            {'value': 1, 'edt__typ': 'bool'}
            )
        # Test "integrated" unmarshalling (should be to native Python bool)
        assert edt_decode({'value': 0, 'edt__typ': 'bool'}) is False
        assert edt_decode({'value': 1, 'edt__typ': 'bool'}) is True
        # Test "integrated" marshalling
        assert edt_encode(False) == {'value': 0, 'edt__typ': 'bool'}
        assert edt_encode(True) == {'value': 1, 'edt__typ': 'bool'}
        return
    def test_ElementalIntegerType(self):
        # Test "standalone" functionality representing values:
        assert ElementalIntegerType().edt_get() is 0
        assert ElementalIntegerType(False).edt_get() is 0
        assert ElementalIntegerType(True).edt_get() is 1
        assert ElementalIntegerType(None).edt_get() is 0
        assert ElementalIntegerType(0).edt_get() is 0
        assert ElementalIntegerType(1).edt_get() is 1
        assert ElementalIntegerType(0L).edt_get() is 0
        assert ElementalIntegerType(1L).edt_get() is 1
        assert ElementalIntegerType(0.0).edt_get() is 0
        assert ElementalIntegerType(3).edt_get() is 3
        assert ElementalIntegerType(-3).edt_get() is -3
        assert ElementalIntegerType(1234567890).edt_get() == 1234567890
        assert (ElementalIntegerType(-98765432109876543210).edt_get()
                == -98765432109876543210)
        # Test "standalone" functionality encoding values:
        assert ElementalIntegerType(3735928559L).edt_dump() == {
            'edt__typ': 'integer', 'bytes':[0, 222, 173, 190, 239]
            }
        assert ElementalIntegerType.edt_decode(
            {'bytes':[0, 222, 173, 190, 239]}
            ) == 3735928559L
        assert ElementalIntegerType.edt_decode(
            {'bytes':[222, 173, 190, 239]}
            ) == -559038737
        # Test "integrated" unmarshalling
        assert edt_decode(
            {'edt__typ': 'integer',
             'bytes': [53, 213, 17, 171, 151, 196, 200, 81, 136, 180, 150,
                       74, 245, 139, 76, 89, 111, 141, 220, 199, 173, 238,
                       184, 13, 79, 255, 129, 254, 210, 66, 129, 94, 85,
                       188, 131, 117, 162, 5, 222, 7, 89, 125, 81, 210,
                       16, 95, 47, 7, 48, 244, 1]
             }) == 139008452377144732764939786789661303114218850808529137991604824430036072629766435941001769154109609521811665540548899435521L
        # Test "integrated" marshalling
        assert edt_encode(1) == {'edt__typ': 'integer', 'bytes': [1]}
        return
    def test_ElementalRealType(self):
        assert ElementalRealType().edt_get() == 0.0
        assert ElementalRealType(math.pi).edt_get() == math.pi
        e = ElementalRealType(-math.pi).edt_dump()
        assert e == {'edt__typ': 'real', 'data': '\xc0\t!\xfbTD-\x18',}
        ElementalRealType(e).edt_get() == -math.pi
        assert ElementalRealType.edt_decode(
            {'edt__typ': 'real', 'data': '@\x05\xbf\n\x8b\x14Wi',}
            ) == math.e
        assert ElementalRealType(float('-inf')).edt_dump() == {
                'edt__typ': 'real', 'data': '\xff\xf0\x00\x00\x00\x00\x00\x00',
                }
        assert edt_decode(
            {'edt__typ': 'real', 'data': '\x7f\xf0\x00\x00\x00\x00\x00\x00',}
            ) == float('inf')
        # Test "integrated" marshalling
        assert edt_encode(math.e) == {
            'edt__typ': 'real', 'data': '@\x05\xbf\n\x8b\x14Wi',
            }
        return
    def test_ElementalComplexType(self):
        assert ElementalComplexType().edt_get() == complex(0,0)
        assert ElementalComplexType(
            complex(1.2,3.4)
            ).edt_get() == complex(1.2,3.4)
        assert ElementalComplexType(complex(-math.pi, math.e)).edt_dump() == {
            'edt__typ': 'complex', 'real': -math.pi, 'imag': math.e,
            }
        assert ElementalComplexType(complex(333, -222)).edt_dump() == {
            'edt__typ': 'complex', 'real': 333.0, 'imag': -222.0,
            }
        assert edt_decode(
            {'edt__typ': 'complex', 'real': 1.23, 'imag': 6.54}
            ) == complex(1.23,6.54)
        # Test "integrated" marshalling
        assert edt_encode(complex(1.0, 2.0)) == {
            'edt__typ': 'complex', 'real': 1.0, 'imag': 2.0
            }
        return
    def test_ElementalEnumeratedType(self):
        assert edt_encode(ElementalEnumeratedType([1,'On'])) == {
            'edt__typ': 'enumerated', 'num': 1, 'str': 'On'
            }
        e = edt_decode({'edt__typ': 'enumerated', 'num': 0, 'str': 'Off'})
        assert isinstance(e, ElementalEnumeratedType)
        assert e.num == 0
        assert e.str == 'Off'
        return
    def test_ElementalDataType(self):
        bytstr = ''.join(map(chr,range(0,256))) # '\x00\x01...\xff'
        b64str = base64.standard_b64encode(bytstr)
        assert ElementalDataType(bytstr).edt_dump() == {
            'edt__typ': 'data', 'edt__enc': 'b64', 'data': b64str,
            }
        edt_decode(
            {'edt__typ': 'data', 'edt__enc': 'b64', 'data': b64str,}
            ) == bytstr
        assert edt_encode(BinaryString('should be encoded into base64')) == {
            'edt__typ': 'data', 'edt__enc': 'b64',
            'data': 'c2hvdWxkIGJlIGVuY29kZWQgaW50byBiYXNlNjQ=',
            }
        return
    def test_ElementalTextType(self):
        ascii = 'ASCII Text'
        bytes = map(ord,ascii) # [65, 83, 67, 73, 73, 32, 84, 101, 120, 116]
        utf8 = u'UTF-8 is assumed for unicode: \u2318' # PLACE OF INTEREST SIGN
        d = ElementalTextType(ascii).edt_dump()
        assert d == {
            'edt__typ': 'text', 'edt__enc': 'bytes', 'text': bytes
            }
        assert isinstance(d['text'], (list,tuple))
        d = ElementalTextType(utf8).edt_dump()
        assert d == {
            'edt__typ': 'text', 'edt__enc': 'utf-8',
            'text': utf8.encode('utf-8')
            }
        assert isinstance(d['text'], BinaryString)
        assert d['text'][-3:] == '\xe2\x8c\x98' # unicode 2318 -> UTF-8 E2 8C 89
        assert edt_encode("hi!") == {
            'edt__typ': 'text', 'edt__enc': 'bytes', 'text': [104, 105, 33]
            }
        return
    def test_ElementalExceptionType(self):
        try: 1/0
        except Exception, ex: pass
        e = ElementalExceptionType(ex)
        assert e.edt_dump() == {
            'edt__typ': 'exception',
            'edt__cls': 'exceptions.ZeroDivisionError',
            'message': 'integer division or modulo by zero', 
            'args': ('integer division or modulo by zero',)
            }
        e = ElementalExceptionType.edt_decode(
            {'edt__typ': 'exception',
             'edt__cls': 'exceptions.ZeroDivisionError',
             'message': 'integer division or modulo by zero', 
             'args': ('integer division or modulo by zero',)}
            )
        try: raise e
        except ZeroDivisionError, z:
            assert e.message == 'integer division or modulo by zero'
            assert e.args == ('integer division or modulo by zero',)
            pass
        else: raise Exception(
            'Did not catch expected ZeroDivisionError exception'
            )
        e = edt_decode({'edt__typ': 'exception',
                        'edt__cls': 'exceptions.NameError',
                        'args': ("global name 'huh' is not defined",),
                        'message': "global name 'huh' is not defined",})
        try: raise e
        except NameError, n:
            assert n.message == "global name 'huh' is not defined"
            assert n.args == ("global name 'huh' is not defined",)
        else: raise Exception(
            'Did not catch expected NameError exception'
            )
        try: os.chdir("/there/ain't/no/such/dir")
        except Exception, ex: pass
        e = ElementalExceptionType(ex).edt_dump()
        assert e == {'edt__typ': 'exception',
                     'edt__cls': 'exceptions.OSError',
                     'args': (2, 'No such file or directory'),
                     'errno': 2,
                     'filename': "/there/ain't/no/such/dir",
                     'strerror': 'No such file or directory',
                     'message': '',}
        try: raise edt_decode(e)
        except OSError, oserr: pass
        assert oserr.args == (2, 'No such file or directory')
        assert oserr.errno == 2
        assert oserr.filename == "/there/ain't/no/such/dir"
        assert oserr.strerror == 'No such file or directory'
        assert oserr.message == ''
        try: open("/there/ain't/no/such/file",'r')
        except Exception, ex: pass
        else:
            raise Exception(
            'Did not catch expected OSError exception'
            )
        e = ElementalExceptionType(ex).edt_dump()
        assert e == {'edt__typ': 'exception',
                     'edt__cls': 'exceptions.IOError',
                     'args': (2, 'No such file or directory'),
                     'errno': 2,
                     'filename': "/there/ain't/no/such/file",
                     'strerror': 'No such file or directory',
                     'message': '',}
        try: raise edt_decode(e)
        except IOError, ioerr: pass
        else:
            raise Exception(
            'Did not catch expected IOError exception'
            )
        assert ioerr.args ==  (2, 'No such file or directory')
        assert ioerr.errno == 2
        assert ioerr.strerror == 'No such file or directory'
        assert ioerr.filename == "/there/ain't/no/such/file"
        assert ioerr.message == ''
        try: raise mpxexc.Forbidden("can't touch this",)
        except Exception, ex: pass
        e = ElementalExceptionType(ex).edt_dump()
        assert e == {'edt__typ': 'exception',
                     'edt__cls': 'mpx.lib.exceptions.Forbidden',
                     'args': ("can't touch this",),
                     'keywords': {},
                     'details': "can't touch this",
                     'message': "can't touch this",}
        try: raise edt_decode(e)
        except mpxexc.Forbidden, f: pass
        else:
            raise Exception(
            'Did not catch expected Forbidden exception'
            )
        assert f.args == ("can't touch this",)
        assert f.keywords == {}
        assert f.details == "can't touch this"
        assert f.message == "can't touch this"
        try: raise mpxexc.EPermission('bogus', 'ridiculous',
                                      target='stay on target',cheese='smelly')
        except Exception, ex: pass
        e = ElementalExceptionType(ex).edt_dump()
        assert e == {'edt__typ': 'exception',
                     'edt__cls': 'mpx.lib.exceptions.EPermission',
                     'args': ('bogus', 'ridiculous'),
                     'filename': 'stay on target',
                     'keywords': {'cheese': 'smelly'},
                     'errno': 13,
                     'strerror': 'Permission denied',
                     'message': '',}
        try: raise edt_decode(e)
        except mpxexc.EPermission, p: pass
        else:
            raise Exception(
            'Did not catch expected mpx.lib.EPermission exception'
            )
        assert p.args == ('bogus', 'ridiculous')
        assert p.filename == 'stay on target'
        assert p.keywords ==  {'cheese': 'smelly'}
        assert p.errno == 13
        assert p.strerror == 'Permission denied'
        assert p.message == ''
        try: raise mpxexc.ERangeError('bond, james bond',
                                      'casino royal',
                                      'not likely',
                                      good_start='lawyer be gone',
                                      good_end='boy gets girl',
                                      cheese='has holes')
        except Exception, ex: pass
        e = ElementalExceptionType(ex).edt_dump()
        assert e == {'edt__typ': 'exception',
                     'edt__cls': 'mpx.lib.exceptions.ERangeError',
                     'args': (),
                     'name': 'bond, james bond',
                     'start': 'casino royal',
                     'end': 'not likely',
                     'keywords': {'cheese': 'has holes'},
                     'good_start': 'lawyer be gone',
                     'good_end': 'boy gets girl',
                     'message': '',}
        ed = dict(e)
        try: raise edt_decode(e)
        except mpxexc.ERangeError, r: pass
        else:
            raise Exception(
            'Did not catch expected mpx.lib.ERangeError exception'
            )
        assert r.args == ()
        assert r.name == 'bond, james bond'
        assert r.start == 'casino royal'
        assert r.end == 'not likely'
        assert r.keywords == {'cheese': 'has holes'}
        assert r.good_start == 'lawyer be gone'
        assert r.good_end == 'boy gets girl'
        assert r.message == ''
        assert edt_encode(r) == ed
        return
    def test_ElementalNodeType(self):
        assert ElementalNodeType(as_internal_node('/')).edt_dump() == {
            'edt__typ': 'node', 'path': '/'
            }
        ne = edt_decode({'edt__typ': 'node', 'path': '/services/time/local'})
        assert isinstance(ne,ElementalNodeType)
        assert ne.edt__typ == 'node'
        assert ne.path == '/services/time/local'
        re = {'edt__typ': 'node', 'path': '/'}
        assert edt_encode(as_internal_node('/')) == re
        assert edt_encode(as_node('/')) == re
        return
    def test_class_hierarchy_dict(self):
        from types import InstanceType
        assert_lookup = self.assert_lookup
        c = ClassHierarchyDict()
        try:
            c[c]
        except KeyError:
            pass
        else:
            self.fail("Did not raise KeyError for empty %r." % c)
        try:
            c.map(1, "error: only can add class/type entries.")
        except TypeError:
            pass
        else:
            self.fail("Did not raise TypeError for setting an instance.")
        try:
            c.lookup(object) == "error: only can lookup instances."
        except TypeError:
            pass
        else:
            self.fail("Did not raise TypeError for getting a class.")
        self.assert_(c.lookup(c) is None,
                     "Failed to return None as default.")
        c.map(int, "an integer")
        assert_lookup(c, 0, "an integer")
        c.map(bool, "a boolean")
        assert_lookup(c, True, "a boolean")
        c.map(object, "an object")
        assert_lookup(c, 4294967295L, "an object")
        c.map(long, "a long")
        assert_lookup(c, 4294967295L, "a long")
        assert_lookup(c, 0, "an integer")
        assert_lookup(c, object(), "an object")
        class N(object):
            pass
        n = N()
        assert_lookup(c, n, "an object")
        c.map(N, "an N")
        assert_lookup(c, n, "an N")
        class I(int):
            pass
        i = I()
        assert_lookup(c, i, "an integer")
        c.map(I, "an I")
        assert_lookup(c, i, "an I")
        assert_lookup(c, 0, "an integer")
        c.map(InstanceType, "an instance")
        class O:
            pass
        o = O()
        assert_lookup(c, o, "an instance")
        c.map(O, "an O")
        assert_lookup(c, o, "an O")
        class S(O):
            pass
        s = S()
        assert_lookup(c, s, "an O")
        c.map(S, "an S")
        assert_lookup(c, s, "an S")
        return

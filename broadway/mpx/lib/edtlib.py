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
"""
This 'Elemental Data Type Library' contains the list of elemental abstract
types supported by Broadway.  These are the fundimental types that can be
represented via RNA over any RPC transport (well, any RPC transport that
implements Elemental Data Types.)  Furthermore, this module contains
universal fallback representations to encode any type that is not directly
supported by the underlying RPC transport.

It is the RPC marshaller's resposibility to decide whether to directly use the
RPC's elemental-data-type, or encode an ElementalType.  The simple example is
that for XMLRPC Marshalling, the XMLRPC Marshaller should use the XMLRPC <i4>
encoding for any integer that will "fit" in a 4-byte integer.  For values
outside that range, the XMLRPC Marshaller should use this module to encode
an ElementalIntegerType.

Furthermore, the ElementalType encoders intentionally do not recurse when
encoding a value.  For example, the if the RPC layer needs to use this
module to encode UTF-8 strings, the ElementalTextType encodes the internal
ElementalTextType.text into a BinaryString(), NOT directly into an
ElementalDataType.  It is the RPC Marashaller's responsiblity to recurse
the ElementalTextType, see that the 'text' attribute is a BinaryString and
decide whether or not there is a native RPC representation or to encode that
as an ElementalDataType.

At this time, it is the RPC Marshaller's responsibility to handle transport
specific encoding/decoding for strings.  THIS SEEMS PHILOSOPHICALLY CORRECT,
BUT I'M RELIES ON CLIENTS AND THE RPC MARSHALLER "GETTING IT RIGHT.  I think
I'm OK with that...

class variables:
    edt__typ: Indicate that a dict is an encoded elemental data type.  Classes
              that wish to register a codec do not, and should not, manaully
              set this attribute.  OK, but pointless, to set it to 'object'

    edt__cls: May be in encoded elemental data type dicts.  Use is type
              specific.  Again, not explicitly required - register_class(cls)
              will calculate and add it.  Though if the class is not
              writable than its encoder must explicitly add it.
"""
if __name__ == '__main__':
    import os
    import sys
    os.chdir(os.path.dirname(sys.argv[0]))
    os.system("run_test_modules -v 2 _test_case_edtlib.pyc")

# edt__*: keywords that will be included in the marshalled object.
# _edt__*: keywords that will not be included in the marshalled object.

# FIXME: Confirm edt__/_edt__ with team.  mpx__/_mpx__ (or nmb, bdw, csco...)
#        may be preferred as "the" reserved attribute/key names in Broadway.
#        Then there is a single rule.  There could even be a file of
#        "reserved" names...
#        Also, there could be a single key to a meta-dict: E.g. _edt__meta = {}
# NOTE: Could use __new__() in ElementalDataTypes to behave as factories
#       for native data type...  Not sure, being able to create the base
#       types MAY be useful.
# FIXME: Should ElementalObjectType.edt_decode return and object?  Eh,
#        sort of nice to know it was an oddly decoded object.
# FIXME: Decide about interplay between marshaller and edt re: encoding
#        data, etc.  Can marshaler ask EDT to transform/encode for it?
#        Should marshaler/EDT transform entire object, or just the data
#        itself.
# FIXME: Allow defaulting values and not encoding defaults? (like [],0,''...)
# FIXME: For completenes elemental data type implementations should support
#        all the relavant __*__ methods.  Then they could even substitute for
#        that type (most useful when it is a type that does not exist), and
#        possibly could even become useful as a base class (Data and Enumerated
#        seem like good candidates.
# FIXME: Address _has_magnitude_interface, as_magnitude,
#        mpx/lib/bacnet/datatype.py.
# FIXME: Ideally, anything that redirects (deferred node,
#        mpx.lib._singleton._ReloadableSingleton, etc) will provide an encoder
#        that looks up the proper encoder...

typ_map = {}

class Error(Exception):
    pass

class AbstractError(Error):
    pass

class InstantiationError(Error):
    pass

##
# Behaves like an <code>String</code> but signifies that its
# value represents a binary object.  This allows for special
# handling of string data containing binary representations.
class BinaryString(str):
    pass

def _abstract(name,label='method'):
    raise AbstractError('Abstract %s %r not implemented' % (name,label))

class NoArg(object):
    def __repr__(self):
        return '<noarg>'
    def __str__(self):
        return 'noarg'

noarg=NoArg()

import mpx # FIXME: Importing mpx sets up some of the PYTHONLIB voodoo.
           #        Bad voodoo!

from base64 import standard_b64decode
from base64 import standard_b64encode
from inspect import isroutine
from struct import pack
from struct import unpack
from threading import RLock
from types import ClassType
from types import InstanceType
from types import ObjectType
from types import TypeType

def class_name(cls):
   """class_name(class) -> a string of the class' fully qualified name."""
   return '.'.join((cls.__module__,cls.__name__))

class ObjDict(dict):
    """
    A convienience class used so that classes that support edt_encode()ing
    can differenciate between a 'normal' dictionary and one that represents
    an elemental data type.  Primarily so that a class' __init__ method
    can accept a native/elemental instance or an encoded object.  E.g.:

    # Non-empty dictionary should be True, even though this looks like a
    # Boolean Type encodes as False.
    d = {'value':0}
    ElementalBooleanType(d) == True

    # But an ObjDict will be treated as an encoded Elemental Type, so
    # the same key,value pair now is False.
    m = ObjDict()
    m['value'] = 0  # or ObjDict({'value':0}), or ObjDict(('value',0))
    ElementalBooleanType(m) == False

    # A normal dictionary can be 'marked' to be treated like ObjDict()
    d = {'value':0}
    ObjDict.mkobjd(d)
    ElementalBooleanType(d) == False
    """
    @classmethod
    def isobjd(cls,d):
        """
        ObjDict.isobjd(d) -> True if d is an ObjDict or is a dictionary that
        has been 'marked' to be treated as an ObjDict.  Otherwise False.
        """
        return (isinstance(d,dict) and d.get('_edt__enc',False) or
                isinstance(d,cls))
    @classmethod
    def mkobjd(cls,d):
        """
        ObjDict.mkobjd(d) -> d 'marked' so ObjDict.isobjd(d) returns True.
        """
        d['_edt__enc'] = True
        return d

def default_attr_names(o):
    """
    default_attr_names(obj) -> List of attribute names "of interest" for
    the default encoding of an object.  This list essentially all attribute
    names that don't begin with '_' and don't reference any sort of 'routine'
    (function, method, callable...).
    """
    n=filter(lambda a: a[0] != '_', dir(o))
    n=filter(lambda a: not isroutine(getattr(o,a)), n)
    return n

def default_encoding(o, def__typ='object', def__cls=None):
    """
    default_encoding(object, def__typ='object', def__cls=None) -> a 'dict' that
    represents object O.

    If O does not have an 'edt__typ' attribute and def__typ is a
    string, then 'edt__typ' is set to def__typ.
    If O does not have an 'edt__cls' attribute and def__cls is a
    string, then 'edt__cls' is set to def__cls.  If def__cls is True,
    then 'edt__cls' is set to O's fully qualified class name.

    Note: This creates a valid internal 'fallback' object representation.
          It does not convert object to an elemental data type, that
          should happen before (and therefore instead of) this call if
          possible.  It also does not convert it's contents to
          elemental-data-types.  That should happen when actually
          marshaling.
    """
    anames=default_attr_names(o)
    d = ObjDict(map(lambda a: (a,getattr(o,a)), anames))
    if def__typ:
        if not d.has_key('edt__typ'): d['edt__typ'] = def__typ
    if def__cls:
           if isinstance(def__cls,basestring): d['edt__cls'] = def__cls
           else: d['edt__cls'] = class_name(o.__class__)
    return d

def load_from_map(obj, edt_map):
    """
    edt_map k,v -> obj attr,value: return obj
    """
    while edt_map:
        k,v = edt_map.popitem()
        setattr(obj,k,v)
    return obj

def get_from_map(obj, edt_map):
    """
    edt_map k,v -> obj attr,value: return obj.edt_get()
    """
    while edt_map:
        k,v = edt_map.popitem()
        setattr(obj,k,v)
    return obj.edt_get()

class ElementalType(object):
    """
    Base/Abstract class for all Elemental Types.  Never directly instanciate.

    FIXME:  Document use here, I find minimal comments in code actually improve
            readability in this case (as long as it is explained here.)
    """
    edt__typ = 'base' # Always replaced.
    def __init__(self,v=None):
        if ObjDict.isobjd(v):
            self.edt_decode(v,self)
        elif v is not None:
            self.edt_set(v)
        return
    edt_encode_hook = staticmethod(default_encoding)
    edt_decode_hook = staticmethod(get_from_map)
    @classmethod
    def edt_encode(cls,obj):
        if not isinstance(obj,cls):
            obj = cls(obj)
        return cls.edt_encode_hook(obj)
    @classmethod
    def edt_decode(cls,edt_map,obj=None):
        if obj is None:
            obj = cls()
        return cls.edt_decode_hook(obj,edt_map)
    def edt_dump(self):
        return self.edt_encode(self)
    def edt_load(self,d):
        return self.edt_decode(d)
    def edt_get(self):
        return self
    def edt_set(self,v): _abstract('edt_set')
    #   note: edt_set() is expected to return self to allow method chaining.
    def __eq__(self,other):
        my_names = default_attr_names(self)
        ur_names = default_attr_names(other)
        my_names.sort()
        ur_names.sort()
        if my_names != ur_names:
            return False
        for k in my_names:
            my_value = getattr(self,k)
            if my_value != getattr(other, k, not my_value):
                return False
        return True

# do not register ElementalType

# See: <http://www.ddj.com/web-development/184406073>
def synchronized(func):
    def wrapper(self,*__args,**__kw):
        try:
            rlock = self._sync_lock
        except AttributeError:
            # from threading import RLock
            rlock = self.__dict__.setdefault('_sync_lock',RLock())
        rlock.acquire()
        try:
            return func(self,*__args,**__kw)
        finally:
            rlock.release()
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper

class ClassHierarchyDict(object):
    """
    A map used to lookup values based on an instance's class, or the
    closest mapped super class.

    Mapping the `object' class to a value essentially provides a
    default for all instances (of both old and new-style classes).
    Mapping TypeInstance will provide a default value for all old-syle
    classes and will take precedence over `object'.
    """
    def __init__(self, d={}):
        # Most marshaled data is an instance of a "registered" class.
        # class_dict provides a direct look-up.
        self.class_dict = {}
        # Handle classes derived from registered classes by having a derivation
        # based priority array.
        self.class_list = []
        # Classes added internally for subclasses of registered classes.
        self.cached_classes = []
        self.update(d)
        return
    @synchronized
    def map(self, cls, val):
        """
        map(cls, val)

        Map val to cls such that lookup(instance of cls) -> val.
        """
        if not type(cls) in (TypeType,ClassType):
            raise TypeError("cls must be a class/type reference.")
        # Flush any cached classes since cls may be a base class.  Could
        # be trickier, but this should always work.
        while self.cached_classes:
            c = self.cached_classes.pop()
            self.class_dict.pop(c,None)
        self.class_dict[cls] = val
        def old_issubclass(sub,base):
            return (base in (ObjectType, InstanceType)
                    or issubclass(sub,base))
        _issubclass = issubclass if type(cls) is object else old_issubclass
        for i in range(0,len(self.class_list)):
            c, m = self.class_list[i]
            if _issubclass(cls,c):
                self.class_list.insert(i,(cls,val))
                return
        self.class_list.append((cls,val))
        return
    __setitem__ = map
    @synchronized
    def lookup(self, inst, d=None):
        """
        lookup(inst[,d]) -> val if inst (or any super of inst) is in self,
                            else d.  d defaults to None.

        Locate the val mapped to inst.__class__.  If cls itself has
        not been mapped, then return the val of the "closest" base
        class.
        """
        if type(inst) in (TypeType,ClassType):
            raise TypeError(
                    "inst must be reference an instance, not a class/type."
                    )
        cls = inst.__class__
        val = self.class_dict.get(cls,None)
        if val is None:
            for c, val in self.class_list:
                if isinstance(inst,c):
                    self.class_dict[cls] = val
                    self.cached_classes.append(cls)
                    return val
            return d
        return val
    get = lookup
    def __getitem__(self, inst):
        val = self.lookup(inst, noarg)
        if val is noarg:
            raise KeyError("Could not determine value for <inst of %r>" %
                           inst.__class__.__name__)
        return val
    @synchronized
    def merge_dict(self, d):
        for k in d.keys():
            self[k] = d[k]
        return
    @synchronized
    def merge_pairs(self, t):
        for k, v in t:
            self[k] = v
        return
    @synchronized
    def update(self, d, **kw):
        if hasattr(d, 'keys'):
            self.merge_dict(d)
        elif hasattr(d, '__len__'):
            self.merge_pairs(d)
        if kw:
            self.merg_dict(kw)
        return

class Codec(object):
    def __init__(self, name, decoder, encoder):
        self.name = name
        self.decoder = decoder
        self.encoder = encoder
        return

class CodecMap(ClassHierarchyDict):
    def __init__(self, d={}):
        self.name_dict = {}
        ClassHierarchyDict.__init__(self, d)
        return
    @synchronized
    def map(self, cls, codec, cls_name=noarg):
        """
        map(cls,codec)

        Map cls so lookup(instance of cls) -> codec # via inheritance
        and lookup_by_name(cls) -> codec            # via class_name(cls)
        """
        ClassHierarchyDict.map(self, cls, codec)
        if cls_name is noarg:
            cls_name = class_name(cls)
        self.name_dict[cls_name] = codec
    __setitem__ = map
    @synchronized
    def lookup_by_name(self, nam, d=None):
        """
        lookup_by_name(nam[,d]) -> codec

        Locate the codec mapped directly to nam.  If nam is not found, then
        return d.  d defaults to None.
        """
        return self.name_dict.get(nam,d)
    def __getitem__(self, cls_or_nam):
        if isinstance(cls_or_nam, basestring):
            codec = self.lookup_by_name(cls_or_nam)
        else:
            codec = self.lookup(cls_or_name)
        if codec is noarg:
            nam = cls_or_nam if isinstance(cls_or_nam, basestring) else (
                    cls_or_nam.__name__
                    )
            raise KeyError("Could not determine value for <inst of %r>" %
                           nam)
        return codec
    @synchronized
    def merge_dict(self, d):
        ClassHierarchyDict.merge_dict(self, d)
        for cls,cdc in d.keys():
            self.name_dict[class_name(cls)] = cdc
        return
    @synchronized
    def merge_pairs(self, t):
        ClassHierarchyDict.merge_pairs(self, t)
        for cls, cdc in t:
            self.name_dict[class_name(cls)] = cdc
        return

codec_map = CodecMap()

def register_class(cls, decoder=noarg, encoder=noarg,
                   set_cls=True, cls_name=noarg):
    """
    register_class(cls, decoder=None, encoder=None[,set_cls,cls_name])

    Adds class CLS to the dictionary of registered 'object' classes.

    DECODER is a callable that can decode and instanciate objects
    that report having a class of CLS.  If DECODER is None, then the
    CLS.edt_decode class method is required for decoding.

    ENCODER is a callable that can encode an instance of CLS as a dictionary.
    If ENCODER is None, then the CLS.edt_encode class method is required for
    encoding.

    SET_CLS primaraly so 'types' don't get edt__cls forced upon them.

    CLS_NAME primarily to support reverse compatibility after a refactor.
             Once a class is in the wild, 'edt__cls' CAN NOT change.
    """
    if not type(cls) in (TypeType,ClassType):
        raise TypeError("cls must be a class/type reference.")

    if cls_name is noarg:
        cls_name = class_name(cls)
    elif not isinstance(cls_name,basestring):
        raise TypeError("Optional cls_name must be a string/unicode string")
    if decoder is noarg: decoder = cls.edt_decode
    if encoder is noarg:
        encoder = (cls.edt_encode
                   if hasattr(cls,'edt_encode') else default_encoding)
    codec = Codec(cls_name,decoder,encoder)
    codec_map.map(cls, codec, cls_name)
    try:
        if set_cls:
            cls.edt__cls = cls_name # Unregestierred subclasses will use this
                                    # class' encodes/decoder.
    except:
        # It's OK not to be able to set the attribute as long as it doesn't
        # exist.
        if hasattr(cls, 'edt__cls'):
            raise
    return cls

def register_typ(cls, *represents, **codec):
    """
    Adds cls as an ElementalType.  FOR USE INTERNAL TO THIS MODULE ONLY.  To
    register class specific encoders and decoders use register_class().
    """
    assert issubclass(cls,ElementalType)
    typ_map[cls.edt__typ] = cls
    decoder = codec.get('decoder',noarg)
    encoder = codec.get('encoder',noarg)
    if decoder is noarg: decoder = cls.edt_decode
    if encoder is noarg: encoder = cls.edt_encode
    register_class(cls, decoder, encoder, set_cls=False)
    for c in represents:
        register_class(c, decoder, encoder)
    return

def import_class(name):
    mod,cls = name.rsplit('.',1)
    del cls
    mod = __import__(mod)
    for attr in name.split('.')[1:]:
        mod = getattr(mod, attr)
    return mod

def new_from_map(edt_map,obj=None):
    """
    new_from_map(edt_map) -> New ElementalObjectType instance with attributes
    populated from the key/value pairs of edt_map using load_from_map().
    """
    assert obj is None
    return load_from_map(ElementalObjectType(), edt_map)

class ElementalObjectType(ElementalType):
    """
    The catchall type for objects that are not 'built into' the
    intermediate object representation.
    """
    edt__typ = 'object'
    _edt_codec = Codec('default_codec', new_from_map, default_encoding)
    _edt_msg1 = ("Can only be set to instances without an edt__typ attribute"
                 " or with edt__typ='other' (not edt__typ=%r).")
    _edt_msg2 = "Can only be set to instances, not classes."
    _edt_msg3 = "%r is a 'builtin' type, and can't be cloned."
    # note: can not just replace edt_decode_hook because obj==None
    #       requires special handling for 'edt__cls'.
    @classmethod
    def edt_decode(cls,edt_map,self=None):
        if self is None:
            cls_name = edt_map.get('edt__cls', None)
            if not cls_name: cls_name = class_name(cls)
            cls_decoder = codec_map.lookup_by_name(cls_name,
                                                   cls._edt_codec).decoder
            return cls_decoder(edt_map)
        return load_from_map(self,edt_map)
    def edt_set(self,v):
        if hasattr(v,'edt__typ') and v.edt__typ != 'object':
            raise TypeError(self._edt_msg1 % v.edt__typ)
        elif type(v) in (TypeType,ClassType):
            raise TypeError(self._edt_msg2)
        elif v.__class__.__module__ == '__builtin__':
            raise TypeError(self._edt_msg3 % class_name(v.__class__))
        # Remove any previously set attributes:
        for n in default_attr_names(self):
            try:
                delattr(self,n)
            except AttributeError:
                # Won't delete the class attributes which is perfect.
                pass
        load_from_map(self, default_encoding(v))
        return self
def obj_from_dict(d):
    """
    Ensure that d is treated as encoded data and not a generic dictionary.
    """
    return ElementalObjectType(ObjDict.mkobjd(d))
def special_encoding(o):
    """
    Hack that allows recognizing the assorted flavors of nodes and encoding
    them simply as nodes.  This SHOULD NOT be extended to any other data
    type unless absolutely necessary.

    FIXME:  Clean up and merge node implementations so this function can be
            removed.
    """
    if ElementalNodeType.is_node(o):
        return ElementalNodeType.edt_encode(o)
    return ElementalObjectType.edt_encode(o)
register_typ(ElementalObjectType, object,
             decoder=obj_from_dict,
             encoder=special_encoding
             )

class ElementalNoneType(ElementalType):
    """
    For the encoding of no value.  None, nil, null, nada...
    """
    edt__typ = 'none'
    def edt_load(self,d): pass
    def edt_get(self): return None
    def edt_set(self,v): return self
    @classmethod
    def edt_decode(cls,d,self=None):
        return None
register_typ(ElementalNoneType, None.__class__)

# Booleans

class ElementalBooleanType(ElementalType):
    """
    A value that is either true or false.  Represented in Python as a bool().
    """
    edt__typ = 'bool'
    value = 0
    def edt_set(self,v):
        self.value = int(bool(v))
        return self
    def edt_get(self):
        return bool(self.value)
register_typ(ElementalBooleanType, bool)

# Numbers

class ElementalIntegerType(ElementalType):
    """
    Any integer value.  Represented in Python as an 'int' or a 'long'.

    This class supports integer values of unconstrained size.  The RPC
    marshaler should only use this class for values outside the range
    supported by the RPC mechanism.

    note: 'int' is all integers [-2147483648,2147483647]
    note: 'long' is all integers outside of [-2147483648,2147483647].
    """
    edt__typ = 'integer'
    bytes = []
    def edt_set(self,i):
        bytes = []
        self.bytes = bytes
        if i >= 0:
            b = 0
            while i:
                b = int(i & 0xff)
                bytes.insert(0,b)
                i = i >> 8
            if b & 0x80:
                bytes.insert(0,0)
        else:
            i = abs(i) - 1
            b = int(i & 0xff) ^ 0xff
            bytes.insert(0,b)
            i = i >> 8
            while i:
                b = int(i & 0xff) ^ 0xff
                bytes.insert(0,b)
                i = i >> 8
            if not b & 0x80:
                bytes.insert(0,0xff)
        return self
    def edt_get(self):
        if not self.bytes:
            return 0
        i = 0
        if self.bytes[0] & 0x80:
            for b in self.bytes:
                i = i << 8
                i = i | (b ^ 0xff)
            i = -i - 1
        else:
            for b in self.bytes:
                i = i << 8
                i = i | b
        return i
    def __int__(self):
        return self.edt_get()

register_typ(ElementalIntegerType, int, long)

class ElementalRealType(ElementalType):
    """Any real value.  Represented in Python as a float()."""
    edt__typ = 'real'
    data = BinaryString('\x00\x00\x00\x00\x00\x00\x00\x00')
    def edt_set(self,v):
        self.data = BinaryString(pack('!d',float(v)))
        return self
    def edt_get(self):
        return unpack('!d',self.data)[0]
register_typ(ElementalRealType, float)

class ElementalComplexType(ElementalType):
    """Any complex number.  Represented in Python as a complex()."""
    edt__typ = 'complex'
    real = 0.0
    imag = 0.0
    def edt_set(self,v):
        self.real = v.real
        self.imag = v.imag
        return self
    def edt_get(self):
        return complex(self.real,self.imag)
register_typ(ElementalComplexType, complex)

class ElementalEnumeratedType(int,ElementalType):
    """
    This is an extremely common data-type in the controls world.  It's
    usually transported as an integer of some sort without the string.
    Could be a fundimental type, or marshalled into an 'object'.
    """
    edt__typ = 'enumerated'
    num = 0
    str = ''
    def __init__(self, *args):
        ElementalType.__init__(self)
        n = len(args)
        assert n < 3
        if n is 0:
            v = 0
            s = '0'
        elif n is 1:
            if isinstance(args[0],(list,tuple)):
                self.__init__(*args[0])
                return
            v = int(args[0])
            s = str(v)
        else:
            v = int(args[0])
            s = args[1]
        self.num = v
        self.str = s
        return
    def __new__(cls, *args):
        if len(args) is 1:
            if isinstance(args[0],(list,tuple)):
                args = args[0]
        v = 0 if not args else int(args[0])
        return int.__new__(cls, v)
    def edt_set(self,v):
        if isinstance(v,dict):
            self.edt_decode_hook(self,v)
        elif isinstance(v,(tuple,list)):
            assert len(v) == 2
            assert isinstance(v[0],int)
            assert isinstance(v[1],basestring)
            self.num = v[0]
            self.str = v[1]
        else:
            self.num = v.num
            self.str = v.str
        return self
    def __str__(self):
        return self.str
    def __int__(self):
        return self.num
    def __repr__(self):
        return '<%s%r>' % (self.num,self.str)
register_typ(ElementalEnumeratedType)

# Sequences

class ElementalListType(ElementalType):
    """"
    All non-string sequences that do not have a specific marshaler,
    are represented as a Python list() (and are unmarshaled as
    the client languages 'list' analogue.)  This includes:
        'list', 'tuple', (set?,) and 'iter'
    """
    edt__typ = 'list'
    def __init__(self, *args):
        assert False, (
            "At this time, there is no fallback implementation for lists.  "
            "JSON, XML-RPC and 5150 all have lists of arbitrary length and "
            "implementing a generic fallback seems interesting but pointless "
            "at this time..."
            )
register_typ(ElementalListType, list, tuple)

class ElementalMapType(ElementalType):
    """
    A map is an associative array indexed by unique elemental data types.
    Unfortunately, XML-RPC and JSON only support keys that are strings.
    We commonly use any hashable object as a key.  The purpose of the
    ElementalMapType is to provide an alternate encoding of maps to work
    around this limitation.

    Sure, we could avoid non-strings as keys, but what fun would that be?

    As usual it is the protocol specific marshaller's responsiblity to
    determine when to add ElementalMapType encoding.  The decoder will
    automatically recurse on ElementalMapTypes containing other
    ElementalTypes.
    """
    edt__typ = 'map'      # Replaced for encoded elemental types.
    edt__map = 'edt__map' # Special case!
    _map_kvpairs = (('edt__map',0),)
    def __init__(self,v=None):
        if isinstance(v,(list,tuple)):
            self.edt_decode(v,self)
        elif v is not None:
            self.edt_set(v)
        return
    def edt_get(self):
        return self.edt_decode_hook(self, self._map_kvpairs)
    def edt_set(self,obj):
        self._map_kvpairs = self.edt_encode_hook(obj)
        return self
    @staticmethod
    def edt_decode_hook(obj, edt_map):
        assert edt_map[0][0] == 'edt__map'
        assert edt_map[0][1] == (len(edt_map)-1)
        obj._map_kvpairs = edt_map
        d = dict(edt_map[1:])
        if d.has_key('edt__typ'):
            return edt_decode(d)
        return d
    @staticmethod
    def edt_encode_hook(obj, def__typ='map', def__cls=None):
        if hasattr(obj,'_map_kvpairs'):
            return obj._map_kvpairs
        kv_pairs = [('edt__map',0),] # edt__map MUST be first.
        keys = (k for k in obj if k not in ('edt__map',))
        for k in keys:
            v = obj[k]
            kv_pairs.append((k,v))
        kv_pairs[0] = ('edt__map',len(kv_pairs)-1)
        return kv_pairs

register_typ(ElementalMapType, dict)

class ElementalDataType(ElementalType):
    """
    Any non-text sequence of bytes should be encapsulated as an type.
    This is a Broadway data-type.
    """
    edt__typ = 'data'
    edt__enc = 'b64'
    data = ''
    def edt_set(self,v):
        self.data = standard_b64encode(v)
        return self
    def edt_get(self):
        return standard_b64decode(self.data)
register_typ(ElementalDataType, BinaryString)

class ElementalTextType(ElementalType):
    """
    Any string of text.  Represented in Python as a str(),
    or unicode() string.  str() is assumed to be ASCII
    and unicode() is always encoded to UTF-8.

    FIXME:  Not 100% sure about this implementation.  Unicode -> binary seems
            logical.  str -> Really list of bytes is the only non-reentrant
                      but any RPC that requires that is pretty bogus.
    """
    edt__typ = 'text'
    edt__enc = 'bytes'
    text = ''
    def edt_get(self):
        return self.text
    def edt_set(self,t):
        if isinstance(t,unicode):
            self.edt__enc = 'utf-8'
            self.text = BinaryString(unicode.encode(t,'utf-8'))
        elif isinstance(t,str):
            self.edt__enc = 'bytes'
            self.text = map(ord,t)
        else:
            assert False, (
                "ElementalTextType expects str or, unicode")
        return self
register_typ(ElementalTextType, str, unicode)

class ElementalExceptionType(ElementalType):
    """
    The nightmare that started this whole thing.  Exceptions are an
    explicit type because they are common and should be readily
    identifiable.

    TBD:  would 'error' be a better type edt__typ than 'exception'?
    """
    edt__typ = 'exception'
    _edt_msg1 = ("Can only be set to instances with an 'edt__typ' attribute"
                 " of 'exception' (not edt__typ=%r) or instances "
                 " derived from the Exception class.")
    _edt_msg2 = ("Can only be set to instances with an 'edt__typ' attribute"
                 " of 'exception' or instances derived from the Exception"
                 " class (not %r).")
    def edt_set(self,e):
        if hasattr(e,'edt__typ') and e.edt__typ != 'exception':
            raise TypeError(self._edt_msg1 % e.edt__typ)
        elif not isinstance(e, Exception):
            raise TypeError(self._edt_msg2 % class_name(e.__class__))
        # Remove any previously set attributes:
        for n in default_attr_names(self):
            try:
                delattr(self,n)
            except AttributeError:
                # Won't delete the class attributes which is perfect.
                pass
        load_from_map(self, default_encoding(e, def__typ='exception',
                                             def__cls=class_name(e.__class__)))
        return self
    def edt_get(self):
        if not hasattr(self,'edt__cls'):
            return None
        try:
            assert self.edt__typ == 'exception'
            exc_cls = import_class(self.edt__cls)
            try:
                # args tuple is not reliable for 'backwards
                # compatibility', and may go away.  So first try to
                # instanciate the exception without args and then
                # manually copy all non-edt__* attributes onto the new
                # exeption instance.
                e = exc_cls()
                attrs = filter(lambda n: not n.startswith('edt__'),
                               default_attr_names(self))
                for attr in attrs:
                    setattr(e,attr,getattr(self,attr))
                return e
            except:
                pass
            # Manual setting of attributes failed, try using the args
            # as arguments.
            return exc_cls(*getattr(self,'args',()),
                            **getattr(self,'keywords',{}))
        except Exception, e:
            cls_name = getattr(self,'edt__cls', None)
            cls_ref = locals().get('exc_cls',None)
            exc_name = class_name(e.__class__)
            raise InstantiationError(
                'Exception %r prevented instantiating %r using %r'
                % (exc_name, cls_name, cls_ref)
                )
        raise Exception('Unreachable code reached.')

register_typ(ElementalExceptionType, Exception)

class ElementalNodeType(ElementalType):
    """
    A reference to a (presumably) remote node.

    The 'path' attribute is relative to the "remote" host, but does not
    include the remote host name/address nor the Node scheme.  This is
    the responsibility of the RPC Marshalling layer as it has that
    information.

    TBD: The amount of information to convey.  Probably less is better
         than more.  That way another layer could cache proxies, with
         what ever information makes sense requested once via a standardized
         API or RPC specific implementaion.
    """
    edt__typ = 'node'
    path = ''
    def edt_set(self,n):
        self.path = self.as_node_url(n)
        return self
    @classmethod
    def _is_node(cls,n):
        from mpx.lib import node
        cls._is_node = staticmethod(node.is_node)
        return node.is_node(n)
    @classmethod
    def is_node(cls,n):
        # FIXME: Hook to work around node implementations short comings.
        #        Should be removed as soon as Node implementations are
        #        merged and cleaned up.
        return cls._is_node(n)
    @classmethod
    def _as_node_url(cls,n):
        from mpx.lib import node
        cls._as_node_url = staticmethod(node.as_node_url)
        return node.as_node_url(n)
    @classmethod
    def as_node_url(cls,n):
        # FIXME: Hook to work around node implementations short comings.
        #        Should be removed as soon as Node implementations are
        #        merged and cleaned up.
        return cls._as_node_url(n)

register_typ(ElementalNodeType) # To avoid module recursion, Node classes are
                                #  registerred where they are defined.

def edt_encode(any_obj):
    return codec_map.lookup(any_obj).encoder(any_obj)

def edt_decode(edt_map):
    """
    edt_decode(edt_map) -> instance describe by EDT_MAP.

    EDT_MAP['edt__typ'] determines which ElementalType is used as a
    decoder (i.e. which ElementalType.edt_decode(edt_map) to invoke.)
    If there is no 'edt__typ', then ElementalMapType is used to
    essentially pass through the dictionary.
    """
    typ_name = 'map' if isinstance(edt_map,list) else edt_map.get('edt__typ',
                                                                  'object')
    cls = typ_map.get(typ_name,ElementalObjectType)
    return cls.edt_decode(edt_map)

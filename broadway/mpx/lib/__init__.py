"""
Copyright (C) 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 Cisco Systems

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
# This module and it's sub-modules provide the fundimental support functions
# required by Broadway.

# Import modules implented in MOAB.
from moab.lib import crc
import types
import os as _os
import string as _string
import warnings as _warnings
import types as _types
import weakref as _weakref
import threading
from Queue import Queue

from string import maketrans as _maketrans
from string import split as _split
from string import join as _join

##
# Msglog must be the first model to load.  This way it is available during
# the rest of the import process to log start-up errors.  Msglog relies on
# the log module, which in-turn relys on the persistent module.
import msglog

import time as _time

##
# This was a thread-safe alternative to the Python sleep() function.
# Now that Python's sleep is thread-safe, this is now longer required.
# @param seconds  The number of seconds to pause for.  This can be any
#                 positive real value.
#
pause = _time.sleep

##
# This was a thread-safe alternative to the Python sleep() function.
# Now that Python's sleep is thread-safe, this is now longer required.
# @param seconds  The number of seconds to pause for.  This can be any
#                 positive real value.
#
sleep = _time.sleep

del _time

class _QueuedActionThread(threading.ImmortalThread):
    def __init__(self,queue=Queue(-1),*args,**keywords):
        self._queue = queue
        self.debug = 0
        threading.ImmortalThread.__init__(self,*args,**keywords)
    def enqueue(self,function,*args,**keywords):
        if self.debug and not (len(self._queue.queue) % 10):
            print 'Callback Unwind Queue: %s entries' % len(self._queue.queue)
        self._queue.put((function,args,keywords),0)
    def run(self):
        while True:
            function,args,keywords = self._queue.get(1)
            try: function(*args,**keywords)
            except Exception,e:
                msglog.exception(
                    prefix='Callback Exception: %s%s failed' % (function,args))

#Callback(callback function, [arg1, arg2...], **keywords)
# call unwind_callbacks to execute all the stacked up callback functions
# The first parameter given to the callback function is "result", optional 
# arg(s) and keywords are passed in after result.
# 

class Callback(list):
    unwind_queue = _QueuedActionThread()
    unwind_queue.start()
    def __init__(self,*args,**keywords):
        self.__spent = 0
        self.callback(*args,**keywords)
    def callback(self,function,*args,**keywords):
        if keywords: keywords = keywords.copy()
        self.append((function,args,keywords))
    def _run_callback(self,*args,**keywords):
        try: 
            callback,cb_args,cb_keywords = self.pop() #get the most recent callback tuple
            if keywords: cb_keywords.update(keywords)
            if args: cb_args = args + cb_args
            result = callback(*cb_args,**keywords) #call the next callback with the whole shebang
        except Exception,error:
            msglog.exception()
            result = error
        return result
    def unwind_callbacks(self,result,*args,**keywords):
        spent,self.__spent = self.__spent,1
        if spent: 
            msglog.log('broadway',msglog.types.DB,
                       'Callback being double-rewound.  '
                       'Callback instance %s, with str "%s"' % (self,str(self)))
            msglog.traceback()
            raise Exception('Callback already rewound')
        self.unwind_queue.enqueue(self._runwind,result,*args,**keywords)
    def _runwind(self,result,*args,**keywords):
        while len(self):
            result = self._run_callback(result,*args,**keywords)
        return result

class Result(object):
    def __init__(self, value=None, timestamp=None, cached=1, changes=0):
        ##
        # The value or exception.
        #
        self.value = value
        ##
        # As close as possible, when value was actually 'read'.  This is
        # important in some cases where caching is used as the timestamp
        # will show when the value was last updated.
        self.timestamp = timestamp
        ##
        # True if the value returned was a cached value, or if the origin of
        # the value is uncertain.
        self.cached = cached
        ##
        # The number of times that the Subscription Node Reference supplying
        # this value has changes values.
        self.changes = changes
        return
    @classmethod
    def edt_encode(cls,obj):
        if not isinstance(obj,cls):
            obj = cls(obj)
        result = {
            # Same as edtlib.default_encoding(), hard coded to speed up.
            'edt__typ':'object',
            'edt__cls':'mpx.lib.Result',
            'cached':obj.cached,
            'changes':obj.changes,
            'timestamp':obj.timestamp,
            }
        if isinstance(obj.value,Exception):
            result['value'] = 'error:' + str(obj.value)
        else:
            result['value'] = obj.value
        return result
    @classmethod
    def edt_decode(cls,edt_map,obj=None):
        if obj is None:
            cached=edt_map['cached']
            changes=edt_map['changes']
            timestamp=edt_map['timestamp']
            value=edt_map['value']
            return Result(cached=cached,changes=changes,timestamp=timestamp,value=value)
        obj.cached=edt_map['cached']
        obj.changes=edt_map['changes']
        obj.timestamp=edt_map['timestamp']
        obj.value=edt_map['value']
        return obj
    def as_dict(self):
        return self.edt_encode(self)
    from_dict = edt_decode
    def __repr__(self):
        return repr(self.as_dict())
import edtlib
edtlib.register_class(Result)

##
# Behaves like an <code>int</code>eger, but <code>str()</code> returns
# descriptive text, <code>repr()</code> returns an eval string, and the
# <code>EnumeratedValue</code> can be compared to other
# <code>EnumeratedValue</code>'s, numbers and strings.
#
# @note The string comparison is only for equality with the associated text.
# @note Mathematical operations directly on an <code>EnumeratedValue</code>
#       result in a numeric (int, float, or complex) result.
from edtlib import ElementalEnumeratedType
class EnumeratedValue(ElementalEnumeratedType):
    _has_magnitude_interface = 1 # Implementation detail.
    def __eq__(self, other):
        if isinstance(other,str) or isinstance(other,unicode):
            return (self.str == other)
        return int(self) == other
    def __ne__(self, other):
        return (not (self.__eq__(other)))
    def _as_dict(self):
        return {"__base__":"EnumeratedValue",
                "__class__":"%s.%s" % (self.__module__,
                                       self.__class__.__name__),
                "num":int(self),
                "str":str(self),
                }
    def is_enum(self):
        return 1
    def enum(self):
        return {"num":int(self),
                "str":str(self),
                "_has_magnitude_interface":1
                }
    def __repr__(self):
        return repr(self._as_dict())
    ##
    # Setter and getter for this enumerated value's text.
    # @param text Optional StringType or UnicodeType to associate with this
    #             enumerated value.
    # @default None If no replacement text is specified, then this method
    #               returns the current associated text.
    # @return This enumerated value's text.
    def text(self, text=None):
        if text is None:
            return self.str
        if isinstance(text,str) or isinstance(text,unicode):
            self.str = text
            return text
        raise exceptions.ETypeError('text must be a StringType or UnicodeType')
    ##
    # @return The "most correct" native Python type.
    # @note This section is in support of the Magnitude interface.
    def as_magnitude(self):
        return int(self)
import edtlib
edtlib.register_class(EnumeratedValue)

##
# Behaves like an <code>String</code> but signifies that its
# value represents a binary object.  This allows for special
# handling of string data containing binary representations.
from edtlib import BinaryString

##
# Behaves like an dictionary, but contains only EnumeratedValues
# The look up key can be an integer, string or an EnumeratedValue
# The return value is an EnumeratedValue

class EnumeratedDictionary:
    ##
    # @value The <code>EnumeratedValue</code>'s integer value.
    # @text  The string to return when str() is invoked on this
    #        <code>EnumeratedValue</code>.
    def __init__(self, dict=None):
        self.int_dict = {} #int key dict
        self.str_dict = {} #string key dict
        if dict is not None: self.update(dict)
    def __repr__(self): return repr(self.int_dict)
    def __cmp__(self, dict):
        if isinstance(dict, EnumeratedDictionary):
            return cmp(self.int_dict, dict.int_dict)
        else:
            return cmp(self.int_dict, dict)
    def __len__(self): return len(self.int_dict)
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.int_dict[key]
        if isinstance(key, str):
            return self.str_dict[key]
    def __setitem__(self, key, item):
        v = None
        if isinstance(item, EnumeratedValue):
            v = item
        elif isinstance(item, int):
            if isinstance(key, str):
                v = EnumeratedValue(item, key)
        elif isinstance(item, str):
            if isinstance(key, int):
                v = EnumeratedValue(key, item)
        if key == v:
            self.int_dict[int(v)] = v
            self.str_dict[str(v)] = v
        else:
            raise KeyError
    def __delitem__(self, key):
        if isinstance(key, int):
            st = str(self.int_dict[key])
            del self.str_dict[st]
            del self.int_dict[key]
        elif isinstance(key, str):
            i = int(self.str_dict[key])
            del self.int_dict[i]
            del self.str_dict[key]
    def clear(self):
        self.int_dict.clear()
        self.str_dict.clear()
    def copy(self):
        return EnumeratedDictionary(self.int_dict)
    def keys(self): return self.int_dict.keys()
    def string_keys(self): return self.str_dict.keys()
    def items(self): return self.int_dict.items()
    def iteritems(self): return self.int_dict.iteritems()
    def iterkeys(self): return self.int_dict.iterkeys()
    def itervalues(self): return self.int_dict.itervalues()
    def values(self): return self.int_dict.values()
    def has_key(self, key):
        if isinstance(key, int):
            return self.int_dict.has_key(key)
        if isinstance(key, str):
            return self.str_dict.has_key(key)
        return 0
    def key_at_value(self, value):
        if isinstance(value, int):
            return self.str_dict.key_at_value(key)
        if isinstance(value, str):
            return self.int_dict.key_at_value(key)
        raise ValueError
    def update(self, dict):
        if isinstance(dict, EnumeratedDictionary):
            self.int_dict.update(dict.int_dict)
            self._string_dict_from_int_dict()
        elif (type(dict) == types.ListType): # list of instances of EnumeratedValue
            for ev in dict:
                self[int(ev)] = ev
        else:
            for k, v in dict.items():
                if isinstance(k, int):
                    if isinstance(v, EnumeratedValue):
                        self[k] = v
                    else:
                        self[k] = EnumeratedValue(k,v)
                if isinstance(k, str):
                    if isinstance(v, EnumeratedValue):
                        self[k] = v
                    else:
                        self[k] = EnumeratedValue(v,k)
                    
    def get(self, key, failobj=None):
        if not self.has_key(key):
            return failobj
        return self[key]
    def setdefault(self, key, failobj=None):
        if not self.has_key(key):
            self[key] = failobj
        return self[key]
    def popitem(self):
        answer = self.int_dict.popitem()
        self._rebuild_from(self.values())
        return answer
    def __contains__(self, key):
        if isinstance(key, int):
            return key in self.int_dict
        if isinstance(key, str):
            return key in self.str_dict
        return 0
    def _rebuild_from(self, values):
        self.int_dict = {}
        self.str_dict = {}
        for v in values:
            self.int_dict[int(v)] = v
            self.str_dict[str(v)] = v
    def _string_dict_from_int_dict(self):
        self.str_dict = {}
        for v in self.int_dict.values():
            self.str_dict[str(v)] = v
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.int_dict.__eq__(other.int_dict)
        return self.int_dict.__eq__(other)
    def __str__(self):
        return str(self.int_dict)
    def __contains__(self, item):
        return self.int_dict.__contains__(item)
    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return self.int_dict.__ge__(other.int_dict)
        return self.int_dict.__ge__(other)
    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self.int_dict.__gt__(other.int_dict)
        return self.int_dict.__gt__(other)
    def __hash__(self):
        self.str_dict.__hash__()
        return self.int_dict.__hash__()
    def __iter__(self):
        return self.int_dict.__iter__()
    def __le__(self, other):
        if isinstance(other, self.__class__):
            return self.int_dict.__le__(other.int_dict)
        return self.int_dict.__le__(other)
    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.int_dict.__lt__(other.int_dict)
        return self.int_dict.__lt__(other)
    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.int_dict.__ne__(other.int_dict)
        return self.int_dict.__ne__(other)
    def get(self, key, default=None):
        if self.has_key(key):
            return self[key]
        return default
    def setdefault(self, key, default): #default not optional
        if self.has_key(key):
            return self[key]
        self[key] = default
        return default

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                              repr(self.int_dict))

##
# Instantiated to create uniquely identifiable "constants" in the
# system.  They are identifiable via "is" as well as "==" and they are
# consistently sortable for lists and hash-able for fast lookups.
#
# The ability to sort any <code>UniqueToken</code> is extremely useful for
# sorted lists.
#
# Being hash-able means that the can participate in dictionaries, which
# is extremely useful for things like state machines or as tokens for
# replaceable messages, etc...
#
# Since each instance is guaranteed unique, there are no name-space
# management issues, an instance has unique identity and equality.
# Therefore, there is no confusion between two tokens with the same
# "name" even if they have the same name.
#
class UniqueToken:
    ##
    # Instantiate a <code>UniqueToken</code>.
    # @param name Handy for introspective purposes.  While typically a
    # string, any object that responds to repr is valid.
    # @default ''
    def __init__(self, name=''):
        self._name = name
    ##
    # No two unique constants return the same internal value.  They
    # are always sortable, comparable and uniquely identifiable.
    def __cmp__(self, other):
        return cmp(id(self), id(other))
    ##
    # The string representation of the constants name.
    def __str__(self):
        return str(self._name)
    ##
    # 
    def __repr__(self):
        return "%s(%s)" % (self.__class__, repr(self._name))
    ##
    #
    def __hash__(self):
        return id(self)

##
# @note It doesn't work if a derived class overloads __setattr__, but other
#       than that it works really well. 
# @todo Lazily detect derived classes that override __setattr__ and raise an
#       exception.
class ImmutableMixin:
    def __setattr__(self, attr, value):
        if self.__dict__.has_key('_immutable'):
            raise exceptions.EImmutable()
        else:
            self.__dict__[attr] = value
    def immutable(self):
        self.__dict__['_immutable'] = 1
    def mutable(self):
        if self.__dict__.has_key('_immutable'):
            del self.__dict__['_immutable']
    def is_mutable(self):
        return not self.__dict__.has_key('_immutable')

##
# Creates an immutable facade for an existing <code>instance</code>.  The
# facade will behave exactly like the orignal <code>instance</code>, except
# that it attributes are read only.  Any attempt to add or modify attributes
# to the facade will raise an <code>mpx.lib.exceptions.EImmutable</code>
# exception.
# @fixme Implement <code>locked</code>
class ImmutableWrapper:
    def __init__(self, instance, locked=0):
        self.__dict__['__instance'] = instance
    def __setattr__(self, attr, value):
        raise exceptions.EImmutable()
    def __getattr__(self, attr):
        return getattr(self.__dict__['__instance'], attr)

##
# Used to dynamically rebind an attribute to a method without creating
# a circular reference.
class WeakInstanceMethod(object):
    def __init__(self, instance, klass_method):
        self._instance = _weakref.ref(instance)
        self._klass_method = klass_method
        return
    def __call__(self, *args, **kw):
        return self._klass_method(self._instance(), *args, **kw)

# With msglog, exceptions, thread, threading, log we have a
# a functional Mediator Framework library.
import exceptions
import thread
import threading
import log

from _singleton import ReloadableSingletonInterface
from _singleton import ReloadableSingletonFactory
from _singleton import EReloadableSingleton
from _singleton import ELoadingDisabled

##
# Magic that completes the msglog's initialization.
# Flush all deferred messages in the msglog to its log.
msglog._ml._log_ready(log, ReloadableSingletonFactory, ELoadingDisabled)

# Force instanciation of actual msglog instance to avoid deadlocks created by
# failures to create other logs.
msglog.log_object().singleton_load()

_globals = {}
_locals  = {}
_modules = {}
##
# Helper function that imports a module by name.
def _import(module_name):
    global _globals
    global _locals
    global _modules
    if _modules.has_key(module_name):
        return _modules[module_name]
    module = __import__(module_name, _globals, _locals, [module_name])
    _modules[module_name] = module
    return module

##
# Generic factory for the MPX framework.
#
# @param callable_path A string that is the Python path to a callable
#                      object that does not require any arrguments.
#                      The callable object should an instance that
#                      implements the <code>CompositeNode</code>
#                      interface.  If the 
#                      <code>callable_path</code>, is a module than
#                      the <code>factory</code> function will look for
#                      a callable object named &quot;factory&quot;
#                      which it will use as callable object.
# @throws	 ImportError
# @return        An object that implements the
#                <code>ConfigurableNode</code> interface. 
def factory(callable_path):
    assert type(callable_path) in _types.StringTypes, (
        "callable_path must be a string type %r." % _types.StringTypes
        )
    iend = _string.rfind(callable_path,'.')
    if iend < 0:
        raise exceptions.EInvalidValue("callable_path", callable_path,
                                       "Improper factory specification: %r" %
                                       callable_path)
    module_path = callable_path[:iend]
    callable_base = callable_path[iend+1:]
    # Import the factory's module (or package).
    module = _import(module_path)
    if hasattr(module,callable_base):
        func = getattr(module,callable_base)
        if callable(func):
            # Execute the factory.
            _set_default_thread_stacklevel(4)
            try:
                return func()
            finally:
                _set_default_thread_stacklevel(None)
    # Reverse compatibility...
    module = _import(callable_path)
    func = getattr(module,'factory')
    # Execute the factory.
    _set_default_thread_stacklevel(4)
    try:
        return func()
    finally:
        _set_default_thread_stacklevel(None)
    raise EInternalError("Executed unreachable statement.")

import signal as _signal
_orig_exit = _os._exit
##
# Replacement for _os._exit which does not seem to work in a multi-threaded
# environment.
# @fixme Determine if this is still required.
def _exit(*code):
    # If all else fails, the sledge_hammer should do the deed in 60 seconds...
    def sledge_hammer():
        pause(60)
        _os.kill(0, _signal.SIGKILL)
    thread.start_new_thread(sledge_hammer, ())
    # Send all processes in our process group a SIGTERM.
    _os.kill(0, _signal.SIGTERM)

# Replace _os._exit.
_os._exit = _exit

_rot13_map = _maketrans('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        'nopqrstuvwxyzabcdefghijklmNOPQRSTUVWXYZABCDEFGHIJKLM')

##
# For simple obfuscation or to provide USENET style text envelopes.
# @warning  Only works on ASCII.
# @fixme Make Unicode compatible?
def rot13(text):
    return text.translate(_rot13_map)

_default_thread_stacklevel = {}
##
# Generate a simple deprecation message.
#
# @param message Message to associate with the deprecation warning.  Typically,
#                this message should contain a reference to the preferred
#                implementation.
def deprecated(message, stacklevel=None):
    if stacklevel is None:
        from mpx._python.thread import get_ident
        ident = get_ident()
        if _default_thread_stacklevel.has_key(ident):
            stacklevel = _default_thread_stacklevel[ident]
        else:
            stacklevel = 3
    _warnings.warn(message, DeprecationWarning, stacklevel)
    return

def _set_default_thread_stacklevel(stacklevel):
    from mpx._python.thread import get_ident
    ident = get_ident()
    if stacklevel is None:
        if _default_thread_stacklevel.has_key(ident):
            del _default_thread_stacklevel[ident]
    else:
        _default_thread_stacklevel[ident] = stacklevel
    return

#
# LOAD CUSTOM DATA MARSHALLERS
#

def _load_custom_marshallers():
    import xmlrpc
    from xmlrpclib import register_marshaller
    from stream import StreamingTupleWithCallback
    from xmlrpclib import ArrayMarshaller
    from xmlrpclib import DictMarshaller
    from xmlrpclib import ExceptionMarshaller
    from xmlrpclib import FloatMarshaller
    from xmlrpclib import IntMarshaller
    from xmlrpclib import LongMarshaller
    from xmlrpclib import StringMarshaller
    register_marshaller(Exception, ExceptionMarshaller())
    register_marshaller(StreamingTupleWithCallback, ArrayMarshaller())
    register_marshaller(dict, DictMarshaller())
    register_marshaller(float, FloatMarshaller())
    register_marshaller(int, IntMarshaller())
    register_marshaller(list, ArrayMarshaller())
    register_marshaller(long, LongMarshaller())
    register_marshaller(str, StringMarshaller())
    register_marshaller(tuple, ArrayMarshaller())
    return

_load_custom_marshallers()

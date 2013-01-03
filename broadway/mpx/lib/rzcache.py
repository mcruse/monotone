"""
Copyright (C) 2010 2011 Cisco Systems

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
from mpx.lib.threading import Lock

class CacheListKey(object):
    def __init__(self, arg):
        self.arg = []
        for item in arg:
            self.arg.append(CacheKey(item))
        return
    def __repr__(self):
        return repr(self.arg)
    def __cmp__(self, other):
        return cmp(self.arg, other.arg)
    def __eq__(self, other):
        return self.arg == other.arg
    def __hash__(self):
        return hash(repr(self))

class CacheTupleKey(object):
    def __init__(self, arg):
        tmp = CacheListKey(arg)
        self.arg = tuple(tmp.arg)
        return
    def __repr__(self):
        return repr(self.arg)
    def __cmp__(self, other):
        return cmp(self.arg, other.arg)
    def __eq__(self, other):
        return self.arg == other.arg
    def __hash__(self):
        return hash(self.arg)

class CacheDictKey(object):
    def __init__(self, arg):
        self.arg = {}
        for key, value in arg.items():
            self.arg[CacheKey(key)] = CacheKey(value)
        return
    def __repr__(self):
        keys = self.arg.keys()
        keys.sort()
        elements = ['{']
        for key in keys:
            elements.append(repr(key))
            elements.append(':')
            elements.append(repr(self.arg[key]))
            elements.append(',')
        elements.append('}')
        return ''.join(elements)
    def __cmp__(self, other):
        return cmp(self.arg, other.arg)
    def __eq__(self, other):
        return self.arg == other.arg
    def __hash__(self):
        return hash(repr(self))

class CacheFunctionKey(object):
    def __init__(self, arg):
        self.arg = arg
        return
    def __repr__(self):
        return self.arg.__name__
    def __cmp__(self, other):
        return cmp(repr(self), repr(other))
    def __eq__(self, other):
        return repr(self) == repr(other)
    def __hash__(self):
        return hash(repr(self))

class CacheKey(object):
    SIMPLE_TYPES = (types.FloatType, types.IntType, types.LongType,
                    types.NoneType, types.StringType, types.UnicodeType)
    def __init__(self, arg):
        if isinstance(arg, CacheKey.SIMPLE_TYPES):
            self.arg = arg
        elif isinstance(arg, types.ListType):
            self.arg = CacheListKey(arg)
        elif isinstance(arg, types.TupleType):
            self.arg = CacheTupleKey(arg)
        elif isinstance(arg, types.DictType):
            self.arg = CacheDictKey(arg)
        elif isinstance(arg, types.FunctionType):
            self.arg = CacheFunctionKey(arg)
        else:
            raise 'Non-supported type: %s' % type(arg)
        return
    def __repr__(self):
        return repr(self.arg)
    def __cmp__(self, other):
        return cmp(self.arg, other.arg)
    def __eq__(self, other):
        return self.arg == other.arg
    def __hash__(self):
        return hash(self.arg)

class SuperSimpleCacheKey(object):
    def __init__(self, function, *args):
        self.key = (CacheKey(function), CacheKey(args))
        return
    def __repr__(self):
        return repr(self.key)
    def __cmp__(self, other):
        return cmp(self.key, other.key)
    def __eq__(self, other):
        return self.key == other.key
    def __hash__(self):
        return hash(self.key)

class SuperSimpleCache(object):
    def __init__(self):
        self.cache = {}
        self.__lock = Lock()
        return
    def lazy_get(self, function, args):
        key = SuperSimpleCacheKey(function, *args)
        self.__lock.acquire()
        try:
            if self.cache.has_key(key):
                return self.cache[key]
            result = function(*args)
            self.cache[key] = result
        finally:
            self.__lock.release()
        return result
    def update_and_get(self, function, args):
        key = SuperSimpleCacheKey(function, *args)
        self.__lock.acquire()
        try:
            result = function(*args)
            self.cache[key] = result
        finally:
            self.__lock.release()
        return result
    def clear(self, function, args):
        key = SuperSimpleCacheKey(function, *args)
        self.__lock.acquire()
        try:
            if self.cache.has_key(key):
                del self.cache[key]
        finally:
            self.__lock.release()
        return
    def cache_keys(self):
        self.__lock.acquire()
        try:
            result = self.cache.keys()
        finally:
            self.__lock.release()
        return result
    def new_sorted_entry(self, key, entry, cmp_function):
        self.__lock.acquire()
        try:
            if self.cache.has_key(key):
                theList = self.cache[key]
                if entry not in theList:
                    theList.append(entry)
                    theList.sort(cmp_function)
        finally:
            self.__lock.release()
        return
    def del_entry(self, key, entry):
        self.__lock.acquire()
        try:
            if self.cache.has_key(key):
                theList = self.cache[key]
                if entry in theList:
                    theList.remove(entry)
        finally:
            self.__lock.release()
        return

COMMON_CACHE = SuperSimpleCache()

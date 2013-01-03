"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
# Assorted cache implementations for the Capstone MicroTurbine.
# @todo CommandCache, CachedION, cache_maps, (possibly separate RO and RW maps.)

import time

from mpx.lib.node import CompositeNode
from mpx.lib.threading import Lock

##
# Object that maintains a read-only Capstone MicroTurbine
# command response cache.
class RO_CommandCache:
    class CommandION(CompositeNode):
        ##
        # @param rgvm A string representation of the Response Get Value Method.
        #        Example 'self.cached_response().engdt1_response().engine_rpm'.
        def __init__(self, cache, name, rgvm, args):
            CompositeNode.__init__(self)
            self.parent = cache.ion()
            self.name = name
            self._cache = cache
            file = 'mpx.ion.capstone.micro_turbine.personality.RO_CommandCache.CommandION.__init__'
            self._compiled_reference = compile(rgvm, file, 'eval')
            self._rgvm_args = args
            self.parent._add_child(self)
        def cached_response(self):
            return self._cache.cached_response()
        def get(self, skipCache=0):
            cache = self._cache
            cache.lock()
            try:
                response, cached = cache._response()
                value = apply(eval(self._compiled_reference), self._rgvm_args)
            finally:
                cache.unlock()
            return value
        def get_result(self, skipCache=0, **keywords):
            cache = self._cache
            cache.lock()
            try:
                response, cached = cache._response()
                result = Result()
                result.timestamp = cache.timestamp()
                result.cached = cached
                result.value = apply(eval(self._compiled_reference), self._rgvm_args)
            finally:
                cache.unlock()
            return result
    def __init__(self, parent, line_handler, command, timeout=1.0):
        self._ion = parent
        self._lh = line_handler
        self._command = command
        self._timeout = timeout
        self._cache = None
        self._timestamp = time.time()
        self._expire_after = self._timestamp - 1.0
        self._lock = Lock() # Light weight, non-reentrant lock.
        self._map = {}
    ##
    # @return The time that the cache was last refreshed.
    def timestamp(self):
        return self._timestamp
    ##
    # @return The ion that is considerred the parent of all cached values.
    def ion(self):
        return self._ion
    ##
    # @return True if the cache is valid.
    def is_valid(self):
        return self._cache and self._expire_after >= time.time()
    ##
    # @return True if the cache is dirty (not valid).
    def is_dirty(self):
        return not self.is_valid()
    ##
    # Mark the cache as dirty, forcing a refresh on the next read.
    def mark_dirty(self):
        self._cache = None
    ##
    # Lock the cache for exclusive access.
    def lock(self):
        self._lock.acquire()
    ##
    # Unlock the cache from exclusive access mode.
    def unlock(self):
        self._lock.release()
    ##
    # Return the cached response, if any.
    def cached_response(self,skipCache=0):
        return self._cache
    ##
    # Refresh the cache from the command.
    # @note Should only be invoked locked.
    def _refresh(self):
        self._cache = self._lh.command(self._command)
        self._timestamp = time.time()
        self._expire_after = self._timestamp + self._timeout
    ##
    # Return the cached response, ensuring it is minty fresh.
    # @note Should only be invoked locked.
    def _response(self,skipCache=0):
        cached = 1
        if skipCache or not self.is_valid():
            self._refresh()
            cached = 0
        return self._cache, cached
    ##
    # @param rgvm A string representation of the Response Get Value Method. 
    def map_child(self, name, rgvm, args=()):
        cache = self
        child = self.CommandION(cache, name, rgvm, args)
        self._map[name] = child

##
# Base class to implement ions that 'cache' a single value and allows
# for complex set behavior.
class SingleValueCommand(CompositeNode):
    ##
    # @param parent The parent node of this ion.
    # @param name The name of this ion.
    # @param query An instance of a command.Message to use to get the ion's value.
    # @param get_value A function that accepts a single response.Reponse argument.
    # @param set_value An optional function that is passed
    #        self.parent, self, value, and asyncOK in that order.
    # @default None
    # @param timeout Optional timeout in seconds.
    # @default 1.0
    def __init__(self, parent, name, query, get_value, set_value=None, timeout=1.0):
        CompositeNode.__init__(self)
        self.parent = parent
        self.name = name
        self._query = query
        self._get_func = get_value
        self._set_func = set_value
        self._timeout = timeout
        self._lh = parent.line_handler
        ##
        # The 'cached' value.
        self._value = None
        self._timestamp = time.time()
        self._expire_after = self._timestamp - 1.0
        # @todo Better Voodoo.
        if set_value:
            # Add the set attribute as a hint to the node browser.
            self.set = self._set
        self.parent._add_child(self)
    ##
    # @return True if the cache is valid and skipCache == 0.
    def is_valid(self, skipCache=0):
        if skipCache or not self._value:
            return 0
        return self._expire_after >= time.time()
    ##
    # Set the ion's value.
    def _set(self,value,asyncOK=1):
        self._value = None
        self._set_func(self.parent,self,value,asyncOK)
    ##
    # Get the ion's value.
    # @fixme Not quite thread safe...
    def get(self,skipCache=0):
        if not self.is_valid(skipCache):
            response = self._lh.command(self._query)
            self._cached = 0
            self._timestamp = time.time()
            self._expire_after = self._timestamp + self._timeout
            self._value = self._get_func(response)
        else:
            self._cached = 1
        return self._value
    ##
    # Get the ion's result.
    # @fixme Not quite thread safe...
    def get_result(self,skipCache=0, **keywords):
        result = Result()
        result.value = self.get(skipCache)
        result.cached = self._cached
        result.timestamp = self._timestamp
        return result

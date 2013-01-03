"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
import time
import copy
import weakref
from threading import Lock
from mpx.lib import Result
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.lib.uuid import UUID
from mpx.lib.neode.interfaces import ISettable
from mpx.lib.neode.interfaces import IOverridable
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from mpx.lib.scheduler import scheduler

class _CallableConstant(object):
    cache = {}
    def __new__(klass, value):
        instance = klass.cache.get(value)
        if instance is None:
            instance = super(_CallableConstant, klass).__new__(klass, value)
        return klass.cache.setdefault(value, instance)
    def __init__(self, value):
        self.value = value
    def __call__(self):
        return self.value

class OverridablePointResult(Result):
    def __init__(self, value, timestamp, overridden, 
                 override_id = None, overridden_at = None, clears_at = None):
        self.overridden = overridden
        self.override_id = override_id
        self.overridden_at = overridden_at
        self.clears_at = clears_at
        super(OverridablePointResult, self).__init__(value, timestamp)
    def as_dict(self):
        dictionary = super(OverridablePointResult, self).as_dict()
        dictionary['overridden'] = self.overridden
        if self.overridden:
            dictionary['override_id'] = self.override_id
            dictionary['overridden_at'] = self.overridden_at
            dictionary['clears_at'] = self.clears_at
        return dictionary
    def equals(self, other):
        return (type(other) is type(self) and 
                other.value == self.value and 
                other.overridden == self.overridden and 
                other.override_id == self.override_id)

class OverridablePoint(object):
    adapts(ISettable)
    implements(IOverridable)
    active_overrides = {}
    
    def __new__(klass, node, urlbase = ''):
        overridable = klass.active_overrides.get(node.url)
        if overridable is None:
            overridable = super(OverridablePoint, klass).__new__(klass, node, urlbase)
        # Trickery intended to prevent race-conditions wherein an 
        #   active override is cached after first line of this method.
        return klass.active_overrides.get(node.url, overridable)

    def __init__(self, node, urlbase = ''):
        self.node = node
        self.__urlbase = urlbase
        self.__state_lock = Lock()
        self.__override = None
        self.__overridden_at = None
        self.__clears_at = None
        self._clearing_value = None
        self.__last_result = None
        self.__cov_registered = False
        self.__dispatcher = Dispatcher()
        self.__dispatcher.__consumers = weakref.WeakKeyDictionary()
        self.source = None
        super(OverridablePoint, self).__init__(node)

    def set_clearing_value(self, value):
        self._clearing_value = value

    def get_clearing_value(self):
        return self._clearing_value

    def override(self, value, seconds = None, *clearing_value):
        if len(clearing_value):
            self.set_clearing_value(clearing_value[0])
        self.__state_lock.acquire()
        try:
            self.__override = override = UUID()
            self.__overridden_at = time.time()
            self.__clears_at = None
            self.node.set(value)
            self.active_overrides.setdefault(self.node.url, self)
            if seconds is not None:
                self.__clears_at = self.__overridden_at + seconds
                scheduler.at(self.__clears_at, self.clear_override, (override,))
        finally:
            self.__state_lock.release()
        self.__notify_if_changed()
        return override

    def is_overridden(self):
        self.__state_lock.acquire()
        override = self.__override
        self.__state_lock.release()
        return override is not None

    def is_overridden_by(self, override_id):
        if override_id is None:
            raise ValueError('Provided "override_id" cannot be None.')
        return self.get_override_id() == override_id

    def get_override_id(self):
        self.__state_lock.acquire()
        override_id = self.__override
        self.__state_lock.release()
        return override_id

    def clear_override(self, override_id = None):
        self.__state_lock.acquire()
        try:
            current_id = self.__override
            if current_id is not None and override_id in (None, current_id):
                self.node.set(self.get_clearing_value())
                cleared_override = True
                self.__override = None
                self.__overridden_at = None
                self.__clears_at = None
                del(self.active_overrides[self.node.url])
            else:
                cleared_override = False
        finally:
            self.__state_lock.release()
        self.__notify_if_changed()
        return cleared_override
    
    def get_result(self, skip_cache = 0):
        self.__state_lock.acquire()
        try:
            value = self.node.get()
            result = self.__build_result(value, False)
        finally:
            self.__state_lock.release()
        return result
    
    def __build_result(self, value, blocking = False):
        locked = self.__state_lock.acquire(blocking)
        try:
            override_id = self.__override
            overridden_at = self.__overridden_at
            clears_at = self.__clears_at
            timestamp = time.time()
        finally:
            if blocking or locked:
                self.__state_lock.release()
        overridden = int(override_id is not None)
        result = OverridablePointResult(value, timestamp, overridden, 
                                        override_id, overridden_at, clears_at)
        return result
    
    def event_subscribe(self, consumer, event_type, *args, **kw):
        event_subscribe = getattr(self.node, 'event_subscribe')
        if issubclass(event_type, ChangeOfValueEvent):
            if getattr(self.node, 'has_cov', _CallableConstant(False))():
                self.__state_lock.acquire()
                try:
                    dispatcher = self.__dispatcher
                    handler = consumer.event_handler
                    sid = dispatcher.register_for_type(handler, event_type)
                    dispatcher.__consumers[consumer] = sid
                    if not self.__cov_registered:
                        self.__cov_registered = True
                        try: 
                            event_subscribe(self, event_type, *args, **kw)
                        except: 
                            self.__cov_registered = False
                            raise
                finally:
                    self.__state_lock.release()
        else: event_subscribe(consumer, event_type, *args, **kw)
        result = self.get_result()
        self.__dispatch_cov(self.__last_result, result)
        self.__last_result = result
        
    def event_unsubscribe(self, consumer, event_type, *args, **kw):
        event_unsubscribe = getattr(self.node, 'event_unsubscribe')
        if issubclass(event_type, ChangeOfValueEvent):
            self.__state_lock.acquire()
            try:
                dispatcher = self.__dispatcher
                sid = dispatcher.__consumers.get(consumer)
                if sid is None:
                    print 'Unsubscribe has no matching consumer, ignoring.'
                    return
                else:
                    dispatcher.unregister(sid)
                    del(dispatcher.__consumers[consumer])
                if self.__cov_registered and not len(dispatcher.__consumers):
                    event_unsubscribe(self, event_type, *args, **kw)
                    self.__cov_registered = False
            finally:
                self.__state_lock.release()
        else: event_unsubscribe(consumer, event_type, *args, **kw)
    
    def __event_handler(self, event, *args, **kw):
        result = self.__build_result(event.value)
        return self.__notify_if_changed(result)
    
    def __notify_if_changed(self, result = None):
        if not self.__cov_registered:
            self.__last_result = None
            return
        last_result = self.__last_result
        if result is None:
            result = self.get_result()
        self.__last_result = result
        if not result.equals(last_result):
            self.__dispatch_cov(last_result, result)
            return
            
    def __dispatch_cov(self, last_result, result):
        cov = ChangeOfValueEvent(self, last_result, result, result.timestamp)
        return self.__dispatcher.dispatch(cov)
        
    def __getattr__(self, name):
        if name == 'event_handler' and self.__cov_registered:
            return self.__event_handler
        return getattr(self.node, name)
    
    def __eq__(self, other):
        return self.url == other.url
    
    def __get_url(self):
        return self.__urlbase + self.node.url
    url = property(__get_url)


register_adapter(OverridablePoint)


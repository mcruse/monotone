"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
# Refactor 2/11/2007
import time
import inspect
from _utilities import CollectableCallback
from _utilities import Expired
from interfaces import IDispatcher
from mpx.lib import msglog
from mpx.componentry.backports import Dictionary
from mpx.componentry import implements
from mpx.componentry import register_utility
from mpx.lib.thread_pool import NORMAL

class ALL(object): pass
class Dispatcher(object):
    implements(IDispatcher)
    dispatchers = Dictionary()

    def __new__(klass, name = None, *args, **keywords):
        dispatcher = Dispatcher.dispatchers.get(name, None)
        if dispatcher is None:
            dispatcher = super(Dispatcher,klass).__new__(klass,name,*args,**keywords)
            if name is not None:
                named = Dispatcher.dispatchers.setdefault(name, dispatcher)
                # If a race-condition existed, 'dispatcher' would not be 'new'
                #   and should not, in that case, be initialized.
                if named is dispatcher:
                    register_utility(dispatcher,IDispatcher,name)
                else: return dispatcher
            dispatcher.initialize(name, *args, **keywords)
        return dispatcher
    def __init__(self, *args, **kw):
        super(Dispatcher, self).__init__()
    def initialize(self, name, debug = True):
        if name is None: name = id(self)
        self.id = name
        self.debug = debug
        self.sources = {ALL: {}}
        self.topics = {ALL: {}}
        self.types = {ALL: {}}

    def register_for_type(
            self, callback, event_type, source = ALL, fast = True):
        if source is None: source = ALL
        return self.register_for(callback, [event_type], [ALL], [source], fast)

    def register_for_types(
            self, callback, event_types, source = ALL, fast = True):
        if source is None: source = ALL
        return self.register_for(callback, event_types, [ALL], [source], fast)

    def register_for_topic(
            self, callback, topic, source = ALL, fast = True):
        if source is None: source = ALL
        return self.register_for(callback, [ALL], [topic], [source], fast)

    def register_for_topics(
            self, callback, topics, source = ALL, fast = True):
        if source is None: source = ALL
        return self.register_for(callback, [ALL], topics, [source], fast)

    def register_for_source(
            self, callback, source, event_type = ALL, topic = ALL, fast = True):
        if event_type is None: event_type = ALL
        if topic is None: topic = ALL
        return self.register_for(
            callback, [event_type], [topic], [source], fast)

    def register_for_sources(
            self, callback, sources, event_type = ALL, topic = ALL, fast = True):
        if event_type is None: event_type = ALL
        if topic is None: topic = ALL
        return self.register_for(
            callback, [event_type], [topic], sources, fast)

    def register_for(self, callback, types, topics, sources, fast = True):
        if types is None: types = [ALL]
        if topics is None: topics = [ALL]
        if sources is None: sources = [ALL]
        callback = CollectableCallback(callback, fast)
        for event_type in types:
            self.types.setdefault(event_type, {})[callback.guid] = callback
        for source in sources:
            self.sources.setdefault(source, {})[callback.guid] = callback
        for topic in topics:
            self.topics.setdefault(topic, {})[callback.guid] = callback
        callback.types = types
        callback.topics = topics
        callback.sources = sources
        return callback.guid

    def unregister(self, guid):
        callback = CollectableCallback.get_callback(guid)
        for event_type in callback.types:
            try: 
                del(self.types[event_type][guid])
            except KeyError:
                pass
        for topic in callback.topics:
            try: 
                del(self.topics[topic][guid])
            except KeyError:
                pass
        for source in callback.sources:
            try: 
                del(self.sources[source][guid])
            except KeyError:
                pass
        return

    def dispatch(self, event, topics = None, *args, **kw):
        if not isinstance(topics, (list, tuple)): topics = [topics]
        source_listeners = self.sources[ALL].copy()
        if hasattr(event, 'source'):
            source_listeners.update(self.sources.get(event.source, {}))
        topic_listeners = self.topics[ALL].copy()
        for topic in topics:
            topic_listeners.update(self.topics.get(topic, {}))
        type_listeners = self.types[ALL].copy()
        # Listners for type(event) or any of its superclasses.
        eventmro = inspect.getmro(type(event))
        for etype in eventmro:
            type_listeners.update(self.types.get(etype, {}))
        set = type_listeners.keys()
        set = filter(topic_listeners.has_key, set)
        set = filter(source_listeners.has_key, set)
        callbacks = map(source_listeners.get, set)

        fast, slow = [], []
        for callback in callbacks:
            if callback.is_fast(): fast.append(callback)
            else: slow.append(callback)
        if fast: self.run_callbacks(fast, event, *args, **kw)
        if slow: self.queue_callbacks(slow, event, *args, **kw)
        return len(callbacks)

    def timed_dispatch(self, *args, **kw):
        tstart = time.time()
        result = self.dispatch(*args, **kw)
        tend = time.time()
        return result

    def run_callbacks(self, callbacks, event, *args, **kw):
        expired = []
        for callback in callbacks:
            try: 
                callback(event, *args, **kw)
            except Expired:
                expired.append(callback)
            except Exception, error:
                msglog.exception(prefix="handled")
        for callback in expired:
            self.unregister(callback.guid)
        return len(callbacks)

    def queue_callbacks(self, callbacks, event, *args, **kw):
        NORMAL.queue_noresult(self.run_callbacks,callbacks,event,*args,**kw)
        return len(callbacks)

    def message(self, message, mtype='debug'):
        if getattr(self, mtype, True):
            print message
        return


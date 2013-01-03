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
# Refactor 2/11/2007
import weakref
from mpx.lib.uuid import UUID
from mpx.lib import msglog

class Expired(Exception):
    def __init__(self, guid, *args, **kw):
        self.guid = guid
        Exception.__init__(self, *args, **kw)

class CollectableCallback(object):
    instances = weakref.WeakValueDictionary()

    def get_callback(klass, guid):
        return klass.instances[guid]
    get_callback = classmethod(get_callback)

    def __new__(klass, callback, fast = True):
        guid = UUID()
        # Naming object that will be 'self' in instance methods, 'self'.
        self = super(CollectableCallback, klass).__new__(klass, callback, fast)
        CollectableCallback.instances[guid] = self
        self.initialize(callback, guid, fast)
        return self
    def __init__(self, *args, **kw):
        super(CollectableCallback, self).__init__()

    def initialize(self, callback, guid, fast = True):
        self.__guid = guid
        self.subject = None
        self.callback = callback
        if hasattr(callback, 'im_self'):
            self.subject = weakref.ref(callback.im_self)
            self.callback = callback.im_func
        self._fast = fast
    def is_fast(self):
        return self._fast
    def make_args(self, args):
        if self.subject is not None:
            subject = self.subject()
            if subject is None: raise Expired(self.guid)
            args = (subject,) + args
        return args
    def __call__(self, *args, **kw):
        args = self.make_args(args)
        return self.callback(*args, **kw)
    def __get_guid(self): return self.__guid
    guid = property(__get_guid)

import Queue
from threading import Thread, Event
class SimpleThreadPool(object):
    class Worker(Thread):
        def __init__(self, queue, stopevent = None):
            if stopevent is None:
                stopevent = Event()
            self.stopevent = stopevent
            self.queue = queue
            Thread.__init__(self)
        def run(self):
            while not self.stopevent.isSet():
                function, args, keywords = self.queue.get(True)
                try: function(*args, **keywords)
                except: msglog.exception()
            else: print 'Terminating becase stopevent set.'
        def terminate(self):
            self.stopevent.set()

    def __init__(self, threadcount = 3):
        self.queue = Queue.Queue(0)
        self.threadcount = threadcount
        self.threads = []
        for i in range(threadcount):
            thread = self.Worker(self.queue)
            thread.setDaemon(True)
            self.threads.append(thread)
        for thread in self.threads: thread.start()
        super(SimpleThreadPool, self).__init__()
    def enqueue(self, function, *args, **kw):
        self.queue.put((function, args, kw))

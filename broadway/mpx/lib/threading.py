"""
Copyright (C) 2001 2002 2003 2005 2010 2011 Cisco Systems

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

from mpx._python import python_threading as _threading

from .thread import getpid
from .thread import gettid

from mpx.lib import exceptions

def msglog():
    from mpx.lib import msglog as msglog_module
    return msglog_module

#
# Import all the public names from Python's threading module.
#
from mpx._python.threading import *

##
# @note More imports done below to avoid conflicts.

##
# @note Mediator threads default to daemonic mode.
class Thread(_threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(),
                 kwargs=None, verbose=None, *vargs, **keywords):
        if kwargs is None:
            kwargs = {}
        _args = (group, target, name, args, kwargs, verbose) + vargs
        _threading.Thread.__init__(self, *_args, **keywords)
        self.__pid = None
        self.__tid = None
        self.setDaemon(1)
        return
    def pid(self):
        return self.__pid
    def tid(self):
        return self.__tid
    def start(self):
        self._run = self.run
        self.run = self._run_wrapper
        _threading.Thread.start(self)
        return
    def _run_wrapper(self):
        self.__pid = getpid()
        self.__tid = gettid()
        try:
            self._run()
        except:
            msglog().exception()
        return

class LocalDict(_threading.local):
    """
        Thread-specific storage type which behaves like a dictionary.
        
        A single LocalDict() instance behaves like a unique dictionary 
        for each thread that uses it.  Each thread's version of the 
        instance is independent, and there is no way for one thread 
        to access another thread's dictionary.
    """
    _initialized = False
    def __init__(self):
        if self._initialized:
            raise TypeError("already initialized")
        self._data = {}
        self._initialized = True
        super(LocalDict, self).__init__()
    def __getitem__(self, *args, **kw):
        return self._data.__getitem__(*args, **kw)
    def __setitem__(self, *args, **kw):
        return self._data.__setitem__(*args, **kw)
    def __iter__(self):
        return self._data.__iter__()
    def __len__(self):
        return self._data.__len__()
    def __contains__(self, *args, **kw):
        return self._data.__contains__(*args, **kw)
    def __delitem__(self, *args, **kw):
        return self._data.__delitem__(*args, **kw)
    def copy(self):
        return self._data.copy()
    def clear(self):
        return self._data.clear()
    def get(self, *args, **kw):
        return self._data.get(*args, **kw)
    def keys(self):
        return self._data.keys()
    def values(self):
        return self._data.values()
    def items(self):
        return self._data.items()
    def setdefault(self, *args, **kw):
        return self._data.setdefault(*args, **kw)
    def iterkeys(self):
        return self._data.iterkeys()
    def itervalues(self):
        return self._data.itervalues()
    def iteritems(self):
        return self._data.iteritems()
    def has_key(self, *args, **kw):
        return self._data.has_key(*args, **kw)
    def pop(self, *args, **kw):
        return self._data.pop(*args, **kw)
    def popitem(self, *args, **kw):
        return self._data.popitem(*args, **kw)
    def update(self, *args, **kw):
        return self._data.update(*args, **kw)

class EKillThread(exceptions.MpxException):
    pass

class ImmortalThread(Thread):
    def __init__(self, group=None, target=None, name=None, args=(),
                 kwargs=None, verbose=None, *vargs, **keywords):
        if kwargs is None:
            kwargs = {}
        _args = (group, target, name, args, kwargs, verbose) + vargs
        if keywords.has_key('reincarnate'):
            self.reincarnate = keywords['reincarnate']
            del(keywords['reincarnate'])
        self._continue_running = 1
        Thread.__init__(self, group, target, name, args, kwargs, verbose,
                        *vargs, **keywords)
        return
    def _run_wrapper(self):
        self._Thread__pid = getpid()
        self._Thread__tid = gettid()
        first_run = 1
        while self._continue_running:
            try:
                if not first_run:
                    self.reincarnate()
                    if not self._continue_running:
                        return
                self._run()
            except EKillThread:
                msglog().exception()
                self._continue_running = 0
            except:
                msglog().exception()
            first_run = 0
        return
    def reincarnate(self):
        pass
    def set_immortal(self, immortal):
        self._continue_running = immortal
        return
    def should_die(self):
        self.set_immortal(0)
        return
    def is_immortal(self):
        return self._continue_running

##
# Provide a platform specific Condition variable with improved performance.
#
from _condition import Condition

##
# Provide a platform specific Semaphore with improved performance.
#
from _semaphore import Semaphore

##
# Provide a platform specific BoundedSemaphore with improved performance.
#
from _bounded_semaphore import BoundedSemaphore

##
# Provide a platform specific Event with improved performance.
#
from _event import Event

class _Unique:
    pass

NOTHING = _Unique()

##
# @todo Consider making the exception a compatible extension of a Python
#       Queue.Full and also adding an MPX equivalent of Queue.Empty.
class QueueFull(exceptions.MpxException):
    pass

##
# @todo Consider making the methods a compatible extension of a Python
#       Queue.Queue() instance.  This would require changing the signature
#       of get and put, as well as implementing qsize(), empty(), full(),
#       put_nowait(item), and get_nowait().
# @todo For some reason get() will exit and return when there is nothing to 
#       return from the queue.  The while loop fixes that.  This needs to be
#       looked into.  It appears to happen whether using our modified or fast
#       conditions, or linux's native condition variable.
class Queue:
    def __init__(self, threshold=0):
        self._threshold = threshold
        self._listeners = []
        self._q = []
        self._underflow = Condition(Lock())
        self._overflow = Condition(Lock())
    def get_threshold(self):
        return self._threshold
    def set_threshold(self, threshold):
        self._threshold = threshold
    def put(self, object, timeout=None):
        self._underflow.acquire()
        if self._threshold and len(self._q) >= self._threshold:
            self._overflow.acquire()
            self._underflow.release()
            self._overflow.wait(timeout)
            self._overflow.release()
            self._underflow.acquire()
            if len(self._q) >= self._threshold:
                self._underflow.release()
                raise QueueFull()
        self._q.append(object)
        self._underflow.notify()
        self._underflow.release()
        for listner in self._listeners:
            listner.notify()
        return
    def get(self, timeout=None):
        original_timeout = timeout
        result = NOTHING
        self._underflow.acquire()
        t_lapsed = 0
        t_start = time.time()
        while not len(self._q):
            if timeout != None:
                timeout = original_timeout - t_lapsed
                if timeout <= 0:
                    break
            self._underflow.wait(timeout)
            t_lapsed = time.time() - t_start
        else:
            result = self._q.pop(0)
        self._overflow.acquire()
        self._overflow.notify()
        self._overflow.release()
        self._underflow.release()
        return result
    def add_listener(self, listener):
        self._listeners.append(listener)

def lookup_by_pid(pid):
    for t in enumerate():
        if hasattr(t, 'pid'):
            if t.pid() == pid:
                return t
    return None

def lookup_by_tid(tid):
    for t in enumerate():
        if hasattr(t, 'tid'):
            if t.tid() == tid:
                return t
    return None

lookup_by_spid = lookup_by_tid
lookup_by_lwp = lookup_by_tid

from mpx import properties
########################################################################
#                        LOCK DEBUGGING HOOKS.
########################################################################
if properties.get_boolean('DEBUG_LOCKS', 0):
    # @fixme Support RLock, Cond, and our Queue.
    from debugging_locks import Lock
from debugging_locks import set_lock_attributes

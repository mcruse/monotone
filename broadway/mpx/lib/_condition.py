"""
Copyright (C) 2002 2003 2004 2010 2011 Cisco Systems

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
# Provide more effecient, possibly platform specific, implementations of
# of the condition variable (Condition).

import sys

from mpx._python import threading as _threading
from mpx._python import thread as _thread
from mpx._python import types as _types
from mpx.lib.scheduler import scheduler

_version = sys.version_info
del sys

_allocate_lock = _thread.allocate_lock

class _ThreadWrapper:
    def __init__(self, thread, id=None):
        self.thread = thread
        self.id = id
    def set_id(self, id):
        self.id = id
    def get_id(self):
        return self.id
    def acquire(self, block=1):
        self.thread.acquire(block)
    def release(self):
        self.thread.release()

class _FastCondition:
    def __init__(self, lock=None):
        self._lock = lock
        if not self._lock:
            self._lock = _threading.Lock()
        self._locks = []
    
    def acquire(self, *args):
        return self._lock.acquire(*args)
    
    def release(self):
        self._lock.release()
    
    def locked(self):
        return self._lock.locked()
    
    def wait(self, timeout=None):
        if not self._lock.locked():
            raise AssertionError('wait called on un-acquire()d lock')
        lock = _ThreadWrapper(_allocate_lock())
        lock.acquire()
        id = None
        if timeout is not None:
            id = scheduler.after(timeout, self._timeout, (lock,))
        lock.set_id(id)
        self._locks.append(lock)
        self.release()
        try:
            lock.acquire()
        finally:
            self.acquire()
    
    def notify(self, n=1):
        if not self._lock.locked():
            raise AssertionError('wait called on un-acquire()d lock')
        release_count = 0
        locks = self._locks
        for lock in locks:
            if lock.get_id():
                scheduler.cancel(lock.get_id())
            if not lock.acquire(0):
                release_count += 1
            lock.release()
            try:
                self._locks.remove(lock)
            except ValueError:
                pass
            if release_count == n:
                return
    
    def _timeout(self, lock):
        self.acquire()
        try:
            if lock.thread.locked():
                lock.release()
            try:
                self._locks.remove(lock)
            except ValueError:
                pass
        finally:
            self.release()
    
    def notifyAll(self):
        self.notify(len(self._locks))

if _version[0:2] == (2, 2):
    _sleep = _threading._sleep
    _allocate_lock = _threading._allocate_lock
    _time = _threading._time
    _currentThread =  _threading.currentThread

    class _ModifiedCondition_2_2:
        def __init__(self, c, max_sleep=0.001):
            for attr in dir(c):
                if not hasattr(self, attr):
                    setattr(self, attr, getattr(c, attr))
            self._c = c
            self._s = max_sleep
        ##
        # Modified from /usr/lib/python2.2/threading.py.
        def __repr__(self):
            return \
                "<ModifiedCondition_2_2(%s, max_sleep=%f, self.__waiters=%d)>"\
                % (self._c._Condition__lock, self._s,
                   len(self._c._Condition__waiters))
        ##
        # Modified from /usr/lib/python2.2/threading.py, support a configurable
        # maximum poll rate instead of a hard-coded .05.
        def wait(self, timeout=None):
            c = self._c
            me = _currentThread()
            assert c._is_owned(), "wait() of un-acquire()d lock"
            waiter = _allocate_lock()
            waiter.acquire()
            c._Condition__waiters.append(waiter)
            saved_state = c._release_save()
            try:    # restore state no matter what (e.g., KeyboardInterrupt)
                if timeout is None:
                    waiter.acquire()
                    if __debug__:
                        c._note("%s.wait(): got it", c)
                else:
                    # Balancing act:  We can't afford a pure busy loop, so we
                    # have to sleep; but if we sleep the whole timeout time,
                    # we'll be unresponsive.  The scheme here sleeps very
                    # little at first, longer as time goes on, but never longer
                    # than 20 times per second (or the timeout time remaining).
                    endtime = _time() + timeout
                    delay = 0.0005 # 500 us -> initial delay of 1 ms
                    while 1:
                        gotit = waiter.acquire(0)
                        if gotit:
                            break
                        remaining = endtime - _time()
                        if remaining <= 0:
                            break
                        delay = min(delay * 2, remaining, self._s)
                        _sleep(delay)
                    if not gotit:
                        if __debug__:
                            c._note("%s.wait(%s): timed out", c, timeout)
                        try:
                            c._Condition__waiters.remove(waiter)
                        except ValueError:
                            pass
                    else:
                        if __debug__:
                            c._note("%s.wait(%s): got it", c, timeout)
            finally:
                c._acquire_restore(saved_state)
    _ModifiedCondition = _ModifiedCondition_2_2
else:
    _ModifiedCondition = _threading._Condition

##
# Returns a modified instance of Python's threading.Condition.
def ModifiedCondition(*args, **kwargs):
    if kwargs.has_key('max_sleep'):
        max_sleep = kwargs['max_sleep']
        del kwargs['max_sleep']
    else:
         max_sleep = .001
    c = _threading.Condition(*args, **kwargs)
    m = _ModifiedCondition(c, max_sleep)
    return m

del _version

##
# Set via platform checks, properties, and god knows what...
from select import poll as _poll
_supports_poll = 0
try:
    _poll()
    _supports_poll = 1
except:
    pass
if _supports_poll:
    Condition = _FastCondition
else:
    Condition = ModifiedCondition

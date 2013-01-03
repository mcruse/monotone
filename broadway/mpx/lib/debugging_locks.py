"""
Copyright (C) 2002 2003 2005 2006 2010 2011 Cisco Systems

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
# Debugging versions of Python locking mechanisms.

import os, time, traceback, sys
    
from moab.linux.lib import uptime

from mpx._python import thread as _thread

# from mpx.lib import msglog
# from mpx.lib.msglog.types import INFO, WARN, ERR

from mpx.lib.exceptions import MpxException
from mpx._python.threading import currentThread
from mpx import properties

# Note: approach picks between two types of debugging locks.
#       Approach #1 throws an exception if a thread tries to reacquire a lock
#                   that it already holds, and also throws an exception if
#                   a thread which isn't the one holding a lock tries to
#                   release it.
#       Approach #2 allows the developer to set a timeout parameter on a lock.
#                   If someone tries to acquire the lock and waits more than
#                   timeout seconds, an exception will be raised.

# REMOVED Approach #3
#       Approach #3 is just like approach #2, except it attempts to acquire
#                   the lock again after dumping the debugging info so that
#                   any previously experienced symptoms (e.g. a lockup) will
#                   hopefully still manifest themselves.

approach = properties.get_int('DEBUG_LOCKS_APPROACH',2)
default_timeout = properties.get_int('DEBUG_LOCKS_TIMEOUT',60*5)

_orig_allocate = _thread.allocate
_orig_allocate_lock = _thread.allocate_lock

class _LockAssertion(MpxException):
    pass
class _ReentrantAcquireAssertion(_LockAssertion):
    pass
class _InternalAssertion(_LockAssertion):
    pass
class _WrongThreadAssertion(_LockAssertion):
    pass
class Lock1:
    locked_list = []
    list_lock = _orig_allocate()
    def __init__(self, lock=None):
        self.locker = []
        if lock is None:
            lock = _orig_allocate()
        self.real_lock = lock
        self.owner = None
    def acquire(self,waitflag=None):
        owner = currentThread()
        if self.owner == owner and waitflag is not 0:
            raise _ReentrantAcquireAssertion('Reentrant lock attempt',
                                             # logtype=msglog.types.DB)
                                             )
        if waitflag is None:
            result = self.real_lock.acquire()
        else:
            result = self.real_lock.acquire(waitflag)
            if not waitflag and not result:
                # We did not acquire the lock and we are in non-blocking
                # mode.
                return result
        self.owner = owner
        # Now add this lock to the list of currently acquired locks.
        self.list_lock.acquire()
        self.locked_list.append(self)
        self.list_lock.release()
        return result
    def acquire_lock(self,waitflag=None):
        return self.acquire(waitflag)
    def locked(self):
        return self.real_lock.locked()
    def locked_lock(self):
        return self.real_lock.locked_lock()
    def release(self):
        if self.owner != currentThread():
            if self.owner is None:
                # Release *should* raise an exception...
                self.real_lock.release()
                # ...but it didn't.
                raise _InternalAssertion(
                    "Debug logic failed to track the lock's state",
                    # logtype=msglog.types.DB)
                    )
            else:
                raise _WrongThreadAssertion(
                    "Attempt to release another thread's lock",
                    # logtype=msglog.types.DB)
                    )
        
        # Now remove this lock to the list of currently acquired locks.
        self.list_lock.acquire()
        if self in self.locked_list:
            self.locked_list.remove(self)
        else:
            self.list_lock.release()
            self.real_lock.release()
            raise _InternalAssertion(
                "Debug logic failed to properly track the lock's state",
                # logtype=msglog.types.DB)
                )
        self.list_lock.release()
        self.owner = None
        self.real_lock.release()
        return
    def release_lock(self):
        return self.release()

class Lock2:
    def __init__(self):
        self.real_lock = _orig_allocate()
        self.locker = None
        self.name = 'Default Lock Name: %s' % id(self)
        self.timeout = default_timeout
    #
    def set_attrs(self, timeout=None, name=None):
        if timeout != None:
            self.timeout = timeout
        if name != None:
            self.name = name
    #
    #def _logMsg(self,  msg):
    #    # msglog.log('Debugging Lock2', type, msg)
    #    print "_logMsg: %r" % (msg,)
    #
    def acquire_lock(self,waitflag=None):
        return self.acquire(waitflag)
    #
    def locked(self):
        return self.real_lock.locked()
    #
    def locked_lock(self):
        return self.real_lock.locked_lock()
    #
    def acquire(self, blocking=1):
        if not blocking:
            return self.real_lock.acquire(blocking)
        # Wait up to timeout seconds to acquire the lock.  If we can't, then
        # raise some hell.
        st_time = uptime.secs()
        while 1:
            result = self.real_lock.acquire(0)
            if result:
                self.locker = currentThread()
                # We got our lock, return
                return result
            cur_time = uptime.secs()
            if cur_time - st_time > self.timeout:
                break
            time.sleep(.1)
        # If we get here, we didn't acquire our lock in time.
        # self._logMsg('Possible deadlock warning!!')
        mstr  = ("Could not acquire lock (%s) within %d seconds!  "
                 "Locker is %s.") % (
            str(self.name), self.timeout, str(self.locker)
            )
        raise _LockAssertion(mstr)
    #
    def release(self):
        return self.real_lock.release()

if approach == 1:
    Lock = Lock1
if approach == 2 or approach == 3:
    Lock = Lock2

def allocate1():
    global _orig_allocate
    return Lock1(_orig_allocate())

def allocate2():
    return Lock2()

def allocate():
    global _orig_allocate
    if approach == 1:
        return Lock(_orig_allocate())
    else:
        return Lock()

def allocate_lock():
    return allocate()

def set_lock_attributes(lock, timeout=None, name=None):
    if hasattr(lock, 'set_attrs'):
        lock.set_attrs(timeout, name)

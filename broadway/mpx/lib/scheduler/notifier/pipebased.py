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
import os
import select
from mpx.lib import msglog
from threading import Lock
from thread import allocate_lock
from moab.linux.lib import uptime

class Condition(object):
    "Pipe-based condition uses poll to mimic build-in Condition"
    MSECSMAX = 0x7FFFFFFF
    def __init__ (self):
        self._lock = Lock()
        self._lockset = set()
        self._poll = select.poll()
        self._readfd, self._writefd = os.pipe()
        self._poll.register(self._readfd, select.POLLIN)
        super(Condition, self).__init__()
    def acquire(self):
        return self._lock.acquire()
    def release(self):
        return self._lock.release()
    def locked(self):
        return self._lock.locked()
    def wait(self, timeout=None):
        assert self._lock.locked(), 'wait called on un-acquire()d lock'
        waitlock = allocate_lock()
        waitlock.acquire()
        self._lockset.add(waitlock)
        self._lock.release()
        try:
            if timeout is None:
                self._waituntil(waitlock)
            else:
                self._waitupto(timeout, waitlock)
        finally:
            self._lock.acquire()
            if waitlock.acquire(0):
                os.read(self._readfd, 1)
            self._lockset.remove(waitlock)
    def _waitupto(self, timeout, waitlock):
        startuptime = uptime.secs()
        while not timeout < 0:
            msecs = min(timeout * 1000, self.MSECSMAX)
            readable = self._pollreadable(msecs)
            if waitlock.locked():
                curuptime = uptime.secs()
                lapsetime = curuptime - startuptime
                timeout = timeout - lapsetime
            else:
                break
        else:
            return False
        return True
    def _waituntil(self, waitlock):
        while waitlock.locked():
            self._pollreadable()
    def _pollreadable(self, timeout = None):
        try:
            return self._poll.poll(timeout)
        except select.error, error:
            msglog.log('broadway', msglog.types.WARN, 
                       'Notifier ignoring %s' % (error,))
        return False
    def notify(self, count=1):
        assert self._lock.locked(), 'notify called on un-acquire()d lock'
        released = 0
        lockset = self._lockset
        for waitlock in lockset:
            if not waitlock.acquire(0):
                released += 1
            waitlock.release()
            if released == count:
                break
        os.write(self._writefd, 'B' * released)
    def notifyAll(self):
        return self.notify(len(self._lockset))

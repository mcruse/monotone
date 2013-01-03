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
import os
import socket
import select
from select import poll as _poll
from select import POLLIN as _POLLIN

from moab.lib import uptime

from mpx import properties

from mpx.lib import msglog
from mpx.lib.thread import allocate_lock
from mpx.lib.threading import Lock
from mpx.lib.threading import gettid

_tmp_dir = properties.get('TEMP_DIR')
##
# Used to truncate the argument passed to select.poll.poll(ms) to
# avoid overflows.
# @fixme Probably should detect on a per-platform bases.
_MAX_MS = 0x7FFFFFFF

class Condition:
    def __init__(self):
        self._lock = Lock()
        self._locks = []
        socket_name = os.path.join(_tmp_dir,
                                   'Scheduler.%d' % gettid())
        while os.path.exists(socket_name):
            try:    os.remove(socket_name)
            except: socket_name += 'x'
        s_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 
                                s_socket.getsockopt(socket.SOL_SOCKET,
                                                    socket.SO_REUSEADDR)|1)
        except Exception, e:
            print 'set reuse failed, %s' % e
        s_socket.bind(socket_name)
        try:
            s_socket.listen(1)
            self.c_connection = socket.socket(socket.AF_UNIX,
                                              socket.SOCK_STREAM)
            self.c_connection.connect(socket_name)
            self.s_connection, addr = s_socket.accept()
            self.s_connection.setblocking(1)
            self._poll = _poll()
            self._poll.register(self.s_connection, _POLLIN)
        finally:
            # Once the connection is established, we can delete the file.
            # It will be remove from its directory, but continue to exist
            # until this process is no longer connected to it.
            os.remove(socket_name)
    def acquire(self):
        self._lock.acquire()
    def release(self):
        self._lock.release()
    def locked(self):
        return self._lock.locked()
    def wait(self, timeout=None):
        if not self._lock.locked():
            raise AssertionError('wait called on un-acquire()d lock')
        lock = allocate_lock()
        lock.acquire()
        self._locks.append(lock)
        self.release()
        ms = None
        try:
            if timeout != None:
                ms = timeout * 1000
            t_start = uptime.secs()
            while timeout == None or timeout >= 0:
                if ms > _MAX_MS:
                    ms = _MAX_MS
                try:
                    readable = self._poll.poll(ms)
                except select.error:
                    msglog.log('broadway',msglog.types.WARN,
                        'Condition ignoring select.error')
                    readable = False
                if readable:
                    if not lock.locked(): break
                else:
                    if timeout == None:
                        continue
                    t_end = uptime.secs()
                    timeout -= t_end - t_start
                    t_start = t_end
                    ms = timeout * 1000
        finally:
            self.acquire()
            if lock.acquire(0):
                self.s_connection.recv(1)
            self._locks.remove(lock)
        return
    def notify(self,n=1):
        if not self._lock.locked():
            raise AssertionError('notify called on un-acquire()d lock')
        release_count = 0
        locks = self._locks
        for lock in locks:
            if not lock.acquire(0):
                release_count += 1
            lock.release()
            if release_count == n:
                break
        self.c_connection.send('B' * release_count)
        
    def notifyAll(self):
        self.notify(len(self._locks))

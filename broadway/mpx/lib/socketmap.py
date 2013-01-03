"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
import asyncore
import os
import socket
import weakref

from errno import EWOULDBLOCK

from mpx import properties

from mpx.lib.exceptions import EInternalError
from mpx.lib.exceptions import EUnreachableCode

from mpx.lib.threading import Lock
from mpx.lib.threading import gettid

TMP_DIR = properties.get('TEMP_DIR')

##
# @note SocketMapNotifier assumes all access is semaphored.  It does not
#       provide it's own locking because that could lead to deadlocks.  All
#       access should be indirect, via the SocketMap.
class SocketMapNotifier(asyncore.dispatcher, object):
    usednames = weakref.WeakValueDictionary()
    classlock = Lock()
    def __unused_socket_name(self, suffix):
        while True:
            socket_name = os.path.join(
                TMP_DIR, 'SocketMapNotifier-%d.%04d' % (gettid(), suffix)
                )
            if not self.usednames.has_key(socket_name):
                return socket_name, suffix
            suffix += 1
        raise EUnreachable()
    def __socket_name(self):
        suffix = 1
        socket_name, suffix = self.__unused_socket_name(suffix)
        while os.path.exists(socket_name):
            try:
                os.remove(socket_name)
            except:
                suffix += 1
                socket_name, suffix = self.__unused_socket_name(suffix)
        self.usednames[socket_name] = self
        return socket_name
    def __setup_sockets(self):
        socket_name = self.__socket_name()
        listen = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        listen.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:
            listen.bind(socket_name)
            listen.listen(1)
            self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.connect(socket_name)
            self.__output, addr = listen.accept()
            self.__output.setblocking(0)
            listen.close()
        finally:
            os.remove(socket_name)
        return
    def __init__(self, map):
        self.__map = map
        self.__output = None
        super(SocketMapNotifier, self).__init__(None, None)
        self.classlock.acquire()
        try: self.__setup_sockets()
        finally: self.classlock.release()
        return
    def wakeup(self):
        try: self.__output.send('B')
        except socket.error,why:
            if why[0] != EWOULDBLOCK:
                raise
        return
    def handle_read(self):
        try:
            while self.recv(1024): pass
        except socket.error,why:
            if why[0] != EWOULDBLOCK:
                raise
        return
    def readable(self): return 1
    def writable(self): return 0
    def handle_connect(self, *args): return
    def add_channel(self, map=None):
        if map is None:
            map = self.__map
        else:
            assert map is self.__map, (
                "SocketMapNotifier should only be used it's assigned map"
                )
        return super(SocketMapNotifier, self).add_channel(self.__map)
    def del_channel(self, map=None):
        if map is None:
            map = self.__map
        else:
            assert map is self.__map, (
                "SocketMapNotifier should only be used it's assigned map"
                )
        return super(SocketMapNotifier, self).del_channel(self.__map)
    def set_socket(self, sock, map=None):
        raise EInternalError(
            "SocketMapNotifier does not support set_socket()."
            )

class ExplicitSocketMap(dict):
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self.__lock = Lock()
        self.__notifier = SocketMapNotifier(self)
        return
    def wakeup(self):
        self.__lock.acquire()
        try:
            self.__notifier.wakeup()
        finally:
            self.__lock.release()
        return

class StubNotifier(object):
    def wakeup(self):
        return

class SocketMap(dict):
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self.__busy = False
        self.__lock = Lock()
        # The StubNotifier is used during the creation of the real
        # SocketMapNotifier().
        self.__notifier = StubNotifier()
        # Creating the SocketMapNotifier will add it to this SocketMap.
        self.__notifier = SocketMapNotifier(self)
        return
    def wakeup(self, force=False):
        self.__lock.acquire()
        force = force or self.__busy
        try:
            if force:
                self.__notifier.wakeup()
        finally:
            self.__lock.release()
        return
    def __delitem__(self,y):
        self.__lock.acquire()
        try:
            result = dict.__delitem__(self,y)
            if self.__busy:
                self.__notifier.wakeup()
            return result
        finally:
            self.__lock.release()
        raise EUnreachable()
    def __setitem__(self,i,y):
        self.__lock.acquire()
        try:
            result = dict.__setitem__(self,i,y)
            if self.__busy:
                self.__notifier.wakeup()
            return result
        finally:
            self.__lock.release()
        raise EUnreachable()
    def __invoke(self, func, *args):
        self.__lock.acquire()
        self.__busy = True
        self.__lock.release()
        try:
            result = apply(func, args)
        finally:
            self.__lock.acquire()
            self.__busy = False
            self.__lock.release()
        return result
    def poll(self, timeout=0.0):
        return self.__invoke(asyncore.poll, timeout, self)
    def poll2(self, timeout=0.0):
        return self.__invoke(asyncore.poll2, timeout, self)
    def poll3(self, timeout=0.0): 
        return self.__invoke(asyncore.poll3, timeout, self)
    def loop(self, timeout=30.0, use_poll=0):
        return self.__invoke(asyncore.loop, timeout, use_poll, self)

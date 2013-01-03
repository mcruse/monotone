"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
import select
import types
from mpx.lib.threading import Lock
from mpx._python.socket import *
from _socket import socket as _OriginalSocket
from mpx.lib.exceptions import ETimeout,EInvalidValue,ENotImplemented

class _Socket:
    def __init__(self,socket,connected=0):
        self._socket = socket
        self._connected = connected
        self._wait_readable = self._select_readable
        self._wait_writable = self._select_writable
        self._blocking = 1
    def setblocking(self,blocking):
        self._socket.setblocking(blocking)
        self._blocking = blocking
    def is_blocking(self):
        return self._blocking
    def bind(self,args):
        return self._socket.bind(args)
    def listen(self,count):
        return self._socket.listen(count)
    def accept(self,timeout=None):
        if timeout is not None:
            if not self._wait_readable(timeout):
                raise ETimeout('Accept timed out.')
        sock,addr = self._socket.accept()
        return _Socket(sock,1),addr
    def connect(self,args,timeout=None):
        if timeout is not None:
            self._socket.setblocking(0)
            try:
                self._non_blocking_connect(args,timeout)
            finally:
                self._socket.setblocking(self._blocking)
        else:
            self._socket.connect(args)
        self._connected = 1
        try:
            poll = select.poll()
            poll.register(self._socket.fileno(),select.POLLIN)
            self._pollin = poll.poll
            self._wait_readable = self._poll_readable
            poll = select.poll()
            poll.register(self._socket.fileno(),select.POLLOUT)
            self._pollout = poll.poll
            self._wait_writable = self._poll_writable
        except:
            self._wait_readable = self._select_readable
            self._wait_writable = self._select_writable
    def send(self,data,timeout=None,flags=0):
        if timeout is not None and self._connected:
            if not self._wait_writable(timeout):
                raise ETimeout('Socket did not become writable')
        return self._socket.send(data,flags)
    def sendall(self,data,timeout=None,flags=0):
        bytes_to_send = len(data)
        while bytes_to_send > 0:
            bytes_sent = self.send(data,timeout,flags)
            bytes_to_send -= bytes_sent
    def recv(self,bufsize,timeout=None,flags=0):
        if timeout is not None and self._connected:
            if not self._wait_readable(timeout):
                raise ETimeout('Socket did not become readable')
        return self._socket.recv(bufsize,flags)
    def fileno(self):
        return self._socket.fileno()
    def close(self):
        result = self._socket.close()
        self._connected = 0
        return result
    def makefile(self,mode='r',bufsize=0):
        if bufsize != 0:
            raise EInvalidValue('bufsize',bufsize,
                                'To ensure safety, '
                                'bufsize must be 0')
        file = self._socket.makefile(mode,0)
        return _SockFile(self,file)
    def _non_blocking_connect(self,args,timeout):
        try:
            self._socket.connect(args)
        except error,why:
            if why[0] != 115:
                raise why
            if not self._wait_writable(timeout):
                raise ETimeout('Connect timed out.')
    def _poll_readable(self,timeout=None):
        if timeout is not None:
            timeout = 1000 * timeout
        return self._pollin(timeout)
    def _poll_writable(self,timeout=None):
        if timeout is not None:
            timeout = 1000 * timeout
        return self._pollout(timeout)
    def _select_readable(self,timeout=None):
        if select.select([self.fileno()],[],[],timeout)[0]:
            return [(self.fileno(),select.POLLIN)]
        return []
    def _select_writable(self,timeout=None):
        if select.select([],[self.fileno()],[],timeout)[1]:
            return [(self.fileno(),select.POLLOUT)]
        return []
    def __getattr__(self,name):
        return getattr(self._socket,name)
class _SafetySocket(_Socket):
    def __init__(self,socket,timeout):
        self._timeout = timeout
        _Socket.__init__(self,socket)
    def recv(self,count,timeout=None,flags=0):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket.recv(self,count,timeout,flags)
    def send(self,data,timeout=None,flags=0):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket.send(self,data,timeout,flags)
    def connect(self,args,timeout=None):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket.connect(self,args,timeout)
    def accept(self,timeout=None):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket.accept(self,timeout)
    def _poll_readable(self,timeout=None):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket._poll_readable(self,timeout)
    def _poll_writable(self,timeout=None):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket._poll_writable(self,timeout)
    def _select_readable(self,timeout=None):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket._select_readable(self,timeout)
    def _select_writable(self,timeout=None):
        if timeout is None or timeout > self._timeout:
            timeout = self._timeout
        return _Socket._select_writable(self,timeout)
class _SockFile:
    def __init__(self,socket,file):
        self._socket = socket
        self._file = file
        self._safety = 0
        if isinstance(socket,_SafetySocket):
            self._safety = 1
        self._buffer = ''
    def read(self,count=None,timeout=None):
        while count is None:
            try:
                data = self._socket.recv(1024,0)
                if data:
                    self._buffer += data
                    continue
            except ETimeout:
                pass
            data = self._buffer
            self._buffer = ''
            return data
        if self._buffer:
            if len(self._buffer) < count:
                if self._socket._wait_readable(0):
                    self._buffer += self._socket.recv(count - len(self._buffer))
            data = self._buffer[0:count]
            self._buffer = self._buffer[count:]
            return data
        return self._socket.recv(count,timeout)
    def write(self,data,timeout=None):
        if self._safety or timeout is not None:
            if not self._socket._wait_writable(timeout):
                raise ETimeout('File did not become writable')
        return self._file.write(data)
    def readline(self,timeout=None):
        data = self._buffer
        self._buffer = ''
        while '\n' not in data:
            previous = len(data)
            try:
                data += self.read(1024,timeout)
            except ETimeout:
                self._buffer = data
                raise
            if len(data) == previous:
                return data
        end = data.index('\n') + 1
        self._buffer = data[end:]
        return data[0:end]
    def readlines(self,sizehint=None,timeout=None):
        raise ENotImplemented(self._file.readlines)
    def xreadlines(self):
        raise ENotImplemented(self._file.xreadlines)
    def seek(self,offset,whence=0):
        raise ENotImplemented(self._file.seek)
    def tell(self):
        raise ENotImplemented(self._file.tell)
    def close(self):
        return self._file.close()
    def fileno(self):
        return self._file.fileno()
    def __getattr___(self,name):
        return getattr(self._file,name)
if type(socket) is types.FunctionType:
    def socket(family,type,proto=0):
        return _socketobject(_Socket(_OriginalSocket(family,type,proto)))
    def safety_socket(family,type,timeout,proto=0):
        return _socketobject(_SafetySocket(timeout,family,type,proto))
else:
    def socket(*args):
        return _Socket(_OriginalSocket(*args))
    def safety_socket(timeout,*args):
        return _SafetySocket(_OriginalSocket(*args),timeout)
try:
    _original_ssl = ssl
except:
    pass
else:
    class SSL:
        def __init__(self,socket,*args):
            if not isinstance(socket,_Socket):
                raise EInvalidValue('socket',socket,
                                    'Must be mpx.lib.socket.socket')
            self._safety = 0
            if isinstance(socket,_SafetySocket):
                self._safety = 1
            self._socket = socket
            self._ssl = _original_ssl(socket._socket,*args)
            self._lock = Lock()
        def read(self,count=None,timeout=None):
            args = (count,)
            if count is None:
                args = ()
            if ((self._safety or timeout is not None) and 
                not self._socket._wait_readable(0)):
                blocking = self._socket.is_blocking()
                self._lock.acquire()
                try:
                    self._socket.setblocking(0)
                    try:
                        return self._ssl.read(*args)
                    except sslerror,why:
                        if why[0] not in (2,11) and blocking:
                            raise why
                finally:
                    self._socket.setblocking(blocking)
                    self._lock.release()
            else:
                return self._ssl.read(*args)
            if (self._socket._connected and not 
                self._socket._wait_readable(timeout)):
                raise ETimeout('Socket did not become readable')
            return self._ssl.read(*args)
        def write(self,data,timeout=None):
            if ((timeout is not None or self._safety) and 
                self._socket._connected):
                if not self._socket._wait_writable(timeout):
                    raise ETimeout('Socket did not become writable')
            self._lock.acquire()
            try:
                return self._ssl.write(data)
            finally:
                self._lock.release()
        def __getattr__(self,name):
            return getattr(self._ssl,name)
    ssl = SSL

            
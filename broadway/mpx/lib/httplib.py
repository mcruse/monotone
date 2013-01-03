"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx._python.httplib import *
from mpx._python import httplib as _httplib
from mpx.lib.exceptions import ENotImplemented
from mpx.lib import socket

class HTTPConnection(_httplib.HTTPConnection):
    def __init__(self,host,port=None,timeout=None):
        self._timeout = timeout
        _httplib.HTTPConnection.__init__(self,host,port)
    def set_timeout(self,timeout):
        if self.sock is not None:
            raise ENotImplemented('set_timeout','Can only call set_timeout'
                                  ' before a connection has been made')
        self._timeout = timeout
    def connect(self,timeout=None):
        if timeout is None:
            timeout = self._timeout
        self._timeout = timeout
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if self._timeout is None:
                    self.sock = socket.socket(af, socktype, proto)
                else:
                    self.sock = socket.safety_socket(self._timeout, 
                                                     af, socktype, proto)
                if self.debuglevel > 0:
                    print "connect: (%s, %s)" % (self.host, self.port)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.debuglevel > 0:
                    print 'connect fail:', (self.host, self.port)
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg
class HTTPSConnection(_httplib.HTTPSConnection):
    def __init__(self,host,port=None,timeout=None,**x509):
        _httplib.HTTPSConnection.__init__(self,host,port,**x509)
        self._timeout = timeout
    def connect(self,timeout=None):
        if timeout is None:
            timeout = self._timeout
        self._timeout = timeout
        if self._timeout is None:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        else:
            sock = socket.safety_socket(self._timeout,
                                        socket.AF_INET,
                                        socket.SOCK_STREAM)
        sock.connect((self.host,self.port))
        realsock = sock
        if hasattr(sock,'_sock'):
            realsock = sock._sock
        ssl = socket.ssl(realsock,self.key_file,self.cert_file)
        self.sock = FakeSocket(sock,ssl)
class HTTP(_httplib.HTTP):
    _connection_class = HTTPConnection
    def __init__(self,host='',port=None,timeout=None):
        _httplib.HTTP.__init__(self,host,port)
        self._conn.set_timeout(timeout)
if hasattr(_httplib, 'HTTPS'):
    class HTTPS(_httplib.HTTPS):
        _connection_class = HTTPSConnection
        def __init__(self,host='',port=None,timeout=None,**x509):
            _httplib.HTTPS.__init__(self,host,port,**x509)
            self._conn.set_timeout(timeout)


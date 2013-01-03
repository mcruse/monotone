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
from mpx._python.ftplib import *
from mpx._python import ftplib as _ftplib
from mpx.lib import socket

class FTP(_ftplib.FTP):
    def __init__(self,host='',user='',passwd='',acct='',timeout=None):
        self._timeout = timeout
        _ftplib.FTP.__init__(self,host,user,passwd,acct)
    def connect(self,host='',port=0,timeout=None):
        if timeout is None:
            timeout = self._timeout
        self._timeout = timeout
        if host: self.host = host
        if port: self.port = port
        self.passiveserver = 0
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if timeout is None:
                    self.sock = socket.socket(af, socktype, proto)
                else:
                    self.sock = socket.safety_socket(timeout,af,
                                                     socktype,proto)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg
        self.af = af
        self.file = self.sock.makefile('rb')
        self.welcome = self.getresp()
        return self.welcome
    def makeport(self):
        timeout = self._timeout
        msg = "getaddrinfo returns an empty list"
        sock = None
        for res in socket.getaddrinfo(None, 0, self.af, 
                                      socket.SOCK_STREAM, 0, 
                                      socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                if timeout is None:
                    sock = socket.socket(af, socktype, proto)
                else:
                    sock = socket.safety_socket(timeout,af,
                                                socktype,proto)
                sock.bind(sa)
            except socket.error, msg:
                if sock:
                    sock.close()
                sock = None
                continue
            break
        if not sock:
            raise socket.error, msg
        sock.listen(1)
        port = sock.getsockname()[1] # Get proper port
        host = self.sock.getsockname()[0] # Get proper host
        if self.af == socket.AF_INET:
            resp = self.sendport(host, port)
        else:
            resp = self.sendeprt(host, port)
        return sock
    def ntransfercmd(self, cmd, rest=None):
        timeout = self._timeout
        size = None
        if self.passiveserver:
            host, port = self.makepasv()
            tp = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
            af, socktype, proto, canon, sa = tp
            if timeout is None:
                conn = socket.socket(af, socktype, proto)
            else:
                conn = socket.safety_socket(timeout,af,socktype,proto)
            conn.connect(sa)
            if rest is not None:
                self.sendcmd("REST %s" % rest)
            resp = self.sendcmd(cmd)
            if resp[0] != '1':
                raise error_reply, resp
        else:
            sock = self.makeport()
            if rest is not None:
                self.sendcmd("REST %s" % rest)
            resp = self.sendcmd(cmd)
            if resp[0] != '1':
                raise error_reply, resp
            conn, sockaddr = sock.accept()
        if resp[:3] == '150':
            # this is conditional in case we received a 125
            size = parse150(resp)
        return conn, size


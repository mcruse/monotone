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
from mpx._python.smtplib import *
from mpx._python import smtplib as _smtplib
from mpx.lib import socket

class SMTP(_smtplib.SMTP):
    def __init__(self,host='',port=0,timeout=None):
        self._timeout = timeout
        _smtplib.SMTP.__init__(self,host,port)
    def connect(self,host='localhost',port=0,timeout=None):
        if timeout is None:
            timeout = self._timeout
        self._timeout = timeout
        if not port and (host.find(':') == host.rfind(':')):
            i = host.rfind(':')
            if i >= 0:
                host, port = host[:i], host[i+1:]
                try: port = int(port)
                except ValueError:
                    raise socket.error, "nonnumeric port"
        if not port: port = SMTP_PORT
        if self.debuglevel > 0: print 'connect:', (host, port)
        msg = "getaddrinfo returns an empty list"
        self.sock = None
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if timeout is None:
                    self.sock = socket.socket(af, socktype, proto)
                else:
                    self.sock = socket.safety_socket(timeout,af,
                                                     socktype,proto)
                if self.debuglevel > 0: print 'connect:', (host, port)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.debuglevel > 0: print 'connect fail:', (host, port)
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg
        (code, msg) = self.getreply()
        if self.debuglevel > 0: print "connect:", msg
        return (code, msg)

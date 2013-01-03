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
import asyncore
from mpx.lib import msglog

class PipeTrigger(asyncore.file_dispatcher):
    "Trigger FD event to interrupt select/poll"
    def __init__ (self, socketmap):
        self._closed = False
        self.socketmap = socketmap
        self._readfd, self._writefd = os.pipe()
        asyncore.file_dispatcher.__init__(self,self._readfd, self.socketmap)
    def close(self):
        if not self._closed:
            self._closed = 1
            self.del_channel()
            os.close(self._readfd)
            self._readfd = None
            os.close(self._writefd)
            self._writefd = None
    def __repr__ (self):
        return '<select-trigger (pipe) at %x>' % id(self)
    def readable (self):
        return 1
    def writable (self):
        return 0
    def handle_connect (self):
        pass
    def handle_close(self):
        self.close()
    def trigger_event(self, callback = None):
        os.write(self._writefd, 'x')
    def handle_read (self):
        try:
            self.recv(8192)
        except socket.error:
            return

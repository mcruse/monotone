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

from errno import EWOULDBLOCK

from moab.lib import process
from mpx import properties
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.threading import gettid

class SocketTrigger(asyncore.dispatcher):
    TMPDIR = properties.get('TEMP_DIR')    
    def __init__(self, socketmap):
        asyncore.dispatcher.__init__(self, None, socketmap)
        self._connecting = False
        self._setup_socketname()
        self._setup_listener_socket()
        try:
            self._setup_input_socket()
            self._setup_output_socket()
        finally:
            self._cleanup_setup()
    def readable(self):
        return 1
    def writable(self):
        return 0
    def handle_read(self):
        try:
            self.socket.recv(8192)
        except socket.error:
            return
    def trigger_event(self):
        self._output_socket.send('X')
    def set_debugmode(self):
        assert self.writable is not self._debug_writable
        self._writable = self.writable
        self._readable = self.readable
        self._handle_read = self.handle_read
        self._trigger_event = self.trigger_event
        self.writable = self._debug_writable
        self.readable = self._debug_readable
        self.handle_read = self._debug_handle_read
        self.trigger_event = self._debug_trigger_event
    def clear_debugmode(self):
        assert self.writable is self._debug_writable
        self.writable = self._writable
        self.readable = self._readable
        self.handle_read = self._handle_read
        self.trigger_event = self._trigger_event
    def _setup_socketname(self):
        socket_name = os.path.join(TMPDIR,'SocketTrigger.%d' % gettid())
        while os.path.exists(socket_name):
            try:
                os.remove(socket_name)
            except:
                socket_name += 'x'
        self._socket_name = socket_name
    def _setup_listener_socket(self):
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(self._socket_name)
        listener.listen(1)
        self._listener_socket = listener
    def _setup_input_socket(self):
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._connecting = True
        self.connect(self._socket_name)
    def _setup_output_socket(self):
        assert self._connecting
        output, addr = self._listener_socket.accept()
        output.setblocking(0)
        self._connecting = False
        self._output_socket = output
    def _cleanup_setup(self):
        self._listener_socket.close()
        self._listener_socket = None
        os.remove(self._socket_name)
    def _debug_writable(self):
        writable = self._writable()
        print 'EventChannel.writable() -> %d' % writable
        return writable
    def _debug_readable(self):
        readable = self._readable()
        print 'EventChannel.readable() -> %d' % readable
        return readable
    def _debug_handle_read(self):
        print 'EventChannel.handle_read()'
        return self._handle_read()
    def _debug_trigger_event(self):
        print 'EventChannel.trigger_event()'
        return self._trigger_event()

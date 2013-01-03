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
import struct
from socket import SOL_SOCKET
from socket import SO_LINGER
from mpx.lib import msglog
from mpx.lib.messaging.tools import debug
from mpx.service.messaging.transport import Connection
from mpx.service.messaging.transport.server.builders import MessageBuilder

class ByteBuffer(object):
    def __init__(self):
        self.buffers = []
        self.bytecount = 0
    def write(self, bytes):
        self.buffers.append(bytes)
        self.bytecount += len(bytes)
    def read(self):
        buffers = self.buffers
        self.buffers = []
        self.bytecount = 0
        return "".join(buffers)
    def __len__(self):
        return self.bytecount
    def __nonzero__(self):
        return bool(self.buffers)

class IncomingChannel(Connection):
    """
        Transport connection which consumes messages from 
        message channel, wraps them in producer Envelopes, 
        and enqueues them for asynchronous sending using 
        driven by asyncore.
    """
    LINGER = struct.pack("ii",0,0)
    @debug
    def __init__(self, dispatcher, connection):
        super(IncomingChannel, self).__init__(dispatcher.monitor)
        self.dispatcher = dispatcher
        self.setup_connection(connection)
        self.buffer = ByteBuffer()
        self.setup_builder()
    @debug
    def setup_connection(self, connection):
        self.connection = connection
        self.set_socket(self.connection, self.monitor)
        # Ensure that we never block waiting for a socket to close.
        self.connection.setsockopt(SOL_SOCKET, SO_LINGER, self.LINGER)
    @debug
    def setup_builder(self):
        self.reset_builder()
        self.set_terminator(self.current_builder.get_terminator())
    @debug
    def reset_builder(self):
        self.current_builder = MessageBuilder()
    @debug
    def collect_incoming_data(self, bytes):
        self.buffer.write(bytes)
    @debug
    def found_terminator(self):
        self.current_builder.write(self.buffer.read())
        if self.current_builder.iscomplete():
            self.dispatcher.dispatch(self.current_builder.message())
            self.reset_builder()
        self.set_terminator(self.current_builder.get_terminator())
    @debug
    def connect(self, address):
        raise TypeError("connect() called on server channel")
    @debug
    def handle_connect(self):
        pass
    @debug
    def handle_close(self):
        super(IncomingChannel, self).handle_close()
        self.dispatcher.closed(self)
    @debug
    def push(self, message):
        raise TypeError("push() called on server channel")
    @debug
    def push_with_producer(self, envelope):
        raise TypeError("push_with_producer() called on server channel")
    @debug
    def writable(self):
        return False
    @debug
    def readable(self):
        return True
    @debug
    def send(self, data):
        raise TypeError("send() called on server channel")
    @debug
    def recv(self, bufsize):
        return super(IncomingChannel, self).recv(bufsize)
    @debug
    def handle_expt(self):
        message =  "%s handling exceptoinal event: closing."
        msglog.log("broadway", message % self, msglog.types.WARN)
        self.close()








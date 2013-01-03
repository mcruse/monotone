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
import socket
import traceback
from mpx.lib import msglog
from mpx.lib.messaging.tools import debug
from mpx.service.messaging.transport import Connection
from mpx.service.messaging.transport.client.producers import MessageProducer

class OutgoingChannel(Connection):
    """
        Transport connection which consumes messages from 
        message channel, wraps them in producer Envelopes, 
        and enqueues them for asynchronous sending using 
        driven by asyncore.
    """
    @debug
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        super(OutgoingChannel, self).__init__(self.dispatcher.monitor)
    @debug
    def connect(self, address):
        self.dispatcher.connecting(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        return super(OutgoingChannel, self).connect(address)
    @debug
    def handle_connect(self):
        self.dispatcher.connected(self)
    def handle_close(self):
        self.dispatcher.closing(self)
        self.close()
    @debug
    def push(self, message):
        self.push_with_producer(MessageProducer(message))
    @debug
    def push_with_producer(self, envelope):
        self.producer_fifo.push(envelope)
    @debug
    def writable(self):
        writable = super(OutgoingChannel, self).writable()
        if not writable:
            self.dispatcher.idling(self)
        else:
            self.dispatcher.working(self)
        return writable
    @debug
    def send(self, data):
        return super(OutgoingChannel, self).send(data)
    @debug
    def recv(self, bufsize):
        return super(OutgoingChannel, self).recv(bufsize)
    @debug
    def close(self):
        super(OutgoingChannel, self).close()
        self.dispatcher.closed(self)
    def handle_expt(self):
        message =  "%s handling exceptoinal event: closing."
        msglog.log("broadway", message % self, msglog.types.WARN)
        self.close()

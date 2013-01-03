"""
Copyright (C) 2010 2011 Cisco Systems

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
from threading import RLock
from threading import Event
from mpx.lib import msglog
from asyncore import dispatcher
from mpx.lib.messaging.tools import debug
from mpx.service.messaging.transport.server.connection import IncomingChannel

class Dispatcher(object, dispatcher):
    """
        Dispatch messages to transport connections.
    """
    @debug
    def __init__(self, messaging, port=5151, interface=""):
        self.port = port
        self.channels = set()
        self.synclock = RLock()
        self.dispatching = Event()
        self.interface = interface
        self.messaging = messaging
        self.monitor = self.messaging.monitor
        dispatcher.__init__(self, map=self.monitor)
    @debug
    def is_dispatching(self):
        return self.dispatching.isSet()
    @debug
    def start_dispatching(self):
        if not self.accepting:
            self.setup_connection()
        self.dispatching.set()
        self.messaging.monitor.check_channels()
    @debug
    def stop_dispatching(self):
        self.close_channels()
        self.dispatching.clear()
        self.messaging.monitor.check_channels()
    @debug
    def readable(self):
        return self.is_dispatching()
    @debug
    def setup_connection(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((self.interface, self.port))
        self.listen(5)
    @debug
    def handle_accept(self):
        try:
            connection,address = self.accept()
        except socket.error:
            # linux: on rare occasions we get a bogus socket back from
            # accept.  socketmodule.c:makesockaddr complains that the
            # address family is unknown.  We don't want the whole server
            # to shut down because of this.
            msglog.exception(prefix="handled")
        except TypeError:
            # unpack non-sequence.  this can happen when a read event
            # fires on a listening socket, but when we call accept()
            # we get EWOULDBLOCK, so dispatcher.accept() returns None.
            # Seen on FreeBSD3.
            msglog.exception(prefix="handled")
        self.create_channel(connection)
    @debug
    def create_channel(self, connection):
        channel = IncomingChannel(self, connection)
        self.synclock.acquire()
        try:
            self.channels.add(channel)
        finally:
            self.synclock.release()
        return channel
    @debug
    def dispatch(self, message):
        self.messaging.route(message)
    @debug
    def closed(self, channel):
        self.synclock.acquire()
        try:
            self.channels.remove(channel)
        finally:
            self.synclock.release()
    @debug
    def close_channels(self):
        while self.channels:
            channel = self.channels.pop()
            try:
                channel.close()
            except:
                msglog.exception(prefix="handled")



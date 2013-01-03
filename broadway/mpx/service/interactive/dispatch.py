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
from __future__ import with_statement
import socket
from threading import Event
from threading import RLock
from mpx.lib import msglog
from mpx.service.interactive.tools import Dispatcher
from mpx.service.interactive.channel import ConsoleChannel

class ConsoleDispatcher(Dispatcher):
    def __init__(self, service):
        self.service = service
        self.channels = set()
        self.synclock = RLock()
        self.dispatching = Event()
        super(ConsoleDispatcher, self).__init__(self.monitor)
    def is_dispatching(self):
        return self.dispatching.isSet()
    def start_dispatching(self):
        with self.synclock:
            if not self.accepting:
                self.setup_connection()
            self.dispatching.set()
        self.monitor.check_channels()
    def stop_dispatching(self):
        with self.synclock:
            self.close_channels()
            self.dispatching.clear()
        self.monitor.check_channels()
    def readable(self):
        return self.is_dispatching()
    def setup_connection(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((self.service.interface, self.service.port))
        self.listen(5)
    def handle_accept(self):
        self.debugout("%s accepting connection.", self)
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
        self.create_channel(connection, address)
    def create_channel(self, connection, address):
        channel = ConsoleChannel(self, connection)
        with self.synclock:
            self.channels.add(channel)
        self.debugout('Created new console channel %s', channel)
        return channel
    def handle_error(self):
        message = "%s closing due to error that follows."
        self.service.logoutput(message, self, type=msglog.types.WARN)
        msglog.exception(prefix="handled")
        self.close_channels()
        self.close()
    def close_channels(self):
        self.debugout('%s closing down channels', self)
        while self.channels:
            channel = self.channels.pop()
            try:
                channel.close()
            except:
                msglog.exception(prefix="handled")
        return len(self.channels)
    def getmonitor(self):
        return self.service.monitor
    monitor = property(getmonitor)
    def debugout(self, message, *args, **kw):
        kw.setdefault("level", 1)
        kw.setdefault("type", msglog.types.DB)
        self.service.logoutput(message, *args, **kw)
    def __str__(self):
        status = [type(self).__name__]
        status.append("(%s:%d)" % (self.service.interface, self.service.port))
        return ' '.join(status)
    def __repr__(self):
        description = "%s %d channels" % (self, len(self.channels))
        return '<%s at %#x>' % (description, id(self))

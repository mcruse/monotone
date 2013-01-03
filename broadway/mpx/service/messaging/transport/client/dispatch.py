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
from threading import RLock
from itertools import cycle
from mpx.lib import msglog
from mpx.service.messaging.transport.client import connection

class Dispatcher(object):
    """
        Dispatch messages to transport connections.
    """
    def __init__(self, host, maxcons=3):
        self.host = host
        self.idlecons = set()
        self.synclock = RLock()
        self.maxcons = maxcons
        self.channels = set()
        self.iterchannels = None
        super(Dispatcher, self).__init__()
    def start_dispatching(self):
        self.monitor = self.host.monitor
        self.messages = self.host.getchannel("outgoing-messages")
        self.address = (self.host.getname(), self.host.getport())
        self.messages.attach(self)
    def stop_dispatching(self):
        self.messages.detach(self)
        self.close_channels()
    def handle_message(self, message):
        return self.dispatch(message)
    def dispatch(self, message):
        self.synclock.acquire()
        try:
            if self.idlecons:
                channel = self.idlecons.pop()
            elif len(self.channels) < self.maxcons:
                channel = self.create_channel()
            else:
                channel = self.iterchannels.next()
        finally:
            self.synclock.release()
        channel.push(message)
        self.monitor.check_channels()
    def create_channel(self):
        self.synclock.acquire()
        try:
            channel = connection.OutgoingChannel(self)
            self.channels.add(channel)
            self.iterchannels = cycle(self.channels)
        finally:
            self.synclock.release()
        channel.connect(self.host.getlocation())
        return channel
    def connecting(self, channel):
        pass
    def connected(self, channel):
        pass
    def idling(self, channel):
        self.synclock.acquire()
        try:
            self.idlecons.add(channel)
        finally:
            self.synclock.release()
    def working(self, channel):
        self.synclock.acquire()
        try:
            self.idlecons.discard(channel)
        finally:
            self.synclock.release()
    def closing(self, channel):
        self.synclock.acquire()
        try:
            self.idlecons.discard(channel)
            self.channels.remove(channel)
            self.iterchannels = cycle(self.channels)
        finally:
            self.synclock.release()
    def closed(self, channel):
        pass
    def close_channels(self):
        while self.channels:
            channel = self.channels.pop()
            try:
                channel.close()
            except:
                msglog.exception(prefix="handled")



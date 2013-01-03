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
import threading
from mpx.lib.deferred import Deferred
from mpx.componentry import implements
from mpx.lib.messaging.channel import MessageChannel
from mpx.lib.messaging.channel.interfaces import IMessageTopic
from mpx.lib.messaging.channel.interfaces import IMessageChannel

class MessageTopic(MessageChannel):
    implements(IMessageTopic)
    def __init__(self, *args, **kw):
        self.deferreds = set()
        self.subscribers = set()
        self.synclock = threading.RLock()        
        super(MessageTopic, self).__init__(*args, **kw)
    def subscribe(self, channel):
        with self.synclock:
            self.subscribers.add(channel)
    def unsubscribe(self, channel):
        with self.synclock:
            self.subscribers.remove(channel)
    def attach(self, listener):
        channel = IMessageChannel(listener)
        self.subscribe(channel)
    def detach(self, listener):
        channel = IMessageChannel(listener)
        self.unsubscribe(channel)
    def publish(self, message):
        return self.send(message)
    def receive(self, blocking=True, timeout=None):
        with self.synclock:
            deferred = Deferred()
            self.deferreds.add(deferred)
        return deferred.getvalue(blocking, timeout)
    def notify(self):
        with self.synclock:
            message = super(MessageTopic, self).receive(False)
            subscribers = set(self.subscribers)
            deferreds = self.deferreds.copy()
            self.deferreds.clear()
        for subscriber in subscribers:
            subscriber.send(message.copy())
        for deferred in deferreds:
            # Use try/except for timing problems to handle 
            # empty blocked-consumer list without exception.
            deferred.succeeded(message)







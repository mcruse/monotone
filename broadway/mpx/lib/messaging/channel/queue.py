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
from mpx.componentry import implements
from mpx.lib.messaging.channel import MessageChannel
from mpx.lib.messaging.channel.interfaces import IMessageChannel
from mpx.lib.messaging.channel.interfaces import IMessageListener
from mpx.lib.messaging.channel.interfaces import IMessageQueue

class MessageQueue(MessageChannel):
    implements(IMessageQueue)
    def __init__(self, *args, **kw):
        self.iterindex = 0
        self.listeners = list()
        super(MessageQueue, self).__init__(*args, **kw)
    def attach(self, listener):
        self.listeners.append(listener)
        self.notify()
    def detach(self, listener):
        self.listeners.remove(listener)    
    def subscribe(self, channel):
        listener = IMessageListener(channel)
        self.attach(listener)
    def unsubscribe(self, channel):
        # Adapters provide __eq__ so comparison will work.
        listener = IMessageListener(channel)
        self.detach(listener)
    def iterlisteners(self):
        while self.listeners:
            try:
                listener = self.listeners[self.iterindex]
            except IndexError:
                self.iterindex = 0
            else:
                yield listener
                self.iterindex += 1
    def notify(self):
        for listener in self.iterlisteners():
            message = self.receive(False)
            if not message:
                break
            listener.handle_message(message)

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
"""
    Package defines the base messaging channel interfaces 
    and types.  There are type basic types of channels.  
    
    Queue type channels enqueue incoming messages until each 
    message has been consumed.  Messages consumed from a 
    queue-type channel are guaranteed to be consumed by no 
    more than one consumer.  Although multiple consumers may 
    consume messages from a single queue-type channel, each 
    will consume unique messages.  In this way, multiple 
    consumers attached to a single queue-type channel, are 
    considered "competing consumers."  
    
    Publish-subscribe type channels send incoming messages 
    to zero or more consumers.  Each consumer attached to a 
    publish-subscribe type channel will receive each messages 
    sent to that channel.  Publish-subscribe type channels do 
    not enqueue messages, and it is therefore possible that 
    messages sent to a publish-subscribe type channel not be 
    consumed by any consumers, if none are registered at the 
    time the message is sent.  Publish-subscribe type channels 
    are also referred to as Topics, or Topic Channels.  The 
    topic terminology is the terminology employed by this 
    package. 
"""
from __future__ import with_statement
import urlparse
import threading
from Queue import Queue
from Queue import Empty
from mpx.componentry import implements
from mpx.lib.messaging.tools import Counter
from mpx.lib.messaging.channel import adapters
from mpx.lib.messaging.channel.interfaces import IDestination
from mpx.lib.messaging.channel.interfaces import IMessageChannel
Undefined = object()

class MessageChannel(object):
    """
        Abstract base-class of all message channel types.
        
        Provides functionality and attribute initialization 
        and management common to all channel types.  Considered 
        "abstract" because implementation of notify() raises 
        exception and must be overridden, and because there 
        is no API method defined for getting messages out of the 
        channel.
    """
    implements(IMessageChannel)
    def __init__(self, name, host=None):
        self.name = name
        self.host = host
        self.added = Counter()
        self.removed = Counter()
        self.messages = Queue()
        super(MessageChannel, self).__init__()
    def getname(self):
        return self.name
    def geturl(self):
        return "/".join([self.host.geturl(), self.getname()])
    def send(self, message):
        self.messages.put(message)
        self.added.increment()
        self.notify()
    def receive(self, blocking=True, timeout=None):
        try:
            message = self.messages.get(blocking, timeout)
        except Empty:
            message = None
        else:
            self.removed.increment()
        return message
    def full(self):
        return self.messages.full()
    def empty(self):
        return self.messages.empty()
    def attach(self, listener):
        raise TypeError("notify() must be overridden")
    def detach(self, listener):
        raise TypeError("notify() must be overridden")
    def subscribe(self, channel):
        raise TypeError("notify() must be overridden")
    def unsubscribe(self, channel):
        raise TypeError("notify() must be overridden")
    def notify(self):
        raise TypeError("notify() must be overridden")
    def __str__(self):
        descriptors = ["%s('%s')" % (type(self).__name__, self.getname())]
        descriptors.append('+%d' % self.added.get())
        descriptors.append('-%d' % self.removed.get())
        return " ".join(descriptors)
    def __repr__(self):
        return '<%s at %#x>' % (self, id(self))

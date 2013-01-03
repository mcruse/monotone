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
from mpx.lib.messaging.channel.queue import MessageQueue
from mpx.lib.messaging.channel.topic import MessageTopic
from mpx.lib.messaging.channel.interfaces import IMessageListener

class Listener(object):
    implements(IMessageListener)
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        super(Listener, self).__init__()
    def handle_message(self, message):
        print '%s handling %s' % (self, message)
        self.callback(self, message)
    def __str__(self):
        return "Listener(%s)" % self.name


def showcallback(subscriber, message):
    print '%s received %s' % (subscriber, message)


class Message(str):
    def copy(self):
        return self
    def __str__(self):
        return "Message('%s')" % super(Message, self).__str__()


message1 = Message(1)
message2 = Message(2)
message3 = Message(3)
message4 = Message(4)

topichandler1 = Listener("Topic Listener 1", showcallback)
topichandler2 = Listener("Topic Listener 2", showcallback)
queuehandler1 = Listener("Queue Listener 1", showcallback)
queuehandler2 = Listener("Queue Listener 2", showcallback)


topic = MessageTopic()
topic.send(message1)
print topic.messages.queue

topic.attach(topichandler1)
topic.send(message2)
print topic.messages.queue

topic.attach(topichandler2)
topic.send(message3)
print topic.messages.queue

queue = MessageQueue("test-channel")
queue.send(message1)
print queue.messages.queue

queue.send(message2)
print queue.messages.queue

print queue.receive()
queue.attach(queuehandler1)
print queue.messages.queue

queue.send(message1)
queue.send(message2)
queue.send(message3)
queue.send(message4)
print queue.messages.queue

queue.attach(queuehandler2)

queue.send(message1)
queue.send(message2)
queue.send(message3)
queue.send(message4)


queue.detach(queuehandler1)
queue.send(message1)
queue.send(message2)
queue.send(message3)
queue.send(message4)


 
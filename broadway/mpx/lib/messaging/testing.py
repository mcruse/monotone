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
import time
from mpx.lib.messaging.tools import Address

tstart = time.time()
for i in xrange(1000):
    address = Address.fromurl(url)
    name = address.name()
    hostname = address.hostname()


tstop = time.time()
print "Took %0.3f seconds to parse %d URLs" % (tstop - tstart, i)
# Took 1.174 seconds to parse 999 URLs


import time
from Queue import Queue
Thing = object()

queue = Queue()
tstart = time.time()
for i in xrange(1000):
    queue.put(Thing)
    thing = queue.get()


tstop = time.time()
print "Took %0.3f seconds put/get %d things" % (tstop - tstart, i)
# Took 1.052 seconds put/get 999 things


import time
from Queue import Queue
Thing = object()

queues = [Queue() for i in range(2)]
tstart = time.time()
for i in xrange(1000):
    queues[0].put(Thing)
    for x in range(1, len(queues)):
        thing = queues[x - 1].get()
        queues[x].put(thing)


tstop = time.time()
print "Took %0.3f seconds put/get %d things" % (tstop - tstart, i)



import time
from Queue import Queue
Thing = object()

queues = [Queue() for i in range(10)]
tstart = time.time()
for i in xrange(1000):
    queues[0].put(Thing)
    for x in range(1, len(queues)):
        thing = queues[x - 1].get()
        queues[x].put(thing)


tstop = time.time()
print "Took %0.3f seconds put/get %d things" % (tstop - tstart, i)
# Took 9.897 seconds put/get 999 things


import time
from mpx.lib.message.types import Message
from mpx.lib.messaging.channel.queue import MessageQueue
Thing = Message()
Thing.setheader("DEST", "//urchin/node-commands")
channel = MessageQueue("Name")

tstart = time.time()
for i in xrange(1000):
    channel.send(Thing)
    thing = channel.receive()


tstop = time.time()
print "Took %0.3f seconds send/receive %d messages" % (tstop - tstart, i)
# Took 1.052 seconds put/get 999 things



import time
from mpx.lib.message.data import SimpleMessage
from mpx.lib.messaging.channel.queue import MessageQueue
Thing = SimpleMessage("Data")
Thing.setheader("DEST", "//urchin/node-commands")

tstart = time.time()
thing = Thing.copy()
for i in xrange(1, 1000):
    thing = thing.copy()


tstop = time.time()
print "Took %0.3f seconds copy %d messages" % (tstop - tstart, i)
# Took 3.815 seconds copy 999 messages


import time
from mpx.lib.node.message import NodeCommand
Thing = NodeCommand("//urchin/interfaces/relay1", "set", (1,))
Thing.setheader("DEST", "//urchin/node-commands")

tstart = time.time()
thing = Thing.copy()
for i in xrange(1, 1000):
    thing = thing.copy()


tstop = time.time()
print "Took %0.3f seconds copy %d messages" % (tstop - tstart, i)
# Took 3.976 seconds copy 999 messages




import time
from mpx.lib.message.data import SimpleMessage
from mpx.lib.messaging.channel.queue import MessageQueue

class Connector(object):
    def __init__(self, incoming, outgoing):
        self.incoming = incoming
        self.outgoing = outgoing
        super(Connector, self).__init__()
    def start(self):
        self.incoming.attach(self)
    def stop(self):
        self.incoming.detach(self)
    def handle_message(self, message):
        self.outgoing.send(message)


Thing = SimpleMessage("Data")
incoming = MessageQueue("incoming")
outgoing = MessageQueue("outgoing")
pairs = [(incoming, outgoing)]
connectors = [Connector(channels[0], channels[1]) for channels in pairs]
for connector in connectors:
    connector.start()


head = pairs[0][0]
tail = pairs[-1][1]

thing = Thing
tstart = time.time()
for i in xrange(1, 1000):
    head.send(thing)
    thing = tail.receive()


tstop = time.time()
print "Took %0.3f seconds to route %d messages" % (tstop - tstart, i)
# Took 3.693 seconds to route 999 messages



import time
from mpx.lib.message.data import SimpleMessage
from mpx.lib.messaging.channel.queue import MessageQueue

class Connector(object):
    def __init__(self, incoming, outgoing):
        self.incoming = incoming
        self.outgoing = outgoing
        super(Connector, self).__init__()
    def start(self):
        self.incoming.attach(self)
    def stop(self):
        self.incoming.detach(self)
    def handle_message(self, message):
        self.outgoing.send(message)


Thing = SimpleMessage("Data")
pairs = []
incoming = MessageQueue("")
for i in range(10):
    outgoing = MessageQueue("")
    pairs.append((incoming, outgoing))
    incoming = outgoing


connectors = [Connector(channels[0], channels[1]) for channels in pairs]
for connector in connectors:
    connector.start()


head = pairs[0][0]
tail = pairs[-1][1]

thing = Thing
tstart = time.time()
for i in xrange(1, 1000):
    head.send(thing)
    thing = tail.receive()


tstop = time.time()
print "Took %0.3f seconds to route %d messages" % (tstop - tstart, i)

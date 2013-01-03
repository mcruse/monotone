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
localname = "urchin"
remotename = "beggar"

remotename = "urchin"
localname = "beggar"

remotename = "urchin"
localname = "hobo"

remotename = "hobo"
localname = "urchin"



import time
import threading
from mpx.lib.node import message
from mpx.lib.node import endpoint
from mpx.lib.node import facade
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.service.messaging import manager
from mpx.service.messaging import host
from mpx.service.messaging import command
from mpx.service.messaging import request
from mpx.lib.messaging.channel.queue import MessageQueue
from mpx.lib.messaging.routers.network import LocationRouter
from mpx.lib.messaging.routers.network import HostnameRouter
from mpx.lib.messaging.routers.datatype import TypeRouter
from mpx.lib.messaging.routers.datatype import ContentTypeRouter
from mpx.lib.message.request import Request
from mpx.lib.message.data import SimpleMessage

def callback(message):
    print "Callback(%s):\n%s\n" % (message, message.serialize())


def errback(message):
    print "Errback(%s):\n%s\n" % (message, message.serialize())


rna = as_node('/services/network/rna')
rna.enabled = True
rna.start()

messaging = manager.MessagingService()
messaging.configure({"name": "messaging", "parent": "/services"})
localhost = host.LocalHost()
localhost.configure({"name": localname, "parent": messaging})
remotehost = host.RemoteHost()
remotehost.configure({"name": remotename, "parent": messaging})
messaging.start()

requests = messaging.get_destination("//%s/requests" % localname)
responses = messaging.get_destination("//%s/responses" % localname)
dead_letters = messaging.get_destination("//%s/dead-letters" % localname)
command_requests = messaging.get_destination("//%s/node-commands" % localname)

command_service = command.CommandService(messaging)
command_service.configure({'name':'Command Service', 
                           'parent': '/services/messaging'})
command_service.start()

request_service = request.RequestService(messaging)
request_service.configure({'name':'Request Service', 
                           'parent': '/services/messaging'})
request_service.start()

nodeurl = "/interfaces/relay1"
nodemsg = message.NodeMessage(nodeurl)
localcmd = message.NodeCommand(nodeurl, "invoke", ("get",))
localcmd.setheader("DEST", command_requests.geturl())
localreq = Request(localcmd, DEST="//%s/node-commands" % localname)
remotereq = localreq.copy()
remotereq.setheader("DEST", "//%s/node-commands" % remotename)

# Local
request_service.send_request(localreq).getvalue(timeout=10).message.data
# Remote
request_service.send_request(remotereq).getvalue(timeout=20).message.data

# Local
deferreds = []
tstart = time.time()
for i in xrange(1000):
    deferreds.append(request_service.send_request(localreq.copy()))


tmiddle = time.time()
for deferred in deferreds:
    if deferred.getvalue(timeout=20).message.data != 0:
        print "Got bad value!"


tend = time.time()
print "Took %0.3f seconds to send %d requests" % (tmiddle - tstart, i)
print "Took %0.3f seconds to get %d responses" % (tend - tmiddle, i)
print "Took %0.3f seconds to complete %d gets" % (tend - tstart, i)


rna1 = as_node('mpx://%s:5150/interfaces/relay1' % localname)
tstart = time.time()
for i in xrange(1000):
    if rna1.get() != 0:
        print "Got bad value!"


tend = time.time()
print "Took %0.3f seconds to complete %d gets" % (tend - tstart, i)


# Remote
deferreds = []
tstart = time.time()
for i in xrange(1000):
    deferreds.append(request_service.send_request(remotereq.copy()))


tmiddle = time.time()
for deferred in deferreds:
    if deferred.getvalue(timeout=20).message.data != 0:
        print "Got bad value!"


tend = time.time()
print "Took %0.3f seconds to send %d requests" % (tmiddle - tstart, i)
print "Took %0.3f seconds to get %d responses" % (tend - tmiddle, i)
print "Took %0.3f seconds to complete %d gets" % (tend - tstart, i)


rna1 = as_node('mpx://%s:5150/interfaces/relay1' % remotename)
tstart = time.time()
for i in xrange(1000):
    if rna1.get() != 0:
        print "Got bad value!"


tend = time.time()
print "Took %0.3f seconds to complete %d gets" % (tend - tstart, i)





from mpx.lib.messaging import tools
from mpx.lib.message.types import Message
from mpx.lib.message.data import PickleMessage
tools.Debug = True

Message.parse = tools.debug(Message.parse)
Message.parse_head = tools.debug(Message.parse_head)
Message.parse_body = tools.debug(Message.parse_body)
Message.serialize = tools.debug(Message.serialize)
Message.serialize_head = tools.debug(Message.serialize_head)
Message.serialize_body = tools.debug(Message.serialize_body)

PickleMessage.__init__ = tools.debug(PickleMessage.__init__)
PickleMessage.setvalue = tools.debug(PickleMessage.setvalue)
PickleMessage.getvalue = tools.debug(PickleMessage.getvalue)













deferred = request_service.send_request(localreq)
deferred.register(callback, errback)

request_service.make_request(localcmd).getvalue(timeout=10).data

deferred = request_service.make_request(localcmd)
deferred.register(callback, errback)



nodeurl = "/services/time/local"
localcmd = message.NodeCommand(nodeurl, "invoke", ("configuration",))
localcmd.setheader("DEST", command_requests.geturl())
localreq = Request(localcmd, DEST="//%s/node-commands" % localname)

# Asynchronous
request_service.send_request(localreq).getvalue(timeout=10).message.data
deferred = request_service.send_request(localreq)
deferred.register(callback, errback)


# Remote
remotereq = localreq.copy()
remotereq.setheader("DEST", "//%s/node-commands" % remotename)
request_service.send_request(remotereq).getvalue(timeout=20).message.data












####
# Use node end-points to transparently invoke messaging system.
# Local uses
# Asynchronous
def callback(*args):
    print "callback%s" % (args,)

def errback(*args):
    print "errback%s" % (args,)

nodeurl = "/interfaces/relay1"
nodeproxy = endpoint.NodeMessenger("//urchin" + nodeurl)

deferred = nodeproxy.get("name")
deferred.register(callback, errback)

deferred = nodeproxy.call("get")
deferred.register(callback, errback)

deferred = nodeproxy.call("set", 1)
deferred.register(callback, errback)

deferred = nodeproxy.call("get")
deferred.register(callback, errback)

# Using deferred to get result synchronously.
nodeproxy.call("set", 0).getvalue(timeout=10)
nodeproxy.call("get").getvalue(timeout=10)

# Synchronous
nodeproxy = endpoint.SyncNodeMessenger("//urchin" + nodeurl)
nodeproxy.get("name")
nodeproxy.call("get")
nodeproxy.call("set", 1)
nodeproxy.call("get")



####
# Use node facades to perform all messaging transparently.
# Local uses
# Asynchronous
def callback(*args):
    print "callback%s" % (args,)

def errback(*args):
    print "errback%s" % (args,)

nodefacade = facade.as_node_facade("//urchin" + nodeurl, True)
deferred = nodefacade.getattr("name")
deferred.register(callback, errback)

deferred = nodefacade.get()
deferred.register(callback, errback)

deferred = nodefacade.set(0)
deferred.register(callback, errback)

deferred = nodefacade.get()
deferred.register(callback, errback)

# Synchronous
nodefacade = facade.as_node_facade("//urchin" + nodeurl)
nodefacade.getattr("name")
nodefacade.get()
nodefacade.set(1)
nodefacade.get()


nodefacade = facade.as_node_facade("//urchin" + nodeurl, True)
deferreds = []
value = nodefacade.get().getvalue()
tstart = time.time()
for i in xrange(1000):
    deferreds.append(nodefacade.set(value))
    deferreds.append(nodefacade.get())
    value = int(not value)

values = []
for deferred in deferreds:
    values.append(deferred.getvalue(timeout=20))

tend = time.time()
print 'Took %0.3f seconds to set/get %d times on %s.' % (tend - tstart, i, nodefacade)


for nodefacade in (facade.as_node_facade("//urchin" + nodeurl), 
                   as_node("mpx://localhost:5150/interfaces/relay1")):
    tstart = time.time()
    for i in xrange(100):
        value = nodefacade.get()
        nodefacade.set(int(not value))
    
    
    tend = time.time()
    print 'Took %0.3f seconds to set/get %d times on %s.' % (tend - tstart, i, nodefacade)



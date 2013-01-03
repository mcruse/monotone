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
import threading
from mpx.lib.node import message
from mpx.lib.node import endpoint
from mpx.lib.node import facade
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.service.network.messaging import command
from mpx.service.network.messaging import request
from mpx.lib.messaging.channel.queue import MessageQueue
from mpx.lib.messaging.routers.network import LocationRouter
from mpx.lib.messaging.routers.network import HostnameRouter
from mpx.lib.messaging.routers.datatype import TypeRouter
from mpx.lib.messaging.routers.datatype import ContentTypeRouter
from mpx.lib.messaging.message.messages import SimpleData
from mpx.service.network.messaging.service import Messaging
from mpx.service.network.messaging.envelope import Envelope
from mpx.service.network.messaging.dispatcher import ServerDispatch
from mpx.service.network.messaging.dispatcher import ClientDispatch

def send(request, count):
    tstart = time.time()
    for i in range(count):
        requests.send(request)
    tend = time.time()
    print 'Sent %d requests in %f seconds' % (count, tend - tstart)


def recv(count):
    tstart = time.time()
    for i in range(count):
        response = service_responses.receive(timeout=20)
        if not response:
            raise Exception("Failed after %d messages" % i)
        #print response.message.data
    tend = time.time()
    print 'Received %d requests in %f seconds' % (count, tend - tstart)


def timed_get(node, count):
    tstart = time.time()
    for i in range(count):
        value = node.get()
    tend = time.time()
    print 'Performed %d gets in %f seconds' % (count, tend - tstart)


def callback(message):
    print "Callback(%s):\n%s\n" % (message, message.serialize())


def errback(message):
    print "Errback(%s):\n%s\n" % (message, message.serialize())


rna = as_node('/services/network/rna')
rna.enabled = True
rna.start()

messaging = Messaging("urchin")
messaging.configure({'name': 'messaging', 'parent': '/services'})
messaging.start()

incoming = messaging.get_destination("//urchin/incoming")
outgoing = messaging.get_destination("//urchin/outgoing")
requests = messaging.get_destination("//urchin/requests")
responses = messaging.get_destination("//urchin/responses")
dead_letters = messaging.get_destination("//urchin/dead-letters")
service_requests = messaging.get_destination("//urchin/service-requests")
service_responses = messaging.get_destination("//urchin/service-responses")
command_requests = messaging.get_destination("//urchin/node-commands")

command_service = command.CommandService(command_requests, responses)
command_service.configure({'name':'Command Service', 
                           'parent': '/services/messaging'})
command_service.start()

request_service = request.RequestService(requests, service_responses, dead_letters)
request_service.configure({'name':'Request Service', 
                           'parent': '/services/messaging'})
request_service.start()

incoming_router = TypeRouter(incoming, dead_letters)
incoming_router.addroute(request.Request.typespec(), requests)
incoming_router.addroute(request.Response.typespec(), responses)
incoming_router.start_routing()

request_locations = LocationRouter("urchin", requests, 
                                   service_requests, outgoing)
request_locations.start_routing()

response_locations = LocationRouter("urchin", responses, 
                                    service_responses, outgoing)
response_locations.start_routing()

services = ContentTypeRouter(service_requests, dead_letters)
services.addroute(message.NodeCommand.typespec(), command_requests)
services.start_routing()

client = ClientDispatch(outgoing, port=5151)
client.start_dispatching()

server = ServerDispatch(incoming, port=5151)
server.start_dispatching()




#######
# Use messaging to run commands via the Request Service.

# Local request testing.
nodeurl = "/interfaces/relay1"
nodemsg = message.NodeMessage(nodeurl)
localcmd = message.NodeCommand(nodeurl, "invoke", ("get",))
localreq = request.Request(localcmd, DEST="//urchin/command-requests")

# Asynchronous
deferred = request_service.make_request(localcmd)
deferred.register(callback, errback)

deferred = request_service.send_request(localreq.copy())
deferred.register(callback, errback)

# Synchronous
callback(request_service.make_request(localcmd).getvalue(timeout=10))
callback(request_service.send_request(localreq).getvalue(timeout=10))

# Remote request testing.
nodeurl = "/interfaces/relay1"
nodemsg = message.NodeMessage(nodeurl)
remotecmd = message.NodeCommand(nodeurl, "invoke", ("get",), DEST="//beggar")
remotereq = request.Request(remotecmd, DEST="//beggar")

# Asynchronous
deferred = request_service.make_request(remotecmd.copy())
deferred.register(callback, errback)

deferred = request_service.send_request(remotereq.copy())
deferred.register(callback, errback)

# Synchronous
callback(request_service.make_request(remotecmd.copy()).getvalue(timeout=10))
callback(request_service.send_request(remotereq.copy()).getvalue(timeout=10))

####
# Use node end-points to transparently invoke messaging system.
# Local uses
# Asynchronous
def callback(*args):
    print "callback%s" % (args,)

def errback(*args):
    print "errback%s" % (args,)

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

# Remote uses
# Asynchronous
nodeproxy = endpoint.NodeMessenger("//beggar" + nodeurl)

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
nodeproxy = endpoint.SyncNodeMessenger("//beggar" + nodeurl)

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

deferred = nodefacade.set(1)
deferred.register(callback, errback)

deferred = nodefacade.get()
deferred.register(callback, errback)

# Synchronous
nodefacade = facade.as_node_facade("//urchin" + nodeurl)
nodefacade.getattr("name")
nodefacade.get()
nodefacade.set(1)
nodefacade.get()

# Remote uses
# Asynchronous
nodefacade = facade.as_node_facade("//beggar" + nodeurl, True)

deferred = nodefacade.getattr("name")
deferred.register(callback, errback)

deferred = nodefacade.get()
deferred.register(callback, errback)

deferred = nodefacade.set(1)
deferred.register(callback, errback)

deferred = nodefacade.get()
deferred.register(callback, errback)

# Synchronous
nodefacade = facade.as_node_facade("//beggar" + nodeurl)
nodefacade.getattr("name")
nodefacade.get()
nodefacade.set(1)
nodefacade.get()



# Performance synchronous
nodefacade = facade.as_node_facade("//beggar" + nodeurl)

##############
# Issue 500 node command requests.
tstart = time.time()
deferreds = []
for i in range(500):
    value = nodefacade.get()


tend = time.time()
print "Issuing %d commands took: %0.3f seconds" % (i, tend - tstart)

# Performance asynchronous
nodefacade = facade.as_node_facade("//beggar" + nodeurl, True)

##############
# Issue 500 node command requests.
tstart = time.time()
deferreds = []
for i in range(1000):
    deferred = nodefacade.get()
    deferreds.append(deferred)


# Wait on for completion of all deferreds.
while deferreds:
    deferred = deferreds.pop()
    result = deferred.getvalue(timeout=20)


tend = time.time()
print "Issuing %d commands took: %0.3f seconds" % (i, tend - tstart)


























nodeurl = as_node('/interfaces/relay1')
nodemsg = message.NodeMessage('/interfaces/relay1')
nodecmd = message.NodeCommand('/interfaces/relay1', "invoke", ("get",), DEST="//urchin")
nodecmd.setheader("DEST", "//urchin")

cmdrequest = request.Request(nodecmd)
cmdrequest.setheader("DEST", "//urchin")
cmdrequest.setheader("REPLY-TO", "//urchin")

# Asynchronous versions
deferred = request_service.make_request(nodecmd)
deferred.register(callback, errback)

deferred = request_service.send_request(cmdrequest)
deferred.register(callback, errback)

# Synchronous versions
callback(request_service.make_request(nodecmd).getvalue(timeout=10))
callback(request_service.send_request(cmdrequest).getvalue(timeout=10))

incoming.send(cmdrequest)
print service_responses.receive(timeout=10).message.data

cmdrequest = request.Request(nodecmd)
cmdrequest.setheader("DEST", "//beggar")
cmdrequest.setheader("REPLY-TO", "//urchin")

tsend1 = threading.Thread(target=send, args=(cmdrequest, 1000))
tsend1.start()
trecv1 = threading.Thread(target=recv, args=(1000,))
trecv1.start()

rnanode = as_node("mpx://beggar/interfaces/relay1")
tget = threading.Thread(target=timed_get, args=(rnanode, 1000))
tget.start()




# Beggar
import time
import threading
from mpx.lib.node import message
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.service.network.messaging import command
from mpx.service.network.messaging import request
from mpx.lib.messaging.channel.queue import MessageQueue
from mpx.lib.messaging.routers.network import LocationRouter
from mpx.lib.messaging.routers.network import HostnameRouter
from mpx.lib.messaging.routers.datatype import TypeRouter
from mpx.lib.messaging.routers.datatype import ContentTypeRouter
from mpx.lib.messaging.message.messages import SimpleData
from mpx.service.network.messaging.service import Messaging
from mpx.service.network.messaging.envelope import Envelope
from mpx.service.network.messaging.dispatcher import ServerDispatch
from mpx.service.network.messaging.dispatcher import ClientDispatch

class FixedRouter(object):
    def __init__(self, incoming, outgoing):
        self.incoming = incoming
        self.outgoing = outgoing
    def start_routing(self):
        self.incoming.attach(self)
    def stop_routing(self):
        self.incoming.detach(self)
    def handle_message(self, message):
        self.outgoing.send(message)

def send(request, count):
    tstart = time.time()
    for i in range(count):
        requests.send(request)
    tend = time.time()
    print 'Sent %d requests in %f seconds' % (count, tend - tstart)


def recv(count):
    tstart = time.time()
    for i in range(count):
        response = service_responses.receive(timeout=20)
        if not response:
            raise Exception("Failed after %d messages" % i)
        #print response.message.data
    tend = time.time()
    print 'Received %d requests in %f seconds' % (count, tend - tstart)


def timed_get(node, count):
    tstart = time.time()
    for i in range(count):
        value = node.get()
    tend = time.time()
    print 'Performed %d gets in %f seconds' % (count, tend - tstart)


def callback(message):
    print "Callback(%s):\n%s\n" % (message, message.serialize())


def errback(message):
    print "Errback(%s):\n%s\n" % (message, message.serialize())


rna = as_node('/services/network/rna')
rna.enabled = True
rna.start()

messaging = Messaging()
messaging.configure({'name': 'messaging', 'parent': '/services'})

incoming = MessageQueue("//beggar/incoming", messaging)
outgoing = MessageQueue("//beggar/outgoing", messaging)
requests = MessageQueue("//beggar/requests", messaging)
responses = MessageQueue("//beggar/responses", messaging)
dead_letters = MessageQueue("//beggar/dead-letters", messaging)
service_requests = MessageQueue("//beggar/service-requests", messaging)
service_responses = MessageQueue("//beggar/service-responses", messaging)
command_requests = MessageQueue("//beggar/node-commands", messaging)

command_service = command.CommandService(command_requests, responses)
command_service.configure({'name':'Command Service', 
                           'parent': '/services/messaging'})

request_service = request.RequestService(requests, service_responses, dead_letters)
request_service.configure({'name':'Request Service', 
                           'parent': '/services/messaging'})
messaging.start()

incoming_router = TypeRouter(incoming, dead_letters)
incoming_router.addroute(request.Request.typespec(), requests)
incoming_router.addroute(request.Response.typespec(), responses)
incoming_router.start_routing()

request_locations = LocationRouter("beggar", requests, 
                                   service_requests, outgoing)
request_locations.start_routing()

response_locations = LocationRouter("beggar", responses, 
                                    service_responses, outgoing)
response_locations.start_routing()

services = ContentTypeRouter(service_requests, dead_letters)
services.addroute(message.NodeCommand.typespec(), command_requests)
services.start_routing()

client = ClientDispatch(outgoing, port=5151)
client.start_dispatching()

server = ServerDispatch(incoming, port=5151)
server.start_dispatching()

#######
# Use messaging to run commands via the Request Service.

# Local request testing.
nodeurl = "/interfaces/relay1"
nodemsg = message.NodeMessage(nodeurl)
localcmd = message.NodeCommand(nodeurl, "invoke", ("get",))
localcmd.setheader("DEST", "//beggar")
localreq = request.Request(localcmd)
localreq.setheader("DEST", "//beggar")

# Asynchronous
deferred = request_service.make_request(localcmd)
deferred.register(callback, errback)

deferred = request_service.send_request(localreq)
deferred.register(callback, errback)

# Synchronous
callback(request_service.make_request(localcmd).getvalue(timeout=10))
callback(request_service.send_request(localreq).getvalue(timeout=10))

# Remote request testing.
nodeurl = "/interfaces/relay1"
nodemsg = message.NodeMessage(nodeurl)
remotecmd = message.NodeCommand(nodeurl, "invoke", ("get",))
remotecmd.setheader("DEST", "//urchin")
remotereq = request.Request(remotecmd)
remotereq.setheader("DEST", "//urchin")

# Asynchronous
deferred = request_service.make_request(remotecmd.copy())
deferred.register(callback, errback)

# Synchronous
callback(request_service.make_request(remotecmd.copy()).getvalue(timeout=10))
callback(request_service.send_request(remotereq.copy()).getvalue(timeout=10))



##############
# Issue 500 node command requests.
tstart = time.time()
deferreds = []
for i in range(500):
    deferred = request_service.make_request(remotecmd.copy())
    deferreds.append(deferred)


# Wait on for completion of all deferreds.
while deferreds:
    deferred = deferreds.pop()
    result = deferred.getvalue(timeout=20)
    print 'Got %s' % result, 


tend = time.time()
print "Issuing %d commands took: %0.3f seconds" % (i, tend - tstart)
















nodeurl = "/interfaces/relay1"
nodemsg = message.NodeMessage(nodeurl)
nodecmd = message.NodeCommand(nodeurl, "invoke", ("get",))

cmdrequest = request.Request(nodecmd)
cmdrequest.setheader("DEST", "//beggar")
cmdrequest.setheader("REPLY-TO", "//beggar")
incoming.send(cmdrequest)
print service_responses.receive(timeout=10).message.data

send(cmdrequest, 1)
recv(1)

cmdrequest = request.Request(nodecmd)
cmdrequest.setheader("DEST", "//urchin")
cmdrequest.setheader("REPLY-TO", "//beggar")

incoming.send(cmdrequest)
print service_responses.receive(timeout=10).message.data

send(cmdrequest, 1)
recv(1)

tsend1 = threading.Thread(target=send, args=(cmdrequest, 1000))
tsend1.start()
trecv1 = threading.Thread(target=recv, args=(1000,))
trecv1.start()


rnanode = as_node("mpx://urchin/interfaces/relay1")
tget = threading.Thread(target=timed_get, args=(rnanode, 1000))
tget.start()

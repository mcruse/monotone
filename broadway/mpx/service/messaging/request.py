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
from uuid import uuid4
from threading import Thread
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.deferred import Deferred
from mpx.lib.node import CompositeNode
from mpx.lib.message.request import Request

def unwrap_response(response):
    return response.getvalue()

class RequestService(Thread, CompositeNode):
    """
        Manage request-reply transactions on behalf of 
        requestor.
        
        Initialized with two channels:
            - requests - 
            channel to which service will send Request 
            Message instances on behalf of caller.
            
            - responses - 
            channel from which service will pull Response 
            Message instances.
            
        Callers invoke 'make_request' method, passing in request 
        content message.  Service will create Request Message 
        wrapper for passed in content, setting the request message's 
        reply-to destination to be the responses channel.
        
        Callers are then given a Deferred instance, which they may 
        use to register arbitrary callbacks to be invoked once the 
        Request Service receives the response.
        
        Note that each Request Service instance creates its own 
        Deferred instance lookup map.  While it is possible to 
        use multiple Request Service instances in order to create 
        and process requests in parallel, each instance must have 
        its own unique response channel.  Otherwise the incoming 
        responses messages may not be associated with the correct 
        Request service, as each would act as a competing consumer 
        on the same response channel.  Instead, parallel processing 
        is achieved by creating multiple Request Services which share 
        the same request channel, but have unique response channels.
    """
    def __init__(self, messaging=None):
        self.timeout = 5
        self.deferreds = {}
        self.responses = None
        self.deadletters = None
        self.messaging = messaging
        super(RequestService, self).__init__()
    def start(self):
        if not self.isDaemon():
            self.setDaemon(True)
        if self.messaging is None:
            self.messaging = as_node("/services/messaging")
        self.responses = self.messaging.get_destination("/responses")
        self.deadletters = self.messaging.get_destination("/dead-letters")
        CompositeNode.start(self)
        Thread.start(self)
    def run(self):
        while self.is_running():
            try:
                response = self.responses.receive(timeout=self.timeout)
                if response is not None:
                    self.handle_response(response)
            except:
                msglog.exception()
    def handle_response(self, response):
        corid = response.getheader("CORID", None)
        try:
            deferred = self.deferreds.pop(corid)
        except KeyError:
            self.deadletters.send(response)
        else:
            responsetype = response.getheader("STATUS", "SUCCESS")
            if responsetype == "FAILURE":
                deferred.failed(response)
            else:
                deferred.succeeded(response)
    def make_request(self, message):
        """
            Make and send request containing message.
            
            Passed in message's destination is used to set 
            the destination of the outgoing request.
            
            A Deferred instance is returned immediately, which 
            can then be used to wait on the response, or to 
            register a call-back instead.
            
            Value returned via deferred will be the inner 
            message of the response.
        """
        request = Request(message)
        deferred = self.send_request(request)
        deferred.register(unwrap_response)
        return deferred
    def send_request(self, request):
        """
            Send request message.
            
            A Deferred instance is returned immediately, which 
            can then be used to wait on the response, or to 
            register a call-back instead.
            
            Value returned via deferred will be the response 
            message itself.
        """
        deferred = Deferred()
        self.deferreds[request.getheader("CORID")] = deferred
        request.setheader("REPLY-TO", self.responses.geturl())
        self.messaging.route(request)
        return deferred


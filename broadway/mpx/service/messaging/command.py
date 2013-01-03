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
from threading import Thread
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import CompositeNode
from mpx.lib.proxy.types import Proxy
from mpx.lib.message.data import PickleMessage
Undefined = object()

class CommandService(Thread, CompositeNode):
    """
        Handle incoming command messages and produced responses.
        
        Initialized with two channels:
        - commands - 
        Channel from which command messages are pulled to be executed.
        
        - responses - 
        Channel to which response messages will be send following 
        command execution.
    """
    def __init__(self, messaging=None):
        self.timeout = 5
        self.commands = None
        self.messaging = messaging
        super(CommandService, self).__init__()
    def start(self):
        if not self.isDaemon():
            self.setDaemon(True)
        if self.messaging is None:
            self.messaging = as_node("/services/messaging")
        self.commands = self.messaging.get_destination("/node-commands")
        CompositeNode.start(self)
        Thread.start(self)
    def run(self):
        while self.is_running():
            try:
                request = self.commands.receive(timeout=self.timeout)
                if request is not None:
                    self.handle_request(request)
            except:
                msglog.exception()
    def handle_request(self, request):
        result = PickleMessage()
        command = request.message
        proxy = Proxy(command.getnode())
        operation = getattr(proxy, command.command)
        try:
            value = operation(*command.arguments, **command.keywords)
        except Exception, error:
            result.seterror(error)
        else:
            result.setresult(value)
        self.messaging.route(request.create_response(result))

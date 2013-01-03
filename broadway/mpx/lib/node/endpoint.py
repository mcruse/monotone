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
from mpx.lib.node import as_node
from mpx.lib.url import ParsedURL
from mpx.lib.node.message import NodeMessage
from mpx.lib.node.message import NodeCommand
from mpx.lib.proxy.interfaces import IProxy
from mpx.lib.proxy.interfaces import IAsyncProxy
Undefined = object()

def unwrap_data(message):
    return message.data

class NodeMessenger(object):
    implements(IProxy)
    def __init__(self, nodeurl):
        self.nodeurl = nodeurl
        self.nodeaddr = ParsedURL.fromstring(nodeurl)
        self.request_service = as_node("/services/messaging/Request Service")
        super(NodeMessenger, self).__init__()
    def get(self, name, default=Undefined):
        arguments = [name]
        if default is not Undefined:
            arguments.append(default)
        return self.make_command("get", *arguments)
    def set(self, name, value):
        return self.make_command("set", name, value)
    def call(self, name, *args, **kw):
        arguments = (name,) + args
        return self.make_command("call", *arguments, **kw)
    def invoke(self, name, args=(), kw=()):
        kw = dict(kw)
        return self.call(name, *args, **kw)
    def make_command(self, command, *args, **kw):
        address = "//%s/node-commands" % self.nodeaddr.hostname
        command = NodeCommand(self.nodeurl, command, args, kw, DEST=address)
        deferred = self.request_service.make_request(command)
        deferred.register(unwrap_data)
        return deferred
    def __str__(self):
        return "%s('%s')" % (type(self).__name__, self.nodeurl)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

class SyncNodeMessenger(NodeMessenger):
    def make_command(self, *args, **kw):
        deferred = super(SyncNodeMessenger, self).make_command(*args, **kw)
        return deferred.getvalue()

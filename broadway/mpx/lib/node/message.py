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
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.proxy.types import Proxy
from mpx.lib.message.types import Message
from mpx.lib.message.data import DataMessage

class NodeMessage(Message):
    TYPENAME = "NODE"
    def __init__(self, nodeurl="", **headers):
        self.nodeurl = nodeurl
        super(NodeMessage, self).__init__(**headers)
    def serialize_body(self):
        return self.nodeurl
    def parse_body(self, body):
        self.nodeurl = body
    def copy(self):
        return type(self)(self.nodeurl, **self.headers)
    def equals(self, other):
        return (type(self) is type(other)) and (self.nodeurl == other.nodeurl)
    def getnode(self):
        return as_node(self.nodeurl)

class NodeCommand(NodeMessage):
    TYPENAME = "COMMAND"
    def __init__(self, nodeurl="", command="", args=(), kw=(), **headers):
        super(NodeCommand, self).__init__(nodeurl, **headers)
        self.command = command
        self.arguments = args
        self.keywords = dict(kw)
    def serialize_body(self):
        nodeurl = super(NodeCommand, self).serialize_body()
        state = (nodeurl, self.command, self.arguments, self.keywords)
        return repr(state)
    def parse_body(self, body):
        state = eval(body)
        nodeurl, self.command, self.arguments, self.keywords = state
        super(NodeCommand, self).parse_body(nodeurl)
    def copy(self):
        initargs = (self.nodeurl, self.command, self.arguments, self.keywords)
        return type(self)(*initargs, **self.headers)
    def equals(self, other):
        return (super(NodeCommand, self).equals(other) and 
                (self.command, self.arguments, self.keywords) == 
                (other.command, other.arguments, other.keywords))

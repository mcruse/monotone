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
from mpx.lib.node import CompositeNode
from mpx.lib.messaging.tools import Undefined
from mpx.lib.messaging.channel.queue import MessageQueue
from mpx.service.messaging.transport.client import dispatch

class MessageHost(CompositeNode):
    """
        Manages collection of channels for a particular 
        host.  
        
        Instances are used to represent both local and 
        remote hosts.
    """
    def __init__(self):
        self.channels = {}
        super(MessageHost, self).__init__()
    def start(self):
        self.messaging.addhost(self)
        super(MessageHost, self).start()
    def stop(self):
        self.messaging.pophost(self.getname())
        super(MessageHost, self).stop()
    def addchannel(self, channel):
        self.channels[channel.getname()] = channel
    def popchannel(self, name):
        return self.channels.pop(name)
    def getchannel(self, name, default=Undefined):
        channel = self.channels.get(name, default)
        if channel is Undefined:
            raise KeyError("no such channel: %s" % name)
        return channel
    def haschannel(self, name):
        try:
            channel = self.getchannel(name)
        except KeyError:
            return False
        else:
            return True
    def getaddress(self):
        return self.getname()
    def getport(self):
        return 5151
    def getname(self):
        return self.name
    def geturl(self):
        return "//%s" % self.getname()
    def getlocation(self):
        return ((self.getaddress(), self.getport()))
    def dispatch(self, message):
        raise TypeError()
    def get_messaging(self):
        return self.parent
    messaging = property(get_messaging)

class LocalHost(MessageHost):
    """
        Unique messaging host type used for local 
        message channel management.
    """
    NAMES = set(("requests", "responses", "dead-letters", "node-commands"))
    def start(self):
        for name in self.NAMES:
            if not self.haschannel(name):
                print "creating %r" % name
                self.addchannel(MessageQueue(name, self))
        self.requests = self.getchannel("requests")
        self.responses = self.getchannel("responses")
        self.deadletters = self.getchannel("dead-letters")
        self.nodecommands = self.getchannel("node-commands")
        super(LocalHost, self).start()

class RemoteHost(MessageHost):
    """
        Unique messaging host type used for remote 
        message channel management.
        
        Remote host creates and manages transport channels 
        used to send messages to remote destinations. 
    """
    def __init__(self):
        self.dispatcher = None
        self.outgoing = Undefined
        super(RemoteHost, self).__init__()
    def start(self):
        if not self.haschannel("outgoing-messages"):
            self.addchannel(MessageQueue("outgoing-messages", self))
        self.outgoing = self.getchannel("outgoing-messages")
        if self.dispatcher is None:
            self.dispatcher = dispatch.Dispatcher(self)
        self.dispatcher.start_dispatching()
        super(RemoteHost, self).start()
    def stop(self):
        if self.dispatcher is not None:
            self.dispatcher.stop_dispatching()
        self.dispatcher = None
        super(RemoteHost, self).stop()
    def getmonitor(self):
        return self.messaging.getmonitor()
    def getchannel(self, name, default=Undefined):
        if default is Undefined:
            default = self.outgoing
        return super(RemoteHost, self).getchannel(name, default)
    monitor = property(getmonitor)


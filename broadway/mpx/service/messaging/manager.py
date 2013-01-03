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
from mpx.lib.message.types import Message
from mpx.lib.messaging.tools import Address
from mpx.lib.messaging.tools import Undefined
from mpx.service.messaging.host import LocalHost
from mpx.service.network.async.connection import monitor
from mpx.service.messaging.transport.server import dispatch

class MessagingService(CompositeNode):
    """
        Manage list of Messaging Hosts.  
        
        Messaging Service provides top-level messaging name 
        space management, and fully qualified destination lookup. 
    """
    def __init__(self):
        self.hosts = {}
        self.localhost = Undefined
        self.monitor = monitor.ChannelMonitor()
        self.dispatcher = dispatch.Dispatcher(self)
        super(MessagingService, self).__init__()
    def start(self):
        if not self.monitor.is_running():
            self.monitor.start_monitor()
        if not self.dispatcher.is_dispatching():
            self.dispatcher.start_dispatching()
        super(MessagingService, self).start()
    def stop(self):
        if self.monitor.is_running():
            self.monitor.stop_monitor()
        if self.dispatcher.is_dispatching():
            self.dispatcher.stop_dispatching()
        super(MessagingService, self).stop()
    def getmonitor(self):
        return self.monitor
    def addhost(self, host):
        if isinstance(host, LocalHost):
            if self.localhost is not Undefined:
                raise TypeError("local-host instance already exists")
            self.localhost = host
        self.hosts[host.getname()] = host
    def gethost(self, hostname, default=Undefined):
        if hostname == "" or hostname == "localhost":
            host = self.localhost
        else:
            host = self.hosts.get(hostname, default)
        if host is Undefined:
            raise KeyError("no such host: %s" % hostname)
        return host
    def pophost(self, hostname):
        return self.hosts.pop(hostname)
    def get_destination(self, address):
        if isinstance(address, Message):
            address = address.getheader("DEST")
        if isinstance(address, str):
            address = Address.fromurl(address)
        host = self.gethost(address.hostname())
        return host.getchannel(address.name())
    def has_destination(self, address):
        try:
            destination = self.get_destination(address)
        except KeyError:
            return False
        else:
            return True
    def route(self, message):
        channel = self.get_destination(message.getheader("DEST"))
        return channel.send(message)


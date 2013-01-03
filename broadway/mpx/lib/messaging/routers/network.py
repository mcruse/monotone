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
from mpx.lib.url import ParsedURL
from mpx.lib.messaging.routers import Router

class LocationRouter(Router):
    def __init__(self, hostname, incoming, local, remote, *args, **kw):
        self.local_messages = local
        self.remote_messages = remote
        self.local_hostnames = set((hostname, "localhost"))
        super(LocationRouter, self).__init__(incoming, *args, **kw)
    def getroute(self, message):
        desturl = message.getheader("DEST", self.local_hostname)
        destination = ParsedURL.fromstring(desturl)
        if destination.hostname in self.local_hostnames:
            route = self.local_messages
        else:
            route = self.remote_messages
        return route

class HostnameRouter(Router):
    def __init__(self, incoming, unknown, *args, **kw):
        self.destinations = {}
        self.dead_letters = unknown
        super(HostnameRouter, self).__init__(incoming, *args, **kw)
    def addroute(self, hostname, channel):
        self.destinations[hostname] = channel
    def getroute(self, message):
        desturl = message.getheader("DEST", self.local_hostname)
        destination = ParsedURL.fromstring(desturl)
        return self.destinations.get(destination.hostname, self.dead_letters)

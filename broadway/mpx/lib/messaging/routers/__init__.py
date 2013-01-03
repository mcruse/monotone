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
from mpx.lib.messaging.tools import Counter

class Router(object):
    def __init__(self, incoming, *args, **kw):
        self.routed = Counter()
        self.incoming = incoming
        super(Router, self).__init__(*args, **kw)
    def start_routing(self):
        self.incoming.attach(self)
    def stop_routing(self):
        self.incoming.detach(self)
    def handle_message(self, message):
        outgoing = self.getroute(message)
        #print "%s: %s > %s > %s" % (type(self).__name__, self.incoming, message.typename(), outgoing)
        outgoing.send(message)
        self.routed.increment()
    def getroute(self, message):
        raise TypeError()

class DestinationRouter(Router):
    def __init__(self, messaging, incoming, default, *args, **kw):
        self.messaging = messaging
        self.defaultout = default
        super(DestinationRouter, self).__init__(incoming, *args, **kw)
    def getroute(self, message):
        if message.hasheader("DEST"):
            name = message.getheader("DEST")
            destination = self.messaging.get_destination(name)
        else:
            destination = self.defaultout
        return destination

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
from mpx.lib.messaging.tools import debug
from mpx.lib.message.envelope import Envelope

class RequestReply(Envelope):
    TYPENAME = "REQREP"

class Response(RequestReply):
    TYPENAME = "RESPONSE"

class Request(RequestReply):
    TYPENAME = "REQUEST"
    @debug
    def __init__(self, *args, **headers):
        headers = dict(headers)
        headers.setdefault("CORID", str(uuid4()))
        super(Request, self).__init__(*args, **headers)
    def setvalue(self, message):
        if message and not self.getheader("DEST", ""):
            if message.hasheader("DEST"):
                self.setheader("DEST", message.getheader("DEST"))
        return super(Request, self).setvalue(message)
    @debug
    def create_response(self, message):
        response = Response(message)
        self.setup_response(response)
        return response
    @debug
    def setup_response(self, response):
        response.setheader("CORID", self.getheader("CORID"))
        response.setheader("DEST", self.getheader("REPLY-TO"))
        return response
    @debug
    def copy(self):
        headers = self.getheaders()
        headers.pop("CORID")
        message = type(self)(**headers)
        message.setvalue(self.getvalue())
        return message

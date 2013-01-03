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
from mpx.lib.messaging.tools import debug
from mpx.lib.message.types import Message
from mpx.lib.message.data import DataMessage

class Envelope(DataMessage):
    """
        Generic message wrapper.
        
        Envelope wraps message instances into message that 
        includes content type and length information.
    """
    TYPENAME = "ENV"
    @debug
    def __init__(self, message=None, **headers):
        self.content = ""
        self.debug = True
        super(Envelope, self).__init__(message, **headers)
    @debug
    def setvalue(self, message):
        self.message = message
        self.setheader("content-type", "")
        self.setheader("content-length", "")
    @debug
    def getvalue(self):
        return self.message
    @debug
    def parse_head(self, head):
        # Clear content headers since content is being rebuilt.
        self.setvalue(None)
        return super(Envelope, self).parse_head(head)
    @debug
    def parse_body(self, body):
        typespec = self.content_typespec()
        messagetype = Message.find_type(typespec)
        message = messagetype()
        message.parse(body)
        self.content = body
        self.message = message
    @debug
    def serialize_head(self):
        if not self.getheader("content-type", ""):
            self.setheader("content-type", self.content_typespec())
        if not self.getheader("content-length", ""):
            self.setheader("content-length", self.content_length())
        return super(Envelope, self).serialize_head()
    @debug
    def serialize_body(self):
        if not self.content:
            message = self.getvalue()
            self.content = message.serialize()
        return self.content
    @debug
    def content_typespec(self):
        typespec = self.getheader("content-type", "")
        if not typespec:
            message = self.getvalue()
            if message:
                typespec = message.typespec()
        return typespec
    @debug
    def content_length(self):
        length = self.getheader("content-length", 0)
        if not length:
            message = self.getvalue()
            if message:
                length = len(self.serialize_body())
        return str(length)


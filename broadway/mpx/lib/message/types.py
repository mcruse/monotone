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
from mpx.lib.message.bases import MessageBase
Undefined = object()

class Message(MessageBase):
    TYPENAME = "MSG"
    headers = ()
    def __init__(self, *args, **headers):
        # This allows headers to be created prior to super's 
        # initialization, without wiping out existing headers.
        self.headers = dict(self.headers)
        self.headers.update(headers)
        self.setheader("MSGID", str(uuid4()))
        self.setheader("TYPESPEC", self.typespec())
        super(Message, self).__init__(*args, **headers)
    def getid(self):
        """
            Get message ID header value.
        """
        return self.getheader("MSGID")
    def hasheader(self, name):
        return name in self.headers
    def setheader(self, name, value):
        self.headers[name] = value
    def setheaders(self, headers):
        headers = dict(headers)
        headers["MSGID"] = self.getid()
        self.headers.update(headers)
    def getheader(self, name, default=Undefined):
        value = self.headers.get(name, default)
        if value is Undefined:
            raise KeyError("no such header: %s" % name)
        return value
    def getheaders(self):
        return dict(self.headers)
    def copy(self):
        """
            Note that copy state is equal, not necessarily headers.
        """
        message = type(self)()
        message.parse(self.serialize())
        return message
    def equals(self, other):
        return self.serialize() == other.serialize()
    def parse(self, bytes):
        head,delim,body = bytes.partition(self.delimiter() * 2)
        self.parse_head(head)
        self.parse_body(body)
        return self
    def parse_head(self, head):
        separator = self.separator()
        delimiter = self.delimiter()
        headlines = head.strip().split(delimiter)
        headitems = [headline.split(separator) for headline in headlines]
        for name,value in headitems:
            self.setheader(name, value.strip())
    def serialize(self):
        head = self.serialize_head()
        body = self.serialize_body()
        delimiter = self.delimiter()
        return delimiter.join((head, body))
    def serialize_head(self):
        separator = self.separator()
        delimiter = self.delimiter()
        headlines = map(separator.join, self.headers.items())
        return "%s%s" % (delimiter.join(headlines), delimiter)
    def serialize_body(self):
        """
            Get byte-string representation of 
            message instance's payload.
        """
        raise TypeError()
    def parse_body(self, body):
        """
            Initialize message instance's payload by 
            parsing its byte-string representation. 
        """
        raise TypeError()
    def separator(self):
        """
            Get string used to separate header names  
            from header values.
        """
        return ": "
    def delimiter(self):
        """
            Get string used to separate message headers 
            and message sections.
            
            This value will be used to delimit each header, 
            as well as delimiting the head from body sections.
            This means that a double-delimiter will appear between 
            last header and body of message, because header ends 
            with one, and head is separated from body by one.
        """
        return "\r\n"
    def __eq__(self, other):
        return self.equals(other)
    def __copy__(self):
        return self.copy()














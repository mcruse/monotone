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
from mpx.lib.message.envelope import Envelope

class MessageBuilder(object):
    def __init__(self):
        self.envelope = Envelope()
        self.terminator = self.envelope.delimiter() * 2
        # Note that order is reversed so pop() gets first.
        self.writers = [self.write_body, self.write_head]
        super(MessageBuilder, self).__init__()
    def write(self, bytes):
        writemethod = self.writers.pop()
        return writemethod(bytes)
    def get_terminator(self):
        return self.terminator
    def write_head(self, head):
        self.envelope.parse_head(head)
        self.terminator = int(self.envelope.content_length())
    def write_body(self, body):
        self.envelope.parse_body(body)
        self.terminator = 0
    def message(self):
        return self.envelope.getvalue()
    def iscomplete(self):
        return not self.writers

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
import copy
import cPickle
from mpx.lib.message.types import Message

class DataMessage(Message):
    """
        Abstract base-class of data messages.
        
        Type is abstract because it does not override super's 
        serialize/parse body methods, which are required to 
        be overridden by concrete message types. 
        
        Methods 'getvalue' and 'setvalue' are used to access 
        and modify instance's data.  Subclasses can override 
        these methods to hook into instance's value meaning.
    """
    TYPENAME = "DATA"
    def __init__(self, data=None, **headers):
        super(DataMessage, self).__init__(**headers)
        self.setresult(data)
    def copy(self):
        message = type(self)(**self.headers)
        message.setvalue(copy.copy(self.getvalue()))
        return message
    def equals(self, other):
        if type(self) is not type(other):
            return False
        return self.getvalue() == other.getvalue()
    def getvalue(self):
        return self.data
    def setvalue(self, data):
        self.data = data
    def setresult(self, result):
        self.setvalue(result)
        self.setheader("STATUS", "SUCCESS")
    def seterror(self, error):
        self.setvalue(error)
        self.setheader("STATUS", "FAILURE")
    def getresult(self):
        value = self.getvalue()
        if self.getheader("STATUS") == "FAILURE":
            raise value
        return value

class TextMessage(DataMessage):
    TYPENAME = "TEXT"
    def setvalue(self, data):
        if data is None:
            data = ""
        return super(TextMessage, self).setvalue(data)
    def serialize_body(self):
        return self.getvalue()
    def parse_body(self, body):
        self.setvalue(body)

class SimpleMessage(DataMessage):
    TYPENAME = "REPR"
    def serialize_body(self):
        return repr(self.getvalue())
    def parse_body(self, bytes):
        self.setvalue(eval(bytes))

class PickleMessage(DataMessage):
    TYPENAME = "PICKLE"
    def serialize_body(self):
        return cPickle.dumps(self.getvalue())
    def parse_body(self, bytes):
        self.setvalue(cPickle.loads(bytes))



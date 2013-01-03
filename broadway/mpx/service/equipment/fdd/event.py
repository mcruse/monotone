"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import time
from mpx.componentry import implements
from mpx.lib.eventdispatch import Event
from interfaces import IFaultEvent

class FaultEvent(Event):
    implements(IFaultEvent)
    TYPE = 'Fault'
    
    def __init__(self, source, title, faulttype, timestamp, 
                 description, origin = None, guid = None):
        super(FaultEvent, self).__init__(source, origin, guid, timestamp)
        self.lifetime = None
        self.closetime = None
        self.title = title
        self.faulttype = faulttype
        self.description = description
    def tostring(self):
        message = '%s Fault Event "%s" at %s: %s'
        return message % (self.faulttype.upper(), self.title, 
                          time.ctime(self.timestamp), self.description)
    def is_states(self, state):
        if state.lower() == 'closed' and self.timeout is not None:
            if time.time() > (self.timestamp + self.timeout):
                print 'Fault %s returning closed.' % self.title
                return True
            else:
                return False
        return False
    def set_timeout(self, timeout):
        self.lifetime = timeout
        self.closetime = time.time() + timeout

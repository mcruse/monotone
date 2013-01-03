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
from mpx.lib.node import CompositeNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.soap.soap_proxy import RemoteWebServiceProxy

from moab.linux.lib.uptime import secs as now

class Server(RemoteWebServiceProxy):
    def configure(self, cd):
        set_attribute(self, 'username', REQUIRED, cd)
        set_attribute(self, 'password', REQUIRED, cd)
        return super(Server, self).configure(cd)

    def configuration(self):
        cd = super(Server, self).configuration()
        get_attribute(self, 'username', cd)
        get_attribute(self, 'password', cd)
        return cd
        
class Point(CompositeNode):
    def __init__(self):
        self._last_value = None
        self._last_rcvd_at = now()
        return

    def configure(self, cd):
        set_attribute(self, 'uri', REQUIRED, cd)
        set_attribute(self, 'readonly', 1, cd, int)
        set_attribute(self, 'change_reason', 'MPX', cd)
        set_attribute(self, 'ttl', 30, cd, int)
        return super(Point, self).configure(cd)
        
    def configuration(self):
        cd = super(Point, self).configuration()
        get_attribute(self, 'uri', cd)
        get_attribute(self, 'readonly', cd)
        get_attribute(self, 'change_reason', cd)
        get_attribute(self, 'ttl', cd)
        return cd

    def start(self):
        if not self.readonly:
            setattr(self, 'set', self._set)
        super(Point, self).start()
        return
    
    def get(self, skipCache=0):
        if self._last_value and (now() - self._last_rcvd_at) < self.ttl:
            return self._last_value
        self._last_value = self.parent.getValue(
            self.parent.username,
            self.parent.password, 
            self.uri
            )
        self._last_rcvd_at = now()
        return self._last_value

    def _set(self, value):
        assert(not self.readonly)
        return self.parent.setValue(
            self.parent.username,
            self.parent.password,
            self.uri,
            str(value), 
            self.change_reason
            )


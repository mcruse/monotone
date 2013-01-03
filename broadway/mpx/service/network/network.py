"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
import mpx.service.network
from mpx.service import ServiceNode
from mpx.service.network import ConnectionMixin
from mpx.lib.exceptions import ENotEnabled
        
class Network(ServiceNode, ConnectionMixin):
    ##
    # This attribute is used in the introspective generation
    # of configuration data.
    __module__ = mpx.service.network.__name__
    
    def __init__(self):
        ServiceNode.__init__(self)
        self.critical_data = self._CriticalData()

        
    def acquire(self,wait=0):
        if not self.enabled:
            raise ENotEnabled('%s service is Not Enabled' % self.name)
        rt = self._increment_connection_count()
        return rt
    
    def _increment_connection_count(self):
        self.critical_data.acquire()
        count = None
        try:
            count = self.critical_data.increment_connection_count()
        finally:
            self.critical_data.release()
        return count
    
    def _decrement_connection_count(self):
        self.critical_data.acquire()
        count = None
        try:
            count = self.critical_data.decrement_connection_count()
        finally:
            self.critical_data.release()
        return count
    
    def release(self):
        self._decrement_connection_count()
    
    def notify(self,event_class,callback):
        pass
        
network_singleton = Network()

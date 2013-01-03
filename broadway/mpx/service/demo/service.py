"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx.lib import threading, pause
from mpx.service import ServiceNode
from mpx.lib.configure import set_attribute, get_attribute, \
     REQUIRED
from mpx.lib.node import as_node, as_node_url
from mpx.lib.exceptions import EAlreadyRunning

##
# All primary services (one that exist at the top service 
# level) inherit from ServiceNode.
#
# After a service object has been instaciated
# and its configure method has been called, start is 
# called.  Start is where, if your service runs in its
# own thread, you start a thread.
class ControlService(ServiceNode):
    def __init__(self):
        self.running = 0
        ServiceNode.__init__(self)
    
    def configure(self, config):
        ServiceNode.configure(self, config)
        set_attribute(self, 'heating', REQUIRED, config, as_node)
        set_attribute(self, 'cooling', REQUIRED, config, as_node)
        set_attribute(self, 'temperature', REQUIRED, config, as_node)
        set_attribute(self, 'minimum', REQUIRED, config, float)
        set_attribute(self, 'maximum', REQUIRED, config, float)
        
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'heating', config, as_node_url)
        get_attribute(self, 'cooling', config, as_node_url)
        get_attribute(self, 'temperature', config, as_node_url)
        get_attribute(self, 'minimum', config, str)
        get_attribute(self, 'maximum', config, str)
        return config
    
    def start(self):
        if not self.running:
            self._thread = threading.Thread(target=self._run,args=())
            self.running = 1
            self._thread.start()
            return
        raise EAlreadyRunning()
    
    def stop(self):
        self.running = 0
        self._thread = None
    
    ##
    # This function simply checks temperature every 2 minutes.  
    # If the temperature is below min, heating is turned on, if 
    # it is above max, cooling is turned on.
    #
    def _run(self):
        while self.running:
            temperature = self.temperature.get()
            if temperature > self.maximum:
                self.heating.set(0)
                self.cooling.set(1)
            elif temperature < self.minimum:
                self.cooling.set(0)
                self.heating.set(1)
            else:
                self.cooling.set(0)
                self.heating.set(0)
            pause(120)

def factory():
    return ControlService()
                

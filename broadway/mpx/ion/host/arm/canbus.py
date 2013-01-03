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
from mpx.lib import msglog
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import map_to_attribute, map_from_attribute
from mpx.lib.exceptions import EInvalidValue, EInvalidResponse

from mpx.lib.threading import Queue, Lock
from mpx.lib.threading import Thread
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib import pause

from node import ARMNode
from array import *

##
# Class for DallasBus ION's.
#
class CANBus(ARMNode, AutoDiscoveredNode):

    def __init__(self):
        ARMNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self._lock = Lock()
        self.conversion_list = {}
        self._queue = Queue()
        self.debug = 0
        self.running = 0
        self._start_called = 0
        self.devices = ''
        self.device_addresses = []
        self._been_discovered = 0

    def lock(self):
        self._lock.acquire()
    def unlock(self):
        self._lock.release()

    ##
    # @see node.ARMNode#configure
    #
    def configure(self,config):
        ARMNode.configure(self,config)

    
    def configuration(self):
        config = ARMNode.configuration(self)
        #get_attribute(self, 'devices', config)
        return config
        

    ##
    # start temperature conversions
    #
    def start(self):
        ARMNode.start(self)
        self.running = 0
    
    def stop(self):
        self.running = 0

    ##
    # discover and create object instances
    #
    def _discover_children(self, force=0):
        if force:
            self._been_discovered = 0
        if self.running == 1 and not self._been_discovered:
            pass
        return self._nascent_children

def factory():
    return CANBus()

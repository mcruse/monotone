"""
Copyright (C) 2003 2011 Cisco Systems

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
## @notes Class TCS
##        Simple abstraction for dynamically
##        discovering TCS nodes and presenting
##        them as nodes in the framework

import array
import time
import random

from mpx.lib import msglog
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, \
     as_boolean, as_onoff, REQUIRED
from mpx.lib.exceptions import EAlreadyRunning, \
     ETimeout, EInvalidValue, MpxException
import tcstypes
from mpx.lib.tcs.device import TCSDevice

debug = 0

class TCS(CompositeNode):
    
    version = '0.0'
    
    def __init__(self, lib_device=None, discovered=None):
        CompositeNode.__init__(self)
        self.__node_id__ = '1254'
        self.running = 0
        self.device_name = None
        self.discovered = discovered
        self.tcstype = None
        if lib_device:
            if debug: print 'TCS device type= ', str(lib_device.type)
            self.tcstype = str(lib_device.type)
        
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'debug', debug, config, as_boolean)
        set_attribute(self,'device_name',REQUIRED,config, str)
        set_attribute(self,'unit_number',REQUIRED, config, int)
        set_attribute(self,'controller_type',None, config, str)
        set_attribute(self,'controller_version',None, config, str)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        get_attribute(self, 'device_name',config)
        get_attribute(self, 'unit_number', config, str)
        get_attribute(self, 'controller_type', config, str)
        get_attribute(self, 'controller_version', config, str)
        get_attribute(self, '__node_id__', config, str)
        return config

    def start(self):
        if not self.running:
            self.running = 1
            self.line_handler = self.parent.line_handler
            if self.discovered: #create child nodes for letter codes and bit posistions
                if self.debug: print 'discovered type'
                if self.tcstype:
                    if self.debug: print 'auto discover children'
                    tcstypes.create_auto_discovered_children_for(self, self.tcstype)
                    if self.debug: print 'finished creating children'
            else: #since static
                if self.controller_type is None: #get the type info
                    device = TCSDevice(self.unit_number, self.line_handler)
                    self.controller_type = device.get_type()
                    self.controller_version = device.get_version()
            CompositeNode.start(self) #start all the little suckers we just created
            
        else:          
            raise EAlreadyRunning
    
    def stop(self):
        self.running = 0
    
    def _run(self):
        pass
    
    
    ## get format list of nodes and their values
    #  @returns format list of values
    #
    def get(self, skipCache=0):
        info =        'Version: %s\n' % TCS.version         
        return 'sz' + str(self.controller_type)
        

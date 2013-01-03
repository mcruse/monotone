"""
Copyright (C) 2003 2009 2011 Cisco Systems

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
##
##  This driver has a self discovery feature 
##    The available modes are: discover none, discover new, discover all
##    Discover new will only create node defs for devices that were not previously
##    in the node tree

import array
import time
import random

from mpx.lib import msglog, thread
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, \
     as_boolean, as_onoff
from mpx.lib.exceptions import EAlreadyRunning, \
     ETimeout, EInvalidValue, MpxException
from mpx.lib.tcs import line_handler
from device import TCS

debug = 0

class LineHandler(CompositeNode):
    
    version = '0.0'
    
    def __init__(self):
        CompositeNode.__init__(self)
        self.running = 0
        
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'debug', 0, config, as_boolean)
        set_attribute(self, 'discover', 'never', config, str)
        set_attribute(self, 'discover_start', 0, config, int)
        set_attribute(self, 'discover_stop', 255, config, int)
        debug = self.debug
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        get_attribute(self, 'discover', config, str)
        get_attribute(self, 'discover_start', config, str)
        get_attribute(self, 'discover_stop', config, str)
        return config

    def start(self):
        if debug: print 'starting tcs line driver'
        if not self.running:
            self.running = 1
            self.line_handler = line_handler.TCSLineHandler(self.parent)
            if self.discover != 'never':
                self.discover_children()
            CompositeNode.start(self)
            
        else:          
            raise EAlreadyRunning
        
    
    def stop(self):
        self.running = 0
    
    def _run(self):
        pass
 
    def discover_children(self):
        if debug: print 'discover_children for ion line_handler'
        map = self.line_handler.discover_children(self.discover_start, self.discover_stop)
        existing = self.addresses_of_existing_children()
        if debug: print 'discovered addresses: ', str(map.keys())
        for k in map.keys():
            if self.discover == 'new':
                if k in existing:  #this one is not new, don't add it again
                    continue
            childDict = {}
            name = '%03d' % k
            childDict['name'] = name
            childDict['parent'] = self
            point = map[k]
            childDict['controller_type'] = point.get_type()
            childDict['controller_version'] = point.get_version()
            childDict['unit_number']=k
            childDict['device_name']=name
            if debug: print 'configure a TCS device with: ', str(childDict)
            child = TCS(point, 1)                
            child.configure(childDict)
            if debug: print 'child has been configured, next start'
 
    def addresses_of_existing_children(self):
        answer = []
        for a_child in self.children_nodes():
            answer.append(a_child.unit_number)
        return answer
            
    
    ## get format list of nodes and their values
    #  @returns format list of values
    #
    def get(self, skipCache=0):
        info =        'Version: %s\n' % LineHandler.version         
        return info
        


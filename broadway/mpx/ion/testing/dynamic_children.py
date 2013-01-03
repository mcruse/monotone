"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
## @notes Class DynamicChildren
##        Simple test node for dynamic discovered children


import random

from mpx.lib import msglog, thread
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, as_boolean, as_onoff
from mpx.lib.exceptions import EAlreadyRunning, MpxException
from mpx.lib.tracer100 import device


def factory():
    return DynamicChildren()  

# Class Tracer100Point
#  Used to encapsulate a single point on the Tracer 100
#
class _DynamicChildPoint(ConfigurableNode):
    
    def configure(self, dict):
        ConfigurableNode.configure(self, dict)
            
        set_attribute(self, 'debug', 0, dict, as_boolean)            
        set_attribute(self, 'value', None, dict)     
        set_attribute(self, '__node_id__', '120075', dict)
     
    def configuration(self):
        config = ConfigurableNode.configuration(self)
        
        get_attribute(self, 'value',config, str)
        get_attribute(self, 'debug',config, str)
        get_attribute(self, '__node_id__', config)
        return config
        
    def get(self, skipCache=0):
        return self.value
        
   
    def set(self, v):
        self.value = v

class DynamicChildren(CompositeNode):
    
    version = '1.0'
    
    def __init__(self):
        CompositeNode.__init__(self)
        self.running = 0
  
                           
        
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'debug', 0, config, as_boolean)

    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, as_onoff)
        return config

    def start(self):
        if not self.running:
            self.running = 1
            self._discoverChildrenNodes()
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
        info =        'Version: %s\n' % DynamicChildren.version                           
        return info
        

    ## 
    #  discover nodes from named Tracer100
    def _discoverChildrenNodes(self):
        
        try:            
            countKids = 21
            i = 1
            while i < countKids:
                childDict = {}
                name = ""
                if i < 10:
                    name = '11-0%d' % i
                else:
                    name = '11-%d' % i
                childDict['name'] = name
                number = random.randint(50,99) + random.random()
                childDict['value'] = '%.1f' % float(number)
                childDict['parent'] = self            
                child = _DynamicChildPoint()                
                child.configure(childDict)   
                child.set('%.1f' % float(number))
                i = i + 1
              
        except Exception, e:
            raise MpxException('Error while discovering DynamicChildren points: ' + str(e))
        

if __name__ == '__main__':
    config = {}
    config['parent'] = None
    
    t100 = DynamicChildren()
    t100.configure(config)
    t100.start()
    
    s = t100.get()
    
    nodes = t100.children_nodes()    
    
    

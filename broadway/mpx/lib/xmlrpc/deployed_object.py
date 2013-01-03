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

from mpx.service import SubServiceNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute


class XMLRPC_DeployedObject(SubServiceNode):
 
    
    def configure(self, config):
        set_attribute(self, 'object_alias', REQUIRED, config)
        set_attribute(self,'object_name','UNKNOWN',config)        
        set_attribute(self,'can_query','1',config)
        set_attribute(self,'is_enabled','1',config)
        set_attribute(self, 'object_lifetime','Per Request', config)
        
        SubServiceNode.configure(self, config)
        
    ##
    # Get the configuration.http://search.netscape.com/search.psp?cp=clkussrp&charset=UTF-8&search=file
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    #
    def configuration(self):
        config = SubServiceNode.configuration(self)
        get_attribute(self, 'object_alias', config)
        get_attribute(self,'object_name',config)
        get_attribute(self,'can_query',config)
        get_attribute(self,'is_enabled',config)        
        get_attribute(self, 'object_lifetime', config)
        
        return config    

def factory():
    return XMLRPC_DeployedObject()



"""
Copyright (C) 2002 2005 2006 2010 2011 Cisco Systems

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

#from mpx.lib.exceptions import ENotImplemented

## 
#  @notes   XMLRPC_ObjectInterface is an interface that
#           describes a single object that is deployed
#           via XMLRPC

from mpx.lib.debug import _merge_class
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
import mpx.lib.node
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.node import as_node
from mpx.lib.node import ServiceNode

class XMLRPC_ObjectInterface:

    ## Find any methods that have been defined
    #  on this object and return it as a list
    #  of strings
    #
    # @return list of method names
    #
    def get_methods(self):
        raise ENotImplemented
    
    def call_method(self, method, params):
        raise ENotImplemented
    
    
    
##
#  @notes Default XMLRPC_Object.  Used as place holder
#         for deployed objects
#
#  Other deployed object can extend from this class to allow
#  for basic discovery of methods (get_methods).  
#  
class XMLRPC_DefaultObject(XMLRPC_ObjectInterface):
    
    def __init__(self):
        self.counter = 0

    
    ## Return all non-private methods
    #  defined by this object
    # @return list of of public methods defined
    #
    import string
    def get_methods(self):
        l_new = []
        l = _merge_class([], self.__class__)
        for i in l:
            if i[0] != '_':
                # Is a public method
                l_new.append(i)
        return l_new
    
    def test(self):
        self.counter += 1
        return self.counter
    
    
    ## @return params passed in
    #
    def get_params(self, params):
        return params
    
    def test_one_param(self, one_param):
        return 'OK One Param -> ' + str(one_param)
    
    def test_two_param(self, one_param, two_param):
        return 'OK Two Param -> %s, %s' % (str(one_param), str(two_param))
    
   
    



## Class RNA_XMLRPC 
# This is a service to node that will register an XMLRPC deployed object

class XMLRPC_Deploy(ServiceNode):
    def configure(self, config):
        set_attribute(self, 'alias', REQUIRED, config)
        set_attribute(self, 'class_name',REQUIRED, config)
        set_attribute(self, 'lifetime', 'Request',config)        
        ServiceNode.configure(self, config)
    def configuration(self):
        config = ServiceNode.configuration(self)        
        get_attribute(self, 'alias', config)
        get_attribute(self, 'class_name', config)
        get_attribute(self, 'lifetime', config)
        return config
    def start(self):
        alias = self.alias
        class_name = self.class_name
        lifetime = self.lifetime
        # Register with our parent the named object
        self.parent.register_deployed_object(alias, class_name, lifetime)
        ServiceNode.start(self)
    
 
if __name__ == '__main__':
    
    d = XMLRPC_DefaultObject()
    li = d.get_methods()
    print li

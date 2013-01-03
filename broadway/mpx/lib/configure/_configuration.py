"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
import urllib
from _tree import Node

##
# Standard Configuration object implementation.
# Represents node tree and makes available configuration
# information.
#
# @implements ConfigurationInterface
#
class Configuration(Node):
    def __init__(self):
        Node.__init__(self)
        self.attributes = {}
    
    ##
    # Set configuration dict for this node.
    #
    # @param attributes  Dictionary containing configuration.
    #
    def _set_config(self, attributes):
        self.attributes = attributes

    def configure(self, config):
        return self._set_config(config)
    
    ##
    # Get the name of this node.
    #
    # @return Name string.
    #
    def get_name(self):
        if self.attributes.has_key('name'):
            return self.attributes['name']
        else:
            return ''
    
    ##
    # Get the description of this node.
    #
    # @return Description string.
    #
    def get_description(self):
        if self.attributes.has_key('description'):
            return self.attributes['description']
        else:
            return ''
    
    ##
    # Get the module for this node.
    #
    # @return Module name for this string.
    #
    def get_module(self):
        if self.attributes.has_key('module'):
            return self.attributes['module']
        else:
            return ''
    
    ##
    # Get the url for this node from its location
    # in the tree.
    #
    # @return url-encoded string representing url
    #         for this node.
    #
    def get_url(self):
        if self.parent:
            if not isinstance(self.parent, str):
                url = self.parent.get_url()
            else:
                url = self.parent
            if url[-1:] != '/':
                url += '/'
            return url + urllib.quote(self.get_name(),'')
        else:
            return self.get_name()
    
    ##
    # Get the configuration dictionary for this node.
    #
    # @return Dictionary with configuration passed in and
    #         a key 'parent' with parent's url.
    #
    def get_config(self, add_parent = 1):
        copy = self.attributes.copy()
        if add_parent:
            parent = self.get_parent()
            if parent and not isinstance(parent, str):
                parent = parent.get_url()
            copy['parent'] = parent
        return copy

    def configuration(self, add_parent = 1):
        return self.get_config(add_parent)




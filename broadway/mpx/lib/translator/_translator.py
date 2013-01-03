"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import ENotImplemented

from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url

##
# Base class for ions that provide getters and setters that are simple
# translations of another ion.  By default it translates the parent
# ion, but an 'ion' configuration attribute can point to any other
# instanciated ion.
#
class Translator(CompositeNode):
    ##
    # @see ConfigurableNode#configure
    #
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'ion', self.parent, config, as_node)
        if not self.ion:
            self.ion = self.parent
        if hasattr(self, '_mutate'):
            self._mutate()

    ##
    # Get this objects configuration.
    #
    # @return Dictionary containg configuration.
    # @see ConfigurableNode#configuration
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'ion', config, as_node_url)
        return config

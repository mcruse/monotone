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
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, set_attributes, \
     get_attribute, get_attributes

##
# Class for simple configured I/O points that return an engineering unit.
#
# A configured point is one that can return different results based on
# configuration.  An example is a configurable AnalogIn that can return V,
# mV, mA, and Ohms.
#
class ConfiguredPoint(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)

    ##
    # Configure object.
    #
    # @param config  Configuration dictionary.
    # @key unit  The units of values.
    # @default None
    # @key min  Minimum value for point.
    # @default None
    # @key max  Max value for point.
    # @default None
    #
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'unit',None, config)
        set_attributes(self, (('min',None),('max',None)), config, float)

    ##
    # Get objects configuration.
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'unit', config, str)
        get_attributes(self, ['min', 'max'], config, str)
        return config
        

    ##
    # @see mpx.ion.ion.IONode#get
    #
    def get(self, skipCache=0):
        return self.parent.get(skipCache)

    ##
    # @see mpx.ion.ion.IONode#get_result
    #
    def get_result(self, skipCache=0, **keywords):
        return self.parent.get_result(skipCache)

    ##
    # @see mpx.ion.ion.IONode#set
    #
    def set(self, value, asyncOK=1):
        return self.parent.set(value, asyncOK)

    ##
    # @see mpx.ion.ion.IONode#set
    #
    def bind_event(self, event, callback):
        return self.parent.bind_event(event, callback)

def factory():
    return ConfiguredPoint()

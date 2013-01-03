"""
Copyright (C) 2001 2003 2010 2011 Cisco Systems

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
from mpx.ion.modbus.cached_ion import CachedION
from register_maps import register_maps
from mpx.lib.node import ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.node import as_node, as_node_url

class DG50(CachedION):
    ##
    # Apply a multiplier to a value before setting it and divide the value
    # when getting it.
    # @fixme Move to mpx.lib.translator.
    # @todo Add an offset?
    class ScaledION(ConfigurableNode):
        ION = 'ion'
        MULTIPLIER = 'multiplier'
        def configure(self,config):
            ConfigurableNode.configure(self, config)
            set_attribute(self, self.ION, self.parent, config, as_node)
            set_attribute(self, self.MULTIPLIER, REQUIRED, config)
        def configuration(self):
            config = ConfigurableNode.configuration(self)
            get_attribute(self, self.ION, config, as_node_url)
            get_attribute(self, self.MULTIPLIER, config)
            return config
        ##
        # @return <i>ion</i>/<i>multiplier</i>.
        def get(self,skipCache=0):
            return self.ion.get(skipCache)/self.multiplier
        ##
        # @return A result with the value <i>ion</i>/<i>multiplier</i>.
        def get_result(self,skipCache=0, **keywords):
            result = self.ion.get_result(skipCache)
            result.value = result.value/self.multiplier
            return result
        ##
        # Set the <i>ion</i> to <i>value</i> x <i>multiplier</i>.
        def set(self, value, asyncOK=1):
            return self.ion.set(value*self.multiplier, asyncOK)

    def configure(self,config):
        # Use the register maps to create all of the inherent children.
        CachedION.configure(self,config)
        # Scale the system_frequency from 'raw' values to Hz.
        h = self.ScaledION()
        h.configure({'name':'scaler',
                     'parent':self.get_child('avr_vscale'),
                     'multiplier':1000.0})
        h = self.ScaledION()
        h.configure({'name':'V',
                     'parent':self.get_child('batt_volts'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'V',
                     'parent':self.get_child('batt_volts_h'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'V',
                     'parent':self.get_child('batt_volts_hsp'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'V',
                     'parent':self.get_child('batt_volts_l'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'V',
                     'parent':self.get_child('batt_volts_lsp'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'Hz',
                     'parent':self.get_child('freq'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'Hz',
                     'parent':self.get_child('freq_h'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'Hz',
                     'parent':self.get_child('freq_hsp'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'Hz',
                     'parent':self.get_child('freq_l'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'Hz',
                     'parent':self.get_child('freq_lsp'),
                     'multiplier':10.0})
        h = self.ScaledION()
        h.configure({'name':'scaler',
                     'parent':self.get_child('gvscale'),
                     'multiplier':10.0})
    ##    
    def register_maps(self):
        return register_maps

def factory():
    return DG50()

"""
Copyright (C) 2001 2002 2003 2010 2011 Cisco Systems

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
##
# Provides the factory used to instantiate the ABB SCD2000 ION.

from mpx.lib.modbus.response import ReadHoldingRegisters
from mpx.ion.modbus.cached_ion import CachedION
from mpx.lib.node import ConfigurableNode
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED
from mpx.lib.node import as_node, as_node_url

##
# @fixme Determin if RegisterDescription should be generic.
from mpx.ion.modbus.veris.h8000 import RegisterDescription

# IMPLEMENTATION NOTE:
# This implementation uses the Framework's mpx.ion.modbus.CachedION class
# to model the SCD2000 as an ION.  The CachedION relies on one or more
# "register maps" to convert a range of registers into an ION.  Each
# register map cooresponds to an internal cache which contains all the
# registers specified in to map.  By using ReadHoldingRegisters to load
# the cache, the modbus layer can provide much greater efficiency than
# if the values where read individually.
#
# Currently, the map contains instances of 
# mpx.ion.modbus.veris.h8000.RegisterDescription which will be moved to
# to a more reasonable location prior to shipping version 1.0.  The
# RegisterDescription class is simply a convenience for containing the
# following information about a value to read from the modbus:
# 1. The ReadHoldingRegister start value. (The MODBUS register - 40001)
# 2. The ReadHoldingRegister count value. (The number of registers)
# 3. The name to give the value.
# 4. The method on the ReadHoldingRegister response used to convert the
#    register(s) into a meaningful value.
# 5. An optional function used to set the value.
map = []
map.append(RegisterDescription(256, 1, "A.A",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(257, 1, "A.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(258, 1, "B.A",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(259, 1, "B.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(260, 1, "C.A",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(261, 1, "C.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(262, 1, "N.A",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(263, 1, "N.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(264, 2, "A-N.V",
                               ReadHoldingRegisters.register_as_dword))
map.append(RegisterDescription(266, 1, "A-N.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(267, 2, "B-N.V",
                               ReadHoldingRegisters.register_as_dword))
map.append(RegisterDescription(269, 1, "B-N.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(270, 2, "C-N.V",
                               ReadHoldingRegisters.register_as_dword))
map.append(RegisterDescription(272, 1, "C-N.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(273, 2, "A-B.V",
                               ReadHoldingRegisters.register_as_dword))
map.append(RegisterDescription(275, 1, "A-B.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(276, 2, "B-C.V",
                               ReadHoldingRegisters.register_as_dword))
map.append(RegisterDescription(278, 1, "B-C.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(279, 2, "C-A.V",
                               ReadHoldingRegisters.register_as_dword))
map.append(RegisterDescription(281, 1, "C-A.Deg",
                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(282, 2, "A.KW",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(284, 2, "B.KW",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(286, 2, "C.KW",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(288, 2, "3Phase.KW",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(290, 2, "A.KVARS",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(292, 2, "B.KVARS",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(294, 2, "C.KVARS",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(296, 2, "3Phase.KVARS",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(298, 2, "A.KWh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(300, 2, "B.KWh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(302, 2, "C.KWh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(304, 2, "3Phase.KWh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(306, 2, "A.KVARh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(308, 2, "B.KVARh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(310, 2, "C.KVARh",
                               ReadHoldingRegisters.register_as_long))
map.append(RegisterDescription(312, 2, "3Phase.KVARh",
                               ReadHoldingRegisters.register_as_long))
##map.append(RegisterDescription(314, 1, "Zero_Sequence_Current",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(315, 1, "Zero_Sequence_Current_Angle",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(316, 1, "Positive_Sequence_Current",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(317, 1, "Positive_Sequence_Current_Angle",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(318, 1, "Negative_Sequence_Current",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(319, 1, "Negative_Sequence_Current_Angle",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(320, 2, "Positive_Sequence_Vlotage_Magnitude",
##                               ReadHoldingRegisters.register_as_dword))
##map.append(RegisterDescription(322, 1, "Positive_Sequence_Vlotage_Angle",
##                               ReadHoldingRegisters.register_as_word))
##map.append(RegisterDescription(323, 2, "Negative_Sequence_Voltage_Magnitude",
##                               ReadHoldingRegisters.register_as_dword))
##map.append(RegisterDescription(325, 1, "Negative_Sequence_Voltage_Angle",
##                               ReadHoldingRegisters.register_as_word))
map.append(RegisterDescription(326, 1, "system_frequency",
                               ReadHoldingRegisters.register_as_word))


##
# A list of (map, timeout) tuples used to define the register mappings
# used to define a specific modbus personality.
_register_maps = [(map, 1.0)]
del map

##
# Modules the SCD2000 as an ION.
class SCD2000(CachedION):
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
        # Use the register maps to create all of the SCD2000's inherent
        # children.
        CachedION.configure(self,config)
        # Scale the system_frequency from 'raw' values to Hz.
        h = self.ScaledION()
        h.configure({'name':'Hz','parent':self.get_child('system_frequency'),
                     'multiplier':100.0})
    ##
    # @return A list of register map, timeout tuples used to create the caches
    #         used by the SCD2000.
    def register_maps(self):
        return _register_maps

##
# Instantiates an unconfigured SCD2000 personality.
def factory():
    return SCD2000()

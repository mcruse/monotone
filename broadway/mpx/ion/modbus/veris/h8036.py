"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
from mpx.lib.modbus.response import ReadHoldingRegisters
from mpx.ion.modbus.cached_ion import CachedION

from h8000 import RegisterDescription, ResetAccumulator

map = []
map.append(RegisterDescription(258, 2, "kWh",
                               ReadHoldingRegisters.register_as_float,
                               ResetAccumulator))
map.append(RegisterDescription(260, 2, "kW",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(262, 2, "var",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(264, 2, "VA",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(266, 2, "pf",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(268, 2, "ltl.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(270, 2, "ltn.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(272, 2, "A",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(274, 2, "A.kW",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(276, 2, "B.kW",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(278, 2, "C.kW",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(280, 2, "pfA",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(282, 2, "pfB",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(284, 2, "pfC",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(286, 2, "A-B.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(288, 2, "B-C.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(290, 2, "A-C.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(292, 2, "A-N.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(294, 2, "B-N.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(296, 2, "C-N.V",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(298, 2, "A.A",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(300, 2, "B.A",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(302, 2, "C.A",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(304, 2, "ave.kW",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(306, 2, "min.kW",
                               ReadHoldingRegisters.register_as_float))
map.append(RegisterDescription(308, 2, "max.kW",
                               ReadHoldingRegisters.register_as_float))

register_maps = [(map, 1.0)]
del map

class H8036(CachedION):
    def register_maps(self):
        return register_maps

def factory():
    return H8036()

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
##
# @todo  Determin if this really is a generic ADAM AnalogIn.  My only example
# is the ADAM-4017.
# @todo I'm not convinced the get/set in here should be doing the string to
# float conversions.  Probably get and set should use strings to be
# consistent with the ION model.

import string
import mpx.lib
from module_point import ModulePoint

class AnalogIn(ModulePoint):
    def __init__(self,name,config):
        ModulePoint.ModulePoint.__init__(self,name,config)
        return

    def configure(self, config):
        ModulePoint.configure(self,config)
        range_name = config[self.parent.range_attribute]
        range = Range.map[range_name]
        ion = mpx.lib.factory('mpx.ion.configured_point')
        ion.configure({'name':range.unit,'parent':self,'unit':range.unit,
                       'min':range.min,'max':range.max})

    def get(self, skipCache=1):
        # For some possible configurations, this may not work...
        result = self.parent.ReadAnalogChannelN(self.id)
        return string.atof(result)

def factory(name, version, configuration_dict, activate):
    return AnalogIn(name,configuration_dict)

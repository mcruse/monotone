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
# @todo Determin if this really is a generic ADAM DigitalOut.  My only example
# is the ADAM-4050.  Assuming that other modules support the DigitalDataIn
# method, then we should be OK.  Otherwise, we should be able to come up
# with a common abstraction for all ADAM modules that support DIs.
# @todo DigitalDataIn doesn't seem to return the correct output status,
#       therefore get() doesn't really work.
# @todo More importantly, SET RELIES ON A TUPLE STORED ON THE parent module.
# This is not reliable and must be resolved!!!

from mpx.lib.exceptions import EInvalidValue

from module_point import ModulePoint
import types

class DigitalOut(ModulePoint):
    def __init__(self):
        ModulePoint.__init__(self)
    def configure(self, config):
        ModulePoint.configure(self, config)
    def get(self, skipCache=0):
        # See TODOs 2 and 3.
        # return self.parent.DigitalDataIn()[1][self.id]
        return self.parent.do_status[self.id]
    def set(self, value, asyncOK=1):
        # Ideally, we'd fetch the current status.  See TODOs 2 and 3.
        if type(value) == types.StringType:
            value = int(value)
        if value not in (0, 1):
            raise EInvalidValue, (self.name, value)
        self.parent.do_status[self.id] = value
        apply(self.parent.DigitalDataOut, self.parent.do_status)
        return

def factory(name, version, configuration_dict, activate):
    return DigitalOut(name,configuration_dict)

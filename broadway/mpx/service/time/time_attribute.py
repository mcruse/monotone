"""
Copyright (C) 2002 2005 2010 2011 Cisco Systems

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
from mpx.service import ServiceNode
from mpx.lib.exceptions import EInvalidValue

##
# Service node
# index in the constructor is used as
# the index in the time_tuple that is returned
# by the parent for the correct value
class TimeAttribute(ServiceNode):
    ##
    # @param index the index in the parents time_tuple of the correct location
    # @exception EInvalidValue if the index is not in the range
    # 0-8
    def __init__(self,index=-1):
        if index == -1:
            t = 'index must be in the range 0-8'
            raise EInvalidValue('index',str(index),text=t)
        else:
            self.index = index
        super(TimeAttribute, self).__init__()
    ##
    # @return the correct value from the parents time_tuple
    def get(self, skipCache=0):
        return self.parent.time_tuple()[self.index]

##
# Service Node
# returns the milliseconds from the parents
# time method
class MilliSeconds(ServiceNode):
    ##
    # @ return the milliseconds from the parents
    # time method
    def get(self, skipCache=0):
        t = self.parent._time()
        t = (t - int(t)) * 1000.0
        return t

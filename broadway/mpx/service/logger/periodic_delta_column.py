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
import mpx.lib
from mpx.lib import msglog
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.security import RExec
from mpx.lib.exceptions import ENotStarted
from mpx.lib.translator.calculator import Calculator

from periodic_column  import PeriodicColumn
from types import *

class PeriodicDeltaColumn(PeriodicColumn):
    ##
    # @author Craig Warren
    # @param config
    #   @key context Sets the context for the function passed in
    #   @value anything Possible context 'import time' because the function
    #                 uses the time modual
    #   @default None
    #   @key function Function to return the value to record
    #   @value function
    #   @required
    #   @key args Arguments to the function
    #   @value list a list of arguments required by the function
    #   @default an empty list
    # @return None
    #
    def configure(self,config):
        PeriodicColumn.configure(self, config)
        if not self.has_child('delta'):
            c = Calculator()
            c.configure({'name':'delta', 
                         'parent':self,
                         'statement':'value - last_value',
                         'variables':[{'vn':'value',
                                       'node_reference':'$value'},
                                      {'vn':'last_value',
                                       'node_reference':'$last_value'}]})
        return
    ##
    # @author Craig Warren
    # @return the delta between the previous value and the current value
    def get(self, skipCache=0):
        if self._calculator is None:
            raise ENotStarted()
        return PeriodicColumn.get(self)

##
# @author Craig Warren
# @return periodiccolumn
#  returns and instanciated PeriodicDeltaColumn
#
def factory():
    return PeriodicDeltaColumn()

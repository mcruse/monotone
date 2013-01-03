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
import mpx.lib
from mpx.lib import msglog
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.security import RExec
from mpx.lib.translator.calculator import Calculator

from periodic_column  import PeriodicColumn
from types import *

class PeriodicAverageColumn(PeriodicColumn):
    ##
    # @author Fred Davison
    # @param config
    # @return None
    #
    def configure(self,config):
        PeriodicColumn.configure(self, config)
        if not self.has_child('average'):
            c = Calculator()
            c.configure({'name':'average',
                         'parent':self,
                         'statement':'(value + last_value)/2.0',
                         'variables':[{'vn':'value',
                                       'node_reference':'$value'}, 
                                      {'vn':'last_value',
                                       'node_reference':'$last_value'}, 
                                      {'vn':'last_time',
                                       'node_reference':'$last_time'}, 
                                      {'vn':'now','node_reference':'$now'},
                                      {'vn':'period',
                                       'node_reference':'$period'}]})
        return
    ##
    # @author Craig Warren
    # @return the delta between the previous, unconverted, value and the
    #         current, unconverted, value.
    def get(self, skipCache=0):
        if self._calculator is None:
            raise msglog.exception()
        return PeriodicColumn.get(self)

##
# @author Craig Warren
# @return periodiccolumn
#  returns and instanciated PeriodicDeltaColumn
#
def factory():
    return PeriodicAverageColumn()

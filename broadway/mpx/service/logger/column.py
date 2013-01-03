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
# @import from mpx.lib.configure set_attribute,get_attribute,REQUIRED
#         from mpx.service SubServiceNode
#
from mpx.lib import msglog
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import EUnreachableCode
from mpx.lib.node import CompositeNode
from mpx.service import SubServiceNode

from mpx.lib import UniqueToken
NOPREVIOUSVALUE = UniqueToken('NOPREVIOUSVALUE')

class Columns(CompositeNode):
    def configure(self,config):
        #
        # log_error_value and log_error_type are used by logs that invoke
        # functions to there value and may throw an exception.  This provides
        # a default for all columns.
        #
        set_attribute(self, 'log_error_value', 'None', config)
        set_attribute(self, 'log_error_type', 'eval', config)
        CompositeNode.configure(self,config)
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'log_error_value', config)
        get_attribute(self, 'log_error_type', config)
        return config

class Column(SubServiceNode):
    ##
    # @author Craig Warren
    # @param config a configuration dictionary
    #   @key position
    #   @value int the position of the column
    #   @required
    #   @key type
    #   @default 'column'
    # @return None
    #
    def configure(self,config):
        set_attribute(self,'position', REQUIRED, config, int)
        set_attribute(self, 'sort_order', 'none', config)
        set_attribute(self, 'type', 'column', config)
        #
        # error_value and error_type are used by logs that invoke functions to
        # there value and may throw an exception.  They are on the fallback
        # column Node primarily out of laziness.
        #
        set_attribute(self, 'column_error_value', 'log_error_value', config)
        set_attribute(self, 'column_error_type', 'log_error_type', config)
        SubServiceNode.configure(self,config)
        return
    def get_error_value(self, previous_value=NOPREVIOUSVALUE):
        try:
            error_type = self.column_error_type
            error_value = self.column_error_value
            if error_type == 'log_error_type':
                error_type = self.parent.log_error_type
                error_value = self.parent.log_error_value
            if error_type == 'eval':
                result = eval(error_value)
                return result
            elif error_type == 'previous_value':
                if previous_value is not NOPREVIOUSVALUE:
                    return previous_value
                # There is no previous value, return the configured error_value.
                result = eval(error_value)
                return result
            else:
                raise EInvalidValue(
                    'error_type', self.error_type,
                    "Valid error_types: 'eval'"
                    )
        except:
            msglog.exception()
            return None
        raise EUnreachableCode()
    ##
    # @author Craig Warren
    # @return
    #   returns the current configuration in a
    #   configuration dictionary
    #
    def configuration(self):
        config = SubServiceNode.configuration(self)
        get_attribute(self, 'sort_order', config)
        get_attribute(self, 'position', config, str)
        get_attribute(self, 'type', config)
        get_attribute(self, 'column_error_value', config)
        get_attribute(self, 'column_error_type', config)
        return config

##
# @author Craig Warren
# @return column
#  returns and instanciated Column
#
def factory():
    return Column()

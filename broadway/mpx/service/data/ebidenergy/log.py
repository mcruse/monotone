"""
Copyright (C) 2010 2011 Cisco Systems

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
from mpx.lib.node import as_node_url,as_node
from mpx.lib.exceptions import EConfiguration
from mpx.lib.configure import set_attribute,get_attribute,\
     REQUIRED,as_boolean
from mpx.lib.translator.calculator import Calculator
from mpx.lib.translator.linear_adjustor import LinearAdjustor
from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.service.logger.periodic_delta_column import PeriodicDeltaColumn

class _Column(PeriodicColumn):
    def configure(self,config):
        set_attribute(self,'node',REQUIRED,config)
        config['function'] = 'mpx.lib.node.as_node("%s").get' % self.node
        PeriodicColumn.configure(self,config)
        set_attribute(self,'delta',0,config,as_boolean)
        if self.delta:
            c = Calculator()
            c.configure({'name':'delta',
                         'parent':self,
                         'statement':'value-last_value',
                         'variables':[{'vn':'value',
                                       'node_reference':'$value'},
                                      {'vn':'last_value',
                                       'node_reference':'$last_value'}]})
        set_attribute(self,'meter_description',self.name,config)
        set_attribute(self,'account',REQUIRED,config)
        set_attribute(self,'meter_number',REQUIRED,config)
        set_attribute(self,'units','',config)
    def configuration(self):
        config = PeriodicColumn.configuration(self)
        get_attribute(self,'node',config,as_node_url)
        get_attribute(self,'meter_description',config)
        get_attribute(self,'account',config)
        get_attribute(self,'meter_number',config)
        get_attribute(self,'units',config)
        return config
    def values(self,entry):
        # list [timestamp]
        return [entry['timestamp']]
class ModbusColumn(_Column):
    def configure(self,config):
        _Column.configure(self,config)
        set_attribute(self,'type','Cumulative',config)
    def configuration(self):
        config = _Column.configuration(self)
        get_attribute(self,'type',config)
        return config
    def start(self):
        self._node = as_node(self.node)
        if hasattr(self._node,'register'):
            self.register = self._node.register
        elif hasattr(self._node,'offset'):
            # @todo DANGER: assumes holding register!!!
            self.register = self._node.offset + 40001
        else:
            raise EConfiguration(('Required attribute "node" ' + 
                                  'must be modbus reg. Node %s ' +
                                  'does not have attribute ' +
                                  'register or offset.') % self.node)
        _Column.start(self)
    def values(self,entry):
        values = _Column.values(self,entry)
        # value
        values.append(entry[self.name])
        # count
        values.append(0)
        return values
class PulseColumn(_Column):
    def configure(self,config):
        _Column.configure(self,config)
        set_attribute(self,'type','Absolute',config)
        set_attribute(self,'multiplier',1,config,float)
        set_attribute(self,'offset',0,config,float)
        self.register = 0
    def configuration(self):
        config = _Column.configuration(self)
        get_attribute(self,'type',config)
        get_attribute(self,'multiplier',config,str)
        get_attribute(self,'offset',config,str)
        return config
    def values(self,entry):
        values = _Column.values(self,entry)
        # Adjusted value
        if entry[self.name] is not None:
            values.append((entry[self.name] * self.multiplier) + self.offset)
        else:
            values.append(None)
        # count
        values.append(entry[self.name])
        return values

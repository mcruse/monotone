"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.modbus.command import ReadHoldingRegisters, \
     ReadCoilStatus, ForceSingleCoil, PresetSingleRegister, \
     ReadInputStatus, ReadInputRegisters

from mpx.lib.exceptions import EAbstractMethod

class ModbusRegister(CompositeNode):
    BASE=0
    def configure(self, config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'register', REQUIRED, config, int)
        set_attribute(self, 'base', self.BASE, config, int)
        set_attribute(self, 'offset', self.register-self.base,config,int)
        set_attribute(self, 'multiplier', 1,config,float)
        

    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'register', config, str)
        get_attribute(self, 'base', config, str)
        get_attribute(self, 'offset', config, str)
        get_attribute(self, 'multiplier', config, str)
        return config
    ##
    # Get the value of the register.  All registers support
    # reads so get is part of interface.
    #
    # @param skip_cache Allow cached value to be returned.
    # @default 0  Allow caching.
    #
    def get(self, skip_cache=0):
        raise EAbstractMethod()

class BooleanWrite(ModbusRegister):
    BASE = 1
    def get(self,skip_cache=0):
        command = ReadCoilStatus(self.parent.address,self.offset, 1)
        response = self.parent.line_handler.command(command)
        return response.status(0,self.offset)
        
    def set(self,value):
        self.parent.line_handler.command(ForceSingleCoil(self.parent.address, 
                                                         self.offset, value))

class BooleanRead(ModbusRegister):
    BASE = 10001
    def get(self, skip_cache=0):
        command = ReadInputStatus(self.parent.address,self.offset,1)
        response = self.parent.line_handler.command(command)        
        return response.status(0,0)

class AnalogRead(ModbusRegister):
    BASE = 30001
    def get(self, skip_cache=0):
        command = ReadInputRegisters(self.parent.address,self.offset,1)
        response = self.parent.line_handler.command(command)
        return response.register_as_int(0,0) * self.multiplier

class AnalogWrite(ModbusRegister):
    BASE = 40001
    def get(self, skip_cache=0):
        command = ReadHoldingRegisters(self.parent.address,self.offset,1)
        response = self.parent.line_handler.command(command)
        return response.register_lobyte(0,0)
    def set(self, value):
        command = PresetSingleRegister(self.parent.address,self.offset,value)
        response = self.parent.line_handler.command(command)


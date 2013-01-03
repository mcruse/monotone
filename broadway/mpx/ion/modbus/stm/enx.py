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
from mpx.lib.node import CompositeNode, as_node, ConfigurableNode
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.ion.modbus.generic import Device,HoldingRegister

class _HoldingRegister(HoldingRegister):
    def base_register(self):
        return 40000
class _DummyRegister(_HoldingRegister):
    def get(self,skip_cache=0):
        return None
class _ControlFlags(_HoldingRegister):
    class _BitPoint(ConfigurableNode):
        def configure(self,config):
            ConfigurableNode.configure(self,config)
            set_attribute(self, 'bit', REQUIRED, config, int)
        def configuration(self):
            config = ConfigurableNode.configuration(self)
            get_attribute(self, 'bit', config, str)
            return config
        def get(self,skip_cache=0):
            return (self.parent.get(skip_cache) >> self.bit) & 0x01
    def configure(self,config):
        _HoldingRegister.configure(self,config)
        for i in range(0,16):
            name = 'bit_%s' % i
            if not self.has_child(name):
                bit = _ControlFlags._BitPoint()
                bit.configure({'name':name, 'parent':self, 'bit':i})

_registers = ((_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Air_Flow','debug': 0,
                                 'register': 41000,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Average_Press','debug': 0,
                                 'register': 41001,'type': 'int'}),
              (_ControlFlags,{'read_only': 1,'length': 1,
                              'name': 'Control_Flags','debug': 0,
                              'register': 41002,'type': 'word'}),
              (_ControlFlags,{'read_only': 1,'length': 1,
                              'name': 'Control_Flags2','debug': 0,
                              'register': 41003,'type': 'word'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Current_Fault','debug': 0,
                                 'register': 41004,'type': 'word'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Current_RPM','debug': 0,
                                 'register': 41005,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Engine_Mode','debug': 0,
                                 'register': 41006,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Fill_Mode','debug': 0,
                                 'register': 41007,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Fill_Control_Press','debug': 0,
                                 'register': 41008,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Fill_Setpoint_Press','debug': 0,
                                 'register': 41009,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Highest_RPM','debug': 0,
                                 'register': 41010,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Ignition_Mode','debug': 0,
                                 'register': 41011,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Power','debug': 0,
                                 'register': 41012,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Power_Factor','debug': 0,
                                 'register': 41013,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Short_Sequence_Timer','debug': 0,
                                 'register': 41014,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Start_Count_Eng','debug': 0,
                                 'register': 41015,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Start_Count_User','debug': 0,
                                 'register': 41016,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Start_Mode','debug': 0,
                                 'register': 41017,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_1_Parm','debug': 0,
                                 'register': 41018,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_8_Parm','debug': 0,
                                 'register': 41019,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_15_Parm','debug': 0,
                                 'register': 41020,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_22_Parm','debug': 0,
                                 'register': 41021,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_29_Oil_Temp','debug': 0,
                                 'register': 41022,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_30_Water_In_Temp','debug': 0,
                                 'register': 41023,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'TC_31_Water_Out_Temp','debug': 0,
                                 'register': 41024,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Volt_Amps','debug': 0,
                                 'register': 41025,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Temp_Setpoint','debug': 0,
                                 'register': 41026,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Throttle_PWM_Pct','debug': 0,
                                 'register': 41027,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Temp_Error_Celcius','debug': 0,
                                 'register': 41028,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Control_Temp','debug': 0,
                                 'register': 41029,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Shutdown_State','debug': 0,
                                 'register': 41030,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Status_Flags','debug': 0,
                                 'register': 41031,'type': 'word'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Cycle_Press_1_Calibrated','debug': 0,
                                 'register': 41032,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Cycle_Press_2_Calibrated','debug': 0,
                                 'register': 41033,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Cycle_Press_3_Calibrated','debug': 0,
                                 'register': 41034,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Cycle_Press_4_Calibrated','debug': 0,
                                 'register': 41035,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Oil_Press_Calibrated','debug': 0,
                                 'register': 41036,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Water_In_Press_Calibrated','debug': 0,
                                 'register': 41037,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'Water_Out_Press_Calibrated','debug': 0,
                                 'register': 41038,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 1,
                                 'name': 'H2_Setpoint_Press','debug': 0,
                                 'register': 41039,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 2,
                                 'name': 'Display_Options','debug': 0,
                                 'register': 45000,'type': 'dword'}),
              (_HoldingRegister,{'read_only': 1,'length': 2,
                                 'name': 'Engine_Revision','debug': 0,
                                 'register': 45002,'type': 'dword'}),
              (_HoldingRegister,{'read_only': 1,'length': 2,
                                 'name': 'Energy','debug': 0,
                                 'register': 45004,'type': 'int'}),
              (_HoldingRegister,{'read_only': 1,'length': 2,
                                 'name': 'Run_Time_Eng','debug': 0,
                                 'register': 45006,'type': 'dword'}),
              (_HoldingRegister,{'read_only': 1,'length': 2,
                                 'name': 'Run_Time_User','debug': 0,
                                 'register': 45008,'type': 'dword'}),
              (_HoldingRegister,{'read_only': 1,'length': 2,
                                 'name': 'Engine_Serial_Number','debug': 0,
                                 'register': 45010,'type': 'dword'}))

class ENX(Device):
    def configure(self,config):
        Device.configure(self, config)
        for reg_class,dict in _registers:
            node = reg_class()
            dict.update({'parent':self})
            node.configure(dict)

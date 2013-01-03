"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
# mpx/cpc/lib/tables.py: Lookup tables for CPC devices, items, objects, and properties.
# @author spenner@envenergy.com
# @fixme Use regular expressions in Python to generate full EnumeratedDictionary tables from UHPDB "MDB" tables.
# @fixme Try to eliminate "same data in two places" problem when instantiating ObjData/ItemData in EnumeratedDictionaries.
# @fixme Had to guess at data_types for all PropTypes except Value and Status. Get correct data_types from CPC...
import types
from mpx.lib import EnumeratedValue, EnumeratedDictionary

##
# _cmds: 2-way tables of allowed UHP Request Commands.
_cmds = EnumeratedDictionary({'GetValue':1, 'SetValue':2, 'GetLog':3, 'Backup':7, 'Restore':8})
##
# _data_types: 2-way tables of supported UHP DataTypes.
_data_types = EnumeratedDictionary({0:'NONE', 1:'UCHAR', 2:'CHAR', 3:'SCHAR', \
                                    4:'INT', 5:'UINT', 6:'INT_DIV10', \
                                    7:'UINT_DIV10', 8:'INT_DIV100', 9:'UINT_DIV100', \
                                    10:'LONG', 11:'ULONG', 12:'FUNK_FLOAT', \
                                    13:'FUNK_TIME', 15:'DATE', 16:'SZSTRING', \
                                    17:'LIST_ITEM', 19:'BIT_ARRAY', 20:'ALARM', \
                                    21:'INT_DIV1000', 22:'MONTH_DAY', \
                                    23:'SCHAR_DIV10', 24:'UCHAR_DIV10', 25:'TIME', \
                                    26:'LONG_DIV10', 27:'TIME_HHMM', 28:'TIME_HHMMSS', \
                                    29:'TIME_MMSS'})
##
# class PropData: Allows use of EnumeratedDictionary for _props table;
# gives us a place to store prop_types.
class PropData(EnumeratedValue):
   ##
   # __init__():
   # @param value Integer value of PropData instance
   # @param text Text label associated with given integer value
   # @param data_type Max num instances of corresponding obj_type allowed per item
   def __init__(self, value, text, data_type='UCHAR'):
      EnumeratedValue.__init__(self,value,text)
      self.data_type = _data_types[data_type] # use ref to EnumValue
      return
   ##
   # __new__(): Called only by Python runtime when a new ObjData instance is
   # instanciated.
   def __new__(klass, value, text, data_type='NONE', default=0, max_insts=1, prop_types=None):
      return EnumeratedValue.__new__(klass, value, text)
##
# _props: 2-way tables of UHP Properties that an Object may have.
# @fixme These PropTypes are GUESSED: Usage, Runtime%, EngUnits, BypassTimeUnits. (No CPC Objects seem to use them...)
_props = EnumeratedDictionary([PropData(0,'Value','NONE'), \
                              PropData(1,'Status','UCHAR'),\
                              PropData(2,'Usage','NONE'), \
                              PropData(3,'Runtime','LONG'), \
                              PropData(4,'Runtime%','INT_DIV10'), \
                              PropData(5,'DailyRuntime','UINT'), \
                              PropData(6,'DailyCycles','UINT'), \
                              PropData(7,'Cycles','LONG'), \
                              PropData(8,'LastChange','FUNK_TIME'), \
                              PropData(9,'LogInterval','LONG'), \
                              PropData(10,'Logged','CHAR'), \
                              PropData(11,'EngUnits','LIST_ITEM'), \
                              PropData(12,'Bypass','LIST_ITEM'), \
                              PropData(13,'BypassType','LIST_ITEM'), \
                              PropData(14,'BypassTime','TIME'), \
                              PropData(15,'BypassTimeUnits','LIST_ITEM'), \
                              PropData(16,'BypassValue','NONE'),\
                              PropData(17,'LastTransition','TIME'), \
                              PropData(18,'High/LowValue','NONE')])
##
# class ObjData: Allows use of EnumeratedDictionary for obj_type tables;
# gives us a place to store obj props and max num instances per item.
class ObjData(EnumeratedValue):
   ##
   # __init__():
   # @param value Integer value of ObjData instance
   # @param text Text label associated with given integer value
   # @param data_type String or int rep of data_type of Object's Value Property
   # @param default 1: this Object's value is to be read during autodiscovery, 0: not
   # @param max_insts Max num instances of corresponding obj_type allowed per item
   # @param prop_types IDs of prop_types supported by corresponding obj_type
   def __init__(self, value, text, data_type='UCHAR', default=0, max_insts=1, \
                prop_types=None, num_insts_obj_type_name=None):
      EnumeratedValue.__init__(self,value,text)
      self.max_num_instances = max_insts
      self.num_insts_obj_type_name = num_insts_obj_type_name
      if prop_types is None:
         prop_types = [0]
      self.prop_types = prop_types
      self.default = default
      self.data_type = data_type
      return
   ##
   # __new__(): Called only by Python runtime when a new ObjData instance is
   # instanciated.
   def __new__(klass, value, text, data_type='UCHAR', default=0, max_insts=1, \
               prop_types=None, num_insts_obj_type_name=None):
      return EnumeratedValue.__new__(klass, value, text)
##
# class ItemData: Allows use of EnumeratedDictionary for item_type tables;
# gives us a place to store refs to obj_type tables.
class ItemData(EnumeratedValue):
   ##
   # __init__():
   # @param value Integer value of ItemData instance
   # @param text Text label associated with given integer value
   # @param obj_types Ref to EnumDict of obj_types
   def __init__(self, value, text, obj_types):
      EnumeratedValue.__init__(self, value, text)
      self.obj_types = obj_types
      return
   ##
   # __new__(): Called only by Python runtime when a new ItemData instance is
   # created.
   def __new__(klass, value, text, obj_types):
      return EnumeratedValue.__new__(klass, value, text)
##
# _XXX_yyyy_obj_types: 2-way tables of UHP 
# Objects that a given type of device/item combo ALWAYS has.
_trivial_obj_types = EnumeratedDictionary([ObjData(0,'None','NONE')])

_RMC_Base_obj_types = EnumeratedDictionary( \
                      [ObjData(1,'ID','INT',1), \
                       ObjData(2,'ModelName','SZSTRING',1), \
                       ObjData(3,'Revision','SZSTRING',1), \
                       ObjData(4,'DeviceName','SZSTRING',1), \
                       ObjData(5,'Date','DATE',1), \
                       ObjData(6,'Time','FUNK_TIME',1), \
                       ObjData(7,'Day','UCHAR',1), \
                       ObjData(21,'Passwords','SZSTRING',1), \
                       ObjData(27,'CaseTypes','SZSTRING'), \
                       ObjData(28,'NumberOf8ROs','UCHAR'), \
                       ObjData(29,'NumberOf16AIs','UCHAR'), \
                       ObjData(30,'NumberOfInputs','INT'), \
                       ObjData(62,'TemperatureUnits','LIST_ITEM'), \
                       ObjData(63,'PressureUnits','LIST_ITEM'), \
                       ObjData(80,'Obj80','LIST_ITEM'), \
                       ObjData(127,'SecurityCode','INT'), \
                       ObjData(147,'LogList','NONE')])

_RMC_Alarm_obj_types = EnumeratedDictionary( \
                      [ObjData(1,'GetAlarmRpt','ALARM'), \
                       ObjData(2,'LastId','UINT'), \
                       ObjData(3,'NumAlarms','UCHAR')])

_RMC_Sensor_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(4,'DeviceName','SZSTRING'), \
                       ObjData(10,'Type','LIST_ITEM'), \
                       ObjData(11,'Setpoints','INT'), \
                       ObjData(12,'LogInterval','LONG'), \
                       ObjData(19,'SensorNums','UCHAR',1), \
                       ObjData(130,'SensorValues','INT',1,4,[0,1]), \
                       ObjData(132,'CurrentAlarmOverrideState','NONE')])

_RMC_Power_obj_types = EnumeratedDictionary( \
                      [ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(128,'Status','LIST_ITEM'), \
                       ObjData(129,'CurrentPowerUsage','LONG',1,1,[0,1])])

_RMC_AI_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(10,'Enable','UCHAR',1), \
                       ObjData(11,'Type','LIST_ITEM'), \
                       ObjData(12,'Instance','UINT'), \
                       ObjData(13,'Field','LIST_ITEM'), \
                       ObjData(15,'BoardType','LIST_ITEM'), \
                       ObjData(16,'BoardNumber','UCHAR'), \
                       ObjData(17,'BoardPoint','UCHAR'),
                       ObjData(26,'AlarmLowLimit','INT_DIV10'), \
                       ObjData(27,'AlarmHighLimit','INT_DIV10'), \
                       ObjData(30,'NoticeLowLimit','INT_DIV10'), \
                       ObjData(31,'NoticeHighLimit','INT_DIV10'), \
                       ObjData(48,'LowLimitSetpoint','INT_DIV10'), \
                       ObjData(49,'HighLimitSetpoint','INT_DIV10'), \
                       ObjData(128,'CalcCommandValue','LIST_ITEM',1,1,[0,1,12,13,14]), \
                       ObjData(129,'AnalogOutputValue','LIST_ITEM',1,1,[0,1]), \
                       ObjData(130,'Inputs','INT_DIV10',0,10), \
                       ObjData(131,'OverrideState','LIST_ITEM'), \
                       ObjData(132,'OverrideTimeLeft','INT'), \
                       ObjData(133,'AlarmOutput','LIST_ITEM'), \
                       ObjData(134,'NoticeOutput','LIST_ITEM'), \
                       ObjData(135,'AlarmState','LIST_ITEM',1)])

_RMC_AO_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(128,'PIDOutput','INT_DIV10',1,1,[0,1,12,13,14,16])])

_RMC_DO_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(128,'CommandValue','LIST_ITEM',1,1,[0,1,12,13,14]), \
                       ObjData(134,'DigitalCombinerOutput','LIST_ITEM'), \
                       ObjData(135,'ScheduleInterfaceOutput','LIST_ITEM'), \
                       ObjData(136,'MinOnOffOutput','LIST_ITEM'), \
                       ObjData(137,'ProofSelectorOutput','LIST_ITEM'), \
                       ObjData(138,'TimerOutput','LIST_ITEM'), \
                       ObjData(140,'Status','LIST_ITEM',1)])

_RMC_Pressure_obj_types = EnumeratedDictionary( \
                      [ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(11,'DischargeTripPoint','INT_DIV100',1), \
                       ObjData(14,'DischargeAlarm','LIST_ITEM',1), \
                       ObjData(16,'DischargeAlarmType','LIST_ITEM',1), \
                       ObjData(17,'OilFailAlarmType','LIST_ITEM',1), \
                       ObjData(23,'PhaseLossAlarmType','LIST_ITEM',1), \
                       ObjData(128,'Obj128','LIST_ITEM',1)])

_RMC_Group_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(10,'Strategy','LIST_ITEM'), \
                       ObjData(11,'ControlMethod','LIST_ITEM'), \
                       ObjData(21,'SuctionSetpoint','INT_DIV10'), \
                       ObjData(24,'SuctionAlarmLimits','INT_DIV10',0,2), \
                       ObjData(25,'SuctionAlarmDelays','INT_DIV10',0,2), \
                       ObjData(26,'PumpDownAlarm','INT_DIV10'), \
                       ObjData(29,'SuctionAlarmType','LIST_ITEM'), \
                       #ObjData(30,'CaseAlarmType','LIST_ITEM'), # CPC: "not supported anymore" \
                       ObjData(31,'PumpDownAlarmType','LIST_ITEM'), \
                       ObjData(45,'NumberOfCompressors','UCHAR',1), \
                       ObjData(46,'FirstCompressorNumber','INT',1), \
                       ObjData(128,'Suction','INT_DIV10',1,1,[0,1,10]), \
                       ObjData(129,'SuctionSetpoint','INT_DIV10',0,1,[0,10]), \
                       ObjData(130,'VSPercentage','UINT',0,1,[0,10]), \
                       ObjData(132,'FloatTemp','INT_DIV10',0,1,[0,10]), \
                       ObjData(133,'CaseTemp','INT_DIV10',0,4), \
                       ObjData(135,'SuctionTemp','LIST_ITEM',1,1,[0,1,10]), \
                       ObjData(139,'DefrostInhibit','LIST_ITEM'), \
                       ObjData(150,'DischargePressure','INT_DIV10',1,1,[0,1,10]), \
                       ObjData(151,'DischargeTemperature','INT_DIV10',1,1,[0,1,10]), \
                       ObjData(152,'PhaseLoss','LIST_ITEM',1)])

_RMC_Compressor_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Obj0','SZSTRING'), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(4,'Obj4','UCHAR'), \
                       ObjData(11,'Type','LIST_ITEM'), \
                       ObjData(14,'LowOilPressure','INT_DIV10',1), \
                       ObjData(128,'Status','LIST_ITEM',1,1,[0,1,3,12]), \
                       ObjData(129,'OilPressure','INT_DIV10',1,1,[0,1])])

_RMC_Condenser_obj_types = EnumeratedDictionary( \
                      [ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(10,'Type','LIST_ITEM',1), \
                       ObjData(11,'NumberOfFans','UCHAR',1), \
                       ObjData(130,'Present','LIST_ITEM',1,12), \
                       ObjData(131,'FanStatus','LIST_ITEM',1,12,[0,1],'NumberOfFans'), \
                       ObjData(132,'SplitStatus','LIST_ITEM'), \
                       ObjData(133,'AmbientTemperature','LIST_ITEM',1,1,[0,1]), \
                       ObjData(134,'ReclaimStatus','LIST_ITEM'), \
                       ObjData(135,'InletTemp','INT_DIV10',1,1,[0,1]), \
                       ObjData(136,'OutletTemp','INT_DIV10',1,1,[0,1]), \
                       ObjData(138,'DischargePressure','INT_DIV10',1,2,[0,1]), \
                       ObjData(139,'DischargeTemperature','INT_DIV10',1,2,[0,1]),
                       ObjData(140,'InletPressure','INT_DIV10',1,2,[0,1]), \
                       ObjData(141,'OutletPressure','INT_DIV10',1,2,[0,1]), \
                       ObjData(143,'InverterAlarm','LIST_ITEM'),
                       ObjData(145,'TwoSpeedStatus','INT_DIV10',1,2,[0,1]), \
                       ObjData(147,'VSOutput','INT_DIV10',1,2,[0,1])])

_RMC_Circuit_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(10,'Type','LIST_ITEM',1), \
                       ObjData(11,'DefrostType','LIST_ITEM'), \
                       ObjData(12,'DefrostTermination','LIST_ITEM'), \
                       ObjData(14,'OverrideMode','LIST_ITEM'), \
                       ObjData(17,'OverrideAlarm','LIST_ITEM',1), \
                       ObjData(23,'DemandDefrostMode','LIST_ITEM',1), \
                       ObjData(24,'CaseType','LIST_ITEM',1), \
                       ObjData(29,'ControlTemp','INT_DIV10',1),
                       ObjData(32,'DefrostTimes','FUNK_TIME',1,6),
                       #ObjData(34,'CompressorGroup',UCHAR',1),  # CPC: "not supported anymore"\
                       ObjData(40,'ShutdownGroup','UCHAR'), \
                       ObjData(42,'NumberOfTempSensors','UCHAR',1), \
                       ObjData(43,'NumberOfTermSensors','UCHAR',1), \
                       ObjData(44,'NumberOfDemandSensors','UCHAR'), \
                       ObjData(46,'ExtraOpts','LIST_ITEM'), \
                       ObjData(48,'LiquidLineSolenoid','LIST_ITEM'), \
                       ObjData(54,'InputHighAlarm','INT_DIV10',1), \
                       ObjData(56,'InputLowAlarm','INT_DIV10',1), \
                       ObjData(58,'InputHighNotice','INT_DIV10',1), \
                       ObjData(60,'InputLowNotice','INT_DIV10',1), \
                       ObjData(63,'SuctionGroup','UCHAR',1), \
                       ObjData(128,'Status','LIST_ITEM',1), \
                       ObjData(129,'Refrigeration','LIST_ITEM',1,1,[0,1,3,5,6,7,8,9,10,12]), \
                       ObjData(130,'Defrost','LIST_ITEM',1,1,[0,1,3,5,6,7,8,9,10,12]), \
                       ObjData(131,'CurrentTemp','INT_DIV10',1,1,[0,10]), \
                       ObjData(133,'CaseTemps','INT_DIV10',1,6,[0,1,9,10,16],'NumberOfTempSensors'), \
                       ObjData(134,'Termination','INT_DIV10',1,6,[0,1,9,10,16],'NumberOfTermSensors'), \
                       ObjData(135,'CleaningState','LIST_ITEM',1,1,[0,1,9,10,16]), \
                       ObjData(136,'DemandDefrostState','LIST_ITEM',1,2,[0,1]), \
                       ObjData(137,'Humidity','INT_DIV10',1,1,[0,1,16]), \
                       ObjData(139,'LLS','LIST_ITEM',1,1,[0,1]), \
                       ObjData(142,'CurrentControlSetpoint','INT_DIV10',1)])

_RMC_Case_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(4,'Circuit','UCHAR'), \
                       ObjData(128,'Status','LIST_ITEM'), \
                       ObjData(129,'CaseTemp','INT_DIV10')])

_RMC_LightSchedule_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(128,'Status','LIST_ITEM')])

_RMC_AntiSweat_obj_types = EnumeratedDictionary( \
                      [ObjData(0,'Name','SZSTRING',1), \
                       ObjData(1,'Obj1','INT'), \
                       ObjData(2,'Obj2','BIT_ARRAY'), \
                       ObjData(128,'Output','SZSTRING',1,8,[0,1,12]), \
                       ObjData(130,'Humidity','INT'), \
                       ObjData(131,'Temperature','INT'), \
                       ObjData(132,'Dewpoint','INT')])

_BCU_item_types = EnumeratedDictionary({})

_RMC_item_types = EnumeratedDictionary({'None':ItemData(0,'None',_trivial_obj_types), \
                  'Base':ItemData(1,'Base',_RMC_Base_obj_types), \
                  'Alarm':ItemData(2,'Alarm',_RMC_Alarm_obj_types), \
                  'Sensor':ItemData(3,'Sensor',_RMC_Sensor_obj_types), \
                  'Power':ItemData(4,'Power',_RMC_Power_obj_types), \
                  'AI':ItemData(5,'AI',_RMC_AI_obj_types), \
                  'AO':ItemData(6,'AO',_RMC_AO_obj_types), \
                  'DO':ItemData(7,'DO',_RMC_DO_obj_types), \
                  'Pressure':ItemData(20,'Pressure',_RMC_Pressure_obj_types), \
                  'Group':ItemData(21,'Group',_RMC_Group_obj_types), \
                  'Compressor':ItemData(22,'Compressor',_RMC_Compressor_obj_types), \
                  'Condenser':ItemData(23,'Condenser',_RMC_Condenser_obj_types), \
                  'Circuit':ItemData(24,'Circuit',_RMC_Circuit_obj_types), \
                  'Case':ItemData(25,'Case',_RMC_Case_obj_types), \
                  'LightSchedule':ItemData(26,'LightSchedule',_RMC_LightSchedule_obj_types), \
                  'AntiSweat':ItemData(32,'AntiSweat',_RMC_AntiSweat_obj_types)})

_BEC_item_types = EnumeratedDictionary({})

_device_types = {'BCU':(100,_BCU_item_types), \
               'RMCC':(200,_RMC_item_types), \
               'RMCH':(200,_RMC_item_types), \
               'RMCT':(200,_RMC_item_types), \
               'BEC':(300,_BEC_item_types)}

"""
Copyright (C) 2003 2004 2005 2010 2011 Cisco Systems

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
from mpx.ion.bacnet.object import _Object
from mpx.ion.bacnet.object import BACnetDeviceProperties as _BACnetDeviceProperties
from mpx.ion.bacnet.trane import property

class Area(_Object):
    _object_type = 130
    _node_def_id = '2acc1e0b-6a9d-4fa0-a420-c49e0be3a2b8'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.PriorityArray, # REQUIRED if PresentValue is present and commandable
                            property.RelinquishDefault, # REQUIRED if PresentValue is present and commandable
                            property.Setpoint,
                            property.LastControlDateTime,
                            property.HeatCoolMode,
                            property.UnoccCoolSetpoint,
                            property.OccCoolSetpoint,
                            property.UnoccHeatSetpoint,
                            property.OccHeatSetpoint,
                            property.SpaceSensor
                            ]
    
class Voyager(_Object):
    _object_type = 169
    _node_def_id = 'a9c3173d-3521-4e70-a11f-f87366d0a251'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.PriorityArray, # REQUIRED if PresentValue is present and commandable
                            property.RelinquishDefault, # REQUIRED if PresentValue is present and commandable
                            property.CommState,
                            property.DiagAutoReset,
                            property.InfoWarning,
                            property.DiagManualResetReqd,
                            property.SpaceControlTemp,
                            property.EconomizerDamperPos,
                            property.VoyagerCoolingSetpoint,
                            property.VoyagerHeat1,
                            property.VoyagerHeat2,
                            property.VoyagerCompressor1,
                            property.VoyagerCompressor2,
                            property.VoyagerSupplyFanStatus,
                            property.VoyagerActiveCoolingSetpoint,
                            property.VoyagerActiveHeatingSetpoint,
                            property.VoyagerDamperPositionMinimum,
                            property.IntellipakActiveMode,           #active mode
                            property.IntellipakOccupiedZoneSetpoint, #heating setpoint
                            ]

    
class VariTrane(_Object): #VariTrane UCM II/III/IV
    _object_type = 155
    _node_def_id = '1177df16-e606-4101-8ee5-d3f2f78c713a'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.PriorityArray, # REQUIRED if PresentValue is present and commandable
                            property.RelinquishDefault, # REQUIRED if PresentValue is present and commandable
                            property.CommState,
                            property.VaritraneUnoccupiedHeatingSetpoint,
                            property.VaritraneUnoccupiedCoolingSetpoint,
                            property.VaritraneOccupiedHeatingSetpoint,
                            property.VaritraneOccupiedCoolingSetpoint,
                            property.VaritraneActiveHeatingSetpoint,
                            property.VaritraneActiveCoolingSetpoint,
                            property.VaritraneSeriesFanOutput,
                            property.VaritraneAirValveControl,
                            property.VaritraneAirValveFlow,
                            property.VaritraneAirValvePosition,
                            property.VaritraneSpaceTemperature,
                            property.VaritraneActiveMode,
                            property.VaritraneHeatActive,
                            property.VaritraneDischargeAirTemp,
                            ]

    
class IntelliPak(_Object): #IntelliPak Rooftop
    _object_type = 165
    _node_def_id = '8409242c-d703-41b4-901d-711fde04cdf1'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.PriorityArray, # REQUIRED if PresentValue is present and commandable
                            property.RelinquishDefault, # REQUIRED if PresentValue is present and commandable
                            property.CommState,
                            property.IntellipakSACoolingSetpoint,
                            property.IntellipakMorningWarmupSetpoint,
                            property.IntellipakSAPressureSetpoint,
                            property.IntellipakSpacePressureSetpoint,
                            property.IntellipakOccupiedZoneSetpoint,
                            property.IntellipakActiveMode,
                            property.IntellipakCoolingCapacityInUse,
                            property.IntellipakHeatingCapacityInUse,
                            property.IntellipakSATemperature,
                            property.IntellipakFanIgvVfd,
                            property.IntellipakSpacePressure,
                            property.IntellipakSpaceTemperature,
                            property.IntellipakSAPressure,
                            ]

    
class Schedule(_Object):
    _object_type = 131
    _node_def_id = '5b52542c-5593-4b8d-a0d9-8df2f9671d17'
    _required_properties = [property.ObjectIdentifier, 
                            property.ObjectName, 
                            property.ObjectType,
                            property.PresentValue,
                            property.EffectivePeriod,
                            property.ExceptionSchedule,
                            property.WeeklySchedule,
                            property.UpdateTag,
                            property.SecurityClass,
                            property.MemberList
                            ]

##
# Fixme:  Short term hack to get time and date into BCU
# need to implement optional properites into discovery process

class BACnetDeviceProperties(_BACnetDeviceProperties):
    _required_properties = _BACnetDeviceProperties._required_properties[:] + \
                            [property.LocalDate] + \
                            [property.LocalTime]
    
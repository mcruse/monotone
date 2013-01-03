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
import types
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.node import ConfigurableNode
from mpx.ion.bacnet.property import *
from mpx.ion.bacnet.property import _Property as _Base_Property
from mpx.lib.bacnet.trane.property import _Property as GenericProperty

class _Property(_Base_Property):
    def __init__(self):
        _Base_Property.__init__(self)
        self._generic_property = GenericProperty
    pass

class LastControlDateTime(_Property):
    _node_def_id = 'e6c1d8aa-86fb-438b-bb1b-56837aeb4cb5'
    _server_attribute = 'last_control_date_time'
    _default_ttl = 1
    pass

class HeatCoolMode(_Property):
    _node_def_id = 'd1d80389-6fc0-41a3-9989-6a3ed8ec3954'
    _server_attribute = 'heat_cool_mode'
    _default_ttl = 1
    pass

# SummitPropertyReference_prop: 
class SummitPropertyReference_prop(_Property):
    _default_ttl = 1
    pass
        
class PropAttr(ConfigurableNode):
    def __init__(self, token, editable=0):
        self.token = token
        if editable != 0:
            self.set = self._set
    def get(self, skipCache=0):
        return self.parent._get_attr_value(self.token, skipCache)
    def _set(self, v):
        self.parent._set_attr_value(self.token, v)
        
# SummitObjectConstant_prop: base class for all properties of type
# SummitObjectConstant. Reqd since this type includes three elements:
# mode (int), property_reference(SummitPropertyReference),
# constant_value (any primitive, incl. real, int, unsigned, enumerated):
class SummitObjectConstant_prop(_Property, AutoDiscoveredNode):
    _default_ttl = 1
    def __init__(self):
        _Property.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self._children_have_been_discovered = 1 #fool non-commandable pv 
        self.last_set_exception = None
        self.running = 0
        self.value = None
        self.set = self._set
    def configure(self, cd, identifier=None):
        _Property.configure(self, cd)
        if self.is_server:
            set_attribute(self, 'value', '0.0', cd, float)
    def configuration(self):
        cd = _Property.configuration(self)
        get_attribute(self, 'value', cd, str)
        get_attribute(self, 'last_set_exception', cd, str)
        return cd
    def start(self):
        _Property.start(self)
        self.bacnet_property.value = self.value
        if self.is_server:
            self.set = self._set
        self._children_have_been_discovered = 0 #allow the children to be discovered
        self.running = 1
    def get(self, skipcache=0):
        if self.parent.is_proxy():
            answer = self.parent.get() #go get the linked value
            self.bacnet_property.value = answer
            return self.bacnet_property
        return _Property.get(self, skipcache)
    def _set(self, value, priority=None, asyncOK=1):
        _Property._set(self,value, priority, asyncOK)
        self.set_exception(None)
        if self.parent.is_proxy():
            self.parent.set(self.bacnet_property.value) #set the linked node
    # below is handled by proxy class now but regular server still needs to support it
    def set_exception(self, exception):
        if self.parent.is_proxy(): return #already handled, shouldn't be here
        if self.is_server:
            self.last_set_exception = exception
            self.parent.set_exception(exception)
    def _discover_children(self):
        if self.running:
            if not self._children_have_been_discovered:
                answer = {}
                answer['mode'] = PropAttr('mode')
                #@FIXME: Use a new type of Prop for prop_ref (?): it needs its OWN child nodes...
                answer['property_reference'] = PropAttr('property_reference')
                answer['constant_value'] = PropAttr('constant_value', 1)
                self._nascent_children = answer
                self._children_have_been_discovered = 1
        return self._nascent_children
    def as_tags(self, index=None):
        if self.parent.is_proxy():
            try:
                self.bacnet_property.value = self.parent.get() #which has been subverted
            except Exception, e:
                self.bacnet_property.value = None #leave the property itself alone? 
        return _Property.as_tags(self, index)
    def _get_attr_value(self, token, skipCache):
        # Make sure that the SOC object has current values from the actual device:
        self.bacnet_property.get_result_from(self.parent.parent.instance, skipCache)
        if token == 'mode':
            return self.bacnet_property.value.mode
        elif token == 'property_reference':
            return self.bacnet_property.value.property_reference
        elif token == 'constant_value':
            return self.bacnet_property.value.constant_value
        else:
            raise Exception('Unknown token: %s' % token)
    def _set_attr_value(self, token, v):
        if token == 'constant_value':
            type_v = type(v)
            if (not type_v == types.IntType) and (not type_v == types.LongType) \
               and (not type_v == types.FloatType) and (not type_v == types.StringType):
                raise EInvalidValue('constant_value', v, 'bad type: %s' % str(type_v))
            self.bacnet_property.value = v
        elif (token == 'mode') or (token == 'property_reference'):
            raise EInvalidValue('token', token, \
                                'attempted to write a read-only property attribute')
        else:
            raise EInvalidValue('token', token, \
                                'Must be mode, constant_value, or property_reference')
        if self.is_client: #make it write to the other device
            self.bacnet_property.set(self.parent.parent.instance) # calls SOC_seq.as_tags() indirectly

class UnoccCoolSetpoint(SummitObjectConstant_prop):
    _node_def_id = '83d9acf8-8da0-4a35-98c0-caa233975fe6'
    _server_attribute = 'unocc_cool_setpoint'
    pass

class OccCoolSetpoint(SummitObjectConstant_prop):
    _node_def_id = '6d7af8a6-2705-41c0-ace9-00fbe11e8e07'
    _server_attribute = 'occ_cool_setpoint'
    pass

class UnoccHeatSetpoint(SummitObjectConstant_prop):
    _node_def_id = '0cf4395f-2880-4fd8-8545-07efdbba8f27'
    _server_attribute = 'unocc_heat_setpoint'
    pass

class OccHeatSetpoint(SummitObjectConstant_prop):
    _node_def_id = 'e08e5eaa-0aa2-4a93-a38f-d3c1dceb6cca'
    _server_attribute = 'occ_heat_setpoint'
    pass
class SpaceSensor(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'space_sensor'
    pass
class CommState(_Property):
    _default_ttl = 1
    _node_def_id = 'f624106c-7ea8-4ba8-926b-c058ccd7b91b'
    _server_attribute = 'comm_state'
    pass

class DiagAutoReset(_Property):
    _default_ttl = 1
    _node_def_id = '8305e652-f5dc-4fd4-8c5c-c52f60ca6e6c'
    _server_attribute = 'diag_auto_reset'
    pass

class InfoWarning(_Property):
    _default_ttl = 1
    _node_def_id = 'da16b9f8-391b-4ca3-a027-5ed711b51d87'
    _server_attribute = 'info_warning'
    pass

class DiagManualResetReqd(_Property):
    _default_ttl = 1
    _node_def_id = '851d985a-c072-4bdb-8881-8db67c1061df'
    _server_attribute = 'diag_manual_reset_reqd'
    pass

class SpaceControlTemp(_Property):
    _default_ttl = 1
    _node_def_id = 'd686ffda-94b4-4dae-a338-cefd0565651f'
    _server_attribute = 'space_control_temp'
    pass
class EconomizerDamperPos(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'econimizer_damper_pos'
    pass
class EffectivePeriod(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'effective_period'
    def __init__(self):
        _Property.__init__(self)
        self.last_set_exception = None
        self.running = 0
        self.value = None
    def configure(self, cd, identifier=None):
        _Property.configure(self, cd)
        self.value = [(None, None, None), (None, None, None)]
    def configuration(self):
        cd = _Property.configuration(self)
        get_attribute(self, 'value', cd, list)
        get_attribute(self, 'last_set_exception', cd, str)
        return cd
    def start(self):
        _Property.start(self)
        self.bacnet_property.value = self.value
        self.set = self._set
        self.running = 1
    def get(self, skipcache=0):
        if self.parent.is_proxy():
            answer = self.parent.get() #go get the linked value
            self.bacnet_property.value = answer
            return self.bacnet_property
        return _Property.get(self, skipcache)
    def _set(self, value, priority=None, asyncOK=1):
        _Property._set(self,value, priority, asyncOK)
        self.set_exception(None)
        if self.parent.is_proxy():
            self.parent.set(self.bacnet_property.value) #set the linked node
    # below is handled by proxy class now but regular server still needs to support it
    def set_exception(self, exception):
        if self.parent.is_proxy(): return #already handled, shouldn't be here
        if self.is_server:
            self.last_set_exception = exception
            self.parent.set_exception(exception)
    def as_tags(self, index=None):
        if self.parent.is_proxy():
            try:
                self.bacnet_property.value = self.parent.get() #which has been subverted
            except Exception, e:
                self.bacnet_property.value = None #leave the property itself alone? 
        return _Property.as_tags(self, index)

class ExceptionSchedule(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'exception_schedule'
    def __init__(self):
        _Property.__init__(self)
        self.running = 0
        self.value = None
    def configure(self, cd, identifier=None):
        _Property.configure(self, cd)
        self.value = []
    def start(self):
        _Property.start(self)
        self.bacnet_property.value = self.value
        self.set = self._set
        self.running = 1

class WeeklySchedule(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'weekly_schedule'
    def __init__(self):
        _Property.__init__(self)
        self.last_set_exception = None
        self.running = 0
        self.value = None
    def configure(self, cd, identifier=None):
        _Property.configure(self, cd)
        self.value = []
    def configuration(self):
        cd = _Property.configuration(self)
        get_attribute(self, 'value', cd, list)
        get_attribute(self, 'last_set_exception', cd, str)
        return cd
    def start(self):
        _Property.start(self)
        self.bacnet_property.value = self.value
        self.set = self._set
        self.running = 1
    def get(self, skipcache=0):
        if self.parent.is_proxy():
            answer = self.parent.get() #go get the linked value
            self.bacnet_property.value = answer
            return self.bacnet_property
        return _Property.get(self, skipcache)
    def _set(self, value, priority=None, asyncOK=1):
        _Property._set(self,value, priority, asyncOK)
        self.set_exception(None)
        if self.parent.is_proxy():
            self.parent.set(self.bacnet_property.value) #set the linked node
    # below is handled by proxy class now but regular server still needs to support it
    def set_exception(self, exception):
        if self.parent.is_proxy(): return #already handled, shouldn't be here
        if self.is_server:
            self.last_set_exception = exception
            self.parent.set_exception(exception)
    def as_tags(self, index=None):
        if self.parent.is_proxy():
            try:
                self.bacnet_property.value = self.parent.get() #which has been subverted
            except Exception, e:
                self.bacnet_property.value = None #leave the property itself alone? 
        return _Property.as_tags(self, index)

class UpdateTag(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'update_tag'

class SecurityClass(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'security_class'

class MemberList(_Property):
    _default_ttl = 1
    _node_def_id = 'TBD'
    _server_attribute = 'member_list'

#varitrane
class VaritraneUnoccupiedHeatingSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = 'f0099097-a4d7-45c8-a447-e0f17574af62'
    _server_attribute = 'varitrane_unoccupied_heating_setpoint'
    pass
class VaritraneOccupiedHeatingSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = '1a4964f2-9f3e-4fc3-869d-b976d0c60b31'
    _server_attribute = 'varitrane_occupied_heating_setpoint'
    pass
class VaritraneUnoccupiedCoolingSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = 'a008564a-882c-4a26-b213-c3725ccda377'
    _server_attribute = 'varitrane_unoccupied_cooling_setpoint'
    pass
class VaritraneOccupiedCoolingSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = 'e9a50b23-5595-467c-a9f0-d3f526b1f088'
    _server_attribute = 'varitrane_occupied_cooling_setpoint'
    pass
class VaritraneActiveCoolingSetpoint(_Property):
    _default_ttl = 1
    _node_def_id = '73514c16-914f-4ad7-a5de-dfd1412cb9fa'
    _server_attribute = 'varitrane_active_cooling_setpoint'
    pass
class VaritraneActiveHeatingSetpoint(_Property):
    _default_ttl = 1
    _node_def_id = 'dfb5dcda-c8df-494c-a57b-6c73f6c2fa39'
    _server_attribute = 'varitrane_active_cooling_setpoint'
    pass
class VaritraneSeriesFanOutput(_Property):
    _default_ttl = 1
    _node_def_id = 'e1acf739-b545-4366-84c6-ccde17235d4a'
    _server_attribute = 'varitrane_series_fan_output'
    pass
class VaritraneAirValveControl(_Property):
    _default_ttl = 1
    _node_def_id = '5409d30e-0dba-4da7-8ed3-1fcab5ce1c36'
    _server_attribute = 'varitrane_air_valve_control'
    pass
class VaritraneAirValveFlow(_Property):
    _default_ttl = 1
    _node_def_id = '71a9290b-f6cb-4de6-ace3-cfbcd5799c06'
    _server_attribute = 'varitrane_air_valve_flow'
    pass
class VaritraneAirValvePosition(_Property):
    _default_ttl = 1
    _node_def_id = 'b02317e8-2970-43e9-a0f3-e509ec0730f7'
    _server_attribute = 'varitrane_air_valve_position'
    pass
class VaritraneSpaceTemperature(_Property):
    _default_ttl = 1
    _node_def_id = '6d813f7c-91e7-48f5-b3bf-cfb8c0b84369'
    _server_attribute = 'varitrane_space_temperature'
    pass
class VaritraneActiveMode(_Property):
    _default_ttl = 1
    _node_def_id = 'abec65e4-f92c-4b4e-b86d-20c4d60aa278'
    _server_attribute = 'varitrane_active_mode'
    pass
class VaritraneHeatActive(_Property):
    _default_ttl = 1
    _node_def_id = '880d8a68-b840-4d6d-aa0b-b8d4b64f58cf'
    _server_attribute = 'varitrane_heat_active'
    pass
class VaritraneDischargeAirTemp(_Property):
    _default_ttl = 1
    _node_def_id = 'ac069a65-da40-45d6-a388-afd5330c55e6'
    _server_attribute = 'varitrane_discharge_air_temp'
    pass

class IntellipakSACoolingSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = '0c184880-e4ed-4456-aae9-0ea8bba85a95'
    _server_attribute = 'intellipak_s_a_cooling_setpoint'
    pass
class IntellipakMorningWarmupSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = 'bd765fb7-a6c4-4873-8b1a-0035799c5fe7'
    _server_attribute = 'intellipak_morning_warmup_setpoint'
    pass
class IntellipakSAPressureSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = 'bf7f19e4-7bef-494c-a606-9f8c37d92c5b'
    _server_attribute = 'intellipak_s_a_pressure_setpoint'
    pass
class IntellipakSpacePressureSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = '5288921e-3dc0-4ad3-bdb9-e498e3ba26a4'
    _server_attribute = 'intellipak_space_pressure_setpoint'
    pass
class IntellipakOccupiedZoneSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = '4311f72f-9897-4327-8615-021dc097d821'
    _server_attribute = 'intellipak_occupied_zone_setpoint'
    pass
class IntellipakActiveMode(_Property):
    _default_ttl = 1
    _node_def_id = 'a265192e-64c8-40b7-94c8-abb0ff4ff283'
    _server_attribute = 'intellipak_active_mode'
    pass
class IntellipakCoolingCapacityInUse(_Property):
    _default_ttl = 1
    _node_def_id = '6fdd7f3c-8b48-431d-bbb5-db2d06d52f2e'
    _server_attribute = 'intellipak_cooling_capacity_in_use'
    pass
class IntellipakHeatingCapacityInUse(_Property):
    _default_ttl = 1
    _node_def_id = '6d341c8b-6efe-4e43-ac8a-eb2dd00daf6a'
    _server_attribute = 'intellipak_heating_capacity_in_use'
    pass
class IntellipakSATemperature(_Property):
    _default_ttl = 1
    _node_def_id = '679a432f-add4-4bbc-a93f-a8d7124b1057'
    _server_attribute = 'intellipak_s_a_temperature'
    pass
class IntellipakFanIgvVfd(_Property):
    _default_ttl = 1
    _node_def_id = 'ce1a0ee3-f38d-429f-bb41-5ebff23f8447'
    _server_attribute = 'intellipak_fan_igv_vfd'
    pass
class IntellipakSpacePressure(_Property):
    _default_ttl = 1
    _node_def_id = '7dfbd36c-7df3-4970-ab4f-6e80c7dba8a9'
    _server_attribute = 'intellipak_space_pressure'
    pass
class IntellipakSpaceTemperature(_Property):
    _default_ttl = 1
    _node_def_id = '154292d5-d629-429f-84ce-2d1de6ae538a'
    _server_attribute = 'intellipak_space_temperature'
    pass
class IntellipakSAPressure(_Property):
    _default_ttl = 1
    _node_def_id = 'e3363198-7dda-4bd7-a38b-1005deafc6c2'
    _server_attribute = 'intellipak_s_a_pressure'
    pass
class VoyagerCoolingSetpoint(SummitObjectConstant_prop):
    _default_ttl = 1
    _node_def_id = '295c0838-d698-4993-ad13-9880d956d144'
    _server_attribute = 'voyager_cooling_setpoint'
    pass
class VoyagerHeat1(_Property):
    _default_ttl = 1
    _node_def_id = '93c6f401-d920-47a2-9feb-4d4dda842bcf'
    _server_attribute = 'voyager_heat_1'
    pass
class VoyagerHeat2(_Property):
    _default_ttl = 1
    _node_def_id = '37a786ed-f4b2-40a2-8548-425296a92f7c'
    _server_attribute = 'voyager_heat_2'
    pass
class VoyagerCompressor1(_Property):
    _default_ttl = 1
    _node_def_id = '058e029b-fd55-4a97-859a-c63541a886bd'
    _server_attribute = 'voyager_compressor_1'
    pass
class VoyagerCompressor2(_Property):
    _default_ttl = 1
    _node_def_id = 'aa9f39fc-aff9-4b4a-939c-7b8b89113abd'
    _server_attribute = 'voyager_compressor_2'
    pass
class VoyagerSupplyFanStatus(_Property):
    _default_ttl = 1
    _node_def_id = '83d23db2-16fa-4f4e-b10f-d09eb4afa958'
    _server_attribute = 'voyager_supply_fan_status'
    pass
class VoyagerActiveCoolingSetpoint(_Property):
    _default_ttl = 1
    _node_def_id = 'b433ba64-f7eb-4049-b986-69c301b379ec'
    _server_attribute = 'voyager_active_cooling_setpoint'
    pass
class VoyagerActiveHeatingSetpoint(_Property):
    _default_ttl = 1
    _node_def_id = 'd4682ad1-4ef5-4d36-a910-72243fade931'
    _server_attribute = 'voyager_active_heating_setpoint'
    pass
class VoyagerDamperPositionMinimum(_Property):
    _default_ttl = 1
    _node_def_id = '874d34b9-e610-40c3-83e6-eb28cff530e9'
    _server_attribute = 'voyager_damper_position_minimum'
    pass

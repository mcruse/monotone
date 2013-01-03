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
##
# @todo Implement.  PASSWRD, USRSTR, STRCMD and LOGOFF.  (LOGOFF.set(0) == mop,
# set(1) == LOGOFF, get() == PSSWRD.is_protect())
# @todo Everything else.

from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.exceptions import EInvalidValue, EInvalidResponse

from mpx.ion.capstone.micro_turbine import command
from mpx.ion.capstone.micro_turbine.cache import RO_CommandCache
from mpx.ion.capstone.micro_turbine.cache import SingleValueCommand

##
# Cache a RO_CommandCache.CommandION using the name as the method
# name to apply to the ALLDAT sub-response.
def _cache_roc_by_name(cache, response_base, name):
    cache.map_child(name, response_base + name)

def _get_password_mode(response):
    return response.mode()

def _set_password(capstone_ion,password_ion,password,asyncOK):
    psswrd = command.PSSWRD(capstone_ion.turbine,password)
    response = capstone_ion.line_handler.command(psswrd)
    if response.is_base():
        raise EInvalidResponse, ('mode', self.mode())

def _get_will_start(response):
    return response.will_start()

##
# @fixme Use the turbine's password if it exists.
# @fixme Validate the responses from the commands.
# @fixme Most of the run commands should be configurable.
def _set_run(capstone_ion,password_ion,value,asyncOK):
    turbine = capstone_ion.turbine
    if value == 1:
        # Start running...
        utlcon = command.UTLCON(turbine,2)
        medbtu = command.MEDBTU(turbine,1)
        autrst = command.AUTRST(turbine,1)
        strcmd = command.STRCMD(turbine,1)
        response = capstone_ion.line_handler.command(utlcon)
        response = capstone_ion.line_handler.command(medbtu)
        response = capstone_ion.line_handler.command(autrst)
        response = capstone_ion.line_handler.command(strcmd)
    elif value == 0:
        strcmd = command.STRCMD(turbine,0)
        response = capstone_ion.line_handler.command(strcmd)
    else:
        raise EInvalidValue, ('run',value)

class Personality(CompositeNode):
    def _create_single_children(self):
        SingleValueCommand(self, 'password', command.PSSWRD(self.turbine),
                           _get_password_mode, _set_password)
        SingleValueCommand(self, 'run', command.STRCMD(self.turbine),
                           _get_will_start, _set_run)
        cache = RO_CommandCache(self, self.line_handler,
                                command.SYSSSL(self.turbine))
        response_base = 'self.cached_response().'
        _cache_roc_by_name(cache, response_base, 'system_severity_level')
        cache = RO_CommandCache(self, self.line_handler,
                                command.SYSSTA(self.turbine))
        response_base = 'self.cached_response().'
        _cache_roc_by_name(cache, response_base, 'current_system_state_string')
        cache = RO_CommandCache(self, self.line_handler,
                                command.WARNTY(self.turbine))
        response_base = 'self.cached_response().'
        _cache_roc_by_name(cache, response_base, 'hours_of_operation')
        _cache_roc_by_name(cache, response_base, 'start_events')
    def _create_lmdata_cache(self):
        cache = RO_CommandCache(self, self.line_handler,
                                command.LMDATA(self.turbine))
        response_base = 'self.cached_response().'
        _cache_roc_by_name(cache, response_base, 'run_stop_signal')
        _cache_roc_by_name(cache, response_base, 'positive_power')
        _cache_roc_by_name(cache, response_base, 'negative_power')
        _cache_roc_by_name(cache, response_base, 'positive_kvars')
        _cache_roc_by_name(cache, response_base, 'negative_kvars')
    def _create_alldat_cache(self):
        cache = RO_CommandCache(self, self.line_handler,
                                command.ALLDAT(self.turbine))
        #
        # @todo response_base = 'self.cached_response().batdat_response().'
        #
        response_base = 'self.cached_response().bcdat1_response().'
        _cache_roc_by_name(cache, response_base, 'battery_temperature')
        #
        response_base = 'self.cached_response().ctrldt_response().'
        _cache_roc_by_name(cache, response_base, 'system_configuration_state')
        _cache_roc_by_name(cache, response_base, 'power_enable')
        _cache_roc_by_name(cache, response_base, 'power_demand')
        _cache_roc_by_name(cache, response_base, 'power_supply')
        _cache_roc_by_name(cache, response_base, 'start_command')
        #
        response_base = 'self.cached_response().engdt1_response().'
        _cache_roc_by_name(cache, response_base, 'year')
        _cache_roc_by_name(cache, response_base, 'month')
        _cache_roc_by_name(cache, response_base, 'day')
        _cache_roc_by_name(cache, response_base, 'hour')
        _cache_roc_by_name(cache, response_base, 'minutes')
        _cache_roc_by_name(cache, response_base, 'seconds')
        _cache_roc_by_name(cache, response_base, 'engine_rpm')
        _cache_roc_by_name(cache, response_base, 'tet_average')
        _cache_roc_by_name(cache, response_base, 'compressor_inlet_temp')
        _cache_roc_by_name(cache, response_base, 'ambient_pressure')
        #
        response_base = 'self.cached_response().engdt2_response().'
        _cache_roc_by_name(cache, response_base, 'fault_ident')
        _cache_roc_by_name(cache, response_base, 'system_severity_level')
        #
        # @todo response_base = 'self.cached_response().gendt1_response().'
        # @todo response_base = 'self.cached_response().gendt2_response().'
        #
        response_base = 'self.cached_response().invdt1_response().'
        _cache_roc_by_name(cache, response_base, 'ac_frequency')
        _cache_roc_by_name(cache, response_base, 'phase_A_current_rms')
        _cache_roc_by_name(cache, response_base, 'phase_B_current_rms')
        _cache_roc_by_name(cache, response_base, 'phase_C_current_rms')
        #
        response_base = 'self.cached_response().invdt2_response().'
        _cache_roc_by_name(cache, response_base, 'neutral_current_rms')
        _cache_roc_by_name(cache, response_base, 'phase_AN_voltage_rms')
        _cache_roc_by_name(cache, response_base, 'phase_BN_voltage_rms')
        _cache_roc_by_name(cache, response_base, 'phase_CN_voltage_rms')
        _cache_roc_by_name(cache, response_base, 'phase_A_power_average')
        _cache_roc_by_name(cache, response_base, 'phase_B_power_average')
        _cache_roc_by_name(cache, response_base, 'phase_C_power_average')
        _cache_roc_by_name(cache, response_base, 'total_power_average')
        #
        # @todo response_base = 'self.cached_response().lfcdat_response().'
        # @todo response_base = 'self.cached_response().mlockd_response().'
        #
        response_base = 'self.cached_response().rfcdat_response().'
        _cache_roc_by_name(cache, response_base, 'rfc_fuel_inlet_pressure')
        #
        response_base = 'self.cached_response().spvdat_response().'
        _cache_roc_by_name(cache, response_base, 'fuel_inlet_pressure')
    def __init__(self):
        CompositeNode.__init__(self)
        self._configured_caches = 0
    def configure(self, cd):
        CompositeNode.configure(self,cd)
        self.line_handler = self.parent
        set_attribute(self, 'turbine', REQUIRED, cd, int)
        set_attribute(self, 'password', None, cd)
        if not self._configured_caches:
            self._create_alldat_cache()
            self._create_single_children()
            self._create_lmdata_cache()
            self._configured_caches = 1
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'turbine', config, str)
        get_attribute(self, 'password', config)
        return config

def factory():
    return Personality()

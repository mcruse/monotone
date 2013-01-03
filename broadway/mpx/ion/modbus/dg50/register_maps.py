"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
# TODO:
# 1.  Implement write methods where appropriate.
# 2.  Writing to will require a read/write, or implementing the Modbus
#     masking commands (which the DG50 probably does not support).
from mpx.lib.modbus.response import ReadHoldingRegisters
from mpx.lib.modbus.cache_writer import CacheWriter

class RegisterDescription:
    def __init__(self, offset, count, name, unbound_read,
                 unbound_write=None, comment=''):
        self.offset  = offset
        self.count   = count
        self.name    = name
        self.read    = unbound_read	# self == response.ReadHoldingRegisters
        self.write   = unbound_write	# self == CacheWriter
        self.comment = comment

map1 = []
map1.append(RegisterDescription(0x0000, 1, 'oil_press_l',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'low oil pressure warning'))
map1.append(RegisterDescription(0x0000, 1, 'oil_press_s',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'low oil pressure shutdown'))
map1.append(RegisterDescription(0x0001, 1, 'coolant_temp_h',
                                ReadHoldingRegisters.register_hibyte,
                                None,
                                'high coolant temperature warning'))
map1.append(RegisterDescription(0x0001, 1, 'coolant_temp_s',
                                ReadHoldingRegisters.register_lobyte,
                                None,
                                'high coolant temperature shutdown'))
map1.append(RegisterDescription(0x0002, 1, 'coolant_temp_l',
                                ReadHoldingRegisters.register_hibyte,
                                None,
                                'low coolant temperature warning'))
map1.append(RegisterDescription(0x0002, 1, 'oil_temp_h',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'high oil temperature warning'))
map1.append(RegisterDescription(0x0003, 1, 'oil_temp_s',
                                ReadHoldingRegisters.register_hibyte,
                                None,
                                'high oil temperature shutdown'))
map1.append(RegisterDescription(0x0003, 1, 'batt_volts_l',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'low battery voltage warning'))
map1.append(RegisterDescription(0x0004, 1, 'batt_volts_h',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'high battery voltage warning'))
map1.append(RegisterDescription(0x0004, 1, 'rpm_s',
                                ReadHoldingRegisters.register_lobyte,
                                None,
                                'overspeed (high rpm) shutdown'))
map1.append(RegisterDescription(0x0005, 1, 'rpm_l',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'underspeed (low rpm) warning'))
map1.append(RegisterDescription(0x0005, 1, 'gen_volts_h',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'overvoltage shutdown'))
map1.append(RegisterDescription(0x0006, 1, 'gen_volts_l',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'undervoltage shutdown'))
map1.append(RegisterDescription(0x0006, 1, 'freq_h',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'over frequency shutdown'))
map1.append(RegisterDescription(0x0007, 1, 'freq_l',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'under frequency shutdown'))
map1.append(RegisterDescription(0x0007, 1, 'fuel_level_h',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'high fuel level warning'))
map1.append(RegisterDescription(0x0008, 1, 'fuel_level_l',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'low fuel level warning'))
map1.append(RegisterDescription(0x0008, 1, 'fuel_level_s',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'low fuel level shutdown'))
map1.append(RegisterDescription(0x0009, 1, 'inter_comm_f',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'internal error shutdown'))
map1.append(RegisterDescription(0x0009, 1, 'fail_start_s',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'over-crank shutdown'))
map1.append(RegisterDescription(0x000a, 1, 'water_level_s',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'coolant level sensor failed'))
map1.append(RegisterDescription(0x000a, 1, 'rpm_sens_s',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'rpm sensor failed'))
map1.append(RegisterDescription(0x000b, 1, 'start_inhibit_n',
                                ReadHoldingRegisters.register_hibyte,
                                None,
                                'start inhibited due to oil press.'))
map1.append(RegisterDescription(0x000b, 1, 'emstop_s',
                                ReadHoldingRegisters.register_lobyte,
                                None, 'emergency stop shutdown'))
map1.append(RegisterDescription(0x000c, 1, 'oil_press_f',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'oil pressure sensor failed'))
map1.append(RegisterDescription(0x000c, 1, 'oil_temp_f',
                                ReadHoldingRegisters.register_lobyte,
                                None,
                                'oil temperature sensor failed'))
map1.append(RegisterDescription(0x000d, 1, 'coolant_temp_f',
                                ReadHoldingRegisters.register_hibyte,
                                None,
                                'coolant temperature sensor failed'))
map1.append(RegisterDescription(0x000d, 1, 'engine_run_status',
                                ReadHoldingRegisters.register_lobyte))
map1.append(RegisterDescription(0x000e, 1, 'engine_running',
                                ReadHoldingRegisters.register_hibyte,
                                None, 'shows if engine running'))
map1.append(RegisterDescription(0x000e, 1, 'system_status',
                                ReadHoldingRegisters.register_lobyte))
map1.append(RegisterDescription(0x000f, 1, 'oil_press',
                                ReadHoldingRegisters.register_as_int))
map1.append(RegisterDescription(0x0010, 1, 'rpm',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0011, 1, 'freq',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0012, 1, 'oil_temp',
                                ReadHoldingRegisters.register_as_int))
map1.append(RegisterDescription(0x0013, 1, 'fuel_level',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0014, 1, 'coolant_temp',
                                ReadHoldingRegisters.register_as_int))
map1.append(RegisterDescription(0x0015, 1, 'batt_volts',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0016, 1, 'gen_voltsA',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0017, 1, 'gen_voltsB',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0018, 1, 'gen_voltsC',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0019, 1, 'power',
                                ReadHoldingRegisters.register_hibyte))
map1.append(RegisterDescription(0x0019, 1, 'power_factor',
                                ReadHoldingRegisters.register_lobyte))
map1.append(RegisterDescription(0x001a, 1, 'load_amps',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x001b, 1, 'util_volts',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x001c, 1, 'util_freq',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x001d, 1, 'gen_amps',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x001e, 1, 'Transfer_error_no',
                                ReadHoldingRegisters.register_as_loint))
# hi struct Dispctrl_bit Dispctrl       001e
# hi struct RS232_bit RS232_bitstr      001f
# lo struct Output_bit Output           001f
# hi union PORTA_store_bit PORTA_store  0020
# lo union PORTB_store_bit PORTB_store  0020
# hi union PORTP_store_bit PORTP_store  0021
# lo union PORTT_store_bit PORTT_store  0021
# union Alarm_bitaddr Alarm          	0022
# hi union AVR_23_bit AVR_23            0023
# lo union AVR_01_bit AVR_01            0023
map1.append(RegisterDescription(0x0024, 1, 'hours_run',
                                ReadHoldingRegisters.register_as_long))
# struct mbstart_bit mb_start        	0026    READ AND WRITE ACCESS
map1.append(RegisterDescription(0x0027, 1, 'ps_kw',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0028, 1, 'ps_pf',
                                ReadHoldingRegisters.register_as_word))
map1.append(RegisterDescription(0x0029, 1, 'reset_genlink',
                                ReadHoldingRegisters.register_hibyte))
map1.append(RegisterDescription(0x002a, 1, 'parallel_en',
                                ReadHoldingRegisters.register_hibyte,
                                CacheWriter.write_hibyte))
map1.append(RegisterDescription(0x002b, 1, 'modem_disconnect',
                                ReadHoldingRegisters.register_as_word))

#
# Editors notes:
# The following locations are setpoints in EEprom and are the
# Stored parameters which are not lost when power is removed.
# (Settings such as  cooldown time etc) The parameters have both
# READ AND WRITE ACCESS.
#
# The following naming conventions are used.
# Variables with a _lsp extension are low setpoints	
# Variables with a _hsp extension are high setpoints	
# Variables with a _ssp extension are shutdown setpoints	
#

map2 = []
# ReadHoldingRegisters.register_as_long, hours_run_ep[6]
# NOT ACCESSIBLE FROM MODBUS
map2.append(RegisterDescription(0x0100, 1, 'start_attempts',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0101, 1, 'pause_time',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0102, 1, 'cool_time',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0103, 1, 'warm_time',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0104, 1, 'hold_off_time',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0105, 1, 'mbus_spare1',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0106, 1, 'mbus_spare2',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0107, 1, 'start_time',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0108, 1, 'rpm_started',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0109, 1, 'preheat_time',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x010a, 1, 'fuel_level_lsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x010b, 1, 'fuel_level_hsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x010c, 1, 'gen_volts_lsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x010d, 1, 'gen_volts_hsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x010e, 1, 'rpm_lsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x010f, 1, 'rpm_ssp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0110, 1, 'batt_volts_hsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0111, 1, 'batt_volts_lsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0112, 1, 'oil_temp_ssp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0113, 1, 'oil_temp_hsp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0114, 1, 'coolant_temp_ssp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0115, 1, 'coolant_temp_hsp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0116, 1, 'coolant_temp_lsp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0117, 1, 'oil_press_ssp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0118, 1, 'oil_press_lsp',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0119, 1, 'flywheel_teeth',
                                ReadHoldingRegisters.register_as_word))
#    /* I *ASSUME* these are strings. */
#    (enum modbus_register_type)(STRING | 8),
#				'userpwd',		0x011a, '',
#    (enum modbus_register_type)(STRING | 8),
#				'panel_id',		0x011e, '',
map2.append(RegisterDescription(0x0122, 1, 'avr_droop_gain',
                                ReadHoldingRegisters.register_hibyte))
map2.append(RegisterDescription(0x0122, 1, 'avr_droop_select',
                                ReadHoldingRegisters.register_lobyte))
map2.append(RegisterDescription(0x0123, 1, 'avr_stability',
                                ReadHoldingRegisters.register_hibyte))
map2.append(RegisterDescription(0x0123, 1, 'avr_gain',
                                ReadHoldingRegisters.register_lobyte))
map2.append(RegisterDescription(0x0124, 1, 'avr_sensing',
                                ReadHoldingRegisters.register_hibyte))
map2.append(RegisterDescription(0x0124, 1, 'avr_freq',
                                ReadHoldingRegisters.register_lobyte))
map2.append(RegisterDescription(0x0125, 1, 'gov_gain',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0126, 1, 'gov_diff',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0127, 1, 'avr_uf_slope',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0128, 1, 'avr_uf_corner',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0129, 1, 'avr_vsetpt',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x012a, 1, 'avr_pf',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x012b, 1, 'avr_kw',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x012c, 1, 'modem_sel',
                                ReadHoldingRegisters.register_hibyte))
map2.append(RegisterDescription(0x012c, 1, 'gov_stability',
                                ReadHoldingRegisters.register_lobyte))
map2.append(RegisterDescription(0x012d, 1, 'preheat_en',
                                ReadHoldingRegisters.register_hibyte))
map2.append(RegisterDescription(0x012d, 1, 'transfer_en',
                                ReadHoldingRegisters.register_lobyte))
map2.append(RegisterDescription(0x012e, 1, 'ct_ratio',
                                ReadHoldingRegisters.register_as_hiint))
map2.append(RegisterDescription(0x012e, 1, 'avr_spare4',
                                ReadHoldingRegisters.register_as_loint))
map2.append(RegisterDescription(0x012f, 1, 'freq_hsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0130, 1, 'freq_lsp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0131, 1, 'fuel_level_ssp',
                                ReadHoldingRegisters.register_as_word))
map2.append(RegisterDescription(0x0132, 1, 'screen_en',
                                ReadHoldingRegisters.register_hibyte))
map2.append(RegisterDescription(0x0132, 1, 'fuel_level_en',
                                ReadHoldingRegisters.register_lobyte))
map2.append(RegisterDescription(0x0133, 1, 'gvscale',
                                ReadHoldingRegisters.register_as_int))
map2.append(RegisterDescription(0x0134, 1, 'avr_vscale',
                                ReadHoldingRegisters.register_as_int))
#    /* (alarm log is read only) 0135 - 015d */
#     * (enum modbus_register_type)(UNSIGNED WORD ARRAY | 0x0029),
#     *				'alarm_log',		0x0135, '',
#     *
#     * eeprom char modbus_id              slave address    NOT ACCESSIBLE
#     * eeprom char RS232_baud             RS232 baud rate  NOT ACCESSIBLE
#     * eeprom char RS232_mode             RS232 comms mode NOT ACCESSIBLE
#     * eeprom char RS485_baud             RS485 baud rate  NOT ACCESSIBLE
#     * eeprom char RS485_mode             RS485 comms mode NOT ACCESSIBLE
#     */

register_maps = [(map1, 1.0), (map2, 1.0)]
del map1
del map2

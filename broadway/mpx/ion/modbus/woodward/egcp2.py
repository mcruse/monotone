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
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.ion.modbus.woodward import BooleanWrite,BooleanRead,AnalogWrite,AnalogRead

_register_map = {1:(BooleanWrite,'auto_bw',1),
                 2:(BooleanWrite,'test_bw',1),
                 3:(BooleanWrite,'run_with_load_bw',1),
                 4:(BooleanWrite,'voltage_raise_bw',1),
                 5:(BooleanWrite,'voltage_lower_bw',1),
                 6:(BooleanWrite,'speed_raise_bw',1),
                 7:(BooleanWrite,'speed_lower_bw',1),
                 8:(BooleanWrite,'process_ie_bw',1),
                 9:(BooleanWrite,'fault_1_bw',1),
                 10:(BooleanWrite,'fault_2_bw',1),
                 11:(BooleanWrite,'fault_3_bw',1),
                 12:(BooleanWrite,'fault_4_bw',1),
                 13:(BooleanWrite,'fault_5_bw',1),
                 14:(BooleanWrite,'fault_6_bw',1),
                 15:(BooleanWrite,'unused_bw',1),
                 16:(BooleanWrite,'commit_alarms_bw',1),
                 
                 10001:(BooleanRead, 'mains_pt_transition_br',1),
                 10002:(BooleanRead, 'mains_stable_br',1),
                 10003:(BooleanRead, 'bus_stable_br',1),
                 10004:(BooleanRead, 'alarm_status_br',1),
                 10005:(BooleanRead, 'loss_of_mains_br',1),
                 10006:(BooleanRead, 'mains_brk_closed_br',1),
                 10007:(BooleanRead, 'gen_brk_closed_br',1),
                 10008:(BooleanRead, 'engine_preglow_br',1),
                 10009:(BooleanRead, 'fuel_solenoid_br',1),
                 
                 10010:(BooleanRead, 'engine_crank_br',1),
                 10011:(BooleanRead, 'visual_alarm_br',1),
                 10012:(BooleanRead, 'bus_pt_connect_br',1),
                 10013:(BooleanRead, 'mains_pt_disconnect_br',1),
                 10014:(BooleanRead, 'mains_brk_trip_br',1),
                 10015:(BooleanRead, 'gen_brk_trip_br',1),
                 
                 10016:(BooleanRead, 'audible_alarm_br',1),
                 10017:(BooleanRead, 'idle_or_ready_br',1),
                 10018:(BooleanRead, 'auto_br',1),
                 10019:(BooleanRead, 'test_br',1),
                 10020:(BooleanRead, 'run_with_load_br',1),
                 
                 10021:(BooleanRead, 'voltage_raise_br',1),
                 10022:(BooleanRead, 'voltage_lower_br',1),
                 10023:(BooleanRead, 'speed_raise_br',1),
                 10024:(BooleanRead, 'speed_lower_br',1),
                 10025:(BooleanRead, 'get_cb_aux_br',1),
                 
                 10026:(BooleanRead, 'mains_cb_aux_br',1),
                 10027:(BooleanRead, 'process_ie_br',1),
                 10028:(BooleanRead, 'fault_1_br',1),
                 10029:(BooleanRead, 'fault_2_br',1),
                 10030:(BooleanRead, 'fault_3_br',1),
                 
                 10031:(BooleanRead, 'fault_4_br',1),
                 10032:(BooleanRead, 'fault_5_br',1),
                 10033:(BooleanRead, 'fault_6_br',1),
                 10034:(BooleanRead, 'sync_timeout_br',1),
                 10035:(BooleanRead, 'sync_reclose_br',1),
                 
                 10036:(BooleanRead, 'crank_fail_br',1),
                 10037:(BooleanRead, 'voltage_range_br',1),
                 10038:(BooleanRead, 'overspeed_br',1),
                 10039:(BooleanRead, 'overcurrent_br',1),
                 10040:(BooleanRead, 'reverse_power_br',1),
                 
                 10041:(BooleanRead, 'loss_of_excitation_br',1),
                 10042:(BooleanRead, 'speed_freq_mismatch_br',1),
                 10043:(BooleanRead, 'h20_high_limit_br',1),
                 10044:(BooleanRead, 'h2-_low_limit_br',1),
                 10045:(BooleanRead, 'oil_press_high_limit_br',1),
                 
                 10046:(BooleanRead, 'oil_pressure_low_limit_br',1),
                 10047:(BooleanRead, 'batt_volt_low_limit_br',1),
                 10048:(BooleanRead, 'batt_volt_high_limit_br',1),
                 10049:(BooleanRead, 'gen_volt_low_limit_br',1),
                 10050:(BooleanRead, 'gen_volt_high_limit_br',1),
                 
                 10051:(BooleanRead, 'gen_freq_high_limit_br',1),
                 10052:(BooleanRead, 'gen_freq_low_limit_br',1),
                 10053:(BooleanRead, 'load_high_limit_br',1),
                 10054:(BooleanRead, 'load_low_limit_br',1),
                 10055:(BooleanRead, 'process_high_limit_br',1),
                 
                 10056:(BooleanRead, 'process_low_limit_br',1),
                 10057:(BooleanRead, 'remote_fault_1_br',1),
                 10058:(BooleanRead, 'remote_fault_2_br',1),
                 10059:(BooleanRead, 'remote_fault_3_br',1),
                 10060:(BooleanRead, 'remote_fault_4_br',1),
                 
                 10061:(BooleanRead, 'remote_fault_5_br',1),
                 10062:(BooleanRead, 'remote_fault_6_br',1),
                 10071:(BooleanRead, 'pf_leading_or_lagging_br',1),
                 
                 30001:(AnalogRead, 'battery_voltage_ar',.1),
                 30002:(AnalogRead, 'engine_oil_pressure_ar',.1),
                 30003:(AnalogRead, 'engine_coolant_temp_ar',1),
                 30004:(AnalogRead, 'engine_run_time_ar',1),
                 30005:(AnalogRead, 'engine_kw_per_hours_ar',1),
                 
                 30006:(AnalogRead, 'engine_rpm_ar',1),
                 30007:(AnalogRead, 'phase_a_volts_ar',1),
                 30008:(AnalogRead, 'phase_b_volts_ar',1),
                 30009:(AnalogRead, 'phase_c_volts_ar',1),
                 30010:(AnalogRead, 'total_kw_ar',1),
                 
                 30011:(AnalogRead, 'total_kva_ar',1),
                 30012:(AnalogRead, 'generator_power_factor_ar',.01),
                 30013:(AnalogRead, 'phase_a_kVAR_ar',1),
                 30014:(AnalogRead, 'phase_b_kVAR_ar',1),
                 30015:(AnalogRead, 'phase_c_kVAR_ar',1),
                 
                 30016:(AnalogRead, 'total_kVAR_ar',1),
                 30017:(AnalogRead, 'bus_out_freq_ar',.1),
                 30018:(AnalogRead, 'gen_out_freq_ar',.1),
                 30019:(AnalogRead, 'network_address_ar',1),
                 30020:(AnalogRead, 'sync_timeout_ar',1),
                 
                 30021:(AnalogRead, 'sync_reclose_ar',1),
                 30022:(AnalogRead, 'crank_fail_ar',1),
                 30023:(AnalogRead, 'voltage_range_ar',1),
                 30024:(AnalogRead, 'overspeed_ar',1),
                 30025:(AnalogRead, 'overcurrent_ar',1),
                 
                 30026:(AnalogRead, 'reverse_power_ar',1),
                 30027:(AnalogRead, 'loss_of_excitation_ar',1),
                 30028:(AnalogRead, 'speed_freq_mismatch_ar',1),
                 30029:(AnalogRead, 'h20_high_limit_ar',1),
                 30030:(AnalogRead, 'h20_low_limit_ar',1),
                 
                 30031:(AnalogRead, 'oil_press_high_limit_ar',1),
                 30032:(AnalogRead, 'oil_press_low_limit_ar',1),
                 30033:(AnalogRead, 'batt_volt_low_limit_ar',1),
                 30034:(AnalogRead, 'batt_volt_high_limit_ar',1),
                 30035:(AnalogRead, 'gen_volt_low_limit_ar',1),
                 
                 30036:(AnalogRead, 'gen_volt_high_limit_ar',1),
                 30037:(AnalogRead, 'gen_freq_high_limit_ar',1),
                 30038:(AnalogRead, 'gen_freq_low_limit_ar',1),
                 30039:(AnalogRead, 'load_high_limit_ar',1),
                 30040:(AnalogRead, 'load_low_limit_ar',1),
                 
                 30041:(AnalogRead, 'process_low_limit_ar',1),
                 30042:(AnalogRead, 'process_high_limit_ar',1),
                 30043:(AnalogRead, 'remote_fault_1_ar',1),
                 30044:(AnalogRead, 'remote_fault_2_ar',1),
                 30045:(AnalogRead, 'remote_fault_3_ar',1),
                 
                 30046:(AnalogRead, 'remote_fault_4_ar',1),
                 30047:(AnalogRead, 'remote_fault_5_ar',1),
                 30048:(AnalogRead, 'remote_fault_6_ar',1),
                 30049:(AnalogRead, 'load_surge_alarm_ar',1),
                 30050:(AnalogRead, 'mains_volt_low_limit_ar',1),
                 
                 30051:(AnalogRead, 'mains_volt_high_limit_ar',1),
                 30052:(AnalogRead, 'mains_freq_high_limit_ar',1),
                 30053:(AnalogRead, 'mains_freq_low_limit_ar',1),
                 30054:(AnalogRead, 'gen_phase_a_neutral_volts_ar',1),
                 30055:(AnalogRead, 'gen_phase_b_neutral_volts_ar',1),
                 
                 30056:(AnalogRead, 'gen_phase_c_neutral_volts_ar',1),
                 30057:(AnalogRead, 'mains_bus_phase_a_neutral_volts_ar',1),
                 30058:(AnalogRead, 'phase_a_current_ar',1),
                 30059:(AnalogRead, 'phase_b_current_ar',1),
                 30060:(AnalogRead, 'phase_c_current_ar',1),
                 
                 30061:(AnalogRead, 'phase_a_kva_ar',1),
                 30062:(AnalogRead, 'phase_b_kva_ar',1),
                 30063:(AnalogRead, 'phase_c_kva_ar',1),
                 30064:(AnalogRead, 'voltage_bias_analog_out_ar',1),
                 30065:(AnalogRead, 'speed_bias_analog_out_ar',1),
                 
                 30066:(AnalogRead, 'load_control_mode_ar',1),
                 30067:(AnalogRead, 'synchronizer_mode_ar',1),
                 30068:(AnalogRead, 'unacknowledged_alarm_count_ar',1),
                 30069:(AnalogRead, 'unit_network_priority_ar',1),
                 30070:(AnalogRead, 'address_of_master_ar',1),
                 
                 30071:(AnalogRead, 'unused_ar',1),
                 30072:(AnalogRead, 'engine_state_ar',1),
                 30073:(AnalogRead, 'synchroscope_phase_angle_ar',1),
                 
                 40001:(AnalogWrite, 'priority_change_address_aw',1)}

class EGCP2(CompositeNode):
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'address', REQUIRED, config, int)
        set_attribute(self, 'line_handler', self.parent, config, as_node)
        for key in _register_map:
            node = _register_map[key][0]()
            node.configure({'parent':self,'register':key,'name':_register_map[key][1],'multiplier':_register_map[key][2]})

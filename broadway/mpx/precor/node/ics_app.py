"""
Copyright (C) 2003 2004 2006 2010 2011 Cisco Systems

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
# mpx.precor.node.ics_app: This file implements high-level classes and functions
# for the ICS (InSite Control System) Application that runs on a CSAFE-enabled
# Mediator Framework.
 
import types, time, array, struct, os, StringIO, threading as _threading, urllib as _urllib
from mpx import properties
from mpx.lib import msglog, urllib, threading, sgml_formatter, socket
from mpx.lib.exceptions import ENoSuchName, ETimeout, ENoData, EConnectionError
from mpx.lib.node import CompositeNode
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.event import EventConsumerMixin, ChangeOfValueEvent
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.persistent import PersistentDataObject
from mpx.lib import datetime
from mpx.lib.scheduler import scheduler
from mpx.lib.node import as_node
from xml import sax
from mpx.precor.node import _xml, session_data_formatter
from mpx.lib.aerocomm import aero
from mpx.ion.aerocomm import aerocomm, csafe, feu
from mpx.service.logger import log, column
from mpx.lib.log import _log
from mpx.service.data import periodic_exporter, http_post_transporter
from mpx.system import system
from mpx.precor.node.local_view import LocalView

##
# Flashing LED constants
#
# When everything is working OK, the LED stays ON all the time (bad choice, I feel it show have a pattern)
# A single flash indicates that the Aerocomm transceiver is not working
# A double flash indicates that the Internet connections is not working to the enterprise system
# A triple flash indicates both errors are present
# A continuous rapid flash indicates the system is unconfigured or is about to get a new configuration

_LED_UNCONFIGURED = 0x55
_LED_OK = 0xFF
_LED_BAD_RADIO = 0x01    # 0000 0001
_LED_BAD_INTERNET = 0x14 # 0001 0100
_LED_NO_CONFIG_IN_SVR = 0x64
_LED_REALLY_BAD   = 0X15 # 0001 0101
_LED_SCANNING = 0
_RADIO_LOSS_TO_FORCED_SESSION_CLOSE = 300 #seconds

##
# _proc_XXXX(): PropAttr-specific processing of obtained values.
#
def _proc_Trivial(ics_app, unit_conf, value):
    return
def _proc_Program(ics_app, unit_conf, pgm_data):
    if (pgm_data is None) or (pgm_data.program == 0):
        return
    unit_conf.program_code = pgm_data.program
    return
def _proc_Version(ics_app, unit_conf, version_data):
    if version_data is None:
        return
    if not unit_conf.version_data is None:
        if (unit_conf.version_data.manufacturer != version_data.manufacturer):
            ics_app._post_AlarmsMsg_input_list.put((1007, unit_conf,))
        if (unit_conf.version_data.CID != version_data.CID):
            ics_app._post_AlarmsMsg_input_list.put((1008, unit_conf,))
    if (type(unit_conf.model_number) != types.IntType) \
        or (unit_conf.model_number != version_data.model):
        ics_app._post_AlarmsMsg_input_list.put((1009, unit_conf,))
    unit_conf.version_data = version_data
    return
def _proc_Serial_Number(ics_app, unit_conf, value):
    #if value != unit_conf.serial_number:
        #ics_app._post_AlarmsMsg_input_list.put((1002, unit_conf,))
    return
def _proc_Odometer(ics_app, unit_conf, value):
    if value is None:
        return
    if value < unit_conf.last_odometer:
        ics_app._post_AlarmsMsg_input_list.put((1000, unit_conf,))
    unit_conf.last_odometer = value
    return
def _proc_Utilization(ics_app, unit_conf, value):
    if value is None:
        return
    now = time.time()
    since_last = now - unit_conf.last_utilization_time
    if (value < unit_conf.last_utilization) \
        or (value > (unit_conf.last_utilization + since_last)):
        ics_app._post_AlarmsMsg_input_list.put((1001, unit_conf,))
    unit_conf.last_utilization = value
    unit_conf.last_utilization_time = now
    return
def _proc_Error_Code(ics_app, unit_conf, value):
    return
def _proc_CalcData(prop, value):
    if value is None:
        return
    if prop.run_total is None:
        prop.num_samples = 1.0 # enforce float ops, not int
        prop.run_total = value
        prop.max = value
        prop.last_sample_time = time.time()
    else:
        if value > prop.max:
            prop.max = value
        prop.num_samples += 1.0 # enforce float ops, not int
        prop.run_total = prop.run_total + value
        period = time.time() - prop.last_sample_time
        if (prop.max_period is None) \
            or (period > prop.max_period):
            prop.max_period = period
        if (prop.min_period is None) \
            or (period < prop.min_period):
            prop.min_period = period
        if prop.run_avg_period is None:
            prop.run_avg_period = period
        else:
            prop.run_avg_period = (prop.run_avg_period + period) / (prop.num_samples - 1)
    return
def _proc_Speed(ics_app, unit_conf, value):
    _proc_CalcData(unit_conf.speed, value)
    return
def _proc_Grade(ics_app, unit_conf, value):
    _proc_CalcData(unit_conf.grade, value)
    return
def _proc_Gear(ics_app, unit_conf, value):
    _proc_CalcData(unit_conf.gear, value)
    return
def _proc_Power(ics_app, unit_conf, value):
    _proc_CalcData(unit_conf.power, value)
    return
def _proc_Status(ics_app, unit_conf, value):
    if value is None:
        unit_conf.feu_data_loss = 1
        if unit_conf.radio_loss == 0: # if ONLY the data is lost, post alarm:
            ics_app._post_AlarmsMsg_input_list.put((1011, unit_conf,))
    return
##
# _get_XXXX(): Functions process and collect required data.
#
def _get_duration(unit_conf):
    time_of_day = unit_conf.feu_node.get_child('Workout_Time').get(0)
    if time_of_day is None:
        return None
    return float(time_of_day)  # minimize work to be done by logger: convert to string now
def _get_program(unit_conf):
    pgm_lvl_data = unit_conf.feu_node.get_child('Program').get(0) # returns a CSafeProgramLevelData instance
    if pgm_lvl_data is None:
        return None
    return pgm_lvl_data.program              # 1-byte program code (2nd (unused) byte in list is level)
def _get_dist_horizontal(unit_conf):
    hdist = unit_conf.feu_node.get_child('Horizontal_Distance').get(0) # returns a CSafeUnitData instance
    if hdist is None:
        return None
    return hdist.value              # 2-byte distance number
def _get_dist_horizontal_unit(unit_conf):
    hdist = unit_conf.feu_node.get_child('Horizontal_Distance').get(0) # returns a CSafeUnitData instance
    if hdist is None:
        return None
    return int(hdist.units)              # 1-byte distance unit code
def _get_dist_vertical(unit_conf):
    vdist = unit_conf.feu_node.get_child('Vertical_Distance').get(0) # returns a CSafeUnitData instance
    if vdist is None:
        return None
    return vdist.value              # 2-byte distance number
def _get_dist_vertical_unit(unit_conf):
    vdist = unit_conf.feu_node.get_child('Vertical_Distance').get(0) # returns a CSafeUnitData instance
    if vdist is None:
        return None
    return int(vdist.units)              # 1-byte distance unit code
def _get_odometer_end(unit_conf):
    odo = unit_conf.feu_node.get_child('Odometer').get(0) # returns a CSafeUnitData instance
    if odo is None:
        return None
    return odo.value
def _get_odometer_end_unit(unit_conf):
    odo = unit_conf.feu_node.get_child('Odometer').get(0) # returns a CSafeUnitData instance
    if odo is None:
        return None
    return int(odo.units)              # 1-byte distance unit code
def _get_hour_meter_end(unit_conf):
    hours = unit_conf.feu_node.get_child('Utilization').get(0)
    return hours                    # 3-byte num hours
def _get_avg_speed(unit_conf):
    if (unit_conf.speed.num_samples is None):
        return None
    return unit_conf.speed.run_total/unit_conf.speed.num_samples
def _get_speed_unit(unit_conf):
    speed = unit_conf.feu_node.get_child('Speed').get(0) # returns a CSafeUnitData instance
    if speed is None:
        return None
    return int(speed.units)             # 1-byte speed unit code
def _get_avg_incline(unit_conf):
    if (unit_conf.grade.num_samples is None):
        return None
    return unit_conf.grade.run_total/unit_conf.grade.num_samples
def _get_incline_unit(unit_conf):
    incline = unit_conf.feu_node.get_child('Grade').get(0) # returns a CSafeUnitData instance
    if incline is None:
        return None
    return int(incline.units)             # 1-byte incline unit code
def _get_avg_resistance(unit_conf):
    if (unit_conf.gear.num_samples is None):
        return None
    return unit_conf.gear.run_total/unit_conf.gear.num_samples
def _get_avg_user_power(unit_conf):
    if (unit_conf.power.num_samples is None):
        return None
    return unit_conf.power.run_total/unit_conf.power.num_samples
def _get_user_power_unit(unit_conf):
    power = unit_conf.feu_node.get_child('Power').get(0) # returns a CSafeUnitData instance
    if power is None:
        return None
    return int(power.units)             # 1-byte user-power unit code
def _get_calories(unit_conf):
    calories = unit_conf.feu_node.get_child('Calories').get(0)
    return calories
def _get_user_weight(unit_conf):
    user_data = unit_conf.feu_node.get_child('User_Information').get(0) # returns a CSafeUserData instance
    if user_data is None:
        return None
    return user_data.value
def _get_user_weight_unit(unit_conf):
    user_data = unit_conf.feu_node.get_child('User_Information').get(0) # returns a CSafeUserData instance
    if user_data is None:
        return 'None'
    return int(user_data.units)
def _get_user_age(unit_conf):
    user_data = unit_conf.feu_node.get_child('User_Information').get(0) # returns a CSafeUserData instance
    if user_data is None:
        return None
    return user_data.age
def _get_user_gender(unit_conf):
    user_data = unit_conf.feu_node.get_child('User_Information').get(0) # returns a CSafeUserData instance
    if user_data is None:
        return None
    return user_data.gender
def _get_user_max_heart_rate(unit_conf):
    max_hr = unit_conf.feu_node.get_child('Maximum_HR').get(0)
    if max_hr is None:
        return None
    return max_hr
def _get_user_avg_heart_rate(unit_conf):
    avg_hr = unit_conf.feu_node.get_child('Average_HR').get(0)
    if avg_hr is None:
        return None
    return avg_hr
def _get_time_in_hr_zone(unit_conf):
    time_of_day = unit_conf.feu_node.get_child('Time_in_HR_Zone').get(0)
    if time_of_day is None:
        return None
    return float(time_of_day)

##
# class IcsAppSvcNode: Implements ICS functionality (ie communication of 
# data updates from FEU/CSAFE Stack to Enterprise Server ("InSite").
# One instance created by Commissioning Tool, ConfigTool, or manually in broadway.xml.
# Instance is child of /services node, with name "Precor_ICS".
def _mirror_url(alt_ip, alt_port, url_tail):
        pass
                        
class IcsAppSvcNode(CompositeNode, EventConsumerMixin, AutoDiscoveredNode):
    _prop_value_procs = { \
                'Version'             :_proc_Version,
                'Serial_Number'       :_proc_Serial_Number,
                'Utilization'         :_proc_Utilization,
                'Odometer'            :_proc_Odometer,
                'Error_Code'          :_proc_Error_Code,
                'Workout_Time'        :_proc_Trivial,
                'Horizontal_Distance' :_proc_Trivial,
                'Vertical_Distance'   :_proc_Trivial,
                'Calories'            :_proc_Trivial,
                'Program'             :_proc_Program,
                'Speed'               :_proc_Speed,
                'Grade'               :_proc_Grade,
                'Gear'                :_proc_Gear,
                'User_Information'    :_proc_Trivial,
                'Current_Heart_Rate'  :_proc_Trivial,
                'Time_in_HR_Zone'     :_proc_Trivial,
                'Power'               :_proc_Power,
                'Average_HR'          :_proc_Trivial,
                'Maximum_HR'          :_proc_Trivial,
                'Status'              :_proc_Status,
                }
    _session_data = [ \
                            ['unit-mac-address', lambda unit: str(unit.unit_mac_address)],
                            ['session-start-time', lambda unit: unit.session_start_time],
                            ['session-end-time', lambda unit: time.time()],
                            ['session-duration', _get_duration],
                            ['program-code', lambda unit: unit.program_code],
                            ['distance-horizontal', _get_dist_horizontal],
                            ['distance-horizontal-unit', _get_dist_horizontal_unit],
                            ['distance-vertical', _get_dist_vertical],
                            ['distance-vertical-unit', _get_dist_vertical_unit],
                            ['odometer-end', _get_odometer_end],
                            ['odometer-end-unit', _get_odometer_end_unit],
                            ['hour-meter-end', _get_hour_meter_end],
                            ['max-speed', lambda unit: unit.speed.max],
                            ['avg-speed', _get_avg_speed],
                            ['speed-unit', _get_speed_unit],
                            ['max-incline', lambda unit: unit.grade.max],
                            ['avg-incline', _get_avg_incline],
                            ['incline-unit', _get_incline_unit],
                            ['max-resistance', lambda unit: unit.gear.max],
                            ['avg-resistance', _get_avg_resistance],
                            ['max-user-power', lambda unit: unit.power.max],
                            ['avg-user-power', _get_avg_user_power],
                            ['user-power-unit', _get_user_power_unit],
                            ['calories', _get_calories],
                            ['user-weight', _get_user_weight],
                            ['user-weight-unit', _get_user_weight_unit],
                            ['user-age', _get_user_age],
                            ['user-gender', _get_user_gender],
                            ['user-max-heart-rate', _get_user_max_heart_rate],
                            ['user-avg-heart-rate', _get_user_avg_heart_rate],
                            ['time-in-hr-zone', _get_time_in_hr_zone],
                            ['radio-loss', lambda unit: unit.radio_loss],
                            ['feu-data-loss', lambda unit: unit.feu_data_loss],
                            ]
    def __init__(self):
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self, self._event_handler)
        #fgd
        AutoDiscoveredNode.__init__(self)
        self._children_have_been_discovered = 0
        self.enable_local_view = 1
        #/fgd
        self.debug_lvl = 0
        self._running = 0
        self._aero_server_node = None
        # Post AlarmsMsg Thread:
        self._post_AlarmsMsg_thread_inst = None
        self._post_AlarmsMsg_thread_go = 1
        self._post_AlarmsMsg_input_list = threading.Queue()
        # Scan Data Thread:
        self._scan_data_sid = None
        self._scan_data_thread_inst = None
        self._scan_data_input_list = threading.Queue()
        self._scan_data_thread_go = 1
        # Send Heartbeat Thread:
        self._send_Heartbeat_sid = None
        self._send_Heartbeat_thread_inst = None
        self._send_Heartbeat_input_list = threading.Queue()
        self._send_Heartbeat_thread_go= 1
        # Handle Events Thread:
        self._event_handler_thread_inst = None
        self._event_handler_thread_go = 1
        self._event_handler_input_list = threading.Queue()
        #
        self._ics_conf = None
        self._subscribed_nodes = []
        self._log = None
        self.actual_ser_num = properties.SERIAL_NUMBER
        # Prepare outgoing Enterprise msg templates:
        self._last_alarms_msg_sent_time = 0.0 # it's been awhile...
        self._cur_alarms_msg = _xml.AlarmsMsg()
        self._cur_alarms_msg.ics_serial_id = self.actual_ser_num
        self._alarms_interval_min_sid = None
        self._hb = _xml.Heartbeat()
        self._hb.ics_serial_id = self.actual_ser_num
        self._hb.sequence_number = 0
        #fgd
        self._flashing_led_node = None
        self._flashing_led_radio_status = 0
        self._flashing_led_internet_status = 1
        self._flashing_led_scanning_status = 0
        #/fgd
        self._ppp_node = None
        return
    def configure(self, cd):
        cd['name'] = 'Precor_ICS' # get rid of any numeric suffixes added during CompositeNode.configure()
        CompositeNode.configure(self, cd)
        set_attribute(self,'aero_server_com_port','com1',cd,str)        # eventually, allow multiple COM ports to support AeroServers...
        set_attribute(self,'aero_server_com_port_baud_rate',57600,cd,int)
        set_attribute(self,'aero_server_relay','relay1',cd,str)         # eventually, allow multiple relays to support AeroServers...
        set_attribute(self,'scan_period',60,cd,int)             # seconds between data scans
        set_attribute(self,'ent_ip_addr','10.0.10.53',cd,str)    # Enterprise server's IP address
        set_attribute(self,'ent_ip_port',18080,cd,int)          # Enterprise server's IP port
        set_attribute(self,'ent_url_conf','configuration',cd,str)            # full URL: http://<EntServerBase>/<ent_url_conf>?ics_serial_id=<sn>
        set_attribute(self,'ent_url_heartbeat','heartbeat',cd,str)       # full URL: http://<EntServerBase>/<ent_url_heartbeat>?ics_serial_id=<sn>
        set_attribute(self,'ent_url_session_data','session_data',cd,str) # full URL: http://<EntServerBase>/<ent_url_session_data>?ics_serial_id=<sn>
        set_attribute(self,'ent_url_alarm','alarm',cd,str)                   # full URL: http://<EntServerBase>/<ent_alarm>?ics_serial_id=<sn>
        set_attribute(self,'conf_file_path','/var/mpx/config/persistent/ics_config.xml',cd,str) # path to XML ICS Config file
        set_attribute(self,'max_num_cur_alarms',100,cd,int)  # max num instances of Alarm allowed in cur AlarmsMsg object's list
        set_attribute(self,'__node_id__','4a32e527-3657-4293-b3ce-236cc0ce3e21',cd, str)  # allows dyn node creation
        set_attribute(self,'enable_local_view', self.enable_local_view, cd, int) #true to discover and start local view service
        set_attribute(self,'alt_ip_addr','',cd,str)    # Envenergys server's IP address
        set_attribute(self,'alt_ip_port','28080',cd,str)          # Envenergys server's IP port
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self,'aero_server_com_port',cd,str)     # eventually, allow multiple COM ports to support AeroServers...
        get_attribute(self,'aero_server_com_port_baud_rate',cd,str)
        get_attribute(self,'aero_server_relay',cd,str)        # eventually, allow multiple relays to support AeroServers...
        get_attribute(self,'scan_period',cd,str)        # seconds between data scans
        get_attribute(self,'ent_ip_addr',cd,str)        # Enterprise server's IP address
        get_attribute(self,'ent_ip_port',cd,int)        # Enterprise server's IP port
        get_attribute(self,'ent_url_conf',cd,str)         # full URL: http://<EntServerBase>/<ent_url_conf>?ics_serial_id=<sn>
        get_attribute(self,'ent_url_heartbeat',cd,str)    # full URL: http://<EntServerBase>/<ent_url_heartbeat>?ics_serial_id=<sn>
        get_attribute(self,'ent_url_session_data',cd,str) # full URL: http://<EntServerBase>/<ent_url_session_data>?ics_serial_id=<sn>
        get_attribute(self,'ent_url_alarm',cd,str)            # full URL: http://<EntServerBase>/<ent_alarm>?ics_serial_id=<sn>
        get_attribute(self,'conf_file_path',cd,str)     # path to XML ICS Config file
        get_attribute(self,'max_num_cur_alarms',cd,int)  # max num instances of Alarm allowed in cur AlarmsMsg object's list
        get_attribute(self,'__node_id__',cd,str)
        get_attribute(self,'enable_local_view',cd,int)
        get_attribute(self,'alt_ip_addr',cd,str)        # Envenergy server's IP address
        get_attribute(self,'alt_ip_port',cd,str)        # Envenergy server's IP port
        get_attribute(self,'_ics_conf',cd,str)
        return cd
    #fgd
    def _discover_children(self):
        if self.enable_local_view and self._running and not self._children_have_been_discovered: #empty
            self.debug_print('ICS_App discover children')
            self._children_have_been_discovered = 1
            answer = {}
            existing_names = self.children_names(auto_discover=0)
            if 'Local_View' not in existing_names:
                answer['Local_View'] = LocalView()
            return answer
        return self._nascent_children
    #/fgd
    def _open_ppp(self):
        if self._ppp_node is None:
            return 0
        msglog.log('mpx:ics',msglog.types.INFO,'Opening PPP conn...')
        try:
            self._ppp_node.acquire()
        except ETimeout:
            msglog.log('mpx:ics',msglog.types.ERR,'Failed to open PPP connection: timeout.')
            return -1
        except Exception, e:
            msglog.log('mpx:ics',msglog.types.ERR,'Failed to open PPP connection: %s.' % str(e))
            return -1
        msglog.log('mpx:ics',msglog.types.INFO,'Opened PPP conn.')
        return 0
    def _close_ppp(self):
        if self._ppp_node is None:
            return
        try:
            msglog.log('mpx:ics',msglog.types.INFO,'Closing PPP conn...')
            self._ppp_node.release()
            msglog.log('mpx:ics',msglog.types.INFO,'Closed PPP conn.')
        except Exception, e:
            msglog.log('mpx:ics',msglog.types.INFO,'Failed to close PPP conn: %s' %  str(e))
        return
    def start(self):
        # @todo REMOVE THIS TEST CODE AFTER DEBUG OF PPP DIALOUT LOCKUP!!!
        #from mpx.precor.node.test_ppp_dialout import TestPppDialout
        #tpd = TestPppDialout()
        #cd = {'parent':'/services', 'name':'TestPppDialout'}
        #tpd.configure(cd)
        #tpd.start()
        #if 1:
            #return
        # @@@ END TEST CODE
        self._flash_led(_LED_UNCONFIGURED)
        try:
            self._ppp_node = as_node('/interfaces/modem/ppp0/outgoing')
            if (self._ppp_node.enable == 0) or (self._ppp_node.enabled == 0):
                self._ppp_node = None
        except ENoSuchName:
            pass
        self._load_config()
        # Create and start Post AlarmsMsg Thread (to gather alarms for xmssn to Enterprise):
        self._post_AlarmsMsg_input_list = threading.Queue()
        self._post_AlarmsMsg_thread_go = 1
        self._post_AlarmsMsg_thread_inst = threading.ImmortalThread(None, self._post_AlarmsMsg_thread)
        self._post_AlarmsMsg_thread_inst.start()
        # Create and start Handle Event Thread (to handle events for which
        # this IcsAppSvcNode has subscribed):
        self._event_handler_thread_go = 1
        self._event_handle_input_list = threading.Queue()
        self._event_handler_thread_inst = threading.ImmortalThread(None, self._event_handler_thread)
        self._event_handler_thread_inst.start()
        # Create and start Scan Data Thread (to scan FEU and child PropAttr 
        # nodes for data):
        self._scan_data_input_list = threading.Queue()
        self._scan_data_thread_go = 1
        self._scan_data_thread_inst = threading.ImmortalThread(None, self._scan_data_thread)
        self._scan_data_thread_inst.start()
        # Create and start Send Heartbeat Thread (to send heartbeat msgs to 
        # Enterprise, and to download config files from Enterprise):
        self._send_Heartbeat_input_list = threading.Queue()
        self._send_Heartbeat_thread_go = 1
        self._send_Heartbeat_thread_inst = threading.ImmortalThread(None, self._send_Heartbeat_thread)
        self._send_Heartbeat_thread_inst.start()
        #
        self._create_node_subtree()
        self._create_log()
        # Wait for feu.feu_poll_thread to be alive:
        timeout = 180.0
        end_time = time.time() + timeout
        while not feu.feu_poll_thread.isAlive():
            if time.time() >= end_time:
                self._stop_all_threads() # do SOME cleanup
                msglog.log('mpx:ics',msglog.types.ERR,'FEU module thread failed to start within %u seconds. ' \
                           'IcsAppSvcNode start() failed.' % timeout)
                return
            time.sleep(1.0)
        # Setup Scheduler to kick off regular scan data polling:
        self._scan_data_sid = scheduler.every(self.scan_period, self._handle_scan_data_wakeup)
        # Setup Scheduler to kick off regular heartbeat update deliveries:
        self._send_Heartbeat_sid = scheduler.every(self._ics_conf.heartbeat_interval, self._handle_send_Heartbeat_wakeup)
        CompositeNode.start(self)
        self._running = 1
        return
    def stop(self):
        self._running = 0
        self._stop_all_threads()
        ##
        # @todo Remove auto-created nodes (eg logger, aeroserver, LocalView child, etc.),
        # to prevent "Already Exists" errors at next call on start(). OR
        # simply check for node pre-existence during start. Reconfig if
        # nodes already exist.
        #
        CompositeNode.stop(self)
        return
    def _stop_all_threads(self):
        for node in self._subscribed_nodes:
            node.event_unsubscribe(self, ChangeOfValueEvent)
        if not self._scan_data_sid is None:
            scheduler.cancel(self._scan_data_sid)
            self._heartbeat_sid = None
        if not self._send_Heartbeat_sid is None:
            scheduler.cancel(self._send_Heartbeat_sid)
            self._heartbeat_sid = None
        if not self._alarms_interval_min_sid is None:
            scheduler.cancel(self._alarms_interval_min_sid)
            self._alarms_interval_min_sid = None
        self._send_Heartbeat_thread_inst.should_die()
        self._send_Heartbeat_thread_go = 0
        self._send_Heartbeat_input_list.put(1) # dummy "object" (an int) is put into Q to notify _send_Heartbeat_thread_inst
        self._send_Heartbeat_thread_inst = None
        self._scan_data_thread_inst.should_die()
        self._scan_data_thread_go = 0
        self._scan_data_input_list.put(1) # dummy "object" (an int) is put into Q to notify _scan_data_thread_inst
        self._scan_data_thread_inst = None
        self._event_handler_thread_inst.should_die()
        self._event_handler_thread_go = 0
        self._event_handler_input_list.put(1) # dummy "object" (an int) is put into Q to notify event_handler_thread_inst
        self._event_handler_thread_inst = None
        self._post_AlarmsMsg_thread_inst.should_die()
        self._post_AlarmsMsg_thread_go = 0
        self._post_AlarmsMsg_input_list.put((None,None,)) # dummy "object" (a 2-tuple) is put into Q to notify _send_AlarmsMsg_thread_inst
        self._post_AlarmsMsg_thread_inst = None
        return
    def _load_config(self):
        ##
        # Try to open, load, and parse config from XML file:
        config_xml_file = None
        try:
            config_xml_file = open(self.conf_file_path, 'r')
        except IOError, e:
            if e.errno != 2: # NOT "No such file or directory"
                raise
            else:
                if properties.HARDWARE_CLASS != 'Unknown':
                    os.system('cp /usr/lib/broadway/mpx/precor/node/ics_config_def.xml %s' \
                              % self.conf_file_path)
                else:
                    print os.getcwd()
                    rtn = os.system('cp mpx/precor/node/ics_config_def.xml %s' \
                              % self.conf_file_path)
                    print rtn
                    # At this point, any exception goes all the way up:
                    config_xml_file = open(self.conf_file_path, 'r')
                # At this point, any exception goes all the way up:
                config_xml_file = open(self.conf_file_path, 'r')
        ch = _xml.ContentHandler()
        sax.parse(config_xml_file, ch)
        self._ics_conf = ch.get_top_tag_obj() # rtns instance of IcsConfig
        # Compare given Mediator Serial Number with actual:
        if self.actual_ser_num != self._ics_conf.ics_serial_id:
            # @todo Send alarm 1006 to Enterprise: Ent thinks this Mediator is someone else...
            msglog.log('mpx',msglog.types.ERR,'Enterprise sent config data for ' \
                            'Mediator %s, but I am %s.' \
                            % (self._ics_conf.ics_serial_id, self.actual_ser_num))
        return
    def _create_node_subtree(self):
        # Create AeroServer node, and use config info from Enterprise to create
        # AeroClient and FEU kids. So, there will be exactly one node for every
        # FEU spec'd by Enterprise. In addition, the low-level driver will
        # discover any Client/FEU pairs NOT spec'd by Enterprise, and will create
        # nodes for those as well:
        port_node = as_node('/interfaces/%s' % self.aero_server_com_port)
        port_node.baud = self.aero_server_com_port_baud_rate # init before aerocomm_server child calls parent.open()
        self._aero_server_node = aerocomm.AerocommServer()
        cd = {'parent':port_node,'name':'aerocomm_server', \
                'relay_node':'/interfaces/%s' % self.aero_server_relay, \
                'discovery_mode':'Always'}
        try:
            self._aero_server_node.configure(cd)
        except Exception, e:
            msglog.log('mpx',msglog.types.ERR,'Failed to configure AerocommServer node under %s:' \
                            % self.aero_server_com_port)
            msglog.exception()
            return
        # Create inherent children (eeprom_params, server_status):
        eeprom_params_node = aerocomm.EEPromParametersGroup()
        cd = {'parent':self._aero_server_node,'name':'eeprom_params'}
        eeprom_params_node.configure(cd)
        for node_name in aerocomm.EEPromParametersGroup._inherent_child_names:
            param_node = aerocomm.EEPromParameter()
            cd = {'parent':eeprom_params_node,'name':node_name}
            param_node.configure(cd)
        server_status_node = aerocomm.StatusGroup()
        cd = {'parent':self._aero_server_node,'name':'server_status'}
        server_status_node.configure(cd)
        for node_name in aerocomm.StatusGroup._inherent_child_names:
            point_node = aerocomm.StatusPoint()
            cd = {'parent':server_status_node,'name':node_name}
            point_node.configure(cd)
        self._aero_server_node.start() # starts all children nodes too; allows _discover_children() to run
        self._aero_server_node.event_subscribe(self, ChangeOfValueEvent)
        self._subscribed_nodes.append(self._aero_server_node)
        for unit in self._ics_conf.units:
            mac_addr = aero.MacAddress(unit.unit_mac_address)
            self._aero_server_node.add_device(mac_addr, 'from_config')
        # Force creation/config/start of nodes from AerocommServer.active_devices data:
        aerocomm_server_kids = self._aero_server_node.children_nodes() 
        for client_node in aerocomm_server_kids:
            if not isinstance(client_node, aerocomm.AerocommClient):
                continue
            client_node.event_subscribe(self, ChangeOfValueEvent)
            self._subscribed_nodes.append(client_node)
            client_kids = client_node.children_nodes()
            units_map = self._ics_conf.get_units_map()
            for feu_node in client_kids:
                if not isinstance(feu_node, feu.FEU):
                    continue
                feu_node.children_nodes() # force autodiscovery of FEU properties
                mac_address_str = str(feu_node.parent.mac_address)
                if units_map.has_key(mac_address_str): # subscribe ONLY to nodes for config'd FEUs:
                    feu_node.event_subscribe(self, ChangeOfValueEvent)
                    self._subscribed_nodes.append(feu_node)
                    units_map[mac_address_str].feu_node = feu_node # link unit_conf to feu_node
                break
        return
    def _create_exporter(self, name, ip, port, parent):
        periodic_exporter_node = periodic_exporter.PeriodicExporter()
        http_post_transporter_node = http_post_transporter.HTTPPostTransporter()
        post_url = 'http://%s:%u/%s?ics_serial_id=%s' \
                % (ip, port, self.ent_url_session_data, \
                    self.actual_ser_num) 
        cd = {'parent':periodic_exporter_node,'name':'http_post_transporter', \
                'post_url':post_url,'content_type':'text/xml','chunked_data':1, \
                'timeout':30.0}
        http_post_transporter_node.configure(cd)
        formatter_node = session_data_formatter.SessionDataFormatter(self.actual_ser_num)
        cd = {'parent':periodic_exporter_node,'name':'session_data_formatter'}
        formatter_node.configure(cd)
        ##
        # @note Seconds portion of session_update_start_timeofday is discarded
        # for compatibility with PeriodicExporter's "synchronize_on" attr:
        #
        sync_on_str = time.strftime('%H:%M',time.gmtime(self._ics_conf.session_upload_start_timeofday))
        time_tuple = time.gmtime(self._ics_conf.session_upload_interval) # NO MORE THAN 28 DAYS!
        conn_node = '/services/network'
        if not self._ppp_node is None:
            conn_node = '/interfaces/modem/ppp0/outgoing'
        cd = {'parent':parent,'name':name, \
                'synchronize_on':sync_on_str,'days':(time_tuple[2]-1), \
                'hours':time_tuple[3], 'minutes':time_tuple[4], \
                'seconds':time_tuple[5],'milliseconds':0.0, \
                'connection_node':conn_node}
        periodic_exporter_node.configure(cd)
        
    def _create_log(self):
        logger_node = as_node('/services/logger')
        self._log = log.Log()
        cd = {'parent':logger_node,'name':'Precor_ICS', \
                'minimum_size':1000,'maximum_size':2000}
        self._log.configure(cd)
        columns_node = CompositeNode()
        cd = {'parent':self._log,'name':'columns'}
        columns_node.configure(cd)
        exporters_node = CompositeNode()
        cd = {'parent':self._log,'name':'exporters'}
        exporters_node.configure(cd)
        #create main exporter
        self._create_exporter('periodic_exporter', self.ent_ip_addr, self.ent_ip_port, exporters_node)
        #create alt exporter(s) but don't die if there is a problem
        try:
            if self.alt_ip_addr:
                addrs = self.alt_ip_addr.split(',')
                ports = self.alt_ip_port.split(',')
                for i in range(len(addrs)):
                    try:
                        self._create_exporter('periodic_exporter'+str(i+1), addrs[i], int(ports[i]), exporters_node)
                    except:
                        print 'exception in alt exporter creation'
        except:
            print "exception splitting alt ip's in create exporters"
        column_node = column.Column()
        cd = {'parent':columns_node, 'name':'timestamp', \
                'position':0,'sort_order':'ascending'} # one-and-only sorted column (field)
        column_node.configure(cd)
        i = 1
        for tag_data in self._session_data:
            column_node = column.Column()
            cd = {'parent':columns_node,'name':tag_data[0], \
                    'position':i,'sort_order':'none'}
            column_node.configure(cd)
            i += 1
        self._log.start() # starts entire self._log subtree; configs log from columns and exporters children nodes
        return
    ##
    # _handle_scan_data_wakeup: Callback for Scheduler to start a run of the
    # _scan_data_thread.
    #
    def _handle_scan_data_wakeup(self):
        # Insert int into queue, and (automatically) notify _scan_data_thread:
        self._scan_data_input_list.put(1)
        return
    ##
    # _scan_data_thread: Regularly polls for latest data. Ensures timely 
    # instanciation of FEU nodes for newly-discovered FEU Transceiver MAC addrs.
    #
    def _scan_data_thread(self):
        while self._scan_data_thread_go:  # test before sleep ...
            self._flashing_led_scanning_status = 0
            start_wait_time = time.time()
            self._scan_data_input_list.get() # blocks until >=1 object appears in Q
            if self._scan_data_thread_go == 0: # ... and test after wakeup
                break # time to go now!
            if time.time() < (start_wait_time + 1.0):
                continue # consider requests for successive scans to be "same" if within 1.0 sec
            aerocomm_server_kids = self._aero_server_node.children_nodes() 
            self._flashing_led_scanning_status = 0
            for client_node in aerocomm_server_kids:
                if not isinstance(client_node, aerocomm.AerocommClient):
                    continue
                client_kids = client_node.children_nodes()
                for feu_node in client_kids:
                    if not isinstance(feu_node, feu.FEU):
                        continue
                    units_map = self._ics_conf.get_units_map()
                    mac_address_str = str(feu_node.parent.mac_address)
                    if not units_map.has_key(mac_address_str):
                        # @todo If this unconfigured FEU has already been seen, then 
                        # move to next node:
                        unit_conf = _xml.Unit()
                        unit_conf.unit_mac_address = feu_node.parent.mac_address
                        unit_conf.feu_node = feu_node
                        self._post_AlarmsMsg_input_list.put((1003, unit_conf,))
                        msglog.log('mpx',msglog.types.WARN,'Found unconfigured FEU with MAC %s' \
                                        % mac_address_str)
                        continue # no need to instanciate PropAttr nodes; we do not poll unconfigd FEUs
                    unit_conf = units_map[mac_address_str] # need place to save running avgs and extrema
                    prop_nodes = feu_node.children_nodes()
                    for prop_node in prop_nodes:
                        if not feu_node.csafe.properties.has_key(prop_node.name):
                            continue
                        offline_only = feu_node.csafe.properties[prop_node.name][2]
                        if (feu_node.feu_state != 'OffLine') and offline_only:
                            continue
                        last_value = prop_node.get(0) # get last_value; avoid prompting an unnecy read
                        if not last_value is None:
                            if isinstance(last_value,csafe.CSafeUnitData):
                                ##
                                # @todo May need to convert value based on units (if/when
                                # Enterprise starts sending conversion tables to ICS), in
                                # order to deal with schizo users who insist on changing
                                # the units during a session... However, MikeW has assured
                                # us that all current Precor models always send a given 
                                # UnitData value as a single unit type, so OK for now...
                                last_value = last_value.value # use only the numeric value of the obj, NOT the units
                        self._prop_value_procs[prop_node.name](self, unit_conf, last_value)
                    break # only one FEU child node for a given Client node; others are status, etc.
            self._flashing_led_scanning_status = 0
        return
    ##
    # _handle_post_AlarmsMsg_wakeup: Callback for Scheduler (or other thread) to start a run of the
    # _post_AlarmsMsg_thread.
    #
    def _handle_post_AlarmsMsg_wakeup(self, error_code=None, unit_conf=None):
        # Insert 2-tuple into queue, and (automatically) notify _post_AlarmsMsg_thread:
        self._post_AlarmsMsg_input_list.put((error_code, unit_conf,))
        return
    ##
    # _post_AlarmsMsg_thread: Receives alarm data from other threads, and then
    # collates and sends alarm data to Enterprise.
    #
    def _post_AlarmsMsg_thread(self):
        while self._post_AlarmsMsg_thread_go:  # test before sleep ...
            error_code,unit_conf = self._post_AlarmsMsg_input_list.get() # blocks until >=1 object appears in Q
            if self._post_AlarmsMsg_thread_go == 0: # ... and test after wakeup
                break # time to go now!
            if error_code is None: # error_code is from Scheduler, so send alarms NOW:
                self._send_AlarmsMsg()
                continue # go back and wait for some more alarm data
            now = time.time()
            for alarm in self._cur_alarms_msg.alarms:
                if (alarm.error_code == error_code):
                    if (unit_conf is None) or (alarm.units[0] is None) \
                        or (alarm.units[0].mac_address == unit_conf.unit_mac_address):
                        alarm.occurrence_count += 1
                        alarm.last_occurrence_time = now
                        break
            else:
                # Create new instance of UnitAlarm and Alarm:
                unit_alarm = _xml.UnitAlarm()
                if not unit_conf is None:
                    unit_alarm.mac_address = unit_conf.unit_mac_address
                    unit_alarm.serial_number = unit_conf.serial_number
                    if unit_conf.feu_node.parent.transceiver_state == 'transceiver_responding':
                        odometer_node = unit_conf.feu_node.get_child('Odometer')
                        cur_odo = odometer_node.get(0)
                        if not cur_odo is None:
                            unit_alarm.odometer_start = cur_odo.value
                            unit_alarm.odometer_start_unit = int(cur_odo.units)
                        util_node = unit_conf.feu_node.get_child('Utilization')
                        unit_alarm.hours_start = util_node.get(0)
                        unit_alarm.version = unit_conf.version_data
                alarm = _xml.Alarm()
                alarm.first_occurrence_time = now
                alarm.last_occurrence_time = now
                alarm.occurrence_count = 1
                alarm.error_code = error_code
                alarm.units.append(unit_alarm) # ever only 1 unit for an alarm, but consistency eases coding (and invites hobgoblins into one's mind)
                self._cur_alarms_msg.alarms.append(alarm)
                # Limit num alarms (to prevent runaway memory usage if ICS is 
                # disconnected for a long time):
                if len(self._cur_alarms_msg.alarms) > self.max_num_cur_alarms:
                    old_alarm = self._cur_alarms_msg.alarms.pop(0)
                    msglog.log('mpx',msglog.types.ERR,'_post_AlarmMsg_thread(), lost old: %s, %s' 
                                    % (old_alarm.units[0].mac_address, old_alarm.error_code))
                if (self._alarms_interval_min_sid is None):
                    time_till_min_done = self._ics_conf.alarm_interval_min - (now - self._last_alarms_msg_sent_time)
                    if (time_till_min_done > 0):
                        at_time = time.time() + time_till_min_done
                        self._alarms_interval_min_sid = scheduler.at_time_do(at_time, self._handle_post_AlarmsMsg_wakeup)
                    else:
                        self._send_AlarmsMsg()
        return
    def _send_AlarmsMsg(self):
        now = time.time()
        try:
            self._cur_alarms_msg.msg_time = now
            # Format current AlarmsMsg into XML:
            ##
            # @todo: For better performance, make one persistent SGMLFormatter instance per 
            # thread (scan_data, send_Heartbeat, send_AlarmsMsg)
            #
            sgml = sgml_formatter.SGMLFormatter()
            self._cur_alarms_msg.get_xml(sgml)
            alarm_xml_msg = _xml._xml_prolog + sgml.output_complete()
            if self._open_ppp() != 0:
                self._flashing_led_internet_status = 0
                self._update_flashing_led()
                msglog.log('mpx:ics',msglog.types.ERR,'_send_AlarmsMsg: Failed to open PPP connection.')
                return
            # POST data to alternate servers:
            self.mirror_url_request('%s?ics_serial_id=%s' % (self.ent_url_alarm, self.actual_ser_num), alarm_xml_msg)
            # POST data to Enterprise App:
            url = 'http://%s:%u/%s?ics_serial_id=%s' \
                    % (self.ent_ip_addr, self.ent_ip_port, self.ent_url_alarm, self.actual_ser_num)
            alarms_fd = None
            try:
                alarms_fd = urllib.urlopen(url, alarm_xml_msg, 30.0)
            except Exception, e:
                msglog.log('mpx',msglog.types.ERR,'_send_Alarms(): %s' % str(e))
                if not alarms_fd is None:
                    msglog.log('mpx:ics',msglog.types.ERR,'Closing alarm URL handle...')
                    alarms_fd.close()
                    msglog.log('mpx:ics',msglog.types.ERR,'Closed alarm URL handle.')
                return
            alarms_fd.close()
            for alarm in self._cur_alarms_msg.alarms:
                msglog.log('mpx:ics',msglog.types.INFO,'Sent Error %u for Unit %s.' % (alarm.error_code,alarm.units[0].mac_address))
            # Note most recent xmssn, and replace sent AlarmsMsg object:
            self._last_alarms_msg_sent_time = now
            self._cur_alarms_msg = _xml.AlarmsMsg()
            self._cur_alarms_msg.ics_serial_id = self.actual_ser_num
            if not self._alarms_interval_min_sid is None:
                scheduler.cancel(self._alarms_interval_min_sid) # may have just started the scheduler...
                self._alarms_interval_min_sid = None
        finally:
            self._close_ppp()
            self._alarms_interval_min_sid = None
        return
    def _post_alarm_1005(self, unit_conf):
        try:
            self._post_AlarmsMsg_input_list.put((1005,unit_conf,))
        finally:
            unit_conf.radio_loss_sid = None # prep for next drop out
        return
    def _force_ready(self, ux):
        unit_conf, xcvr = ux
        msglog.log('mpx:ics',msglog.types.INFO,'_force_ready: %s.' % str(unit_conf.unit_mac_address))
        unit_conf.self_powered_radio_loss_sid = None # prep for next drop out
        xcvr.get_child('FEU').update_state(1)  #force Ready state onto feu
        return
    ##
    # _handle_Heartbeat_wakeup: Callback for Scheduler (or other thread) to start a run of the
    # _send_Heartbeat_thread.
    #
    def _handle_send_Heartbeat_wakeup(self):
        # Insert 2-tuple into queue, and (automatically) notify _post_AlarmsMsg_thread:
        self._send_Heartbeat_input_list.put(1)
        return
    ##
    # _send_Heartbeat_thread: Sends heartbeat msgs to Enterprise. Determines whether
    # latest config file available from Enterprise is later than local file. If so,
    # downloads config file from Enterprise.
    #
    def _send_Heartbeat_thread(self):
        while self._send_Heartbeat_thread_go:
            self._send_Heartbeat_input_list.get() # blocks until >=1 object appears in Q
            if self._send_Heartbeat_thread_go == 0: # ... and test after wakeup
                break # time to go now!
            try:
                hb_resp_fd = None # declare it out here, so that we can close it in exception handler, if necy
                answer = None
                try: # lots of file manipulations, with only one recourse (bail), so use single try/except
                    ##
                    # Send heartbeat data to Enterprise. If current config is 
                    # out of date, download, save, and parse new config from Enterprise, 
                    # and then restart MFW.
                    self._hb.msg_time = time.time()
                    self._hb.sequence_number = 0 # we may decide to use this later so that Enterprise can determine if any HBs were missed...
                    sgml = sgml_formatter.SGMLFormatter()
                    self._hb.get_xml(sgml)
                    hb_xml_msg = _xml._xml_prolog + sgml.output_complete()
                    # If necy, open PPP connection:
                    if self._open_ppp() != 0:
                        raise EConnectionError('Could not open PPP connection.')
                    # POST data to alternate servers:
                    self.mirror_url_request('%s?ics_serial_id=%s' % (self.ent_url_heartbeat, self.actual_ser_num), hb_xml_msg)
                    # POST data to Enterprise App:
                    url = 'http://%s:%u/%s?ics_serial_id=%s' \
                            % (self.ent_ip_addr, self.ent_ip_port, self.ent_url_heartbeat, self.actual_ser_num) 
                    self.debug_print('send_HB: Opening url: %s', (url,))
                    hb_resp_fd = urllib.urlopen(url, hb_xml_msg, 30.0)
                    answer = hb_resp_fd.read()
                    hb_resp_fd.close()
                    hb_resp_fd = None
                    self.debug_print('send_HB: Closed url: %s', (url,))
                    # Obtain and parse heartbeat-response:
                    ch = _xml.ContentHandler()
                    s = StringIO.StringIO(answer)
                    if self.debug_lvl >= 1: print s.read(); s.seek(0)
                    sax.parse(s, ch)
                    #update da blink'n light that the internet; she is gud
                    self._flashing_led_internet_status = 1
                    self._update_flashing_led()
                    hb_resp = ch.get_top_tag_obj() # rtns instance of _xml.HeartbeatResponse
                    self.debug_print('send_HB: response last_config_time: %s', (hb_resp.last_config_time,))
                    # Note that hb_resp.last_config_time can be None in comparison below,
                    # but None compares with numeric types without an exception. Also, 
                    # None evaluates to be less than ANY numeric (or string) value:
                    if hb_resp.last_config_time > self._ics_conf.last_config_time:
                        self._download_config_file()
                    elif hb_resp.last_config_time is None:
                        self._update_flashing_led(_LED_NO_CONFIG_IN_SVR)
                    msglog.log('mpx',msglog.types.INFO,'Heartbeat Update: Done successfully.')
                except Exception, e:
                    print 'send_HB exception: ', str(e)
                    #update da blink'n light that the internet; she is baad
                    self._flashing_led_internet_status = 0
                    self._update_flashing_led()
                    if answer is None: #did not get an answer to url request
                        # Setup Scheduler to kick off another heartbeat update delivery in one minute
                        if self._ics_conf.heartbeat_interval > 300: #more than 5 minutes between heart beats, need to try quicker
                            scheduler.seconds_from_now_do(60, self._handle_send_Heartbeat_wakeup) #try again in one minute
                    if not hb_resp_fd is None:
                        hb_resp_fd.close()
                    msglog.log('mpx',msglog.types.ERR,'_send_Heartbeat_thread: %s' % str(e))
                    msglog.exception()
            finally:
                self._close_ppp()
        return
    ##
    # _download_config_file: Downloads, stores, and parses new XML config file
    # from Enterprise. Raises exceptions, so ENCLOSE IN TRY BLOCK. Currently,
    # called ONLY by _send_Heartbeat_thread().
    #
    def _download_config_file(self):
        conf_fd = None
        config_xml_file_tmp = None
        tmp_path = None
        try:
            self._update_flashing_led(_LED_UNCONFIGURED)
            # POST data to alternate servers:
            self.mirror_url_request('%s?ics_serial_id=%s' % (self.ent_url_conf, self.actual_ser_num), None)
            url = 'http://%s:%u/%s?ics_serial_id=%s' \
                    % (self.ent_ip_addr, self.ent_ip_port, self.ent_url_conf, self.actual_ser_num)
            self.debug_print('send_HB: Opening url: %s', (url,))
            conf_fd = urllib.urlopen(url, None, 30.0)
            self.debug_print('send_HB: Opened url: %s', (url,))
            tmp_path = self.conf_file_path + '.tmp'
            config_xml_file_tmp = open(tmp_path, 'w+r')
            self.debug_print('send_HB: about to while away the time...')
            exc = [0]
            sid = scheduler.seconds_from_now_do(30.0, self._kill_the_damn_file,(conf_fd,exc,))
            while 1: # minimize temporary footprint of XML file in RAM, during xfr from Ent to disk file
                buf = conf_fd.read(8096)
                if (buf is None) or (len(buf) == 0):
                    if exc[0] != 0:
                        raise ENoData('Socket closed before ICS Config data received.')
                    break
                config_xml_file_tmp.write(buf)
            config_xml_file_tmp.flush()
            scheduler.cancel(sid)
            sid = None
        except:
            self._flashing_led_internet_status = 0
            self._update_flashing_led()
            raise
        ics_conf = _xml.IcsConfig() # default SHOULD be replaced toute suite
        try:
            self.debug_print('send_HB: Closed url: %s', (url,))
            config_xml_file_tmp.seek(0)
            ch = _xml.ContentHandler()
            sax.parse(config_xml_file_tmp, ch)
            ics_conf = ch.get_top_tag_obj() # rtns instance of IcsConfig
            if self.actual_ser_num != ics_conf.ics_serial_id:
                self._post_AlarmsMsg_input_list.put((1006, None,)) # bad ser num in config file!
                raise EInvalidValue('ics_serial_id',ics_conf.ics_serial_id, \
                                    'Serial Number from Enterprise should be %s' \
                                    % self.actual_ser_num)
        finally:
            conf_fd.close()
            config_xml_file_tmp.close()
        try:
            self.debug_print('send_HB: Stopping all threads...')
            # We're about to download a new config, and then restart the MFW,
            # so stop all other threads, and cause this one to exit when done.
            # This measure prevents other threads from tossing exceptions while
            # the config changes:
            self._stop_all_threads()
            self.debug_print('send_HB: All threads stopped.')
            self._ics_conf = ics_conf
            self.debug_print('send_HB: Copying temp ics-config.xml file to active.')
            os.system('cp %s %s' % (tmp_path, self.conf_file_path)) # make temp file semi-permanent
            msglog.log('mpx',msglog.types.INFO,'Heartbeat Update: Downloaded new config.')
        finally:
            msglog.log('mpx',msglog.types.INFO,' Restarting MFW within 1 sec...')
            system.exit() # restart MFW
        return
    def _kill_the_damn_file(self, file, exc):
        file.close()
        exc[0] = 1
        return
    def _event_handler(self, event):
        ##
        # @todo Give event to separate thread for handling.
        # Implement: mainly state-change events thrown by Server, Client, and FEU nodes. 
        # Do final calcs and log data when FEU state goes from OffLine->Ready. 
        # Create a current error (one of possibly several or many), and send Alarm msg when 
        # OffLine/Ready->Error. Record Session Start Time at Ready/Error->OffLine, and clear CalcData instances. 
        # Record Session End Time, and calc Session Duration at Offline->Ready/Error OR
        # OffLine->(FEU Xcvr Not Responding OR ICS Xcvr Not Responding).
        if not isinstance(event, ChangeOfValueEvent):
            return
        # Insert event into queue, and (automatically) notify _event_handler_thread:
        self._event_handler_input_list.put(event)
        return
    def _event_handler_thread(self):
        while self._event_handler_thread_go:
            event = self._event_handler_input_list.get() # blocks until >=1 object appears in Q
            if self._event_handler_thread_go == 0:
                break
            units_map = self._ics_conf.get_units_map()
            if isinstance(event.source, aerocomm.AerocommServer):
                if (event.old_value == 'transceiver_responding') \
                    and (event.value != 'transceiver_responding'):
                    # Post Alarm with Error Code 1004:
                    self._post_AlarmsMsg_input_list.put((1004, None,)) # system-wide; not assocd with specific FEU
                    # Walk all unit_confs, and set their radio_loss attr to 1. (Cleared to 0
                    # at next FEU state change.):
                    for unit_conf in units_map.values():
                        unit_conf.radio_loss = 1
                    #update da blink'n light
                    self._flashing_led_radio_status = 0
                    self._update_flashing_led()
                elif (event.old_value != 'transceiver_responding') \
                    and (event.value == 'transceiver_responding'):
                    #update da blink'n light
                    self._flashing_led_radio_status = 1
                    self._update_flashing_led()
            elif isinstance(event.source, aerocomm.AerocommClient):
                if (event.old_value == 'transceiver_responding') \
                    and (event.value != 'transceiver_responding'):
                    # Get unit_conf for FEU child:
                    mac_address_str = str(event.source.mac_address)
                    if not units_map.has_key(mac_address_str):
                        return
                    unit_conf = units_map[mac_address_str] # get storage location for running avgs, extrema, etc.
                    unit_conf.radio_loss = 1
                    if (unit_conf.no_comm_timeout is None) or (unit_conf.no_comm_timeout < 1.0): # secs
                        self._post_AlarmsMsg_input_list.put((1005, unit_conf,))
                    elif unit_conf.radio_loss_sid is None:
                        unit_conf.radio_loss_sid = scheduler.seconds_from_now_do(unit_conf.no_comm_timeout,self._post_alarm_1005,(unit_conf))
                        unit_conf.self_powered_radio_loss_sid = scheduler.seconds_from_now_do(_RADIO_LOSS_TO_FORCED_SESSION_CLOSE,self._force_ready,(unit_conf, event.source))
                elif (event.old_value != 'transceiver_responding') \
                    and (event.value == 'transceiver_responding'):
                    # Get unit_conf for FEU child:
                    mac_address_str = str(event.source.mac_address)
                    if not units_map.has_key(mac_address_str):
                        return
                    unit_conf = units_map[mac_address_str] # get storage location for running avgs, extrema, etc.
                    #unit_conf.radio_loss = 0
                    if hasattr(unit_conf, 'radio_loss_sid') and (not unit_conf.radio_loss_sid is None):
                        sid = unit_conf.radio_loss_sid
                        unit_conf.radio_loss_sid = None
                        scheduler.cancel(sid)
                    if hasattr(unit_conf, 'self_powered_radio_loss_sid') and (not unit_conf.self_powered_radio_loss_sid is None):
                        sid = unit_conf.self_powered_radio_loss_sid
                        unit_conf.self_powered_radio_loss_sid = None
                        scheduler.cancel(sid)
            elif isinstance(event.source, feu.FEU):
                mac_address_str = str(event.source.parent.mac_address)
                if not units_map.has_key(mac_address_str):
                    return # don't act on state changes in unconfigured FEUs
                unit_conf = units_map[mac_address_str] # get storage location for running avgs, extrema, etc.
                if event.old_value == 'OffLine':
                    if event.value == 'Ready':
                        self.debug_print('Non-Error session end for %s detected.', (str(unit_conf.unit_mac_address),), 1)
                        # Session done, and FEU still responding(?). Log data, and clear unit_conf accumulators:
                        self._send_record_to_log(unit_conf)
                    elif event.value == 'Error':
                        self.debug_print('Error caused session for %s to end.', (str(unit_conf.unit_mac_address),), 1)
                        self._send_record_to_log(unit_conf)
                        err_code = unit_conf.feu_node.get_child('Error_Code').get(1)
                        self._post_AlarmsMsg_input_list.put((err_code, unit_conf,))
                elif event.old_value == 'Ready':
                    if event.value == 'OffLine':
                        self.debug_print('Session start detected for %s.', (str(unit_conf.unit_mac_address),), 1)
                        # Kick off next run of _scan_data_thread() ASAP:
                        self._scan_data_input_list.put(1)
                        unit_conf.session_start_time = time.time()
                        unit_conf.program_code = 0
                    elif event.value == 'Error':
                        err_code = unit_conf.feu_node.get_child('Error_Code').get(1)
                        self._post_AlarmsMsg_input_list.put((err_code, unit_conf,))
                        unit_conf.program_code = 0
                elif event.old_value == 'Error':
                    if event.value == 'OffLine':
                        self.debug_print('Session start detected for %s.', (str(unit_conf.unit_mac_address),), 1)
                        # Kick off next run of _scan_data_thread() ASAP:
                        self._scan_data_input_list.put(1)
                        unit_conf.session_start_time = time.time()
                        unit_conf.program_code = 0
                    elif event.value == 'Ready':
                        pass
                # If ANY state change occurred, clear the bad-comm flags for
                # the unit whose state changed:
                unit_conf.radio_loss = 0
                unit_conf.feu_data_loss = 0
        return
    def _exception_handler(self, event):
        ##
        # @todo Implement
        msglog.log('mpx',msglog.types.ERR,'IcsAppSvcNode: recvd exception event %s' % str(event))
        return
    def _send_record_to_log(self, unit_conf):
        now = time.time()
        record_list = [time.time()]
        for tag_data in self._session_data:
            record_list.append(tag_data[1](unit_conf))
        self._log.add_entry(record_list)
        unit_conf.clear()
        msglog.log('mpx',msglog.types.INFO,'Sent workout session record to log: %s.' % str(unit_conf.unit_mac_address))
        return
    def debug_print(self, msg_fmt_str, msg_value_tuple=None, msg_lvl=1):
        if msg_lvl <= self.debug_lvl:
            if msg_value_tuple is None:
                prn_msg = 'IcsApp: ' + msg_fmt_str
            else:
                prn_msg = 'IcsApp: ' + (msg_fmt_str % msg_value_tuple)
            print prn_msg
        return
    def force_reconfig(self):
        self._ics_conf.last_config_time = 0.0
        return self._ics_conf.last_config_time

    def _flash_led(self, pattern=85, speed=100):
        try:
            if self._flashing_led_node is None:
                self._flashing_led_node = as_node('/interfaces/gpio1')
            self._flashing_led_node.set([3, speed, pattern])
        except:
            print 'gpio node exception'
        return
    def _update_flashing_led(self, pattern=0):
        if not pattern:
            if not self._flashing_led_internet_status:
                pattern = _LED_BAD_INTERNET
            if not self._flashing_led_radio_status:
                pattern |= _LED_BAD_RADIO
            if pattern == 0:
                pattern = _LED_OK
                if self._flashing_led_scanning_status:
                    pattern = _LED_SCANNING
        self._flash_led(pattern)
    def mirror_url_request(self, url, payload=None): #payload=None means get, not None means post
        try:
            if self.alt_ip_addr:
                addrs = self.alt_ip_addr.split(',')
                ports = self.alt_ip_port.split(',')
                for i in range(len(addrs)):
                    try:
                        _url = 'http://%s:%d/%s' % (addrs[i], int(ports[i]), url)
                        msglog.log('mpx:ics',msglog.types.INFO,'Opening monitor URL %s' % _url)
                        self.debug_print('ics_app opening alt url: %s', (url,))
                        fd = urllib.urlopen(_url, payload, 3.0)
                        answer = fd.read()
                        self.debug_print('alt url answer is: %s', (str(answer),))
                    except Exception, e:
                        #msglog.exception()
                        self.debug_print('Exception in alt request: %s', (str(e),))
        except Exception, e:
            self.debug_print('Exception splitting alt ip addrs and ports: %s', (str(e),))
        return

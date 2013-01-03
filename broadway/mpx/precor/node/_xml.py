"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
# _xml.py: This module contains class and function definitions to support parsing
# of XML messages received from Precor Enterprise Application via HTTP POST or GET.

import types, time, string, re
from xml import sax
from mpx.lib.node import as_node
from mpx.lib import msglog
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.aerocomm import aero
from mpx.lib import sgml_formatter
from mpx.lib.scheduler import scheduler

_xml_prolog = '<?xml version="1.0" encoding="utf-8"?>\n'

##
## INBOUND: (from Enterprise)
#
def _convert_none(text):
   return text

def _convert_hhmmss_str_to_float(text):
   text = string.lstrip(text)
   values = string.split(text,':')
   try:
      time_sec = int(values[0]) * 3600 + int(values[1]) * 60
   except:
      msglog.exception()
      return None
   if len(values) > 2:
      time_sec += int(values[2])
   return time_sec

def _convert_date_time_str_to_utc_sec(text):
   try:
      date_time_str = text[:19]
      local_sec = time.mktime(time.strptime(date_time_str, '%Y-%m-%dT%H:%M:%S'))
      tz_str = text[19:]
      tz_str = string.lstrip(tz_str)
      utc_sec = local_sec - _convert_time_zone_offset_str_to_int(tz_str)
   except:
      msglog.exception()
      return None
   return utc_sec
##
# _convert_time_zone_offset_str_to_int(): Rtns offset_sec to add to utc_sec
# to get local_sec: local_sec = utc_sec + offset_sec
#
def _convert_time_zone_offset_str_to_int(text):
   offset_sec = 0
   text = string.lstrip(text)
   try:
      i = string.find(text,':')
      if i > -1: # Eg "-5:30"
         offset_sec = int(text[:i]) * 3600
         offset_sec_from_minutes = int(text[i+1:]) * 60
         if offset_sec < 0:
            offset_sec_from_minutes = -offset_sec_from_minutes
         offset_sec += offset_sec_from_minutes
      else: # Eg "-0530"
         west = 0
         i = 0
         if text[0] == '-':
            west = 1
            i = 1
         offset_sec = int(text[i:i+2]) * 3600 + int(text[i+2:i+4]) * 60
         if west: offset_sec = -offset_sec
   except:
      msglog.exception()
      return 0
   return offset_sec

def _convert_str_to_mac(text):
   return aero.MacAddress(str(text))

def _convert_str_to_int(text):
   n = None
   try:
      n = int(text)
   except:
      pass
   return n

class BaseXmlCompositeTagDecode:
   _tag_name = ''
   _table = {}
   def __init__(self):
      for tag_data in self._table.values():
         if type(tag_data[1]) == types.ClassType:
            setattr(self,tag_data[0],[])
         else:
            setattr(self,tag_data[0],None)
      return
   
class CalcData:
   def __init__(self):
      self.run_total = None
      self.num_samples = None
      self.cur_num_zeroes = None
      self.max = None
      self.last_sample_time = None
      self.run_avg_period = None # weighted running avg, for internal use only
      self.max_period = None
      self.min_period = None
      return

class Unit(BaseXmlCompositeTagDecode):
   _tag_name = 'unit'
   _table = { \
             'unit-mac-address':['unit_mac_address', _convert_str_to_mac], \
             'product-category':['product_category', _convert_none], \
             'model-number':['model_number', _convert_str_to_int], \
             'identifier':['identifier', _convert_none], \
             'serial-number':['serial_number', _convert_none], \
             'no-comm-timeout':['no_comm_timeout', _convert_hhmmss_str_to_float], \
             }
   def __init__(self):
      BaseXmlCompositeTagDecode.__init__(self)
      self.feu_node = None
      self.clear()
      return
   def clear(self):
      self.program_code = 0 # '0' is 'Manual' AND 'Cool-Down' Program
      self.version_data = None
      self.last_odometer = 0
      self.last_utilization = 0
      self.last_utilization_time = 0 # to determine if new_utilization is too high for current time
      self.session_start_time = 0
      self.session_end_time = 0
      self.radio_loss = 0    # 1: indicates that the FEU xcvr state was NOT "transceiver_responding" during the current CSAFE state
      self.feu_data_loss = 0 # 1: indicates that the FEU GetStatus call returned "None" at least once during the current CSAFE state
      self.self_powered_radio_loss = 0
      if hasattr(self, 'radio_loss_sid') and (not self.radio_loss_sid is None):
         scheduler.remove(self.radio_loss_sid)
      if hasattr(self, 'self_powered_radio_loss_sid') and (not self.self_powered_radio_loss_sid is None):
         scheduler.remove(self.self_powered_radio_loss_sid)
      self.self_powered_radio_loss_sid = None
      self.radio_loss_sid = None
      self.speed = CalcData()
      self.gear = CalcData()
      self.grade = CalcData()
      self.power = CalcData()
      return

class IcsConfig(BaseXmlCompositeTagDecode):
   _tag_name = 'ics-config'
   _table = { \
             'msg-time':['msg_time',_convert_date_time_str_to_utc_sec], \
             'last-config-time':['last_config_time',_convert_date_time_str_to_utc_sec], \
             'time-zone':['time_zone',_convert_time_zone_offset_str_to_int], \
             'ics-serial-id':['ics_serial_id',_convert_none], \
             'site-name':['site_name',_convert_none], \
             'alarm-interval-min':['alarm_interval_min',_convert_hhmmss_str_to_float], \
             'heartbeat-interval':['heartbeat_interval',_convert_hhmmss_str_to_float], \
             'session-upload-interval':['session_upload_interval',_convert_hhmmss_str_to_float], \
             'session-upload-start-timeofday':['session_upload_start_timeofday',_convert_hhmmss_str_to_float], \
             'unit': ['units',Unit], \
             }
   def __init__(self):
      BaseXmlCompositeTagDecode.__init__(self)
      self._units_map = {}
      return
   def get_units_map(self):
      if len(self.units) != len(self._units_map):
         self._units_map = {}
         for unit in self.units:
            self._units_map[str(unit.unit_mac_address)] = unit
      return self._units_map

class HeartbeatResponse(BaseXmlCompositeTagDecode):
   _tag_name = 'heartbeat-response'
   _table = { \
             'msg-time':['msg_time',_convert_date_time_str_to_utc_sec], \
             'ics-serial-id':['ics_serial_id',_convert_none], \
             'last-config-time':['last_config_time',_convert_date_time_str_to_utc_sec], \
             }

class ContentHandler(sax.ContentHandler):
   _comp_tags = { \
                 IcsConfig._tag_name:IcsConfig, \
                 HeartbeatResponse._tag_name:HeartbeatResponse, \
                 }
   def __init__(self):
      sax.ContentHandler.__init__(self)
      self.debug = 1
      self._tag_stack = [] # elem: target_object (eg IcsConfig instance) or 2-list (eg ['msg-time',_convert_str_to_time]
      self._top_tag_obj = None
      return
   def get_top_tag_obj(self):
      return self._top_tag_obj
   def startDocument(self):
      self.__init__()
      return
   def endDocument(self):
      assert len(self._tag_stack) == 0, 'Unmatched tags found'
      return
   def startElement(self, name, attrs):
      if len(self._tag_stack) == 0:
         if not self._comp_tags.has_key(name):
            msglog.log('mpx',msglog.types.ERR,'%s does not understand XML tag %s' \
                       % (self.__class__.__name__, name))
            raise EInvalidValue('start tag name',name,'Unknown tag name.')
         tag_class = self._comp_tags[name]
         self._top_tag_obj = tag_class()
         self._tag_stack.append(self._top_tag_obj)
      else:
         cur_tag_obj = self._tag_stack[-1]
         if not cur_tag_obj._table.has_key(name):
            msglog.log('mpx',msglog.types.ERR,'%s (under tag "%s") does not understand XML tag %s' \
                       % (self.__class__.__name__, cur_tag_obj._tag_name, name))
            raise EInvalidValue('start tag name',name,'Unknown tag name.')
         tag_data = cur_tag_obj._table[name]
         if type(tag_data[1]) == types.ClassType:
            new_tag_obj = tag_data[1]()
            tag_obj_list = getattr(cur_tag_obj,tag_data[0])
            tag_obj_list.append(new_tag_obj)
            self._tag_stack.append(new_tag_obj)
         else:
            self._tag_stack.append([name,tag_data]) # tag_data: [attr_name, convert_fn]
      return
   def endElement(self, name):
      cur_tag_obj = self._tag_stack.pop(-1)
      tag_name = None
      if isinstance(cur_tag_obj, BaseXmlCompositeTagDecode):
         tag_name = cur_tag_obj._tag_name
      else:
         tag_name = cur_tag_obj[0]
      if name != tag_name:
         msglog.log('mpx',msglog.types.ERR,'%s encountered misplaced XML end tag %s' \
                    % (self.__class__.__name__, name))
         raise EInvalidValue('end tag name',name,'Misplaced end tag.')
      return
   def characters(self, content):
      cur_tag_obj = self._tag_stack[-1]
      if isinstance(cur_tag_obj, BaseXmlCompositeTagDecode):
         return
      value = cur_tag_obj[1][1](content)
      assert isinstance(self._tag_stack[-2],BaseXmlCompositeTagDecode),'Malformed XML file.'
      setattr(self._tag_stack[-2], cur_tag_obj[1][0], value)
      return
   
##
# OUTBOUND: (to Enterprise)
#
def _convert_simple_to_str(value):
   return str(value)

def _convert_float_to_hhmmss_str(f): # f: sec since whenever
   if f is None:
      return 'None'
   return time.strftime('%H:%M:%S', time.gmtime(f))

def _convert_utc_sec_to_date_time_str(f): # f: sec since Unix epoch, GMT (UTC)
   if f is None:
      return 'None'
   local_time_tuple = time.localtime(f)
   date_time_str = time.strftime('%Y-%m-%dT%H:%M:%S', local_time_tuple)
   dst_adj_timezone = time.timezone
   if local_time_tuple[8] == 1:
      dst_adj_timezone -= 3600 # subtract 1 hr if local is in DST
   date_time_str += _convert_float_to_time_zone_offset_str(dst_adj_timezone)
   return date_time_str

def _convert_float_to_time_zone_offset_str(num):
   if num is None:
      return '-0000' # "unknown" offset
   int_num = int(num)
   hours = int_num / 3600
   rmndr_sec = int_num % 3600
   mins = rmndr_sec / 60
   if (rmndr_sec % 60) >= 30:
      mins += 1
      if mins >= 60:
         mins = 0
         hours += 1
   return '%+03i%02u' % (-hours,abs(mins))

def _convert_mac_to_str(mac):
   return str(mac)

def _convert_CSafeVersionData_to_str(csvd):
   if (csvd is None) or (type(csvd) == types.StringType):
      return 'None'
   return csvd.as_string_of_hex_values()

class BaseXmlCompositeTagEncode:
   _tag_name = ''
   _table = {}
   def __init__(self):
      for tag_data in self._table.values():
         if type(tag_data[1]) == types.ClassType:
            setattr(self,tag_data[0],[])
         else:
            setattr(self,tag_data[0],None)
      return
   def get_xml(self, sgml):
      sgml.open_tag(self._tag_name)
      for tag_name, tag_data in self._table.items():
         if type(tag_data[1]) == types.ClassType:
            attr_list = getattr(self, tag_data[0])
            for attr in attr_list:
               attr.get_xml(sgml)
         else:
            sgml.open_tag(tag_name)
            value = getattr(self, tag_data[0])
            value_str = str(tag_data[1](value))
            sgml.add_text(value_str)
            sgml.close_tag(tag_name, 1) # open, text, close on same line
      sgml.close_tag(self._tag_name)
      return

class Heartbeat(BaseXmlCompositeTagEncode):
   _tag_name = 'heartbeat'
   _table = { \
             'msg-time':['msg_time', _convert_utc_sec_to_date_time_str], \
             'ics-serial-id':['ics_serial_id', _convert_simple_to_str], \
             'sequence-number':['sequence_number', _convert_simple_to_str], \
             }
   
class UnitAlarm(BaseXmlCompositeTagEncode):
   _tag_name = 'unit'
   _table = { \
             'mac-address':['mac_address', _convert_mac_to_str], \
             'serial-number':['serial_number', _convert_simple_to_str], \
             'odometer-start':['odometer_start', _convert_simple_to_str], \
             'odometer-start-unit':['odometer_start_unit', _convert_simple_to_str], \
             'hours-start':['hours_start', _convert_simple_to_str], \
             'version':['version', _convert_CSafeVersionData_to_str], \
             }

class Alarm(BaseXmlCompositeTagEncode):
   _tag_name = 'alarm'
   _table = { \
             'first-occurrence-time':['first_occurrence_time', _convert_utc_sec_to_date_time_str], \
             'last-occurrence-time':['last_occurrence_time', _convert_utc_sec_to_date_time_str], \
             'occurrence-count':['occurrence_count', _convert_simple_to_str], \
             'error-code':['error_code', _convert_simple_to_str], \
             'unit':['units', UnitAlarm], \
             }
   
class AlarmsMsg(BaseXmlCompositeTagEncode):
   _tag_name = 'alarms-msg'
   _table = { \
             'msg-time':['msg_time', _convert_utc_sec_to_date_time_str], \
             'ics-serial-id':['ics_serial_id', _convert_simple_to_str], \
             'alarm':['alarms', Alarm], \
             }
   
class WorkoutSession(BaseXmlCompositeTagEncode):
   _tag_name = 'workout-session'
   _table = { \
             'unit-mac-address':['unit_mac_address', _convert_mac_to_str],
             'session-start-time':['session_start_time', _convert_utc_sec_to_date_time_str],
             'session-end-time':['session_end_time', _convert_utc_sec_to_date_time_str],
             'session-duration':['session_duration', _convert_float_to_hhmmss_str],
             'program-code':['program_code', _convert_simple_to_str],
             'distance-horizontal':['distance_horizontal', _convert_simple_to_str],
             'distance-horizontal-unit':['distance_horizontal_unit', _convert_simple_to_str],
             'distance-vertical':['distance_vertical', _convert_simple_to_str],
             'distance-vertical-unit':['distance_vertical_unit', _convert_simple_to_str],
             'odometer-end':['odometer_end', _convert_simple_to_str],
             'odometer-end-unit':['odometer_end_unit', _convert_simple_to_str],
             'hour-meter-end':['hour_meter_end', _convert_simple_to_str],
             'max-speed':['max_speed', _convert_simple_to_str],
             'avg-speed':['avg_speed', _convert_simple_to_str],
             'speed-unit':['speed_unit', _convert_simple_to_str],
             'max-incline':['max_incline', _convert_simple_to_str],
             'avg-incline':['avg_incline', _convert_simple_to_str],
             'incline-unit':['incline_unit', _convert_simple_to_str],
             'max-resistance':['max_resistance', _convert_simple_to_str],
             'avg-resistance':['avg_resistance', _convert_simple_to_str],
             'max-user-power':['max_user_power', _convert_simple_to_str],
             'avg-user-power':['avg_user_power', _convert_simple_to_str],
             'user-power-unit':['user_power_unit', _convert_simple_to_str],
             'calories':['calories', _convert_simple_to_str],
             'user-weight':['user_weight', _convert_simple_to_str],
             'user-weight-unit':['user_weight_unit', _convert_simple_to_str],
             'user-age':['user_age', _convert_simple_to_str],
             'user-gender':['user_gender', _convert_none],
             'user-max-heart-rate':['user_max_heart_rate', _convert_simple_to_str],
             'user-avg-heart-rate':['user_avg_heart_rate', _convert_simple_to_str],
             'time-in-hr-zone':['time_in_hr_zone', _convert_float_to_hhmmss_str],
             'radio-loss':['radio_loss', _convert_simple_to_str],
             'feu-data-loss':['feu_data_loss', _convert_simple_to_str],
             }
   def __init__(self, data_dict=None):
      if data_dict is None:
         BaseXmlCompositeTagEncode.__init__(self)
         return
      if (type(data_dict) != types.DictType):
         raise EInvalidValue('data_dict',data_dict,'Should be dict from log.')
      for tag_name,value in data_dict.items():
         if not self._table.has_key(tag_name):
            continue
         tag_data = self._table[tag_name]
         #if type(tag_data[0]) == types.ClassType:
            #setattr(self,tag_name,[])
            #target_list = getattr(self,tag_name)
            #for sub_val in value:
               #new_obj = tag_data[1](sub_val)
               #sub_vals.append(new_obj)
         #else:
         setattr(self,tag_data[0],value)
      return
   
class WorkoutSessions(BaseXmlCompositeTagEncode):
   _tag_name = 'workout-sessions'
   _table = { \
             'msg-time':['msg_time', _convert_utc_sec_to_date_time_str], \
             'ics-serial-id':['ics_serial_id', _convert_simple_to_str], \
             'workout-session':['workout_sessions', WorkoutSession], \
             }
   

   
   
   
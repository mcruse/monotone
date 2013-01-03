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
# mpx/cpc/lib/utils.py: Support code.
# @author spenner@envenergy.com

import array, math, time, string, types
from mpx.ion.host.port import Port
from mpx.lib import threading, msglog
from mpx.lib.exceptions import MpxException,ETimeout
import tables # in local dir
from mpx.lib import EnumeratedDictionary, EnumeratedValue
      
_crc_table_xmodem = [\
   0x0000,  0x1021,  0x2042,  0x3063,  0x4084,  0x50a5,  0x60c6,  0x70e7,
   0x8108,  0x9129,  0xa14a,  0xb16b,  0xc18c,  0xd1ad,  0xe1ce,  0xf1ef,
   0x1231,  0x0210,  0x3273,  0x2252,  0x52b5,  0x4294,  0x72f7,  0x62d6,
   0x9339,  0x8318,  0xb37b,  0xa35a,  0xd3bd,  0xc39c,  0xf3ff,  0xe3de,
   0x2462,  0x3443,  0x0420,  0x1401,  0x64e6,  0x74c7,  0x44a4,  0x5485,
   0xa56a,  0xb54b,  0x8528,  0x9509,  0xe5ee,  0xf5cf,  0xc5ac,  0xd58d,
   0x3653,  0x2672,  0x1611,  0x0630,  0x76d7,  0x66f6,  0x5695,  0x46b4,
   0xb75b,  0xa77a,  0x9719,  0x8738,  0xf7df,  0xe7fe,  0xd79d,  0xc7bc,
   0x48c4,  0x58e5,  0x6886,  0x78a7,  0x0840,  0x1861,  0x2802,  0x3823,
   0xc9cc,  0xd9ed,  0xe98e,  0xf9af,  0x8948,  0x9969,  0xa90a,  0xb92b,
   0x5af5,  0x4ad4,  0x7ab7,  0x6a96,  0x1a71,  0x0a50,  0x3a33,  0x2a12,
   0xdbfd,  0xcbdc,  0xfbbf,  0xeb9e,  0x9b79,  0x8b58,  0xbb3b,  0xab1a,
   0x6ca6,  0x7c87,  0x4ce4,  0x5cc5,  0x2c22,  0x3c03,  0x0c60,  0x1c41,
   0xedae,  0xfd8f,  0xcdec,  0xddcd,  0xad2a,  0xbd0b,  0x8d68,  0x9d49,
   0x7e97,  0x6eb6,  0x5ed5,  0x4ef4,  0x3e13,  0x2e32,  0x1e51,  0x0e70,
   0xff9f,  0xefbe,  0xdfdd,  0xcffc,  0xbf1b,  0xaf3a,  0x9f59,  0x8f78,
   0x9188,  0x81a9,  0xb1ca,  0xa1eb,  0xd10c,  0xc12d,  0xf14e,  0xe16f,
   0x1080,  0x00a1,  0x30c2,  0x20e3,  0x5004,  0x4025,  0x7046,  0x6067,
   0x83b9,  0x9398,  0xa3fb,  0xb3da,  0xc33d,  0xd31c,  0xe37f,  0xf35e,
   0x02b1,  0x1290,  0x22f3,  0x32d2,  0x4235,  0x5214,  0x6277,  0x7256,
   0xb5ea,  0xa5cb,  0x95a8,  0x8589,  0xf56e,  0xe54f,  0xd52c,  0xc50d,
   0x34e2,  0x24c3,  0x14a0,  0x0481,  0x7466,  0x6447,  0x5424,  0x4405,
   0xa7db,  0xb7fa,  0x8799,  0x97b8,  0xe75f,  0xf77e,  0xc71d,  0xd73c,
   0x26d3,  0x36f2,  0x0691,  0x16b0,  0x6657,  0x7676,  0x4615,  0x5634,
   0xd94c,  0xc96d,  0xf90e,  0xe92f,  0x99c8,  0x89e9,  0xb98a,  0xa9ab,
   0x5844,  0x4865,  0x7806,  0x6827,  0x18c0,  0x08e1,  0x3882,  0x28a3,
   0xcb7d,  0xdb5c,  0xeb3f,  0xfb1e,  0x8bf9,  0x9bd8,  0xabbb,  0xbb9a,
   0x4a75,  0x5a54,  0x6a37,  0x7a16,  0x0af1,  0x1ad0,  0x2ab3,  0x3a92,
   0xfd2e,  0xed0f,  0xdd6c,  0xcd4d,  0xbdaa,  0xad8b,  0x9de8,  0x8dc9,
   0x7c26,  0x6c07,  0x5c64,  0x4c45,  0x3ca2,  0x2c83,  0x1ce0,  0x0cc1,
   0xef1f,  0xff3e,  0xcf5d,  0xdf7c,  0xaf9b,  0xbfba,  0x8fd9,  0x9ff8,
   0x6e17,  0x7e36,  0x4e55,  0x5e74,  0x2e93,  0x3eb2,  0x0ed1,  0x1ef0]


def make_xmodem_crc(buf, n):
   crc = 0x0000
   for i in range(n):
      crc = ((_crc_table_xmodem[((crc >> 8) & 0xFF) ^ (buf[i] & 0xFF)]) & 0xFFFF) \
            ^ ((crc << 8) & 0xFFFF)
   return crc	
      
def print_array_as_hex(array_in, line_len = 14):
   """
   print_array_as_hex():
   """
   len_array = len(array_in)
   lines = math.floor(len_array / line_len) # whole lines only
   offset = 0
   for line in range(lines):
      for byte in range(offset, offset + line_len):
         print '%02x' % array_in[byte],
      print
      offset = byte + 1
      
   # Deal with partial line at end:
   for byte in range(offset, offset + (len_array % line_len)):
      print '%02x' % array_in[byte],
   print

def _convert_trivial(data):
   return data
##
# _convert_char(data):
# @param data 1 ASCII char
# @return 1 ASCII char
def _convert_char(data):
   return data[0]
##
# _convert_schar(data):
# @param data 1 signed byte
# @return Python int
def _convert_schar(data):
   i_data = int(data[0])
   if (i_data & 0x80) != 0:
      return (i_data | 0xffffff00L)
   return i_data
##
# _convert_uchar(data):
# @param data 1 unsigned byte
# @return Python int
def _convert_uchar(data):
   return int(data[0])
##
# _convert_schar_div10(data):
# @param data 1 signed byte
# @return Python float
def _convert_schar_div10(data):
   return float(_convert_schar(data)) / 10.0
##
# _convert_uchar_div10(data):
# @param data 1 unsigned byte
# @return Python float
def _convert_uchar_div10(data):
   return float(_convert_uchar(data)) / 10.0
##
#
_special_int_values = { \
                   0x8AD0:'Short', \
                   0x8ACF:'Open', \
                   0x8ACE:'Closed', \
                   0x8ACD:'None', \
                   0x8ACC:'...', \
                   0x86E8:'Not Configured', \
                   0x86E3:'***', \
                   0x86E2:'Ignore', \
                   }
_special_funk_float_values = { \
                   0x8000:'OPEN', \
                   0xE000:'SHORT', \
                   0xC000:'NONE', \
                   }
##
# _convert_int(data):
# @param data 2 signed bytes, LSB-1st
# @return Python int
def _convert_int(data):
   i_data = data[0] + (data[1] << 8)
   i_data = (i_data & 0xffffffffL)
   if _special_int_values.has_key(i_data):
      return _special_int_values[i_data]
   if (i_data & 0x8000) != 0:
      return (i_data | 0xffff0000L)
   return i_data
##
# _convert_uint(data):
# @param data 2 unsigned bytes, LSB-1st
# @return Python int
def _convert_uint(data):
   u_data = data[0] + (data[1] << 8)
   u_data = (u_data & 0xffffffffL)
   if _special_int_values.has_key(u_data):
      return _special_int_values[u_data]
   return u_data
##
# _convert_int_div10(data):
# @param data 2 signed bytes, LSB-1st
# @return Python float
def _convert_int_div10(data):
   i_data = _convert_int(data)
   if (type(i_data) == types.StringType) \
      or (i_data is None):
      return i_data
   return float(i_data) / 10.0
##
# _convert_uint_div10(data):
# @param data 2 unsigned bytes, LSB-1st
# @return Python float
def _convert_uint_div10(data):
   u_data = _convert_int(data)
   if (type(u_data) == types.StringType) \
      or (u_data is None):
      return u_data
   return float(u_data) / 10.0
##
# _convert_int_div100(data):
# @param data 2 signed bytes, LSB-1st
# @return Python float
def _convert_int_div100(data):
   i_data = _convert_int(data)
   if (type(i_data) == types.StringType) \
      or (i_data is None):
      return i_data
   return float(i_data) / 100.0
##
# _convert_uint_div100(data):
# @param data 2 unsigned bytes, LSB-1st
# @return Python float
def _convert_uint_div100(data):
   u_data = _convert_int(data)
   if (type(u_data) == types.StringType) \
      or (u_data is None):
      return u_data
   return float(u_data) / 100.0
##
# _convert_int_div1000(data):
# @param data 2 signed bytes, LSB-1st
# @return Python float
def _convert_int_div1000(data):
   i_data = _convert_int(data)
   if (type(i_data) == types.StringType) \
      or (i_data is None):
      return i_data
   return float(i_data) / 1000.0
##
# Python(data):
# @param data 4 signed bytes, LSB-1st
# @return Python int
def _convert_long(data):
   return data[0] + (data[1] << 8) + (data[2] << 16) + (data[2] << 24)
##
# _convert_ulong(data):
# @param data 4 unsigned bytes, LSB-1st
# @return Python int
def _convert_ulong(data):
   return _convert_long(data)
##
# _convert_long_div10(data):
# @param data 4 signed bytes, LSB-1st
# @return Python float
def _convert_long_div10(data):
   return float(_convert_long(data)) / 10.0
##
# _convert_funk_float(data):
# @param data 2 bytes, LSB-1st
# @return Python float
def _convert_funk_float(data):
   if _special_funk_float_values.has_key(data):
      return _special_funk_float_values[data]
   exp10 = data[0] & 0x03
   if (data[0] & 0x04) != 0:
      exp10 = -exp10
   mant = (data[0] >> 3) + (data[1] << 8)
   if (data[1] & 0x80) != 0:
      mant = -mant
   return  mant * pow(10,exp10)
##
# _convert_funk_time(data):
# @param data 2 bytes, LSB-1st
# @return 2-tuple (H,M)
def _convert_funk_time(data):
   i_data = data[0] + (data[1] << 8)
   hours = i_data / 100
   minutes = i_data % 100
   return  (hours, minutes)
##
# _convert_time(data):
# @param data 2 bytes, LSB-2nd
# @return 2-tuple (H,M)
def _convert_time(data):
   return  (data[0], data[1])
##
# _convert_time_hhmm(data):
# @param data 2 bytes, LSB-1st
# @return 2-tuple (H,M)
def _convert_time_hhmm(data):
   i_data = data[0] + (data[1] << 8)
   hours = i_data / 60
   minutes = i_data % 60
   return  (hours, minutes)
##
# _convert_time_hhmmss(data):
# @param data 2 bytes, LSB-1st
# @return 3-tuple (H,M,S)
def _convert_time_hhmmss(data):
   i_data = data[0] + (data[1] << 8)
   hours = i_data / 3600
   rem_sec = i_data % 3600
   minutes = rem_sec / 60
   seconds = rem_sec % 60
   return  (hours, minutes, seconds)
##
# _convert_time_mmss(data):
# @param data 2 bytes, LSB-1st
# @return 2-tuple (M,S)
def _convert_time_mmss(data):
   i_data = data[0] + (data[1] << 8)
   minutes = i_data / 60
   seconds = i_data % 60
   return  (minutes, seconds)
##
# _convert_date(data):
# @param data 3 bytes, (M,D,Y)
# @return 3-tuple (Y,M,D)
def _convert_date(data):
   return  (data[2], data[0], data[1])
##
# _convert_month_day(data):
# @param data 2 bytes, MSB-1st (?)
# @return 2-tuple (M,D)
def _convert_month_day(data):
   return  (data[0], data[1])
##
# _convert_szstring(data):
# @param data 0-terminated string
# @return Python string
def _convert_szstring(data):
   text = data.tostring()
   end_idx = string.find(text,'\0')
   return text[:end_idx] # strip off all "extraneous" (?) chars at end of actual string...
##
# _convert_list_item(data):
# @param data 3 bytes: 1 byte + 1 word (LSB-1st)
# @return 2-tuple (index, list_id)
def _convert_list_item(data):
   i_data = data[1] + (data[2] << 8)
   return (data[0], i_data)
##
# _convert_bit_array(data):
# @param data variable num bytes in an array
# @return Python LongType (arbitrary number of bytes, allows easy bit-shifting)
def _convert_bit_array(data):
   flags = 0L
   for i in range(len(data)):
      flags += long(data[i] << (i * 8))
   return flags
##
# class CpcAlarm: Encapsulates CPC alarm data (ie a single record
# from an alarm log).
class CpcAlarm:
   _status_values = EnumeratedDictionary({0:'UNACKED',1:'ACKED',2:'RESET'})
   _type_values = EnumeratedDictionary({0:'NOTICE',1:'ALARM', 2:'RESET'})
   def __init__(self):
      self.id = None          # unique instance ID (2 bytes of a Python int)
      self.orig_date = None   # date alarm occurred (3-tuple)
      self.orig_time = None   # time alarm occurred (3-tuple)
      self.ack_date = None    # date alarm acknowledged (3-tuple)
      self.ack_time = None    # time alarm acknowledged (3-tuple)
      self.status = None      # 0, 1, or 2 (EnumeratedValue)
      self.type = None        # 0 or 1 (EnumeratedValue)
      self.item = None        # type of item that posted this alarm (Python int)
      self.item_num = None    # instance of item that posted this alarm (Python int)
      self.obj = None         # type of object that posted this alarm (Python int)
      self.obj_num = None     # instance of object that posted this alarm (Python int)
      self.text = None        # alarm text msg (Python string)
   def __eq__(self, o):
      return (self.id == o.id)
   def as_list(self):
      return [self.id,self.orig_date,self.orig_time,self.ack_date,self.ack_time, \
              self.status, self.type,self.item,self.item_num,self.obj,self.obj_num, \
              self.text]
         
##
# _convert_alarm(data):
# @param data 18 bytes + length of alarm text string (fixed at 40 chars)
# @return initialized instance of class CpcAlarm
def _convert_alarm(data):
   alarm = CpcAlarm()
   alarm.id = data[0] + (data[1] << 8)
   alarm.orig_date = _convert_date(data[2:5])
   alarm.orig_time = _convert_time(data[5:7])
   alarm.ack_date = _convert_date(data[7:10])
   alarm.ack_time = _convert_time(data[10:12])
   alarm.status = CpcAlarm._status_values[data[12]]
   alarm.type = CpcAlarm._type_values[data[13]]
   alarm.item = data[14]
   alarm.item_num = data[15]
   alarm.obj = data[16]
   alarm.obj_num = data[17]
   alarm.text = data[18:].tostring()
   alarm.device_name = None # init'd by mpx.cpc.lib.line_handler.Device.get_alarms()
   return alarm

_convert_funcs = {0:_convert_trivial, 1:_convert_uchar, 2:_convert_char, \
               3:_convert_schar, 4:_convert_int, 5:_convert_uint, 6:_convert_int_div10, \
               7:_convert_uint_div10, 8:_convert_int_div100, 9:_convert_uint_div100, \
               10:_convert_long, 11:_convert_ulong, 12:_convert_funk_float, \
               13:_convert_funk_time, 14:None, 15:_convert_date, 16:_convert_szstring, \
               17:_convert_list_item, 18:None, 19:_convert_bit_array, 20:_convert_alarm, \
               21:_convert_int_div1000, 22:_convert_month_day, 23:_convert_schar_div10, \
               24:_convert_uchar_div10, 25:_convert_time, 26:_convert_long_div10, \
               27:_convert_time_hhmm, 28:_convert_time_hhmmss, 29:_convert_time_mmss}













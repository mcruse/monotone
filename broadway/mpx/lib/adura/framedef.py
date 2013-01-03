"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
from mpx.lib import msglog

from mpx.lib.msglog.types import INFO

import struct
import sys
debug = 0

UINT_8 = 1
UINT_16 = 2
UINT_32 = 4

##
# frames that meet the following criteria:
# ((amtype == 0x31 or amtype == 0x33) or ((socketid == 0x31 or socketid == 0x33) and 
# (amtype == 0x0b or amtype == 0x0d)))
# are of potential interest to us and shall be evaluated further.

# LightPoint Config - Groups: Relay1
# board_id == 0x84 and packet_id == 0x10
lightpoint_config1 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('group1', 18, UINT_16, None),
    ('group2', 20, UINT_16, None),
    ('group3', 22, UINT_16, None),
    ('group4', 24, UINT_16, None),
    ('group5', 26, UINT_16, None),
    ('group6', 28, UINT_16, None),
    ('group7', 30, UINT_16, None),
    ('group8', 32, UINT_16, None),)

# LightPoint Config - Groups: Relay2
# board_id == 0x84 and packet_id == 0x20
lightpoint_config2 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('group1', 18, UINT_16, None),
    ('group2', 20, UINT_16, None),
    ('group3', 22, UINT_16, None),
    ('group4', 24, UINT_16, None),
    ('group5', 26, UINT_16, None),
    ('group6', 28, UINT_16, None),
    ('group7', 30, UINT_16, None),
    ('group8', 32, UINT_16, None),)

# LightPoint Config - Scenes 1-4
# board_id == 0x84 and packet_id == 0x30
lightpoint_config3 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('scene1', 18, UINT_16, None),
    ('scene1_state', 20, UINT_16, None),
    ('scene2', 22, UINT_16, None),
    ('scene2_state', 24, UINT_16, None),
    ('scene3', 26, UINT_16, None),
    ('scene3_state', 28, UINT_16, None),
    ('scene4', 30, UINT_16, None),
    ('scene4_state', 32, UINT_16, None),)
    
# LightPoint Config - Scenes 5-8
# board_id == 0x84 and packet_id == 0x40
lightpoint_config4 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('scene5', 18, UINT_16, None),
    ('scene5_state', 20, UINT_16, None),
    ('scene6', 22, UINT_16, None),
    ('scene6_state', 24, UINT_16, None),
    ('scene7', 26, UINT_16, None),
    ('scene7_state', 28, UINT_16, None),
    ('scene8', 30, UINT_16, None),
    ('scene8_state', 32, UINT_16, None),)
    
# LightPoint Config - Version, Load, Voltage
# board_id == 0x84 and packet_id == 0x50
lightpoint_config5 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('major', 18, UINT_8, None),
    ('minor', 19, UINT_8, None),
    ('build', 20, UINT_16, None),
    ('initialState', 22, UINT_16, None),
    ('connectedLoad1', 24, UINT_16, None),
    ('connectedLoad2', 26, UINT_16, None),
    ('voltage', 28, UINT_16, None),
    ('nDevices', 30, UINT_16, None),
    ('unused1', 31, UINT_8, None),
    ('unused2', 32, UINT_16, None),)
     
# LightPoint Config - Schedule Events (2 at a time)
# board_id == 0x84 and (packet_id == 0xa0, 0xb0, 0xc0,
# 0xd0, 0xe0, 0xf0, 0x10, 0x11, 0x12, 0x13, 0x14, 
# 0x15, 0x16, 0x17, 0x18 or 0x19
lightpoint_config10 = (\
    ('amtype', 2, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('group', 3, UINT_8, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('elem1', 16, UINT_8, None),
    ('elem2', 16, UINT_8, '_addO'),
    ('totalElems', 17, UINT_8, None),
    ('day1', 18, UINT_8, None),
    ('hour1', 19, UINT_8, None),
    ('minute1', 20, UINT_8, None),
    ('action1', 21, UINT_8, None),
    ('runflag1', 22, UINT_8, None),
    ('group1', 23, UINT_16, None),
    ('day2', 25, UINT_8, None),
    ('hour2', 26, UINT_8, None),
    ('minute2', 27, UINT_8, None),
    ('action2', 28, UINT_8, None),
    ('runflag2', 29, UINT_8, None),
    ('group2', 30, UINT_16, None),)

# LightPoint Config - TouchPointMap IDs
# board_id == 0x84 and (packet_id == 0x60, 0x70, 0x80 or 0x90)
lightpoint_config6 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('elem1', 16, UINT_8, None),
    ('elem2', 16, UINT_8, '_addO'),
    ('totalElems', 17, UINT_8, None),
    ('id1', 18, UINT_16, None),
    ('device1', 20, UINT_16, None),
    ('button1', 22, UINT_16, None),
    ('action1', 23, UINT_8, None),
    ('id2', 24, UINT_16, None),
    ('device2', 26, UINT_16, None),
    ('button2', 28, UINT_8, None),
    ('action2', 29, UINT_8, None),)

# LightPoint Config - Holidays
# board_id == 0x84 and (packet_id == 0x1a, 0x1b, 0x1c,
# 0x1d, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25
lightpoint_config26 = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('elem1', 16, UINT_8, None),
    ('elem2', 16, UINT_8, '_addO'),
    ('totalElems', 17, UINT_8, None),
    ('dayID1', 18, UINT_16, None),
    ('startDayEncoded1', 20, UINT_16, None),
    ('startDay1', 20, UINT_16, '_maskandshift', 0x1f, 0),
    ('startMonth1', 20, UINT_16, '_maskandshift', 0x1e0, 5),
    ('startYear1', 20, UINT_16, '_getyear16'),
    ('stopDayEncoded1', 22, UINT_16, None),
    ('stopDay1', 22, UINT_16, '_maskandshift', 0x1f, 0),
    ('stopMonth1', 22, UINT_16, '_maskandshift', 0x1e0, 5),
    ('stopYear1', 22, UINT_16, '_getyear16'),
    ('dayID2', 24, UINT_16, None),
    ('startDayEncoded2', 26, UINT_16, None),
    ('startDay2', 26, UINT_16, '_maskandshift', 0x1f, 0),
    ('startMonth2', 26, UINT_16, '_maskandshift', 0x1e0, 5),
    ('stopYear2', 26, UINT_16, '_getyear16'),
    ('stopDayEncoded2', 28, UINT_16, None),
    ('stopDay2', 28, UINT_16, '_maskandshift', 0x1f, 0),
    ('stopMonth2', 28, UINT_16, '_maskandshift', 0x1e0, 5),
    ('stopYear2', 28, UINT_16, '_getyear16'),)
    
# LightPoint Config - Event Insert
# board_id == 0x84 and packet_id == 0x00
lightpoint_data_config = (\
    ('amtype', 2, UINT_8, None),
    ('group', 3, UINT_8, None),
    ('firmware_id', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('board_id', 12, UINT_8, None),
    ('packet_id', 13, UINT_8, None),
    ('parent', 14, UINT_16, None),
    ('vref', 16, UINT_16, None),
    ('cur1', 18, UINT_16, '_getcurrent'),
    ('cur2', 20, UINT_16, '_getcurrent'),
    ('group1', 22, UINT_16, None),
    ('group2', 24, UINT_16, None),
    ('relayState1', 26, UINT_8, None),
    ('relayState2', 27, UINT_8, '_maskandshift', 0xfe, 1),
    ('year', 28, UINT_32, '_getyear32'),
    ('month', 28, UINT_32, '_maskandshift', 0x3c00000, 22),
    ('day', 28, UINT_32, '_maskandshift', 0x3e0000, 17),
    ('hour', 28, UINT_32, '_maskandshift', 0x1f000, 12),
    ('minute', 28, UINT_32, '_maskandshift', 0xfc0, 6),
    ('second', 28, UINT_32, '_maskandshift', 0x3f, 0),
    ('clock', 28, UINT_32, None),)
    
# LightPoint Xcommand Config
# board_id == 0x84 packet_id == 0x00
xcommand_config = (\
    ('amtype', 2, UINT_8, None),
    ('sourceaddr', 5, UINT_16, None),
    ('originaddr', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('boardid', 12, UINT_8, None),
    ('packetid', 13, UINT_8, None),
    ('nodeid', 14, UINT_16, None),
    ('responsecode', 16, UINT_8, None),
    ('cmdkey', 17, UINT_8, None),)
    
# LightPoint Health Mesh Config
# socketid == 0x03 old_type (byte12) == 0x0f type ==0x01
health_mesh_config = (\
    ('amtype', 2, UINT_8, None),
    ('sourceaddr', 5, UINT_16, None),
    ('nodeid', 7, UINT_16, None),
    ('socketid', 11, UINT_8, None),
    ('old_type', 12, UINT_8, '_maskandshift', 0xf0, 4),
    ('node_count', 12, UINT_8, '_maskandshift', 0x0f, 0),
    ('version', 13, UINT_8, None),
    ('type', 14, UINT_8, None),
    ('health_pkts', 15, UINT_16, None),
    ('node_pkts', 16, UINT_16, None),
    ('forwarded', 19, UINT_16, None),
    ('dropped', 21, UINT_16, None),
    ('retries', 23, UINT_16, None),
    ('battery', 25, UINT_8, '_getbattery'),
    ('power_sum', 26, UINT_16, None),
    ('board_id', 28, UINT_8, None),
    ('parent', 29, UINT_16, None),
    ('quality_tx', 31, UINT_8, '_maskandshift', 0x0f, 0),
    ('quality_rx', 31, UINT_8, '_maskandshift', 0xff, 4),
    ('path_cost', 32, UINT_8, None),
    ('parent_rssi', 33, UINT_8, None),)

# LightPoint Heartbeat Config XML
# amtype == 253
heartbeat_config = (\
    ('amtype', 2, UINT_8, None),)
    
##
# class for representing an Adura wireless sensor message
# and accessing it's properties.
class AduraFrame(object):
    # Decode raw frame as appropriate adura frame
    def __init__(self, frame):
        self.frame_type = 'Unknown'
        unpack_fmt = {UINT_8:'B',
                      UINT_16:'<H',
                      UINT_32:'<I'}
        self.decoded_frame = {}
        frame_template = ()
        amtype = frame[2]
        if amtype == 0xfd:
            # the most common frame that is sent periodically
            frame_template = heartbeat_config
            self.frame_type = 'heartbeat_config'
        else:
            board_id = frame[12]
            packet_id = frame[13]
            if frame[11] == 0x03 and ((frame[12] & 0xf0) >> 4) == 0x0f and \
                 frame[14] == 0x01:
                 # periodically sent node health messages
                 frame_template = health_mesh_config
                 self.frame_type = 'health_mesh_config'
            elif board_id == 0x84 and packet_id == 0x67:
                # whenever a LightPoints state changes, ie. a relay actuates, 
                # this message is generated.
                frame_template = lightpoint_data_config
                self.frame_type = 'lightpoint_data_config'
            elif board_id == 0x84 and packet_id == 0x00:
                # xml-rpc commands sent to the gateway are translated
                # to these xcommand_config messages to the LightPoints.
                frame_template = xcommand_config
                self.frame_type = 'xcommand_config'
            # lightpoint_config* messages follow - these are not yet well understood,
            # nor particularly relevant to us at this time.
            elif board_id == 0x84 and packet_id == 0x10:
                frame_template = lightpoint_config1
                self.frame_type = 'lightpoint_config1'
            elif board_id == 0x84 and packet_id == 0x20:
                frame_template = lightpoint_config2
                self.frame_type = 'lightpoint_config2'
            elif board_id == 0x84 and packet_id == 0x30:
                frame_template = lightpoint_config3
                self.frame_type = 'lightpoint_config3'
            elif board_id == 0x84 and packet_id == 0x40:
                frame_template = lightpoint_config4
                self.frame_type = 'lightpoint_config4'
            elif board_id == 0x84 and packet_id == 0x50:
                frame_template = lightpoint_config5
                self.frame_type = 'lightpoint_config5'
            elif board_id == 0x84 and (packet_id in \
                (0xa0, 0xb0, 0xc0, 0xd0, 0xe0, 0xf0,
                 0x10, 0x11, 0x12, 0x13, 0x14, 0x15,
                 0x16, 0x17, 0x18,0x19)):
                frame_template = lightpoint_config10
                self.frame_type = 'lightpoint_config10'
            elif board_id == 0x84 and (packet_id in \
                (0x60, 0x70, 0x80, 0x90)):
                frame_template = lightpoint_config6
                self.frame_type = 'lightpoint_config6'
            elif board_id == 0x84 and (packet_id in \
                (0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x20, 
                 0x21, 0x22, 0x23, 0x24, 0x25)):
                 frame_template = lightpoint_config26
                 self.frame_type = 'lightpoint_config26'
            else:
                # undocumented message - no need to process any further
                if debug:
                    msg = ''
                    for c in frame:
                        msg += '%x' % c
                    msg = 'Unable to load frame: %s' % msg
                    msglog.log('Adura', INFO, msg)
                return
         
        # now that we know what type of message it is, extract
        # all meaningful data using the corresponding Adura frame 
        # template.
        for frame_entry in frame_template:
            name = frame_entry[0]
            offset = frame_entry[1]
            v_type = frame_entry[2]
            func = frame_entry[3]
            if v_type == UINT_8:
                value = frame[offset]
            else:
                value = struct.unpack(
                            unpack_fmt.get(v_type), 
                            frame.tostring()[offset:offset+v_type]
                        )[0]
            if func is not None:
                # manipluate the raw value using func
                if func == '_maskandshift':
                    mask = frame_entry[4]
                    shift = frame_entry[5]
                    f = self._get_module_attr(func)
                    value = f(value, mask, shift)
                else:
                    value = self._get_module_attr(func)(value)
            # we can now access the value using {}.get('value_name')
            self.decoded_frame[name] = value
        return
        
    ##    
    # return the value of a named property
    def get(self, name):
        return self.decoded_frame.get(name)
        
    ##
    # print\log friendly version of frame contents
    def get_value_string(self):
        s = self.frame_type
        for name, value in self.decoded_frame.items():
            s = '%s %s (%d), ' % (s, name, value)
        return s
    
    #
    # return a module attr that is a helper function used to decode a frame
    # value
    def _get_module_attr(cls, func_name):
        return getattr(sys.modules['mpx.lib.adura.framedef'], func_name)
    _get_module_attr = classmethod(_get_module_attr)
    
# frame decoding helper functions
def _addOne(v):
    return v+1
    
def _getyear16(v):
    return int(2006 + ((v & 0xfff) >> 9))
    
def _getyear32(v):
    return int(2006 + ((v & 0xfc000000) >> 26))
    
def _maskandshift(v, mask, shift):
    return (v&mask)>>shift

def _getcurrent(v):
    return v / 1024.0 * 5
        
def _getbattery(v):
    return v / 10.0
                      
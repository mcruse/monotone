"""
Copyright (C) 2010 2011 Cisco Systems

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
""" Xbow pckt types - due to the dynamic nature of TinyOS, this has been structured 
in such a manner that it should be easy to add support for new message types """

import math, struct, time
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.scheduler import scheduler
from mpx.lib.exceptions import *

debug = 1
u_char = 1
u_short = 2
u_int = 3

class _TinyOS_Packet:
    _element_list = ()
    def __init__(self, raw_pkt):
        self._lock = Lock()
        self._clean_msg(raw_pkt)
        self.array = raw_pkt
        self.time_stamp = time.time()
        # figure out what type of message we are
        if self.array[4] in XBOW_TYPES.keys():
            self.__class__ = XBOW_TYPES[self.array[4]]
        self.map = {}
        for i in range(len(self._element_list)):
            self.map[self._element_list[i][0]] = i
        
    def get_element(self, name):
        if self.map.has_key(name):
            name_str, info = self._element_list[self.map[name]]
            offset, xtype = info
            if offset >= len(self.array):
                raise EInvalidValue('offset out of range', offset, 'get()')
            # conversions done on ion side with the aid of child calculators
            if xtype == u_char:
                return self.array[offset]
            if xtype == u_short:
                return struct.unpack('2B', self.array[offset:offset + 2])[0]
            if xtype == u_int:
                return struct.unpack('4B', self.array[offset:offset + 4])[0]
        raise EInvalidValue('parameter not found', name, 'get_element')
    
    def _clean_msg(self, b):
        # The raw data packet uses an escape u_char of 0x7d.  This is needed in case a u_char of
        # payload data itself is the same as a reserved u_char code, such as the frame synch u_char 0x7e.
        # In such a case, the payload data will be preceeded by the escape u_char and the payload data 
        # itself, XOR'd with 0x20.  F.e., a payload data u_char of 0x7e would appear in the data packet 
        # as 0x7d 0x5e
        buf_len = len(b)
        i = 0
        while i < buf_len:
            if b[i] == 0x7d:
                b.pop(i)
                b[i] ^= 0x20
                buf_len -= 1
            i += 1
        
    def is_sensor_data(self):
        # This allows us to to distinguish between messages like routing updates, 
        # which we don't care about and sensor reading updates.
        # Different radio\sensor modules will require additional logic - overridden
        # by sub-class 
        return 0
        
    def get_packet_type(self):
        return self.get_element('_PacketType')
        
    def get_address(self):
        return self.get_element('_MHOriginAddress')
        
    def get_group(self):
        return self.get_element('_TOSGroup')
        
    def needs_ack(self):
        return self.get_element('_PacketType') == 0x41
        
    def __str__(self):
        if len(self._element_list) > 0:
            answer = ''
            for e in self._element_list:
                if (e[0][0] != '_') or debug:
                    answer += e[0] + ': ' + str(self.get_element(e[0])) + '\n'
            return answer
        return str(self.array)

class _TOSMessage(_TinyOS_Packet):  
    # TinyOS messages are layered, ie. TOS_MSG|MULTIHOP_MSG|SURGE_MSG
    # Name: (offset, width, type)
    _element_list = (\
        ("_StartToken",         (0, u_char)),        # packet frame synch u_char ... always 0x7e
        # There are presently 5 known packet types:
        # 0x42: User packet with no ACK required.
        # 0x41: User packet.  ACK required.
        # 0x40: The ACK response to a 0x41
        # 0xFF: An unknown packet type
        ("_PacketType",         (1, u_char)), 
        # Begin TinyOS Message ... see TOS_Msg struct in /tos/types/AM.h of tinyos-1.x
        # _TOSAddr has 3 possible value types:
        # 0xffff: broadcast message to all nodes
        # 0x007e: message from a node to a gateway - here's where our primary interest lies.
        ("_TOSAddr",            (2, u_short)), 
        # Active Message (AM) unique identifier for the type of message it is.  Typically
        # each application will have its own message type, ie:
        # 0x00: AMTYPE_XUART
        # 0x03: AMTYPE_MHOP_DEBUG
        # 0x11: AMTYPE_SURGE_MSG 
        # 0x32: AMTYPE_XSENSOR
        # 0x33: AMTYPE_XMULTIHOP
        # 0xFA: AMTYPE_MHOP_MSG
        ("_TOSType",            (4, u_char)),
        ("_TOSGroup",           (5, u_char)),        # mote networks may be segmented by group id
        ("_TOSLength",          (6, u_char)),
    )
    # where does net portion of packet begin ...
    nxt_pkt_start = 7

class _MultiHopMessage(_TOSMessage):
    s_index = _TOSMessage.nxt_pkt_start
    _element_list = _TOSMessage._element_list + (\
        # Begin Multihop message ... see MultihopMsg struct in /contrib/xbow/toslib/ReliableRoute/MultiHop.h, f.e.
        ("_MHSourceAddress",    (s_index + 0, u_short)),       # address of forwarding node
        ("_MHOriginAddress",    (s_index + 2, u_short)),       # address of originating node
        ("_MHSeqNumber",        (s_index + 4, u_short)),       # used for determining missed pkts
        ("_MHHopCnt",           (s_index + 6, u_char)),        # hop cnt
    )
    nxt_pkt_start = _TOSMessage.nxt_pkt_start + 7

class MTSMultiHopSurgeRsp(_MultiHopMessage):
    s_index = _MultiHopMessage.nxt_pkt_start
    _element_list = _MultiHopMessage._element_list + (\
        # Begin Surge message ... see SurgeMsg struct in contrib/xbow/apps/Surge_Reliable, f.e.
        # Known Surge types include:
        # 0x00: message containing sensor data.
        # 0x01: root beacon
        # 0x02: changes mote update rate
        # 0x03: puts mote to sleep
        # 0x04: wakes mote
        # 0x05: chirps mote
        ("_Type",               (s_index + 0, u_char)), 
        ("_Reading",            (s_index + 1, u_short)),       # unused??
        ("_ParentAddress",      (s_index + 3, u_short)), 
        # upper 9 bits represent batt. voltage, remaining cnt since app. was last reset.
        ("_SequenceNum",        (s_index + 5, u_int)), 
        ("Light",               (s_index + 9, u_char)),
        ("Temp",                (s_index + 10, u_char)),
        ("MagX",                (s_index + 11, u_char)),
        ("MagY",                (s_index + 12, u_char)),
        ("AccelX",              (s_index + 13, u_char)),
        ("AccelY",              (s_index + 14, u_char)),
        ("_Crc",                (s_index + 15, u_short)),
    )
    
    def is_sensor_data(self):
        return not self.get_element('_Type') #sensor data type == 0
            
class MDAMultiHopSurgeRsp(_MultiHopMessage):
    # MDA sensor boards require multiple transmission to complete an entire
    # message transmission.
    #
    # ** note ** - unlike the MTS sensor boards - MDA will return raw values and children of ion can cook it
    # in whatever fashion deemed appropriate.  MDA is essentially a generic DAQ module.
    s_index = _MultiHopMessage.nxt_pkt_start
    _element_list = _MultiHopMessage._element_list + (\
        ("_SensorId",           (s_index + 0, u_char)),
        ("NodeId",              (s_index + 1, u_char)),
        # analog adc channels - found in first packet xmit'd
        ("ADC0",                (s_index + 2, u_short)),
        ("ADC1",                (s_index + 4, u_short)),
        ("ADC2",                (s_index + 6, u_short)),
        ("ADC3",                (s_index + 8, u_short)),
        ("ADC4",                (s_index + 10, u_short)),
        ("ADC5",                (s_index + 12, u_short)),
        ("ADC6",                (s_index + 14, u_short)),
        # precison adc channels - found in second packet xmit'd
        ("ADC7",                (s_index + 16, u_short)),
        ("ADC8",                (s_index + 18, u_short)),
        ("ADC9",                (s_index + 20, u_short)),
        ("ADC10",               (s_index + 22, u_short)),
        ("ADC11",               (s_index + 24, u_short)),
        ("ADC12",               (s_index + 26, u_short)),
        ("ADC13",               (s_index + 28, u_short)),
        # digital channels - found in third packet xmit'd
        ("DIGI0",               (s_index + 30, u_short)),
        ("DIGI1",               (s_index + 32, u_short)),
        ("DIGI2",               (s_index + 34, u_short)),
        ("DIGI3",               (s_index + 36, u_short)),
        ("DIGI4",               (s_index + 38, u_short)),
        ("DIGI5",               (s_index + 40, u_short)),
        # misc sensor data - found in fourth packet xmit'd
        ("Battery",             (s_index + 42, u_short)),
        ("Humidity",            (s_index + 44, u_short)),
        ("Temperature",         (s_index + 46, u_short)),
        ("Counter",             (s_index + 48, u_short)),
        ("_Crc",                (s_index + 50, u_short)),
    )

class MDASurgeRsp(_TOSMessage):
    s_index = _TOSMessage.nxt_pkt_start
    _element_list = _MultiHopMessage._element_list + (\
        ("_SensorId",           (s_index + 0, u_char)),        
        ("NodeId",              (s_index + 1, u_char)),
        # analog adc channels - found in first packet xmit'd
        ("ADC0",                (s_index + 2, u_short)),
        ("ADC1",                (s_index + 4, u_short)),
        ("ADC2",                (s_index + 6, u_short)),
        ("ADC3",                (s_index + 8, u_short)),
        ("ADC4",                (s_index + 10, u_short)),
        ("ADC5",                (s_index + 12, u_short)),
        ("ADC6",                (s_index + 14, u_short)),
        # precison adc channels - found in second packet xmit'd
        ("ADC7",                (s_index + 16, u_short)),
        ("ADC8",                (s_index + 18, u_short)),
        ("ADC9",                (s_index + 20, u_short)),
        ("ADC10",               (s_index + 22, u_short)),
        ("ADC11",               (s_index + 24, u_short)),
        ("ADC12",               (s_index + 26, u_short)),
        ("ADC13",               (s_index + 28, u_short)),
        # digital channels - found in third packet xmit'd
        ("DIGI0",               (s_index + 30, u_short)),
        ("DIGI1",               (s_index + 32, u_short)),
        ("DIGI2",               (s_index + 34, u_short)),
        ("DIGI3",               (s_index + 36, u_short)),
        ("DIGI4",               (s_index + 38, u_short)),
        ("DIGI5",               (s_index + 40, u_short)),
        # misc sensor data - found in fourth packet xmit'd
        ("Battery",             (s_index + 42, u_short)),
        ("Humidity",            (s_index + 44, u_short)),
        ("Temperature",         (s_index + 46, u_short)),
        ("Counter",             (s_index + 48, u_short)),
        # hrmmmm - suspect, need research on this fifth packet.
        ("_SequenceNum",        (s_index + 50, u_short)),
        ("ADC0_1",              (s_index + 52, u_short)),
        ("ADC1_1",              (s_index + 54, u_short)),
        ("ADC2_1",              (s_index + 56, u_short)),
        ("Battery_1",           (s_index + 58, u_short)),
        ("_Crc",                (s_index + 60, u_short)),
    )
    
XBOW_TYPES = {0x11:MTSMultiHopSurgeRsp}                    
        
	
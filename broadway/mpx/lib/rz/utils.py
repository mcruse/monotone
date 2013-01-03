"""
Copyright (C) 2003 2004 2007 2008 2010 2011 Cisco Systems

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
"""utils.py:"""

import sys
import struct
import fcntl
import array
import time
import exceptions
import string
import os
import select
import math
import tty

##
# @note Other RZNET modules rely on getting these constants from this module.
from errno import EBUSY
from errno import ENODEV
from errno import EINVAL
from errno import EXFULL
from errno import errorcode

from termios import *

from mpx.lib import EnumeratedDictionary
from mpx.lib import socket

from mpx.lib.exceptions import ENotOpen
from mpx.lib.exceptions import EAlreadyOpen
from mpx.lib.exceptions import EPermission
from mpx.lib.exceptions import EInvalidValue

from mpx.lib import threading

from mpx import properties as props

# rznet ldisc ioctl cmd numbers:
#@FIXME: Implement more graceful way of importing CPP defines from icos.h...
RZNET_IOCGADDRS     = 0x54E00010  # - get own and next addrs (8 bytes total)
RZNET_IOCSADDR      = 0x54E00011  # - set own addr (4 bytes total)
RZNET_IOCGNODES     = 0x54E10012  # - get main rznet node addrs; num nodes to
                                  #   read is 1st byte in buf param in ioctl
                                  #   call

# Date values returned to PhWin client during LAN Status Query. Arbitrary,
# and should not need to change. Any date other than that of the
# client instance of PhWin causes error message in PhWin. @FIXME:
# Either have PhWin insert its date into xpoints.net so that RznetNode
# can read it during start(), or have RznetThread watch OS download
# for date:
RZNET_YEAR      = 3   # 2003
RZNET_MONTH     = 3   # March
RZNET_DAY       = 30  # 30th

# "Memory addresses" and "page numbers" for LAN_SEND_MEM ops on Mediator:
RZNET_MEM_TYPE       = 0x44
RZNET_PAGE_TYPE      = 0
RZNET_MEM_VERSION    = 0xE002
RZNET_PAGE_VERSION   = 0
RZNET_MEM_ALIAS      = 0xF200
RZNET_PAGE_ALIAS     = 0
RZNET_MEM_DATE       = 0xC003
RZNET_PAGE_DATE      = 0
RZNET_MEM_APP_STAT   = 0x4020
RZNET_PAGE_APP_STAT  = 0x8C
RZNET_MEM_NODE_LIST  = 0x5555


# ASCII Values:
NUL = 0x00
SOH = 0x01
STX = 0x02
ACK = 0x06
NAK = 0x15
SYN = 0x16

# rznet Packet Types
LAN_RESET       = 0x03
LAN_TO_MEM      = 0x05
LAN_TO_MEM_SEQ  = 0x85 # (LAN_TO_MEM plus bit 7 set)
LAN_SEND_MEM    = 0x06
LAN_GOTO        = 0x07
LAN_TO_HOST     = 0x08
LAN_OBJ_VAL     = 0x09
LAN_MTR_VAL     = 0x0A
LAN_UPDATE      = 0x0B
LAN_TIME        = 0x0C
LAN_OBJ_RQST    = 0x0D
LAN_OBJ_OVRD    = 0x0E
LAN_OBJ_CLOV    = 0x0F
LAN_CML         = 0x10
LAN_AML         = 0x11
LAN_REPORT      = 0x12
LAN_ALARMS      = 0x14
LAN_ACK_ALARM   = 0x15
LAN_ACK_TREND   = 0x19
LAN_ALARM_REPORT= 0x1A
LAN_TOKEN_LIST  = 0x1C
LAN_EXTEND      = 0x40

PacketTypeEnum = EnumeratedDictionary({
        'LAN_RESET'       : 0x03,
        'LAN_TO_MEM'      : 0x05,
        'LAN_TO_MEM_SEQ'  : 0x85,
        'LAN_SEND_MEM'    : 0x06,
        'LAN_GOTO '       : 0x07,
        'LAN_TO_HOST'     : 0x08,
        'LAN_OBJ_VAL'     : 0x09,
        'LAN_MTR_VAL'     : 0x0A,
        'LAN_UPDATE'      : 0x0B,
        'LAN_TIME '       : 0x0C,
        'LAN_OBJ_RQST'    : 0x0D,
        'LAN_OBJ_OVRD'    : 0x0E,
        'LAN_OBJ_CLOV'    : 0x0F,
        'LAN_CML  '       : 0x10,
        'LAN_AML  '       : 0x11,
        'LAN_REPORT'      : 0x12,
        'LAN_ALARMS'      : 0x14,
        'LAN_ACK_ALARM'   : 0x15,
        'LAN_ACK_TREND'   : 0x19,
        'LAN_ALARM_REPORT': 0x1A,
        'LAN_TOKEN_LIST'  : 0x1C,
        'LAN_EXTEND'      : 0x40,
})

# host_master pkt indices for packets from phwin to modem server
RZHM_HDR_LEN      = 10
RZHM_DST_1ST      = 2
RZHM_DST_LAST     = 5
RZHM_TYPE         = 6
RZHM_DATA_1ST     = 7
RZHM_DATA_LAST    = 8
RZHM_CHKSUM       = 9

# host_slave pkt indices for response packets from modem server to phwin:
RZHS_HDR_LEN      = 6
RZHS_TYPE         = 2
RZHS_SEQ          = 3
RZHS_LEN          = 4
RZHS_CHKSUM       = 5

RZHS_SRC_1ST      = 6
RZHS_SRC_LAST     = 9
RZHS_TYPE2        = 10
RZHS_DATA_1ST     = 11
RZHS_DATA_LAST    = 12
RZHS_2ND_CHKSUM   = 13


# rznet_peer pkt indices for packets on the network:
RZNP_HDR_LEN       = 14 #
RZNP_DST_1ST       = 2
RZNP_DST_LAST      = 5
RZNP_SRC_1ST       = 6 #
RZNP_SRC_LAST      = 9 #
RZNP_TYPE          = 10
RZNP_DATA_1ST      = 11 #
RZNP_DATA_LAST     = 12 #
RZNP_HDR_CHKSUM    = 13

# Pkt Handling Flags:
PKTFL_RESPOND      = 0x00000001
PKTFL_NO_BCAST_RESP= 0x00000002

# Other constants:
MODEM_SERVER_DEF_ADDR = 0xFFFFFFFFL # - interpreted as "-1" without the
                                    #   concluding "L"
BROADCAST_ADDR        = 0
APP_FLAG              = 0x40 # - ORed with MSB of address in "others'"
                             #   LAN_TO_HOST responses to bcast LAN_TOKEN_LIST

ENDIANNESS = '<' # little
if props.HARDWARE_CODENAME == 'Megatron':
    ENDIANNESS = '>' # big

debug_lvl = 0
def debug_print(msg_lvl, msg, *args):
    if msg_lvl < debug_lvl:
        if args:
            print msg % args
        else:
            print msg

def print_array_as_hex(array_in, line_len = 14):
    """
    print_array_as_hex():
    """
    len_array = len(array_in)
    lines = int(math.floor(len_array / line_len)) # whole lines only
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

def HiTech_to_float(buf):
    """
    HiTech_to_float(): Converts a 4-byte "HiTech" Z180 C-compiler float, given
    in an array object, to an 8-byte little- (x86) or big- (PPC) endian double.
    """
    exponent = ord(buf[3]) & 0x7f
    if exponent == 0:
        return 0.0
    mantissa = struct.pack('<I',(struct.unpack('<I', buf)[0] & 0x7FFFFF) << 5)
    a = array.array('B')
    a.fromstring(mantissa)
    exponent = struct.pack('<H',((exponent + 958)<<4) + ord(mantissa[3]))
    a = array.array('B')
    a.fromstring(exponent)
    s = '\0\0\0' + mantissa[:3] + exponent
    a = array.array('B')
    a.fromstring(s)
    d = struct.unpack('<d', s)[0] # unpack rtns one-elem tuple
    if ord(buf[3]) & 0x80:
        return -d
    return d

def float_to_HiTech(float_val):
    """
    float_to_HiTech(): Converts an 8-byte little-endian Intel x86 double to
    a 4-byte "HiTech" Z180 C-compiler float, returned in an array object.
    """
    ht_buf = array.array('B', 4 * '\0')
    if float_val == 0.0:
        return ht_buf

    # Restrict input value according to HiTech's allowable ranges:
    if float_val > 0:
        if float_val > 9.0e18:
            float_val = 9.0e18
        elif float_val < 1.0e-19:
            float_val = 1.0e-19
    else:
        if float_val < -9.0e18:
            float_val = -9.0e18
        elif float_val > -1.0e-19:
            float_val = -1.0e-19

    s_float_val = struct.pack('<d', float_val)
    b_float_val = struct.unpack(8 * 'B', s_float_val)

    wExponent = ((b_float_val[7] & 0x7F) << 4) & 0xFFFF
    wExponent = wExponent + (((b_float_val[6] & 0xF0) >> 4) - 958) & 0xFFFF

    ht_buf[3] = wExponent & 0xFF

    if (b_float_val[7] & 0x80):
        ht_buf[3] = ht_buf[3] ^ 0x80

    dwMantissa = ((b_float_val[6] & 0x0F) | 0x10) << 8
    dwMantissa = (dwMantissa + b_float_val[5]) << 8
    dwMantissa = (dwMantissa + b_float_val[4]) << 8
    dwMantissa = (dwMantissa + b_float_val[3]) >> 5

    ht_buf[0] = dwMantissa & 0xFF
    ht_buf[1] = (dwMantissa >> 8)  & 0xFF;
    ht_buf[2] = (dwMantissa >> 16)  & 0xFF;

    return ht_buf

g_str_create_listen_skt = 'create_listen_skt(): '

def create_listen_skt(port_num):
    """create_listen_skt(): Create/rtn TCP (stream) socket with given port num,
       to listen for remote connections."""

    # AF_INET attr allows skt access via an Ethernet adapter, and SOCK_STREAM
    # specifies a reliable, connection-based (TCP) protocol:
    debug_print(0, "%s%s",
                g_str_create_listen_skt, 'Initializing listen_skt...')
    listen_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    linger = struct.pack("ii", 1, 0) # - prevent skt from jabbering with empty
                                     #   pkts after closure
    listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
    debug_print(0, "%s listen_skt = %s",
                g_str_create_listen_skt, str(listen_skt))
    # Bind the listen_skt object to a port (by specifying the port
    # number found in this node's config). The empty string used to specify
    # the host address causes the Python wrapper to send INADDR_ANY to the
    # underlying bind() system call, thereby enabling listening on the given
    # port on ALL adapters (eg ethX and serial/PPP):
    skt_address = ('', int(port_num))
    listen_skt.bind(skt_address)
    debug_print(0, '%s listen_skt is bound to address %s.',
                g_str_create_listen_skt, str(skt_address))

    # Set listen_skt to listen for connections from remote client skts. Allow
    # max of 3 queued connection requests (may change number for future uses):
    try:
        listen_skt.listen(3)
    except socket.error, details:
        debug_print(0, 'Call to socket.listen() failed: %s', details)
        return None
    except:
        debug_print(0, 'Unknown exception while calling socket.listen()...')
    return listen_skt


g_str_create_cmd_skts = 'create_cmd_skts(): '

def create_cmd_skts(class_name, _tmp_dir):
    # Establish an internal connection anchored by a pair of stream sockets by
    # which other threads may deliver cmds to this thread. (The actual cmd
    # calls wrap all access to the sockets and connection.):
    socket_name = os.path.join(_tmp_dir,
                               (class_name + '.%d') % threading.gettid())

    # Delete any existing file with the path & name of the socket to be
    # created:
    while os.path.exists(socket_name):
        try:    os.remove(socket_name)
        except: socket_name += 'x'

    # Create UNIX listen_skt object:
    listen_skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Set this_socket to allow rebinding to different local connections while
    # a previous binding is "in the process" of disconnecting (can take up to
    # several minutes after binding is already disconnected...):
    try:
        listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception, e:
        debug_print(0, '%s Set reuse failed, %s', g_str_create_cmd_skts, e)

    # Assign the created socket name/address to the listen socket object:
    listen_skt.bind(socket_name)

    # Create the actual sockets for each end of the command connection,
    # and establish a connection between the 2 sockets:
    _far_cmd_skt = None
    _near_cmd_skt = None
    try:
        listen_skt.listen(1) # only want one connection (ie to far_skt)
        _far_cmd_skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        _far_cmd_skt.connect(socket_name)
        _near_cmd_skt, addr = listen_skt.accept()
        _near_cmd_skt.setblocking(0) # no blocking on cmd skt connection
    finally:
        # Once the connection is established, we can delete the file.
        # It will be removed from its directory, but continue to exist
        # until this process is no longer connected to it.
        os.remove(socket_name)
    debug_print(1, '%s Cmd skt created', g_str_create_cmd_skts)
    return (_far_cmd_skt, _near_cmd_skt)

def form_net_pkt(dst_addr, type, data, ext = None, flags = 0):
    debug_print(1, 'Forming net pkt with dst_addr = %d, type = %d, data = %d',
                dst_addr, type, data)

    if(ext):
        type = type | LAN_EXTEND # make sure that this bit is set
        ext.append(0x00) # to hold ext chksum (calc'd by rznet ldisc)
        data = len(ext) # len MUST INCLUDE chksum byte

    b_dst_addr = form_long(dst_addr)
    b_data = form_short(data)
    b_flags = form_long(flags)

    # Set src_addr bytes to 0's; set to proper addr by rznet ldisc:
    pkt = array.array('B', [SYN, SOH, b_dst_addr[0], b_dst_addr[1],
                            b_dst_addr[2], b_dst_addr[3],
                            0x00, 0x00, 0x00, 0x00, type,
                            b_data[0], b_data[1], 0x00])
    if(ext):
        pkt.extend(ext) # add extension to hdr

    pkt.extend(array.array('B', [b_flags[0], b_flags[1], b_flags[2],
                                 b_flags[3]]))

    debug_print(1, 'Formed outgoing pkt:')
    if debug_lvl > 0:
        print_array_as_hex(pkt)

    return pkt


host_channel_lock = threading.Lock()

class RzHostPkt(object):
    def __init__(self, pkt=None):
        self._pkt = pkt
    def tofile(self, fileno):
        #only one request at a time - once we do sequence packets we can relax this
        host_channel_lock.acquire()
        try:
            #examine type of packet going to modem server and prepare for response
            type = self._pkt[6]
            self._pkt.tofile(fileno)
            #wait for ACK or response
        finally:
            host_channel_lock.release()
    def tostring(self):
        return self._pkt.tostring()
        

def form_host_pkt(dst_addr, type, data, ext = None, flags = 0):
    debug_print(1, 'Forming host pkt with dst_addr = %d, type = %d, data = %d',
                dst_addr, type, data)

    if(ext):
        type = type | LAN_EXTEND # make sure that this bit is set
        ext.append(0x00) # to hold ext chksum (calc'd by rznet ldisc)
        data = len(ext) # len MUST INCLUDE chksum byte

    b_dst_addr = form_long(dst_addr)
    b_data = form_short(data)

    # no src_addr bytes
    pkt = array.array('B', [SYN, SOH, 
                            b_dst_addr[0], b_dst_addr[1], b_dst_addr[2], b_dst_addr[3],
                            type,
                            b_data[0], b_data[1],
                            0x00])
    pkt[-1] = rznet_chksum(pkt[2:])

    if(ext):
        pkt.extend(ext) # add extension to hdr
        pkt[-1] = rznet_chksum(pkt[10:])

    debug_print(1, 'Formed outgoing host packet:')
    if debug_lvl > 0:
        print_array_as_hex(pkt)

    return RzHostPkt(pkt)

def rznet_chksum(ar, sum=0): #allow preset of sum for Host slave passthrough of net packets
    for b in ar:
        sum = sum + b
    chksum = (0x55 - sum) & 0xFF
    return chksum

def form_slave_pkt(ext, pkt=None):
    # ALWAYS a LAN_TO_HOST type (assumed, but not spec'd in pkt), and ALWAYS
    # extended:
    assert (ext != None)
    ext_chksum = rznet_chksum(ext)
    ext.append(ext_chksum)
    data = len(ext) # len MUST INCLUDE chksum byte

    type = LAN_TO_HOST
    seq_num = 0
    if pkt: #get request packet type and sequence info
        type = pkt[RZHM_TYPE]
        seq_num = pkt[RZHM_DST_LAST]
    pkt = array.array('B', [SYN, SOH, type, seq_num, data, 0x00])
    hdr_chksum = rznet_chksum(pkt[RZHS_TYPE : RZHS_CHKSUM])
    pkt[RZHS_CHKSUM] = hdr_chksum

    pkt.extend(ext) # add extension to hdr

    debug_print(1, 'Formed slave pkt:')
    if debug_lvl > 1:
        print_array_as_hex(pkt)

    return pkt

def form_short(short):
    s_short = struct.pack('<H', short & 0xFFFF)
    b_short = struct.unpack(2 * 'B', s_short)
    return b_short


def form_long(long):
    s_long = struct.pack('<I', long)
    b_long = struct.unpack(4 * 'B', s_long)
    return b_long

def form_addr_obj_id_array(dst_addr, obj_id):
    b_dst_addr = form_long(dst_addr)
    b_obj_id = form_short(obj_id)
    pnt_ext = array.array('B', [b_dst_addr[0], b_dst_addr[1], b_dst_addr[2],
                                b_dst_addr[3], b_obj_id[0], b_obj_id[1]])
    return pnt_ext

if __name__ == '__main__':
    print 'Starting utils.py unit test...'

    ext = array.array('B', [5,0,0xFF,0xFF,0xFF,0])
    pkt = form_slave_pkt(LAN_SEND_MEM, 0, ext)

    print 'Starting utils.py unit test...'
    pass


    # host command
    # SYN
    # SOH
    # DEST LSB
    # DEST
    # DEST MSB
    # SEQ
    # TYPE
    # DATA OR LENGTH LSB
    # DATA OR LENGTH MSB
    # CHK
    # EXT....
    # CHK

    # slave response
    # SYN
    # SOH
    # TYPE (formerly, DEPTH)
    # SEQ
    # COUNT
    # CHK
    # EXT....
    # CHK

    #net passthrough for LAN_OBJ_VAL and LAN_UPDATE pkts
    #SYN
    # SOH
    # TYPE (formerly, DEPTH)
    # SEQ
    # COUNT
    # CHK
    #SRC LSB
    #SRC
    #SRC MSB
    #SPARE
    #TYPE
    #DATA OR LEN LSB
    #DATA OR LEN MSB
    #CHK (calc like net packet assuming sent to 100,000 destination address)
    # EXT....
    # CHK

    # net packet
    # SYN
    # SOH
    # DEST LSB
    # DEST
    # DEST MSB
    # SEQ
    # SRC LSB
    # SRC
    # SRC MSB
    # SRC SPARE
    # TYPE
    # DATA OR LENGTH LSB
    # DATA OR LENGTH MSB
    # CHK
    # EXT....
    # CHK

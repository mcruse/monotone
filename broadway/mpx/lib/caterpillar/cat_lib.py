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
import time 
import array
import string
import struct
import types
from mpx.lib.exceptions import ETimeout, EInvalidValue
from mpx.lib import threading

debug = 0

INT    = 0
UINT   = 1
STRING = 2

BROADCAST_RESPONSE = 0x10
STATUS_RESPONSE    = 0x15
READ_RESPONSE      = 0x25
WRITE_RESPONSE     = 0x35

#
# If parameters are singular, pid node gets value directly
# If parameters are multiple and one has None as it's name, pid node gets value directly
# If parameters are multiple, named parameters are children of pid node
# If parameters are multiple and all are named, pid node gets tuple of values
#
# array formats:
#   the port object wants either strings or arrays of chars
#   the packet creation and analysis routines use arrays of bytes (ints)

PID = { \
    # pid      name                              security (params (name,length))
    0x000D: ('Remote Fault Reset',                     2, 'B',    ()),
    0x0080: ('Device ID Code',                         1, '<HHH', ('Module ID','Service Tool Support Change Level', 'Application Type')),
    0x0082: ('CCM Error Codes',                        1, '>HB',  ('Reserved', 'Fault Code Status')),
    0xAA12: ('CCM Communication Rate Change Enable',   1, 'B',    ()),
    0xAA87: ('Access Level 1 Password',                1, '8s',   ()),
    0xAA88: ('Access Level 2 Password',                1, '8s',   ()),
    0xAA89: ('Access Level 3 Password',                1, '8s',   ()),
    0xAA8A: ('Login Password',                         1, '8s',   ()),
    0xF012: ('Security Access Level',                  1, 'B',    ()),
    0xF601: ('Serial Port Configuration',              1, '>L',   ()),
    0xF814: ('Application Software Part Number',       1, '10s',  ()),
    0x0040: ('Generator Set Engine RPM',               1, '>H',   ()),
    0x0042: ('Generator Set Ring Gear Teeth Setpoint', 1, '>H',   ()),
    0x0044: ('Engine Coolant Temperature',             1, '>H',   ()),
    0x0054: ('Engine Oil Pressure kPa',                1, '>H',   ()),
    0x005E: ('Generator Set Hourmeter',                1, '>H',   ()),
    }

# 0x000D;0x0080;0x0082;0xAA12;0xAA87;0xAA88;0xAA89;0xAA8A;0xF012;0xF601;0xF814;0x0040;0x0042;0x0044;0x0054;0x005E

def is_writeable(pid):
    return 0 #false

def read_single_parameter_packet(mid, pid):
    if not type(mid) == types.IntType:
        mid = _hex_str_2_int(mid)
    if not type(pid) == types.IntType:
        pid = _hex_str_2_int(pid)
    answer = array.array('B')
    answer.fromlist([0x50, 0x00, 0x24, 0x04, 0x00, mid, pid // 256, pid % 256])
    return (_finished_packet(answer),(mid,pid,))

def write_single_parameter_packet(mid, pid, bytes):
    if not type(mid) == types.IntType:
        mid = _hex_str_2_int(mid)
    if not type(pid) == types.IntType:
        pid = _hex_str_2_int(pid)
    answer = array.array('B')
    answer.fromlist([0x50, 0x00, 0x34, len(bytes) + 4, 0x00, mid, pid // 256, pid % 256])
    answer.fromlist(bytes)
    return _finished_packet(answer)

def create_broadcast_list_packet(list_number, mid, rate, pids):
    list_number = int(list_number)
    if list_number < 1 or list_number > 8:
        raise EInvalidValue
    rate = int(float(rate) * 2)
    if rate > 255:
        raise EInvalidValue
    if not type(mid) == types.IntType:
        mid = _hex_str_2_int(mid)
    answer = array.array('B')
    answer.fromlist([0x50, 0x00, 0x13, 21, list_number, mid, rate, 0, 0])
    for pid in pids:
        if not type(pid) == types.IntType:
            pid = _hex_str_2_int(pid)
        answer.fromlist([pid // 256, pid % 256])
    if len(pids) < 8:
        for i in range(8-len(pids)):
            answer.fromlist([0,0])
    return _finished_packet(answer)


def _activate_broadcast_list_packet(iid, list_number):
    list_number = int(list_number)
    if list_number < 1 or list_number > 8:
        raise EInvalidValue
    answer = array.array('B')
    answer.fromlist([0x50, 0x00, iid, 0x01, list_number])
    return _finished_packet(answer)

def activate_broadcast_list_packet(list_number):
    return _activate_broadcast_list_packet(0x11, list_number)

def deactivate_broadcast_list_packet(list_number):
    return _activate_broadcast_list_packet(0x12, list_number)

def _finished_packet(answer):
    _append_crc(answer)
    answer = _byte_array_2_ascii_hex_char_array(answer)
    answer.fromstring('\r')
    return answer
    
def _hex_str_2_int(s):
    if not type(s) in types.StringTypes:
        s = s.tostring()
    if s.find('0x') < 0:
        s = '0x' + s
    return eval(s)

def _hex_str_2_byte_array(char_array_or_string):
    answer = array.array('B')
    if not type(char_array_or_string) in types.StringTypes:
        char_array_or_string = char_array_or_string.tostring()
    for i in range(0, len(char_array_or_string), 2):
        answer.append(_hex_str_2_int(char_array_or_string[i:i+2]))
    return answer

def _byte_array_2_ascii_hex_char_array(byte_array):
    answer = array.array('c')
    for byte in byte_array:
        answer.fromstring('%02X' % byte)
    return answer

def _append_crc(packet):
    sum = 0
    for b in packet:
        sum += b
    sum = 0 - sum
    sum %= 256
    packet.append(sum)
    return packet

def _check_crc(packet):
    sum = 0
    for b in packet:
        sum += b
    sum %= 256
    return sum == 0


class CCMLineHandler:
    def __init__(self, port):
        self.port = port
        self._lock = threading.Lock()  #for coordinating between threads 
        self._condition = threading.Condition(self._lock)
        self._mutex = threading.Lock()  #allow only one exclusive access at a time
        self._running = 0
        self._thread = None
        self.debug = debug
        self._offline = 0
        self.point_dictionary = {}
        self.broadcast_lists = {}
        self.password = ''
        
    def _wait_for_values(self, timeout):
        self._lock.acquire()
        try:
            self._condition.wait(timeout) #timeout in seconds
            if self.debug > 2: print 'done waiting'
        finally:
            self._lock.release()
    
    def _notify_waiting(self):
        self._lock.acquire()
        try:
            if self.debug > 2: print 'notifying'
            self._condition.notify()
        finally:
            self._lock.release()
    
    def start(self, password):
        self.password = array.array('B', password).tolist()
        if not self._running:
            if self.port.is_open() == 0:
                self.port.open()
                if self.debug: print '***port opened'
            self._running = 1
            self._thread = threading.ImmortalThread(target=self._run,args=())
            self._thread.start()
            if self.debug: print '***started new thread for ccm'
        else:
            raise EAlreadyRunning
    
    def stop(self):
        self._running = 0

    def _run(self):
        timeouts = 0
        print '***cat ccm receive thread running***'
        #while 1:
            #try:
                #self._initialize()
                #break
            #except ETimeout:
                #self.port.poll_input(2000)
        while self._running:
            # allow 2 seconds for timeout before
            # sending a heartbeat.
            if not self.port.poll_input(2000):
                #if timeouts > 10:
                    #timeouts = 0
                    #self._heartbeat()
                #else:
                if self.debug > 2: print 'timeouts: ', timeouts
                timeouts = timeouts + 1
            else:
                timeouts = 0
                self._read_input()
        else:
            self._thread.should_die()

    def _read_input(self):
        message = array.array('c')
        self.port.read(message, 8, 2) # read header of response or broadcast packet
        self._outstanding_heartbeats = 0
        while message and (message[:4].tostring() != '5001'):
            message.pop(0) #remove first char and try again
            self.port.read(message, 1, 1) #read one more to hopefully complete the header
            continue
        #at this point we have 8 chars beginning with a 5.  Check out what we can
        expected_length = _hex_str_2_int(message[6:])
        iid = _hex_str_2_int(message[4:6])
        if iid not in [BROADCAST_RESPONSE, STATUS_RESPONSE, READ_RESPONSE, WRITE_RESPONSE]:
            if self.debug: print 'iid not valid: ', str(iid)
            return
        #read the rest of the packet
        self.port.read(message, expected_length * 2 + 3, 1)   #read expected bytes plus two checksum chars plus a <cr>
        if self.debug: print repr(message)
        packet = _hex_str_2_byte_array(message[:-1]) #convert to byte array
        if not _check_crc(packet):
            if self.debug: print 'bad crc for :', message
            return
        # we've got a good one
        if iid == BROADCAST_RESPONSE:
            self._process_broadcast_response(packet)
        elif iid == STATUS_RESPONSE:
            self._process_status_response(packet)
        elif iid == READ_RESPONSE:
            self._process_read_response(packet)
        elif iid == WRITE_RESPONSE:
            self._process_write_response(packet)
        else:
            raise Exception
        
    def _process_broadcast_response(self, packet):
        if self.debug: print 'broadcast message recieved'
        if self.broadcast_lists.has_key(int(packet[4])):
            self.broadcast_lists[int(packet[4])] = packet
        else:
            if self.debug: 
                print 'ccm received bogus broadcast response packet'
                print repr(packet)
                print repr(packet[4]), repr(int(packet[4]))

    def _process_status_response(self, packet):
        if self.debug: print 'status response received'
        self._ack_rcvd = 1
        self._notify_waiting()

    def _process_read_response(self, packet):
        if self.debug: print 'read response received'
        mid = packet[4]
        pid = packet[5] * 256 + packet[6]
        if self.point_dictionary.has_key((mid,pid,)):
            self.point_dictionary[(mid,pid,)] = packet[:-1] #strip off crc
            self._notify_waiting()
        else:
            if self.debug: print 'ccm received read response for wrong mid,pid', str((mid,pid,)), str(self.point_dictionary)

    def _process_write_response(self, packet):
        if self.debug: print 'write response received'
        # we could retrieve value from response if we wanted but for now just ack it
        self._ack_rcvd = 1
        self._notify_waiting()
        
    def _send_packet_and_wait_for_ack(self, packet, timeout=2):
        self._mutex.acquire()
        try:
            for i in range(3): #try three times to send packet
                if self.debug: 
                    print 'ccm writing packet: %s' % str(packet)
                self._ack_rcvd = 0
                self.port.write(packet)
                #now wait for ack to come back
                _timeout = timeout
                t_end = time.time() + timeout
                while (self._ack_rcvd == 0) \
                       and _timeout >= 0:
                    try:
                        self._wait_for_values(_timeout)
                        if self.debug > 2: print 'notified of ack'
                    except ETimeout:
                        if self.debug: print 'ack wait timed out'
                        break
                    _timeout = t_end - time.time()
                if self._ack_rcvd: return #yipee
                if self.debug: print 'ccm ack timeout'
            if self.debug: print 'ccm send packet failure due to timeouts'
            raise ETimeout
        finally:
            self._mutex.release()

    def _read_single_parameter(self, mid, pid, timeout=2):
        self._mutex.acquire()
        try:
            #key = (mid,pid,)
            packet, key = read_single_parameter_packet(mid,pid)
            for i in range(3):
                self.point_dictionary[key] = None
                if self.debug: 
                    print 'writing ccm to port: %s' % str(packet.tolist())
                self.port.write(packet)
                _timeout = timeout
                t_end = time.time() + timeout
                while (self.point_dictionary[key] == None) \
                      and _timeout  >= 0:
                    try:
                        self._wait_for_values(_timeout)
                        if self.debug > 2: print 'notified'
                    except ETimeout:
                        if self.debug: print 'wait timed out'
                        break
                    _timeout = t_end - time.time()
                value = self.point_dictionary[key]
                if self.debug: print 'type(value) = %s' % type(value)
                del(self.point_dictionary[key])
                if value != None:
                    self._offline = 0 #allow retries next time since this point did respond
                    return value
                if self._offline: #known bad point
                    raise ETimeout()
                self._offline = 1 #don't wait around for retries on this point, it's not responding
            raise ETimeout()  #fail after third timeout
        finally:
            self._mutex.release()
            pass
        pass

    def read_single_parameter(self, mid, pid, timeout=2):
        try:
            return self._read_single_parameter(mid, pid, timeout)
        except ETimeout:
            self._login()
            return self._read_single_parameter(mid, pid, timeout)
                            
    def write_single_parameter(self, mid, pid, bytes):
        packet = write_single_parameter_packet(mid, pid, bytes)
        self._send_packet_and_wait_for_ack(packet)

    def create_broadcast_list(self, list_number, mid, rate, pids):
        packet = create_broadcast_list_packet(list_number, mid, rate, pids)
        self.broadcast_lists[int(list_number)] = None
        self._send_packet_and_wait_for_ack(packet)
            
    def activate_broadcast_list(self, list_number):
        packet = activate_broadcast_list_packet(list_number)
        self._send_packet_and_wait_for_ack(packet)

    def deactivate_broadcast_list(self, list_number):
        packet = deactivate_broadcast_list_packet(list_number)
        self._send_packet_and_wait_for_ack(packet)

    def _login(self):
        answer = self._read_single_parameter(0x61, 0xF012, 1)
        if self.debug: print 'ccm login: ',str(answer)
        self.write_single_parameter(0x61, 0xAA8A, self.password)
        






"""

from mpx.lib.caterpillar import cat_lib
from mpx.lib.node import as_node

p = as_node('/interfaces/com1')
p.open()

lh = cat_lib.CCMLineHandler(p)
lh.start()
lh.read_single_parameter(0x61,0xF012)
lh.write_single_parameter(0x61,0xAA8A,[])

lh.stop()
reload(cat_lib)

lh.create_broadcast_list(1, 0x58, 0, [0x0040,0x0054,0x0044,0x005e,0x0080,'0xf013','0xf08f','0xf0b0'])
lh.create_broadcast_list(1, 0x58, 2, [0x0040,0x0054,0x0044,0x005e,'0xf013','0xf08f','0xf0b0',0x0042])
lh.activate_broadcast_list(1)
lh.deactivate_broadcast_list(1)

"""

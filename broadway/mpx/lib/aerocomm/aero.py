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
#!/usr/bin/env python-mpx
import struct
import select
from termios import *
from mpx.lib import threading, msglog
import array, types
import Queue
from mpx.lib.exceptions import ETimeout, EInvalidValue
from mpx.lib.datetime import TimeOfDay
import time

STRING = 0
HEX = 1
INT = 2
BIT = 3
MAC = 4

start_time = time.time()
##
# MacAddress wrapper
# accepts mac address values in the forms:
#   00:01:02:03:04:05 or 00 01 02 03 04 05 or 00_01_02_03_04_05 or 00... well, you get the idea.
#   binary string: '\x00\x01\x02\x03\x04\x05'
#   [0,1,2,3,4,5] or (0,1,2,3,4,5)
#   4328719365L
#   an instance of a MacAddress
# prints in the 00:01:... format
#
class MacAddress:
    def __init__(self, value=None):
        self.value = '\x00\x00\x00\x00\x00\x00'
        if value:
            if (type(value) == types.ListType) or (type(value) == types.TupleType): #mac address as list of numbers
                if len(value) != 6: raise EInvalidValue('mac address must be 6 bytes')
                self.value = apply(struct.pack, ('BBBBBB',) + tuple(value))
            if (type(value) == types.StringType) or (type(value) == types.StringTypes): #mac address as string
                if len(value) == 17: # in the form 00:00:00:00:00:00 or 00 00 00 00 00 00
                    temp = []
                    for i in range(6):
                        temp.append(eval('0x' + value[i*3:(i*3)+2]))
                        if i < 5: #test for proper format
                            if not value[(i*3)+2] in (':', ' '): raise EInvalidValue('mac address bad format')
                    self.value = apply(struct.pack, ['BBBBBB'] + temp)
                elif len(value) == 6: 
                    self.value = value
                elif len(value) == 12: #straight hex 010203040506
                    temp = []
                    for i in range(6):
                        temp.append(eval('0x' + value[i*2:(i*2)+2]))
                    self.value = apply(struct.pack, ['BBBBBB'] + temp)
                else:
                    raise EInvalidValue('mac address must be 6 bytes')
            if type(value) == types.LongType:  #mac address as long integer
                temp = []
                for i in range(6):
                    temp.append(value & 255)
                    value = value >> 8
                if value > 0: raise EInvalidValue('mac address number too large')
                temp.reverse()
                self.value = apply(struct.pack, ['BBBBBB'] + temp)
            if type(value) == types.InstanceType: #must be another macaddress
                if value.__class__ != MacAddress: raise EInvalidValue('mac address wrong class')
                self.value = value.value
    def __str__(self):
        answer = ''
        for c in self.value:
            answer += '%2.2x:' % ord(c)
        return answer[:-1]
    def __hash__(self):
        return hash(self.value)
    def __cmp__(self, o):
        if o.__class__ == MacAddress:
            o = o.value
        return cmp(self.value, o)
        
        
class aero(threading.ImmortalThread):
    debug = 0

    speeds = {
        300: B300,
        2400: B2400,
        4800: B4800,
        9600: B9600,
        19200: B19200,
        38400: B38400,
        57600: B57600,
        115200: B115200,
    }
    aero_speeds = {
        0xf484: 300,
        0xfe91: 2400,
        0xff48: 4800,
        0xffa4: 9600,
        0xffd2: 19200,
        0xffe1: 28800,
        0xffe9: 38400,
        0xfff1: 57600,
    }
    eeprom_parameters = {
                            #addr len r/w,type, range or enum, description
        'version'          : (0x1d, 8, 0, STRING, None,     'Software Version Number'),
        'address'          : (0x28, 6, 0, MAC,    None,     'IEEE MAC Address'),
        'channel'          : (0x2e, 1, 1, INT,    (0,0x4c), 'Channel'),
        'transmit_attempts': (0x2f, 1, 1, INT,    None,     'Transmit Attempts'),
        'rxmode'           : (0x31, 1, 1, INT,    (1, 3),   'Receive Mode'),
        'range_refresh'    : (0x32, 1, 1, INT,    (0x20, 0x32), 'Range Refresh'),
        'mode'             : (0x33, 1, 1, INT,    (1, 2),   'Client/Server Mode'),
        'system_id'        : (0x34, 8, 1, HEX,    None,     'System ID Number'),
        'serial_speed'     : (0x40, 2, 1, INT,    aero_speeds, 'Baud Rate'),
        'serial_mode'      : (0x4a, 1, 1, BIT,    (0, 3),   'Serial Interface Mode'),
        'RTS_enable'       : (0x4a, 1, 1, BIT,    (3, 1),   'RTS Handshaking 1=enable, 0=disable'),
        'modem_mode'       : (0x4a, 1, 1, BIT,    (6, 1),   'Modem Mode 1=enable lines'),
        'power_down'       : (0x4a, 1, 1, BIT,    (7, 1),   'Power Down Sleep Mode 1=enable'),
        'txmode'           : (0x4b, 1, 1, INT,    (0, 1),   'Transmit Mode'),
        'read_switches'    : (0x4c, 1, 1, BIT,    (1, 1),   'Read Switches 1=enable read'),
        'end_type'         : (0x4c, 1, 1, BIT,    (2, 1),   'End Type (transparent mode only)'),
        'limit_rf_buffer'  : (0x4c, 1, 1, BIT,    (4, 1),   'Limit RF Buffers to 1'),
        'rf_priority'      : (0x4c, 1, 1, BIT,    (5, 1),   'RF Interrupt Priority'),
        'mixed_mode'       : (0x4c, 1, 1, BIT,    (7, 1),   'Allow transparent client to operate with server in API mode'),
        'interface_timeout'	:(0x4d, 1, 1, INT,    (0,0x40,0x80,0xc0), 'Interface Timeout wait before transmitting'),
        'broadcast_attempts':(0x4e,1, 1, INT,    None,     'Number of times to broadcast packets'),
        'turbo_mode'       : (0x4f, 1, 1, BIT,    (1, 1),   'Disable random backoff CSMA if 1'),
        'baud_rate_double' : (0x4f, 1, 1, BIT,    (4, 1),   'Doubles Baud Rate if true'),
        '485_rts'          : (0x4f, 1, 1, BIT,    (5, 1),   'TX/RX Enable for RS-485 systems'),
        'in_range_select'  : (0x4f, 1, 1, BIT,    (6, 1),   'Select pin for In-Range'),
        'auto_destination' : (0x4f, 1, 1, BIT,    (7, 1),   'Auto Destination for Transparent mode'),
        'destination_mac'  : (0x50, 6, 1, MAC,    None,     'Destination IEEE MAC Address for Transparent modes'),
        'sleep_time'       : (0x7a, 3, 1, INT,    (0, 255), 'Sleep Time for client sleep walk mode'),
        'wait_time'        : (0x7d, 3, 1, INT,    (0, 255), 'Wait Time for client sleep walk mode'),
    }
    all = '\xff\xff\xff\xff\xff\xff'
    def __init__(self, port):
        threading.ImmortalThread.__init__(self)
        self.rx_event = threading.Event()
        self.rf_event = threading.Event()
        self.rf_queue = Queue.Queue(50)
        self.port = port #open(port, 'r+', 0)
        #self.port.debug = self.debug
        #self.debug = 1
        self.devices = []  
        self.timeout = 0.5 #seconds
        self.last_status = None
 
    def runtime(self):
        return time.time() - start_time
    def run(self):
        while self._continue_running:
            if self.debug:
                print 'Waiting for message %f ' % (self.runtime())
            self.port.poll_input()
            if self.debug > 1: print 'data available, read it in'
            if not self._continue_running: return
            command, length, data, checksum = self.receive()
            if self.debug:
                print 'RX: %f %2.2x %4.4x %s %2.2x' % (self.runtime(), command, length, self.hexdump(data), checksum)

            # Solicited responses
            if command in (0x80, 0x82, 0x87, 0x8b, 0x8c, 0x8e, 0xaa):
                self.message = (command, length, data, checksum)
                self.rx_event.set()
                continue

            # Unsolicited messages
            if command in (0x83, 0x84, 0x85):
                self.process_message(command, length, data, checksum)
                continue

            print 'Unrecognized aerocomm message!'
            pass
    def process_message(self, command, length, data, checksum):
        if command == 0x83:
            if self.debug > 1: print '** process message: ', self.hexdump(data)
            dest, src = struct.unpack('6s6s', data[0:12])
            payload = data[12:]
            self.rf_queue.put((MacAddress(src), payload))
            if self.debug > 1: print '** process message done', self.rf_queue.qsize()
        if command == 0x84:
            if self.debug: print 'In range:', self.hexdump(data)
            self.devices.append(data)
        if command == 0x85:
            if self.debug: print 'Out of range:', self.hexdump(data)
            status = self.status(1)
            self.devices = []
            for device in status['devices']:
                self.devices.append(device[0])

    def update_device_list(self):
        status = self.status(1)
        new_list = []
        for device in status['devices']:
            new_list.append(device[0])
        self.devices = new_list

    def show_devices(self):
        print '%d' % len(self.devices),
        if len(self.devices) == 1:
            print 'device is',
        else:
            print 'devices are',
        print 'in range.'
        for device in self.devices:
            print '  %s' % str(device)
    ##
    # send aerocomm command along with payload data
    #
    def send(self, command, data):
        self.rx_event.clear() #should not be neccessary
        self.msg = struct.pack('<BH', command, len(data)) + data
        self.msg = self.msg + struct.pack('B', self.checksum(self.msg))
        self.port.write(self.msg)
        self.port.flush()
        if self.debug:
            print 'TX: %f %2.2x  data: %s' % (self.runtime(), command, self.hexdump(self.msg))
    ##
    # receive data from port
    # device thread uses this to receive all traffic from port
    #
    def receive(self):
        #dbg_buf = array.array('c')
        buffer = array.array('c')
        self.port.read(buffer, 3, 1) #once poll indicates data is available, no more than 1 second per character allowed
        self.header = buffer.tostring()
        #dbg_buf.extend(buffer)
        command, length = struct.unpack('<BH', self.header)
        buffer = array.array('c')
        data = self.port.read(buffer, length, 1)
        data = buffer.tostring()
        #dbg_buf.extend(buffer)
        buffer = array.array('c')
        self.port.read(buffer,1,1)
        checksum = ord(buffer[0])
        #dbg_buf.extend(buffer)
        #if ('\xf1' in data[13:]): # skip initial, expected f1
            #hex_str = ''
            #for c in dbg_buf:
                #hex_str += (' %x' % ord(c))
            #msglog.log('mpx:aero',msglog.types.INFO,hex_str)
        return (command, length, data, checksum)

    def checksum(self, data):
        result = 0
        for byte in data:
            result ^= ord(byte)
        return result

    def hexdump(self, data):
        s = ''
        for byte in data:
            s += '%2.2x ' % ord(byte)
        return s

    ##
    # wait for response to solicited command
    # use recv below to wait for unsolicited traffic
    #
    def get_response(self):
        if self.debug: print 'Waiting for Rx event'
        self.rx_event.wait(self.timeout)
        if self.debug: print 'Got RX event or timeout'
        if self.rx_event.isSet():
            if self.debug: print 'RX event was set'
            self.rx_event.clear()
            return self.message
        if self.debug: '!!!!! %f get_response raise ETimeout' % (self.runtime())
        raise ETimeout('Aerocomm driver command response Timeout',str(self),'Aerocomm')

    def init_radio(self):
        result = 0
        # Attempt to configure (hopefully) attached Aerocomm Server Radio:
        api_ee_chksum_req = array.array('B',[0x8d,0,0,0x8d])
        response = array.array('B')
        try:
            api_ee_chksum_req.tofile(self.port.file)
            self.port.read(response, 5, 3.0) # expect 5-byte response
            if (response[0] != 0x8e) \
               or (response[1] != 0x01) \
               or (response[2] != 0x00):
                msglog.log('mpx',msglog.types.ERR,'Aerocomm Transceiver responded to an API command ' \
                           'with unexpected bytes. Transceiver is in unknown serial mode.')
            elif response[3] == 0:
                msglog.log('mpx',msglog.types.WARN,'Aerocomm Transceiver\'s EEPROM checksum is invalid. ' \
                           'Transceiver is in API serial mode. Attempting to validate checksum...')
                api_ee_chksum_upd = array.array('B',[0x8c,0,0,0x8c])
                api_ee_chksum_upd.tofile(self.port.file)
                response = array.array('B')
                self.port.read(response, 4, 3.0) # expect 4-byte response
                if response != api_ee_chksum_upd:
                    msglog.log('mpx',msglog.types.WARN,'Could not validate Aerocomm Transceiver EEPROM checksum.')
                else:
                    msglog.log('mpx',msglog.types.INFO,'Validated Aerocomm Transceiver EEPROM checksum.')
            elif response[3] == 1:
                msglog.log('mpx',msglog.types.INFO,'Aerocomm Transceiver is in API serial mode, with valid EEPROM checksum.')
            else:
                msglog.log('mpx',msglog.types.ERR,'Aerocomm Transceiver responded to a request for EEPROM checksum ' \
                           'validity with unexpected value. Transceiver is in API serial mode.')
        except ETimeout, e:
            try:
                self.port.write('AT+++\r')
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATW4A?\r')     # read current Serial Interface Mode
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATW4A=03\r')   # set Serial Interface Mode to "API"
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATW31?\r')     # read current Rx Mode
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATW31=01\r')   # set Rx Mode to "Unicast/Broadcast"
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATW33?\r')     # read current Server/Client Mode
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATW33=01\r')   # set Server/Client Mode to "Server"
                self.port.read_upto(response,['\r'],3.0)
                response = array.array('B')
                self.port.write('ATZ\r')
                self.port.read_upto(response,['\r'],3.0)
                result = 1
            except ETimeout, e:
                msglog.log('mpx',msglog.types.ERR,'Aerocomm radio failed to respond to both an API and an AT command. ' \
                           'Cannot communicate with radio via serial link. Check cable and COM port settings.')
        return result

    def reset(self):
        if self.debug:
            print 'Sending reset message'
        self.rx_event.clear()
        self.rf_event.clear()
        self.send(0xaa, '')
        command, length, data, checksum = self.get_response()
        # Check for correct acknowledge, command and checksum bytes
        if command == 0xaa and checksum == 0xab:
            return 0
        else:
            return 1

    def control(self, data):
        self.send(0x86, data)
        return self.get_response()
        
    def read_ee(self, address, length):
        subcommand = struct.pack('<BHH', 0x02, address, address + length - 1)
        command, length, response, checksum = self.control(subcommand)
        if self.debug:
            print self.hexdump(response)
        return response[1:]

    def nop(self):
        subcommand = struct.pack('B', 0x08)
        command, length, response, checksum = self.control(subcommand)
        if response == '\x08\x00':
            return 0
        else:
            return 1

    def write_ee(self, addr, _len, data):
        subcommand = struct.pack('<BHH' + '%d' % len(data) + 's', 0x09, addr, addr + _len - 1, data)
        command, length, response, checksum = self.control(subcommand)
        return (response[1])

    def get_ee_parameter(self, name):
        addr, length, rw, type, _range, desc = self.eeprom_parameters[name]
        if self.debug: print 'addr', addr, 'length', length, rw, 'type', type, range, desc
        value = self.read_ee(addr, length)
        if self.debug: print 'value:', str(value)
        if type == STRING:
            return value #it is already a string
        if type == MAC:
            return MacAddress(value)
        if type == HEX:
            answer = 0
            if self.debug: print range(length)
            for i in range(length):
                if self.debug: print 'i:', i
                answer *= 256
                answer += struct.unpack('B', value[i])[0]
            return hex(answer) #.upper()
        if type == INT:
            answer = 0
            for i in range(length):
                if self.debug: print 'i:', i
                answer *= 256
                answer += struct.unpack('B', value[i])[0]
            return answer
        if type == BIT:
            pos, len = _range
            return (ord(value) >> pos) & ((2 ** len) - 1)
        raise EIvalidValue('unknown type', type, 'aerocomm get_ee_parameter')
#as_node('/interfaces/com1').children_nodes()[0].driver
    def set_ee_parameter(self, name, value):
        addr, length, rw, type, _range, desc = self.eeprom_parameters[name]
        if rw == 0:
            raise EPermission('attempt to set read only parameter', addr, 'Aerocomm driver')
        if type == MAC:
            return self.write_ee(addr, length, MacAddress(value).value)
        if type == BIT:
            old_value = self.get_ee_parameter(name)
            pos, len = _range
            old_value &= _bitfield_mask(pos, len) #clean out bits for new value
            value = _int2bitfield(value, pos, len)
            value |= old_value
            type = INT
        if type == HEX or type == INT:
            value = int(value)            
            s = []
            for i in range(length):
                s.append(value & 255)
                value = value // 256
            s.append(str(length)+'B')
            s.reverse()
            answer = apply(struct.pack, s)
            return self.write_ee(addr, length, answer)
        raise EInvalidValue('unknown type', type, 'aerocomm set_ee_parameter')
         
    def status(self, reset=0):
        data = struct.pack('B', reset)
        self.send(0x8a, data)
        command, length, response, checksum = self.get_response()
        if self.debug:
            print hex(command), hex(length), self.hexdump(response), hex(checksum)
        t = struct.unpack('<BBBLLLLB', response[0:20])
        ts = (t[0] + (t[1] * 256) + (t[2] * 65536)) / 4.0 #increments in 250ms intervals

        result = {}
        result['time'] = str(TimeOfDay(ts))
        result['txfail'] = t[3]
        result['txretry'] = t[4]
        result['rxfail'] = t[5]
        result['rxretry'] = t[6]
        result['count'] = t[7]

        if self.debug:
            print 'Found %d' % result['count'],
            if result['count'] == 1:
                print 'device'
            else:
                print 'devices'

        txlist = []
        for n in range(0, result['count']):
            offset = 20 + (n * 12)
            if self.debug:
                print self.hexdump(response[offset:offset+12])
            entry = struct.unpack('6sBBBBBB', response[offset:offset+12])
            time_stamp = str(TimeOfDay(entry[1:4]))
            packet_count = entry[4] << 16 + entry[5] << 8 + entry[6]
            txlist.append((MacAddress(entry[0]), time_stamp, packet_count))
        result['devices'] = txlist
        self.last_status = result
        return result

    def update_ee_checksum(self):
        self.send(0x8c, '')
        command, length, response, checksum = self.get_response()
        if command == 0x8c and checksum == 0x8c:
            return 0
        else:
            return 1

    def check_ee_checksum(self):
        self.send(0x8d, '')
        command, length, data, checksum = self.get_response()
        if command == 0x8e and data[0] == '\x01' and checksum == 0x8e:
            return 0
        else:
            return 1

    def rf_enable(self):
        self.send(0x80, '')
        command, length, response, checksum = self.get_response()
        if command == 0x80 and checksum == 0x80:
            return 0
        else:
            return 1

    def send_data(self, data):
        self.send(0x81, data)
        command, length, data, checksum = self.get_response()
        if command == 0x82 and data[0] == '\x00':
            return 0
        else:
            return 1

    def sendto(self, dest, source, data):
        return self.send_data(dest + source + data)

    def recv(self):
        return self.rf_queue.get(1)

    def check(self):
        try:
            msg = self.rf_queue.get_nowait()
            self.rf_queue.put(msg)
            return 1
        except:
            return 0 













    #def get_version(self):
        #return self.read_ee(0x1d, 8)

    #def get_address(self):
        #return self.read_ee(0x28, 6)

    #def get_channel(self):
        #return self.read_ee(0x2e, 1)

    #def set_channel(self, channel):
        #data = struct.pack('B', channel)
        #return self.write_ee(0x2e, 1, channel)

    #def get_transmit_attempts(self):
        #return self.read_ee(0x2f, 1)

    #def set_transmit_attempts(self, attempts):
        #data = struct.pack('B', attempts)
        #self.write_ee(0x2f, 1, data)

    #def get_rxmode(self):
        #return self.read_ee(0x31, 1)

    #def set_rxmode(self, mode):
        #data = struct.pack('B', mode)
        #self.write_ee(0x31, 1, data)

    #def get_range_refresh(self):
        #return self.read_ee(0x32, 1)

    #def set_range_refresh(self, range):
        #data = struct.pack('B', range)
        #self.write_ee(0x32, 1, data)
                                                                                                
    #def get_mode(self):
        #return self.read_ee(0x33, 1)
                                                                                                
    #def set_mode(self, mode):
        #data = struct.pack('B', mode)
        #self.write_ee(0x33, 1, data)
                                                                                                
    #def get_system_id(self):
        #return self.read_ee(0x34, 1)
                                                                                                
    #def set_system_id(self, system_id):
        #data = struct.pack('8s', system_id)
        #self.write_ee(0x34, 1, data)

    #def get_serial_speed(self):
        #s = self.read_ee(0x40, 2)
        #s, = struct.unpack('>H', s)
        #return self.aero_speeds[s]
                                                                                                
    #def set_serial_speed(self, speed):
        #aero_speed = 0
        #for s in self.aero_speeds.iteritems():
            #if speed == s[1]:
                #aero_speed = s[0]
        #if aero_speed:
            #data = struct.pack('>H', aero_speed)
            #self.write_ee(0x40, 2, data)
                                                 
    #def get_serial_mode(self):
        #return self.read_ee(0x4a, 1)
                                                                                                
    #def set_serial_mode(self, mode):
        #data = struct.pack('B', mode)
        #self.write_ee(0x4a, 1, data)
                                                                      
    #def get_txmode(self):
        #return self.read_ee(0x4b, 1)
                                                                                                
    #def set_txmode(self, mode):
        #data = struct.pack('B', mode)
        #self.write_ee(0x4b, 1, data)
                                                                                                

def _int2bitfield(value, pos=0, len=1):
    return (value & ((2 ** len) - 1)) << pos
def _bitfield_mask(pos=0, len=1):
    return (((2 ** len) - 1) << pos) ^ 255

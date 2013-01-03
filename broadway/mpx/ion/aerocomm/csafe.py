"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
from mpx import properties
from mpx.lib import msglog
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, get_attributes, set_attributes
from mpx.lib import threading
import time
from mpx.lib.exceptions import *
import array, struct, types
from mpx.lib.datetime import TimeOfDay
from mpx.lib.magnitude import MagnitudeInterface
from mpx.lib import EnumeratedDictionary
from mpx.lib.exceptions import ETimeout
from mpx.lib import debug as _debug

debug = 0

def who_is_message():
    return '\xf1\xf2'

status_text = EnumeratedDictionary({
        0: 'Error',
        1: 'Ready',
        2: 'Idle',
        3: 'HaveId',
        5: 'InUse',
        6: 'Paused',
        7: 'Finished',
        8: 'Manual',
        9: 'OffLine',
        })
units_text = EnumeratedDictionary({
        1: 'mile',
        2: 'tenth_mile',
        3: 'hundredth_mile',
        4: 'thousandth_mile',
        5: 'ft',
        6: 'inch',
        7: 'lbs',
        8: 'tenth_lbs',
        10: 'ten_ft',
        16: 'mile_per_hour',
        17: 'tenth_mile_per_hour',
        18: 'hundredth_mile_per_hour',
        19: 'ft_per_minute',
        33: 'Km',
        34: 'tenth_Km',
        35: 'hundredth_Km',
        36: 'Meter',
        37: 'tenth_meter',
        38: 'Cm',
        39: 'Kg',
        40: 'tenth_kg',
        48: 'Km_per_hour',
        49: 'tenth_Km_per_hour',
        50: 'hundredth_Km_per_hour',
        51: 'Meter_per_minute',
        55: 'Minutes_per_mile',
        56: 'Minutes_per_km',
        57: 'Seconds_per_km',
        58: 'Seconds_per_mile',
        65: 'floors',
        66: 'tenth_floors',
        67: 'steps',
        68: 'revolutions',
        69: 'strides',
        70: 'strokes',
        71: 'beats',
        72: 'calories',
        73: 'Kp',
        74: 'percent_grade',
        75: 'hundredth_percent_ grade',
        76: 'tenth_percent_ grade',
        79: 'tenth_floors_per_minute',
        80: 'floors_per_minute',
        81: 'steps_per_minute',
        82: 'revs_per_minute',
        83: 'strides_per_minute',
        84: 'strokes_per_minute',
        85: 'beats_per_minute',
        86: 'calories_per_minute',
        87: 'calories_per_hour',
        88: 'Watts',
        89: 'Kpm',
        90: 'Inch-Lb ',
        91: 'Foot-Lb ',
        92: 'Newton-Meters ',
        97: 'Amperes',
        98: 'Milliamps',
        99: 'Volts',
        100: 'Millivolts',
        })

class CSafe: #protocol framing and port handling
    def __init__(self, port):
        self.port = port
        self.timeout = 0.5
        self.properties = {
            'Version'             :('\x91', self.unpack_version, 0),
            'Serial_Number'       :('\x94', None, 0),
            #'List'                :('\x98', self.hexdump),
            'Utilization'         :('\x99', self.unpack_int24, 0),
            'Odometer'            :('\x9b', self.unpack_int32_units, 0),
            'Error_Code'          :('\x9c', self.unpack_int24, 0),
            'Workout_Time'        :('\xa0', self.unpack_time, 1),
            'Horizontal_Distance' :('\xa1', self.unpack_int16_units, 1),
            'Vertical_Distance'   :('\xa2', self.unpack_int16_units, 1),
            'Calories'            :('\xa3', self.unpack_int16, 1),
            'Program'             :('\xa4', self.unpack_2_bytes, 1),
            'Speed'               :('\xa5', self.unpack_int16_units, 1),
            'Grade'               :('\xa8', self.unpack_sint16_units, 1),
            'Gear'                :('\xa9', self.unpack_1_byte, 1),
            #'Uplist'              :('\xaa', self.hexdump),
            'User_Information'    :('\xab', self.unpack_user_data, 1),
            'Current_Heart_Rate'  :('\xb0', self.unpack_1_byte, 1),
            'Time_in_HR_Zone'     :('\xb2', self.unpack_time, 1),
            'Power'               :('\xb4', self.unpack_int16_units, 1),
            'Average_HR'          :('\xb5', self.unpack_1_byte, 1),
            'Maximum_HR'          :('\xb6', self.unpack_1_byte, 1),
            'Status'              :('\x80', self.unpack_status, 0),
            }
        self.cur_status = 1
        return
    def send_command(self, cmd):
        command = cmd
        checksum = self.checksum(command)
        if cmd: #only add checksum to packets with commands
            command += '%c' % checksum
        frame_contents = ''
        for byte in command: # byte stuffing
            if byte in ('\xf0', '\xf1', '\xf2', '\xf3'):
                frame_contents += '\xf3%c' % (ord(byte) & 0x03)
            else:
                frame_contents += byte
        #self.port.drain() #discard lingering packets
        self.port.write(array.array('c','\xf1' + frame_contents + '\xf2'))
        #time.sleep(0.2)
        while 1: #loop until response comes back or timeout
            msg = array.array('c')
            self.port.read_upto(msg, ['\xf1',], self.timeout)  #find beginning of response or timeout
            msg = array.array('c')
            if debug: print 'about to read upto f2'
            self.port.read_including(msg, ['\xf2',], 1)
            frame_contents = msg.tostring()
            if debug: print 'frame_contents: ', self.hexdump(frame_contents)
            msg = ''
            index = 0
            while frame_contents[index] != '\xf2':  #un stuff data segment
                byte = frame_contents[index]
                if byte == '\xf3':
                    index += 1
                    msg += '%c' % (ord(frame_contents[index]) | 0xf0)
                else:
                    msg += byte
                index += 1
                if index >= len(frame_contents):
                    msglog.log('csafe:send_command',msglog.types.ERR,'Comm error: Frame did not contain end character "f2".')
                    return (status_text[0],msg[3:-1]) # show Error
            #check checksum
            #if self.checksum(msg) != 0:
                #msglog.log('mpx:csafe',msglog.types.WARN,'Bad CSAFE checksum detected. New status = %u' % ord(msg[0]) & 0xF)
                #continue #bad check try again
            new_status = ord(msg[0]) & 0xF
            if (new_status == 1) and (self.cur_status == 9):
                msglog.log('mpx:csafe',msglog.types.INFO,'Detected OffLine To Ready: %s' % _debug.dump_tostring(msg))
            self.cur_status = new_status
            #print 'FEU %s sent %s' % (self.hexdump(addr), self.hexdump(msg))
            # seperate out the status
            status = ord(msg[0]) & 0xF
            try:
                status = status_text[status]
            except:
                pass #non-legal value for status
            if debug: print 'status: ', str(status)
                
            if len(msg) == 2:
                #print 'FEU state is now %2.2x' % ord(msg[0])
                if cmd == '\x80': #only return if this was a status request
                    return (status, msg[0],)
            else:
                if command[0] == '\xaa':
                    return (status, msg[2:-1],)
                else:
                    if command[0] == msg[1]: #only return if response matches request
                        return (status, msg[3:-1],)  #strip off status, command and checksum
            if debug: 
                print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! @@@ csafe rejected a response, look again'
                print self.hexdump(frame_contents), self.hexdump(cmd)

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
    def unpack_int16_units(self, msg):
        v, u = struct.unpack('<HB', msg)
        return CSafeUnitData(v, u)
    def unpack_sint16_units(self, msg):
        v, u = struct.unpack('<hB', msg)
        return CSafeUnitData(v, u)
    def unpack_int32_units(self, msg):
        if len(msg) != 5:
            print '**** UNPACK INT32 UNITS ERROR: ', self.hexdump(msg)
        v, u = struct.unpack('<LB', msg)
        return CSafeUnitData(v, u)
    def unpack_version(self, msg):
        return CSafeVersionData(msg)
    def unpack_int24(self, msg):
        if len(msg) < 3:
            return self.unpack_int16(msg)
        l, h = struct.unpack('<HB', msg)
        return (h * 65536) + l
    def unpack_time(self, msg):
        return TimeOfDay(struct.unpack('BBB', msg))
    def unpack_int16(self, msg):
        if len(msg) < 2:
            return self.unpack_1_byte(msg)
        return struct.unpack('<H', msg)[0]
    def unpack_2_bytes(self, msg):
        return CSafeProgramLevelData(struct.unpack('BB', msg))
    def unpack_1_byte(self, msg):
        return ord(msg[0])
    def unpack_user_data(self, msg):
        v,u, a, g = struct.unpack('<HBBB', msg)
        return CSafeUserData(v, u, a, g)
    def unpack_status(self, msg):
        try:
            return status_text[ord(msg[0]) & 15]
        except:
            return ord(msg[0]) & 15
    def get(self, prop_name):
        cmd, rsp, mode = self.properties[prop_name]
        for i in range(3):
            try:
                status, msg = self.send_command(cmd) #(status, payload)
                if debug: print 'response payload: ', self.hexdump(msg)
                if rsp: 
                    return (status, rsp(msg),)
                return (status, msg,)
            except ETimeout:
                if debug: print '@@@ csafe ate a timeout'
                continue
            except struct.error, e:
                msg_hex_str = ''
                for c in msg:
                    msg_hex_str += (str(ord(c)) + ' ')
                msglog.log('mpx:csafe',msglog.types.ERR,'Badly formatted status:msg (%s:%s) recvd from FEU %s' \
                           ', for property %s' % (status, msg_hex_str, self.port.name, prop_name))
                msglog.exception()
                return (None, None,)
            pass
        if debug: print '@@@@ tried three times with no joy'
        return (None, None,)
    ##
    # return 1 if this property is only available during offline mode
    def offline_mode(self, prop_name):
        cmd, rsp, mode = self.properties[prop_name]
        return mode

class CSafeUnitData(MagnitudeInterface):
    def __init__(self, value=None, units=None):
        self.units = units
        #if units:
            #self.units = units_text[units]
        MagnitudeInterface.__init__(self, value)
        #@todo extend to accept tuples or strings to initalize values (like bacnet datatypes)
        #      if and when we need to set values onto the FEU
    def __str__(self):
        answer = '[' + MagnitudeInterface.__str__(self) + ','
        if self.units is None:
            answer += 'None]'
        else:
            answer += "'" + str(int(self.units)) + "']"
        return answer

class CSafeUserData(CSafeUnitData):
    def __init__(self, value=None, units=None, age=None, gender=None):
        self.age = age
        self.gender = gender
        CSafeUnitData.__init__(self, value, units)
    def __str__(self):
        answer = CSafeUnitData.__str__(self)
        answer = answer[:-1] #trim off trailing ]
        if self.age:
            answer += ',' + str(self.age) + ','
        else:
            answer += ',None,'
        if self.gender:
            answer += str(self.gender) + ']'
        else:
            answer += 'None]'
        return answer
        
class CSafeProgramLevelData(MagnitudeInterface):
    def __init__(self, program_level=None):
        self.value = 0
        if program_level:
            if (type(program_level) == types.TupleType) or (type(program_level) == types.ListType):
                self.value = program_level[0] * 256 + program_level[1]
            else:
                self.value = program_level
        self._program = self.value // 256
        self._level = self.value & 255
    def __getattr__(self, attribute):
        if attribute == 'program':
            return self.value // 256
        if attribute == 'level':
            return self.value & 255
        return self.__dict__[attribute]
    def __setattr__(self, attribute, value):
        if attribute == 'program':
            self.value = ((value & 255) * 256) + (self.value & 255)
            return
        if attribute == 'level':
            self.value = (self.value & 0xFF00) + (value & 255)
            return
        self.__dict__[attribute] = value
    def __str__(self):
        return '[' + str(self.program) + ', ' + str(self.level) + ']'
    
class CSafeVersionData:
    def __init__(self, msg=None):
        self.value = '\x00\x00\x00\x00\x00\x00'
        self.manufacture_data = ''
        if msg:
            self.value = msg[0:5]
            self.manufacture_data = msg[5:]
    
    def __getattr__(self, attribute):
        if attribute == 'manufacturer':
            return ord(self.value[0])
        if attribute == 'CID':
            return ord(self.value[1])
        if attribute == 'model':
            return ord(self.value[2])
        if attribute == 'version':
            return ord(self.value[3])
        if attribute == 'release':
            return ord(self.value[4])
        return self.__dict__[attribute]
    def as_list(self):
        answer = struct.unpack('BBBBB', self.value)
        if len(self.manufacture_data) > 0:
            answer += struct.unpack('B' * len(self.manufacture_data), self.manufacture_data)
        return list(answer)
    def __str__(self):
        return str(self.as_list())
    def as_string_of_hex_values(self):
        self_list = self.as_list()
        result = ''
        for n in self_list:
            result += '\\x%02x' % n
        return result

    #def Get_Version(self):
        #msg = self.send_command('\x91')
        #return (msg[0:5], msg[5:])

    #def Get_Serial_Number(self):
        #msg = self.send_command('\x94')
        #return msg

    #def Get_List(self):
        #msg = self.send_command('\x98')
        #return self.hexdump(msg)
        
    #def Get_Utilization(self):
        #msg = self.send_command('\x99')
        #try:
            #l, m, h = struct.unpack('BBB', msg)
        #except:    #def Get_Version(self):
        #msg = self.send_command('\x91')
        #return (msg[0:5], msg[5:])

    #def Get_Serial_Number(self):
        #msg = self.send_command('\x94')
        #return msg

    #def Get_List(self):
        #msg = self.send_command('\x98')
        #return self.hexdump(msg)
        
    #def Get_Utilization(self):
        #msg = self.send_command('\x99')
        #try:
            #l, m, h = struct.unpack('BBB', msg)
        #except:
            #return self.hexdump(msg)
        #return l + (m << 8) + (h << 16)

    #def Get_Horizontal_Distance(self):
        #msg = self.send_command('\xa1')
        #try:
            #v, u = struct.unpack('<HB', msg)
        #except:
            #return self.hexdump(msg)
        #return (v, self.units[u])

    #def Get_Vertical_Distance(self):
        #msg = self.send_command('\xa2')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])

    #def Get_Calories(self):
        #msg = self.send_command('\xa3')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])

    #def Get_Speed(self):
        #msg = self.send_command('\xa5')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])

    #def Get_Upload(self):
        #msg = self.send_command('\xaa')
        #return self.hexdump(msg)
    #def Get_Odometer(self):
        #msg = self.send_command('\9b')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_Error_Code(self):
        #msg = self.send_command('\x9c')
        #return self.hexdump(msg)
    #def Get_Workout_Time(self):
        #msg = self.send_command('\xA0')
        #return self.hexdump(msg)
    #def Get_Grade(self):
        #msg = self.send_command('\9b')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_Gear(self):
        #msg = self.send_command('\9b')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_User_Information(self):
        #msg = self.send_command('\xAB')
        #return self.hexdump(msg)
    #def Get_Current_Heart_Rate(self):
        #msg = self.send_command('\xB0')
        #return self.hexdump(msg)
    #def Get_Time_in_HR_Zone(self):
        #msg = self.send_command('\xB2')
        #return self.hexdump(msg)
    #def Get_Power(self):
        #msg = self.send_command('\B4')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_Average_HR(self):
        #msg = self.send_command('\xB5')
        #return self.hexdump(msg)
    #def Get_Maximum_HR(self):
        #msg = self.send_command('\xB6')
        #return self.hexdump(msg)

            #return self.hexdump(msg)
        #return l + (m << 8) + (h << 16)

    #def Get_Horizontal_Distance(self):
        #msg = self.send_command('\xa1')
        #try:
            #v, u = struct.unpack('<HB', msg)
        #except:
            #return self.hexdump(msg)
        #return (v, self.units[u])

    #def Get_Vertical_Distance(self):
        #msg = self.send_command('\xa2')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])

    #def Get_Calories(self):
        #msg = self.send_command('\xa3')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])

    #def Get_Speed(self):
        #msg = self.send_command('\xa5')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])

    #def Get_Upload(self):
        #msg = self.send_command('\xaa')
        #return self.hexdump(msg)
    #def Get_Odometer(self):
        #msg = self.send_command('\9b')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_Error_Code(self):
        #msg = self.send_command('\x9c')
        #return self.hexdump(msg)
    #def Get_Workout_Time(self):
        #msg = self.send_command('\xA0')
        #return self.hexdump(msg)
    #def Get_Grade(self):
        #msg = self.send_command('\9b')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_Gear(self):
        #msg = self.send_command('\9b')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_User_Information(self):
        #msg = self.send_command('\xAB')
        #return self.hexdump(msg)
    #def Get_Current_Heart_Rate(self):
        #msg = self.send_command('\xB0')
        #return self.hexdump(msg)
    #def Get_Time_in_HR_Zone(self):
        #msg = self.send_command('\xB2')
        #return self.hexdump(msg)
    #def Get_Power(self):
        #msg = self.send_command('\B4')
        #v, u = struct.unpack('<HB', msg)
        #return (v, self.units[u])
    #def Get_Average_HR(self):
        #msg = self.send_command('\xB5')
        #return self.hexdump(msg)
    #def Get_Maximum_HR(self):
        #msg = self.send_command('\xB6')
        #return self.hexdump(msg)

#return status value as part of csafe data objects

        
"""
CSAFE Data Requirements 
General 
 This section provides lists of monitored FEU data points required to be read by the ICS.
 The Product will convert the raw data to a user readable form and add any necessary units.

Registration Data Points
 The following list of points represents the required data points to be read by the ICS for FEUs that have not been initiated by the CSAFE driver:

    Config File  FEU(CSAFE) Point   Notes
    SERIALnn     Serial Number
    VERSNnn      Version            Software Version
    MANFACnn     Manufacturer
    MODELnn      Model
    RLSEnn       Release number
    STATEnn      Status

* nn represents the arbitrary instance

 The points in the above list will be sent to the Product to compare the data with existing database records.
 If there is a discrepancy in the data that the ICS is reading and what the Product database has recorded then a ServiceAlert is issued

Ready Status Data Points
 The following list of points represents the required data points to be polled and logged by the ICS for FEUs in a ready state:

    Property   FEU (CSAFE) Point   Notes
    STATEnn    Status              Confirms Offline status

Offline Status Data Points
The following list of points represents the required data points to be polled and logged by the ICS: 

    Property   FEU (CSAFE) Point   Notes
    STATEnn    Status              
    UTILnn     Utilization         Hour meter
    ODOnn      Odometer
    PRGAMnn    Program
    LEVELnn    Program level
    TWKHRnn    Workout duration    Hours
    TWKMINnn   Workout duration    Minutes
    TWKSECnn   Workout duration    Seconds
    DSTHORnn   Horizontal distance 
    DSTVERnn   Vertical distance
    CLRIESnn   Calories
    SPEEDnn    Speed 
    GRADEnn    Grade               Incline
    GEARnn     Gear                Resistance
    USRSTnn    User Information    Weight, age, and gender
    HRCURnn    Current Heart Rate  If available
    ZNEHRnn    Heart rate Zone Hours
    ZNEMINnn   Heart rate Zone Minutes
    ZNESECnn   Heart rate Zone Seconds
    POWERrnn   Power               User's current calories/min
    HRAVG      Average heart rate
    HRMAX      Maximum heart rate


Error Status Data Points
The following list of points represents the required data points to be polled and logged by the SCS for FEUs in an error state:

    Property   FEU (CSAFE) Point  Notes
    STATEnn    Status             Confirms Offline status
    ERRCDEnn   Error Code         
    UTILnn     Utilization        Hour meter
    ODOnn      Odometer
"""
    
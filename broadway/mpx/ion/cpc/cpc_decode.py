"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import string
import array
import struct
import exceptions
from mpx.lib.debug import _debug

debug = 0
CSI = '\x1b[' #ANSI escape
CSI_Reset = CSI+'0m'
CSI_RED = CSI + '41;37;1m'
CSI_CYAN = CSI + '46;37;1m'
CSI_GREEN = CSI + '42;37;1m'

#import as_html

EInvalidResponse = exceptions.ValueError
EInvalidValue = exceptions.ValueError

debug = 0
## Packet exchange

    # Packets are exchanged in the following sequence:
    #  1) The mediator connects to the TCP socket 1025
    #  2) The mediator sends a DeviceListRequest
    #  3) The CPC sends a DeviceListResponse containing the names and index or ID number for each connected device
    #  4) The mediator sends a LoginRequest with the username password (usually USER / PASS)
    #  5) The CPC sends a LoginResponse - I don't know yet was a reject looks like
    #  6) Three more request / response exchanges.  Information is unknown
    #  6A) The fith response is followed or preceeded by a screen update command
    #  7) The mediator sends an inital page request
    #  8) The CPC respondes with a page update packets
    #  9) The mediator sends a page update request
    # 10) The CPC responds with any changes to the page values
    # 11) go back to step 9
    # 12) to shut down or switch to another device,  mediator sends LogoutRequest
    # 13) CPC response is LogoutResponse
    # 14) Goto setp 2 or 4 or close TCP port

## Packet objects
#header exception|CPCR            |  43 50 43 52 00 01 19 00 00 00 1B 00 00 00 02 00
#header exception|      <         |  00 00 01 01 01 01 3C 00 01 02 00

HEADER = 'CPCR\x00\x01\x19\x00\x00\x00'
SUB_HEADER = '\x05\x01\x00\x01\x01\x03\x00\x00\x00\x02\x00'
MIN_PKT_LEN = 26

RSP_SUB_HEADER_1 = '\x00\x00\x01\x01' #[16:18]
RSP_SUB_HEADER_2 = '\x01\x3c\x00' #\x00' #[21:25]
RSP_SUB_HEADER_2B = '\x01\x08\x00\x00' #[21:25]
RSP_UNIT_NAME_LEN = 23

class CPCRequest(object): #Common request elements
    def __init__(self, request_prototype, device_number = 0):
        self.request = array.array('B', request_prototype)
        self.request[18] = int(device_number)
    def __str__(self):
        return self.request.tostring()
    def __repr__(self):
        return repr(self.request)
        
class CPCResponse(object): #Common response elements
    def __init__(self, pkt):
        self.pkt = pkt
        try:
            self.parse_header(pkt)
        except:
            _debug.dump(pkt, 'header exception')
            raise
    def parse_header(self, pkt): #find all text elements in update
        #check header for length fields proper format
        if len(pkt) < MIN_PKT_LEN:
            raise EInvalidResponse('packet too short')
        if pkt[:10] != HEADER:
            raise EInvalidResponse('packet header is wrong')
        self.pkt_len = struct.unpack('H',pkt[10:12])[0]
        if len(pkt) < self.pkt_len:
            raise EInvalidResponse('packet is shorter than reported length')
        if len(pkt) > self.pkt_len:
            if debug: print CSI_RED+'Packet Length mismatch - possible concatentated packets'+CSI_Reset
        self.payload_len = struct.unpack('H',pkt[14:16])[0] 
        if self.payload_len + 25 != self.pkt_len:
            raise EInvalidResponse('payload length is shorter wrong')
        if pkt[16:20] != RSP_SUB_HEADER_1: #check that this is common to all packets
            raise EInvalidResponse('packet sub header part 1 is wrong')
        if pkt[21:24] != RSP_SUB_HEADER_2: #check that this is common to all packets
            if pkt[21:25] != RSP_SUB_HEADER_2B: #check that this is common to all packets
                raise EInvalidResponse('packet sub header part 2 is wrong')
        self.response_device_number = ord(pkt[20]) #@TODO Confirm?
        return

REQUEST_DEVICES = "CPCR\x00\x01\x19\x00\x00\x00\x1a\x00\x00\x00\x01\x00\x00"+\
                  "\x00\x00\x00\x00\x00\x32\x00\x00\x02"
                  
class DeviceListRequest(CPCRequest):
    def __init__(self):
        super(DeviceListRequest, self).__init__(REQUEST_DEVICES)
        
class DeviceListResponse(CPCResponse):
    def __init__(self, pkt):
        super(DeviceListResponse, self).__init__(pkt)
        self._units = {}
        self.device_count = None
        self.parse_device_list(pkt)
    def parse_device_list(self, pkt):
        self.device_count = ord(pkt[30]) #@TODO Confirm?
        offset = 32 #first device name starts here
        for i in range(self.device_count):
            name = pkt[offset:offset+9]
            name = name.split('\x00')[0] #strip off any trailing nulls
            unit_number = ord(pkt[offset + 15]) #need to verify
            self._units[name] = unit_number
            if debug:
                print 'device list unit: ', name, unit_number
            offset += RSP_UNIT_NAME_LEN
    def units(self):
        return self._units

REQUEST_LOGIN =  'CPCR\x00\x01\x19\x00\x00\x00\x3e\x00\x00\x00\x25\x00'+\
            '\x00\x00\xFF\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'+\
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'+\
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02'

class LoginRequest(CPCRequest):
    def __init__(self, device_number, username, password):
        super(LoginRequest, self).__init__(REQUEST_LOGIN, device_number)
        username = array.array('B', (username + '\x00' * 16)[:16])
        password = array.array('B', (password + '\x00' * 16)[:16])
        self.request[26:42] = username
        self.request[42:58] = password
        
class LoginResponse(CPCResponse):
    pass
    
REQUEST3 = "CPCR\x00\x01\x19\x00\x00\x00\x26\x00\x00\x00\x0d\x00\x00\x00"+\
           "\xFF\x01\x00\x00\x08\x00\x00\x00\x01\x00\xFF\x01\x04\x00\x00"+\
           "\x00\x01\x00\x01\x00"
           
class Request3(CPCRequest):
    def __init__(self, device_number):
        super(Request3, self).__init__(REQUEST3, device_number)
        self.request[28] = int(device_number)
        
class Response3(CPCResponse):
    pass
    
REQUEST4 = "CPCR\x00\x01\x19\x00\x00\x00\x26\x00\x00\x00\x0d\x00\x00\x00"+\
           "\xFF\x01\x00\x00\x08\x00\x00\x00\x01\x00\xFF\x01\x01\x00\x00"+\
           "\x00\x01\x00\x01\x00"
           
class Request4(CPCRequest):
    def __init__(self, device_number):
        super(Request4, self).__init__(REQUEST4, device_number)
        self.request[28] = int(device_number)
        
class Response4(CPCResponse):
    pass
    
REQUEST5 = "CPCR\x00\x01\x19\x00\x00\x00\x24\x00\x00\x00\x0b\x00\x00\x00"+\
           "\xFF\x01\x00\x00\x08\x00\x00\x00\x01\x00\xFF\x01\x05\x00\x00"+\
           "\x00\x01\x00"
           
class Request5(CPCRequest):
    def __init__(self, device_number):
        super(Request5, self).__init__(REQUEST5, device_number)
        self.request[28] = int(device_number)
        
class Response5(CPCResponse):
    pass
    
class InitScreenCmd(CPCResponse):
    pass
INIT_SCREEN_REQUEST = "CPCR\x00\x01\x19\x00\x00\x00\x45\x00\x00\x00\x2c\x00"+\
           "\x00\x00\xFF\x01\x00\x00\x3c\x00\x00\x08\x00\x01\x00\x04\x00\x00"+\
           "\x00\x01\x00\x01\x00\x05\x00\x01\x00\x00\x00\x01\x00\x02\x00\x00"+\
           "\x00\x01\x00\x03\x00\x00\x00\x02\x00\x04\x00\x00\x00\x01\x00\x05"+\
           "\x00\x00\x00\x01\x00"
           
class InitialScreenRequest(CPCRequest):
    def __init__(self, device_number):
        super(InitialScreenRequest, self).__init__(INIT_SCREEN_REQUEST, device_number)
        
class TextElement(object): #is a point name or value, id'd by XY location
    def __init__(self, text='', x=0, y=0):
        self.x = x
        self.y = y
        self.text = text
    def __eq__(self, o):
        if self.__class__ != o.__class__:
            return self == o
        return (self.x == o.x) and (self.y == o.y)
    def __ne__(self, o):
        return not self.__eq__(o)
    def __lt__(self, o):
        if self.__class__ != o.__class__:
            return self < o
        if self.y == o.y:
            return self.x < o.x
        return self.y < o.y
    def __gt__(self, o):
        if self.__class__ != o.__class__:
            return self > o
        if self.y == o.y:
            return self.x > o.x
        return self.y > o.y
    def __repr__(self):
        return '(%d,%d)=%s' % (self.x, self.y, self.text)
        
tokens = [0,1,2,3,4,5, 7,8,9,10,11,12,13,14,15] + range(0x20, 0x31) + [0x7F,]
class ScreenUpdate(object):
    def __init__(self, pkt):
        self.pkt = pkt
        self.texts = {}
        self.screen_cleared = 0
        self.parse_screen_update_header(pkt)
        self.parse_screen_update_body(pkt)
        self.sequence = ord(pkt[0x24]) #decode_xy(pkt[0x24:0x26]) 
    def parse_screen_update_header(self, pkt): #find all text elements in update
        #check header for length fields proper format
        if len(pkt) < MIN_PKT_LEN:
            raise EInvalidResponse('packet too short')
        if pkt[:10] != HEADER:
            raise EInvalidResponse('packet header is wrong')
        self.pkt_len = struct.unpack('H',pkt[10:12])[0]
        if len(pkt) < self.pkt_len:
            print 'packet length: ',len(pkt),' reported length: ', self.pkt_len
            raise EInvalidResponse('packet is shorter than reported length')
        self.payload_len = struct.unpack('H',pkt[14:16])[0] 
        if self.payload_len + 25 != self.pkt_len:
            raise EInvalidResponse('payload length is shorter wrong')
        #if pkt[25:36] != SUB_HEADER:
            #raise EInvalidResponse('packet header is wrong')
        self.pkt_count = ord(pkt[40]) # is zero for "screen complete" packet
        if self.pkt_count == 0:
            if debug > 1: print CSI_GREEN+'Screen Complete packet received'+CSI_Reset
        return
    def parse_screen_update_body(self, pkt):
        i = 0x2E #first token starts here
        while i < self.pkt_len:
            i = self._parse_screen_update_body(pkt, i)
            if i is None: return #success
            #failed to read entire packet.  Bad token or bad parameter.
            i += 1 #look at next byte and try it
            while (i < self.pkt_len) and (ord(pkt[i]) not in tokens):
                i += 1 #skip any bytes we know are not any good
    def _parse_screen_update_body(self, pkt, start):
        i = start
        last_i = i
        tokens = []
        x = 0
        y = 0
        token = None
        delimiter = 0
        try:
            while i < self.pkt_len: #don't run past end of valid data on catenated packets
                last_delimiter = delimiter
                delimiter = 0
                last_token = token
                token = ord(pkt[i])
                tokens.append((i,token,))
                #tokens.append((last_i,last_token,token,i-last_i))
                last_i = i
                if debug > 3:
                    print 'token: %X index: %X' % (token,i)
                if (token == 0 and last_token == 8) or \
                   (token == 8 and last_token == 0) or \
                   (token == 0 and last_token == 0x0F) or \
                   (token == 0x0F and last_token == 0) or \
                   (token == 0 and last_token == 0x0A) or \
                   (token == 0x0F and last_token == 0x0A) or \
                   (token == 0 and last_token == 0x09) or \
                   (token == 0x0F and last_token == 0x09) or \
                   (token == 0 and last_token == 0x0C): #text string or xy follows
                    str_len = ord(pkt[i+1])
                    if (str_len == 1) and (last_token != 8) and (last_token != 0) and (last_token != 0x0F):
                        i += 2
                        delimiter = 1
                        continue
                    if str_len > 0:
                        text = pkt[i+2:i+str_len+2]
                        text = text.split('\x00')[0] #some strings are zero terminated prior to the full length
                        text = text.strip() #remove leading and trailing whitespace.
                        if last_token != 0x0A: #this token preceeds raw binary
                            self.texts[(x,y)] = TextElement(text, x, y) #add text to our dict
                            if debug > 2:
                                print 'found text: ', text
                    i += str_len + 2
                    continue
                if (token == 0x08 or token == 0 or token == 0x0F): #back space - clear - so far the last token seems to always be 0D
                    if ord(pkt[i+1]) == 1: #DLE , next four bytes are not position
                        i += 2
                        delimiter = 1
                        continue
                    x,y = self.decode_xy(pkt[i+1:i+5])
                    if x > 640 or y > 640:
                        #raise EInvalidValue('token 8, 1st xy value wrong')
                        pass
                    i += 5
                    continue
                if token == 0x09: #define area
                    x,y = self.decode_xy(pkt[i+5:i+9])
                    flag = x == 640 and y == 434
                    if x > 640 or y > 640:
                        raise EInvalidValue('token 9, 2nd xy value wrong')
                    x,y = self.decode_xy(pkt[i+1:i+5])
                    if flag and x == 0 and y == 37:
                        self.texts = {} #a cleared screen has no values...
                        self.screen_cleared = 1 #let the screen object know
                        if debug > 1: print CSI_GREEN+'Clear Screen'+CSI_Reset
                            #clear all texts?
                    if x > 640 or y > 640:
                        raise EInvalidValue('token 9, 1st xy value wrong')
                    i += 9
                    continue
                if (token == 0x0A): # draw line... get new xy and continue
                    if ord(pkt[i+1]) == 1: #DLE , next four bytes are not position
                        i += 2
                        delimiter = 1
                        continue
                    if last_token == 0x0D: #so far just one case of non-10 length
                        i += 5
                        continue
                    if last_token == 0 and not last_delimiter:
                        l = ord(pkt[i+1]) + 2 #only have seen 80's here but it might different
                        if l == 80: #only have seen lengths of 80 bytes (640 bits) for this
                            i += l
                            continue
                    #when last 0 token was delimited, it is always an x,y packet
                    try:
                        x,y = self.decode_xy(pkt[i+1:i+5])
                        if x > 640 or y > 640:
                            raise EInvalidValue('token A, 1st xy value wrong')
                    except:
                        if last_token == 0: #last chance but I don't think we will see this happen
                            l = ord(pkt[i+1]) + 2
                            i += l
                            continue
                        raise
                    i += 10 #all other tokens follwing A have been 10 long
                    continue
                if token == 0x0B:
                    i += 32
                    continue
                if token == 0x0C: #text block
                    if ord(pkt[i+1]) == 1: #DLE , next four bytes are not position
                        i += 2
                        delimiter = 1
                        continue
                    if last_token == 0:
                        #no xy cords, just use xy from last 0 token
                        i += ord(pkt[i+1]) + 2
                        continue
                    x,y = self.decode_xy(pkt[i+1:i+5])
                    if x > 640 or y > 640:
                        raise EInvalidValue('token C, xy value wrong')
                    bl = ord(pkt[i+5]) #length of block following
                    bl += ord(pkt[i+6]) * 256 #don't know for sure about this second byte
                    i += (bl + 8)
                    continue
                if token == 0x0D: #new line
                    x,y = self.decode_xy(pkt[i+5:i+9])
                    if x > 640 or y > 640:
                        raise EInvalidValue('token D, 2nd xy value wrong')
                    x,y = self.decode_xy(pkt[i+1:i+5])
                    if x > 640 or y > 640:
                        raise EInvalidValue('token D, 1st xy value wrong')
                    i += 9
                    continue
                if token == 0x0E:
                    i += 2
                    continue
                if token == 0x03:
                    next_token = ord(pkt[i+1])
                    if next_token in (1,2,4,5): #add more 2nd bytes that inc index by 2
                        i += 2
                        continue
                    raise EInvalidValue('token 3, 2nd byte sucks')
                if token == 0x01:
                    i += 9
                    continue
                if token == 0x02:
                    i += 3 #ord(pkt[i+1]) + 2
                    continue
                if token == 0x04:
                    i += 2
                    continue
                if token == 0x05:
                    i += 3
                    continue
                if token == 0x07:
                    next_token = ord(pkt[i+1])
                    if next_token == 2:
                        i += 2
                        continue
                    raise EInvalidValue('token 7, 2nd byte sucks')
                if token == 0x7F:
                    i += 5
                    continue
                if token in range(0x20, 0x31):
                    i += 1
                    continue
                raise EInvalidValue('unknown token: %X index: %X' % (token,i))
        except:
            if debug and (start == 0x2E): #print this only once per packet
                print str(tokens)
                try:
                    _debug.dump(pkt, 'unknown token: %X index: %X' % (token,i))
                except:
                    _debug.dump(pkt, 'unknown token: '+str(token)+' index: '+str(i))
            return i #let caller know where the failure occured
        #scan for text elements and place into XY keyed dictionary
        #print str(tokens)
        return None #indicates success
    def decode_xy(self, str):
            return struct.unpack('HH', str)[:2]
    
ACK_UPDATE = "CPCR\x00\x01\x19\x00\x00\x00\x23\x00\x00\x00\x0a\x00\x00" +\
                 "\x00\xFF\x01\x00\x00\x3c\x00\x00\x08\x00\x01\x00\x03\x00" +\
                 "\x00\x00\x02\x00"
                 
class ScreenUpdateAck(CPCRequest): #ack we send when we get a screen update
    def __init__(self, device_number):
        super(ScreenUpdateAck, self).__init__(ACK_UPDATE, device_number)
        
#SIGNOFF_REQUEST_1 = "CPCR\x00\x01\x19\x00\x00\x00\x26\x00\x00\x00\x0d\x00\x00"+
#           "\x00\xFF\x01\x00\x00\x08\x00\x00\x00\x01\x00\xFF\x01\x01\x00\x00"+
#           "\x00\x01\x00\x00\x00"

class SignOffRequest1(Request4):
    pass
        
SIGNOFF_REQUEST_2 = "CPCR\x00\x01\x19\x00\x00\x00\x2b\x00\x00\x00\x12\x00\x00"+\
           "\x00\xFF\x01\x00\x00\x02\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00"+\
           "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05"
           
class SignOffRequest2(CPCRequest): #signoff our user name
    def __init__(self, device_number, username):
        super(SignOffRequest2, self).__init__(SIGNOFF_REQUEST_2, device_number)
        username = array.array('B', (username + '\x00' * 16)[:16])
        self.request[26:42] = username
        
class SignOffResponse(CPCResponse):
    pass
#
KEYS = {
    'f1' : 0x3B,
    'f2' : 0x3C,
    'f3' : 0x3D,
    'f4' : 0x3E,
    'f5' : 0x3F,
    'f6' : 0x40,
    'f7' : 0x41,
    'f8' : 0x42, #home
    'f9' : 0x43, #menu
    'f10': 0x44, #return
    'f11': 0x45,
    'enter' : 0x1C, #only key up
    '0'  : 0x0B, #confirm
    '1'  : 0x02,
    '2'  : 0x03, # key down only
    '3'  : 0x04,
    '4'  : 0x05,
    '5'  : 0x06,
    '6'  : 0x07,
    '7'  : 0x08,
    '8'  : 0x09,
    '9'  : 0x0A,
    ':'  : 0x27,
    '.'  : 0x34,
    'up' : 0x48,
    'down':0x50,
    'pgdn':0x51,
    'pgup':0x49,
    }
    
KEYDOWN =           "CPCR\x00\x01\x19\x00\x00\x00\x26\x00\x00\x00\x0d\x00\x00"+\
           "\x00\xFF\x01\x00\x00\x08\x00\x00\x00\x01\x00\x01\x01\x02\x00\x00"+\
           "\x00\x01\x00\xFF\x00"

class KeyDown(CPCRequest):
    def __init__(self, device_number, key):
        super(KeyDown, self).__init__(KEYDOWN, device_number)
        self.request[36] = KEYS[key]
        if key in ('pgdn', 'pgup', 'down', 'up'): 
            self.request[37] = 1

KEYUP =             "CPCR\x00\x01\x19\x00\x00\x00\x26\x00\x00\x00\x0d\x00\x00"+\
           "\x00\xFF\x01\x00\x00\x08\x00\x01\x00\x01\x00\x01\x01\x02\x00\x00"+\
           "\x00\x01\x00\xFF\xc0"
class KeyUp(CPCRequest):
    def __init__(self, device_number, key):
        super(KeyUp, self).__init__(KEYUP, device_number)
        self.request[36] = KEYS[key]

class KeyAck(CPCResponse):
    pass
# key ack
# 0000   43 50 43 52 00 01 19 00 00 00 59 00 00 00 40 00
# 0010   00 00 01 01 01 01 3c 00 00 08 00 01 00 02 00 00
# 0020   00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00
# 0030   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
# 0040   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
# 0050   00 00 00 00 00 00 00 00 00

#            
## Higher level objects

class ScreenDecoder(object):
    def __init__(self):
        self.texts = {} #key is XY, value is TextElement object
        self.template = None #templates control the decoding of the points on the screen
    def points(self): #return a dict keyed by point names with current values
        return {}
    def parse(self, pobj):
        if pobj.screen_cleared: #a clear screen command was detected
            self.texts = pobj.texts
        else:
            self.texts.update(pobj.texts)
    def find_name(self, str):
        answer = self.find_names(str)
        if answer:
            return answer[0]
        return None
    def find_names(self, str):
        texts = filter(lambda t: t.text == str, self.texts.values())
        return texts
    def find_y(self, y): #find other text elements at the same Y location
        answer = []
        for text in self.texts.values():
            if text.y == y:
               answer.append(text)
        return answer
    def find_x(self, x): #find other text elements at the same X location
        answer = []
        for text in self.texts.values():
            if text.x == x:
               answer.append(text)
        return answer
    def find_xy(self, xy):
        return self.find_x_y(xy[0], xy[1])
    def find_x_y(self, x, y):
        answer = []
        for text in self.texts.values():
            if text.x == x:
                if text.y == y:
                    answer.append(text)
        return answer
    def get_name(self, str): #can be simple name, comma seperated names and/or final index of points to the right of the name
        names = str.split(',') #two names seperated by a comma is used for tables
        column = 0
        if names[-1].isdigit():
            column = int(names.pop())
        text = None
        if len(names) > 1:
            texts = self.find_names(names[0]) #find the first name of the pair
            for t in texts: #now search for the second name
                texts2 = self.find_y(t.y) #find the texts on the same line as the first
                for t2 in texts2:
                    if t2.text == names[1]:
                        text = t2
                        break
                if text: break
        else:
            text = self.find_name(names[0])
        if text:
            texts = self.find_y(text.y)
            texts.sort() #in place
            #find first element to the right of the text
            for t in texts:
                if t.x > text.x:
                    if column < 1:
                        return t.text #value to the right of the name
                    column -= 1 #allow additional columns to the right of the text element to be used
        return None
    def as_html(self): #show decoded text items on a web page inside div tags
        return as_html.screen_to_html(self)
            
#3c 00 00 32 DeviceListResponse
#3c 00 00 01 LoginResponse
#3c 00 00 08 00 01 00 04 Response3
#3c 00 00 08 00 01 00 01 Response4
#3c 00 00 08 00 01 00 05 Response5
#08 00 00 05 01 00 01 01 04 Push new screen
#08 00 00 05 01 00 01 01 03 Push screen changes

def find_response_type(pkt): #figure out what type of response packet was received
    if pkt[22] == '\x3C': #response
        if pkt[25] == '\x32': return DeviceListResponse(pkt)
        if pkt[25] == '\x01': return LoginResponse(pkt)
        if pkt[25] == '\x08':
            if pkt[29] == '\x01': return Response4(pkt)
            if pkt[29] == '\x02': return KeyAck(pkt)
            if pkt[29] == '\x04': return Response3(pkt)
            if pkt[29] == '\x05': return Response5(pkt)
    if pkt[22] == '\x08':
        if pkt[30] == '\x04': return InitScreenCmd(pkt)
        if pkt[30] == '\x03': return ScreenUpdate(pkt)
    return None #flag that nothing matched
#'CPCR\x00\x01\x19\x00\x00\x00&\x00\x00\x00\r\x00\x00\x00\x01\x01\x01\x01\x08\x00\x01\x05\x01\x00\x01\x01\x01\x00\x00\x00\x01\x00\x00\x05'
 

"""
Copyright (C) 2003 2011 Cisco Systems

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
import array
import crc
import time

from mpx.lib.exceptions import *
from mpx import properties

CR = 0x0D

debug = 0 
def _crc(string):
    crc = 0
    for c in string:
        crc += ord(c)
    return crc % 256
#
#  SendFrame:  Prepares frames to be sent to TCS devices.
#
def send_frame(tx_pdu, unit_num, port, use_crc=1):
    if debug: print 'In frame.send_frame().'
    # clear out any left overs from a late response
    while len(port.drain()): 
        if debug: print 'Draining stale buffer'
        time.sleep(0.2)
    payload = ('%02X' % unit_num) + tx_pdu.tostring()
    #compute crc of payload
    if use_crc:
        crc = _crc(payload)
        buf = '>' + payload + ('%02X' % crc) + '\r'  #add checksum and CR
    else:
        buf = '>' + payload + '??\r' #no crc used
    if debug: print 'send_frame: '+ buf
    port.write(buf)
    if debug: print 'buffer written to port'
    #Read back the loopback frame in case of megatron.
    if properties.HARDWARE_CODENAME == 'Megatron':
        loopback = array.array('c')
        port.read(loopback,len(buf),.1)
        if debug : print 'loopback frame:' + loopback.tostring()
    return None

# Receive a frame of unknown length and check the CRC, framing, etc
# @return a string of the data portion of the response or exception

def receive_frame(port, length=None):
    if debug: print 'receive_frame'
    timeout = 0.5
    buffer = array.array('c')
    c = port.read_upto(buffer, [chr(CR)], timeout)
    if debug: print 'response is: ' + buffer.tostring()
    if buffer[0] == 'N':
        raise EInvalidCommand
    if buffer[0] != 'A':
        raise EInvalidCommand
    answer = buffer[1:-2].tostring() #return just the data portion
    #check the crc
    crc = _crc(answer)
    if crc != int(buffer[-2:].tostring(),16): #crc error
        if debug: print 'crc error ' + str(crc) + buffer[-2:].tostring()
        #raise EProtocol('crc error', str(crc) + ' not equal ' + buffer[-2:])

    return answer #return just the data portion

def receive_ack(port):
    if debug: print 'receive_frame'
    timeout = 0.5
    buffer = array.array('c')
    c = port.read_upto(buffer, [chr(CR)], timeout)
    if debug: print 'response is: ' + buffer.tostring()
    if buffer[0] == 'N':
        raise EInvalidCommand
    if buffer[0] != 'A':
        raise EInvalidCommand
    if len(buffer) == 1:
        return 1
    if debug:
        print 'ack expected and this was rcvd: ', buffer[1:].tostring()
    return 0
    
    

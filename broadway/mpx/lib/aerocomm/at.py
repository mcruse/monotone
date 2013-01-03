"""
Copyright (C) 2004 2006 2010 2011 Cisco Systems

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

##
# @todo Add code to turn on Relay that gates power to Aerocomm Server radio...
# Currently, this is done in the existing framework BEFORE exiting from the
# framework and running this script.

import struct
import select
from termios import *
import threading
import time
                                                                                
class at(threading.Thread):
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
                                                                                
    def __init__(self, port, speed):
        self.port = open(port, 'r+', 0)
        attr = tcgetattr(self.port.fileno())
        attr[0] = IGNPAR
        attr[1] = 0
        attr[2] = CS8 | CREAD | HUPCL | CLOCAL
        attr[3] = 0
        if self.speeds.has_key(speed):
            attr[4] = self.speeds[speed]
            attr[5] = self.speeds[speed]
        else:
            print 'Bad speed, using 9600'
            attr[4] = B9600
            attr[5] = B9600
                                                                                
        tcsetattr(self.port.fileno(), TCSANOW, attr)
        self.poll = select.poll()
        self.poll.register(self.port.fileno(), select.POLLIN)
        self.devices = []
                                                                                
    def send_command(self, command):
        print 'Sending: ',
        for b in command:
            print '%2.2x ' % ord(b),
        print
        self.port.write(command)

    def show_response(self):
        while 1:
            c = self.port.read(1)
            if c == '\r':
                print
                return
            print c,
                                                                                
    def init_radio(self):
        self.send_command('AT+++\r')
        self.show_response()
        self.send_command('ATW4A?\r')     # read current Serial Interface Mode
        self.show_response()
        self.send_command('ATW4A=03\r')   # set Serial Interface Mode to "API"
        self.show_response()
        self.send_command('ATW31?\r')     # read current Rx Mode
        self.show_response()
        self.send_command('ATW31=01\r')   # set Rx Mode to "Unicast/Broadcast"
        self.show_response()
        self.send_command('ATW33?\r')     # read current Server/Client Mode
        self.show_response()
        self.send_command('ATW33=01\r')   # set Server/Client Mode to "Server"
        self.show_response()
        self.send_command('ATZ\r')
        self.show_response()
        return

    
    

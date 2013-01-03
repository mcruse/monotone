"""
Copyright (C) 2001 2006 2010 2011 Cisco Systems

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

import termios, sys
from TERMIOS import *

if len(sys.argv) != 3:
    print "\nUsage: monitor.py /dev/ttyS<N> <speed>\n"
    sys.exit()

speed = {
    '0':B0,
    '50':B50,
    '75':B75,
    '110':B110,
    '134':B134,
    '150':B150,
    '200':B200,
    '300':B300,
    '600':B600,
    '1200':B1200,
    '1800':B1800,
    '2400':B2400,
    '4800':B4800,
    '9600':B9600,
    '19200':B19200,
    '38400':B38400,
    '57600':B57600,
    '115200':B115200,
    '230400':B230400,
    '460800':B460800
}

try:
    fd = open(sys.argv[1], "r+", 0)
except:
    print "\nCan't find " + sys.argv[1] + "\n"
    sys.exit()

if speed.has_key(sys.argv[2]) == 0:
    print "\nGnarly speed dude!\n"
    sys.exit()

old = termios.tcgetattr(fd.fileno())
new = termios.tcgetattr(fd.fileno())

iflags = IGNPAR
oflags = 0
cflags = CS8 | CREAD | HUPCL | CLOCAL
lflags = 0

new[0] = iflags
new[1] = oflags
new[2] = cflags
new[3] = lflags
new[4] = speed[sys.argv[2]]
new[5] = speed[sys.argv[2]]

try:
    termios.tcsetattr(fd.fileno(), TCSANOW, new)
    print "Monitoring...\n"
    while 1:
        print "%02.2x " % ord(fd.read(1)),
        sys.stdout.flush()
finally:
    termios.tcsetattr(fd.fileno(), TCSANOW, old)


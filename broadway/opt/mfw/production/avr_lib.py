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
from struct import *
from array import *
import select
import time

class avr:
    def __init__(self):
        self.avr = open("/dev/avr", "r+")
        self.avroob = open("/dev/avroob", "r")
        self.p = select.poll()
        self.p.register(self.avroob, select.POLLIN)

    def tohex(self, m):
        s = ''
        for i in m:
           s = s + '%2.2x' % ord(i)
        return s
        
    def version(self):
        m = pack("BBB", 0x17, 0x00, 0x00)
        self.avr.write(m)
        m = self.recv()
        return "%d.%d" % (ord(m[0]), ord(m[1]))

    def recv(self):
        m = self.avr.read(3)
        m = unpack("BBB", m)
        v = self.avr.read(m[2])
        return v

    def dallas_cmd(self, cmd, flags):
        m = pack("BBB", 0x15, flags, len(cmd)) + cmd
        self.avr.write(m)
        return self.recv()
        
    def set_relay(self, relay, value):
        m = pack("BBBBB", 0x10, 0x00, 0x02, relay, value)
        self.avr.write(m)
        v = self.recv()

    def get_relay(self, relay):
        m = pack("BBBB", 0x11, 0x00, 0x01, relay)
        self.avr.write(m)
        return self.recv()[0]

    def reset_counter(self, counter):
        m = pack("BBBB", 0x12, 0x00, 0x01, counter)
        self.avr.write(m)
        v = self.recv()

    def set_counter(self, counter, value):
        m = pack("BBBBI", 0x19, 0x00, 0x05, counter, value)
        self.avr.write(m)
        v = self.recv()

    def get_counter(self, counter):
        m = pack("BBBB", 0x13, 0x00, 0x01, counter)
        self.avr.write(m)
        return unpack("I", self.recv())[0]

    def get_digital(self, input):
        m = pack("BBBB", 0x14, 0x00, 0x01, input)
        self.avr.write(m)
        return self.recv()

    def dallas_readbits(self, bus, n):
        m = pack("BBB", 0x40, bus, n)
        return self.dallas_cmd(m, 0)

    def dallas_readbytes(self, bus, n):
        m = pack("BBB", 0x50, bus, n)
        return self.dallas_cmd(m, 0)

    def dallas_writebits(self, bus, n, bits):
        m = pack("BBB", 0x60, bus, n) + bits
        return self.dallas_cmd(m, 0)

    def dallas_writebytes(self, bus, n, bytes, flags):
        m = pack("BBB", 0x70, bus, n) + bytes
        return self.dallas_cmd(m, flags)

    def dallas_reset(self, bus):
        m = pack("BB", 0x10, bus)        
        return self.dallas_cmd(m, 0)[0]
        
    def dallas_skiprom(self, bus):
        m = pack("B", 0xcc)
        return self.dallas_writebytes(bus, 1, m, 0)[0]

    def dallas_readrom(self, bus):
        self.dallas_reset(bus)
        m = pack("B", 0x33)
        self.dallas_writebytes(bus, 1, m, 0)
        return self.dallas_readbytes(bus, 8)


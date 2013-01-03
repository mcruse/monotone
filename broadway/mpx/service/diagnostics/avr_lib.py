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
from struct import *
from array import *
import select
import time
from mpx import properties

from mpx.lib.node import as_node

_Avr = None

def get_avr():
    global _Avr
    if _Avr is None:
        if properties.HARDWARE_CODENAME == "Megatron":
            _Avr = Arm()
        else:
            _Avr = Avr()
    return _Avr
    
class Avr(object):
    def __init__(self):
        self.avr = as_node('/interfaces').coprocessor
        return
        
    def tohex(self, msg):
        s = ''
        for i in msg:
           s = s + '%2.2x' % ord(i)
        return s
        
    def version(self):
        msg = pack("BBB", 0x17, 0x00, 0x00)
        rsp = self.avr.invoke_message(msg)
        return "%d.%d" % (ord(rsp[0]), ord(rsp[1]))
        
    def dallas_cmd(self, cmd, flags):
        msg = pack("BBB", 0x15, flags, len(cmd)) + cmd
        return self.avr.invoke_message(msg)
        
    def set_relay(self, relay, value):
        msg = pack("BBBBB", 0x10, 0x00, 0x02, relay, value)
        return self.avr.invoke_message(msg)
        
    def get_relay(self, relay):
        msg = pack("BBBB", 0x11, 0x00, 0x01, relay)
        return self.avr.invoke_message(msg)[0]
        
    def reset_counter(self, counter):
        msg = pack("BBBB", 0x12, 0x00, 0x01, counter)
        return self.avr.invoke_message(msg)
        
    def set_counter(self, counter, value):
        msg = pack("BBBBI", 0x19, 0x00, 0x05, counter, value)
        return self.avr.write(msg)

    def get_counter(self, counter):
        msg = pack("BBBB", 0x13, 0x00, 0x01, counter)
        rsp = self.avr.invoke_message(msg)
        return unpack("I", rsp)[0]
        
    def get_digital(self, input):
        msg = pack("BBBB", 0x14, 0x00, 0x01, input)
        return self.avr.invoke_message(msg)
        
    def dallas_readbits(self, bus, n):
        msg = pack("BBB", 0x40, bus, n)
        return self.dallas_cmd(msg, 0)
        
    def dallas_readbytes(self, bus, n):
        msg = pack("BBB", 0x50, bus, n)
        return self.dallas_cmd(msg, 0)
        
    def dallas_writebits(self, bus, n, bits):
        msg = pack("BBB", 0x60, bus, n) + bits
        return self.dallas_cmd(msg, 0)
        
    def dallas_writebytes(self, bus, n, bytes, flags):
        msg = pack("BBB", 0x70, bus, n) + bytes
        return self.dallas_cmd(msg, flags)
        
    def dallas_reset(self, bus):
        msg = pack("BB", 0x10, bus)        
        return self.dallas_cmd(msg, 0)[0]
        
    def dallas_skiprom(self, bus):
        msg = pack("B", 0xcc)
        return self.dallas_writebytes(bus, 1, msg, 0)[0]
        
    def dallas_readrom(self, bus):
        self.dallas_reset(bus)
        msg = pack("B", 0x33)
        self.dallas_writebytes(bus, 1, msg, 0)
        return self.dallas_readbytes(bus, 8)

    
class Arm(object):
    def __init__(self):
        self.arm = as_node('/interfaces').coprocessor
        return
        
    def tohex(self, msg):
        s = ''
        for i in msg:
           s = s + '%2.2x' % ord(i)
        return s
        
    def set_relay(self, relay, value):
        n = as_node('/interfaces/relay%d' % relay)
        n.set(value)
        return n

    def get_relay(self, relay):
        n = as_node('/interfaces/relay%d' % relay)
        return n.get()
        
    def reset_counter(self, counter):
        n = as_node('/interfaces/counter%d' % counter)
        n.set(0)
        return n
        
    def set_counter(self, counter, value):
        n = as_node('/interfaces/counter%d' % counter)
        n.set(value)
        return n

    def get_counter(self, counter):
        n = as_node('/interfaces/counter%d' % counter)
        return n.get()


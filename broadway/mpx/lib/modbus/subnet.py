"""
Copyright (C) 2004 2007 2011 Cisco Systems

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
import os
import select
import socket
import array

from mpx import properties
from mpx.lib import msglog
from mpx.lib.debug import dump
from mpx.lib.node import Node
from mpx.lib.threading import ImmortalThread
from mpx.lib.threading import Lock
from mpx.lib.modbus.base import crc

debug = 0

# >>> from mpx.ion.modbus.serial.subnet import VirtualSubNetThread
# >>> t = VirtualSubNetThread('/dev/xxx')
__test = """
#from mpx.ion.host.port import Port
#p = Port()
from mpx.lib.node import as_node
p = as_node("/interfaces/com1")
p.configure({'baud':9600})
p.start()
#p.configure({'parent':None, 'name':'com1', 'dev':'/dev/ttyS1','baud':9600})

from mpx.ion.modbus.serial.subnet import VirtualSubNet
v = VirtualSubNet()
v.configure({'parent':p, 'name':'vn'})
v.start()
"""

packet_type_vs_length = {1:8, 2:8, 3:8, 4:8, 5:8, 6:8,
                         15:-9, 16:-9}

#someday we may support these additional functions
#, 20:-5, 21:-5,
#  7:4, 8:8, 11:4, 12:4, 17:4,
#  22:10, 23:-13, 24:6}
# command packets 1 - 6 are 8 bytes
# 7, 11, 12, 17 are 4
# 15 and 16 are 9 + ord(buffer[6])
# 20 & 21 5 + ord(buffer[2])
# 23 13 + ord(buffer[10])


class VirtualSubNetThread(ImmortalThread):
    def __init__(self, owner):
        self._buffer = None
        self.owner = owner  #owner is the slave ion
        self._port = owner.parent  #slave ion is child of com port
        ImmortalThread.__init__(self, name="%s(%r)" % (self.__class__,
                                                       self._port.dev))
        # Determine if we are attached to an RS485 port on a Megatron
        # If so then we need to handle reception of our transmitted data
        self.megatron = properties.HARDWARE_CODENAME == 'Megatron' 
        self.megatron_485 = self.megatron and (self.owner.parent.name in ('com3', 'com4', 'com5', 'com6'))
        print 'Modbus Slave device thread started in',
        if self.megatron_485:
            print 'RS485 echo mode'
        else:
            print 'RS485 no-echo mode'

        return

    def _setup_wakeup(self):
        socket_name = os.path.join(properties.TEMP_DIR,
                                   self.__class__.__name__)
        listen_skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        while 1:
            while os.path.exists(socket_name):
                socket_name += 'x'
            try:
                listen_skt.bind(socket_name)
                break
            except:
                raise
        try:
            listen_skt.listen(1) # only want one connection (ie to far_skt)
            self._wakeup = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._wakeup.connect(socket_name)
            self._wait, addr = listen_skt.accept()
            self._wait.setblocking(0)
            self._poll_list = select.poll()
            self._poll_map = {}
            wait_id = self._wait.fileno()
            self._poll_list.register(wait_id, select.POLLIN)
            self._poll_map[wait_id] = {
                select.POLLIN:self._wait_pollin,
                }
            port_id = self._port.file.fileno()
            self._poll_list.register(port_id, select.POLLIN)
            self._poll_map[port_id] = {
                select.POLLIN:self._port_pollin,
                }
        finally:
            os.remove(socket_name)
        return
    def _teardown_wakeup(self):
        self._wakeup.close()
        self._wait.close()
        return
    def _wait_pollin(self):
        self._wait.recv(1)
        return
    def _port_pollin(self):
        chars = self._port.drain()
        if self._buffer is None:
            self._buffer = array.array('c')
            self._packet_length = 4 #shortest legit packet
        self._buffer.extend(chars)
        if len(self._buffer) >= self._packet_length: #might be a good packet, otherwise wait for more
            packet_type = ord(self._buffer[1])
            if not packet_type_vs_length.has_key(packet_type): #don't crock this one
                self._buffer = None #reset the packet processing
                return
            packet_length = packet_type_vs_length[packet_type]
            if packet_length < 0: #must be variable length packet
                packet_length = abs(packet_length)
                if len(self._buffer) < packet_length: #not enough of the packet in yet
                    return #try again when more comes in
                packet_length = packet_length + ord(self._buffer[packet_length - 3]) #calc variable length packet size
            if len(self._buffer) >= packet_length: #enought to test the crc
                chars = self._buffer
                self._buffer = None #reset packet parsing regardless of what happens below
                bbuffer = array.array('B', chars[:packet_length].tostring())
                #is checksum good?        
                if crc(bbuffer) == 0: #things is gud
                    if debug:
                        print 'command'
                        dump(chars)
                    response = self.owner.command(chars)
                    if response is None: # message sent to a Modbus that does not exist
                        return
                    response.append_crc()
                    if debug:
                        print 'response:', response
                        dump(response.buffer) 
                    self._port.write(response.buffer)
                    # If this is a Megatron RS485 port then consume echoed transmit characters
                    # Wait for up to 2 seconds to see our echoed transmit data.
                    if self.megatron_485:
                        try:
                            self.port.read(array.array('c'), len(response.buffer), 2.0)
                        except:
                            msglog.exception()
                else:
                    if debug:
                        print 'crc failed - might be response'
        return
    def run(self):
        print "quoteth modbus subnet: I am (re)born!"
        try:
            self._port.open()
            self._setup_wakeup()
        except:
            msglog.exception()
            try: self._port.close()
            except: pass
            try: self._teardown_wakeup()
            except: pass
            self.should_die()
            raise
        try:
            while self.is_immortal():
                ready_list = self._poll_list.poll()
                for fid, bitmask in ready_list:
                    if bitmask & select.POLLIN:
                        self._poll_map[fid][select.POLLIN]()
                    if bitmask & select.POLLOUT:
                        self._poll_map[fid][select.POLLOUT]()
                    if bitmask & select.POLLERR:
                        self._poll_map[fid][select.POLLERR]()
        finally:
            try: self._port.close()
            except: pass
            try: self._teardown_wakeup()
            except: pass
            print "Ugh! I am dead!"
        return
    def stop(self):
        self.should_die()
        self._wakeup.send('b')
        # if self.id != currentThread().id wait X seconds for death?
        return

class VirtualSubNet:
    def __init__(self, owner):
        self._lock = Lock()
        self._thread = None
        self.owner = owner
        return
    def start(self):
        self._lock.acquire()
        try:
            if not self._thread:
                t = VirtualSubNetThread(self.owner)
                t.start()
                # Add interlock for successful start-up... (wait on Q for
                # 10 seconds).
                self._thread = t
        finally:
            self._lock.release()
        return
    def stop(self):
        self._lock.acquire()
        try:
            if self._thread:
                self._thread.stop()
                self._thread = None
        finally:
            self._lock.release()
        return


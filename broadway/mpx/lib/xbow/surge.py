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
""" surge reliable xbow wsn """
import struct, time, math, pkt_types, array
from mpx.lib import msglog, threading, thread, socket
from mpx.lib.msglog.types import ERR, WARN, DB
from mpx.lib.exceptions import EResourceError, ETimeout, EConnectionError, EAlreadyRunning
from crc import get_crc

def log(msg, log_type, debug_lvl):
    if debug_lvl:
        print msg
    msglog.log('mpx.xbow', log_type, msg)

class TcpLineHandler:
    def __init__(self, port, host, debug):
        self.port = port
        self.host = host
        self._s = None
        self.debug = debug
        
    def open_connection(self):
        try:
            self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, e:
            log('Error creating socket - stopping protocol', ERR, self.debug)
            raise EResourceError
        try:
            self._s.connect((self.host, self.port))
        except socket.gaierror, e:
            # host related error, ie. hostname not resolving.  possibly transient
            log('Error resolving host:%s' % self.host, WARN, self.debug)
            raise EConnectionError
        except socket.error, e:
            # connection error, possibly transient - error 106 ('Transport endpoint is already
            # connected) can be ignored.
            if e.args[0] != 106:
                log('Error connecting to gateway: %s' % self.host, WARN, self.debug)
                raise EConnectionError
        
    def close_connection(self):
        self._s.close()
        
    def connection_ok(self):
        if not self._s:
            return 0
        return self._s._connected
        
    def read(self, b, length):
        msg = ''
        while len(msg) < length:
            try:
                chunk = self._s.recv(length - len(msg))
            except socket.error, e:
                log('Error reading socket - reinitializing communication', WARN, self.debug)
                self.close_connection()
                raise EConnectionError
            if chunk == '':
                log('Broken connection - reinitializing communication', WARN, self.debug)
                self.close_connection()
                raise EConnectionError
            msg += chunk
        b.fromstring(msg)

class SerialLineHandler:
    def __init__(self, port, debug):
        self._conn_status = 0
        self.port = port
        self.debug = debug
        self.timeout = 300 
        
    def open_connection(self):
        if not self.port.is_open():
            self.port.open()
        self.port.drain()
        self._conn_status = 1
        
    def close_connection(self):
        self.port.close()
        self._conn_status = 0
        
    def connection_ok(self):
        return self._conn_status
        
    def read(self, b, length):
        try:
            self.port.read(b, length, self.timeout)
        except:
            if self.debug:
                msglog.exception()
            self.close_connection()
            raise EConnectionError
            
class XbowWsn:	
    def __init__(self, lh, cache):
        self.lh = lh
        self.cache = cache
        self._running = 0
        self.debug = lh.debug
        
    def is_running(self):
        return self._running
        
    def start(self):
        if not self._running:
            self._running = 1
            self._thread = threading.ImmortalThread(target=self._run, args=())
            self._thread.start()
            if self.debug: 
                print '**xbow** starting Immortal thread'
        else:
            raise EAlreadyRunning
            
    def stop(self):
        self.lh.close_connection()
        self._running = 0
        
    def _run(self):
        while self._running:
            # initialize the communications interface
            try:
                self.lh.open_connection()
            except EResourceError:
                self.stop()
                raise
            except EConnectionError:
                pass
            except:
                # unaccounted for exception - send it to the msglog
                msglog.exception()
            time.sleep(30)
            while self.lh.connection_ok():
                msg = None
                try:
                    msg = self._get_next_msg()
                except:
                    # connection will now be closed, re-init comm.
                    continue
                if msg:
                    tos_msg = pkt_types._TinyOS_Packet(msg)
                    # only add sensor data - we don't care about routing
                    # updates, etc..
                    if tos_msg.is_sensor_data():
                        self.cache.add_msg(tos_msg)
        else: 
            self._thread.should_die()
  	
    def _get_next_msg(self):
        msg = array.array('B')
        while 1: # keep trying until we get a good packet
            self.lh.read(msg, 1)
            if msg[0] != 0x7e: # looking for start token
                self._clear_buffer(msg)
                continue
            # It's unclear how much buffering xbow MIBs perform.  We could have a message 
            # that was in flight and thus this 0x7e was actually the tail, not the start byte.  
            # If so, get rid of it.
            self.lh.read(msg, 1)
            if msg[-1] == 0x7e:
                msg.pop()
                self.lh.read(msg, 1)
            while msg[-1] != 0x7e:
                self.lh.read(msg, 1)
            # check crc sans 0x7e's on start and finish
            if not self.check_crc(msg[1:-1]):
                if self.debug:
                    log('Bad crc', WARN, self.debug)
                self._clear_buffer(msg)
                continue
            return msg
            
    def _clear_buffer(self, b):
        while len(b):
            b.pop()
            
    def check_crc(self, msg):
        check = msg[-2]
        check += msg[-1] * 256
        crc = get_crc(msg[:-2])
        return crc == check
    
        

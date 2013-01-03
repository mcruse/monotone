"""
Copyright (C) 2002 2008 2009 2010 2011 Cisco Systems

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
# TODO:
# 2.  Add auto-detect.

from mpx.lib import threading
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.modbus.tcp_management import TcpClientConnection, MBAP
from mpx.lib.exceptions import *
from mpx.lib.modbus import base, command, exception, response
import copy
from mpx.lib.debug import _debug
from mpx.lib import msglog
from time import sleep

debug = 0

# LineHandler modules should supply the following functions:
buffer = base.buffer
crc = base.crc

class TcpIpClient(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self._lock = threading.RLock()
        self._port = None
        self.last_error = None
        self.retries = 3 #used by register_cache.RegisterCache._refresh
        self.report_timeouts = 1 #0 == try but give back last good val
        return
    def configure(self,config):
        self.timeout = 1.0
        CompositeNode.configure(self,config)
        set_attribute(self, 'ip', REQUIRED, config)
        set_attribute(self, 'port', 502, config, int)
        self.udp_port = int(self.port)
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'retries', 3, config, int)
        set_attribute(self, 'report_timeouts', 1, config, int)
        self.port = self #intercept any calls to the port
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'ip', config, str)
        config['port'] = str(self.udp_port)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'last_error', config, str)
        get_attribute(self, 'retries', config, str)
        get_attribute(self, 'report_timeouts', config, str)
        return config

    def buffer(self, initializer=None):
        return base.buffer(initializer)

    def crc(self, byte_array):
        return 0 #always answer that crc is good

    def read(self, header, n , timeout): #pretend to be a serial port but do nothing
        pass
    ##
    # Prevent other threads from reading or writing to the connection until
    # it's unlocked().
    #
    # Used to synchronize access to the connection.
    #
    def lock(self):
        self._lock.acquire()
        return
    ##
    # Release the inner most lock on the connection by the current thread.
    #
    # Used to synchronize access to the connection.
    #
    def unlock(self):
        self._lock.release()
        return

    def _command(self, cmd, ip=None):
        if debug: 
            print 'TcpIpClient command: ', cmd, self.ip
            print cmd.buffer
        if self.ip is None: raise EnvalidValue('Modbus IP: there must be an ip address')
        b = cmd.buffer.tostring()
        b = b[:-2] #trim off the crc
        t = cmd.timeout(self.timeout)
        port = None
        self._lock.acquire()
        try:
            try:
                if self._port is None:
                    if debug: print 'TcpIpClient open new tcp connection'
                    self._port = TcpClientConnection(self.ip, self.udp_port, .750) #.75 second connect timeout
                    if debug: print 'TcpIpClient port is: ', self._port
                    self._port.open_connection()
                    if debug: print 'TcpIpClient connection has opened'
                mbapw = MBAP(len(b), cmd.slave_address, 0)
                if debug: print 'MBAP encoding is: ', mbapw, b
                self._port.write(mbapw.encoding + b)
                if debug: print 'TcpIpClient command sent, wait for response'
                header = buffer()
                #todo timeout faster than tcp/ip does
                mbapr = self._port.read_MBAP()
                if debug:
                    print 'TcpIpClient MBAP of response received'
                    print mbapr

                if mbapr is None:
                    raise EInvalidResponse('Modbus: no response to client command', mbapw)
                if mbapw.transaction_id != mbapr.transaction_id: raise EInvlaidValue("Modbus: transaction id mismatch", mbapr)
                if mbapr.length > 256: raise EInvalidValue('Modbus: length too long', mbapr.length)
                #if mbapw.unit_id != mbapr.unit_id: raise EInvalidValue('Modbus: unit id mismatch')

                header.fromstring(self._port.read(mbapr.length)) #get the whole thing at once
                if debug: print 'TcpIpClient complete response: ', header
                if header[1] & 0x80:
                    e = cmd.exception(exception.factory)(self, header)
                    raise e
                resp = cmd.response(response.factory)(self, header, t)
                return resp
                #when response calls crc, return 0 (happy code)
                #when response uses port calls, intercept them
                #an alternative would be to append the crc to the header...
            except Exception, e:
                if self._port:
                    try:
                        if debug:
                            print 'modbus tcp: close connection', self._port
                        self._port.close_connection()
                    except:
                        pass
                self._port = None
                raise e
        finally:
            self._lock.release()
        raise EUnreachableCode()

    def command(self, cmd, ip=None):
        e = None
        try:
            for i in range(3):
                try:
                    return self._command(cmd, ip)
                except Exception, e:
                    if debug:
                        print str(e)
                    sleep(1)
        finally:
            self.last_error = str(e)
        raise

#this takes the place of the line handler node for 485/232 device hanging off the bridge

class TcpBridge(CompositeNode):
    def configure(self, config):
        CompositeNode.configure(self, config) #skip our parents configure to delay building the register map
        set_attribute(self, 'address', REQUIRED, config, int)
        return
    def ip(self):
        return self.address

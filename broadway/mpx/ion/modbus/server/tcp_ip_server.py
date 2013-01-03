"""
Copyright (C) 2002 2004 2010 2011 Cisco Systems

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

from mpx.lib.threading import ImmortalThread
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.modbus.tcp_management import TcpClientConnection, TcpServerConnection, MBAP
from mpx.lib.exceptions import *
from mpx.lib.modbus import server
import mpx.lib.modbus.exception
import copy
from mpx.lib.debug import _debug
from mpx.lib.ifconfig import ip_address
from mpx.ion.host.eth.ip import IP

debug = 0


#this takes the place of the line handler node for 485/232 device hanging off the bridge
class TcpIpServer(CompositeNode):
    def __init__(self):
        self.server = None
        return
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'port', 502, config, int)
        set_attribute(self, 'debug', 0, config, int)
        self.udp_port = self.port
        self.port = self #intercept any calls to the port
        return

    def configuration(self):
        config = CompositeNode.configuration(self)
        config['port'] = str(self.udp_port)  #get_attribute(self, 'port', config, str)
        get_attribute(self, 'debug', config, str)
        return config
    def start(self):
        self.device_map = {}
        if self.debug: print 'Start modbus tcpip server node'
        if self.parent.__class__ == IP: #then must be an 'internet_protocol' node (1.3)
            self.ip = self.parent.address
        else: #must be directly under the eth# port (1.4)
            self.ip = ip_address(self.parent.name)
        self.server = TcpServerConnection(self.ip, self.udp_port, self)
        CompositeNode.start(self)
        if self.debug: print 'modbus tcpip server node started'

    def _find_device(self, address):
        if self.device_map.has_key(address):
            return self.device_map[address]
        try:
            for d in self.children_nodes():
                if d.address == address:
                    self.device_map[address] = d
                    return d
        except:
            pass
        return None
    def buffer(self, initializer=None):
        return base.buffer(initializer)

    def crc(self, byte_array):
        return 0 #always answer that crc is good

    def read(self, header, n , timeout): #pretend to be a serial port but do nothing
        pass
        
    def command(self, buffer):
        cmd = server.ServerCommand(decode=buffer)
        device = self._find_device(cmd.slave_address)
        if device:
            response = device.perform_command(cmd)
        else:
            if self.debug: print 'TcpIpServer, no device found'
            response = None
        return response




"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
from mpx.lib.modbus.subnet import VirtualSubNet
from mpx.lib.exceptions import *
from mpx.lib.modbus import server
import mpx.lib.modbus.exception
import copy
from mpx.lib.debug import _debug

debug = 0


#this is the line handler node for 485/232 devices
class Slaves(CompositeNode):
    def __init__(self):
        self.subnet = VirtualSubNet(self)
        return
    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'debug', debug, config, int)
#
#
        if debug: self.debug = debug
#
#
        self.port = self #intercept any calls to the port
        return

    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug', config, str)
        return config
    def start(self):
        self.device_map = {}
        if self.debug: print 'Start modbus serial slave node'
        CompositeNode.start(self)
        self.subnet.start()
        if self.debug: print 'modbus serial slave node started'
        return
    def stop(self):
        self.subnet.stop()
        CompositeNode.stop(self)
        return
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
        
    def command(self, buffer):  #called from tcp or serial threads
        cmd = server.ServerCommand(decode=buffer)
        device = self._find_device(cmd.slave_address)
        if device:
            if self.debug: print 'command received: ' + str(cmd)
            response = device.perform_command(cmd)
        else:
            if self.debug: print 'SerialServer, no device found'
            response = None
        return response




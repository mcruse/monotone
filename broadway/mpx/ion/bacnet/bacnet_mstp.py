"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx.lib.bacnet import network
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.ion.bacnet.network import _Network
from mpx.lib.bacnet.npdu import Addr
from mpx.lib.bacnet.network import _device_info, _DeviceInfo
import struct
import fcntl
import errno
import array
from termios import *

MSTP_IOCGADDRS = 0x54E00010 #@FIXME: Find graceful way to import this assignmt from iocs.h in mstp ldisc
MSTP_IOCTESTREQ = 0x54E10013 #@FIXME: Find graceful way to import this assignmt from iocs.h in mstp ldisc

class BacnetMstp(_Network):
	def configure(self, config):
		_Network.configure(self, config)
		set_attribute(self, 'addr', REQUIRED, config, int)
		
	def configuration(self):
		config = _Network.configuration(self)
		get_attribute(self, 'addr', config, int)
		return config
	
	def start(self):
		# Open COM port BEFORE calling to open BACnet interface, so that we can use the
		# Port.open() method, and pass in only the file descriptor to open_interface():
		self.parent.open(1) # specify that port should block to complete read/write ops (default is NON-blocking)
		
		self.interface = network.open_interface('MSTP', self.parent.name, \
														self.network, MACaddr=self.addr, \
														fd_mstp=self.parent.file.fileno())
		_Network.start(self)
	
	def stop(self):
		network.close_interface(self.interface)
		self.parent.close() # close actual COM port AFTER clean up by network object
		_Network.stop(self)
		
	# Rtns 'passive' if Mediator is just listening, 'active' if Mediator has joined
	# token passing:
	def get(self, skipCache=0):
		if self.parent.file is None:
			return 'stopped'
		status_str = 'passive'
		str_addrs = 8 * '\0'
		str_addrs = fcntl.ioctl(self.parent.file.fileno(), MSTP_IOCGADDRS, str_addrs)
		addrTS, addrNS = struct.unpack(2 * 'I', str_addrs)
		print 'TS = %u. NS = %u.' % (addrTS, addrNS)
		if addrTS != addrNS: # if our and next addrs differ, then we're passing token
			status_str = 'active'
		return status_str
	
	# do_test_req(): Called from interactive Python prompt, to initiate MSTP Test 
	# Request/Response sequence. From Python prompt:
	# from mpx.lib.node import as_node
	# f = as_node('/interfaces/com2/bacnet_mstp') (or whatever...)
	# f.do_test_req(<target_BACnet_device_instance_number_OR_negative_MAC_addr>):
	def do_test_req(self, instance = -16):
		mac_addr = -instance
		if (instance >= 0):
			info = _device_info(instance)
			if (info == None):
				return -1
			mac_addr = int(struct.unpack('B', info.mac_address.address[0])[0])

		s_addr_rslt = struct.pack('I', mac_addr)
		return fcntl.ioctl(self.parent.file.fileno(), MSTP_IOCTESTREQ, s_addr_rslt)

def factory():
	return BacnetMstp()



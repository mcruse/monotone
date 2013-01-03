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
"""Module InterfaceRouteNode.py: Class definitions for InterfaceRouteNode and
subclasses. As a child of a Port or Eth node, an instance of a subclass of 
InterfaceRouteNode locks some or all of that parent's resources for exclusive 
use by the Router Service. For Port parents, the port is completely owned by the 
Router Service, while for Eth parents, specific sockets are owned.
"""

import sys, socket, array, time, exceptions, string, os, select, termios, struct
from mpx import properties
from mpx.lib.debug import _debug
from mpx.lib.threading import ImmortalThread, Thread, Lock, EKillThread, Event, Condition, currentThread
from mpx.lib import msglog
from mpx.lib.exceptions import ENotOpen, EAlreadyOpen, EPermission, EInvalidValue
from mpx.lib.node import ConfigurableNode, CompositeNode

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

from mpx.ion.host.port import Port
from mpx.ion.host.eth import Eth

from mpx.ion.router.InterfaceWrap import InterfaceWrap, ComIfWrap, TcpIfWrap, RzvcIfWrap
from mpx.lib.router.PortMonThr import PortMonThr

debug_lvl = 2
	
class InterfaceRouteNode(ConfigurableNode):
	"""class InterfaceRouteNode: An instance of InterfaceRouteNode beneath a given Mediator 
	hardware interface in the nodetree allows the ConfigTool user to specify some params,
	and to lock the hardware interface associated with the parent node for exclusive use
	by the Router Service. Nodes of this class should not need to have children. RouterThreads
	maintain dicts of refs to InterfaceRouteNode objects, and allow those objects to handle
	interface events intercepted by RouterThreads.
	"""
	def __init__(self):
		self._file = None
		self._iw = None # placeholder for InterfaceWrap to be created later
		
	
	def configure(self, config):
		"""method configure(): Called by MFW."""
		self.debug_print('Starting configuration...', 0)
		
		ConfigurableNode.configure(self, config)

		self.debug_print('Configuration complete.', 0)
		
	
	def configuration(self):
		self.debug_print('Reading configuration...', 0)
		config = ConfigurableNode.configuration(self)
		return config
	
	
	def start(self):
		"""method start(): Called by MFW."""
		self.debug_print('Starting...', 0)
		ConfigurableNode.start(self)
		
	
	def stop(self):
		self.debug_print('Stopping...', 0)
		ConfigurableNode.stop(self)
		
		
	def get_wrapper(self):
		"""method get_wrapper(): Subclass overrides return InterfaceWrapper subclass 
		object refs, for use by RouterThread."""
		return None
	
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'InterfaceRouteNode: ' + msg
			print prn_msg


class ComIfRouteNode(InterfaceRouteNode):
	def __init__(self):
		InterfaceRouteNode.__init__(self)
		self._port = None
		
	
	def configure(self, config):
		"""method configure(): Called by MFW."""
		self.debug_print('Starting configuration...', 0)
		
		ConfigurableNode.configure(self, config) # includes addition of "parent" attr
		
		self._port = self.parent
		
		self.debug_print('Configuration complete.', 0)
		
	
	def configuration(self):
		self.debug_print('Reading configuration...', 0)
		config = ConfigurableNode.configuration(self)
		return config
	
	
	def start(self):
		"""method start(): Called by MFW."""
		self.debug_print('Starting...', 0)
		ConfigurableNode.start(self)
		
		try:
			self._port.open() # any raised exceptions are caught by caller; locks com port for our exclusive use
		except termios.error, details:
			self.debug_print('termios.error: %s.' % str(details))
			
		self._file = self._port.file # com_node.file is valid only after successful call to open()
		
		self.debug_print('%s file = %s.' % (self.name, str(self._file)), 1)
		
		
	def stop(self):
		self.debug_print('Stopping...', 0)
		ConfigurableNode.stop(self)
		
		self._file = None # file is about to be invalidated
		
		try:
			self._port.close() # any raised exceptions are caught by caller
		except termios.error, details:
			self.debug_print('termios.error: %s.' % str(details))
			
		
	def get_wrapper(self):
		"""method get_wrapper(): Create, and return a ref to, an instance of ComIfWrapper."""
		return ComIfWrap(self._port, self._file, self.name) # note: "name" attr not avail till after configure()
	
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'ComIfRouteNode: ' + msg
			print prn_msg
			

class TcpIfRouteNode(InterfaceRouteNode):
	def __init__(self):
		InterfaceRouteNode.__init__(self)
		self._port_num = None
		self._rd_buf_len = 0
		
	
	def configure(self, config):
		"""method configure(): Called by MFW."""
		self.debug_print('Starting configuration...', 0)
		
		ConfigurableNode.configure(self, config)
		
		port_num = 6005 # choose Netlink utility's default and a random, high num as our defaults...
		set_attribute(self, 'port_num', port_num, config, int)
		
		self.debug_print('Configuration complete.', 0)
		
	
	def configuration(self):
		self.debug_print('Reading configuration...', 0)
		config = ConfigurableNode.configuration(self)
		return config
	
	
	def start(self):
		"""method start(): Called by MFW."""
		self.debug_print('Starting...', 0)
		ConfigurableNode.start(self)
		
		# Open a TCP socket on given port_num, under this Eth interface object:
		self.debug_print('Attempting to open a listening skt.', 0)
		self._file = self._create_listen_skt()
		if not self._file:
			self.debug_print('Could not open listening socket for Eth object %s.' % interface, 0)
			raise ENotOpen
		
		self._type = 'listen'
		self._rd_buf_len = self._file.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
		self.debug_print('fd %d has read buf len = %d.' % (self._file.fileno(), self._rd_buf_len), 0)
		
	
	def stop(self):
		self.debug_print('Stopping...', 0)
		ConfigurableNode.stop(self)
		
		self._file.close()
		
		
	def get_wrapper(self):
		"""method get_wrapper(): Create, and return a ref to, an instance of TcpIfWrapper."""
		return TcpIfWrap(self._file, self.name, 'listen') # note: "name" attr not avail till after configure()
		
	def _create_listen_skt(self):
		"""method _create_listen_skt(): Create TCP (stream) socket object for this 
		thread to listen for remote client connectons."""
		
		# AF_INET attr allows skt access via an Ethernet adapter, and SOCK_STREAM 
		# specifies a reliable, connection-based (TCP) protocol:
		self.debug_print('Initializing listen_skt...', 0)
		listen_skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		linger = struct.pack("ii", 1, 0) # prevent skt from jabbering with empty pkts after closure
		listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
		self.debug_print('listen_skt = %s.' % str(listen_skt), 0)
		
		# Bind the listen_skt object to a port (by specifying the port
		# number found in this node's config). The empty string used to specify
		# the host address causes the Python wrapper to send INADDR_ANY to the
		# underlying bind() system call, thereby enabling listening on the given
		# port on ALL adapters (eg ethX and serial/PPP):
		skt_address = ('', int(self.port_num))
		listen_skt.bind(skt_address)
		self.debug_print('listen_skt is bound to address %s.' % str(skt_address), 0)
		
		# Set listen_skt to listen for connections from remote client skts. Allow
		# max of 3 queued connection requests (may change number for future uses):
		try:
			listen_skt.listen(3)
		except socket.error, details:
			self.debug_print('Call to socket.listen() failed: %s' % details, 0)
			return None
		except:
			self.debug_print('Unknown exception while calling socket.listen()...', 0)
		return listen_skt
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'TcpIfRouteNode: ' + msg
			print prn_msg


class RzvcIfRouteNode(InterfaceRouteNode):
	def __init__(self):
		InterfaceRouteNode.__init__(self)
		self._portmon_thr = None
	
	def configure(self, config):
		"""method configure(): Called by MFW."""
		self.debug_print('Starting configuration...', 0)
		
		ConfigurableNode.configure(self, config) # includes addition of "parent" attr
		
		self._port = self.parent
		try:
			self._port.open() # any raised exceptions are caught by caller; locks com port for our exclusive use
		except termios.error, details:
			print 'termios.error: %s.' % str(details)
			
		self._file = self._port.file # com_node.file is valid only after successful call to open()
		
		print '%s file = %s.' % (self.name, str(self._file))
		
		self.debug_print('Configuration complete.', 0)
	
	def configuration(self):
		self.debug_print('Reading configuration...', 0)
		config = ConfigurableNode.configuration(self)
		return config
	
	def start(self):
		"""method start(): Called by MFW."""
		self.debug_print('Starting...', 0)
		ConfigurableNode.start(self)
		
		# Start port monitor thread:
		self._portmon_thr = PortMonThr(self)
		self._portmon_thr.start()
		
	def stop(self):
		self.debug_print('Stopping...', 0)
		ConfigurableNode.stop(self)
		
		self._portmon_thr.go = 0
		
	def get_wrapper(self):
		"""method get_wrapper(): Create, and return a ref to, an instance of RzvcIfWrapper."""
		return RzvcIfWrap(self._port, self._file, self.name) # note: "name" attr not avail till after configure()
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = self.__class__.__name__ + ' ' + msg
			print prn_msg

			
if __name__ == '__main__':
	print 'InterfaceRouteNode.py: Starting Unit Test...'
	
	print 'InterfaceRouteNode.py: Unit Test completed.'
	pass

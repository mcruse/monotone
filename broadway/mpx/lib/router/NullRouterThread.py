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
"""Module pkt_drivers.py: Class definitions for RouterThread and InterfaceWrapper.
RouterThread performs actual I/O ops, includes a single wait point for all events
associated with all registered InterfaceWrappers. InterfaceWrapper wraps variables
and methods that allow higher-level I/O ops than are supported by low-level,
builtin drivers for serial and Ethernet ports.
"""

import sys, socket, array, time, exceptions, string, os, select
from mpx import properties
from mpx.lib.debug import _debug
from mpx.lib.threading import ImmortalThread, Thread, Lock, EKillThread, Event, Condition, currentThread
from mpx.lib import msglog
from mpx.lib.exceptions import ENotOpen, EAlreadyOpen, EPermission, EInvalidValue
from mpx.lib.node import ConfigurableNode, CompositeNode, as_internal_node

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

from mpx.ion.host.port import Port
from mpx.ion.host.eth import Eth

from mpx.ion.router.InterfaceRouteNode import InterfaceWrap, ComIfWrap, TcpIfWrap, InterfaceRouteNode, ComIfRouteNode, TcpIfRouteNode

debug_lvl = 1

def print_array_as_hex(array_in, line_len = 16):
	len_array = len(array_in)
	lines = len_array / line_len
	for line in range(lines):
		for byte in range(line_len):
			print '%x ' % array_in[byte],
		print
	for byte in range(len_array % line_len):
		print '%x ' % array_in[byte],
	print
		
	
class NullRouterThread(Thread):
	"""class RouterThread: Ties together arbitrary number of serial ports and sockets.
	Routes output from one port to one or more of the others, according
	to the attached Router object. Uses InterfaceWrap objects and objects of
	derived classes to format and process incoming bytes and other events.
	"""
	
	def __init__(self):
		"""method __init__(): Parameter 'ir_nodes' is a list (not dictionary) of one 
		or more valid InterfaceRouteNode subclass instance refs."""
		
		Thread.__init__(self)
		
		self._poll_obj = None
		
		self.go = 1
		
		self._com1 = as_internal_node('/interfaces/com1')
		self._com1.open()
		self._com1_file = self._com1.file
		self._com1_fd = self._com1_file.fileno()
		
		self._com2 = as_internal_node('/interfaces/com2')
		self._com2.open()
		self._com2_file = self._com2.file
		self._com2_fd = self._com2_file.fileno()
		
	def run(self):
		self.debug_print(' runs on %s.' % currentThread(), 0)
		
		# Create one-and-only poll object:
		self._poll_obj = select.poll()
		poll_obj = self._poll_obj
		
		# Register each port's fd to correlate with incoming bytes for poll() triggering:
		poll_obj.register(self._com1_file, select.POLLIN)
		poll_obj.register(self._com2_file, select.POLLIN)
		
		# Enter thread's main loop:
		self.go = 1 # set to '0' only by other threads that want to stop this thread
		while self.go:
			# Enter the one-and-only wait state used by this RouterThread:
			evt_pairs = poll_obj.poll()
			self.debug_print('Event pairs received = %s' % evt_pairs, 0)
			
			buffer = array.array('B')
			for evt_pair in evt_pairs:
				if evt_pair[0] == self._com1_fd:
					buffer.fromstring(self._com1_file.read())
					buffer.tofile(self._com2_file)
				else:
					buffer.fromstring(self._com2_file.read())
					buffer.tofile(self._com1_file)
	
		# Unregister all of the fd's in the local dict from the poll() machinery:
		poll_obj.register(self._com1_file)
		poll_obj.register(self._com2_file)

		self.debug_print('on %s is ending run()...' % currentThread(), 0)
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'RouterThread: ' + msg
			print prn_msg

if __name__ == '__main__':
	print 'RouterThread.py: Starting Unit Test...'
	
	print 'RouterThread.py: Unit Test completed.'
	pass

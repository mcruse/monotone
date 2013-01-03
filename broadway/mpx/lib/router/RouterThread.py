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
"""Module RouterThread.py: Class definitions for RouterThread and InterfaceWrapper.
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
from mpx.lib.node import ConfigurableNode, CompositeNode

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

from mpx.ion.host.port import Port
from mpx.ion.host.eth import Eth

from mpx.ion.router.InterfaceWrap import print_array_as_hex
from mpx.ion.router.InterfaceRouteNode import InterfaceRouteNode, ComIfRouteNode, TcpIfRouteNode

debug_lvl = 1
	
#@fixme: Router class is currently hardcoded for RZ byte routing. Need to create subclasses, OR need
# to allow mode selection by broadway.xml
class RzRouter:
	"""class RzRouter: Based on mode, uses one or more criteria (src, dest, type) to forward
	the contents of the buffer of a given IW to other IWs.
	"""
	
	def __init__(self):
		self._iws = {} # dict of lists of IWs, where each list is keyed by it's name/type (eg 'rzhost_master')
		self._route_tbl = {'rzhost_slave':'rzhost_master', 'rzhost_master':'rzhost_slave', 'rznet_peer':'mon_skt'}
		self._rzhost_slave = None
		self._rzhost_master = None
		self._rznet_peer = None
	
		_accum_buf = array.array('B')
				
	def add_interface_wrap(self, iw):
		if self._iws.has_key(iw.node_name):
			# Existing key should point to a list value, so append to the list:
			self._iws[iw.node_name].append(iw)
		else:
			self._iws[iw.node_name] = [iw]

	def rmv_interface_wrap(self, iw):
		result = 0
		if self._iws.has_key(iw.node_name):
			iws_list = self._iws[iw.node_name]
			for i in range(0, len(iws_list)):
				if iws_list[i] is iw:
					del iws_list[i] # must use index form, to force true ref deletion; else, ref sticks around...
					# If the list for the current node_name is now empty, delete the list from the dict:
					if len(self._iws[iw.node_name]) == 0:
						del self._iws[iw.node_name] # must use index form, to force true ref deletion; else, ref sticks around...
					result = 1
					break
			if result == 0:
				print 'rmv_iw(): Failed to find IW %s with fd %d in list for node_name key %s' % (iw, iw._file.fileno(), iw.node_name)
		else:
			print 'rmv_iw(): Failed to find list with node_name key %s for IW %s with fd %d' % (iw.node_name, iw, iw._file.fileno())
		return result

	def send(self, iw_src):
		iws_dest = []
		iw_dest_name = None
		if self._route_tbl.has_key(iw_src.node_name):
			iw_dest_name = self._route_tbl[iw_src.node_name]
			
		if self._iws.has_key(iw_dest_name):
			iws_dest = self._iws[iw_dest_name]
		
		return iws_dest
	
class RouterThread(Thread):
	"""class RouterThread: Ties together arbitrary number of serial ports and sockets.
	Routes output from one port to one or more of the others, according
	to the attached Router object. Uses InterfaceWrap objects and objects of
	derived classes to format and process incoming bytes and other events.
	"""
	
	def __init__(self, ir_nodes):
		"""method __init__(): Parameter 'ir_nodes' is a list (not dictionary) of one 
		or more valid InterfaceRouteNode subclass instance refs."""
		
		Thread.__init__(self)
		
		self._poll_obj = None
		
		self.go = 1
		
		self._timeout_iw = None # ref to IW responsible for any timeout given to poll()
		self._timeout_param = None # ref to param provided by IW above, to be handed back to IW at timeout
				
		self._router = RzRouter()
		
		self._iws = {} # a dict of IWs
		
		# Walk the list of given ports, create an IW for each, and add the
		# new IW to the local dict, keyed by fd:
		for ir_node in ir_nodes:
			try:
				iw = ir_node.get_wrapper()
				self._iws[iw._file.fileno()] = iw
				if iw._type != 'listen':
					self._router.add_interface_wrap(iw)
			except:
				self.debug_print('Failed to create InterfaceWrap to wrap %s.' % str(ir_node.parent.name), 0)
				continue
		
		# Add a socket to send monitor output, (and eventually by which to receive cmds?):
		self._mon_skt = None # created in response to a query from a specific port_num (10001)
			
	def __del__(self):
		iw_fds_list = self._iws.keys()
		for iw_fd in iw_fds_list:
			try:
				del self._iws[iw_fd] # decr ref cnt, further undermining obj's tenuous hold on existence...
			except:
				pass
			
	# @param msg: String containing single '%d', to take fd of offending, and now doomed, IW file object
	def _erase(self, iw, msg = None):
		fd = iw._file.fileno()
		if msg: 
			msg = msg + ' Erasing InterfaceWrapper.'
			self.debug_print((msg % fd), 0)
		if fd >= 0:
			self._poll_obj.unregister(fd) # unreg for poll evts
			iw._file.close() # close IW file obj: iw._file.fileno() -> -1 from this pt on...
			del self._iws[fd] # rmv IW obj ref from local dict
		else:
			print 'Programming error: Attempted to erase IW %s with fd %d less than 0!' % (iw, fd)
		if not self._router.rmv_interface_wrap(iw):
			print 'Failed to remove IW %s from RzRouter!' % iw
		
	def run(self):
		self.debug_print(' runs on %s.' % currentThread(), 0)
		
		# Create one-and-only poll object:
		self._poll_obj = select.poll()
		poll_obj = self._poll_obj
		
		# Register each port's fd to correlate with incoming bytes for poll() triggering:
		iws_list = self._iws.values() # extract list of values from local IW dict
		for iw in iws_list:
			poll_obj.register(iw._file.fileno(), select.POLLIN)
		
		# Enter thread's main loop:
		total_bytes = 0
		avg_bytes_per_loop = 0
		loop_count = 0
		total_loop_time = 0
		avg_loop_time = 0
		macro_cnt = 2000
		self.go = 1 # set to '0' only by other threads that want to stop this thread
		start_time = time.clock()
		
		while self.go:
			loop_count = loop_count + 1
			if ((loop_count % macro_cnt) == 0):
				temp_time = time.clock()
				macro_loop_time = temp_time - start_time
				print 'macro_loop_time = ', macro_loop_time, 'temp_time = ', temp_time, 'start_time = ', start_time
				start_time = temp_time
				avg_loop_time = macro_loop_time / macro_cnt
				burden = avg_loop_time / avg_bytes_per_loop
				print 'avg_loop_time = ', avg_loop_time, 'avg_bytes_per_loop = ', avg_bytes_per_loop, 'burden per byte = ', burden
				
			#@fixme: Set timeouts:
			timeout_msec = -1
				
			# Enter the one-and-only wait state used by this RouterThread:
			self.debug_print('timeout_msec = %d' % timeout_msec, 0)
			evt_pairs = poll_obj.poll(timeout_msec)
			self.debug_print('Event pairs received = %s' % evt_pairs, 0)
			
			# If no event pairs are returned by poll(), then a timeout must have occurred:
			if len(evt_pairs) == 0:
				if not self._timeout_iw:
					self.debug_print('Programming Error. poll() timed out without any responsible InterfaceWrapper!', 0)
					raise EInvalidValue
				self.debug_print('Timeout detected for fd %d, %s.' % (self._timeout_iw._file.fileno(), self._timeout_iw), 1)
				result = self._timeout_iw.handle_timeout(self._timeout_param)
				if result == 'erase':
					self._erase(self._timeout_iw, 'Timeout caused scan of data_skt %d, and it looks dead.')
				self._timeout_iw = None
				self._timeout_param = None
			# Else, process event pairs:
			else:
				for evt_pair in evt_pairs:
					# Obtain the signaled IW from the local dict:
					try:
						iw_rd = self._iws[evt_pair[0]]
					except KeyError: # erasure ops below may have removed IW responsible for given evt_pair
						self.debug_print('Ignoring event pair for closed fd %d' % evt_pair[0], 0)
						continue
						
					# Submit the kernel event(s) to the generating IW for processing, 
					# and act on the result:
					result = iw_rd.process_kernel_evt(evt_pair[1])
					cmd = result[0]
					if not cmd:
						continue
					elif cmd == 'send':
						# Give iw_rd ref to Router, get back list of IWs to which to send 
						# reading IW's buffer:
						iws_dest = self._router.send(iw_rd)
						wr_buf = result[1]
						total_bytes = total_bytes + len(wr_buf)
						avg_bytes_per_loop = total_bytes / loop_count
						if len(iws_dest) == 0:
							continue
						for iw_dest in iws_dest:
							if iw_dest._file.fileno() < 0:
								print 'Program error: IW %s has fd %d! Already closed/deleted!' % (iw_dest, iw_dest._file.fileno())
								continue
							try:
								iw_dest.write(wr_buf)
								print 'Sent pkt to %d' % iw_dest._file.fileno()
							except: # destination IW may have been closed already...
								print 'Failed to write to fd %d: %s, %s' % (iw_dest._file.fileno(), sys.exc_type, sys.exc_value)
								#self._erase(iw_dest, 'Failed to write to fd %d.')
								continue
						# If debugging, send notification of xmitted bytes to console:
						self.debug_print('Xmitted byte array from fd %d:' % iw_rd._file.fileno(), 0)
						if debug_lvl > 1:
							print_array_as_hex(iw_rd._rd_buf)
						iw_rd._rd_buf = array.array('B') # clear the read buf of the current IW
					elif cmd == 'new_iw':
						# We have another data_skt to poll, so register it and add it into the local dict:
						new_iw = result[1]
						data_skt_fd = new_iw._file.fileno()
						self._iws[data_skt_fd] = new_iw
						self._router.add_interface_wrap(new_iw)
						poll_obj.register(data_skt_fd, select.POLLIN)
						self.debug_print('Input event on listen_skt %d => data_skt %d.' % (iw_rd._file.fileno(), data_skt_fd), 0)
						continue # connection established, but no data to process yet
					elif cmd == 'mon_iw':
						# We have a data_skt from which to echo incoming bytes/pkts:
						self._mon_skt = result[1]
						data_skt_fd = self._mon_skt._file.fileno()
						self._iws[data_skt_fd] = self._mon_skt
						self._router.add_interface_wrap(self._mon_skt)
						poll_obj.register(data_skt_fd, select.POLLIN) # no input expected from this mon_skt (yet), but be prepared...
						self.debug_print('Input event on listen_skt %d => mon_skt %d.' % (iw_rd._file.fileno(), data_skt_fd), 0)
						continue # connection established
					elif cmd == 'erase':
						# IW determined it was not worthy of existence, so squish it:
						self._erase(iw_rd, result[1])
						continue
					else:
						self.debug_print('Unknown result from InterfaceWrap.process_kernel_evt(): %s' % str(result), 0)
						raise EInvalidValue('Result from InterfaceWrap.process_kernel_evt()', str(result))
		
		# Unregister all of the fd's in the local dict from the poll() machinery:
		iw_fds_list = self._iws.keys()
		for iw_fd in iw_fds_list:
			poll_obj.unregister(iw_fd)

		self.debug_print('on %s is ending run()...' % currentThread(), 0)
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'RouterThread: ' + msg
			print prn_msg

if __name__ == '__main__':
	print 'RouterThread.py: Starting Unit Test...'

	a = array.array('B', [16, 24, 56, 255])
	print_array_as_hex(a, 16)
	
	print 'RouterThread.py: Unit Test completed.'
	pass

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
"""Module InterfaceWrap.py: Class definitions for InterfaceWrap and
subclasses. InterfaceWrap wraps variables and methods that allow higher-level
I/O ops than are supported by low-level, builtin drivers for serial and Ethernet ports.
"""

import sys, socket, array, time, exceptions, string, os, select, termios, math, struct
from mpx import properties
from mpx.lib.debug import _debug
from mpx.lib.threading import ImmortalThread, Thread, Lock, EKillThread, Event, Condition, currentThread
from mpx.lib import msglog
from mpx.lib.exceptions import ENotOpen, EAlreadyOpen, EPermission, EInvalidValue, ETimeout
from mpx.lib.node import ConfigurableNode, CompositeNode

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

from mpx.ion.host.port import Port
from mpx.ion.host.eth import Eth


debug_lvl = 0

def long_to_bytes(long_in):
	"""long_to_bytes(): parses given long into a list of 4 bytes, LSB at index 0."""
	byte_list = []
	temp_num = long_in
	for i in range(4):
		byte_list.append(temp_num & 0xFF)
		temp_num = (temp_num >> 8)
	return byte_list

def bytes_to_long(bytes_in):
	"""long_to_bytes(): parses given long into a list of 4 bytes, LSB at index 0."""
	long_out = 0
	length = len(bytes_in)
	for i in range(length):
		long_out = long_out + (bytes_in[i] << (8 * i))
	return long_out

def print_array_as_hex(array_in, line_len = 14):
	len_array = len(array_in)
	lines = math.floor(len_array / line_len) # whole lines only
	offset = 0
	for line in range(lines):
		for byte in range(offset, offset + line_len):
			print '%02x' % array_in[byte],
		print
		offset = byte + 1
		
	# Deal with partial line at end:
	for byte in range(offset, offset + (len_array % line_len)):
		print '%02x' % array_in[byte],
	print

def checksum(byte_array, start_idx = 0, stop_idx = -1):
	assert start_idx >= 0, 'checksum(): Bad start index.'
	
	sum = 0
	if stop_idx < 0:
		stop_idx = len(byte_array)
	assert stop_idx > start_idx, 'checksum(): Start index exceeds or equals stop index.'
	
	for i in range(start_idx, stop_idx):
		sum = sum + byte_array[i]
	
	sum = (0x55 - sum) & 0xFF
	return sum

class InterfaceWrap:
	def __init__(self, node_name, init_msec = sys.maxint, byte_msec = sys.maxint, seq_msec = sys.maxint):
		# Timeout values, effectively set to "never":
		self._init_msec = init_msec
		self._byte_msec = byte_msec
		self._seq_msec = seq_msec
		
		self._endtime = None # keeps track of next timeout endtime
		self._endtime_to = None # indicates which of the three timeout types generated the endtime
		self._rd_buf = array.array('B')
		
		self._file = None # set by subclasses, depending upon parent node type, OR by 
		
		self._type = 'data'
		
		self.node_name = node_name
		
		# Counters (used for purposes specific to interface type):
		self._counter0 = 0
		
	def read(self):
		pass
	
	def write(self, wr_buf):
		pass
	
	def get_next_timeout(self):
		#@fixme: Code for real eval of next timeout, based upon type of IW operation desired (read/write, byte/seq, etc.)
		# and on current time, and saved endtimes, and on port activity (ie bytes recvd/sent, etc.)...
		return (min(self._init_msec, self._byte_msec, self._seq_msec), None) # tuple[1] will be a param for RT to hand back in case of timeout
	
	def handle_timeout(self, param):
		#@fixme: Use given param to determine how to handle the timeout
		if isinstance(self._interface, socket.SocketType):
			try:
				host_name, port_num = self._file.getpeername()
			except:
				return 'erase' # indicate that this IW should be erased
		return None
	
	def process_kernel_evt(self, evt):
		"""method process_kernel_evt(): Placeholder, overridden by subclasses to process 
		POLLIN, POLLOUT, and POLLERR kernel-level events from poll() method."""
		return None

	
class ComIfWrap(InterfaceWrap):
	def __init__(self, _port, _file, node_name, init_msec = sys.maxint, byte_msec = sys.maxint, seq_msec = sys.maxint):
		InterfaceWrap.__init__(self, node_name, init_msec, byte_msec, seq_msec)
		self._file = _file 
		self._port = _port
	
	def read(self):
		self._rd_buf.fromstring(self._file.read())
		
	def write(self, wr_buf):
		wr_buf.tofile(self._file)
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = self.__class__.__name__ + ' ' + msg
			print prn_msg
	
	def get_next_timeout(self):
		#@fixme: Code for real eval of next timeout, based upon type of IW operation desired (read/write, byte/seq, etc.)
		# and on current time, and saved endtimes, and on port activity (ie bytes recvd/sent, etc.)...
		return sys.maxint
		#return (min(self._init_msec, self._byte_msec, self._seq_msec), None) # tuple[1] will be a param for RT to hand back in case of timeout
	
	def handle_timeout(self, param):
		#@fixme: Use given param to determine how to handle the timeout
		return None
	
	# return value indicates action to RouterThread: continue with next loop, or send byte buf contents to Router (as pkt or bytes)
	#@fixme: disable the init timer, and kick the byte and/or seq timers back to start
	def process_kernel_evt(self, evt):
		result = (None, None)
		if evt == select.POLLIN:
			self.read()
			if len(self._rd_buf) >= 1:
				result = ('send', self._rd_buf)
		return result

	
class TcpIfWrap(InterfaceWrap):
	
	# If a TcpIfWrap recvs this many empty pkts in a row, close the attd socket,
	# and erase the TcpIfWrap object:
	max_empty_pkts = 3
	
	def __init__(self, _file, node_name, _type = 'data', init_msec = sys.maxint, byte_msec = sys.maxint, seq_msec = sys.maxint):
		InterfaceWrap.__init__(self, node_name, init_msec, byte_msec, seq_msec)
		
		self._rd_buf = array.array('B')
		
		self._file = _file 
		
		self._type = _type # 'data': data socket, 'listen': listen socket
		self._rd_buf_len = self._file.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
	
	def read(self):
		self._rd_buf.fromstring(self._file.recv(self._rd_buf_len))
		
	def write(self, wr_buf):
#		print 'Trying to write to TcpIfWrap fd %d...' % self._file.fileno()
#		try:
		self._file.sendall(wr_buf.tostring())
#		except:
#			'Exception encountered during write op.'
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = self.__class__.__name__ + ' ' + msg
			print prn_msg
	
	def get_next_timeout(self):
		#@fixme: Code for real eval of next timeout, based upon type of IW operation desired (read/write, byte/seq, etc.)
		# and on current time, and saved endtimes, and on port activity (ie bytes recvd/sent, etc.)...
		return sys.maxint
		#return (min(self._init_msec, self._byte_msec, self._seq_msec), None) # tuple[1] will be a param for RT to hand back in case of timeout
	
	def handle_timeout(self, param):
		#@fixme: Use given param to determine how to handle the timeout
		if isinstance(self._interface, socket.SocketType):
			try:
				host_name, port_num = self._file.getpeername()
			except:
				return 'erase' # indicate that this IW should be erased
		return None
	
	#@fixme: disable the init timer, and kick the byte and/or seq timers back to start
	def process_kernel_evt(self, evt):
		"""method process_kernel_evt(): Return pair indicates one of these commands to caller (RouterThread): 
		(None, None) => do nothing.
		('send', None) => send buf ref from this IW to Router. 
		('new_iw', IW object ref) => add new IW ref to list of polled IWs
		('erase', msg) => erase this IW, due EITHER to jabbering or closure at other end, and print rtnd msg
		"""
		result = (None, None)
		
		# Test remote data_skt (but NOT listen_skt) for closure. If remote socket is closed, then tell RouterThread
		# to close and erase this socket/wrapper as well:
		if self._type == 'data':
			try:
				host_name, port_num = self._file.getpeername()
			except: # remote socket is closed, so tell RouterThread to do this one too:
				msg = 'data-skt %d appears to be dead on the other end.'
				result = ('erase', msg)
				
		if not result[0]:
			if evt == select.POLLIN:
				if self._type == 'listen':
					addr = None
					try:
						data_skt, addr = self._file.accept()
					except socket.error, details: # in case remote client socket disappeared after calling connect()
						self.debug_print('listen_skt could not accept connection from remote client socket: %s.' % str(details), 0)
					else:
						data_skt.setblocking(0)
						data_skt.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
						linger = struct.pack("ii", 1, 0) # prevent skt from jabbering with empty pkts after closure
						data_skt.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
						if self.node_name == 'mon_skt':
							result = ('mon_iw', TcpIfWrap(data_skt, 'mon_skt'))
						else:
							result = ('new_iw', TcpIfWrap(data_skt, self.node_name))
				else:
					self.read()
					if len(self._rd_buf) < 1:
						# Incr jabber pkt counter:
						self._counter0 = self._counter0 + 1
						if self._counter0 >= TcpIfWrap.max_empty_pkts:
							msg = 'Recvd max allowed consecutive empty TCP pkts from fd %d.'
							result = ('erase', msg)
					else:
						self._counter0 = 0
						result = ('send', self._rd_buf)
		return result
	
LAN_EXTENDED = 0x40
	
class RzvcIfWrap(InterfaceWrap):
	"""class RzvcIfWrap: One or more instances of this class may exist on the Mediator, 
	created by RzvcRouteNodes under the /virtuals node in the node tree. Such instances
	act like RZ Virtual Controllers, with the following black-box features:
		1) Participate in RS485-based RZNet token passing, complete with Serial Number/Address.
		2) Monitor points on the RZNet.
		3) Publish monitored points to the Mediator Node Tree/Browser.
		4) Download an xpoints.net file from PhWin.
		5) Publish xpoints.net data to Mediator Node Tree.
		6) Act as Modem Server for rest of RZNet.
		7) Act as MultiNet gateway (using two serial ports in the RS485 mode).
		8) Communicate as an RZ Controller with other Mediators running RZVC nodes.
	"""
	_pkt_hdr_len = 14
	_pkt_type_idx = 10
	_pkt_data_idx = 11
	_pkt_dst_idx = 2
	_pkt_src_idx = 6
	_pkt_hdr_chksum_idx = 13
	
	def __init__(self, _port, _file, node_name, init_msec = sys.maxint, byte_msec = sys.maxint, seq_msec = sys.maxint):
		InterfaceWrap.__init__(self, node_name, init_msec, byte_msec, seq_msec)
		
		self._port = _port
		self._file = _file 
		self._rd_state = 0 # start the subclass reading state machine in the 1st state
		self._rd_buf_idx = 0 # keeps trask of current target byte in buffer
		self._pkt_ext_len = 0 # set to non-zero in transition from State 2 to State 3, if any for a given pkt
		self._total_pkt_len = 0 # sum of _pkt_hdr_len and _pkt_ext_len for any given pkt
		
		self._ser_num = 30000 # 0x7530: choose higher number than expected from regular Mozaic, RZ100, or Tessera; @fixme: what about multi-Mediator systems?
		# Prepare to send pkts by breaking _ser_num into component bytes:
		self._ser_num_bytes = long_to_bytes(self._ser_num)
		
		self._peers = {}
		self._prev_rzc = None # RZ controller from which we recv token
		self._next_rzc = None # RZ controller to which we pass token
		
		self._low_rzc = sys.maxint # listen for and store lowest dst/src address
		self._high_rzc = 0 # listen for and store highest dst/src address
		
		self._rcvd_pkts = []
	
	def read(self):
		buf = array.array('B', self._file.read())
		self._rd_buf.extend(buf)
		
	def write(self, wr_buf):
		wr_buf.tofile(self._file)
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = self.__class__.__name__ + ' ' + msg
			print prn_msg
	
	def get_next_timeout(self):
		#@fixme: Code for real eval of next timeout, based upon type of IW operation desired (read/write, byte/seq, etc.)
		# and on current time, and saved endtimes, and on port activity (ie bytes recvd/sent, etc.)...
		return sys.maxint
		#return (min(self._init_msec, self._byte_msec, self._seq_msec), None) # tuple[1] will be a param for RT to hand back in case of timeout
	
	def handle_timeout(self, param):
		#@fixme: Use given param to determine how to handle the timeout
		if isinstance(self._interface, socket.SocketType):
			try:
				host_name, port_num = self._file.getpeername()
			except:
				return 'erase' # indicate that this IW should be erased
		return None
	
	# return value indicates action to RouterThread: continue with next loop, or send byte buf contents to Router (as pkt or bytes)
	#@fixme: disable the init timer, and kick the byte and/or seq timers back to start
	def process_kernel_evt(self, evt):
		"""method process_kernel_evt(): Form incoming bytes into RZ pkts."""
		result = (None, None)
		if evt == select.POLLIN:
			self.read() # read all available bytes from serial port, and add to end of _rd_buf

			buf_len = len(self._rd_buf)
			if self._rd_state == 0: # searching _rd_buf for for SYNC byte, 0x00 response to LAN_HELLO, OR 0x0253 ACK (latter two must be expected)
				for i in range(buf_len):
					if self._rd_buf[i] == 0x16:
						self._rd_buf = self._rd_buf[i:]
						self._rd_state = 1
						buf_len = len(self._rd_buf)
						break
				if self._rd_state != 1: # failed to find even a single SYNC in given byte buffer, so stay at State 0
					print 'No SYNC found in recv buffer:'
					print_array_as_hex(self._rd_buf)
					self._rd_buf = array.array('B')
					return result

			if self._rd_state == 1:
				if	buf_len >= 2: # looking for SOH byte after SYNC
					if self._rd_buf[1] == 0x01:
						self._rd_state = 2
					else:
#						self._rd_buf = array.array('B') # comment out:let State 0 code scan bytes for new SYNC
						self._rd_state = 0
						return result
				else:
					return result
					
			if self._rd_state == 2:
				if	buf_len >= self._pkt_hdr_len: # waiting for remainder of hdr
					chksum_calc = checksum(self._rd_buf, 2, self._pkt_hdr_len - 2) # do not use SYNC/SOH or chksum itself in calc
					chksum_given = self._rd_buf[self._pkt_hdr_len - 1]
					if chksum_calc == chksum_given:
						# Get packet type and determine whether or not to expect an extension:
						ext = self._rd_buf[self._pkt_type_idx] & LAN_EXTENDED
						if ext:
							self._pkt_ext_len = ((self._rd_buf[self._pkt_data_idx] << 8) + self._rd_buf[self._pkt_data_idx + 1]) & 0xC000
							self._total_pkt_len = self._pkt_hdr_len + self._pkt_ext_len
							self._rd_state = 3
						else:
							# Finished receiving this header-only pkt recvd from the RS485 port, 
							# so process it:
							self._total_pkt_len = self._pkt_hdr_len
							pkt = self._rd_buf[:self._total_pkt_len]
							result = self.process_rd_pkt(pkt) # @fixme: Rtn value could have a pkt to pass to RouterThread to send on to other interface
							self._rd_buf = self._rd_buf[self._total_pkt_len:] # trim processed pkt bytes from start of _rd_buf
							self._total_pkt_len = 0
							self._rd_state = 0
							return result
					else: # checksum failed, so try to deal with possible causes gracefully
						#@fixme Scan contents of read buffer for more instances of SYNC/SOH
						# header which might be starts of true pkt headers.
						print 'Calc checksum %02x does not match pkt hdr checksum %02x:' % (chksum_calc, chksum_given)
						print_array_as_hex(self._rd_buf[:self._pkt_hdr_len])
						self._rd_buf = array.array('B')
						self._rd_state = 0
						return result
				else:
					return result
						
			if self._rd_state == 3: # waiting for extension
				if	buf_len >= self._total_pkt_len: # waiting for remainder of extension
					chksum_calc = checksum(self._rd_buf, self._pkt_hdr_len, self._total_pkt_len - 2)
					chksum_given = self._rd_buf[self._total_pkt_len - 1]
					if chksum_calc == chksum_given:
						# Finished receiving this header/ext pkt from the RS485 port, so process it:
						pkt = self._rd_buf[:self._total_pkt_len]
						result = self.process_rd_pkt(pkt) # @fixme: Rtn value could have a pkt to pass to RouterThread to send on to other interface
						self._rd_buf = self._rd_buf[self._total_pkt_len:] # trim processed pkt bytes from start of _rd_buf
					else: # checksum failed, so try to deal with possible causes gracefully
						#@fixme Scan contents of read buffer for more instances of SYNC/SOH
						# header which might be starts of true pkt headers.
						print 'Calc checksum %02x does not match pkt extension checksum %02x:' % (chksum_calc, chksum_given)
						print_array_as_hex(self._rd_buf[:self._total_pkt_len])
					self._rd_buf = self._rd_buf[self._total_pkt_len:] # don't delete any bytes from subsequent pkts
					self._rd_state = 0
					self._pkt_ext_len = 0
					self._total_pkt_len = 0
				return result
				
			else:
				raise EInvalidValue('RzvcIfWrap Substate', str(self._rd_state))
			
		return result
	
	def process_rd_pkt(self, pkt):
		#@fixme: Actually do RZVC logic, including writing bytes back out of RS485, updating node tree
		# values, etc. For now, just return the pktzd bytes for echo out of mon_skt.
		
		LAN_HELLO = 0x00
		LAN_TOKEN = 0x01
		
		pkt_type = pkt[self._pkt_type_idx]
		response_type = None
		pkt_src = bytes_to_long(pkt[self._pkt_src_idx : self._pkt_src_idx + 3])
		pkt_dst = bytes_to_long(pkt[self._pkt_dst_idx : self._pkt_dst_idx + 3])
		
		# Maintain low/high address monitors:
		if pkt_src < self._low_rzc: self._low_rzc = pkt_src
		if pkt_src > self._high_rzc: self._high_rzc = pkt_src
		
		# Process pkt according to type:
		if pkt_type == LAN_HELLO:
			print 'LAN_HELLO: src = 0x%08x, dst = 0x%08x' % (pkt_src, pkt_dst)
			if pkt_src >= pkt_dst:
				if	pkt_src <= self._ser_num or pkt_dst > self._ser_num: # indicates that last RZC is sending to first, closing the token ring
					response_type = 'null'
			else: # else previous RZC is sending to next
				if pkt_src <= self._ser_num and pkt_dst > self._ser_num:
					response_type = 'null'
		
			if response_type == 'null':
				# Break procedure, and send multiple 0x00 bytes out RS485 port as directly
				# (and therefore with as little overhead) as possible. (Only one byte should
				# be necessary, but Mediator may turn around from RS485 slave to master 
				# faster than Mozaic can do the opposite):
				self._file.write('\0')
				self._file.flush() # make sure bytes are away...
				print 'Ack LAN_HELLO.'
				
		elif pkt_type == LAN_TOKEN:
			if pkt_dst == self._ser_num:
				# Pass the token on to our next without doing anything (yet...):
				wr_buf = self.create_pkt(self._low_rzc, LAN_TOKEN) #@fixme Use NEXT addr, not LOWEST addr (currently, assume that we have highest addr...)
				self.write(wr_buf)
				print 'Passed LAN_TOKEN.'
			else: # record src and dst controllers in local dict:
				self.debug_print('LAN_TOKEN for 0x%08x' % pkt_dst, 1)
			
		else:
			print 'Packet type 0x%02x for 0x%08x' % (pkt_type, pkt_dst)
			
		return ('send', pkt)
	
	def create_pkt(self, dst, pkt_type, hdr_data = 0x0000, ext_data = None):
		#@fixme: Add processing for extended pkts.
		assert isinstance(dst, int), 'RzvcIfWrap.create_pkt(): Param "dst" not an integer!'
		dst_bytes = long_to_bytes(dst)
		pkt_buf = array.array('B', [0x16, 0x01, dst_bytes[0], dst_bytes[1], dst_bytes[2], dst_bytes[3], \
			self._ser_num_bytes[0], self._ser_num_bytes[1], self._ser_num_bytes[2], self._ser_num_bytes[3], \
			pkt_type, hdr_data, (hdr_data >> 8), 0x00])
		
		pkt_buf[self._pkt_hdr_chksum_idx] = checksum(pkt_buf, 0, self._pkt_hdr_chksum_idx - 1)
		
		return pkt_buf
			
if __name__ == '__main__':
	print 'InterfaceRouteNode.py: Starting Unit Test...'
	
	print 'InterfaceRouteNode.py: Unit Test completed.'
	pass

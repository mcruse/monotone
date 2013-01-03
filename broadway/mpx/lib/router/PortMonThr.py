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
"""Module PortMonThr.py: Test one thread per serial port.
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

from mpx.ion.router.InterfaceWrap import print_array_as_hex, long_to_bytes, bytes_to_long, checksum

debug_lvl = 1
	
	
LAN_EXTENDED = 0x40
	
class PortMonThr(Thread):
	"""class PortMonThr: Test one-thread-per-port performance on RS485 networks.
	"""
	_pkt_hdr_len = 14
	_pkt_type_idx = 10
	_pkt_data_idx = 11
	_pkt_dst_idx = 2
	_pkt_src_idx = 6
	_pkt_hdr_chksum_idx = 13
	
	def __init__(self, ir_node):
		"""method __init__(): Parameter 'ir_node' is a ref to an instance of an RzvcIfRouteNode."""
		
		Thread.__init__(self)
		
		self._ir_node = ir_node
		self._file = self._ir_node._file
		self._fd = self._ir_node._file.fileno()
		
		self._poll_obj = None
		
		self.go = 1
		
		self._rd_buf_len = 256
		self._rd_buf = array.array('B', '\0' * self._rd_buf_len)
		self._rd_buf_start_idx = 0 # holds index of first byte in (potential) pkt
		self._rd_buf_cur_idx = 0 # holds index of current byte in buffer (logically, if not physically, between start and end)
		self._rd_buf_end_idx = 0 # holds index of last byte read
		self._bytes_read = 0
		
		self._rd_state = 0 # start the subclass reading state machine in the 1st state
		self._pkt_ext_len = 0 # set to non-zero in transition from State 2 to State 3, if any for a given pkt
		self._total_pkt_len = 0 # sum of _pkt_hdr_len and _pkt_ext_len for any given pkt
		
		self._ser_num = 30000 # 0x7530: choose higher number than expected from regular Mozaic, RZ100, or Tessera; @fixme: what about multi-Mediator systems?
		# Prepare to send pkts by breaking _ser_num into component bytes:
		self._ser_num_bytes = long_to_bytes(self._ser_num)
		
		self._low_rzc = sys.maxint # listen for and store lowest dst/src address
		self._high_rzc = 0 # listen for and store highest dst/src address
		
	def run(self):
		self.debug_print(' runs on %s.' % currentThread(), 0)
		
		# Create one-and-only poll object:
		self._poll_obj = select.poll()
		
		# Register one-and-only fd for input events:
		self._fd = self._ir_node._file.fileno() # in case it changed without de/reconstruction of this thread obj
		self._poll_obj.register(self._fd, select.POLLIN)
		
		# Enter thread's main loop:
		total_bytes = 0
		avg_bytes_per_loop = 0
		loop_count = 0
		total_loop_time = 0
		avg_loop_time = 0
		macro_cnt = 500
		byte_threshold = 1000
		self.go = 1 # set to '0' only by other threads that want to stop this thread
		start_time = time.clock()
		
		while self.go:
			loop_count = loop_count + 1
			if (total_bytes > byte_threshold):
				temp_time = time.clock()
				macro_loop_time = temp_time - start_time
				#print 'macro_loop_time = ', macro_loop_time, 'temp_time = ', temp_time, 'start_time = ', start_time
				start_time = temp_time
				avg_loop_time = macro_loop_time / loop_count
				avg_bytes_per_loop = total_bytes / loop_count
				loop_count = 0 # reset
				total_bytes = 0 # reset
				burden = avg_loop_time / avg_bytes_per_loop
				#print 'avg_loop_time = ', avg_loop_time, 'avg_bytes_per_loop = ', avg_bytes_per_loop, 'burden per byte = ', burden
			
			# Enter the one-and-only wait state used by this RouterThread:
			evt_pairs = self._poll_obj.poll()
			self.debug_print('Event pairs received = %s' % evt_pairs, 1)
			
			# If no event pairs are returned by poll(), then an error must have occurred:
			if len(evt_pairs) == 0:
				self.debug_print('Timeout error detected for fd %d, %s.' % self._fd, 1)
			# Else, process event pairs:
			else:
				for evt_pair in evt_pairs:
					# Submit the kernel event(s) to the generating IW for processing, 
					# and act on the result:
					if evt_pair[1] == select.POLLIN:
						rd_str = self._file.read()
						total_bytes = total_bytes + len(rd_str)
						self._bytes_read = len(rd_str)
						for i in range(self._bytes_read):
							self._rd_buf[self._rd_buf_end_idx] = ord(rd_str[i])
							self._rd_buf_end_idx = (self._rd_buf_end_idx + 1) & 0xFF
						self.process_byte_rd()
					else:
						raise EInvalidValue('Event Type', evt_pair[1])

		self._poll_obj.unregister(self._fd)

		self.debug_print('on %s is ending run()...' % currentThread(), 0)
	
	def process_byte_rd(self):
		"""method process_kernel_evt(): Form incoming bytes into RZ pkts."""
		#buf_len = len(self._rd_buf)
		if self._rd_state == 0: # searching _rd_buf for for SYNC byte, 0x00 response to LAN_HELLO, OR 0x0253 ACK (latter two must be expected)
			
			for i in range(self._bytes_read):
				if self._rd_buf[self._rd_buf_start_idx] == 0x16:
					self._rd_state = 1
					break
				self._rd_buf_start_idx = (self._rd_buf_start_idx + 1) & 0xFF
					
			self._rd_buf_cur_idx = self._rd_buf_start_idx
			
			if self._rd_state != 1: # failed to find even a single SYNC in given byte buffer, so stay at State 0
				print 'No SYNC found in recv buffer:'
				recvd_bytes = array.array('B', '\0' * self._bytes_read)
				idx = self._rd_buf_start_idx - self._bytes_read
				for i in range(self._bytes_read):
					recvd_bytes[i] = self._rd_buf[idx]
					idx = (idx + 1) & 0xFF
					
				print_array_as_hex(recvd_bytes)
				del recvd_bytes
				return

		buf_len = (self._rd_buf_end_idx - self._rd_buf_start_idx) & 0xFF
		if self._rd_state == 1:
			if	buf_len >= 2: # looking for SOH byte after SYNC
				if self._rd_buf[(self._rd_buf_start_idx + 1) & 0xFF] == 0x01:
					self._rd_state = 2
				else:
					self._rd_state = 0
					return
			else:
				return
				
		if self._rd_state == 2:
			if	buf_len >= self._pkt_hdr_len: # waiting for remainder of hdr
				
				# Make a copy of the nominal pkt:
				pkt = array.array('B', '\0' * self._pkt_hdr_len)
				for i in range(self._pkt_hdr_len):
					idx = (self._rd_buf_start_idx + i) & 0xFF
					pkt[i] = self._rd_buf[idx]
				
				if pkt[self._pkt_type_idx] == 0x00: print 'H',
				else: print '.',
				sys.stdout.flush()
					
				#print_array_as_hex(pkt)
				
				chksum_calc = checksum(pkt, 2, self._pkt_hdr_len - 2) # do not use SYNC/SOH or chksum itself in calc
				chksum_given = pkt[self._pkt_hdr_len - 1]
				if chksum_calc == chksum_given:
					# Get packet type and determine whether or not to expect an extension:
					ext = pkt[self._pkt_type_idx] & LAN_EXTENDED
					if ext:
						#self._pkt_ext_len = ((self._rd_buf[self._pkt_data_idx] << 8) + self._rd_buf[self._pkt_data_idx + 1]) & 0xC000
						#self._total_pkt_len = self._pkt_hdr_len + self._pkt_ext_len
						#self._rd_state = 3
						print 'Extended pkts not supported yet!'
						self._rd_state = 0
						self._rd_buf_start_idx = (self._rd_buf_start_idx + self._pkt_hdr_len) & 0xFF
						return
					else:
						# Finished receiving this header-only pkt recvd from the RS485 port, 
						# so process it:
						self._total_pkt_len = self._pkt_hdr_len
						#pkt = self._rd_buf[:self._total_pkt_len]
						self.process_rd_pkt(pkt) # @fixme: Rtn value could have a pkt to pass to RouterThread to send on to other interface
						#self._rd_buf = self._rd_buf[self._total_pkt_len:] # trim processed pkt bytes from start of _rd_buf
						self._rd_state = 0
						self._rd_buf_start_idx = (self._rd_buf_start_idx + self._pkt_hdr_len) & 0xFF
						del pkt
						return
				else: # checksum failed, so try to deal with possible causes gracefully
					#@fixme Scan contents of read buffer for more instances of SYNC/SOH
					# header which might be starts of true pkt headers.
					print 'Calc checksum %02x does not match pkt hdr checksum %02x:' % (chksum_calc, chksum_given)
					print_array_as_hex(self._rd_buf[:self._pkt_hdr_len])
					self._rd_state = 0
					self._rd_buf_start_idx = (self._rd_buf_start_idx + self._pkt_hdr_len) & 0xFF
					return
			else:
				return
						
		if self._rd_state == 3: # waiting for extension
			if	buf_len >= self._total_pkt_len: # waiting for remainder of extension
				chksum_calc = checksum(self._rd_buf, self._pkt_hdr_len, self._total_pkt_len - 2)
				chksum_given = self._rd_buf[self._total_pkt_len - 1]
				if chksum_calc == chksum_given:
					# Finished receiving this header/ext pkt from the RS485 port, so process it:
					pkt = self._rd_buf[:self._total_pkt_len]
					self.process_rd_pkt(pkt) # @fixme: Rtn value could have a pkt to pass to RouterThread to send on to other interface
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
			return
			
		else:
			raise EInvalidValue('RzvcIfWrap Substate', str(self._rd_state))
			
		return
	
	def process_rd_pkt(self, pkt):
		#@fixme: Actually do RZVC logic, including writing bytes back out of RS485, updating node tree
		# values, etc. For now, just return the pktzd bytes for echo out of mon_skt.
		
		LAN_HELLO = 0x00
		LAN_TOKEN = 0x01
		
		pkt_type = pkt[self._pkt_type_idx]
		response_type = None
		pkt_src = bytes_to_long(pkt[self._pkt_src_idx : (self._pkt_src_idx + 3)])
		pkt_dst = bytes_to_long(pkt[self._pkt_dst_idx : (self._pkt_dst_idx + 3)])
		
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
				# Break procedure, and send 0x00 byte out RS485 port as directly
				# (and therefore with as little overhead) as possible. :
				self._file.write('\0\0\0')
				self._file.flush() # make sure bytes are away...
				print 'Ack LAN_HELLO.'
				
		elif pkt_type == LAN_TOKEN:
			if pkt_dst == self._ser_num:
				# Pass the token on to our next without doing anything (yet...):
				wr_buf = self.create_pkt(self._low_rzc, LAN_TOKEN) #@fixme Use NEXT addr, not LOWEST addr (currently, assume that we have highest addr...)
				#time.sleep(0.01)
				wr_buf.tofile(self._file)
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
		
		pkt_buf[self._pkt_hdr_chksum_idx] = checksum(pkt_buf, 2, self._pkt_hdr_chksum_idx - 1)
		
		return pkt_buf
			
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'PortMonThr: ' + msg
			print prn_msg

if __name__ == '__main__':
	print 'PortMonThr.py: Starting Unit Test...'
	
	print 'PortMonThr.py: Unit Test completed.'
	pass

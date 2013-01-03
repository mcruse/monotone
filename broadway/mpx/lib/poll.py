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
import select, os, socket
from mpx.lib import threading

class Poll:
	_tmp_dir = '/tmp'
	def __init__(self):
		self._lock = threading.Lock()
		self._lock.acquire()
		try:
			self._poll_obj = select.poll()
			self._far_cmd_skt = None
			self._near_cmd_skt = None
			self._create_cmd_skts(self._tmp_dir)
			self._poll_obj.register(self._near_cmd_skt.fileno(), select.POLLIN)
		finally:
			self._lock.release()
		return
	def register(self, fd, evt_bit_mask):
		result = None
		self._lock.acquire()
		try:
			result = self._poll_obj.register(fd, evt_bit_mask)
			self._far_cmd_skt.sendall('Hey!')
		finally:
			self._lock.release()
		return result
	def unregister(self, fd):
		result = None
		self._lock.acquire()
		try:
			result = self._poll_obj.unregister(fd)
			self._far_cmd_skt.sendall('Hey!')
		finally:
			self._lock.release()
		return result
	def poll(self, timeout):
		poll_result_list = []
		go = 1
		while go:
			poll_result_list = self._poll_obj.poll(timeout)
			if len(poll_result_list) > 0:
				for poll_result in poll_result_list:
					if poll_result[0] == self._near_cmd_skt.fileno():
						self._lock.acquire()
						try:
							self._near_cmd_skt.recv(1024)
						finally:
							self._lock.release()
						poll_result_list.remove(poll_result)
						if len(poll_result_list) != 0:
							go = 0 # more results means other files have input
						break
				else:
					go = 0
			else:
				break
		return poll_result_list
	def _create_cmd_skts(self, _tmp_dir):
		# Establish an internal connection anchored by a pair of stream sockets by which 
		# other threads may deliver cmds to this thread:
		socket_name = os.path.join(_tmp_dir, (self.__class__.__name__ + '.%d') % os.getpid())
		
		# Delete any existing file with the path & name of the socket to be created:
		while os.path.exists(socket_name):
			try:    os.remove(socket_name)
			except: socket_name += 'x'
			
		# Create UNIX listen_skt object:
		listen_skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		
		# Set this_socket to allow rebinding to different local connections while
		# a previous binding is "in the process" of disconnecting (can take up to
		# several minutes after binding is already disconnected...):
		listen_skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			
		# Assign the created socket name/address to the listen socket object:
		listen_skt.bind(socket_name)
		
		# Create the actual sockets for each end of the command connection,
		# and establish a connection between the 2 sockets:
		try:
			listen_skt.listen(1) # only want one connection (ie to far_skt)
			self._far_cmd_skt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self._far_cmd_skt.connect(socket_name)
			self._near_cmd_skt, addr = listen_skt.accept()
			self._near_cmd_skt.setblocking(0) # no blocking on cmd skt connection
		finally:
			# Once the connection is established, we can delete the file.
			# It will be removed from its directory, but continue to exist
			# until this process is no longer connected to it.
			os.remove(socket_name)
		return

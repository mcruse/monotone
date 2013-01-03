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
import sys, socket, array, time, exceptions, string, os, select, termios
from mpx import properties
from mpx.lib.debug import _debug
from mpx.lib import msglog
from mpx.lib.exceptions import ENotOpen, EAlreadyOpen, EPermission, EInvalidValue
from mpx.lib.node import ConfigurableNode, CompositeNode

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

from mpx.ion.host.port import Port
from mpx.ion.host.eth import Eth

debug_lvl = 1


class TestOpen(ConfigurableNode):
	def __init__(self):
		ConfigurableNode.__init__(self)
	
	def configure(self, config):
		"""method configure(): Called by MFW."""
		self.debug_print('Starting configuration...', 0)
		
		ConfigurableNode.configure(self, config) # includes addition of "parent" attr
		
		try:
			self.parent.open()
		except termios.error, details:
			print 'termios.error: %s.' % str(details)
		
		print 'COM1 file = %s.' % str(self.parent.file)
		
		self.debug_print('Configuration complete.', 0)
	
	def configuration(self):
		self.debug_print('Reading configuration...', 0)
		config = ConfigurableNode.configuration(self)
		return config
	
	def start(self):
		self.debug_print('Starting...', 0)
		ConfigurableNode.start(self)
		
		poll_obj = select.poll()
		poll_obj.register(self.parent.file.fileno(), select.POLLIN)
		
		count = 0
		while count < 10:
			evt_prs = poll_obj.poll()
			print 'Got event pair %s.' % evt_prs
			self.parent.file.read(1024)
			count = count + 1
			time.sleep(0.5)
		
	def stop(self):
		self.debug_print('Stopping...', 0)
		ConfigurableNode.stop(self)
		
	def debug_print(self, msg, msg_lvl):
		if msg_lvl < debug_lvl:
			prn_msg = 'test_open: ' + msg
			print prn_msg

def factory():
	return TestOpen()

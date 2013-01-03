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
"""__init__.py:
Package file for router service. Define class RouterNode. RouterNode creates 
and manages an arbitrary number of RouterThread instances. Each RouterThread 
instance has an attached Router instance created and provided by the one-and-only
RouterNode instance. A RouterThread instance provides the vehicle by which 
a given Router receives events and incoming bytes, and sends events and outgoing
bytes. Behavior (eg full bytewise pass-through vs. RZ Virtual Modem Server) is
implemented by instances of Router subclasses (eg PassThrough Router and RzRouter).
"""

import asyncore, sys, string, select

from mpx.lib import msglog, thread
from mpx.lib.msglog import types, log
from mpx.lib.exceptions import EAlreadyRunning, EMissingAttribute, ENoSuchName

from mpx.lib.node import ConfigurableNode, CompositeNode, as_internal_node

from mpx.service import ServiceNode

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

from mpx.ion.host.port import Port
from mpx.ion.host.eth import Eth
from mpx.lib.router.RouterThread import RouterThread

debug = 1

class RouterNode(ServiceNode):
	"""class RouterNode: Finds and connects ports together. Manages Router Service.
	"""
	
	# This architecture assumes that every RouterNode object is created and
	# initialized before any object is configured:
	def __init__(self):
		self.running = 0
		self._interfaces = [] # list of all interfaces owned by this RouterNode
		self._router_thread = None
	
	def configure(self, config):
		"""method configure(): Called by MFW."""
		if debug: print 'Starting Router Service Node configuration...'
		
		ServiceNode.configure(self, config)
		
		# Read in the URLs of the target interface objects from the given dict. Assume that each
		# URL is prefaced by "interfaces".
		if_paths = []
		
		set_attribute(self, 'interface_paths', if_paths, config, eval)
		
		# Go find the actual interface objects (Ports and Eths) whose paths we just read
		# in the "interfaces" subtree:
		for path in self.interface_paths:
			url = '/interfaces/' + path
			try:
				interface = as_internal_node(url)
				self._interfaces.append(interface)
			except ENoSuchName, segment:
				if debug: print 'RouterNode: Failed to find expected interface object at %s, at segment %s!' % (url, segment)
			else:
				if debug: print 'RouterNode: Found interface object at %s.' % url
		
		if debug: print 'Router Service Node configuration complete.'
	
	def configuration(self):
		if debug: print 'RouterNode: Reading Router Service Node configuration...'
		config = ServiceNode.configuration(self)
		get_attribute(self, 'interface_paths', config, str)
		return config
	
	def start(self):
		"""method start(): Called by MFW."""
		if debug: print 'Starting Router Service...'
		ServiceNode.start(self)        
		if not self.running:
			self.running = 1
			# Create and attach RouterThread object:
			if debug: print 'RouterNode: Creating, attaching, and starting RouterThread.'
			self._router_thread = RouterThread(self._interfaces)
			self._router_thread.start()
		else:
			print 'Cannot start Router Service: already running.'
	
	def stop(self):
		if debug: print 'Stopping Router Service...'
		ServiceNode.stop(self)        
		if self.running:
			self.running = 0
			# Dettach and destroy test_tunnel object:
			if debug: print 'Ordering RouterThread to exit.'
			self._router_thread.go = 0
		else:
			print 'Cannot stop Router Service: not running.'


def factory():
	return RouterNode()

if __name__ == '__main__':
	pass

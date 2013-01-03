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
subclasses. Act as only children to hold places and to pass Port parents on
to classes that actually do the work (such as RznetThread).
"""

import sys, socket, array, time, exceptions, string, os, select, termios, struct
from mpx import properties
from mpx.lib.debug import _debug
from mpx.lib.threading import ImmortalThread, Thread, Lock, EKillThread, Event, Condition, currentThread
from mpx.lib import msglog
from mpx.lib.exceptions import ENotOpen, EAlreadyOpen, EPermission, EInvalidValue
from mpx.lib.node import ConfigurableNode, CompositeNode

from mpx.lib.configure import set_attribute, get_attribute, as_boolean

debug_lvl = 2

class InterfaceRouteNode(ConfigurableNode):
    """class InterfaceRouteNode: An instance of InterfaceRouteNode beneath a
    given Mediator hardware interface in the nodetree allows the ConfigTool
    user to specify some params, and to lock the hardware interface associated
    with the parent node for exclusive use by the Router Service. Nodes of this
    class should not need to have children. RouterThreads maintain dicts of
    refs to InterfaceRouteNode objects, and allow those objects to handle
    interface events intercepted by RouterThreads.  """
    def __init__(self):
        self._file = None
        self._iw = None # placeholder for InterfaceWrap to be created later
        return

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


    def stop(self):
        self.debug_print('Stopping...', 0)
        ConfigurableNode.stop(self)


    def debug_print(self, msg, msg_lvl):
        if msg_lvl < debug_lvl:
            prn_msg = 'ComIfRouteNode: ' + msg
            print prn_msg


if __name__ == '__main__':
    print 'InterfaceRouteNode.py: Starting Unit Test...'

    print 'InterfaceRouteNode.py: Unit Test completed.'
    pass

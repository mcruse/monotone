"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
##
# Test cases to exercise the bvlc class.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib.exceptions import EOverflow
from mpx.lib.bacnet.npdu import Addr
from mpx.lib.exceptions import EInvalidValue

import struct

from mpx.lib import pause, msglog
from mpx.lib.bacnet import npdu, network, tag, data, TEST, _bacnet
from mpx.lib.bacnet.npdu import NPDU, Addr

from mpx.lib.bacnet import server

class FakeNode:
    def __init__(self):
        self.instance = None

class TestCase(DefaultTestFixture):
            
    def test_server(self):
        msg = TEST.example_confirmed_request_npdu()
        #print msg
        source = Addr()
        _network = 1111
        node = FakeNode()
        node.instance = 1

        the_device = server._DeviceInfo()
        the_device.instance_number = node.instance
        the_device.node = node
        the_device.network = _network
        the_device.mac_network = _network
        the_device.address = '127.0.0.1'
        the_device.mac_address = the_device.address

        the_device.find_bacnet_object = find_bacnet_object
        server.the_device = the_device
        #tag.decode(msg.data)
        
        rsp = _bacnet.server_read_property(the_device, msg)
        if msg.sspec != rsp.dspec:
            raise 'the source spec and destination spec do not match'

def find_bacnet_object(obj_id):
    #print 'find_bacnet_object',obj_id
    return FakeObject()

class FakeObject:
    def find_property(self, prop_id):
        #print prop_id
        return FakeProperty()

class FakeProperty:
    def as_tags(self, index):
        return [tag.CharacterString(data.ANSI_String('This is a BACnet string!'))]
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

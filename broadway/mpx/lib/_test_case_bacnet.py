"""
Copyright (C) 2001 2002 2007 2010 2011 Cisco Systems

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
# Test cases to exercise the BACnet modules.
#
# @note The ethernet specific tests are only run if the process is the root
#       user.
# @fixme Report exceptions correctly from C.  (Raise MpxException objects).
# @fixme Phase out this test.  Replace it with APDU tests that include sending
#        and receiving a packet on "lo" and validataing they are the same.

import os
# import socket

from mpx_test import DefaultTestFixture

# from mpx.lib import pause
# from mpx.lib.bacnet import npdu
from mpx.lib.bacnet import network

# class PsuedoDevice:
#     original_broadcast_header = "\x81\x0b%c%c"
#     def __init__(self, device, port):
#         self.device = device
#         self.port = port
#         self.address = npdu.Addr('\x7f\x00\x00\x01%c%c' % \
#                                  (chr(port >> 8), chr(port & 0xff)))
#         self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.socket.bind(('127.0.0.1', port))
#         self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#     def __del__(self):
#         self.close()
#     def close(self):
#         if self.socket:
#             self.socket.close()
#             self.socket = None
#     def broadcast(self, string):
#         lo = (len(string) + 4) & 0x00ff
#         hi = ((len(string) + 4) >> 8) & 0x00ff
#         msg = self.original_broadcast_header % (hi,lo) + string
#         self.socket.sendto(msg, 0, ('127.255.255.255', 0xBAC0))
#     def who_is(self, device):
#         self.broadcast("\x01\x20\xFF\xFF\x00\xFF\x10\x08\x09%c\x19%c" % \
#                        (chr(device),chr(device)))
#     def i_am(self):
#         self.broadcast("\x01\x20\xff\xff\x00\xff\x10\x00\xc4\x02\x00\x00" + \
#                        ("%c\x22\x01\xe0\x91\x00\x21\x00" % chr(self.device)))

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        self.is_root = not os.getuid()
    def setUp(self):
        if self.is_root:
#             self.ethernet = network.open_interface('Ethernet', 'lo', 3)
            pass
        else:
            self.ethernet = None
        self.ip1 = network.open_interface('IP', 'lo', 1)
#         self.ip2 = network.open_interface('IP', 'lo', 2, port=0xbac1)
        DefaultTestFixture.setUp(self)
        return
    def tearDown(self):
        try:
#             if self.ethernet:
#                 network.close_interface(self.ethernet)
#                 pass
            network.close_interface(self.ip1)
#             network.close_interface(self.ip2)
        finally:
            DefaultTestFixture.tearDown(self)    
        return
#     def test_interfaces(self):
#         known_interfaces = ('IP', 'Ethernet')
#         i = network.interface_types()
#         for k in known_interfaces:
#             if k not in i:
#                 raise "Missing support for the '%s' interface." % k
    def test_open_all(self):
        pass
    ##
    # There was a bug in which every entry in the device_table referred to
    # the same address object (oops).
#     def test_reused_address(self):
#         devices = []
#         # Register a bunch of bogus devices via the BACnet network thread.
#         for i in range(100,110):
#             d = PsuedoDevice(i, 0xbac0+i)
#             d.i_am()
#             devices.append(d)
#             pause(0.01)
#         # Check that every entries address is correct.
#         for device in devices:
#             na = network.device_address(device.device)
#             if device.address.address !=  na.address:
#                 raise('Invalid reuse of an Addr() object detected.')
#         # clean up the bogus devices.
#         for d in devices:
#             del network._device_table[d.device]
#             d.close()

"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
# Test cases to exercise the port ion.
#
# @note Many of the tests are only run if the process is the root user.
#       because much of the configuration is logic is deferred until the
#       port is opened.

import os
import types

from mpx_test import DefaultTestFixture, main

from mpx.ion.host.port import factory
from mpx.lib.exceptions import EConfigurationIncomplete, EInvalidValue

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        self.is_root = not os.getuid()
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.port = factory()
        self.port.configure({'name':'port1', 'parent':None,
                             'dev':'/dev/ttyS0'})
        return
    def tearDown(self):
        try:
            if hasattr(self,'port'):
                if self.port.is_open():
                    self.port.close()
                del self.port
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_create(self):
        return
    def test_open(self):
        if not self.is_root:
            return
        self.port.open()
    def test_reconfigure_baud(self):
        if not self.is_root:
            return
        self.port.open()
        for baud in (0, 50, 75, 110, 134, 150, 200, 300, 600, 1200,
                     1800, 2400, 4800, 9600, 19200, 38400, 57600,
                     115200, 230400, 460800):
            self.port.configure({'baud':baud})
            self.port.configure({'baud':str(baud)})
            cd = self.port.configuration()
            if int(cd['baud']) != baud:
                raise 'Configured baud not reflected in the configuration'
    def test_reconfigure_baud_bad(self):
        if not self.is_root:
            return
        self.port.open()
        for baud in (-1, 1, 9601, 'BAUD'):
            try:
                self.port.configure({'baud':baud})
            except EInvalidValue:
                pass
            else:
                raise 'Configure baud did not detect a bad value of "%s".' % baud
    def test_reconfigure_stop_bits(self):
        if not self.is_root:
            return
        self.port.open()
        for stop_bits in (1,2):
            self.port.configure({'stop_bits':stop_bits})
            if type(stop_bits) == types.IntType:
                self.port.configure({'stop_bits':str(stop_bits)})
            cd = self.port.configuration()
            if int(cd['stop_bits']) != stop_bits:
                raise 'Configured stop_bits not reflected in the configuration'
    def test_reconfigure_stop_bits_bad(self):
        if not self.is_root:
            return
        self.port.open()
        for stop_bits in (-1,0,3):
            try:
                self.port.configure({'stop_bits':stop_bits})
            except EInvalidValue:
                pass
            else:
                raise 'Configure stop_bits did not detect a bad value of "%s".' \
                      % stop_bits
    def test_reconfigure_bits(self):
        if not self.is_root:
            return
        self.port.open()
        for bits in range(5,9):
            self.port.configure({'bits':bits})
            self.port.configure({'bits':str(bits)})
            cd = self.port.configuration()
            if int(cd['bits']) != bits:
                raise 'Configured bits not reflected in the configuration'
    def test_reconfigure_bits_bad(self):
        if not self.is_root:
            return
        self.port.open()
        for bits in (-1,0,4,9):
            try:
                self.port.configure({'bits':bits})
            except EInvalidValue:
                pass
            else:
                raise 'Configure bits did not detect a bad value of "%s".' % bits
    def test_reconfigure_flow_control(self):
        if not self.is_root:
            return
        self.port.open()
        for flow_control in (0, 1, 2, 3, 'none', 'rts/cts', 'xon/xoff', 'both'):
            msg = 'Configured flow_control not reflected in the configuration'
            self.port.configure({'flow_control':flow_control})
            if type(flow_control) == types.IntType:
                self.port.configure({'flow_control':str(flow_control)})
            cd = self.port.configuration()
            if type(flow_control) == types.StringType:
                if cd['flow_control'] != flow_control:
                    raise msg
            else:
                if ('none', 'rts/cts', 'xon/xoff', 'both')[flow_control] != \
                   cd['flow_control']:
                    raise msg
    def test_reconfigure_flow_control_bad(self):
        if not self.is_root:
            return
        self.port.open()
        for flow_control in (-1,4,'some',None):
            try:
                self.port.configure({'flow_control':flow_control})
            except EInvalidValue:
                pass
            else:
                raise 'Configure flow_control did not detect a bad value of "%s".'\
                      % flow_control
    def test_reconfigure_parity(self):
        if not self.is_root:
            return
        self.port.open()
        for parity in (0, 1, 2, 'none', 'odd', 'even'):
            msg = 'Configured parity not reflected in the configuration'
            self.port.configure({'parity':parity})
            if type(parity) == types.IntType:
                self.port.configure({'parity':str(parity)})
            cd = self.port.configuration()
            if type(parity) == types.StringType:
                if cd['parity'] != parity:
                    raise msg
            else:
                if ('none', 'odd', 'even')[parity] !=  cd['parity']:
                    raise msg
    def test_reconfigure_parity_bad(self):
        if not self.is_root:
            return
        self.port.open()
        for parity in (-1,3,'strange'):
            try:
                self.port.configure({'parity':parity})
            except EInvalidValue:
                pass
            else:
                raise 'Configure parity did not detect a bad value of "%s".'\
                      % parity

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

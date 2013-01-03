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
# Test cases to exercise the ethernet ion.

from mpx_test import DefaultTestFixture, main

import os

from mpx.ion.host.eth import factory
from mpx.lib.exceptions import EConfigurationIncomplete

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        self.is_root = not os.getuid()
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.eth0 = factory()
        self.eth0.configure({'name':'eth0', 'parent':None, 'dev':'eth0'})
        return
    def _tearDown(self):
        if hasattr(self,'eth0'):
            del self.eth0
        return
    def tearDown(self):
        try:
            self._tearDown()
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_create(self):
        return
    def test_bad_configure(self):
        self._tearDown()
        self.eth0 = factory()
        self.eth0.configure({'name':'eth0', 'parent':None})
        if not self.eth0._outstanding_attributes:
            raise 'Failed to detect missing dev.'
        return
    def test_open(self):
        if not self.is_root:
            return
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

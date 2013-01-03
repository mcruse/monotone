"""
Copyright (C) 2002 2003 2006 2010 2011 Cisco Systems

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
import os

from mpx_test import DefaultTestFixture, main

import rna
import exceptions

class TestCase(DefaultTestFixture):
    VERBOSE = 0
    next_file = -1
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        return
    def progress_message(self, fmt, *args):
        if self.VERBOSE:
            print fmt % args
    def filename(self):
        TestCase.next_file += 1
        return "/tmp/_test_case_rna.%s.%s" % (os.getpid(), TestCase.next_file)
    def named_socket_config(self):
        return {'filename':self.filename()}
    def service_tcp_config(self):
        return {'interface':'all', 'port':9999}
    def client_tcp_config(self):
        return {'interface':'all', 'port':9999}
    def test_SimpleTcpTransport(self):
        rna.SimpleTcpTransport(**self.service_tcp_config())
        return
    def test_SimpleTcpTransport_bind(self):
        s = rna.SimpleTcpTransport(**self.service_tcp_config())
        s.listen()
        return
    def test_SimpleTcpTransport_connect(self):
        config = self.service_tcp_config()
        s = rna.SimpleTcpTransport(**config)
        s.listen()
        c = rna.SimpleTcpTransport(**config)
        c.connect()
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    TestCase.VERBOSE = 1
    main()

"""
Copyright (C) 2005 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
#
# Test cases to exercise the Mehta Tech objects
#

# Note: These are performance test cases that are not designed to be run
#       nightly, but instead when comparing relative performance between
#       alternative versions of libraries & code which affects the
#       framework's XML-RPC performance

from mpx_test import DefaultTestFixture, main

import time, os, sys, base64, StringIO, binascii
import xmlrpclib
import moab.linux.lib.uptime as up

debug = 0


class TestCase(DefaultTestFixture):
    def setUp(self):
        global debug
        
        DefaultTestFixture.setUp(self)

        self.case = 100
        
        
        # Set up defaults
        self.port = 80
        self._username = 'mpxadmin'
        self._password = 'mpxadmin'
        self.hostname = 'bubba'
        
        self.nodeurl = '/interfaces/eth1/mehtatech_ied_protocol'

        # Override as needed
        #self.hostname = 'localhost'
        #self.port = 8080

        self.port = 443
        
        self.xmlrpcurl = 'https://%s:%s/xmlrpc' % (self.hostname, self.port)

        self.server = xmlrpclib.Server(self.xmlrpcurl, None, None, debug)
            
        # Authenticate with the server and get back a session ID
        self.session = self.server.rna_xmlrpc2.create_session(self._username,
                                                              self._password)
                
    def tearDown(self):
        DefaultTestFixture.tearDown(self)
        self.server = None
        self.session = None

    def _walk_tree(self, session, nodeurl):
        rsp = self.server.rna_xmlrpc2.invoke(session, nodeurl,
                                             'children_names')

        config = None
        try:
            config = self.server.rna_xmlrpc2.invoke(session, nodeurl,
                                                    'configuration')
        except:
            print 'Got problem calling configuration on %s.' % nodeurl
            raise
        #if config:
        #    print 'Configuration of %s: %s' % (nodeurl, str(config))

        for child in rsp:
            new_nodeurl = nodeurl+'/'+child
            self._walk_tree(session, new_nodeurl)
        
    def _test_cases(self):
        #
        if self.case == 100:
            nodeurl = '/services/time'
            num_iters = 200

            st = up.secs()

            for i in range(0, num_iters):
                rsp = self.server.rna_xmlrpc2.invoke(self.session,
                                                     nodeurl,'get',
                                                     )

            end = up.secs()

            print '%d gets took %f seconds.' % (num_iters,end-st)
           
##
# Support a standalone excecution.
#
if __name__ == '__main__':
    a = TestCase('_test_cases')
    a.setUp()
    a._test_cases()


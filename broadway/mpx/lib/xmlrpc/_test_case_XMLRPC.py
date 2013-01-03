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
import array
import os
import time
import types

from mpx_test import DefaultTestFixture, main

import mpx.service.session
from mpx.lib import xmlrpclib

from mpx.service.network.http.xmlrpc_handler import XMLRPC_Handler
from mpx.lib.node import as_internal_node

class TestCase(DefaultTestFixture):
    def setUp(self):
        mpx.service.session.SessionManager.PASSWD_FILE = (
            os.path.join(os.path.dirname(__file__), 'passwd.test')
            )
        DefaultTestFixture.setUp(self)
        self.config = {}
        lo = []
        lr = {}
        lr['alias'] = 'default'
        lr['class'] = 'mpx.lib.xmlrpc.XMLRPC_DefaultObject'
        lr['lifetime'] = 'Request'
        lo.append(lr)
        lr = {}
        lr['alias'] = 'rna_xmlrpc'
        lr['class'] = 'mpx.lib.xmlrpc.rna_xmlrpc.RNA_XMLRPC_Handler'
        lr['lifetime'] = 'Runtime'
        lo.append(lr)
        config = {}
        config['name'] = 'XMLRPC_Handler'
        config['parent'] = None
        config['module'] = ''
        config['deployed_objects'] = lo
        self.handler = XMLRPC_Handler()
        self.handler.configure(config)
        root = as_internal_node('/')
        self.new_node_tree()
        as_internal_node('/').start()
        self._session = as_internal_node(
            '/services/session_manager'
            ).create('mpxadmin', 'mpxadmin')
        return
    def tearDown(self):
        as_internal_node('/services/session_manager').destroy(self._session)
        self.del_node_tree()
        DefaultTestFixture.tearDown(self)
        return
    ##
    # Try and create the default XMLRPC object.  Call it's
    # get_methods and make sure a list is returned.
    # This will verify the internal methods of XMLRCP Handler
    # 
    def test_case_XMLRPCDefaultObject(self):
        params = []
        list_methods = self.handler.call('default', 'get_methods', params)
        assert len(list_methods) > 0, 'Default object has not methods'

        # Try and create the default XMLRCP object.  Call it's
        #  get_methods and make sure a list is returned.
        #  This will verify the inter
        s = 'Test Argument'
        params.append(s)
        result = self.handler.call('default', 'test_one_param', params)
        assert result == s, 'Test method returned wrong parameters'
        return
    ##
    #
    def test_case_xmlrpc_invoke(self): # Esentially, RNA over XMLRPC
        params = (self._session,'/','configuration')
        result = self.handler.call('rna_xmlrpc', 'invoke', params)
        return
    ##
    #
    def test_case_xmlrpc_invoke_batch(self):
        params = (self._session,
                  '/services/time:get',
                  '/services/time/local:get')
        results = self.handler.call('rna_xmlrpc', 'invoke_batch', params)
        for result in results:
            if type(result) is not types.FloatType:
                raise "Expected a float, got a %s." % type(result)
        return
    ##
    #
    def test_case_xmlrpc_invoke_batch_async(self):
        params = (self._session,
                  '/services/time:get',
                  '/services/time/local:get')
        results = self.handler.call('rna_xmlrpc', 'invoke_batch_async', params)
        t1 = time.time()
        while 1:
            for result in results:
                if type(result) is not types.FloatType:
                    self.assert_(time.time() < t1 + 1.0,
                                 "Expected valid results long ago, got: %r"
                                 % results)
                    time.sleep(0.1)
                    results = self.handler.call('rna_xmlrpc',
                                                'invoke_batch_async', params)
                    break
            else:
                # For loop's else clause only executed if the loop DID NOT
                # break.
                return
        raise "Can't get to this statement..."
    ##
    #
    def test_case_xmlrpc_invoke_batch_async_invalid_method(self):
        params = (self._session,
                  '/services/time:get_out_of_dodge',
                  "/services/time")
        results = self.handler.call('rna_xmlrpc', 'invoke_batch_async', params)
        t1 = time.time()
        while (not results[0] or not results[1]
               or
               not results[0].startswith("error: 'get_out_of_dodge' method")
               or
               not results[1].startswith("error: '' method")):
            self.assert_(time.time() < t1 + 1.0,
                         "Expected valid results long ago, got: %r"
                         % results)
            time.sleep(0.1)
            results = self.handler.call('rna_xmlrpc',
                                        'invoke_batch_async', params)
        return
    ##
    #
    def test_case_xmlrpc_invoke_batch_async_error(self):
        params = (self._session,
                  '/:get',
                  "/i/don't/exist:get")
        results = self.handler.call('rna_xmlrpc', 'invoke_batch_async', params)
        t1 = time.time()
        while (not results[0] or not results[1]
               or
               not results[0].startswith('error: exceptions.AttributeError(')
               or
               not results[1].startswith('error: '
                                         'mpx.lib.exceptions.ENoSuchName')):
            self.assert_(time.time() < t1 + 1.0,
                         "Expected valid results long ago, got: %r"
                         % results)
            time.sleep(0.1)
            results = self.handler.call('rna_xmlrpc',
                                        'invoke_batch_async', params)
        return
    ##
    #
    def test_case_xmlrpc_invoke_batch_async_destroy_sessions(self):
        session_manager = as_internal_node('/services/session_manager')
        params = (self._session,
                  '/services/time:get',
                  '/services/time/local:get')
        results = self.handler.call('rna_xmlrpc', 'invoke_batch_async', params)
        t1 = time.time()
        while t1:
            for result in results:
                if type(result) is not types.FloatType:
                    self.assert_(time.time() < t1 + 1.0,
                                 "Expected valid results long ago, got: %r"
                                 % results)
                    time.sleep(0.1)
                    results = self.handler.call('rna_xmlrpc',
                                                'invoke_batch_async', params)
                    break
            else:
                # For loop's else clause only executed if the loop DID NOT
                # break.
                t1 = None
        # Now start using new sessions.
        old_sessions = []
        for i in range(10):
            old_sessions.append(self._session)
            self._session = session_manager.create('mpxadmin', 'mpxadmin')
            params = (self._session,
                      '/services/time:get',
                      '/services/time/local:get')
            results = self.handler.call('rna_xmlrpc', 'invoke_batch_async',
                                        params)
            for result in results:
                if type(result) is not types.FloatType:
                    raise "Expected immediate values, but I got %r." % results
                # Now start destroying sessions.  Destroy 1, then 2 more, then
                # 3 more and finally the last 4.
            for i in range(1,5):
                for n in range(i):
                    session = old_sessions.pop(0)
                    session_manager.destroy(session)
                    time.sleep(0.2)
                    # A fresh session is what causes invoke_batch_async to
                    # collect old sessions.
                    old_sessions.append(self._session)
                    self._session = session_manager.create('mpxadmin',
                                                           'mpxadmin')
                    params = (self._session,
                              '/services/time:get',
                              '/services/time/local:get')
                    results = self.handler.call('rna_xmlrpc',
                                                'invoke_batch_async',
                                                params)
                    for result in results:
                        if type(result) is not types.FloatType:
                            raise ("Expected immediate values, but I got %r." %
                                   results)
        # Wow, looks good, one last test.  Are values change?
        old_results = results
        t1 = time.time()
        while time.time() < t1 + 10.0:
            time.sleep(0.1)
            results = self.handler.call('rna_xmlrpc', 'invoke_batch_async',
                                        params)
            if results != old_results:
                return
        raise "Values stopped changing at %r, at %r." % (results, time.time())

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

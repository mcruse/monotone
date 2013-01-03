"""
Copyright (C) 2003 2006 2007 2010 2011 Cisco Systems

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
import time

from mpx_test import DefaultTestFixture

from mpx import properties
from mpx.lib.node import *
from mpx.service.network.rna import RNA_Tcp
from mpx.lib.exceptions import EAbstract
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ERNATimeout

import socket

class RNATargetNode(CompositeNode):
    def __init__(self):
        self.__get_count = 0
        self._abort = False
        return
    def get(self, skipCache=0):
        self.__get_count += 1
        return self.__get_count
    def raise_divide_by_zero(self):
        1/0
        return
    def sleep(self,seconds):
        while not self._abort and seconds > 0.0:
            time.sleep(0.1)
            seconds -= 0.1
        return
    def raise_eabstract(self):
        raise EAbstract("Test of handling an MpxException")

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        try:
            self.root = as_internal_node('/')
            self.services = CompositeNode()
            self.services.configure({'parent':self.root, 'name':'services'})
            self.rna_service = RNA_Tcp()
            # port = 0 indicates that the RNA Service should bind to any
            # available port.
            self.rna_service.configure({'parent':self.services, 'name':'rna',
                                        'port':0, 'enabled':1, 'debug':0})
            self.rna_target = RNATargetNode()
            self.rna_target.configure({'parent':self.services,
                                       'name':'RNA Target'})
            self.aliases = Aliases()
            self.aliases.configure({'parent':self.root, 'name':'aliases'})
            self.root.start()
            # Determine what port the running RNA Service bound to.
            port = self.rna_service.bound_port()
            port_wait_expire_at = time.time() + 1.0
            while not port:
                self.failIf(time.time() > port_wait_expire_at,
                            "Failed to establish test's RNA port.")
                time.sleep(0.1)
                port = self.rna_service.bound_port()
            # Construct the URL explicitly using the port the RNA Service
            # bound to.
            self.rna_target_url = (
                'mpx://localhost:%d/services/RNA%%20Target' % port
                )
            self.alias1 = Alias()
            self.alias1.configure(
                {'parent':self.aliases, 'name':'Remote Target',
                 'node_url':self.rna_target_url}
                )
        except:
            self.tearDown()
            raise
        return
    def tearDown(self):
        try:
            self.rna_target._abort = True
            self.root.prune()
            self.root = None
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_simple_get(self):
        as_node(self.rna_target_url).get()
        return
    def test_alias_as_node(self):
        as_node('/aliases/Remote Target').get()
        return
    def test_alias_node(self):
        self.alias1.get()
        return
    ##
    # This test is essentially of "simple" MpxExceptions that occur
    # inside of the target method.  "Simple" means that there is
    # no special argument handling by the exception.
    def test_mpx_exception(self):
        try:
            as_node(self.rna_target_url).raise_eabstract()
        except EAbstract, e:
            pass
        else:
            self.fail("Did not receive expected exception!")
        return
    ##
    # This test is essentially of built-in Python exceptions that occur
    # inside of the target method.
    def test_python_exception(self):
        try:
            as_node(self.rna_target_url).raise_divide_by_zero()
        except ZeroDivisionError, e:
            pass
        else:
            self.fail("Did not receive expected exception")
        return
    ##
    # This test is essentially of the exception logic for an exception
    # generated by the RNA Service, after a successful node look up.
    def test_no_such_method(self):
        try:
            as_node(self.rna_target_url).no_such_method()
        except AttributeError, e:
            pass
        else:
            self.fail("Invoked a non-existant method.  Freaky!")
        return
    ##
    # This test is essentially of the exception logic for an exception
    # generated by the RNA Service, before a successful node look up.
    def test_no_such_node(self):
        try:
            as_node(self.rna_target_url + '/no/such/child/node').get()
        except ENoSuchName, e:
            pass
        else:
            self.fail("Invoked a method on a non-existant node.  Freaky!")
        return
    def test_rna_timeout(self):
        self.rna_service.configure({'client_transaction_timeout':0.1})
        try:
            as_node('/aliases/Remote Target').sleep(60)
        except ERNATimeout:
            pass
        return

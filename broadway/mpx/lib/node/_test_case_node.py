"""
Copyright (C) 2001 2003 2004 2007 2010 2011 Cisco Systems

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

from mpx_test import DefaultTestFixture, main

from mpx import properties
from mpx.lib import thread
from mpx.lib import threading
from mpx.lib.node import *
from mpx.lib.exceptions import EAttributeError
from mpx.lib.exceptions import EImmutable
from mpx.lib.exceptions import EInternalError
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ENoSuchNode

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.root = as_internal_node('/')
        self.child1 = CompositeNode()
        self.child2 = CompositeNode()
        self.child1_1 = CompositeNode()
        self.child1.configure({'parent':self.root, 'name':'child1',
                               '__node_id__':'1234'})
        self.child2.configure({'parent':self.root, 'name':'child2'})
        self.child1_1.configure({'parent':self.child1, 'name':'child1_1',
                                 '__factory__':'Hand crafted in America'})
        self.aliases = Aliases()
        self.aliases.configure({'parent':self.root, 'name':'aliases'})
        self.alias1 = Alias()
        self.alias1.configure({'parent':self.aliases, 'name':'child1',
                               'node_url':'/child1'})
        self.plus1 = CompositeNode()
        self.plus1.configure({'parent':self.root,'name':'1+1'})
        self.space1 = CompositeNode()
        self.space1.configure({'parent':self.root,'name':'space between'})
        self.test_lock_owner = None
        self.test_lock_node = None
        return
    def tearDown(self):
        try:
            self.root.prune()
            self.root = None
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_as_node(self):
        child = as_node('/child1')
        self.failUnless(child.name == self.child1.name, 'Returned wrong node')
        child = as_node('/child2')
        self.failUnless(child.name == self.child2.name, 'Returned wrong node')
        child = as_node('/child1/child1_1')
        self.failUnless(child.name == self.child1_1.name,
                        'Returned wrong node')
        self.failUnless(as_node('/child1') == as_node('/aliases/child1'),
                        'Alias did not return the same node as the direct'
                        ' lookup: expected %r, got %r.' % (
            as_node('/child1'), as_node('/aliases/child1')
            ))
        return
    def test_relative_as_node(self):
        child = as_node('child1', '/')
        self.failUnless(child.name == self.child1.name, 'Returned wrong node')
        child = as_node('child2', '/')
        self.failUnless(child.name == self.child2.name, 'Returned wrong node')
        child = as_node('child1_1', '/child1')
        self.failUnless(child.name == self.child1_1.name,
                        'Returned wrong node')
        # Down one.
        node = self.child1.as_node('child1_1')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # Down one, terminal slash.
        node = self.child1.as_node('child1_1/')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # Down one, and hold.
        node = self.child1.as_node('child1_1/.')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # Down one, hold, and terminal slash.
        node = self.child1.as_node('child1_1/./')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # Hold and down one.
        node = self.child1.as_node('./child1_1')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # Hold, down one, and hold.
        node = self.child1.as_node('./child1_1/.')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # Hold, down one, hold, and terminal slash.
        node = self.child1.as_node('./child1_1/./')
        self.assert_(node == self.child1_1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1_1.as_node_url(), node.as_node_url()))
        # One up.
        node = self.child1_1.as_node('..')
        self.assert_(node == self.child1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1.as_node_url(), node.as_node_url()))
        # Two up.
        node = self.child1_1.as_node('../..')
        self.assert_(node == self.root,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.root.as_node_url(), node.as_node_url()))
        # Waaaaaaay up.
        node = self.child1_1.as_node('../../../../../../../../../..')
        self.assert_(node == self.root,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.root.as_node_url(), node.as_node_url()))
        # Two up, one down.
        node = self.child1_1.as_node('../../child2')
        self.assert_(node == self.child2,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child2.as_node_url(), node.as_node_url()))
        # One up and stay a while.
        node = self.child1_1.as_node('../././././././.')
        self.assert_(node == self.child1,
                     'Returned wrong node, expected %r, get %r.' %
                     (self.child1.as_node_url(), node.as_node_url()))
        return
    def test_as_internal_node(self):
        child = as_internal_node('/child1')
        self.failUnless(child.name == self.child1.name, 'Returned wrong node')
        child = as_internal_node('/child2')
        self.failUnless(child.name == self.child2.name, 'Returned wrong node')
        child = as_internal_node('/child1/child1_1')
        self.failUnless(child.name == self.child1_1.name,
                        'Returned wrong node')
        self.failUnless(
            as_node('/child1') != as_internal_node('/aliases/child1'),
            'Internal alias returned the same node as the direct lookup.'
            )
        return
    def test_relative_as_internal_node(self):
        child = as_internal_node('child1', '/')
        self.failUnless(child.name == self.child1.name, 'Returned wrong node')
        child = as_internal_node('child2', '/')
        self.failUnless(child.name == self.child2.name, 'Returned wrong node')
        child = as_internal_node('child1_1', '/child1')
        self.failUnless(child.name == self.child1_1.name,
                        'Returned wrong node')
        return
    def test_special_paths(self):
        # Leading '/' should override relative path.
        child = as_node('/child1', '/child2')
        self.failUnless(child.name == self.child1.name,
                        'Returned wrong node, expected %r, get %r.' %
                        (child.as_node_url(), self.child1.as_node_url()))
        return
    def testas_node_url(self):
        url = as_node_url(self.child1)
        self.failUnless(url == '/child1', 'Returned wrong url')
        url = as_node_url(self.child2)
        self.failUnless(url == '/child2', 'Returned wrong url')
        url = as_node_url(self.child1_1)
        self.failUnless(url == '/child1/child1_1', 'Returned wrong url')
        return    
    def test_children_names(self):
        p = as_node('/child1')
        n = p.children_names()
        self.child1_2 = CompositeNode()
        self.child1_2.configure({'parent':self.child1, 'name':'child1_2'})
        self.failUnless(n == ['child1_1'],
                        'Returned the wrong children names-1')
        n = p.children_names()
        if not ((n == ['child1_2', 'child1_1']) or (n == ['child1_1',
                                                          'child1_2'])):
            self.fail('Returned the wrong children names-2')
        p = as_node('/child2')
        n = p.children_names()
        self.failUnless(n == [], 'Returned the wrong children names-3')
    def test_has_child(self):
        p = as_node('/child1')
        self.failUnless(p.has_child('bleah') == 0, 'Has child failed-1')
        self.failUnless(p.has_child('child1_1') == 1, 'Has child failed-2')
        p = as_node('/')
        self.failUnless(p.has_child('child1') == 1, 'Has child failed-3')
        self.failUnless(p.has_child('foo') == 0, 'Has child failed-4')
    def test_children_nodes(self):
        p = as_node('/child1')
        n = p.children_nodes()
        self.failUnless(n[0] == self.child1_1,
                        'Returned the wrong children nodes-1')
        self.child1_2 = CompositeNode()
        self.child1_2.configure({'parent':self.child1, 'name':'child1_2'})
        n = p.children_nodes()
        if not ((n == [self.child1_1, self.child1_2]) or
                (n == [self.child1_2, self.child1_1])):
            self.fail('Returned the wrong children nodes-2')
    def test_case_get_child(self):
        p = as_node('/child1')
        n = p.get_child('child1_1')
        self.failUnless(n == self.child1_1,
                        'get_child returned the wrong child')
        try:
            n = p.get_child('foobar')
        except ENoSuchName:
            # Success!
            return
        self.fail('Did not catch an ENoSuchName '
                  'from get_child when we should have.')
        return
    def test_configuration(self):
        self.child1.configuration()
        self.child2.configuration()
        self.child1_1.configuration()
        return
    def test_space(self):
        self.assert_comparison(
            "as_node('/space between')", "==", "self.space1"
            )
        self.assert_comparison(
            "as_node('/space%20between')", "==", "self.space1"
            )
        self.assert_comparison(
            "as_node('/space+between')", "==", "self.space1"
            )
        return
    def test_plus(self):
        self.assert_comparison(
            "as_node('/1%2B1')", "==", "self.plus1"
            )
        try:
            as_node('/1+1')
        except ENoSuchName:
            pass
        else:
            self.fail('Found "/1+1", which should decode to "/1 1" which'
                      ' should not exist.')
        return
    def test_enosuch_exception(self):
        try:
            as_node('/1%2B1/no_such_node/stuff/after/missing/node')
        except ENoSuchName, e:
            self.assert_comparison(
                'e.args[0]', '==', '"/1%2B1/no_such_node"'
                )
        else:
            self.fail('Found "/1%2B1/no_such_node/stuff/after/missing/node",'
                      ' which should not exist.')
        return
    def test_deferred_node(self):
        n = as_deferred_node('/child1/child1_1/deferred_node')
        try:
            parent = n.parent
        except ENoSuchNode:
            pass
        else:
            self.fail(
                "/child1/child1_1/deferred_node should NOT exist, but does."
                )
        try:
            n.parent = None
        except EImmutable:
            pass
        else:
            self.fail("/child1/child1_1/deferred_node should be immutable.")
        CompositeNode().configure({'name':'deferred_node',
                                   'parent':'/child1/child1_1'})
        # Now the attributes should be readable.
        parent = n.parent
        # Verify we got back a sensible node.
        self.assert_(parent.as_node_url() == "/child1/child1_1")
        self.assert_(n.as_node_url() == "/child1/child1_1/deferred_node")
        return
    def test_has_method(self):
        self.assert_(self.child1.has_method('configure'),
                     "self.child1.has_method('configure') SHOULD be true.")
        self.assert_(not self.child1.has_method('parent'),
                     "self.child1.has_method('parent') SHOULD NOT be true.")
        self.assert_(not self.child1.has_method('xxx'),
                     "self.child1.has_method('xxx') SHOULD NOT be true.")
        return
    def test_get_method(self):
        self.child1.get_method('configure')
        try:
            self.child1.get_method('parent')
            self.fail(
                "self.child1.get_method('parent') SHOULD raise EAttributeError"
                )
        except EAttributeError:
            pass
        try:
            self.child1.get_method('xxx')
            self.fail(
                "self.child1.get_method('xxx') SHOULD raise EAttributeError"
                )
        except EAttributeError:
            pass
        self.child1.get_method('configuration')()
        return

if(__name__ == '__main__'):
    main()

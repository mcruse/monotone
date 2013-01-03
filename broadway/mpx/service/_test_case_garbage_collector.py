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
from mpx_test import DefaultTestFixture, main
from mpx.lib.node import CompositeNode, as_node, as_internal_node
from mpx import properties
import os

from mpx.service.garbage_collector import GC_ONDELETE
from mpx.service.garbage_collector import GC_NEVER
from mpx.service.garbage_collector import GC_ONFAILURE
from mpx.service.garbage_collector import GARBAGE_COLLECTOR

debug = 0

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        self.path = properties.PDO_DIRECTORY
    def _build_path(self, filename):
        return os.path.join(self.path, filename)
    def _create_file(self, filename):
        f = open(filename, 'w')
        f.close()
    def _check_for_non_existance(self, files):
        for f in files:
            fname = self._build_path(f)
            if os.path.exists(fname):
                os.system('ls -al %s' % self.path)
                raise "%s should NOT exist, but it does." % fname
    def _check_for_existance(self, files):
        for f in files:
            fname = self._build_path(f)
            if not os.path.exists(fname):
                os.system('ls -al %s' % self.path)
                raise "%s should still exist, but it doesn't." % fname
    def _local_setup(self):
        self.new_node_tree()
        self.root = as_internal_node('/')
        self._dm = GARBAGE_COLLECTOR
        self._dm.debug = debug
        self._dm.start()
        return
    def _local_teardown(self):
        from mpx.lib._singleton import _ReloadableSingleton
        self.del_node_tree()
        _ReloadableSingleton.singleton_unload_all()
        return
    def _local_restart(self):
        self._local_teardown()
        self._local_setup()
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self._local_setup()
        return
    def tearDown(self):
        self._local_teardown()
        DefaultTestFixture.tearDown(self)
        return

    ##
    # Test to make sure the data manager doesn't blow away persistent data for
    # nodes which didn't fail to start up.
    def test_a(self):
        files = ['file1_2', 'file1_3', 'file1_4']

        # Create bogus persistent files
        for f in files:
            self._create_file(os.path.join(self.path, f))
        
        self._dm.register('/test1/test2', self._build_path('file1_2'),
                          GC_ONDELETE)
        self._dm.register('/test1/test2', self._build_path('file1_3'),
                          GC_NEVER)
        self._dm.register('/test1/test2', self._build_path('file1_4'),
                          GC_ONFAILURE)
        
        self._dm.set_faillist([])

        # Now simulate a restart
        self._local_restart()

        self._dm.register('/test1/test2', self._build_path('file1_2'),
                          GC_ONDELETE)
        self._dm.register('/test1/test2', self._build_path('file1_3'),
                          GC_NEVER)
        self._dm.register('/test1/test2', self._build_path('file1_4'),
                          GC_ONFAILURE)
        
        self._dm.set_faillist([])
        
        # Because we had no failures, all of our persistent files should
        # still be around.
        self._check_for_existance(files)
       
    ##
    # Test to make sure that GC_ONFAILURE works with a node which is reported
    # to have failed when it's parent was trying to load and that the other
    # children node's persistent data does not go away.
    def test_b(self):
        files = ['file1_2', 'file1_3', 'file1_4']

        # Create bogus persistent files
        for f in files:
            self._create_file(self._build_path(f))
        
        self._dm.register('/test1/test2', self._build_path('file1_2'),
                          GC_ONDELETE)
        self._dm.register('/test1/test2', self._build_path('file1_3'),
                          GC_NEVER)
        self._dm.register('/test1/test2', self._build_path('file1_4'),
                          GC_ONFAILURE)
        
        self._dm.set_faillist([])

        # Now simulate a restart
        self._local_restart()

        self._dm.set_faillist([{'name':'test1', 'parent':'/', 'type':'load'}])
        
        # Because we had a failure, some of our persistent files should
        # have been cleaned-up and some should still be around.
        self._check_for_non_existance(['file1_4'])
        self._check_for_existance(['file1_2', 'file1_3'])

    ##
    # Test for correctness when a specific node fails (test3) and another node
    # does not appear to have failed, but isn't present (test1).
    def test_c(self):
        files = ['file1_2', 'file1_3', 'file1_4']

        # Create bogus persistent files
        for f in files:
            self._create_file(self._build_path(f))
        
        self._dm.register('/test1/test2/test1', self._build_path('file1_2'),
                          GC_ONDELETE)
        self._dm.register('/test1/test2/test2', self._build_path('file1_3'),
                          GC_NEVER)
        self._dm.register('/test1/test2/test3', self._build_path('file1_4'),
                          GC_ONFAILURE)
        
        self._dm.set_faillist([])

        # Now simulate a restart
        self._local_restart()
         
        self._dm.set_faillist([{'name':'test3',
                                'parent':'/test1/test2',
                                'type':'load'}])

        # Because we had a failure, some of our persistent files should
        # have been cleaned-up and some should still be around.
        self._check_for_non_existance(['file1_2', 'file1_4'])
        self._check_for_existance(['file1_3'])

    ##
    # This is another case where everything comes up successfully and the
    # garbage collector should not purge the persistent data.  It is related to
    # the following test case where the node will have been instantiated, but
    # it won't have completely started up.
    def test_d(self):
        files = ['file1_2']

        # Create bogus persistent files
        for f in files:
            self._create_file(self._build_path(f))
        
        self._dm.register('/test1/test2/test3', self._build_path('file1_2'),
                          GC_ONDELETE)
        
        self._dm.set_faillist([])

        # Now simulate a restart
        self._local_restart()

        # Create an actual node for test1
        test1 = CompositeNode()
        test1.configure({'parent':self.root, 'name':'test1'})
        test2 = CompositeNode()
        test2.configure({'parent':test1, 'name':'test2'})
        test3 = CompositeNode()
        test3.configure({'parent':test2, 'name':'test3'})

        # Register on test3's behalf
        self._dm.register('/test1/test2/test3', self._build_path('file1_2'),
                          GC_ONDELETE)
        
        self._dm.set_faillist([])

        self._check_for_existance(['file1_2'])
        
    ##
    #
    # @fixme:  Don't run this test case for now, it relies on an as_node in
    #          the Garbage Collector working, and it doesn't for some reason.
    def _test_e(self):
        files = ['file1_2']

        # Create bogus persistent files
        for f in files:
            self._create_file(self._build_path(f))
        
        self._dm.register('/test1/test2/test3', self._build_path('file1_2'),
                          GC_ONDELETE)
        
        self._dm.set_faillist([])

        # Now simulate a restart
        self._local_restart()

        # Create an actual node for test1
        test1 = CompositeNode()
        test2 = CompositeNode()
        test3 = CompositeNode()
        
        test1.configure({'parent':self.root, 'name':'test1'})
        test2.configure({'parent':test1, 'name':'test2'})
        test3.configure({'parent':test2, 'name':'test3'})

        self.root.start()

        x = as_node('/test1/test2/test3')

        # Skip Registering on test3's behalf
        
        self._dm.set_faillist([])
        
        # The persistent file should still be there because the node exists,
        # even though it didn't register.  It should be kept because the node
        # definitely has not been deleted, but probably had a failure on
        # startup (and the purging policy was GC_ONDELETE).
        self._check_for_existance(['file1_2'])

    ##
    # Tests the case where a node is deleted on the same startup as it's parent
    # fails to start.  On the next startup (or whenever the parent gets
    # successfully started), the node's persistent data should be removed (if
    # the appropriate purge policy has been specified of course).
    def test_f(self):
        files = ['file1_2', 'file1_3']

        # Create bogus persistent files
        for f in files:
            self._create_file(self._build_path(f))

        # Our node tree is going to look like:
        # /test1/
        #       /test2
        #             /test1
        # /services
        #          /garbage_collector
        
        # Simulate first startup, everything happy
        test1 = CompositeNode()
        test2 = CompositeNode()
        test3 = CompositeNode()
        
        test1.configure({'parent':self.root, 'name':'test1'})
        test2.configure({'parent':test1, 'name':'test2'})
        test3.configure({'parent':test2, 'name':'test1'})
        
        self._dm.register('/test1/test2',       self._build_path('file1_2'),
                          GC_ONDELETE)
        self._dm.register('/test1/test2/test1', self._build_path('file1_3'),
                          GC_ONDELETE)

        self._dm.set_faillist([])

        # Now simulate a restart
        self._local_restart()

        # Simulate second startup, /test1/test2 fails to config and
        # /test1/test2/test1 has been deleted.  At this point, the persistent
        # data for /test1/test2/test1 should still exist.        
        test1 = CompositeNode()
        test2 = CompositeNode()
        test3 = CompositeNode()
        
        test1.configure({'parent':self.root, 'name':'test1'})
        test2.configure({'parent':test1, 'name':'test2'})
        
        self._dm.set_faillist([{'name':'test2', 'parent':'/test1',
                                'type':'config'}])

        self._check_for_existance(files)

        # Now simulate a restart
        self._local_restart()

        # OK, finally simulate a third startup, /test1/test2 comes up happily.
        # At this point, the Garbage Collector should figure out that
        # /test1/test2/test1 has been deleted and get rid of it's persistent
        # data.
        test1 = CompositeNode()
        test2 = CompositeNode()
        test3 = CompositeNode()
        
        test1.configure({'parent':self.root, 'name':'test1'})
        test2.configure({'parent':test1, 'name':'test2'})
        
        self._dm.register('/test1/test2', self._build_path('file1_2'),
                          GC_ONDELETE)

        self._dm.set_faillist([])

        self._check_for_non_existance(['file1_3'])
        self._check_for_existance(['file1_2'])

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

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
import time

from mpx_test import DefaultTestFixture
from mpx_test import main

from mpx.lib.threading import Lock
from mpx.lib.threading import Queue

from mpx.lib.thread_pool import HIGH
from mpx.lib.thread_pool import NORESULT
from mpx.lib.thread_pool import PendingAction
from mpx.lib.thread_pool import PendingResult
from mpx.lib.thread_pool import ThreadPool

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.lock = Lock()
        self.pool = ThreadPool(3)
        self.queue = Queue()
        self.simple_action_counter = 0
        return
    def tearDown(self):
        self.pool._unload()
        DefaultTestFixture.tearDown(self)
        return
    def simple_action(self, object):
        # @note It appears that even the '+= 1' operation is not
        #       guaranteed to be atomic.
        self.lock.acquire()
        self.simple_action_counter += 1
        self.lock.release()
        return 'simple_action_result'
    def slow_action(self, object):
        time.sleep(1.0)
        return 'slow_action_result'
    def simple_queue_action(self, object):
        self.queue.put(object)
        return
    def test_simple_queue(self):
        self.pool.queue(self.simple_queue_action, self)
        result = self.queue.get(1.0)
        if result is not self:
            raise "Queue returned %r instead of self, %r." % (result, self)
        return
    def test_result(self):
        t1 = time.time()
        pending_result = self.pool.queue(self.simple_action, self)
        result = pending_result.result(10.0)
        t2 = time.time()
        if result != 'simple_action_result':
            raise (
                "pending_result.result() returned the wrong value (%s)." %
                result
                )
        if (t2-t1) >= 10.0:
            raise "pending_result.result() blocked for no reason."
        return
    def test_pending_reasult(self):
        t1 = time.time()
        pending_result = PendingResult(None, None, self.simple_action, self)
        pending_result_two = self.pool.queue_pending_result(pending_result)
        if pending_result_two is not pending_result:
            raise "pending_result_two is NOT pending_result"
        result = pending_result.result(10.0)
        t2 = time.time()
        if result != 'simple_action_result':
            raise (
                "pending_result.result() returned the wrong value (%s)." %
                result
                )
        if (t2-t1) >= 10.0:
            raise "pending_result.result() blocked for no reason."
        return
    def test_pending_action(self):
        pending_action = PendingAction(self.simple_queue_action, self)
        self.pool.queue_pending_action(pending_action)
        result = self.queue.get(1.0)
        if result is not self:
            raise "Queue returned %r instead of self, %r." % (result, self)
        return
        return
    def test_result_timeout(self):
        t1 = time.time()
        pending_result = self.pool.queue(self.slow_action, self)
        result = pending_result.result(0.25)
        t2 = time.time()
        if (t2-t2) >= 1.0:
            raise "Blocked 1 second when a 1/4 second timeout."
        if result != NORESULT:
            raise "Got a result (%s) when none was expected."
        return
    def test_1000_actions(self):
        for i in xrange(0,1000):
            self.pool.queue(self.simple_action, self)
        time.sleep(0.1)
        t1 = time.time()
        while self.simple_action_counter < 1000:
            tn = time.time()
            if (tn-t1) > 3.0:
                raise (
                    "Taking ridiculously long to process 1000 queued actions."
                    )
            time.sleep(0.1)
        return
    def test_HIGH_pool_1(self):
        t1 = time.time()
        pending_result = HIGH.queue(self.simple_action, self)
        result = pending_result.result(10.0)
        t2 = time.time()
        if result != 'simple_action_result':
            raise (
                "pending_result.result() returned the wrong value (%s)." %
                result
                )
        if (t2-t1) >= 10.0:
            raise "pending_result.result() blocked for no reason."
        return
    def test_HIGH_pool_2(self):
        self.test_HIGH_pool_1()
        return
    def test_HIGH_pool_resize_1(self):
        HIGH.resize(1)
        if HIGH.size() != 1:
            raise "Resize to 1 thread failed."
        for i in xrange(0,100):
            HIGH.queue(self.simple_action, self)
        t1 = time.time()
        while self.simple_action_counter < 100:
            tn = time.time()
            if (tn-t1) > 3.0:
                raise (
                    "Taking ridiculously long to process 100 queued actions."
                    )
            time.sleep(0.1)
        return
    def test_HIGH_pool_resize_20(self):
        HIGH.resize(20)
        if HIGH.size() != 20:
            raise "Resize to 20 threads failed."
        for i in xrange(0,100):
            HIGH.queue(self.simple_action, self)
        t1 = time.time()
        while self.simple_action_counter < 100:
            tn = time.time()
            if (tn-t1) > 3.0:
                raise (
                    "Taking ridiculously long to process 100 queued actions."
                    )
            time.sleep(0.1)
        return

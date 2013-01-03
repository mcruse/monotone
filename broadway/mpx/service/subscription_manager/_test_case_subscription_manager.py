"""
Copyright (C) 2003 2005 2006 2010 2011 Cisco Systems

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
# @todo 1. Test assorted Node error conditions:
#          - ETimeout
#          - No such node
#          - No such node, deferred creation
#          - Other exceptions
# @todo 2. Test changes to the subscription while: poll_all, poll_changes,
#          and accepting events.
# @todo 3. Prove the slow poll list works...

from mpx_test import DefaultTestFixture
from mpx_test import main

import time

import mpx.lib # Bootstraping...

from mpx.lib import Result

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute

from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import EventProducerMixin

from mpx.lib.exceptions import EBadBatch

from mpx.lib.node import CompositeNode
from mpx.lib.node import Node
from mpx.lib.node import as_internal_node

from mpx.lib.threading import Lock

from mpx.service.subscription_manager import ENoSuchNodeID
from mpx.service.subscription_manager import ENoSuchSubscription
from mpx.service.subscription_manager import ENodeIDExists
from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER
from mpx.service.subscription_manager import SubscriptionManager

class GetException(CompositeNode):
    def configure(self, cd):
        CompositeNode.configure(self, cd)
        set_attribute(self, 'exception', Exception, cd)
        set_attribute(self, 'args', ("GetException",), cd, tuple)
        return
    def configuration(self, config=None):
        config = ServiceNode.configuration(self, config)
        get_attribute(self, 'exception', config)
        get_attribute(self, 'args', config)
        return config
    def get(self, skipCache=0):
        raise self.exception(*self.args)

class EventProducerTestClass(CompositeNode, EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self._old_value = 100
        return
    ##
    # answer true to let Subscription Manager know it can look for events from
    # us
    def has_cov(self):
        return 1
    ##
    # see if something changed and
    # let anyone interested know about it
    def _cov_check(self, new_value):
        if new_value != self._old_value:
            cov = ChangeOfValueEvent(self, self._old_value, new_value,
                                     time.time())
            self._old_value = new_value
            self.event_generate(cov) #trigger the event using the Mixin class.
        return
    def get(self, skipCache=1):
        return self._old_value
    def event_subscribe(self, *args):
        result = EventProducerMixin.event_subscribe(self, *args)
        # @note:  COV model REQUIRES generating an initial event.
        self.event_generate(ChangeOfValueEvent(self, self.get(), self.get(),
                                               time.time()))
        return result
class _Batch:
    def __init__(self, batch_table):
        self.batch_table = batch_table
        # Force the same order for a warm fuzzy.
        self.batch_keys = batch_table.keys()
        return
    def get_batch(self):
        response = {}
        for k in self.batch_keys:
            response[k] = self.batch_table[k].get_result()
        return response

class BatchManager:
    def create_batches(self, batch_table):
        batches = []
        remaining_keys = batch_table.keys()
        while remaining_keys:
            batch_keys = remaining_keys[:15]
            remaining_keys = remaining_keys[15:]
            sub_table = {}
            for k in batch_keys:
                sub_table[k] = batch_table[k]
            batches.append(_Batch(sub_table))
        return batches
    def get_batch(self, batch):
        result = batch.get_batch()
        return result
    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        return """BatchManager(%X)""" % id(self)
    def __getattr__(self, name):
        print "*"*60
        import traceback
        print "BatchManager.__getattr__(%r)" % name
        print "-"*60
        traceback.print_stack()
        print "*"*60
        return

class FastNode(Node):
    def __init__(self):
        Node.__init__(self)
        self.value = 0L
        return
    def get(self, skipCache=0):
        self.value += 1
        return self.value
    def get_result(self, skipCache=0, **keywords):
        return Result(self.get(), time.time())

class SlowNode(FastNode):
    def get(self, skipCache=0):
        time.sleep(4)
        return FastNode.get(self, skipCache)

class ErrorNode(FastNode):
    def get(self, skipCache=0):
        FastNode.get(self, skipCache)
        if self.value & 1:
            raise NotImplementedError
        return self.value

class BatchNode(FastNode):
    bm = BatchManager()
    def __init__(self, ebadbatch=0):
        FastNode.__init__(self)
        if ebadbatch:
            self.get = self.get_ebadbatch
        else:
            self.get = self.get_value
        return
    def configure(self, cd):
        FastNode.configure(self, cd)
        return
    def get_ebadbatch(self, skipCache=0):
        self.get = self.get_value
        self.bm = None
        raise EBadBatch(self.as_node_url())
    def get_value(self, skipCache=0):
        return FastNode.get(self, skipCache)
    def get_batch_manager(self):
        return self.bm

class PrintOnCOV(EventConsumerMixin):
    def __init__(self):
        EventConsumerMixin.__init__(self, self.__print_on_cov)
        return
    def __print_on_cov(self, event):
        results = event.results()
        for k in results.keys():
            print "%s: %r" % (k, results[k]['value'])
            continue
        return

class TestCase(DefaultTestFixture, EventConsumerMixin):
    ID1 = "/services/time/UTC/second"
    ID2 = "/services/time/local"
    nrt1to2 = {
        ID1:ID1,
        ID2:ID2,
        }
    ID3 = "/services/time/UTC/milliseconds"
    ID4 = "/services/time/local/minute"
    nrt3to4 = {
        ID3:ID3,
        ID4:ID4,
        }
    nrt1to4 = {}
    nrt1to4.update(nrt1to2)
    nrt1to4.update(nrt3to4)
    ID5 = "/services/time/local/day"
    nrtB10 = {}
    for i in range(0,10):
        url = "/BatchNode-%03d" % i
        nrtB10[url] = url
    del url
    def __init__(self, *args, **kw):
        DefaultTestFixture.__init__(self, *args,**kw)
        EventConsumerMixin.__init__(self, self.change_of_value)
        self.__event_lock = Lock()
        self.__event_updated_values = {}
        self._cov_counter = 0
        return
    def change_of_value(self,event):
        self._cov_counter += 1
        results = event.results()
        self.__event_lock.acquire()
        try:
            self.__event_updated_values.update(results)
        finally:
            self.__event_lock.release()
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.__event_updated_values = {}
        self.new_node_tree()
        root = as_internal_node('/')
        self._cov_counter = 0
        GetException().configure({'name':'exception', 'parent':'/services'})
        SUBSCRIPTION_MANAGER.configure({'debug':0,
                                        '_normal_pool_size':2,
                                        '_slow_pool_size':2,
                                        '_prime_pool_size':2,
                                        '_minimum_poll_interval':0.001,
                                        '_slow_poll_threshold':0.500,
                                        }
                                       )
        for i in range(0,10):
            f = FastNode()
            f.configure({'parent':root, 'name':"FastNode-%03d"%i})
            s = SlowNode()
            s.configure({'parent':root, 'name':"SlowNode-%03d"%i})
            e = ErrorNode()
            e.configure({'parent':root, 'name':"ErrorNode-%03d"%i})
            b = BatchNode(i & 1)
            b.configure({'parent':root, 'name':"BatchNode-%03d"%i})
        root.start()
        return
    def tearDown(self):
        self.del_node_tree()
        DefaultTestFixture.tearDown(self)
        # self.dump_msglog()
        return
    def __values_changing(self, sid):
        r1 = SUBSCRIPTION_MANAGER.poll_all(sid)
        t1 = time.time()
        while 1:
            changed_values = SUBSCRIPTION_MANAGER.poll_changed(sid)
            if len(changed_values):
                return
            if (time.time() - t1) > 1.0:
                raise "Never got changes for any of the values."
            time.sleep(0.1)
        assert 1, "Can't reach here."
    def __all_plus_exceptions_check(self, all_values):
        no_such_node = all_values[
            '/services/time/is/an/illusion']['value']
        assert isinstance(no_such_node,
                          mpx.lib.exceptions.ENoSuchName), (
            "%r is not mpx.lib.exceptions.ENoSuchName" % no_such_node
            )
        get_exception = all_values['/services/exception']['value']
        assert get_exception.__class__ is Exception, (
            "%r is not an Exception" % get_exception
            )
        assert get_exception.args == ("GetException",), (
            "%r is not %r" % (get_exception.args, ("GetException",))
            )
        return
    def test_create_polled(self):
        sid = SUBSCRIPTION_MANAGER.create_polled()
        return
    def test_create_delivered(self):
        sid = SUBSCRIPTION_MANAGER.create_delivered(self, self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        time.sleep(0.1)
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            self.__event_lock.acquire()
            try:
                if len(self.__event_updated_values) == 4:
                    # We got all 4 values!
                    return
            finally:
                self.__event_lock.release()
            time.sleep(0.1)
        if len(self.__event_updated_values) != 4:
            raise (("Never got changes for all four values, only %d.\n"
                    "Values: %r") % (len(self.__event_updated_values),
                                     self.__event_updated_values))
    def test_destroy(self):
        sids = []
        for i in range(2):
            # ID3 is /services/time/UTC/milliseconds which should
            # change "really fast."
            sid = SUBSCRIPTION_MANAGER.create_polled({self.ID3:self.ID3})
            # Make sure it comes up.
            t1 = time.time()
            self.__values_changing(sid)
            sids.append(sid)
        # Double check the values are changing.
        for sid in sids:
            self.__values_changing(sid)
        # Now nuke one of the suscriptions and see that the other stays valid.
        sid = sids.pop(0)
        SUBSCRIPTION_MANAGER.destroy(sid)
        try:
            SUBSCRIPTION_MANAGER.destroy(sid)
        except ENoSuchSubscription:
            pass
        else:
            raise "No such subscription not detected."
        # Make sure that the other subscription is valid.
        sid = sids.pop(0)
        self.__values_changing(sid)
        # Finally, make sure that the mnr is removed when the last snr is
        # deleted.
        if len(SUBSCRIPTION_MANAGER.diag_get_mnrs()) != 1:
            raise (
                "Bogus test, there should be 1 mnr at this point, not %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnrs()))
        SUBSCRIPTION_MANAGER.destroy(sid)
        if len(SUBSCRIPTION_MANAGER.diag_get_mnrs()) != 0:
            raise (
                "There should not be any mnrs at this point,"
                " but there are %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnrs()))
        return
    def test_destroy_batch(self):
        sids = []
        for i in range(2):
            # BatchNodes change "really fast."
            sid = SUBSCRIPTION_MANAGER.create_polled(self.nrtB10)
            # Make sure it comes up.
            t1 = time.time()
            self.__values_changing(sid)
            sids.append(sid)
        # Double check the values are changing.
        for sid in sids:
            self.__values_changing(sid)
        # Now nuke one of the suscriptions and see that the other stays valid.
        sid = sids.pop(0)
        SUBSCRIPTION_MANAGER.destroy(sid)
        try:
            SUBSCRIPTION_MANAGER.destroy(sid)
        except ENoSuchSubscription:
            pass
        else:
            raise "No such subscription not detected."
        # Make sure that the other subscription is valid.
        sid = sids.pop(0)
        self.__values_changing(sid)
        if len(SUBSCRIPTION_MANAGER.diag_get_mnrs()) != 10:
            raise (
                "Bogus test, there should be 10 mnr at this point, not %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnrs()))
        if len(SUBSCRIPTION_MANAGER.diag_get_mnbs()) != 1:
            raise (
                "Bogus test, there should be 1 mnb at this point, not %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnbs()))
        SUBSCRIPTION_MANAGER.destroy(sid)
        # Make sure that the mnr is removed when the last snr is deleted.
        if len(SUBSCRIPTION_MANAGER.diag_get_mnrs()) != 0:
            raise (
                "There should not be any mnrs at this point,"
                " but there are %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnrs()))
        # Finally, make sure that the mnb is removed when the last mnr is
        # deleted.
        if len(SUBSCRIPTION_MANAGER.diag_get_mnbs()) != 0:
            raise (
                "There should not be any mnbs at this point,"
                " but there are %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnbs()))
        return
    def test_node_reference_table(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to2)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to2:
            raise "Node reference table mismatch."
        return
    def test_merge(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to2)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to2:
            raise "Initial node reference table mismatch."
        SUBSCRIPTION_MANAGER.merge(sid, self.nrt3to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Node reference table mismatch."
        return
    def test_replace(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to2)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to2:
            raise "Initial node reference table mismatch."
        SUBSCRIPTION_MANAGER.replace(sid, self.nrt3to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt3to4:
            raise "Replaced node reference table mismatch."
        return
    def test_empty(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        SUBSCRIPTION_MANAGER.empty(sid)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != {}:
            raise "Node reference table not empty."
        return
    def test_add(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to2)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to2:
            raise "Initial node reference table mismatch."
        SUBSCRIPTION_MANAGER.add(sid, self.ID5, self.ID5)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        nrt125 = {}
        nrt125.update(self.nrt1to2)
        nrt125[self.ID5] = self.ID5
        if nrt != nrt125:
            raise "Node reference table mismatch."
        try:
            SUBSCRIPTION_MANAGER.add(sid, self.ID5, self.ID5)
        except ENodeIDExists:
            pass
        else:
            raise "Node ID in use not detected."
        return
    def test_add_and_get(self):
        st_time = time.time()
        rdict = SUBSCRIPTION_MANAGER.create_polled_and_get(self.nrt1to2)
        # Ensure we got back values for everything
        assert rdict['sid'] != None, "sid is not set in results dictionary."
        for x in rdict['values'].values():
            assert x != None, "Got None in values: %s." % str(rdict['values'])
        
    def test_modify(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to2)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to2:
            raise "Initial node reference table mismatch."
        SUBSCRIPTION_MANAGER.modify(sid, self.ID2, self.ID3)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt == self.nrt1to2:
            raise "Modified node reference table not modified."
        if nrt != {self.ID1:self.ID1,self.ID2:self.ID3}:
            raise "Modified node reference table mismatch."
        try:
            SUBSCRIPTION_MANAGER.modify(sid, self.ID3, self.ID2)
        except ENoSuchNodeID:
            pass
        else:
            raise "No such NodeID not detected."
        return
    def test_remove(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        SUBSCRIPTION_MANAGER.remove(sid, self.ID2)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        nrt134 = {}
        nrt134.update(self.nrt1to4)
        del nrt134[self.ID2]
        if nrt != nrt134:
            raise "Node reference table mismatch."
        try:
            SUBSCRIPTION_MANAGER.remove(sid, self.ID2)
        except ENoSuchNodeID:
            pass
        else:
            raise "No such NodeID not detected."
        return
    def test_poll_all(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        # Check that each invokation gets all values.
        for i in range(0,10):
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            if len(all_values) != len(self.nrt1to4):
                # We did not get all 4 values!
                raise (
                    "poll_all(self.nrt1to4) did not return all values."
                    " (%d out of %d)" % (len(all_values),len(self.nrt1to4))
                    )
        # Check that (eventually) all the values are result dictionaries.
        all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            if None not in all_values.values():
                return
            time.sleep(0.1)
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        if None in all_values.values():
            raise (
                "Never got changes for all four result dictionaries, %d." %
                len(all_values)
                )
        return
    def test_poll_all_plus_exceptions(self):
        SUBSCRIPTION_MANAGER._set_tunable_parameters({
            'minimum_poll_interval':0.0,
            })
        nrt1to4bad5to6 = {}
        nrt1to4bad5to6.update(self.nrt1to4)
        nrt1to4bad5to6['/services/time/is/an/illusion'] = (
            '/services/time/is/an/illusion'
            )
        nrt1to4bad5to6['/services/exception'] = '/services/exception'
        sid = SUBSCRIPTION_MANAGER.create_polled(nrt1to4bad5to6)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != nrt1to4bad5to6:
            raise "Initial node reference table mismatch."
        # Check that each invokation gets all values.
        for i in range(0,10):
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            if len(all_values) != len(nrt1to4bad5to6):
                # We did not get all 4 values!
                raise (
                    "poll_all(self.nrt1to4) did not return all values."
                    " (%d out of %d)" % (len(all_values),len(nrt1to4bad5to6))
                    )
        # Check that (eventually) all the values are result dictionaries.
        all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            if None not in all_values.values():
                self.__all_plus_exceptions_check(all_values)
                # Finally, test that a new subscription gets the correct
                # results.
                time.sleep(0.1)
                sid = SUBSCRIPTION_MANAGER.create_polled(nrt1to4bad5to6)
                time.sleep(0.1)
                all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
                self.__all_plus_exceptions_check(all_values)                
                time.sleep(0.1)
                all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
                self.__all_plus_exceptions_check(all_values)                
                return
            time.sleep(0.1)
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        if None in all_values.values():
            raise ("Never got values for all nodes: %r." % all_values)
        return
    def test_poll_changed(self):
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        all_values = {}
        time.sleep(0.1)
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            time.sleep(0.1)
            changed_values = SUBSCRIPTION_MANAGER.poll_changed(sid)
            all_values.update(changed_values)
            if len(all_values) == 4:
                # We got all 4 values!
                return
        raise "Never got changes for all four values, %d." % len(all_values)
        return
    def test_fast_minimum_poll_interval(self):
        SUBSCRIPTION_MANAGER._set_tunable_parameters({
            'minimum_poll_interval':0.0,
            })
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        # Check that each invokation gets all values.
        for i in range(0,10):
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            if len(all_values) != len(self.nrt1to4):
                # We did not get all 4 values!
                raise (
                    "poll_all(self.nrt1to4) did not return all values."
                    " (%d out of %d)" % (len(all_values),len(self.nrt1to4))
                    )
        # Check that (eventually) all the values are result dictionaries.
        all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            time.sleep(0.1)
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        if None in all_values.values():
            raise (("Never got changes for all four result dictionaries, %d.\n"
                    "Values: %r") % (len(all_values),all_values))
        # ID3 is /services/time/UTC/milliseconds which should
        # change "really fast."
        c1 = all_values[self.ID3]['changes']
        time.sleep(1.0)
        all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        c2 = all_values[self.ID3]['changes']
        if (c2 - c1) < 25: # It's usually 500 on fearfactory...
            raise "%r only changed %d times in one second." % (
                self.ID3, (c2 - c1),
                )
        return
    def test_adjusted_minimum_poll_interval(self):
        SUBSCRIPTION_MANAGER._set_tunable_parameters({
            'minimum_poll_interval':0.2,
            })
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrt1to4)
        nrt = SUBSCRIPTION_MANAGER.node_reference_table(sid)
        if nrt != self.nrt1to4:
            raise "Initial node reference table mismatch."
        # Check that each invokation gets all values.
        for i in range(0,10):
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            if len(all_values) != len(self.nrt1to4):
                # We did not get all 4 values!
                raise (
                    "poll_all(self.nrt1to4) did not return all values."
                    " (%d out of %d)" % (len(all_values),len(self.nrt1to4))
                    )
        # Check that (eventually) all the values are result dictionaries.
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            if None not in all_values.values():
                # ID3 is /services/time/UTC/milliseconds which should
                # change "really fast."
                c1 = all_values[self.ID3]['changes']
                time.sleep(1.0)
                all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
                c2 = all_values[self.ID3]['changes']
                if (c2 - c1) > 6: # 0.2 == Max 5/second.
                    raise ("1/5th second throttle failed,"
                           " %r changed %d times in one second.") % (
                        self.ID3, (c2 - c1),
                        )
                return
            time.sleep(0.1)
        raise (
            "Never got changes for all four result dictionaries, %d." %
            len(all_values)
            )
        return
    def test_polled_event_handling(self):
        event_maker = EventProducerTestClass()
        event_maker.configure({'name':'EventProducerTester','parent':'/'})
        event_maker.start()
        sid = SUBSCRIPTION_MANAGER.create_polled({1:event_maker})

        # Wait for polling to start and verify value made it without any events
        t1 = time.time()
        all_values = {1: None}
        while all_values[1] is None:
            if (time.time() - t1) > 1.0:
                raise "Got tired of waiting..."
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            time.sleep(0.1)
        # Check that subscription value is the initial value of 100
        if all_values[1]['value'] != 100:
            raise ("polled_event_handling did not return inital value: " +
                   str(all_values[1]['value']))
        # make a rapid series of changes to the node value
        for i in range(10):
            event_maker._cov_check(i)
            time.sleep(0.1)
        # check change count, should be approx 10
        all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
        change_count = all_values[1]['changes']
        if change_count < 8 or change_count > 12:
            raise (
                "polled_event_handling change count wrong."
                "  Should be approx 10, not %d" % (change_count,)
                )
        # Check that the last value is corrent.
        final_value = all_values[1]['value']
        if final_value != 9:
            raise (
                "polled_event_handling final value incorrect."
                "  Should be 9, not %d" % (final_value,)
                )
        return
    def test_targeted_event_handling(self):
        event_maker = EventProducerTestClass()
        event_maker.configure({'name':'EventProducerTester','parent':'/'})
        event_maker.start()
        nr = {1:event_maker}
        sid = SUBSCRIPTION_MANAGER.create_delivered(self, nr)

        # Wait for polling to start and verify value made it without any events
        t1 = time.time()
        while (time.time() - t1) < 1.0:
            all_values = SUBSCRIPTION_MANAGER.poll_all(sid)
            time.sleep(0.1)
        # Check that subscription value is the initial value of 100
        if all_values[1]['value'] != 100:
            raise ("polled_event_handling did not return inital value: " +
                   str(all_values[1]['value']))
        # make a rapid series of changes to the node value
        for i in range(10):
            event_maker._cov_check(i)
            time.sleep(0.1)
        # check change count, should be approx 10
        value_updates = self.__event_updated_values[1]['changes']
        cov_counts = self._cov_counter
        if value_updates < cov_counts:
            raise (
                "Targeted event handling event count did not match %d vs %d"
                % (value_updates, cov_counts)
                )
    def test_timeout(self):
        sids = []
        for i in range(2):
            if not i:
                timeout = 1.0
            else:
                timeout = None
            # ID3 is /services/time/UTC/milliseconds which should
            # change "really fast."
            sid = SUBSCRIPTION_MANAGER.create_polled({self.ID3:self.ID3},
                                                     timeout)
            # Make sure it comes up.
            t1 = time.time()
            self.__values_changing(sid)
            sids.append(sid)
        # Double check the values are changing and that the subscriptions
        # stay valid while we poll for values.
        t1 = time.time()
        while (time.time() - t1) < 2.0:
            for sid in sids:
                self.__values_changing(sid)
            time.sleep(0.1)
        # Now ensure that sid[0] times out...
        sid = sids.pop(0)
        t1 = time.time()
        while sid in SUBSCRIPTION_MANAGER.diag_get_sids():
            if (time.time()-t1) > 2.0:
                raise "%r did not timeout." % sid
            time.sleep(0.1)
        # Finally, make sure that the other subscription is valid.
        sid = sids.pop(0)
        self.__values_changing(sid)
        return
    def test_timeout_batch(self):
        # nrtB10 changes "really fast."
        sid = SUBSCRIPTION_MANAGER.create_polled(self.nrtB10, 1.0)
        # Make sure it comes up.
        t1 = time.time()
        self.__values_changing(sid)
        # Double check the values are changing and that the subscriptions
        # stay valid while we poll for values.
        t1 = time.time()
        while (time.time() - t1) < 2.0:
            self.__values_changing(sid)
            time.sleep(0.1)
        if len(SUBSCRIPTION_MANAGER.diag_get_mnrs()) != 10:
            raise (
                "Bogus test, there should be 10 mnr at this point, not %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnrs()))
        if len(SUBSCRIPTION_MANAGER.diag_get_mnbs()) != 1:
            raise (
                "Bogus test, there should be 1 mnb at this point, not %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnbs()))
        t1 = time.time()
        while sid in SUBSCRIPTION_MANAGER.diag_get_sids():
            if (time.time()-t1) > 2.0:
                raise "%r did not timeout." % sid
            time.sleep(0.1)
        # Make sure that the mnr is removed when the last snr is deleted.
        if len(SUBSCRIPTION_MANAGER.diag_get_mnrs()) != 0:
            raise (
                "There should not be any mnrs at this point,"
                " but there are %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnrs()))
        # Finally, make sure that the mnb is removed when the last mnr is
        # deleted.
        if len(SUBSCRIPTION_MANAGER.diag_get_mnbs()) != 0:
            raise (
                "There should not be any mnbs at this point,"
                " but there are %r." %
                len(SUBSCRIPTION_MANAGER.diag_get_mnbs()))
        return
    #
    #
    #
    def _print_subscriptions(self):
        print ""
        print "*"*60
        for s in SUBSCRIPTION_MANAGER.diag_get_subscriptions():
            print s
        print "*"*60
        return
    def _print_sids(self):
        print ""
        print "*"*60
        for s in SUBSCRIPTION_MANAGER.diag_get_sids():
            print s
        print "*"*60
        return
    def _print_mnrs(self):
        print ""
        print "*"*60
        for s in SUBSCRIPTION_MANAGER.diag_get_mnrs():
            print s
        print "*"*60
        return
    def _print_mnbs(self):
        print ""
        print "*"*60
        for s in SUBSCRIPTION_MANAGER.diag_get_mnbs():
            print s
        print "*"*60
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

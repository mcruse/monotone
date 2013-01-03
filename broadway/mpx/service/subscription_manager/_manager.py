"""
Copyright (C) 2003 2004 2005 2006 2007 2008 2009 2010 2011 Cisco Systems

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
#
#
# @todo 1. Complete MontyDoc documentation...
# @todo 7. Add efficient single-point subscribe for fallback cached-get().
# @todo 8. Add shared/timedout subscriptions for batch reuse.
# @todo 9. Add diagnostic API for statistics, etc.
# @todo 10. Saved node and batch manager reference should use a weak reference.
# @todo 11. Ensure that shutdown really shutsdown.
# @todo 12. Keep unsuscribed MNRs and batch managers (as long as they still
#           reference valid objects) allowing clients to instantly get the
#           last fetched value, for caching, etc...

import copy
import traceback
import StringIO
import warnings
import sys
import types
from threading import RLock
from threading import Event as Flag
from time import time as now
from time import sleep
from moab.linux.lib import uptime

import mpx.lib # Bootstraping...

from mpx.lib import ReloadableSingletonFactory
from mpx.lib import Result
from mpx.lib import msglog
from mpx.lib import thread_pool
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import ChangingCovEvent
from mpx.lib.event import Event
from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import EventProducerMixin
from mpx.lib.exceptions import EBadBatch
from mpx.lib.exceptions import EInternalError
from mpx.lib.exceptions import ENoSuchNode
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ENotFound
from mpx.lib.exceptions import ECovNode
from mpx.lib.exceptions import ENonCovNode
from mpx.lib.exceptions import MpxException, Exception
from mpx.lib.node import as_internal_node
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import Alias, Aliases
from mpx.lib.node.interfaces import IAliasNode
from mpx.lib.rna import NodeFacade
from mpx.lib.scheduler import scheduler
from mpx.lib.scheduler.datatypes import Counter
from mpx.lib.threading import Lock
from mpx.lib.threading import Thread
from mpx.lib.uuid import UUID
from mpx.service import ServiceNode
from mpx.service.time import Time
from mpx.lib import Callback
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER

debug = 0
##
# Class from which all SubscriptionManager specific exceptions are
# derived.
class ESubscriptionManager(MpxException):
    pass

class ENoSuchSubscription(ESubscriptionManager):
    pass

class ESubscription(ESubscriptionManager):
    pass

class ENodeIDExists(ESubscription):
    pass

class ENoSuchNodeID(ESubscription):
    pass

NoArgument = object()

def _exception_string(e):
    _print_exc_str = getattr(e,'_print_exc_str',None)
    if not _print_exc_str:
        s = StringIO.StringIO()
        traceback.print_exc(None,s)
        s.seek(0)
        _print_exc_str = s.read()
        del s
        if hasattr(e,'_print_exc_str'):
            e._print_exc_str = _print_exc_str
    return '%s.%s%r\n%s' % (e.__class__.__module__,
                            e.__class__.__name__,
                            e.args,
                            _print_exc_str)

##
# @note All access to SubscriptionNodeReferences is via the Subscription that
#       includes the SubscriptionNodeReference.  The Subscription node
#       reference table lock ensures that there are no race conditions.
#       Accessed via the _MasterNodeReference as well.
class SubscriptionNodeReference(object):
    """
        Represents a nid-node mapping in a particular subscription.
    """
    def __init__(self, subscription, nid, nodespec):
        self._nid = nid
        self._node = None
        self._nodeurl = None
        self._nodespec = nodespec
        self.current_result = None
        self.changes = Counter()    
        self._masternode = None
        self._mastertable = None
        self._scheduled = None
        self._subscription = subscription
        self.registration_completed = False
        self.registration_initiated = False
        self.registration_cancelled = False
        self.next_resolve = self.resolve_node
        self.registration_failures = Counter()
        super(SubscriptionNodeReference, self).__init__()
    def initiate_registration(self, nodetable):
        if self.registration_initiated:
            raise TypeError("%s registration already initiated" % self)
        self._mastertable = nodetable
        self.registration_initiated = True
        self.registration_cancelled = False
        self.enqueue_registration()
    def enqueue_registration(self):
        manager = self.subscription_manager()
        pool = manager._SubscriptionManager__prime_pool
        pool.queue_noresult(self.complete_registration)
    def subscription_manager(self):
        return SUBSCRIPTION_MANAGER
    def cancel_registration(self, nodetable):
        self._subscription.snrlock.acquire()
        try:
            self.registration_cancelled = True
            self.next_resolve = None
            scheduled = self._scheduled
            if scheduled:
                scheduled.cancel()
            self._scheduled = None
            if self.registration_completed:
                self._masternode.remove_snr(self._mastertable, self)
            self.registration_completed = False
            self._masternode = None
            self._mastertable = None
        finally:
            self._subscription.snrlock.release()
    def reschedule_registration(self, delay=5.0):
        if self.registration_completed:
            raise TypeError("%s registration already complete" % self)
        if self._scheduled:
            self._scheduled.cancel()
        if not self.registration_cancelled:
            register = self.enqueue_registration
            self._scheduled = scheduler.after(delay, register)
    def complete_registration(self):        
        self._scheduled = None
        while self.next_resolve:
            try:
                self.next_resolve()
            except Exception, error:
                changed = self.set_exception(error)
                count = self.registration_failures.increment()
                if changed:
                    errormsg = "%s registration failure #%d" % (self, count)
                    msglog.log("broadway", msglog.types.WARN, errormsg)
                    msglog.exception(prefix="handled")
                self.reschedule_registration(min(count * 5.0, 180))
                return
        self._subscription.snrlock.acquire()
        try:
            if not self.registration_cancelled:
                self._masternode.add_snr(self)
                self.registration_completed = True
        finally:
            self._subscription.snrlock.release()
    def resolve_node(self):
        try:
            self._node = as_internal_node(self._nodespec)
        except:
            self.next_resolve = self.resolve_node
            raise
        else:
            if IAliasNode.providedBy(self._node):
                self.next_resolve = self.resolve_alias
            elif isinstance(self._node, Aliases):
                self.next_resolve = self.resolve_aliases
            else:
                self.next_resolve = self.resolve_path
        return self._node
    def resolve_aliases(self):
        try:
            self._node = as_node(self._node.node_url)
        except:
            self.next_resolve = self.resolve_aliases
            raise
        else:
            self.next_resolve = self.resolve_path
        return self._node
    def resolve_alias(self):
        try:
            self._node = self._node.dereference(True)
        except:
            self.next_resolve = self.resolve_alias
            raise
        else:
            self.next_resolve = self.resolve_path
        return self._node
    def resolve_path(self):
        try:
            try:
                self._nodeurl = self._node.as_node_url()
            except:
                self._nodeurl = as_node_url(self._node)
        except:
            self.next_resolve = self.resolve_path
            raise
        else:
            self.next_resolve = self.resolve_mnr
        return self._nodeurl
    def resolve_mnr(self):
        nodeurl = self._nodeurl
        mastertable = self._mastertable
        MNR = _MasterNodeReference
        self._subscription.snrlock.acquire()
        try:
            if not self.registration_cancelled:
                self._masternode = MNR.for_url(mastertable, nodeurl)
        except:
            self.next_resolve = self.resolve_mnr
            raise
        else:
            self.next_resolve = None
        finally:
            self._subscription.snrlock.release()
        return self._masternode
    def nid(self, nid=NoArgument):
        result = self._nid
        if nid is not NoArgument:
            self._nid = nid
        return result
    def node_reference(self):
        return self._nodespec
    def node(self):
        if self._node:
            return self._node
        return as_internal_node(self._nodespec)
    def node_url(self):
        if self._nodeurl:
            return self._nodeurl
        return as_node_url(self._nodespec)
    def set_result(self, result):
        self._subscription.snrlock.acquire()
        try:
            if self.current_result:
                previous = self.current_result
                previous_value = previous.value
            else:
                # Set to a never to be returned value.
                previous_value = previous = NoArgument
            self.current_result = result
            try:
                # @fixme try block is a HACK to work around protocols that
                #        that return values that either are not new instances
                #        for changed values, or that do not support the
                #        inequality operator.  This MAY be the case for
                #        BACnet.
                if hasattr(previous, 'equals'):
                    changed = not previous.equals(result)
                else:
                    changed = (previous_value != result.value)
            except:
                changed = 1
            if changed:
                # Generate event for delivered
                self._subscription.touch_snr(self)
        finally:
            self._subscription.snrlock.release()
        return changed
    def set_exception(self, exception):
        self._subscription.snrlock.acquire()
        try:
            if self.current_result:
                last_result = self.current_result
                if isinstance(last_result.value, Exception):
                    previous = (last_result.value.__class__, 
                                last_result.value.args)
                else:
                    previous = (None, None)
            else:
                previous = None
            # If the Exception class and arguments are the same, 
            # assume it is unchanged.
            new_value = (exception.__class__, exception.args)
            if previous != new_value:
                if not hasattr(exception, '_print_exc_str'):
                    sio = StringIO.StringIO()
                    traceback.print_exc(None, sio)
                    exception._print_exc_str = sio.getvalue()
                    sio.close()
                new_result = Result(exception, now(), 0)
                self.current_result = new_result
                self._subscription.touch_snr(self)
                changed = True
            else:
                changed = False
        finally:
            self._subscription.snrlock.release()
        return changed
    def get_result(self):
        if self.current_result:
            self.current_result.changes = self.changes.getvalue()
        return self.current_result
    def __str__(self):
        typename = type(self).__name__
        details = ["'%s'" % self._subscription.id()]
        details.append("'%s'" % self.nid())
        details.append("'%s'" % self._nodespec)
        return "%s(%s)" % (typename, ", ".join(details))
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

##
# Dictionary of <code>SubscriptionNodeReference</code>s,
# keyed by the client supplied NID hashable object. 
class SubscriptionNodeReferenceDict(dict):
    pass

class SubscriptionNodeReferenceSet(set):
    pass

class SubscriptionResultMap(dict):
    pass

class NodeReferenceTable(dict):
    """
        Represents a nid to nodeurl mapping.
    """
    ##
    # NRT may be instantiated with a table of name, url pairs, 
    #   or a single node URL.  When a single node URL is used, 
    #   a table is built automatically wherein the names and 
    #   URLs are those of the node's children.
    def __init__(self, reference = {}):
        if isinstance(reference, str):
            node = as_node(reference)
            names = node.children_names()
            baseurl = reference
            # Build list of key,value tuples to initialize dict.
            reference = [(name, '%s/%s' % (baseurl, name)) for name in names]
        return super(NodeReferenceTable, self).__init__(reference)

class Subscription(EventProducerMixin):
    ##
    # Constructor for a new subscription.
    #
    # @param subscription_manager The SubscriptionManager that will manage
    #                             this subscription.
    # @note This class does not automatically add itself to the
    #       <code>subscription_manager</code>.
    def __init__(self, subscription_manager, timeout=None, id=None):
        EventProducerMixin.__init__(self)
        self._subscription_manager = subscription_manager
        self.snrlock = self._subscription_manager._SubscriptionManager__lock
        # Dictionary of <code>SubscriptionNodeReference</code>s,
        # keyed by the client supplied NID hashable object. 
        if id is None:
            id = UUID()
        self._id = id
        self._generate_change_events = 0
        self._generator_in_progress = 0
        # must poll this often or self will be destroyed and return the Budda
        self._timeout = timeout
        self._last_polled_at = uptime.secs()
        if timeout is not None:
            self._timeout_event = scheduler.after(
                self._timeout, self._timeout_handler)
        else:
            self._timeout_event = None
        self.primed = Flag()
        self.snrmap = SubscriptionNodeReferenceDict()
        self.changed = SubscriptionNodeReferenceSet()
        self.untouched = SubscriptionNodeReferenceSet()
    def is_primed(self):
        return self.primed.isSet()
    def await_priming(self, timeout=None):
        self.primed.wait(timeout)
        return self.is_primed()
    def _timeout_handler(self):
        time_remaining = (self._last_polled_at + self._timeout) - uptime.secs()
        if time_remaining <= 0.0:
            thread_pool.HIGH.queue_noresult(
                self._subscription_manager.destroy, self._id)
        else:
            self._timeout_event = scheduler.after(
                time_remaining, self._timeout_handler)
    def _changed_values(self):
        # Note, semi-private name indicates all bets are 
        # off if invoked from outside synchronized block.
        valuemap = SubscriptionResultMap()
        for snr in self.changed:
            valuemap[snr.nid()] = snr.get_result().as_dict()
        return valuemap
    def _all_values(self):
        # Note, semi-private name indicates all bets are 
        # off if invoked from outside synchronized block.
        valuemap = SubscriptionResultMap()
        for nid,snr in self.snrmap.items():
            value = snr.get_result()
            if value:
                value = value.as_dict()
            valuemap[nid] = value
        return valuemap
    def changed_values(self):
        self.reset_timeout()
        self.snrlock.acquire()
        try:
            changes = self._changed_values()
            self.changed.clear()
        finally:
            self.snrlock.release()
        return changes
    def all_values(self):
        self.reset_timeout()
        self.snrlock.acquire()
        try:
            values = self._all_values()
            self.changed.clear()
        finally:
            self.snrlock.release()
        return values
    def empty(self):
        self.snrlock.acquire()
        try:
            self._empty()
        finally:
            self.snrlock.release()
    def reset_timeout(self):
        self._last_polled_at = uptime.secs()
    ##
    # @return A string that is this subscription's unique id (aka the SID).
    def id(self):
        return str(self._id)
    ##
    # Update this subscriptions SubscriptionNodeReference table from the
    # client specified dictionary.
    #
    # @param node_reference_table The dictionary of node references
    #                             keyed by NIDs (the client specific, node
    #                             identifier) to merge into the existing
    #                             subscription.
    def merge(self, node_reference_table):
        self.snrlock.acquire()
        try:
            self._merge(node_reference_table)
        finally:
            self.snrlock.release()
    ##
    # @return A copy of the subscription's Node Reference Table.
    def node_reference_table(self):
        nid_map = NodeReferenceTable()
        self.snrlock.acquire()
        try:
            for nid,snr in self.snrmap.items():
                assert nid == snr.nid(), "Internal failure, nid != snr.nid()"
                nid_map[snr.nid()] = snr.node_reference()
        finally:
            self.snrlock.release()
        return nid_map
    ##
    # Completely replace a subscription's node reference table.
    #
    # @param node_reference_table A dictionary of node references keyed by
    #                             NIDs (the client specific, node identifier).
    def replace(self, node_reference_table):
        self.snrlock.acquire()
        try:
            self._empty()
            self._merge(node_reference_table)
            if self.untouched:
                self.primed.clear()
            else:
                self.primed.set()
        finally:
            self.snrlock.release()
    def remove(self, nid):
        self.snrlock.acquire()
        try:
            snr = self._get_subscription_node_reference(nid)
            if not snr:
                raise ENoSuchNodeID(nid)
            self._del_subscription_node_reference(snr)
            if not self.untouched:
                self.primed.set()
        finally:
            self.snrlock.release()
    def add(self, nid, node_reference):
        self.snrlock.acquire()
        try:
            snr = self._get_subscription_node_reference(nid)
            if snr:
                raise ENodeIDExists(nid)
            snr = SubscriptionNodeReference(self, nid, node_reference)
            self._add_subscription_node_reference(snr)
            if self.untouched:
                self.primed.clear()
        finally:
            self.snrlock.release()
    def modify(self, nid, node_reference):
        self.snrlock.acquire()
        try:
            snr = self._get_subscription_node_reference(nid)
            if not snr:
                raise ENoSuchNodeID(nid)
            self._del_subscription_node_reference(snr)
            snr = SubscriptionNodeReference(self, nid, node_reference)
            self._add_subscription_node_reference(snr)
            if self.untouched:
                self.primed.clear()
            else:
                self.primed.set()
        finally:
            self.snrlock.release()
    def _subscription_cov_event(self, event):
        pass
    def touch_snr(self, snr):
        self.snrlock.acquire()
        try:
            self._touch_snr(snr)
            if not self.untouched:
                self.primed.set()
        finally:
            self.snrlock.release()
    def _touch_snr(self, snr):
        snr.changes.increment()
        # Because changed is set-type, 
        # no need to test membership.
        self.changed.add(snr)
        self.untouched.discard(snr)
        if (self._generate_change_events and not self._generator_in_progress):
            # Set flag second in case queuing causes exception.
            thread_pool.HIGH.queue_noresult(self.notifycov)
            self._generator_in_progress = 1
    def notifycov(self):
        self.snrlock.acquire()
        try:
            event = self._generate_cov_event()
        finally:
            self.snrlock.release()
        # Inherited from mix-in...
        self.event_generate(event)
    def _generate_cov_event(self):
        # There is no need to synchronize the generation of 
        # the event itself.  Management of generator 
        # in-progress flag could be much cleaner.
        try:
            changes = self.changed_values()
            covevent = _ChangeValueEvent(changes)
        finally:
            self._generator_in_progress = 0
        return covevent
    def _empty(self):
        map(self._del_subscription_node_reference, self.snrmap.values())
    ##
    # @return The SubscriptionNodeReference instance mapped to the client
    #         spicific <code>nid</code>, if one exists.  Otherwise,
    #         <code>None</code>.
    def _get_subscription_node_reference(self, nid, default=None):
        return self.snrmap.get(nid, default)
    ##
    # Add a <code>SubscriptionNodeReference</code> to the client
    # specific <code>nid</code> map.
    # @param snr The <code>SubscriptionNodeReference</code> to add.
    def _add_subscription_node_reference(self, snr):
        if snr.nid() in self.snrmap:
            raise TypeError("NID %s already exists." % snr.nid())
        self.snrmap[snr.nid()] = snr
        self.untouched.add(snr)
        self._subscription_manager._add_subscription_node_reference(snr)
    ##
    # Delete a <code>SubscriptionNodeReference</code> to the client
    # specific <code>nid</code> map.
    # @param nid The key to the <code>SubscriptionNodeReference</code> to
    #            delete.
    def _del_subscription_node_reference(self, snr):
        self._subscription_manager._del_subscription_node_reference(snr)
        del(self.snrmap[snr.nid()])
        self.untouched.discard(snr)
    ##
    # Implements public merge(), assumes the nodes are locked.
    def _merge(self, node_reference_table):
        for nid,node in node_reference_table.items():
            snr = self._get_subscription_node_reference(nid)
            if snr:
                self._del_subscription_node_reference(snr)
            snr = SubscriptionNodeReference(self, nid, node)
            self._add_subscription_node_reference(snr)
    ##
    # Add an envent consumer for this subscription.
    def add_target(self, target):
        self.event_subscribe(target, _ChangeValueEvent)
        self._generate_change_events = 1
    def __repr__(self):
        return '<%s at %#x>' % (self, id(self))
    def __str__(self):
        return 'Subscription(%s)' % self.id()

class _ChangeValueEvent(Event): #this is a local event type.  do not use elsewhere.
    def __init__(self, results):
        Event.__init__(self)
        self.__results = results
        return
    def results(self):
        return self.__results
    def __str__(self):
        classname = 'mpx.service.subscription_manager._ChangeValueEvent'
        return "%s(%r)" % (classname, self.__results)
    def __repr__(self):
        return '<%s at %#x>' % (self, id(self))

class _MasterNodeBatch:
    def __init__(self, bm, master_node_table):
        self.__lock = SUBSCRIPTION_MANAGER._SubscriptionManager__lock
        self._master_node_table = master_node_table
        master_node_table[id(bm)] = self
        self._bm = bm
        self._batches = ()
        self._mnrs = {}
        self._added = set()
        self._changed = True
        self.slow_poll_threshold = (
            SUBSCRIPTION_MANAGER._get_tunable_parameters()[
                'slow_poll_threshold'
                ]
            )
        self.minimum_poll_interval =(
            SUBSCRIPTION_MANAGER._get_tunable_parameters()[
                'minimum_poll_interval'
                ]
            )
        self.prime_count = 0
        self.__reset_statistics()
        self._prime_triggered = 0
        return
    def __str__(self):
        return ("%s:\n"
                "    timestamp = %r\n"
                "    prime_count = %r\n"
                "    successful_gets = %r\n"
                "    failed_gets = %r\n"
                "    total_gets = %r\n"
                "    total_get_time = %r\n"
                "    last_get_time = %r\n"
                "    mnr_count = %r\n"
                "    batch_count = %r\n"
                ) % (
            "_MasterNodeBatch: %r" % self,
            now(),
            self.prime_count,
            self.successful_gets,
            self.failed_gets,
            self.total_gets,
            self.total_get_time,
            self.last_get_time,
            len(self._mnrs),
            len(self._batches)
            )
    def __repr__(self):
        return "%X" % id(self)
    def __reset_statistics(self):
        # Tuning statistics
        self.successful_gets = 0
        self.failed_gets = 0
        self.total_gets = 0
        self.total_get_time = 0.0
        self.last_get_time = 0.0
        self.last_get_delta = 0.0
        self.__refresh_enabled = 0 #produces side effect of short circuiting refresh
        return
    def add_mnr(self, mnr):
        prime = SUBSCRIPTION_MANAGER._SubscriptionManager__prime_pool
        self.__lock.acquire()
        try:
            self._mnrs[id(mnr)] = mnr
            self._added.add(id(mnr))
            self._changed = True
            mnr._mnb = self
            if len(self._mnrs) == 1:
                # Prime the pump.
                self.__refresh_enabled = 1
                prime.queue_noresult(self.prime)
        finally:
            self.__lock.release()
    def remove_mnr(self, mnr):
        self.__lock.acquire()
        try:
            # In theory discard() should never fail.
            self._added.discard(id(mnr))
            self._mnrs.pop(id(mnr))
        except KeyError:
            pass
        else:
            if hasattr(mnr, "_mnb"):
                delattr(mnr, "_mnb")
            if self._mnrs:
                self._changed = True
            else:
                self.__refresh_enabled = 0
                self._changed = False
                try:
                    self._master_node_table.pop(id(self._bm))
                except KeyError:
                    pass
        finally:
            self.__lock.release()
    def prime(self):
        self.prime_count += 1
        if debug: 
            print 'master batch prime: %s' % (self,)
        self.__lock.acquire()
        try:
            mnrs = dict([(mid, mnr._node) for mid,mnr in self._mnrs.items()])
            added = dict([(mid, mnrs[mid]) for mid in self._added])
            self._added.clear()
            self._changed = False
            self._prime_triggered = False
        finally:
            self.__lock.release()
        # get any new subscriptions and get their values ASAP
        try:
            if added and (len(added) < len(mnrs)): 
                # Make up batches for just the new points
                batches = self._bm.create_batches(added)
                for batch in batches:
                    # This is part of a local throttle 
                    # that we attach to the batch object
                    batch.__last_get_time = 0 
                    self.refresh(batch, 0) # flag that these batches do not refresh themselves
            self._batches = self._bm.create_batches(mnrs)
        except EBadBatch:
            msglog.exception()
            self.__reset_batch()
        except:
            msglog.exception()
            self.__abort_batch()
        else:
            for batch in self._batches:
                batch.__last_get_time = 0 #this is part of a local throttle that we attach to the batch object
                self.refresh(batch) #these batches run continuously until replaced
        #now that the new additions have been gotten once, proceed with the normal list of all points
        #create_batches for thousands of points can take a while.  That is why we get the new points first
    def refresh(self, batch, auto_refresh=1):
        prime = SUBSCRIPTION_MANAGER._SubscriptionManager__prime_pool
        self.__lock.acquire()
        try:
            if not self.__refresh_enabled:
                return #stop refreshing
            if auto_refresh and self._changed:
                # Reprocess the list of nodes to batch.
                if not self._prime_triggered: #only trigger once per group of mnr changes
                    self._prime_triggered = True
                    prime.queue_noresult(self.prime)
                return
        finally:
            self.__lock.release()
        if auto_refresh and (batch not in self._batches):
            if debug: 
                print 'expired batch on refresh: ', str(now()), str(id(batch)), str(len(batch.ids))
            return #do nothing, this batch is dead.
        # START HACK - Use scheduler, tunable minimum delay.
        #gaurantee the minimum poll interval between the end of the last result and the next request
        self.interval = uptime.secs() - batch.__last_get_time
        s = max(self.minimum_poll_interval - self.interval, 0.001)
        sleep(s)
        # END HACK
        if auto_refresh and (batch not in self._batches):
            if debug: 
                print 'expired batch after sleep: ', str(now()), str(s),  str(id(batch)), str(len(batch.ids))
            return #do nothing, this batch is dead.
        set_result = SubscriptionNodeReference.set_result
        set_exception = SubscriptionNodeReference.set_exception
        try:
            self.total_gets +=1
            set_result = SubscriptionNodeReference.set_result
            set_exception = SubscriptionNodeReference.set_exception
            start_get_time = uptime.secs()
## Callback object create here
            result_table = self._bm.get_batch(batch) #, \
                      # callback=Callback(self._distribute_results_callback, \
                                        # batch, \
                                        # set_result, \
                                        # set_exception))
            if isinstance(result_table, Exception):
                raise result_table
            if isinstance(result_table, Callback):
                return
            self.successful_gets +=1
## test for callback. make below into call back routine
## queue up next request in callback?
            t2 = uptime.secs()
            self.last_get_time = t2
            batch.__last_get_time = t2
            deltaT = t2 - start_get_time
            self.last_get_delta = deltaT
            self.total_get_time += deltaT
            # should we place these values on the mnrs too?
            for mnr_id,result in result_table.items():
                if self._mnrs.has_key(mnr_id):
                    mnr = self._mnrs[mnr_id]
                    mnr._try_batching = 2 #if we get a reply, don't give up right away if it does not work once.
                    if isinstance(result.value,Exception):
                        mnr._distribute_result(result.value, set_exception)
                    else:
                        mnr._distribute_result(result, set_result)
        except EBadBatch:
            msglog.exception()
            self.__reset_batch()
            return
        except:
            msglog.exception()
            self.__abort_batch()
            self.failed_gets += 1
            return

        if not auto_refresh: #do not retrigger batch
            return
        # @fixme:  What's up with use_slow_poll and the statistics?
        #use_slow_poll = 0
        #if use_slow_poll:
        if self.last_get_delta < self.slow_poll_threshold:
            (SUBSCRIPTION_MANAGER._SubscriptionManager__normal_pool.
             queue_noresult)(self.refresh, batch)
        else:
            (SUBSCRIPTION_MANAGER._SubscriptionManager__slow_pool.
             queue_noresult)(self.refresh, batch)
        return
    def _distribute_results_callback(self, result_table, batch, set_result, set_exception):
        #print '_distribute_results_callback: ', result_table
        try:
            if isinstance(result_table, Exception):
                raise result_table
            batch.__last_get_time = uptime.secs()
            for mnr_id,result in result_table.items():
                mnr = self._mnrs.get(mnr_id, None)
                if mnr:
                    mnr._try_batching = 2 #if we get a reply, don't give up right away if it does not work once.
                    if isinstance(result.value,Exception):
                        mnr._distribute_result(result.value, set_exception)
                    else:
                        mnr._distribute_result(result, set_result)
        except EBadBatch:
            msglog.exception()
            self.__reset_batch()
            return
        except:
            msglog.exception()
            self.__abort_batch()
            return
        if batch not in self._batches:
            if debug: print 'dead batch on callback: ', str(id(batch)), str(len(batch.ids))
            return #do nothing, this batch is dead.
        # @fixme:  What's up with use_slow_poll and the statistics?
        use_slow_poll = 0
        if use_slow_poll:
            (SUBSCRIPTION_MANAGER._SubscriptionManager__slow_pool.
             queue_noresult)(self.refresh, batch)
        else:
            (SUBSCRIPTION_MANAGER._SubscriptionManager__normal_pool.
             queue_noresult)(self.refresh, batch)
        return
    def __reset_batch(self):
        msglog.log("Subscription Manager", msglog.types.INFO,
                   "Reseting batch.")
        self.__lock.acquire()
        try:
            ## NOTE on NOTE:  Does this really apply to Batches?  I don't think so....
            # NOTE:  A side effect of resetting that statistics is that we
            #        avoid the minimum_poll_interval while processing
            #        EBadBatch exceptions.
            self.__reset_statistics()
            for mnr in self._mnrs.values():
                self.remove_mnr(mnr)
                mnr.reset_batching()
            self._batches = ()
        finally:
            self.__lock.release()
    def __abort_batch(self):
        msglog.log("Subscription Manager", msglog.types.INFO,
                   "Aborting batch.")
        self.__lock.acquire()
        try:
            for mnr in self._mnrs.values():
                self.remove_mnr(mnr)
                mnr.abort_batching()
            self._batches = ()
        finally:
            self.__lock.release()

##
# @note The constructor of this class, for_url, only instanciates a new object if there
#       is not a node_url keyed instance in the dictionary.
# @note It is assumed that access to the dictionary is managed by the invoker.
class _MasterNodeReference(EventConsumerMixin):
    def __init__(self, node_url, master_node_table):
        EventConsumerMixin.__init__(self)
        self.__lock = SUBSCRIPTION_MANAGER._SubscriptionManager__lock
        self.snrset = SubscriptionNodeReferenceSet()
        self._node_url = node_url
        self._get_result = self.__node_url_get_result
        self._master_node_table = master_node_table
        master_node_table[node_url] = self
        self._result = None
        self._try_batching = 2
        self._using_cov = 0
        self._node = None
        self.interval = 0 # how long between refresh calls
        self.__refresh_enabled = 0
        self.slow_poll_threshold = (
            SUBSCRIPTION_MANAGER._get_tunable_parameters()[
                'slow_poll_threshold'
                ]
            )
        self.minimum_poll_interval =(
            SUBSCRIPTION_MANAGER._get_tunable_parameters()[
                'minimum_poll_interval'
                ]
            )
        return
    def for_url(klass, master_node_table, node_url):
        if not master_node_table.has_key(node_url):
            mnr = klass(node_url, master_node_table)
        else:
            mnr = master_node_table[node_url]
        return mnr
    for_url = classmethod(for_url)

    def __create_statistics(self):
        # Tuning statistics
        self.successful_gets = 0
        self.failed_gets = 0
        self.total_gets = 0
        self.total_get_time = 0.0
        self.last_get_time = 0.0
        self.last_get_delta = 0.0
        return
    def __delete_statistics(self):
        if hasattr(self,'successful_gets'):
            delattr(self,'successful_gets')
        if hasattr(self,'failed_gets'):
            delattr(self,'failed_gets')
        if hasattr(self,'total_gets'):
            delattr(self,'total_gets')
        if hasattr(self,'total_get_time'):
            delattr(self,'total_get_time')
        if hasattr(self,'last_get_time'):
            delattr(self,'last_get_time')
        if hasattr(self,'last_get_delta'):
            delattr(self,'last_get_delta')
        return
    def add_snr(self, snr):
        if snr in self.snrset:
            raise TypeError("Subscription Node Reference "
                            "already in the Master Node Reference.")
        self.snrset.add(snr)
        if len(self.snrset) == 1:
            # Prime the pump.
            self.__refresh_enabled = 1
            self.prime()
        if self._result is not None:
            snr.set_result(self._result)
    def __untangle(self):
        self.__refresh_enabled = 0
        self.snrset = SubscriptionNodeReferenceSet()
        self._node_url = None
        self._get_result = None
        self._master_node_table = None
        self._result = None
        self._try_batching = 0
        if hasattr(self._node, 'changing_cov') and self._node.changing_cov():
           self._node.event_unsubscribe(self, ChangingCovEvent)
        _node = self._node
        _using_cov = self._using_cov
        self._node = None
        self._using_cov = 0
        if _using_cov:
            _node.event_unsubscribe(self, ChangeOfValueEvent)
        return
    def remove_snr(self, dictionary, snr):
        if snr not in self.snrset:
            raise TypeError("Subscription Node Reference is "
                            "not in the Master Node Reference.")
        self.snrset.remove(snr)
        if not self.snrset: #since we are no longer subscribed to, evaporate
            ## comment out the next two lines to return old values quickly
            del dictionary[self._node_url]
            self.__untangle()
            self.__refresh_enabled = 0
            if hasattr(self, '_mnb'):  # if we are part of a batch, remove us
                self._mnb.remove_mnr(self)
        return
    def abort_batching(self):
        if hasattr(self,'_mnb'):
            delattr(self,'_mnb')
        if self._try_batching:
            self._try_batching -= 1
            (SUBSCRIPTION_MANAGER.
             _SubscriptionManager__prime_pool.queue_noresult)(self.prime)
            return
        if hasattr(self._node, 'set_batch_manager'):
            self._node.set_batch_manager(None)
        msglog.log("Subscription Manager", msglog.types.INFO,
                   "Aborting batch: %s" % (self._node.as_node_url(),))
        return
    def reset_batching(self):
        if hasattr(self,'_mnb'):
            delattr(self,'_mnb')
        SUBSCRIPTION_MANAGER._SubscriptionManager__prime_pool.queue_noresult(
            self.prime
            )
        return
    def prime(self):
        if not self.__refresh_enabled:
            return #stop refreshing
        error = None
        try:
            self.get_node_reference()
        except Exception, e:
            error = e
            _exception_string(e)
        except:
            error = Exception(sys.exc_info()[0])
            _exception_string(error)
        if error is None:
            #
            # Looks like a valid node reference.  Find the most effecient
            # mechanism to fetch it's value.
            #
            #
            # If the COV capability of the node can change on the fly, subscribe
            # to those changes. 
            if hasattr(self._node, 'changing_cov') and self._node.changing_cov():
                    self._node.event_subscribe(self, ChangingCovEvent)
            try:
                #
                # If the node supports COV, let it do all the work.
                #
                if hasattr(self._node, 'has_cov') and self._node.has_cov():
                    self._node.event_subscribe(self, ChangeOfValueEvent)
                    self._using_cov = 1
                    self._get_result = self.__get_cov_result
                    if hasattr(self._node, 'changing_cov') and \
                        self._node.changing_cov():
                        # The node is already in COV mode here,
                        # be sure to get the current stored value
                        # from the hosting module (eg: BACnet), ie 
                        # an initial value, while waiting for any
                        # COV notifications happening in the furture. 
                        self._result = self._node.get_result()
                    return
            except:
                msglog.exception()
            try:
                #
                # If the node participates in batching, then that is the
                # second best option.
                #
                if self._try_batching:
                    bm = self._node.get_batch_manager()
                    if bm is not None:
                        bm_id = id(bm)
                        self.__lock.acquire()
                        try:
                            if self._master_node_table.has_key(bm_id):
                                mnb = self._master_node_table[bm_id]
                            else:
                                mnb = _MasterNodeBatch(bm,
                                                       self._master_node_table)
                            mnb.add_mnr(self)
                        finally:
                            self.__lock.release()
                        return
            except:
                pass
            #
            # Neither COV nor batching are supported (or failed).  Call
            # self.refresh() to start polling the individual point.
            #
            self.__create_statistics()
            return self.refresh()
        #
        # Could not get a valid node reference.  Report the error and try again
        # later.
        #
        if self._master_node_table._manager.debug > 2:
            if isinstance(error, Exception):
                self.debug_message("%r %r %r",
                                   now(), self._node_url,
                                   _exception_string(error),
                                   level=2)
            else:
                self.debug_message('%r %r %r', now(), self._node_url, error,
                                   level=2)
        self._distribute_result(error,
                                SubscriptionNodeReference.set_exception)
        self.reprime()
    def reprime(self):
        if not self.__refresh_enabled:
            return #stop refreshing
        scheduler.after(5.0, self.queue_reprime)
    def queue_reprime(self):
        if self._node is not None and self._using_cov:
            try:
                self._node.event_unsubscribe(self, ChangeOfValueEvent)
            except: 
                msglog.exception()
        self._node = None
        self._using_cov = 0
        self._get_result = self.__node_url_get_result
        SUBSCRIPTION_MANAGER._SubscriptionManager__prime_pool.queue_noresult(
            self.prime
            )
        return
    def queue_refresh(self):
        if self.last_get_delta < self.slow_poll_threshold:
            pool = SUBSCRIPTION_MANAGER._SubscriptionManager__normal_pool
        else:
            pool = SUBSCRIPTION_MANAGER._SubscriptionManager__slow_pool
        pool.queue_noresult(self.refresh)
    def schedule_refresh(self, delay):
        scheduler.after(delay, self.queue_refresh)
    def refresh(self):
        if not self.__refresh_enabled:
            return #stop refreshing
        # START HACK - Use scheduler, tunable minimum delay.
        self.interval = uptime.secs() - self.last_get_time
        s = max(self.minimum_poll_interval - self.interval, 0.001)
        sleep(s)
        # END HACK
        set_result = SubscriptionNodeReference.set_result
        try:
            t1 = uptime.secs()
            result = self._get_result(1) # skipCache=1
            self.successful_gets += 1
        except Exception, e:
            self.failed_gets += 1
            set_result = SubscriptionNodeReference.set_exception
            result = e
        except:
            self.failed_gets += 1
            set_result = SubscriptionNodeReference.set_exception
            e = Exception(sys.exc_info()[0])
            result = e            
        t2 = uptime.secs()
        deltaT = t2 - t1
        self.total_gets += 1
        self.total_get_time += deltaT
        self.last_get_delta = deltaT
        self.last_get_time = t2 #used a throttle as well as statistics
    
        try:            
            # Start Debug 
            if (self._master_node_table and
                self._master_node_table._manager.debug > 2):
                if isinstance(result, Exception):
                    self.debug_message("%r %r %r",
                                       now(), self._node_url,
                                       _exception_string(result),
                                       level=2)
                elif hasattr(result,'value'):
                    self.debug_message('%r %r %r',
                                       now(), self._node_url,
                                       Result.as_dict(result),
                                       level=2)
                else:
                    self.debug_message('%r %r %r', now(), self._node_url,
                                       result, level=2)
            # End Debug
        except Exception,err:
            print 'Debug error:%s' % (err,)
        self._distribute_result(result, set_result)
        self.queue_refresh()
    def _distribute_result(self, result, set_result):
        snrs = self.snrset.copy()
        while snrs:
            try:
                while snrs:
                    snr = snrs.pop()
                    set_result(snr, result)
            except Exception, error:
                self.debug_message(_exception_string(error), level=1)
                msglog.exception()
        # For subscriber's that join between update's
        if not hasattr(result, "value"):
            result = Result(result, now(), 0)
        self._result = result
    def debug_message(self, fmt, *args, **kw):
        return self._master_node_table.debug_message(fmt, *args, **kw)
    def debug_message_kw(self, fmt, level=1, **kw):
        return self._master_node_table.debug_message_kw(fmt, level, **kw)
    def get_node_reference(self):
        if self._node is None:
            self._node = as_internal_node(self._node_url)
            if IAliasNode.providedBy(self._node):
                msglog.warn("MNR references Alias type: %r" % self._node_url)
                self._node = self._node.dereference(True)
        return self._node
    def __node_url_get_result(self, skipCache=0, **keywords):        
        self._get_result = self.__node_try_get_result
        result = self._get_result(**keywords)
        return result
    def __node_try_get_result(self, skipCache=0, **keywords):
        try:
            result = self.__node_get_result(**keywords)
            self._get_result = self.__node_get_result
        except AttributeError, NotImplementedError:
            self._get_result = self.__node_try_get
            result = self._get_result(**keywords)
        return result
    def __node_get_result(self, skipCache=0, **keywords):
        result = self._node.get_result(skipCache,**keywords)
        self._get_result = self._node.get_result
        return result
    def __node_try_get(self, skipCache=0, **keywords):
        result = self.__node_get(skipCache)
        self._get_result = self.__node_get
        return result
    def __node_get(self, skipCache=0, **keywords):
        result = Result(self._node.get(skipCache), now())
        return result
    def __get_cov_result(self, skipCache=0, **keywords):
        return self._result
    ##
    # Called when node generates events.
    # @fixme Add event to a SequentalProcessQueue
    def event_handler(self, event):
        if isinstance(event, ChangeOfValueEvent):
            if self.__refresh_enabled and event.source == self._node:
                # @fixme When there is a process queue, then queue each
                #        event in order.  Until then order is not ensured...
                result = event.as_result()
                self._result = result
                thread_pool.HIGH.queue_noresult(self.__event_handler)
                # @fixme Add a seperate Event for when the Node is changed
                # or pruned rather than examining each value.
                if isinstance(result.value, ENoSuchNode):
                    self.reprime()
        elif isinstance(event, ChangingCovEvent):
            if event.source == self._node:
                # @fixme When there is a process queue, then queue each
                # event in order.  Until then order is not ensured...
                #
                # Note that priming of mnr in processing below happens
                # in a thread from subscription manager pool. 
                if event.value == 2: # ENonCoVNode transition
                    # If the event indicates that the node changed
                    # from COV mode to non-COV mode, see if the
                    # mnr needs to be added back to its batch.
                    self.reprime()
                elif event.value == 1: # ECovNode transition
                    # If the event indicates that the node changed
                    # from non-COV mode to COV-mode, turn of batching,
                    # if any, and mark the node for COV handling.
                    if hasattr(self, '_mnb'):
                        self._mnb.remove_mnr(self)
                    self.reset_batching()
                else:
                     pass

    ##
    # disperse change event to all snrs that look to this master
    # @fixme Convert to action on a SequentalProcessQueue which will
    #        set self._result and then preform set_results...
    def __event_handler(self):
        result = self._result # get the current value
        if result is None or not self.__refresh_enabled:
            # MNR refresh disabled prior to getting scheduled.
            # @fixme Stiil a small window and probably cleaner locking
            #        could be devised...
            return
        snrs = self.snrset.copy()
        while snrs:
            try:
                while snrs:
                    snr = snrs.pop()
                    snr.set_result(self._result)
            except Exception, error:
                self.debug_message(_exception_string(error), level=1)
                msglog.exception()
    def __str__(self):
        if self._node:
            return ("%s:\n"
                    "    successful_gets = %r\n"
                    "    failed_gets = %r\n"
                    "    total_gets = %r\n"
                    "    total_get_time = %r\n"
                    "    last_get_time = %r\n"
                    ) % (
                str(self._node),
                self.successful_gets,
                self.failed_gets,
                self.total_gets,
                self.total_get_time,
                self.last_get_time,
                )
        return 'a MasterNodeReference'
##
# A SubscriptionManager's list of subscriptions, keyed by the subscription'
# ID.
class SubscriptionDict(dict):
    pass

##
# Union of all node objects referenced by any subscription.
class _MasterNodeTableDict(dict):
    def __init__(self, manager, *args):
        self._manager = manager
        super(_MasterNodeTableDict, self).__init__(*args)
    def debug_message(self, fmt, *args, **kw):
        return self._manager.debug_message(fmt, *args, **kw)
    def debug_message_kw(self, fmt, level=1, **kw):
        return self._manager.debug_message_kw(fmt, level, **kw)

class _TunableParameters(dict):
    pass

_DEBUG_DEFAULT=0

class SubscriptionManager(ServiceNode):
    ##
    #
    def __init__(self):
        self.__subscriptions = SubscriptionDict()
        self.__lock = RLock()
        self.__start_count = 0
        self.__stop_count = 0
        self.__untuned_result = None
        self.__slow_result = None
        # Some thread scheduler's thrash with a "spinning" thread pool.
        self.__minimum_poll_delay = 0.001
        self.__evil_tuning = _TunableParameters({
            'slow_poll_threshold':0.500,
            'normal_pool_size':1,
            'slow_pool_size':1,
            'prime_pool_size':1,
            'minimum_poll_interval':2.7,
            })
        self.__normal_pool = thread_pool.ThreadPool(
            self.__evil_tuning['normal_pool_size'],
            name='SubscriptionManager-NORMAL'
            )
        self.__slow_pool = thread_pool.ThreadPool(
            self.__evil_tuning['slow_pool_size'],
            name='SubscriptionManager-SLOW'
            )
        self.__prime_pool = thread_pool.ThreadPool(
            self.__evil_tuning['prime_pool_size'],
            name='SubscriptionManager-PRIME'
            )
        self._pdo = None # for storing tunable parameters
        ##
        # Union of all node objects referenced by any subscription.
        self.__master_node_table = _MasterNodeTableDict(self)
        ServiceNode.__init__(self)
        return
    def start(self):
        self.__lock.acquire()
        try:
            if self.__start_count > self.__stop_count:
                return
            ServiceNode.start(self)
            cd = self.get_tunable_parameters_pdo()
            if cd.has_key('normal_pool_size'):
                self._set_tunable_parameters(
                    {'normal_pool_size':int(cd['normal_pool_size'])}
                    )
            if cd.has_key('slow_pool_size'):
                self._set_tunable_parameters(
                    {'slow_pool_size':int(cd['slow_pool_size'])}
                    )
            if cd.has_key('prime_pool_size'):
                self._set_tunable_parameters(
                    {'prime_pool_size':int(cd['prime_pool_size'])}
                    )
            if cd.has_key('minimum_poll_interval'):
                self._set_tunable_parameters(
                    {'minimum_poll_interval':float(cd['minimum_poll_interval'])}
                    )
            if cd.has_key('slow_poll_threshold'):
                self._set_tunable_parameters(
                    {'slow_poll_threshold':float(cd['slow_poll_threshold'])}
                    )
            self.__normal_pool.resize(
                self._get_tunable_parameters()['normal_pool_size']
                )
            self.__slow_pool.resize(
                self._get_tunable_parameters()['slow_pool_size']
                )
            self.__prime_pool.resize(
                self._get_tunable_parameters()['prime_pool_size']
                )
            self.__start_count += 1
        finally:
             self.__lock.release()
        return
    def configure(self, cd):
        set_attribute(self, 'enabled', 1, cd, int)
        set_attribute(self, 'debug', _DEBUG_DEFAULT, cd, int)
        if cd.has_key('_normal_pool_size'):
            self._set_tunable_parameters(
                {'normal_pool_size':int(cd['_normal_pool_size'])}
                )
        if cd.has_key('_slow_pool_size'):
            self._set_tunable_parameters(
                {'slow_pool_size':int(cd['_slow_pool_size'])}
                )
        if cd.has_key('_prime_pool_size'):
            self._set_tunable_parameters(
                {'prime_pool_size':int(cd['_prime_pool_size'])}
                )
        if cd.has_key('_minimum_poll_interval'):
            self._set_tunable_parameters(
                {'minimum_poll_interval':float(cd['_minimum_poll_interval'])}
                )
        if cd.has_key('_slow_poll_threshold'):
            self._set_tunable_parameters(
                {'slow_poll_threshold':float(cd['_slow_poll_threshold'])}
                )
        ServiceNode.configure(self, cd)
        return
    def configuration(self, config=None):
        config = ServiceNode.configuration(self, config)
        get_attribute(self, 'enabled', config, str)
        get_attribute(self, 'debug', config, str)
        tp = self._get_tunable_parameters()
        config['_slow_poll_threshold'] = tp['slow_poll_threshold']
        config['_normal_pool_size'] = tp['normal_pool_size']
        config['_slow_pool_size'] = tp['slow_pool_size']
        config['_prime_pool_size'] = tp['prime_pool_size']
        config['_minimum_poll_interval'] = tp['minimum_poll_interval']
        return config
    def get_tunable_parameters_pdo(self): #call while locked
        if self._pdo is None:
            self._pdo = PersistentDataObject(self, dmtype=GC_NEVER)
            self._pdo.tunable_parameters = _TunableParameters()
            self._pdo.load()
        return self._pdo.tunable_parameters
    def save_tunable_parameters_pdo(self):
        self.__lock.acquire()
        try:
            self.get_tunable_parameters_pdo() # init pdo
            params = self._get_tunable_parameters()
            self._pdo.tunable_parameters = params
            self._pdo.save()
            msglog.log('SubcriptionManager', 'saved SM tunable parameters', str(params))
        finally:
            self.__lock.release()
    def _debug_message(self, fmt, *args):
        try:
            print fmt % args
        except:
            print "debug_message(%r,*%r)" % (fmt,args)
        return
    def debug_message(self, fmt, *args, **kw):
        if kw.has_key('level'):
            level = kw['level']
        else:
            level = 1
        if self.debug >= level:
            self._debug_message(fmt, *args)
        return
    def _debug_message_kw(self, fmt, **args):
        try:
            print fmt % args
        except:
            print "_debug_message(%r,**%r)" % (fmt,args)
        return
    def debug_message_kw(self, fmt, level=1, **kw):
        if self.debug >= level:
            self._debug_message_kw(fmt, **kw)
        return
    def stop(self):
        ServiceNode.stop(self)
        self.__normal_pool._unload()
        self.__slow_pool._unload()
        self.__prime_pool._unload()
        wait_for_results = 0
        self.__lock.acquire()
        try:
            wait_for_results = self.__stop_count != self.__start_count
            self.__stop_count = self.__start_count
            untuned_result = self.__untuned_result
            slow_result = self.__slow_result
        finally:
            self.__lock.release()
        if wait_for_results:
            if untuned_result is not None:
                result = untuned_result.result(60.0)
                if result is thread_pool.NORESULT:
                    sys.stderr.flush()
                    sys.stdout.flush()
                    warnings.warn(
                        "Failed to get untuned_result after %r seconds."
                        "  untuned_result:\n%s" % (60.0,
                                                   untuned_result)
                        )
            if slow_result is not None:
                result is slow_result.result(60.0)
                if result is thread_pool.NORESULT:
                    sys.stderr.flush()
                    sys.stdout.flush()
                    warnings.warn("Failed to get slow_result after %r seconds."
                                  "slow_result:\n%s" % (60.0,
                                                        slow_result))
        return
    ##
    # Create a new subscription where the caller intends to poll for the
    # values.
    #
    # @param node_reference_table An optional dictionary of node references
    #                             keyed by NIDs (the client specific, node
    #                             identifier) used as the initial
    #                             subscription.
    # @timeout An optional timeout specified in seconds.  If the subscription
    #          is not polled within TIMEOUT seconds, then the subscription
    #          will be destroyed.
    # @return The SID (subscription identification) used to uniquely identify
    #         the subscription.
    def create_polled(self, node_reference_table={}, timeout=1800, sid=None):
        nodetable = NodeReferenceTable(node_reference_table)
        if debug: 
            print 'SM: create_polled: begin %s %s' % (now(), nodetable)
        subscription = Subscription(self, timeout, sid)
        sid = self.add_subscription(subscription)
        subscription = self.get_subscription(sid)
        self.__lock.acquire()
        try:
            subscription.merge(nodetable)
        finally:
            self.__lock.release()
        if debug: 
            print 'SM: create_polled: end %s %s' % (now(), sid)
        return sid
    
    ##
    # Create a new subscription where the caller intends to poll for the
    # values and return both with the SID and initial values and ONLY return
    # the value
    #
    # @param node_reference_table An optional dictionary of node references
    #                             keyed by NIDs (the client specific, node
    #                             identifier) used as the initial
    #                             subscription.
    # @return A dictionary with the following keys:
    #         sid - The SID (subscription identification) used to uniquely
    #         identify the subscription.
    #         values - Initial values.
    def create_polled_and_get_values(self, node_reference_table={}, 
                                     timeout=1800, maxwait=60, sid=None):
        if debug: 
            print 'SM: create_polled_and_get_values: begin %s %s' % (now(), node_reference_table)
        results = self.create_polled_and_get(
            node_reference_table, timeout, maxwait, sid)
        new_results = {}
        for k,v in results['values'].items():
            new_results[k] = v['value']
        results['values']  = new_results
        if debug: 
            print 'SM: create_polled_and_get_values: end %s' % now()
        return results
    ##
    # Create a new subscription where the caller intends to poll for the
    # values and return both with the SID and initial values.
    #
    # @param node_reference_table An optional dictionary of node references
    #                             keyed by NIDs (the client specific, node
    #                             identifier) used as the initial
    #                             subscription.
    # @return A dictionary with the following keys:
    #         sid - The SID (subscription identification) used to uniquely
    #         identify the subscription.
    #         values - Initial values.
    def create_polled_and_get(self, node_reference_table={}, 
                              timeout=1800, maxwait=60, sid=None):
        if debug: 
            print 'SM: create_polled_and_get: start %s %s' % (now(), node_reference_table)
        sid = self.create_polled(node_reference_table, timeout, sid)
        subscription = self.get_subscription(sid)
        complete = subscription.await_priming(maxwait)
        results = subscription.all_values()
        if not complete:
            # Only filter Nones if results incomplete.
            results = dict([(nid, value) for nid,value in 
                            results.items() if value is not None])
        if debug: 
            print 'SM: create_polled_and_get: end %s' % now()
        return {'sid': sid, 'values': results}
    ##
    # @param target The event consumer that will accept notifications.
    # @param node_reference_table An optional dictionary of node references
    #                             keyed by NIDs (the client specific, node
    #                             identifier) used as the initial
    #                             subscription.
    # @return The SID (subscription identification) used to uniquely identify
    #         the subscription.
    def create_delivered(self, target, node_reference_table={}, sid=None):
        if debug: 
            print 'SM: create_delivered: start', str(now()), str(node_reference_table)
        node_reference_table = NodeReferenceTable(node_reference_table)
        subscription = Subscription(self, None, sid)
        sid = self.add_subscription(subscription)
        subscription = self.get_subscription(sid)
        self.__lock.acquire()
        try:
            subscription.add_target(target)
            subscription.merge(node_reference_table)
        finally:
            self.__lock.release()
        if debug: 
            print 'SM: create_delivered: end', str(now()),str(sid)
        return sid
    ##
    # Destroy an existing subscription.
    # @param sid The subscription id returned by <code>new_subscription</code>.
    def destroy(self, sid):
        if debug: 
            print 'SM: destroy: begin', str(now()),str(sid)
        self.__lock.acquire()
        try:
            if not self.__get_subscription(sid):
                if debug:
                    raise ENoSuchSubscription(sid)
                return #this is to stop the message log from filling with exception messages for timeed out subscriptions
            self.__del_subscription(sid)
        finally:
            self.__lock.release()
        if debug: 
            print 'SM: destroy: end', str(now()),str(sid)
        return
    ##
    # @param sid The subscription id returned by <code>new_subscription</code>.
    # @return A dictionary of node references keyed by NIDs (the client
    #         specific, node identifier).
    def node_reference_table(self, sid):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            node_reference_table = subscription.node_reference_table()
        finally:
            self.__lock.release()
        return node_reference_table
    ##
    # Add new node references and replace existing node references from a
    # dictionary.
    #
    # @param sid The subscription id returned by <code>new_subscription</code>.
    # @param node_reference_table A dictionary of node references keyed by
    #                             NIDs (the client specific, node identifier).
    def merge(self, sid, node_reference_table):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            subscription.merge(node_reference_table)
        finally:
            self.__lock.release()
        return
    ##
    # Completely replace a subscription's node reference table.
    #
    # @param sid The subscription id returned by <code>new_subscription</code>.
    # @param node_reference_table A dictionary of node references keyed by
    #                             NIDs (the client specific, node identifier).
    def replace(self, sid, node_reference_table):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            subscription.replace(node_reference_table)
        finally:
            self.__lock.release()
        return
    ##
    # Remove all entries from a subscription's node reference table.
    #
    # @param sid The subscription id returned by <code>new_subscription</code>.
    def empty(self, sid):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            subscription.empty()
        finally:
            self.__lock.release()
        return
    ##
    # Add a new entry to the subscription's node reference table.
    #
    # @param sid The subscription id returned by <code>new_subscription</code>.
    # @param nid The Node ID that will identify the new node reference.
    # @param node_reference A Node Reference for the Node to add to the
    #                       subscription's  node reference table.
    def add(self, sid, nid, node_reference):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            subscription.add(nid, node_reference)
        finally:
            self.__lock.release()
        return
    ##
    # Modify an existing entry in the subscription's node reference table.
    #
    # @param sid The subscription id returned by <code>new_subscription</code>.
    # @param nid The Node ID that will identify the new node reference.
    # @param node_reference A Node Reference for the Node to add to the
    #                       subscription's  node reference table.
    def modify(self, sid, nid, node_reference):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            subscription.modify(nid, node_reference)
        finally:
            self.__lock.release()
        return
    ##
    # Remove a specific node reference from a subscription's node reference
    # table.
    #
    # @param sid The subscription id returned by <code>new_subscription</code>.
    # @param nid The Node ID used that identifies the specific node reference
    #            to remove.
    def remove(self, sid, nid):
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            subscription.remove(nid)
        finally:
            self.__lock.release()
        return
    ##
    # Poll the subscription service for all subscribed Node's whose values have
    # changed since the last time <code>poll_changed</code> was invoked or
    # since the subscription was created, which ever is more recent.
    #
    # @param sid The id of the subscription to poll for changes.  This is the
    #            'handle' that was returned by create_polled.
    # @return A dictionary, keyed by the Node ID of the changed values "result
    #         dictionary".  The "result dictionary" dictionary has three
    #         keys: "value", "timestamp" and "cached".  The "value" key returns
    #         the actual value read from the Node, or the exception that
    #         prevented reading a value.  The "timestamp" key returns that best
    #         estimate as to when the value was read, as a float of seconds
    #         since 1970, UTC.  And "cached" is a boolean that is false if it
    #         is guaranteed that the value was not returned from a cache.
    def poll_changed(self, sid):
        if debug: 
            print 'SM: poll_changed: begin', str(now()),str(sid)
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            if subscription is None:
                raise ENotFound('subscription manager', sid, 'not found')
        finally:
            self.__lock.release()
        results = subscription.changed_values()
        if debug: 
            print 'SM:poll_changed:end %s %s %d' % (now(), sid, len(results))
        return results
    ##
    # Poll the subscription service for all subscribed Node's whose values have
    # changed since the last time <code>poll_changed_values</code> was invoked
    # or since the subscription was created, which ever is more recent.
    #
    # @param sid The id of the subscription to poll for changes.  This is the
    #            'handle' that was returned by create_polled.
    # @return A dictionary, keyed by the Node ID of the changed values "result
    #         dictionary".  The "result dictionary" dictionary has three
    #         keys: "value", "timestamp" and "cached".  The "value" key returns
    #         the actual value read from the Node, or the exception that
    #         prevented reading a value.  The "timestamp" key returns that best
    #         estimate as to when the value was read, as a float of seconds
    #         since 1970, UTC.  And "cached" is a boolean that is false if it
    #         is guaranteed that the value was not returned from a cache.
    def poll_changed_values(self, sid):
        if debug: 
            print 'SM: poll_changed_values: begin', str(now()),str(sid)
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            if subscription is None:
                raise ENotFound('subscription manager', sid, 'not found')
        finally:
            self.__lock.release()
        results = subscription.changed_values()
        newresults = dict([(k, v['value']) for k,v in results.items()])
        if debug: 
            print 'SM: poll_changed_values: end %s %s %d' % (now(), sid, 
                                                             len(newresults))
        return newresults
    ##
    # Poll the subscription service for all subscribed Node's.
    #
    # @param sid The id of the subscription to poll for changes.  This is the
    #            'handle' that was returned by create_polled.
    # @return A dictionary, keyed by the Node ID of the Node's "result
    #         dictionary".  The "result dictionary" dictionary has three
    #         keys: "value", "timestamp" and "cached".  The "value" key returns
    #         the actual value read from the Node, or the exception that
    #         prevented reading a value.  The "timestamp" key returns that best
    #         estimate as to when the value was read, as a float of seconds
    #         since 1970, UTC.  And "cached" is a boolean that is false if it
    #         is guaranteed that the value was not returned from a cache.
    #         If the subscription service has not received an initial value for
    #         the node, then None is returned for that Node instead of a
    #         "result dictionary."
    def poll_all(self, sid):
        if debug: print 'SM: poll_all: ', str(now()),str(sid)
        self.__lock.acquire()
        try:
            subscription = self.__get_subscription(sid)
            if subscription is None:
                raise ENotFound('subscription manager', sid, 'not found')
        finally:
            self.__lock.release()
        return subscription.all_values()
    def get_subscription(self, sid):
        self.__lock.acquire()
        try:
            subscription = self.__subscriptions.get(sid)
        finally:
            self.__lock.release()
        return subscription
    def add_subscription(self, subscription):
        self.__lock.acquire()
        try:
            sid = subscription.id()
            if sid in self.__subscriptions:
                raise TypeError("SID %s already exists" % sid)
            self.__subscriptions[sid] = subscription
        finally:
            self.__lock.release()
        return sid    
    def _master_node_table(self):
        return self.__master_node_table
    def _get_tunable_parameters(self):
        return _TunableParameters(self.__evil_tuning)
    def _set_tunable_parameters(self, parameters):
        self.__evil_tuning.update(parameters)
    def __get_subscription(self, sid):
        return self.__subscriptions.get(sid)
    def __add_subscription(self, subscription):
        self.__lock.acquire()
        try:
            sid = subscription.id()
            assert not self.__subscriptions.has_key(sid), (
                'SID %s already exist.' % (sid,))
            self.__subscriptions[sid] = subscription
        finally:
            self.__lock.release()
        return sid
    def __del_subscription(self, sid):
        self.__lock.acquire()
        try:
            assert self.__subscriptions.has_key(sid), (
                'No such SID %s.' % (sid,))
            subscription = self.__subscriptions[sid]
            subscription.empty()
            del self.__subscriptions[sid]
        finally:
            self.__lock.release()
        return sid
    def _add_subscription_node_reference(self, snr):
        snr.initiate_registration(self.__master_node_table)
    def _del_subscription_node_reference(self, snr):
        snr.cancel_registration(self.__master_node_table)
    ##
    # Hook for the ReloadableSingletonFactory.
    def singleton_unload_hook(self):
        self.stop()
    #
    #
    #
    def diag_get_sids(self):
        self.__lock.acquire()
        try:
            result = self.__subscriptions.keys()
        finally:
            self.__lock.release()
        return result
    def diag_get_subscriptions(self):
        self.__lock.acquire()
        try:
            result = self.__subscriptions.values()
        finally:
            self.__lock.release()
        return result
    def diag_dup_master_node_table(self):
        self.__lock.acquire()
        try:
            result = {}
            result.update(self.__master_node_table)
        finally:
            self.__lock.release()
        return result
    def diag_get_mnrs(self):
        self.__lock.acquire()
        try:
            dup = {}
            dup.update(self.__master_node_table)
        finally:
            self.__lock.release()
        result = []
        for master in dup.values():
            if isinstance(master,_MasterNodeReference):
                result.append(master)
        return result
    def diag_get_mnbs(self):
        self.__lock.acquire()
        try:
            dup = {}
            dup.update(self.__master_node_table)
        finally:
            self.__lock.release()
        result = []
        for master in dup.values():
            if isinstance(master,_MasterNodeBatch):
                result.append(master)
        return result
    def nodebrowser_handler(self, nb, path, node, node_url):
        mnrs = self.diag_get_mnrs()
        block = [nb.get_default_view(node, node_url)]
        block.append('<div class="node-section node-statistics">')
        block.append('<h2 class="section-name">Statistics</h2>')
        block.append('<ul>')
        block.append('<li>Number of SIDs: %s</li>' % len(self.diag_get_sids()))
        block.append('<li>Number of MNRs: %s</li>' % len(mnrs))
        block.append('<li>Number of MNBs: %s</li>' % len(self.diag_get_mnbs()))
        block.append('<li>Normal Queue:   %s</li>' % len(self.__normal_pool._ThreadPool__queue._q))
        block.append('<li>Slow Queue:     %s</li>' % len(self.__slow_pool._ThreadPool__queue._q))
        block.append('<li>Prime Queue:    %s</li>' % len(self.__prime_pool._ThreadPool__queue._q))
        block.append('<li>MNRs Using COV: %s</li>' % len([v for v in mnrs if v._using_cov]))
        block.append('<li>SNRs Using COV: %s</li>' % len([s for s in self.diag_get_subscriptions() if s._generate_change_events]))
        block.append('</ul>')
        # make table of 5 slowest points
        block.append('<h2 class="section-name">Slowest MNRs</h2>')
        block.append('<table border="1">')
        block.append('<tr><th>URL</th><th>Seconds</th></tr>')
        deltas = [(m.last_get_delta, m._node_url) for m in mnrs if hasattr(m,'last_get_delta')]
        deltas.sort()
        deltas.reverse()
        deltas = deltas[:5]
        for d in deltas:
            block.append('<tr><td>%s</td><td>%s</td></tr>' % (d[1],d[0]))
        block.append('</table>')
        # make table of 5 slowest batches
        block.append('<h2 class="section-name">Slowest MNBs</h2>')
        block.append('<table border="1">')
        block.append('<tr><th>URL</th><th>Seconds</th></tr>')
        deltas = [(m.last_get_delta, id(m._bm)) for m in self.diag_get_mnbs() if hasattr(m,'last_get_delta')]
        deltas.sort()
        deltas.reverse()
        deltas = deltas[:5]
        for d in deltas:
            block.append('<tr><td>%s</td><td>%s</td></tr>' % (d[1],d[0]))
        block.append('</table>')
        # make table of 5 largest SNRs
        block.append('<h2 class="section-name">Largest Subscriptions</h2>')
        block.append('<table border="1">')
        block.append('<tr><th>ID</th><th>Size</th></tr>')
        sizes = [(len(s.snrmap), s._id) for s in self.diag_get_subscriptions()]
        sizes.sort()
        sizes.reverse()
        sizes = sizes[:5]
        for s in sizes:
            block.append('<tr><td>%s</td><td>%s</td></tr>' % (s[1],s[0]))
        block.append('</table>')
        if self.debug: # mask the ability to change the tunable parameters except in debug mode
            # Allow adjustments to tuning parameters
            tp = self._get_tunable_parameters()
            block.append('<h2 class="section-name">Adjust Thread Pool sizes and Timing Thresholds</h2>')
            block.append('''
<form name="input" action="Subscription%%20Manager?action=invoke&method=form_submit&parameters=1" method="post">
<table>
<tr><td>Prime pool size:</td><td><input type="text" name="prime_pool_size" value="%s"/></td></tr>
<tr><td>Normal pool size:</td><td><input type="text" name="normal_pool_size" value="%s" /></td></tr>
<tr><td>Slow pool size:</td><td><input type="text" name="slow_pool_size" value="%s" /></td></tr>
<tr><td>Slow pool threshold:</td><td><input type="text" name="slow_poll_threshold" value="%s" /></td></tr>
<tr><td>Minimum Poll Interval:</td><td><input type="text" name="minimum_poll_interval" value="%s" /></td></tr>
</table>
<input type="submit" value="Submit" />
</form> 
''' % (tp['prime_pool_size'], tp['normal_pool_size'], tp['slow_pool_size'], tp['slow_poll_threshold'], tp['minimum_poll_interval']))
        block.append("</div>")
        return "\n".join(block)

    def form_submit(self, *args, **parameters):
        tp = self._get_tunable_parameters()
        pps = self._form_eval('prime_pool_size', 1, 32, tp, parameters)
        nps = self._form_eval('normal_pool_size', 1, 4, tp, parameters)
        sps = self._form_eval('slow_pool_size', 1, 16, tp, parameters)
        spt = self._form_eval('slow_poll_threshold', 0.005, 2.0, tp, parameters)
        mpi = self._form_eval('minimum_poll_interval', 0.5, 30.0, tp, parameters)
        if pps or nps or sps or spt or mpi:
            self._set_tunable_parameters(tp)
            self.save_tunable_parameters_pdo()
            if spt: # update existing mnrs
                for mnr in self.diag_get_mnrs() + self.diag_get_mnbs():
                    mnr.slow_poll_threshold = spt
            if mpi: # update minimum poll interval
                for mnr in self.diag_get_mnrs() + self.diag_get_mnbs():
                    mnr.minimum_poll_interval = mpi
        return '''
<meta http-equiv="REFRESH" content="2;url=%s">
Saving parameters
''' % ('/nodebrowser' + self.as_node_url(),)

    def _form_eval(self, key, _min, _max, tp, parameters):
        value = parameters.get(key, tp.get(key, None))
        if value:
            if isinstance(_min, int):
                value = int(value)
            else:
                value = float(value)
            value = min(max(value, _min), _max)
            if tp[key] != value:
                tp[key] = value
                return value
        return None

SUBSCRIPTION_MANAGER = ReloadableSingletonFactory(SubscriptionManager)
#from mpx.service.subscription_manager import _manager as smm
#smm.debug=1
#from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER as sm

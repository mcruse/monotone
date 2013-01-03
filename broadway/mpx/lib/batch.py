"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
import weakref
from mpx.lib import edtlib
from mpx.lib import Result
from mpx.lib import msglog
from mpx.lib.thread_pool import NORMAL
from mpx.lib.exceptions import ENotFound
from mpx.lib.exceptions import ERNATimeout
debug = False
TRANSACTION_TIMEOUT = 30
TIMEDOUT_TRANSACTION_TIMEOUT = 15

def as_result(value):
    if isinstance(value, Exception):
        value = error_dictionary(value)
    if isinstance(value, dict):
        if value.has_key('edt__typ'):
            value = edtlib.edt_decode(value)
        elif (value.get('__base__') == 'Result' or 
              all(value.has_key(key) for key in 
                  ["cached", "changes", "timestamp", "value"])):
            value = Result.from_dict(value)
    if not isinstance(value, Result):
        msglog.log("broadway", msglog.types.WARN, 
                   "Unable to convert %r to Result." % (value,))
    return value

def error_dictionary(error):
    return {'value': error, 'changes': 1L, 
            'cached': 0, 'timestamp': time.time()}

def same_error(err1, err2):
    return ((type(err1) is type(err2)) and 
            (err1.args == err2.args) and 
            (err1.message == err2.message))

class RnaBatchManager(object):
    MAXBATCH = 100
    destinations = weakref.WeakValueDictionary()
    def get_manager(klass, dest):
        """
            Get batch manager for network location 'dest'.
            
            Class method creates new instance if one is not cached, 
            or returns an existing instance of one does.
        """
        manager = klass.destinations.get(dest)
        if manager is None:
            manager = klass(dest)
        return klass.destinations.setdefault(dest, manager)
    get_manager = classmethod(get_manager)
    def subscription_manager(netlocation):
        from mpx.lib.node import as_node
        nodeurl = "mpx://%s:%d/services/Subscription%%20Manager" % netlocation
        return as_node(nodeurl)
    subscription_manager = staticmethod(subscription_manager)
    def __init__(self, netlocation):
        self.prime = set()
        self.batches = set()
        self.destroy = set()
        self.netlocation = netlocation
        self.manager = self.subscription_manager(netlocation)
        super(RnaBatchManager, self).__init__()
    def clear_batches(self):
        """
            Schedule existing batches for destruction.

            Once all newly created batches have been primed, 
            or refreshed once, batches scheduled for destruction 
            are queued into NORMAL thread-pool to destroy.
            
            If invoked before previously scheduled batches are 
            destroyed, previous batches are enqueued for destruction 
            immediately.  Although this risks delaying priming and 
            refresh of new batches, it prevents runaway situation 
            wherein batches created and destroyed too quickly to 
            cleanup are not left behind.
            
            Potential problems are backup of NORMAL pool, may consider 
            destroying expired in-line in clear-batches to guarantee 
            new batches aren't created too quickly.
        """
        self.destroy.update(self.batches)
        self.batches.clear()
        self.prime.clear()
    def destroy_cleared(self):
        destroy = self.destroy.copy()
        self.destroy.clear()
        if debug:
            msglog.debug("%s destroying batches: \n%r\n" % (self, destroy))
        for batch in destroy:
            NORMAL.queue_noresult(batch.destroy, self.manager)
        return len(destroy)
    def create_batches(self, nodemap):
        # MNB calls create batches once with only newly subscribed 
        # point-map.  For example, those MNRs added due to user 
        # visiting single web-page.  
        # 
        # After invoking get-batch once on newly created batches, 
        # create-batches invoked again, this time with point-map 
        # containing all subscribed points.
        #
        # The point-map passed to the second invocation will be a 
        # superset of the firsts point-map.
        building = None
        self.clear_batches()
        for nid,node in nodemap.items():
            if (building is None) or (len(building) > self.MAXBATCH):
                building = RnaBatch(self)
                self.batches.add(building)
            building[nid] = node
        self.prime.update(self.batches)
        if debug:
            msglog.debug("%s created batches: \n%r\n" % (self, self.batches))
        return list(self.batches)
    def get_batch(self, batch, *args, **kw):
        transport = self.manager._NodeFacade__protocol.transport
        results = batch.get_results(self.manager, *args, **kw)
        if batch.timeout_occurred:
            transport.transaction_timeout = TIMEDOUT_TRANSACTION_TIMEOUT
        else:
            transport.transaction_timeout = TRANSACTION_TIMEOUT
        if not self.prime:
            # Prime was cleared by a previous get-batch 
            # invocation, ensuring that single-get batches 
            # created for added MNRs does not trigger destruction 
            # of subscribed batches associated with superset.
            # Note that batch protects destroy() caller from by 
            # skipping destroy of subscription if timeout occurred.
            if self.destroy:
                self.destroy_cleared()
        else:
            self.prime.discard(batch)
        return results
    def __str__(self):
        typename = type(self).__name__
        addr,port = self.netlocation
        batchcount = len(self.batches)
        return "%s(%s:%d %d batches)" % (typename, addr, port, batchcount)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

class RnaBatch(object):
    SUBTIMEOUT = 300
    MAXTIMEOUT = 1800
    def __init__(self, manager):
        self.sid = None
        self.nodemap = {}
        self.last_results = {}
        self.last_polled = 0
        self.last_failed = 0
        self.prime_timeout = 5
        self.last_refreshed = 0
        self.last_subscribed = 0
        self.nodes_changed = True
        self.created = time.time()
        self.batch_manager = manager
        self.timeout_occurred = False
        self.subscription_manager = None
        self.subscription_timeout = self.SUBTIMEOUT
        super(RnaBatch, self).__init__()
    def __setitem__(self, nid, node):
        if not isinstance(node, str):
            node = node._NodeFacade__service
        self.nodemap[nid] = node
        self.nodes_changed = True
    def __getitem__(self, nid):
        return self.nodemap[nid]
    def __len__(self):
        return len(self.nodemap)
    def clear(self):
        self.nodemap.clear()
        self.last_results.clear()
        self.nodes_changed = True
    def destroy(self, manager=None):
        if not manager:
            manager = self.subscription_manager
        if manager and self.subscribed():
            if self.timeout_occurred:
                message = ("Batch %s destruction leaving remote"
                           " subscription: timeout had occurred.")
                msglog.warn(message % self)
            else:
                try:
                    manager.destroy(self.sid)
                except:
                    message = "%s failed to destroy subscription %s on %s."
                    msglog.log("broadway", msglog.types.WARN, 
                               message % (self, self.sid, manager))
                    msglog.exception(prefix="handled")
                else:
                    if debug:
                        message = "Batch %s destroyed remote subscription."
                        msglog.debug(message % self)
        self.clear()
        self.sid = None
        self.subscription_manager = None
    def dirty(self):
        return self.nodes_changed
    def subscribed(self):
        return self.sid is not None
    def subscribe(self, manager):
        timeout = self.subscription_timeout
        self.subscription_manager = manager
        create = self.subscription_manager.create_polled_and_get
        result = create(self.nodemap, timeout, self.prime_timeout)
        self.sid = result["sid"]
        self.last_subscribed = time.time()
        self.nodes_changed = False
        if debug:
            total = len(self)
            primed = len(result["values"])
            msglog.debug("%s primed %d/%d values." % (self, primed, total))
        return result["values"]
    def get_results(self, manager):
        self.last_polled = time.time()
        if self.dirty() and self.subscribed():
            self.destroy(manager)
        try:
            try:
                if not self.subscribed():
                    changed = self.subscribe(manager)
                else:
                    changed = manager.poll_changed(self.sid)
            except ENotFound:
                self.sid = None
                self.last_results.clear()
                # Raise subscription timeout up to MAXTIMEOUT 
                # in increments of SUBTIMEOUT iteratively.
                # Consider also lowering prime-timeout, so that 
                # refresh loop doesn't block as long.  Problem is 
                # likely cause by RNA blocking, though, and so lowering 
                # prime-timeout may only increase chance that this 
                # particular call is useless.
                timeout = self.subscription_timeout + self.SUBTIMEOUT
                self.subscription_timeout = min(timeout, self.MAXTIMEOUT)
                message = "Recreating remote subscription %s on next poll."
                msglog.log("broadway", msglog.types.WARN, message % self)
                msglog.exception(prefix="handled")
            else:
                for nid,value in changed.items():
                    self.last_results[nid] = as_result(value)
                self.last_refreshed = time.time()
            results = self.last_results.copy()
        except Exception, error:
            self.last_failed = time.time()
            msglog.log("broadway", msglog.types.WARN, 
                       "Update batch %s get failed" % self)
            msglog.exception(prefix="handled")
            errors = [(nid, as_result(error)) for nid in self.nodemap.keys()]
            results = dict(errors)
            self.timeout_occurred = isinstance(error, ERNATimeout)
        else:
            self.timeout_occurred = False
        return results
    def __str__(self):
        typename = type(self).__name__
        lifespan = time.time() - self.last_polled
        return "%s(%d nodes, %0.3f old)" % (typename, len(self), lifespan)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

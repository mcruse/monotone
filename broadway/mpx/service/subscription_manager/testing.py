"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
from mpx.lib.node import as_node
sm = as_node('/services/Subscription Manager')
sid = sm.create_polled({'r1': '/interfaces/relay1'}, 20)
sub = sm.diag_get_subscriptions()[0]
snr = sub.snrmap.values()[0]
mnr = sm.diag_get_mnrs()[0]
sub.setdebug(2)
r1 = as_node('/interfaces/relay1')
sm.poll_changed(sid)

print mnr.description()



import time
import random
import threading
from mpx.lib import msglog
from mpx.lib import thread_pool
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.lib.scheduler import scheduler
from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent

class Node(CompositeNode):
    def __init__(self, *args, **kw):
        self.last = None
        self.value = None
        super(Node, self).__init__(*args, **kw)
    def get(self, asyncok=True):
        value = self.value
        self.last = value
        return value
    def getlast(self):
        return self.last
    def set(self, value):
        self.value = value

class IncrementalValue(Node):
    def configure(self, config):
        self.starting_value = int(config.get("start", 0))
        self.value_increment = int(config.get("increment", 1))
        super(IncrementalValue, self).configure(config)
    def start(self):
        self.set(self.starting_value)
        super(IncrementalValue, self).start()
    def get(self, asyncok=True):
        value = super(IncrementalValue, self).get()
        self.set(value + self.value_increment)
        return value

class TimeValue(Node):
    def get(self, asyncok=True):
        self.set(time.time())
        return super(TimeValue, self).get()

class RandomValue(Node):
    def configure(self, config):
        self.range = int(config.get('range', 1000))
        super(RandomValue, self).configure(config)
    def get(self, asyncok=True):
        self.set(self.range * random.random())
        return super(RandomValue, self).get()

class COVValue(IncrementalValue, EventProducerMixin):
    def __init__(self, *args, **kw):
        self.lastvalue = None
        self.scheduled = None
        IncrementalValue.__init__(self, *args, **kw)
        EventProducerMixin.__init__(self, *args, **kw)
    def start(self):
        super(COVValue, self).start()
        self.lastvalue = None
        self.schedule()
    def stop(self):
        if self.scheduled:
            try:
                self.scheduled.cancel()
            except:
                pass
        super(COVValue, self).stop()
    def schedule(self):
        self.scheduled = scheduler.after(15, self.trigger)
    def trigger(self):
        thread_pool.NORMAL.queue_noresult(self.notify)
        self.schedule()
    def notify(self):
        value = self.get()
        if value != self.lastvalue:
            event = ChangeOfValueEvent(self, self.lastvalue, value)
            self.event_generate(event)
        self.lastvalue = value

class Target(object):
    def __init__(self, nrt):
        self.events = 0
        self.debug = False
        self.exceptions = 0
        self.lookup = dict([(nid, as_node(nodeurl)) for 
                            nid,nodeurl in nrt.items()])
        super(Target, self).__init__()
    def event_handler(self, event):
        if self.debug:
            print "event_handler(%s)" % event
        changes = event.results()
        for nid,result in changes.items():
            value = result["value"]
            node = self.lookup[nid]
            if node.getlast() != value:
                errormsg = "%s event value is %r, last is %r"
                raise TypeError(errormsg % (nid, value, node.getlast()))
        self.events += 1
    def event_exception(self, *args, **kw):
        if self.debug:
            print "exception_handler(*%s, **%s)" % (args, kw)
        self.exceptions += 1
        msglog.exception()


def build_tree(types, parent="/interfaces/virtuals", count=30, levels=5):
    nodelevels = [[] for i in range(levels)] 
    parent = as_node(parent)
    for childnode in parent.children_nodes():
        childnode.prune()
    for number in range(count):
        nodetype = types[random.randint(0, len(types) - 1)]
        nodename = "%s(%d:%d)" % (nodetype.__name__, number, 0)
        parentnode = nodetype()
        parentnode.configure({'name': nodename, "parent": parent})
        nodelevels[0].append(parentnode)
        for level in range(1, levels):
            nodetype = types[random.randint(0, len(types) - 1)]
            nodename = "%s(%d:%d)" % (nodetype.__name__, number, level)
            node = nodetype()
            node.configure({'name': nodename, "parent": parentnode})
            parentnode = node
            nodelevels[level].append(node)
    return nodelevels


def create_tables(levels):
    tables = []
    for level in levels:
        items = [(node.name, node.as_node_url()) for node in level]
        tables.append(dict(items))
    return tables


types = [IncrementalValue, TimeValue, RandomValue, COVValue]
sm = as_node('/services/Subscription Manager')
virtuals = as_node("/interfaces/virtuals")
levels = build_tree(types, virtuals, 30, 5)
virtuals.start()
tables = create_tables(levels)
sids = []

tstart = time.time()
for table in tables:
    sids.append(sm.create_polled_and_get(table)['sid'])

tend = time.time()
print "Took %0.3f seconds" % (tend - tstart)


def destroy(sids):        
    tstart = time.time()
    while sids:
        sm.destroy(sids.pop())
    tend = time.time()
    print "Took %0.3f seconds" % (tend - tstart)


import threading
t = threading.Thread(target=destroy, args=(sids,))
t.start()



def run_tests(tables, count=10, interval=20.0):
    targets = []
    lookup = {}
    map(lookup.update, tables)
    delay = interval / (len(tables) + 1)
    for iteration in range(count):
        try:
            subscribed = {}
            target = Target(lookup)
            sid = sm.create_delivered(target)
            subscription = sm._SubscriptionManager__subscriptions[sid]
            print 'Test iteration %d (%s):' % (iteration, sid)
            last = {}
            for table in tables:
                if set(table) == set(last):
                    errormsg = "tables have same keys: %s, %s"
                    raise TypeError(errormsg % (last,table))
                last = table
            for table in tables:
                nrt = subscription.node_reference_table()
                if nrt != subscribed:
                    errormsg = "subscribed NRT mismatch: %s, %s"
                    raise TypeError(errormsg % (nrt, subscribed))
                print "\t-> merged %d nodes into %s" % (len(table), sid)
                sm.merge(sid, table)
                subscribed.update(table)
                print "\t-> pausing %0.3f seconds" % delay
                time.sleep(delay)
            nrt = subscription.node_reference_table()
            if nrt != subscribed:
                errormsg = "subscribed NRT mismatch: %s, %s"
                raise TypeError(errormsg % (nrt, subscribed))
            sm.destroy(sid)
            print "\t-> destroyed subscription"
            targets.append(target)
        except:
            msglog.exception()
    return targets


def run_parallel(processes, function, *args):
    threads = []
    for process in range(processes):
        thread = threading.Thread(target=function, args=args, verbose=True)
        threads.append(thread)
        thread.setDaemon(True)
        thread.start()
    return threads


run_tests(tables, 1, 1.0)
run_tests(tables, 2, 4.0)
run_tests(tables, 10, 20.0)

t1 = threading.Thread(target=run_tests, args=(tables, 2, 4.0))
t1.start()

threads = run_parallel(2, run_tests, tables, 2, 4.0)
threads = run_parallel(5, run_tests, tables, 10, 20.0)

for i in range(3):
    threads = run_parallel(5, run_tests, tables, 4, 10.0)
    for thread in threads:
        thread.join()
    print "Test %d complete" % i



sid = sm.create_polled(tables[0], 40)
subs = sm.diag_get_subscriptions()
sub = subs[0]
snrs = sub.snrmap.values()
sub.setdebug(2)

sids = []

tstart = time.time()
for table in tables:
    sids.append(sm.create_polled_and_get(table)['sid'])

tend = time.time()
print "Took %0.3f seconds" % (tend - tstart)

tstart = time.time()
while sids:
    sm.destroy(sids.pop())

tend = time.time()
print "Took %0.3f seconds" % (tend - tstart)


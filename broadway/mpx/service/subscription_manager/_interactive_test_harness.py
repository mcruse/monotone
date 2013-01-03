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
import threading
import time

from mpx.lib import thread_pool
from mpx.lib.scheduler import scheduler
from mpx.lib.node import as_internal_node, as_node_url, CompositeNode
from mpx.service.time import Time

from _manager import SUBSCRIPTION_MANAGER

def all_getable_nodes(node, result=None):
    if result is None:
        result = []
    node = as_internal_node(node)
    try:
        children = node.children_nodes()
        for child in children:
            all_getable_nodes(child, result)
    except:
        pass
    try:
        node.get()
        result.append(node)
    except:
        pass
    return result

def pop_optional_by_key(dict, key, default=None):
    if dict.has_key(key):
        result = dict[key]
        del dict[key]
        return result
    return default

def print_values(values_orig):
    values = {}
    values.update(values_orig)
    now = time.time()
    nids = values.keys()
    nids.sort()
    for nid in nids:
        print "%r:" % nid
        value_dict = {}
        value_dict.update(values[nid])
        cached = pop_optional_by_key(value_dict, 'cached', 'N/A')
        timestamp = pop_optional_by_key(value_dict, 'timestamp', 'N/A')
        changes = pop_optional_by_key(value_dict, 'changes', 'N/A')
        value = pop_optional_by_key(value_dict, 'value', 'N/A')
        try:
            age = now-timestamp
        except:
            age = 'N/A'
        print "  %r %r %r %r (%r)" % (value,changes,cached,timestamp,age)
        if value_dict:
            print "  Unknown attributes:"
            keys = value_dict.keys()
            keys.sort()
            for key in keys():
                print "    %r: %r" % (key, value_dict[key])
    return

class PolledSubscription(object):
    __doc = {}
    def __init__(self, name, poll_all):
        self._name = name
        self._run = 0
        self._running = 0
        self._sid = 0
        self._changed_values = {}
        self._values = {}
        self._poll_all = poll_all
        self.DELAY = 0.0
        self.__doc['DELAY'] = 'Delay in seconds between polling for values.'
        root = as_internal_node('/')
        if not root.has_child(name):
            anchor = CompositeNode()
            anchor.configure({'name':name,'parent':root})
            self._anchor = anchor
            t = Time()
            t.configure({'name':'time', 'parent':anchor})
            t.start()
        return
    def _schedule(self):
        try:
            float(self.DELAY)
        except:
            print "WARNING:  Bad DELAY (%r), setting to 1.0" % self.DELAY
            self.DELAY=1.0
        if self.DELAY > 0.0:
            scheduler.after(self.DELAY, self._queue)
        else:
            self._queue()
        return
    def _queue(self):
        if self._run:
            thread_pool.NORMAL.queue_noresult(self._poll)
        else:
            self._running = 0
        return
    def _poll(self):
        try:
            self._running = 1
            if self._poll_all:
                changed_values = SUBSCRIPTION_MANAGER.poll_all(self._sid)
            else:
                changed_values = SUBSCRIPTION_MANAGER.poll_changed(self._sid)
                if changed_values:
                    self._changed_values = changed_values
            self._values.update(changed_values)
        finally:
            self._schedule()
        return
    def changed_values(self):
        """Display the most recent set of changed values."""
        print_values(self._changed_values)
        return
    def values(self):
        """Display all values every updated."""
        print_values(self._values)
        return
    def start(self):
        """Start the memory use test's thread."""
        if self._run:
            print "ERROR:  Test already started"
            return
        nrt = {}
        self._nids = []
        getable_nodes = all_getable_nodes(self._anchor)
        for node in getable_nodes:
            node_url = as_node_url(node)
            self._nids.append(node_url)
            nrt[node_url] = node
        self._nids.sort()
        self._sid = SUBSCRIPTION_MANAGER.create_polled(nrt)
        self._run = 1
        self._schedule()
        return
    def stop(self):
        """Stop polling the subscription."""
        if not self._run:
            print "ERROR:  Test not started"
            return
        SUBSCRIPTION_MANAGER.destroy(self._sid)
        self._run = 0
        self._sid = None
        return
    def help(self):
        """Display this message."""
        method_names = []
        attribute_names = []
        for name in dir(self):
            if name[0:1] != '_':
                attribute = getattr(self,name)
                if callable(attribute):
                    if hasattr(getattr(self,name),'__doc__'):
                        if getattr(self,name).__doc__:
                            method_names.append(name)
                elif self.__doc.has_key(name):
                    attribute_names.append(name)
        method_names.sort()
        attribute_names.sort()
        print 78*"*"
        print "Interactive Methods:"
        for name in method_names:
            print "  %s() - %s" % (name, getattr(self,name).__doc__)
        print "Tunable Attributes:"
        for name in attribute_names:
            print "  %s=%r:  %s" % (name, getattr(self,name), self.__doc[name])
        print 78*"*"
        return

_subscribers = []

def new_polled(start=1,poll_all=0):
    global _subscribers
    index = len(_subscribers)
    name = 'p%d' % index
    p = PolledSubscription(name, poll_all)
    _subscribers.append(p)
    globals()[name] = p
    print name
    if start:
        p.start()
    return

def subscribers():
    """Display the list of subscribers and their status."""
    global _subscribers
    dup = _subscribers
    def _cmp(s1, s2):
        return cmp(s1,s2)
    dup.sort(_cmp)
    for s in dup:
        status = 'stopped'
        if s._run:
            status = 'starting/stopping'
        if s._running:
            status = 'running'
        print "%s: %s" % (s._name, status)

def examples():
    print 78*"*" + """
Examples:

>>> new_polled()
p0
>>> p0.start()
"""
    print 78*"*"
    return

def help():
    print 78*"*" + """
Interactive Functions:

  help() - Display this message.

  examples() - Display a bunch of test doc examples.

  new_polled() - Instanciate a new "memory use test."
  
          Returns an integer used to identify the test.  Pass the returned
          integer to the subscriber() function to get a reference to the new
          test.

          The test object has a "help()" method providing information on
          interacting with the test.  The test does not start running until
          the start() method is invoked."""
    print 78*"*"

if __name__ == '__main__':
    SUBSCRIPTION_MANAGER._set_tunable_parameters({'slow_poll_delay':0.5,
                                                  'untuned_poll_delay':0.0,
                                                  })
    SUBSCRIPTION_MANAGER.start()
    help()

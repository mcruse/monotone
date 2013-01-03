"""
Copyright (C) 2003 2004 2006 2007 2011 Cisco Systems

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
# Defines the base node classes and interfaces.
#
# @todo from_path needs to support remote node lookup.

from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ETypeError
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import EBusy
from mpx.lib.exceptions import *
from mpx.lib import msglog
from mpx.lib.threading import Lock, Thread
from mpx.lib.scheduler import scheduler
import string
import traceback
import types
from _node import as_node_url

class _Lock:
    def __init__(self):
        self._minutes = 0
        self._lock = Lock()
        self._scheduled = None
        self._stack = None
    def acquire(self,blocking=0):        
        value = self._lock.acquire(blocking)
        self._stack = traceback.extract_stack()
        self._schedule_print()
        return value
    def release(self):
        try:
            if self._scheduled:
                self._scheduled.cancel()
        finally:
            self._lock.release()
    def locked(self):
        return self._lock.locked()
    def _schedule_print(self):
        self._scheduled = scheduler.after(60,self._print,(self._stack,))
    def _print(self,stack):
        self._minutes += 1
        print 'Lock acquired: %s min' % self._minutes
        print string.join(traceback.format_list(stack))
        if self.locked():
            self._schedule_print()                 
        

# Active/Passive discovery
# Keyword parameter of 'wait_for_discovery' overrides default behavior of
# discovery processes.

###
## Abstract class for provide base discovery functionality for auto discovered nodes
##
class AutoDiscoveredNode(object):
    def __init__(self):
        self._nascent_children = {} #instantiated but unconfigured or started nodes
        self.discovered = 0
        self._adn_lock = Lock()
        self._discovery_thread = None
    ##
    # Lazily discovers children
    #
    # the subclass should implement this method
    #
    def _discover_children(self):
        raise ENotImplemented #implemented by subclass
    ##
    # Configures and starts a node
    #
    # @param node (a instantiated but unconfigured node), name.
    # @return nothing
    # @throws nothing (to prevent one bad node from blocking other's from starting)
    #
    def _configure_nascent_node(self, node, name):
        if self.debug > 1: print '_configure_nascent_node: ', name
        if type(node) == types.ClassType:
            node = node()
        elif type(node) == types.TypeType:
            node = node()
        node.configure({'name':name,
                        'parent':self,
                        'discovered':1,
                        'debug':self.debug})
        if not hasattr(node,'debug'):
            # HACK!
            node.debug = self.debug
        if self.debug > 1: print 'node configured', node.name
        return node
    ##
    # Configures and starts a node
    #
    # @param node (a instantiated b22050ut unconfigured node), name.
    # @return nothing
    # @throws nothing (to prevent one bad node from blocking other's from starting)
    #
    def _start_nascent_node(self, node):
        try:
            if self.debug: print 'start', node.name
            node.start()
            if self.debug > 1: print 'node started'
        except:
            msglog.exception()
            if self.debug:
                print 'failed to start node: %s %s' % (
                    node.__class__.__name__, node.name
                    )
    ##
    # Answer a list of names of discovered bacnet properties
    #
    # @param keyword dictionary.
    # @return list of property names
    # @throws None
    #
    def discover_children_names(self, **options):
        wait_for_discovery = 1
        if options.has_key('wait_for_discovery'):
            wait_for_discovery = options['wait_for_discovery']
        if self.debug > 1: print 'discover_children_names acquire for: ', self.name
        if self._adn_lock.acquire(wait_for_discovery) == 0: 
            if self.debug > 1: print 'did not acquire lock, return previous names'
            answer = self._nascent_children.keys()
            answer.sort()
            return answer
        try:
            if wait_for_discovery:
                return self._discover_children_names() #do it on the main thread
            else:
                self._start_discovery_thread()  #will start once we release the lock
                answer = self._nascent_children.keys()  #return what we've got so far
                answer.sort()  
                return answer
        finally:
            self._adn_lock.release()
            if self.debug > 1: print 'discover_children_names release for: ', self.name
    def _discover_children_names(self, **options):
        self._nascent_children = self._discover_children(**options)
        answer = self._nascent_children.keys()
        answer.sort()
        return answer
    ##
    # Discover any nodes on this object
    # that are not part of the node tree
    # Place the new nodes into the tree, configure and start them
    #
    # @param keyword dictionary.
    # @return None
    # @throws None
    #
    def discover_children_nodes(self, **options):
        wait_for_discovery = 1
        if options.has_key('wait_for_discovery'):
            wait_for_discovery = options['wait_for_discovery']
        if not hasattr(self,'debug'):
            # HACK!
            _debug = 0
            _parent = self.parent
            while _parent and not hasattr(_parent,'debug'):
                _parent = _parent.parent
            else:
                if _parent:
                    _debug = _parent.debug
            self.debug = _debug
        if self.debug > 1:
            print 'discover_children_nodes acquire for: ', self.name
        if self._adn_lock.acquire(wait_for_discovery) == 0: 
            if self.debug > 1: print 'discover_children_nodes did not acquire lock'
            return #do nothing
        if self.debug > 1: print 'discover_children_nodes acquired lock'
        try:
            if wait_for_discovery:
                if self.debug > 1: print 'discover children nodes, do complete discovery'
                self._discover_children_names(**options)  #do a complete discovery
            else:
                self._start_discovery_thread() # will start thread, which will
                                               # wait for us to release lock
            # By creating a new list, we are not iterating over a dictionary
            # that we are changing.
            node_keys = list(self._nascent_children.keys())
            node_keys.sort()
            if self.debug > 1: print 'discover_children_nodes, node keys: ', str(node_keys)
            for name in node_keys:
                new_node = self._nascent_children[name]
                del self._nascent_children[name] #remove from nascent list
                try:
                    new_node = self._configure_nascent_node(new_node, name)
                    self._start_nascent_node(new_node)
                except ENameInUse:
                    if self.debug: print 'name was in use already'
                    pass
                except:
                    msglog.exception()
                    if self.debug: 'something went wrong during configure or start node'
            #now that the new nodes are ensconced
            #self._nascent_children = {}
        finally:
            self._adn_lock.release()
            if self.debug > 1: print 'discover_children_nodes release for: ', self.name
            
    ##
    # Answer true if the named undiscovered node could exist
    #
    # @param name, keyword dictionary.
    # @return 1 if named device was found
    # @throws None
    #
    def _discover_name(self, name, **options):
        if self._nascent_children.has_key(name):
            return 1 #already discovered, no need to re-discover
        return name in self._discover_children_names()
    def discover_name(self, name, **options):
        wait_for_discovery = 1
        if options.has_key('wait_for_discovery'):
            wait_for_discovery = options['wait_for_discovery']
        if self.debug > 1: print 'discover_name acquire for: ', self.name
        if self._adn_lock.acquire(wait_for_discovery) == 0:
            return self._nascent_children.has_key() #give the best answer we can
        try:
            return self._discover_name(name)
        finally:
            self._adn_lock.release()
            if self.debug > 1: print 'discover_name release for: ', self.name
    ##
    # Find a particular child on this node.  Add to node tree if found
    #
    # @param name, keyword dictionary
    # @return the new node if found
    # @throws ENoSuchName is node is not found   
    def discover_child(self, name, **options):
        wait_for_discovery = 1
        if options.has_key('wait_for_discovery'):
            wait_for_discovery = options['wait_for_discovery']
        if self.debug > 1: print 'discover_child acquire for: ', self.name
        if self._adn_lock.acquire(wait_for_discovery) == 0:
            raise EBusy, 'busy'  #we didn't want to wait around
        try:          
            if wait_for_discovery:            
                self._discover_name(name)            
            else: #passively discover
                self._start_discovery_thread()
            if self._nascent_children.has_key(name):
                new_node = self._nascent_children[name]
                del self._nascent_children[name] #remove from nascent list
                try:
                    new_node = self._configure_nascent_node(new_node, name)
                    self._start_nascent_node(new_node)
                except ENameInUse:
                    if self.debug: print 'name was in use already'
                    # find and return the original node
                    return self._get_children()[name] # it better exist.... 
                except:
                    msglog.exception()
                    if self.debug: 
                        print 'something went wrong during configure or start node'
                return new_node

            raise ENoSuchName, name
        finally:
            self._adn_lock.release()
            if self.debug > 1: print 'discover_child release for: ', self.name
    def _start_discovery_thread(self, **options):
        if self._discovery_thread:
            #a thread is already running or setup to run
            if self.debug: print 'discovery thread allready running'
            return
        self._discovery_thread = _DiscoveryThread(self, **options)
        self._discovery_thread.start()

##
# This thread is spawned to continue discovery while the main thread returns
# empty handed.
#
class _DiscoveryThread(Thread):
    def __init__(self, node, **options):
        node_url = as_node_url(node)
        Thread.__init__(self, name='_DiscoveryThread(%r)' % node_url)
        if node.debug: print '%s.__init__()' % self.getName()        
        self.node = node
        self.options = options
    def run(self):
        #
        if self.node.debug: print '%s._DiscoveryThread.run()' % self.getName()
        try:
            answer = self.node._discover_children(**self.options)
            self.node._adn_lock.acquire()
            self.node._nascent_children = answer
        finally:
            self.node._discovery_thread = None
            self.node._adn_lock.release()
            if self.node.debug: print '%s.finally' % self.getName()

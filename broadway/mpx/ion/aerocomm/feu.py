"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
from mpx import properties
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, get_attributes, set_attributes
from mpx.lib import threading, msglog
import time, select
from mpx.lib.exceptions import *
import array, struct
from csafe import CSafe, status_text
from mpx.lib.event import EventProducerMixin, ChangeOfValueEvent

_who_is_message = '\xf1\x00\xf2'

def who_is_message():
    return _who_is_message

class FEU(CompositeNode, AutoDiscoveredNode, EventProducerMixin):
    def __init__(self):
        self.running = 0
        self._children_have_been_discovered = 0
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        EventProducerMixin.__init__(self)
        self.csafe = None
        self._mutex = threading.Lock() #preven multiple io operations
        self.ttl = 10
        self.feu_state = None
        self.cov = ChangeOfValueEvent(self, None, self.feu_state)
        self.description = None
    def default_name(self):
        return 'FEU' #only one per port so no need to individualize it like for a aerocomm client
    def configure(self, dict):
        CompositeNode.configure(self, dict)
        set_attribute(self, 'ttl', self.ttl, dict, float)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'ttl', config, str)
        return config
    def start(self):
        if not self.running:
            if not self.parent.is_open():
                self.parent.open()
            self.csafe = CSafe(self.parent) #port
            if feu_poll_thread:
                #global feu_poll_thread
                feu_poll_thread.add_feu(self)   #register with the status loop
        CompositeNode.start(self)
        self.running = 1
    def _discover_children(self):
        if self.debug: print 'FEU io group discover children'
        if self.running and not self._children_have_been_discovered: #empty
            self._children_have_been_discovered = 1
            answer = {}
            keys = self._get_attribute_node_names()
            for k in keys:
                child = _PropAttr()  #note this could be just the class, not the instance
                if self.debug: print 'IO point: %s discovered child: %s' % (self.name, k)
                answer[k] = child                                      
            return answer
        return self._nascent_children
    def update_state(self, new_state):
        if new_state is None: return
        if self.feu_state != new_state:
            try:
                new_state = status_text[new_state] #make sure its an enumerated value
            except:
                pass
            if self.debug: print 'update feu state, old state: %s new state: %s' % (str(self.feu_state), str(new_state))
            self.cov.old_value = self.feu_state
            self.feu_state = new_state
            self.cov.value = new_state
            self.event_generate(self.cov)
    def get(self, skipCache=0):
        return self.feu_state
    def _get_attribute_node_names(self):
        return self.csafe.properties.keys() + ['description']
    def _get_attr_value(self, name, skipCache=0):
        #if self.parent.transceiver_state in ('transceiver_responding','exception_in_xmit'):
        state, value = self.csafe.get(name)
        self.update_state(state)
        return value        
    def _allow_set(self, name):
        if name == 'description':
            return 1
        return 0
    def get_status(self): #must be called either with the lock locked
        return self._get_attr_value('Status')
#@todo
#put customer description node (with set)

class _PropAttr(CompositeNode):
    _read_lockout_period = 300.0 # sec
    def __init__(self):
        CompositeNode.__init__(self)
        self.last_value = None
        self.last_get_time = None
        self.ttl = 10
        self.valid_states={}
        self.exists_in_feu = 0
        self.old_feu_state = None
        self.missing_counter = 0
        self.missing_counter_threshold = 10
    def start(self):
        CompositeNode.start(self)
        if self.parent._allow_set(self.name):
            self.set = self._set
        self.ttl = self.parent.ttl
    def get(self, skipCache=0, **keywords):
        ttl = self.ttl
        if keywords.has_key('ttl'):
            ttl = keywords['ttl']
        if self.name == 'description': #the only settable attribute
            return self.parent.description
        self.parent._mutex.acquire()
        try:
            if not skipCache:  #setting skipcache always forces a read
                if self.last_get_time:
                    if (time.time() - ttl) < self.last_get_time:
                        return self.last_value

                #if the transceiver is not present, only read from status point
                #this presents a chicken and the egg problem if Status node is not read
                #therefor, any application MUST get() from the Status node to start the
                #others reading.
                if self.parent.parent.transceiver_state != 2: #'transceiver_responding':
                    if self.name != 'Status':
                        return self.last_value # attempt to read only status when xcvr down; for all others, rtn last value

                #only read certain points while in offline mode
                if self.parent.csafe.offline_mode(self.name):
                    if self.parent.feu_state == 9: #'OffLine':
                        if self.exists_in_feu == 0: # if we haven't seen even one response for this prop yet:
                            if self.missing_counter > self.missing_counter_threshold: # if retries have exceeded threshold:
                                # if we have not exceeded read lockout time threshold:
                                if (time.time() - self.last_get_time) < self._read_lockout_period:
                                    return self.last_value
                    else:
                        return self.last_value
                
            answer = None
            try:
                answer = self.parent._get_attr_value(self.name, skipCache)
                if answer is None: #timeout
                    if (self.name != 'Status') and (self.exists_in_feu == 0):
                        self.missing_counter += 1
                    pass
                else:
                    self.missing_counter = 0
                    self.exists_in_feu = 1
                if self.parent.debug: print 'PropAttr %s: exit get(): %s' % (self.name, str(answer))
            except EInvalidValue:
                print 'FEU Property invalid name: ', self.name
                pass
            self.last_value = answer
            self.last_get_time = time.time()
            return answer
        finally:
            self.parent._mutex.release()
    def _set(self, value):
        if self.name == 'description': #the only settable attribute
            print 'set description: ', value
            self.parent.description = value
            return
        raise ENotImplemented  #self.parent._set_attr_value(self.name, value)

def factory():
    return FEU()

class FeuPollThread(threading.ImmortalThread):
    _number_of_threads = 5
    def __init__(self):
        threading.ImmortalThread.__init__(self)
        self._lock = threading.Lock()
        self._FEU_map = None # control access to map to allow special processing during adds
        self._FEU_scan_list = None
        self._FEU_active_map = None # thread_name:feu_node_ref
        self._thread_pool = None    # thread_name:thread_obj
        self._poll_obj = None
        self.debug = 1
        self.update_interval = 1.0
        self._go = 1
        self._pause = threading.Event()
        return
    ##
    # run(): Main thread loop. Maintains a regular stream of requests to, 
    # and hopefully responses from, the detected FEUs, via the local and
    # remote xcvrs.
    #
    def run(self):
        if self.debug: print 'Start FeuPollThread'
        self._FEU_map = {} # control access to map to allow special processing during adds
        self._FEU_scan_list = []
        self._FEU_active_map = {} # thread_name:feu_node_ref
        self._thread_pool = {}    # thread_name:thread_obj
        self._poll_obj = select.poll()
        self._go = 1
        # Create threads for local thread pool:
        for i in range(self._number_of_threads):
            t = threading.ImmortalThread(target=self._scan_thread,args=())
            self._thread_pool[t.getName()] = t
            t.start()
        time.sleep(30)
        if self.debug: print 'FeuPollThread initial wait over, getting to work'
        try:
            while self._go:
                poll_result_list = self._poll_obj.poll(2000) # adapt to changes in registered fd's every X msec
                self._pause.wait() # wait if we should be paused
                if len(poll_result_list) == 0: # timeout
                    continue # hop right back into polling, with (possibly) updated list
                for poll_result in poll_result_list:
                    self._lock.acquire()
                    try:
                        feu = self._FEU_map[poll_result[0]]
                        try:
                            feu_status_node = feu.get_child('Status')
                            feu_status_node.get(1) # skip cache (block) to update node value and FEU state
                        except ENoSuchName: # Status child may not be created yet...
                            continue
                    finally:
                        self._lock.release()
        finally:
            # Clean up before thread termination:
            self._lock.acquire()
            try:
                # Terminate all threads in thread pool:
                self._FEU_scan_list = []
                for i in range(len(self._thread_pool)):
                    self._FEU_scan_list.append('End')
            finally:
                self._lock.release()
            for thr in self._thread_pool.values(): # make SURE they die...
                thr.should_die()
                thr.join(3.0)
        return
    def add_feu(self, feu):
        self._lock.acquire()
        try:
            self._FEU_map[feu.parent.file.fileno()] = feu
            self._FEU_scan_list.append(feu)
            self._poll_obj.register(feu.parent.file.fileno(), select.POLLIN)
        finally:
            self._lock.release()
        return
    def _get_next_feu_to_scan(self):
        thread_name = threading.currentThread().getName()
        feu = None
        self._lock.acquire()
        try:
            # Release existing FEU from this thread, back into scan_list:
            if self._FEU_active_map.has_key(thread_name):
                feu_old = self._FEU_active_map[thread_name]
                self._FEU_scan_list.append(feu_old)
                self._poll_obj.register(feu_old.parent.file.fileno(), select.POLLIN)
                del self._FEU_active_map[thread_name]
            # Remove head FEU from scan_list, into care of this thread:
            try:
                feu = self._FEU_scan_list.pop(0)
                if isinstance(feu, FEU): # could be string ("End")...
                    self._FEU_active_map[thread_name] = feu
                    self._poll_obj.unregister(feu.parent.file.fileno())
            except IndexError, e:
                pass
        finally:
            self._lock.release()
        return feu
    def _scan_thread(self):
        while 1:
            feu_node = self._get_next_feu_to_scan() # mutexed access
            if feu_node == 'End':
                return # all done now
            elif feu_node is None:
                time.sleep(2.0)
                self._pause.wait() # wait if we should be paused
                continue # go see if any FEUs need scanning...
            prop_nodes = feu_node.children_nodes()
            for prop_node in prop_nodes:
                if not feu_node.csafe.properties.has_key(prop_node.name):
                    continue # get here due to 'description' PropAttr
                offline_only = feu_node.csafe.properties[prop_node.name][2]
                if (feu_node.feu_state != 'OffLine') and offline_only:
                    continue
                prop_node.get(ttl=1) # skip cache (block) to update PropAttr value and FEU state
        return
    def pause(self): # pause all threads, while maintaining FEU info in this thread:
        self._pause.set()
        return
    def unpause(self): # unpause all threads:
        self._pause.clear()
        return
##
# Create and start the one-and-only feu_poll_thread when this module loads.
#
feu_poll_thread = FeuPollThread()
feu_poll_thread.start()
        
        
#"""        
        
#from mpx.lib.node import as_node

#def _some_test():
    #n=as_node('/interfaces/com1/aerocomm_server/00_50_67_0f_06_73/FEU')
    #c = n.children_nodes()
    #for i in range(10):
        #for child in c:
            #v = child.get(1)
            #print child.name, v, i
        #print '_______________________'
        
#"""            
#"""
#notes:
    #create simple TTL cache of 30 seconds for each value
    #when state change occurs, invalidate cache
    #don't cache STATE
    #use lock to prevent muti-thread access to FEU 
    #when state change occurs, generate event callback to scheduler
    #present a list of available points per current state
    #if error on point request, re-search available points
    #generate state change callbacks on radio errors

 
    
    ##add settable node to server status to allow reset of status counters
    ##feu module level thread to register and query status of all feu's
    ##get_status() which double blocks for mutex and returns latest status
    ##change whois to a couple at start up and then more relaxed, still needs
    ##to check health of tranceiver.  
    #make based on scheduler
    ##when message received from transceiver then update status with good
    #test eeprom write
    
    #decide what to do about Offline points during other states (learn each states point list?)
    

#"""
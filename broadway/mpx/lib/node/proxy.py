"""
Copyright (C) 2003 2004 2005 2006 2007 2010 2011 Cisco Systems

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
import types
from mpx.lib.node import as_node
from mpx.lib.configure import set_attribute, get_attribute, REQUIRED, as_boolean
from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.exceptions import Exception, ENotStarted, ETimeout, EConnectionError, ENoSuchNode
from mpx.lib.event import EventConsumerMixin, ChangeOfValueEvent
from mpx.lib.scheduler import scheduler
from mpx.lib.thread_pool import NORMAL
from mpx.lib.threading import NOTHING, Lock, Queue
from mpx.lib import msglog
from random import randint
##
#  Abstract class for provide base proxy point functionality for nodes
#  assumes Mix-in with Composite or Configurable node
#

#control which direction is actively proxied

GET_ONLY = 0
SET_ONLY = 1

debug = 0

class ProxyAbstractClass:
    def __init__(self):
        self._link = None #'actual' node 
        self.link = None #string url or node reference
        self._proxy_get = None #set to actual's preferred get method
        self._proxy_set = None
        self._proxy_start_exception = None
        self._proxy_sid = None
    def configure(self, cd):
        if self.is_proxy():
            set_attribute(self, 'link', self.link, cd, str) #self.link to allow descendent init classes to dymanically affect self.link
            set_attribute(self, 'error_response', '%ERROR%', cd, str)  #keywords: %ERROR% %NONE% or desired value
            set_attribute(self, 'use_subscription', '1', cd, as_boolean)
    def configuration(self, cd=None):
        if cd is None:
            cd = {}
        if self.is_proxy():
            get_attribute(self, 'link', cd, str)
            get_attribute(self, 'error_response', cd, str)
            get_attribute(self, 'use_subscription', cd, as_boolean)
        return cd
    ##
    # hook into get/set interface
    # if linked node has special interface to help proxies, use that
    # if sub-class has special interface to act as proxy, use that
    #
    def start(self):
        if self.is_proxy():
            self.get = self._start_proxy_get
            self.set = self._start_proxy_set
            self._proxy_start_exception = None
        return

    def stop(self):
        return
    ##
    #
    def _start_proxy_get(self):
        try:
            self._proxy_get = self._proxy_get_link
            if hasattr(self._proxy_linked_node(), 'get_for_proxy'): #the actual wants to help
                self._proxy_get = self._proxy_get_for_proxy
            if hasattr(self, 'get_from_proxy'): #the sub class has a better idea for get
                self.get = self.get_from_proxy
            else:
                self.get = self._proxy_get
        except Exception, e: #something went wrong during start, forget the link
            self._proxy_start_exception = e
            self._proxy_set_exception(e)
            raise
        else:
            self._proxy_start_exception = None
        return self.get()
    def _start_proxy_set(self, value=None):
        try:
            self._proxy_set = self._proxy_set_link
            if hasattr(self._proxy_linked_node(), 'set_for_proxy'):
                self._proxy_set = self._proxy_set_for_proxy
            if hasattr(self, 'set_from_proxy'):
                self.set = self.set_from_proxy
            else:
                self.set = self._proxy_set
        except Exception, e: #something went wrong during start, forget the link
            self._proxy_start_exception = e
            self._proxy_set_exception(e)
            raise
        else:
            self._proxy_start_exception = None
        if value:
            self.set(value)
    def _proxy_set_exception(self, e):
        return #override this method to handle reporting exceptions (mainly in bacnet)
    def is_proxy(self):
        return 1
    def _proxy_get_link(self, skip_cache=0):
        try:
            if self._proxy_start_exception:  #if there was an exception during start, repeat it now
                self._start_proxy_get() #try again until it starts ok
            answer = None
            if self.use_subscription:
                if (self._proxy_sid is None):
                    self._proxy_sid = SM.create_polled(
                        {1:self._proxy_linked_node()}, timeout=None
                        )
                answer = SM.poll_all(self._proxy_sid)[1]
                if isinstance(answer, dict):
                    answer = answer['value']
                    if isinstance(answer, Exception):
                        raise answer
            else:
                answer = self._proxy_linked_node().get() # @fixme skip_cache) how to use gets that dont have skip cache
            self._proxy_set_exception(None)
            return answer
        except Exception, e: #transfer any exception over to the proxy
            if hasattr(self, 'error_response'): 
                if self.error_response != '%ERROR%':   #default error response is to pass exception up
                    if self.error_response == '%NONE%': return None
                    return self.error_response  #return specific desired value when an error occurs
            self._proxy_set_exception(e)
            raise # reraise the exception
            
    def _proxy_get_for_proxy(self, skip_cache=0):
        return self._proxy_linked_node().get_for_proxy(skip_cache)
    def _proxy_set_link(self, value):
        try:
            if self._proxy_start_exception:
                self._start_proxy_set() #try again until it starts ok
            self._proxy_linked_node().set(value)
            self._proxy_set_exception(None)
        except Exception, e:
            self._proxy_set_exception(None)
            raise # reraise the exception

    def linked_node_has_set(self):
        return hasattr(self._proxy_linked_node(), 'set')
    
    def _proxy_set_for_proxy(self, value):
        self._proxy_linked_node().set_for_proxy(value)
    ##
    # Lazily discovers reference to linked node
    #
    def _proxy_linked_node(self):
        if self._link is None:
            self._link = as_node(self.link)
        return self._link
    ##
    # If the subclass supports the 'set_exception' interface, keep it updated
    #
    def _proxy_set_exception(self, e):
        if hasattr(self, 'set_exception'):
            self.set_exception(e)

    
###
#we could use a more direct reference to the desired get/set methods for performance
#but I want to wait to see how the subscription service will cut into the loop
class ActiveProxyAbstractClass(EventConsumerMixin):
    def __init__(self):
        self._link = None #get 'actual' node
        self.link = None
        self._proxy_get = None #set to actual's preferred get method
        self._proxy_set = None
        self._proxy_start_exception = None
        self._proxy_sid = None
        self.proxy_direction = GET_ONLY #direction subscription "pushes" the data
        self._proxy_active_source = None
        self._proxy_active_destination = None
        self._proxy_active_lock = Lock()
        self._proxy_active_thread_lock = Lock()
        self._proxy_active_event = None
        self._proxy_trigger_counter = 0
        self._retry_win_high = 30
        EventConsumerMixin.__init__(self, self.change_of_value)
        self.debug = debug
    def configure(self, cd):
        set_attribute(self, 'link', None, cd, str)
        set_attribute(self, 'error_response', '%ERROR%', cd, str)  #keywords: %ERROR% %NONE% or desired value
        set_attribute(self, 'proxy_direction', self.proxy_direction, cd, int)
    def configuration(self, cd=None):
        if cd is None:
            cd = {}
        get_attribute(self, 'link', cd, str)
        get_attribute(self, 'error_response', cd, str)
        get_attribute(self, 'proxy_direction', cd, str)
        return cd
    ##
    def start(self):
        self._proxy_start_exception = None
        if self.is_proxy():
            self._proxy_start_active_mode()

    def stop(self):
        if self._proxy_sid is not None:
            SM.destroy(self._proxy_sid)
            self._proxy_sid = None
        return
    
    ##
    # start up subscription service if we are in active mode
    # keep trying until we are successful
    # todo: thread safe?
    def _proxy_start_active_mode(self):
        if self.link:
            try:
                if self._proxy_sid is None: #have not started subscription service yet
                    if self.proxy_direction == GET_ONLY:
                        self._proxy_active_source = self._proxy_linked_node()
                        if self._proxy_active_source is None:
                            raise ENotStarted()
                        self._proxy_active_destination = self
                    else: #SET_ONLY
                        self._proxy_active_source = self
                        self._proxy_active_destination = self._proxy_linked_node()
                        if self._proxy_active_destination is None:
                            raise ENotStarted()
                    self._proxy_active_queue = Queue()
                    self._proxy_sid = SM.create_delivered(self, {1:self._proxy_active_source})
                    if self.debug: print 'Active proxy %s started successfully' % (self.name)
            except:
                #it didn't work.  Setup schedule to try again in x seconds.  
                if self._retry_win_high < 90:
                    self._retry_win_high += 1
                retry_in = randint(int(self._retry_win_high * .66), self._retry_win_high)
                scheduler.seconds_from_now_do(retry_in, self._proxy_start_active_mode)
                #raise  #took this out since it mostly just served to force the scheduler tread to restart
                if self.debug: msglog.exception()

    def change_of_value(self, event):
        #print 'proxy change of value event'
        self._last_event = event
        #if not isinstance(event, ChangeOfValueEvent):
            #return
        # Insert event into queue, and (automatically) notify _event_handler_thread:
        trigger = 0
        self._proxy_active_lock.acquire()
        try:
            self._proxy_active_event = event # save only latest event, throw away older values
            if self._proxy_trigger_counter < 3: #no point in trigger too many times for noisy inputs
                self._proxy_trigger_counter += 1
                trigger = 1
        finally:
            self._proxy_active_lock.release()  #could this line go below the next to reduce triggers to thread?
        if trigger:
            #print 'proxy trigger'
            self._proxy_trigger_queue()

    def _proxy_trigger_queue(self):
        #print 'proxy triggerED'
        # run the set function on a thread pool thread:
        NORMAL.queue_noresult(self.proxy_active_set, self)
        return
    def proxy_active_set(self, dummy):
        #print 'active proxy event'
        self._proxy_active_thread_lock.acquire() #only one set at a time is active
        try:
            try:
                event = None
                self._proxy_active_lock.acquire()
                try:
                    event = self._proxy_active_event
                    self._proxy_active_event = None
                    if self._proxy_trigger_counter:
                        self._proxy_trigger_counter -= 1
                finally:
                    self._proxy_active_lock.release() #allow any new covs while we do the set
                if event: #pending event
                    if self.debug:
                        print str(event)
                    value = event.results()[1]['value']
                    if isinstance(value, Exception):
                        raise value
                    try: #to set() value on destination node
                        self._proxy_active_destination.set(value) #don't know how long this will take
                        self._proxy_set_exception(None)
                    #failure in attempt to set data, maybe node is not ready yet, try again later    
                    except (ETimeout, EConnectionError, ENotStarted, ENoSuchNode):
                        #put the event back in the active event if no new one has come in while we were trying to set()
                        self._proxy_active_lock.acquire()
                        try:
                            if self._proxy_active_event is None:
                                self._proxy_active_event = event #put it back in for next attempt unless a new one came in
                        finally:
                            self._proxy_active_lock.release() #allow any new covs while we do the set
                        scheduler.seconds_from_now_do(60, self._proxy_trigger_queue)  #try again in one minute
                        raise #re-raise the set() exception
                    except:
                        raise
                    if self.debug: print 'proxy_active_set call set returned'
            except Exception, e:
                try:
                    self._proxy_set_exception(e)
                    # we have squashed the exception
                    # we want to log exceptions that are potential bugs
                    # but we don't want to fill the msglog with ETimeouts
                    if not isinstance(e, ETimeout):
                        msglog.exception()
                except:
                    # if there is a bug in the set_exception method we want
                    # to see this otherwise it makes debugging difficult
                    msglog.exception()
        finally:
            self._proxy_active_thread_lock.release()
        if self.debug: print 'proxy_active_set done'
        pass
    
    def is_proxy(self):
        if self.link:
            return 1
        return 0

    def linked_node_has_set(self):
        return hasattr(self._proxy_linked_node(), 'set')
    
    ##
    # Lazily discovers reference to linked node
    #
    def _proxy_linked_node(self):
        if self._link is None:
            self._link = as_node(self.link)
        return self._link
    ##
    # If the subclass supports the 'set_exception' interface, keep it updated
    #
    def _proxy_set_exception(self, e):
        if hasattr(self, 'set_exception'):
            self.set_exception(e)
    
###
#we could use a more direct reference to the desired get/set methods for performance
#but I want to wait to see how the subscription service will cut into the loop
###

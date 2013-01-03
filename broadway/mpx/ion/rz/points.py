"""
Copyright (C) 2003 2004 2007 2008 2009 2011 Cisco Systems

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
"""module points.py: Contains defs for support classes that
encapsulate data/control points on a network.
"""
import array
import random
import string
import time

from mpx.lib import Result
from mpx.lib import msglog
from mpx.lib import thread_pool

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import as_onoff
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.event import EventConsumerAbstract
from mpx.lib.event import EventProducerMixin

from mpx.lib.exceptions import EAlreadyRunning
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import ENoSuchNode
from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import MpxException

from mpx.lib.node import as_internal_node
from mpx.lib.node import CompositeNode
from mpx.lib.node import ConfigurableNode
from mpx.lib.node.proxy import ActiveProxyAbstractClass


from mpx.lib.rz.rznet_line_handler import RznetThread

from mpx.lib.scheduler import scheduler

from mpx.lib.threading import Lock
from mpx.lib.threading import Condition

from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER as SM


##
# Helper class that Nodes (or others) can use to implement get() and
# get_result() interfaces using the Node's ChangeOfValueEvent event.
#
# @note Intended for "oneshot" use, although multiple gets work.
# @note OPTIMIZED FOR SINGLE THREAD ACCESS!
#@todo  add a way to get subscription started without blocking
class GetViaCOV(EventConsumerAbstract):
    def __init__(self, source_node, timeout=960):
        EventConsumerAbstract.__init__(self)
        self.__node = as_internal_node(source_node)
        self.__cond = Condition()
        self.__event = None
        self.__sched = None #scheduled action to unsubscribe the point
        self.__timeout = timeout #number of seconds to maintain subscription
        self._event_received = False
        return
    def get_event(self,**keywords):
        if self.__node._pruned_url:
            try:
                self.__node = as_internal_node(self.__node._pruned_url)
            except ENoSuchName, e:
                raise ENoSuchNode(self.__node._pruned_url)
        self.__cond.acquire()
        try:
            if self.__event is None:
                self.__node.event_subscribe(self, ChangeOfValueEvent)
#@todo  add a way to get subscription started without blocking  - ie return a value of None - based on keyword?
                do_not_wait = keywords.get('do_not_wait', None)
                if do_not_wait:
                    #create a dummy event and put None in the value and return that
                    self.__event = ChangeOfValueEvent(self.__node, None, None)
                else:
                    self.__cond.wait() #block until the value shows up
            elif not self._event_received:  #if event not nil and no event received it means 'do_not_wait' was used on first call
                do_not_wait = keywords.get('do_not_wait', None)
                if not do_not_wait:
                    self.__cond.wait() #if do_not_wait was used on last call, now we wait for cov
            if self.__sched:
                sched = self.__sched.reset() #if it's too late to reschedule, this returns None
                if sched is None: #too late
                    self.__sched.cancel() #try to cancel it
                self.__sched = sched
            if self.__sched is None: #first time or after expiration
                self.__sched = scheduler.after(self.__timeout, self.unsubscribe)
            return self.__event
        finally:
            self.__cond.release()
    def get(self, skipCache=0, **keywords):
        value = self.get_event(**keywords).value
        if isinstance(value, Exception):
            raise value
        return value
    def get_result(self, skipCache=0):
        result = self.get_event().as_result()
        if isinstance(result.value, Exception):
            raise result.value
        return result
    #as long as we are subscribed, this will get point updates
    def event_action(self, event):
        self.__cond.acquire()
        self.__event = event
        self._event_received = True
        # markeva: Shane was right...
        self.__cond.notifyAll()
        self.__cond.release()
        return
    def event_handler(self, event):
        thread_pool.NORMAL.queue_noresult(self.event_action, event)
        return
    def unsubscribe(self):
        thread_pool.NORMAL.queue_noresult(self._unsubscribe)
    def _unsubscribe(self):
        self.__cond.acquire()
        try:
            # markeva: This unsubscribe really scares me...
            self.__cond.notifyAll()
            if self.__sched: #executed outside of rescheduling unsubscribe
                self.__sched = None
                self.__event = None #indicates we need to resubscribe
                self._event_received = False
                self.__node.event_unsubscribe(self, ChangeOfValueEvent)
        finally:
            self.__cond.release()

    def __str__(self):
        return 'GetViaCov for node: %s\n event: %s\n sched: %s\n timeout: %s\n' % (str(self.__node),str(self.__event),str(self.__sched),str(self.__timeout))
class PointNode(CompositeNode, ActiveProxyAbstractClass, EventProducerMixin):
    """class PointNode: Wraps data/control point as a tree node.
    """
    _node_id_ = '120075'
    _PointNode__cov_lock = Lock() # No need to create a lock for every instance.

    class Status(ConfigurableNode, EventProducerMixin):
        _Status__cov_lock = Lock() # No need to create a lock for every instance.
        def __init__(self, parent):
            self.__parent = parent
            self.__cov_count = 0
            self._old_value = None
            ConfigurableNode.__init__(self)
            EventProducerMixin.__init__(self)
            return
        def get(self, skipCache=0):
            if self.__parent.is_bound_proxy():
                new_value = {'value': self.__parent._value,
                             'status': self.__parent._state & 1}
                return new_value
            return GetViaCOV(self).get()
        def get_result(self, skipCache=0):
            return GetViaCOV(self).get_result()
        ##
        # callback from the line handler thread
        # is called from within a critical section of code
        # needs to be short and sweet
        # @note Do not "filter out" COV of equal value, consumers of COV
        #       are guaranteed an initial callback.
        def _cov_event_callback(self, point_data_object):
            try:
                new_value = {'value': point_data_object.value,
                             'status': point_data_object.state & 1}
                cov = ChangeOfValueEvent(self,
                                         self._old_value, new_value,
                                         time.time())
                self._old_value = new_value
                self.event_generate(cov) # - trigger the event.  This is on
                                         #   the line handler thread.
            except:
                msglog.exception()
            return
        def prune(self, force=False):
            ConfigurableNode.prune(self, force)
            new_value = ENoSuchNode(self._pruned_url)
            self._value = new_value
            cov = ChangeOfValueEvent(self, self._old_value, new_value,
                                     time.time())
            self._old_value = new_value
            self.event_generate(cov)
            return
        def has_cov(self):
            return 1
        # @fixme HACK ALERT.
        #
        # The COV event implementation for Status nodes is circuitous.  The
        # Status node implementation of event_subscribe() and
        # event_unsubscribe() register as consumers of the Status node's,
        # parent node's COV event.  This is done because:
        # 1. The parent node's COV event production manages interest in rznet
        #    values via AML/CML messages.
        # 2. Status node's values are updated via the parent node's RZNET COV
        #    callback mechanism.
        # The parent's COV events are ignored (they do not contain enough
        # information to generate a Status value), but the parent's RZNET
        # COV handler call's the Status node's _cov_event_callback() directly
        # which then generates events for the consumer's of the Status node.
        #
        def event_handler(self, event):
            return
        def event_subscribe(self, consumer, event, **keywords):
            self.__cov_lock.acquire()
            try:
                EventProducerMixin.event_subscribe(self, consumer, event,
                                                   **keywords)
                if event is ChangeOfValueEvent:
                    if self.__cov_count == 0:
                        self.__parent.event_subscribe(self, event, **keywords)
                    else:
                        # Force initial COV value on parent.  Oh what a tangled
                        # web.
                        self.__parent._request_cov_callbacks()
                    self.__cov_count += 1
            finally:
                self.__cov_lock.release()
            return
        def event_unsubscribe(self, consumer, event, **keywords):
            self.__cov_lock.acquire()
            try:
                EventProducerMixin.event_unsubscribe(self, consumer, event,
                                                     **keywords)
                if event is ChangeOfValueEvent:
                    self.__cov_count -= 1
                    if self.__cov_count == 0:
                        self.__parent.event_unsubscribe(self, event,
                                                        **keywords)
                    elif self.__cov_count < 0:
                        # @fixme add log message.
                        self.__cov_count = 0
            finally:
                self.__cov_lock.release()
            return
    def __init__(self, line_handler = None):
        CompositeNode.__init__(self)
        ActiveProxyAbstractClass.__init__(self)
        EventProducerMixin.__init__(self)
        self.__cov_count = 0
        self._line_handler = line_handler
        self._old_value = None
        self.__status = None
        self.proxy_lan_addr = None
        self.proxy_obj_ref = None
        self._value = None
        self._state = None
        self._get_via_cov = None
        return
    def configure(self, config):
        CompositeNode.configure(self, config) 
        ActiveProxyAbstractClass.configure(self, config)
        set_attribute(self, 'debug_lvl', 1, config, as_boolean)            
        set_attribute(self, 'lan_address', 0, config, int)
        set_attribute(self, 'id_number', 0, config, int)
        set_attribute(self, 'description', '', config)
        set_attribute(self, 'proxy_lan_addr', 0, config, int)
        set_attribute(self, 'proxy_obj_ref', 0, config, int)
        set_attribute(self, 'proxy_direction', 0, config, int)
        set_attribute(self, '__node_id__', self._node_id_, config)
        return
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'debug_lvl', config)
        get_attribute(self, 'lan_address', config)
        get_attribute(self, 'id_number', config)
        get_attribute(self, 'description', config)
        get_attribute(self, 'proxy_lan_addr', config)
        get_attribute(self, 'proxy_obj_ref', config)
        get_attribute(self, '__node_id__', config)
        ActiveProxyAbstractClass.configuration(self, config)
        return config
    def start(self):
        #only if we are an active point (not simply a parent node)
        if self.lan_address != 0 and self.id_number != 0:
            #do we have a _line_handler and therefore want get/set
            if self._line_handler is None: #preconfigured instead of autodiscovered
                self._line_handler = self.get_line_handler()
            if self._line_handler:
                self.get = self._get
                self.get_result = self._get_result
                self.set = self._set
                self.has_cov = self._has_cov
                self.event_subscribe = self._event_subscribe
                self.event_unsubscribe = self._event_unsubscribe
                self._line_handler_up = self.__line_handler_up
                try:
                    if not self.has_child("_status"):
                        self.__status = self.Status(self)
                        self.__status.configure({'name':'_status', 'parent':self})
                except:
                    msglog.exception()
                if self.is_bound_proxy():
                    self._line_handler.register_bound_proxy(self)
        CompositeNode.start(self)
        ActiveProxyAbstractClass.start(self)
        return
    def stop(self):
        try:
            ActiveProxyAbstractClass.stop(self)
            if self._line_handler is not None:
                if self.is_bound_proxy():
                    self._line_handler.unregister_bound_proxy(self)
                else:
                    self._line_handler.unregister_subscribed_proxy(self)
        except:
            msglog.exception()
        CompositeNode.stop(self)
        return
    def prune(self, force=False):
        CompositeNode.prune(self, force)
        new_value = ENoSuchNode(self._pruned_url)
        self._value = new_value
        cov = ChangeOfValueEvent(self, self._old_value, new_value,
                                 time.time())
        self._old_value = new_value
        self.event_generate(cov)
        return
    def is_bound_proxy(self):
        return (self.proxy_obj_ref > 0 and
                self.proxy_lan_addr > 0)
    def get_line_handler(self):
        return self.parent.get_line_handler()
    ##
    # @note # DO NOT CALL BEFORE SETTING line_handler PROPERTY!
    # I don't think this is used any more
    def _get_value(self, skipCache=0):
        if self.is_bound_proxy():
            return self._value
        force = 0 #force retransmission of subscribe packet
        for i in range(3):
            value = self._line_handler.get_value(self.lan_address,
                                                 self.id_number, force,
                                                 self._cov_event_callback)
            self._value = value
            if not value is None:
                # @fixme later one, figure out how to get state info to user
                return value
            force = 1
            print 'force rz point %s resubscription' % (self.name)
        return ETimeout()
    def _get(self, SkipCache=0, **keywords):
        if self.is_bound_proxy():
            return self._value
        if self._get_via_cov is None:
            self._get_via_cov = GetViaCOV(self)
        return self._get_via_cov.get(**keywords)
    def _get_result(self, SkipCache=0):
        if self._get_via_cov is None:
            self._get_via_cov = GetViaCOV(self)
        return self._get_via_cov.get_result()
    ##
    # @note DO NOT CALL BEFORE SETTING line_handler PROPERTY!
    def _set(self, v):
        if self._pruned_url:
            try:
                return as_internal_node(self._pruned_url)._set(v)
            except ENoSuchName, e:
                raise ENoSuchNode(self._pruned_url)
        if v in ("", "None", None):
            v = None
        else:
            v = float(v)
        self._value = v
            
        lan_address = self.lan_address
        id_number = self.id_number
        if self.is_bound_proxy():
            lan_address = self.proxy_lan_addr
            id_number = self.proxy_obj_ref
            if self.proxy_direction < 1: # mpx get in rz-100 only receives
                if v is not None:
                    self._line_handler.set_value(lan_address, id_number, v)
                return
        if v == None:
            self._line_handler.clr_override(lan_address, id_number)
        else:
            self._line_handler.set_override(lan_address, id_number, v)
        return
    def _has_cov(self):
        return 1
    ##
    # Register for callbacks with the line handler.  If we are already
    # registered and have up-to-date point data, then this will immediately
    # generate a callback.  This behavior is important for generating initial
    # COVs for event subscriptions.
    def _request_cov_callbacks(self):
#in line handler, collect these requests for a short period of time (1 second) before sending
        self._line_handler.register_rznet_cov(
            self.lan_address,
            self.id_number,
            self._cov_event_callback
            )
        return
    def __line_handler_up(self, rznet_line_handler):
        assert self._line_handler is rznet_line_handler, (
            "self._line_handler is NOT rznet_line_handler"
            )
        if self.is_bound_proxy():
            self._line_handler.register_bound_proxy(self)
        else:
            self.__cov_lock.acquire()
            try:
                if self.__cov_count:
                    # If anyone has registered for ChangeOfValue events,
                    # re-register for callbacks from the RzNet handler.
                    self._request_cov_callbacks()
            finally:
                self.__cov_lock.release()
        return
    ##
    # @note HACK to integrate with mpx.lib.proxy.ActiveProxyAbstractClass
    def change_of_value(self, event):
        ActiveProxyAbstractClass.change_of_value(self, event)
        self.event_generate(event)
        return
    def _event_subscribe(self, consumer, event, **keywords):
        EventProducerMixin.event_subscribe(self, consumer, event, **keywords)
        if event is ChangeOfValueEvent:
            if self.is_bound_proxy():
                # Cheesy HACK that ensures COV callback for bound points.
                self._line_handler.register_bound_proxy(self)
            else:
                self.__cov_lock.acquire()
                try:
                    # Always _request_cov_callbacks because we rely on the
                    # initial callback to generate an initial event.
                    self._request_cov_callbacks()
                    self.__cov_count += 1
                finally:
                    self.__cov_lock.release()
        return
    def _event_unsubscribe(self,consumer,event,**keywords):
        EventProducerMixin.event_unsubscribe(self, consumer, event, **keywords)
        if event is ChangeOfValueEvent:
            if self.is_bound_proxy():
                pass
            else:
                self.__cov_lock.acquire()
                try:
                    self.__cov_count -= 1
                    if self.__cov_count == 0:
                        self._line_handler.unregister_rznet_cov(
                            self.lan_address,
                            self.id_number
                            )
                    elif self.__cov_count < 0:
                        # @fixme add log message.
                        self.__cov_count = 0
                finally:
                    self.__cov_lock.release()
        return
    ##
    # callback from the line handler thread
    # is called from within a critical section of code
    # needs to be short and sweet
    # @note Do not "filter out" COV of equal value, consumers of COV
    #       are guaranteed an initial callback.
    def _cov_event_callback(self, point_data_object):
        try:
            new_value = point_data_object.value
            self._value = new_value
            self._state = point_data_object.state
            cov = ChangeOfValueEvent(self, self._old_value, new_value,
                                     time.time())
            self._old_value = new_value
            self.event_generate(cov) # - trigger the event.  This is on the
                                     #   line handler thread.
            if self.__status:
                # Update the _status child handle value too:
                self.__status._cov_event_callback(point_data_object)
        except:
            msglog.exception()
        return
    def _map_output_connections(self,offset_x,offset_y,tdn): #to support mediator based application references
        #answer a dict of xy vs nodes for all the outputs
        output_connections = {}
        for n in self.children_nodes(): #output register nodes
            if isinstance(n, PointNode):
                xy = tdn.get_output_x_y(n.name)
                if xy is not None:
                    if xy > (0,0): #this output register is used as a connection point
                        x,y = xy
                        x = x + offset_x #add in the offset for this template
                        y = y + offset_y
                        output_connections[(x,y)] = n
        return output_connections
    def nodebrowser_handler(self, nb, path, node, node_url):
        # the purpose of this special handler is to get all the points in 
        # one subscription instead of individually.  This greatly speeds up
        # the rz net peer driver
        sid = None
        html = ''
        if len(self.children_names()):
            node_table = {}
            for c in self.children_nodes(): #pre AML
                if isinstance(c, PointNode):
                    node_table[id(c)]=c
            if len(node_table):
                sid = SM.create_polled(node_table)
        try:
            html = nb.get_default_view(node, node_url)
        finally:
            if sid:
                SM.destroy(sid)
        return html

class PointGroupNode(PointNode):
    """ class PointGroupNode: Instances act as children of RznetNode or other
    PointGroupNode objects, and as parents of PointNode or other PointGroupNode
    objects. Currently, PointGroupNode acts as an unadulterated CompositeNode,
    but let's keep it around in case we think of things that we'll want to 
    do to groups of points.
    """
    _node_id_ = '120076'
    def configure(self, config):
        set_attribute(self, '__node_id__', self._node_id_, config)
        PointNode.configure(self, config)
        return
    def configuration(self):
        config = PointNode.configuration(self)
        get_attribute(self, '__node_id__', config)
        return config    
    def start(self):
        PointNode.start(self)
        return
    def stop(self):
        PointNode.stop(self)
        return

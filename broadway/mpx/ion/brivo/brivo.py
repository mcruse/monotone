"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import as_boolean

from mpx.lib.exceptions import ETimeout 

from mpx.lib.persistent import PersistentDataObject

from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent

from mpx.lib import msglog
from mpx.lib.msglog.types import ERR
from mpx.lib.msglog.types import WARN
from mpx.lib.msglog.types import INFO

from mpx.lib.xmlrpclib import Server

from mpx.lib.scheduler import scheduler

from dispatcher import BrivoDispatcher

from data import *
import time

##
# OnSite (Standalone) Brivo access control panel
class OnSite(CompositeNode, AutoDiscoveredNode):
    def __init__(self):
        self._endpoint = None
        self.running = False
        self._discovered = False
        super(OnSite, self).__init__()
        return
        
    def configure(self, cd):
        super(OnSite, self).configure(cd)
        set_attribute(self, 'address', REQUIRED, cd)
        set_attribute(self, 'user', REQUIRED, cd)
        set_attribute(self, 'password', REQUIRED, cd)
        set_attribute(self, 'email', REQUIRED, cd)
        set_attribute(self, 'use_https', 'yes', cd, as_boolean)
        # discovery mode == once or none
        set_attribute(self, 'discovery_mode', 'once', cd)
        if self.use_https:
            transport = 'https'
        else:
            transport = 'http'
        default_uri = '%s://%s/cgi-bin/acs.fcgi?user=%s&pass=%s' %\
            (transport, self.address, self.user, self.password)
        set_attribute(self, 'endpoint_uri', default_uri, cd)
        if self.running is True:
            # force endpoint reconfiguration
            self.running = False 
            self.start() 
        return
        
    def configuration(self):
        cd = super(OnSite, self).configuration()
        get_attribute(self, 'address', cd)
        get_attribute(self, 'user', cd)
        get_attribute(self, 'password', cd)
        get_attribute(self, 'email', cd)
        get_attribute(self, 'use_https', cd)
        get_attribute(self, 'discovery_mode', cd)
        get_attribute(self, 'endpoint_uri', cd)
        return cd
        
    def start(self):
        if self.running is False:
            self._endpoint = Server(self.endpoint_uri)
        super(OnSite, self).start()
        self.running = True
        return
        
    def stop(self):
        self.running = False
        self._discovered = False
        return
        
    def _discover_children(self):
        answer = {}
        if not self._discovered and self.running is True and \
            self.discovery_mode == 'once':
            existing_accounts = []
            for accnt in self.children_nodes({'auto_discover':False}): #self._get_children().values():
                existing_accounts.append(accnt.configuration().get('brivo_id_value'))
            # query panel for list of active accounts
            accnts = self.list_accounts()
            for accnt_id in accnts:
                # add new accounts
                if accnt_id.get('value') not in existing_accounts:
                    accnt_name = self.retrieve_account(accnt_id)['name']
                    answer[accnt_name] = Account(accnt_id)
            self._discovered = True
        return answer
        
    # Brivo XML-RPC methods follow
    def list_accounts(self, filter=[]):
        print 'list_accounts'
        return self._endpoint.list_accounts(filter)
        
    def retrieve_account(self, accnt):
        print 'retrieve_account'
        return self._endpoint.retrieve_account(accnt)
        
    def retrieve_device(self, accnt, dev):
        print 'retrieve_device'
        return self._endpoint.retrieve_device(accnt, dev)
        
    def list_events(self, accnt, filter=[]):
        print 'list_events'
        return self._endpoint.list_events(accnt, filter)
        
    def list_devices(self, accnt, filter=[]):
        print 'list_devices'
        return self._endpoint.list_devices(accnt, filter)
        
    def delete_event_subscription(self, accnt, sid):
        print 'delete_event_subscription'
        return self._endpoint.delete_event_subscription(accnt, sid)
        
class _PersistentSubscriptionIds(PersistentDataObject):
    def __init__(self, node):
        self.array = []
        PersistentDataObject.__init__(self, node)
        PersistentDataObject.load(self)
        return

##
# An installation consists of one or more accounts
class Account(CompositeNode, AutoDiscoveredNode):
    def __init__(self, accnt_id=None):
        if accnt_id is not None:
            self.brivo_account = BrivoId(accnt_id)
            self.brivo_id_value = accnt_id.get('value')
        else:
            self.brivo_account = None
        self.running = False
        self.__server = None
        self._discovered = False
        super(Account, self).__init__(self)
        return
    
    def configure(self, cd):
        super(Account, self).configure(cd)
        # the email property is used when we register for events - if the
        # OnSite panel has problems communicating events to us via XML-RPC
        # then the 'email' recipient is notificed
        set_attribute(self, 'email', self.parent.email, cd)
        if cd.has_key('brivo_id_value') or self.brivo_account is None:
            set_attribute(self, 'brivo_id_value', REQUIRED, cd)
        return
        
    def configuration(self):
        cd = super(Account, self).configuration()
        get_attribute(self, 'email', cd)
        get_attribute(self, 'brivo_id_value', cd)
        return cd
    
    def start(self):
        if self.brivo_account is None:
            self.brivo_account = BrivoId({'type':'brivo_id', 
                                          'value':self.brivo_id_value})
        self.event_path = '/brivo/'+self.name
        self.dispatcher = BrivoDispatcher()
        if self.use_https:
            server = '/services/network/https_server'
        else:
            server = '/services/network/http_server'
        self.dispatcher.configure({'request_path':self.event_path, 
                                   'parent':server,
                                   'name':'brivo_%s_handler' % urllib.encode(self.name)})
        self.dispatcher.start()
        self.__pdo_sids = _PersistentSubscriptionIds(self)
        self._subscriptions = self.__pdo_sids.array[:]
        self.children_nodes() # force device discovery ...
        self.register_for_events()
        super(Account, self).start()
        self.get_all_events()
        self.running = True
        return
        
    def stop(self):
        for sid in self._subscriptions:
            self.server.delete_event_subscription(self.brivo_account, 
                                                  BrivoId({'type':'brivo_id', 'value':sid}))
        self.dispatcher.stop()
        self.dispather.prune()
        return
        
    def _discover_children(self):
        answer = {}
        if not self._discovered and self.running is True and \
            self.parent.discovery_mode == 'once':
            existing_devices = []
            for dev in self.children_nodes({'auto_discover':False}): #self._get_children().values()
                existing_devices.append(accnt.configuration.get('brivo_id_value'))
            devs = self.server.list_devices(self.brivo_account)
            for dev in devs:
                brivo_dev = self.server.retrieve_device(self.brivo_account, dev)
                brivo_dev_id = brivo_dev.get('id').get('value')
                if brivo_dev_id not in existing_devices:
                    # add newly discovered devices
                    brivo_dev_name = brivo_dev.get('name')
                    #names = []
                    #names.extend(self._get_children().keys()) #children_names
                    if brivo_dev_name in self.children_names({'auto_discover':False}):
                        msg = 'Skipping auto-creation - node %s already exists in account %s' % \
                            (brivo_dev_name, self.name)
                        msglog.log('Brivo', WARN, msg)
                        continue
                    answer[brivo_dev_name] = Device(brivo_dev)
            self._discovered = True
        return answer
        
    def get_all_events(self):
        evts = self.server.list_events(self.brivo_account)
        # sort events based on when they occurred (occurred == XML-RPC DateTime)
        evts.sort(lambda x,y: cmp(x.get('occurred'), y.get('occurred')))
        for evt in evts:
            self.dispatcher.distribute(BrivoEvent(evt))
        return
        
    def register_for_events(self):
        for sid in self._subscriptions:
            # remove any existing subscriptions
            self.server.delete_event_subscription(self.brivo_account, 
                                                  BrivoId({'type':'brivo_id', 'value':sid}))
        self._subscriptions = []
        i = 0
        for dev in self.children_nodes():
            # register interest in events from each device
            id = BrivoId({'type':'brivo_id', 'value':str(i)})
            criteria = BrivoCriteria({'keyword':'device_id', 
                                      'operator':'eq',
                                      'value':BrivoId({'type':'brivo_id',
                                                       'value':dev.brivo_id_value})})
            sid = BrivoEventSubscription({'id':id,
                                          'name':'dev_%s_subscr' % dev.name,
                                          'url':self.event_path,
                                          'string':self.email,
                                          'criteria':criteria})
            self._subscriptions.append(sid)
            i += 1
        self._save_subscriptions()
        return
        
    def _save_subscriptions(self):
        self.__pdos_sids.array = self._subscriptions[:]
        self.__pdos.save()
        return
  
    def __get_server(self):
        if self.__server is None:
            self.__server = self.parent
        return self.__server
        
    server = property(__get_server)
    
class Device(CompositeNode, EventProducerMixin):
    CLOSED = 0
    OPEN = 1
    PULSE = 2
    TIMED_OPEN = 3
    class DeviceState(object):
        def __init__(self, device):
            self._present_value = CLOSED
            self._state_lock = Lock()
            self._scheduled = None
            self._device = device
            self._event_map = {\
                'access_by_user':TIMED_OPEN,
                'admin_latch_output':CLOSED,
                'admin_locked_early':CLOSED,
                'admin_pulse_output':PULSE,
                'admin_unlatch_output':OPEN,
                'admin_unlocked_early':OPEN,
                'door_ajar':OPEN,
                'door_ajar_cleared':CLOSED,
                'door_auto_lock':CLOSED,
                'door_auto_unlock':OPEN,
                'door_forced_open':OPEN,
                'man_lock':CLOSED,
                'man_unlock':OPEN}
            return
            
        def _toggle_state(self):
            self._state_lock.acquire()
            try:
                # confirm that we are still scheduled - there's a small
                # race window between _toggle_state and _set, otherwise.
                if self._scheduled:
                    self._present_value = int(not self._present_value)
                    self.device.trigger_cov()
                    self._scheduled = None
            finally:
                self._state_lock.release()
            
        def _schedule_toggle(self):
            when = time.time() + self.device.toggle_period
            self._scheduled = scheduler.at(when, self._toggle_state, ())
            return
            
        def _set(self, evt):
            if evt not in self.event_map.keys():
                # an event we're not interested in
                return
            self._state_lock.acquire()
            try:
                if self._scheduled is not None:
                    # a state transition is scheduled, cancel it and allow this
                    # event to take precedence. 
                    scheduled = self._scheduled
                    self._scheduled = None
                    try:
                        scheduled.cancel()
                    except:
                        pass
                new_value = self.event_map.get(evt)
                if new_value in (OPEN, CLOSED,):
                    self._present_value = new_value
                else:
                    if new_value == PULSE:
                        self._toggle_state()
                    else:
                        #TIMED_OPEN
                        self._present_value = OPEN
                    self._schedule_toggle()
                self.device.trigger_cov()
            finally:
                self._state_lock.release()
                
        def _get(self, value):
            return self._present_value

        present_value = property(_get, _set)
        
    def __init__(self, device=None):
        if device is not None:
            self.device = BrivoDevice(device)
            self.brivo_id_value = device.get('id').get('value')
        else:
            self.device = None
        self.state = self.DeviceState(self)
        self.running = False
        self._last_value = None
        self.__dispatcher = None
        super(Device, self).start()
        # call __init__ on old style class
        EventProducerMixin.__init__(self)
        return
        
    def configure(self, cd):
        super(Device, self).configure(cd)
        if cd.has_key('brivo_id_value') or self.device is None:
            set_attribute(self, 'brivo_id_value', REQUIRED, cd)
        set_attribute(self, 'toggle_period', 30.0, float)
        return
        
    def configuration(self):
        cd = super(Device, self).configuration()
        get_attribute(self, 'brivo_id_value', cd)
        get_attribute(self, 'toggle_period', cd)
        return cd
        
    def start(self):
        # register for events that are of interest to this particular
        # device
        self.dispatcher.register(self, self.brivo_id_value)
        super(Device, self).start()
        self.running = True
        return
        
    def stop(self):
        self.dispatcher.unregister(self, self.brivo_id_value)
        self.running = False
        return
        
    def get(self, skipCache=0):
        return self.state.present_value
        
    def has_cov(self):
        return 1
                
    def trigger_cov(self):
        if not self.event_class_consumer_count:
            return
        v = self.get()
        if v != self._last_value:
            cov = ChangeOfValueEvent(self, self._last_value, v, time.time())
        self.event_generate(cov)
        self.old_value = v
        return
        
    def update(self, evt):
        self.state.present_value = evt.get('event')
        print 'name=%s, evt=%s' % (self.name, self__last_evt)
        self.trigger_cov()
        return
        
    def __get_dispatcher(self):
        if self.__dispatcher is None:
            self.__dispatcher = self.parent.dispatcher
        return self.__dispatcher
    
    dispatcher = property(__get_dispatcher)
        

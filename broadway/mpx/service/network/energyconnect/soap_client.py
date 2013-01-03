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
import time

from SOAPpy.Types import *

from mpx.lib.node import CompositeNode
from mpx.lib.node import as_deferred_node
from mpx.lib.node import as_node_url
from mpx.lib.node import as_node

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.persistent import PersistentDataObject

from mpx.lib.scheduler import scheduler

from mpx.lib.threading import Lock

from mpx.lib.soap.soap_proxy import RemoteWebServiceProxy

from mpx.lib import EnumeratedDictionary
from mpx.lib import msglog
from mpx.lib import Result

EVENT_NS = 'http://eservices.energyconnectinc.com/'
# Time barrier == (2038, 1, 18, 19, 14, 7, 0, 18, 0)
# This is the value that is returned, when there are no
# events scheduled.
MAXTIME = 9999999999.0 

# An events action level is expressed via the strings
# 'Green' and 'Red'.  These are enumerated for the
# benefit of application (TIM) logic.
action_level_codes = EnumeratedDictionary(
    {0:'',
     1:'Green',
     2:'Red'}
)

class _PDO(PersistentDataObject):
    def __init__(self, node):
        self.events = None
        PersistentDataObject.__init__(self, node)
        PersistentDataObject.load(self)
        return
        
class DREvent(object):
    class ScheduleEntry(object):
        def __init__(self, when, cb, state):
            self.when = when
            # Callback that is executed when the schedule wakes up.
            self._cb = cb
            self._scheduled = scheduler.at_time_do(when, self.cb, state)
            return
        def cb(self, state):
            self._scheduled = None
            self._cb(state)
            return
        def cancel(self):
            self._scheduled.cancel()
            return
        def reschedule(self, when, cb, *args):
            self.cancel()
            self._scheduled = scheduler.at_time_do(when, cb, args)
            return
        def is_active(self):
            return self._scheduled
    def __init__(self, event_container, event=None):
        self._scheduler = {'EventStartTimeLocal':None,
                           'EventEndTimeLocal':None,
                           'EventMaxEndTimeLocal':None}
        self._state_lock = Lock()
        self.event_container = event_container
        if event is not None:
            for t in ['EventStartTimeUTC',
                      'EventEndTimeUTC',
                      'EventMaxEndTimeUTC']:
                datetime = event.get(t)
                if datetime and isinstance(datetime, str):
                    datetime = self._to_secs(datetime)
                event[t] = datetime
            self.__event_attrs__ = event
        else:
            self.__event_attrs__ = {}
        self.load_attrs(event)
        self.EventActive = 0
        if self.EventStartTimeUTC and self.EventStartTimeUTC != MAXTIME:
            self.EventPending = 1
        else:
            self.EventPending = 0
        if not self.is_expired():
            self._schedule()
        return
    def update_state(self, state):
        self._state_lock.acquire()
        try:
            self.EventActive = state
            if self.event_container.debug:
                msglog.log(
                    'EnergyConnect', msglog.types.INFO,
                    'Event (%s) transitioning to state:%d.' % (self.EventID, state)
                )
            if state:
                self.EventPending = 0
            if self.is_expired():
                # Remove this event from the event containers list.
                self.event_container.destroy_event(self)
                for sched_obj in self._scheduler.values():
                    if sched_obj and sched_obj.is_active():
                        # This could just be a, potentially redundant, 
                        # scheduled state change that is driven via max 
                        # end time.  Nothing in the spec. prevents having 
                        # both an endtime and a maxendtime.  If we're already 
                        # expired, then there's no need to keep it around.
                        sched_obj.cancel()
        finally:
            self._state_lock.release()
        return
    def is_pending(self):
        return (time.time() < self.EventStartTimeLocal)
    def is_active(self):
        return self.EventActive
    def is_expired(self):
        return time.time() > self.EventEndTimeLocal
    def load_attrs(self, event):
        if not event:
            # Load an empty event.
            event = {
                'EventID':'NullEvent',
                'SiteCode':self.event_container.parent.site_code,
                'EventCode':'',
                '_ActionLevelCode':None,
                'EventStartTimeUTC':MAXTIME,
                'EventEndTimeUTC':MAXTIME,
                'EventMaxEndTimeUTC':MAXTIME
            }
        for name, value in event.items():
            if name == 'ActionLevelCode':
                # ActionLevelCode property gets "fixed up"
                name = '_ActionLevelCode'
            setattr(self, name, value)
        return
    def _schedule(self):
        state_map = {'EventStartTimeLocal':1,
                     'EventEndTimeLocal':0,
                     'EventMaxEndTimeLocal':0}
        t = time.time()
        for time_slot_name, sched_obj in self._scheduler.items():
            if not hasattr(self, time_slot_name) or \
                getattr(self, time_slot_name) == MAXTIME:
                continue
            if time_slot_name == 'EventStartTimeLocal' and \
                getattr(self, time_slot_name) < t:
                if self.is_expired():
                    self.event_container.destroy_event(self)
                else:
                    # this event should already be active.
                    self.update_state(1)
                continue
            when = getattr(self, time_slot_name)
            state = state_map[time_slot_name]
            if sched_obj is None:
                self._scheduler[time_slot_name] = self.ScheduleEntry(
                        when,
                        self.update_state,
                        state
                    )
            elif sched_obj.when != getattr(self, time_slot_name):
                sched_obj.reschedule(when, self.update_state, state)
        return
    # Converts a datetime from EnergyConnect to unix time.
    def _to_secs(self, time_string):
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        utc_time_tuple = time.strptime(time_string, fmt)
        return time.mktime(utc_time_tuple)
    def __get_action_level(self):
        # Return an EnumeratedValue, instead of just 'Red', f.e..
        return action_level_codes[getattr(self, '_ActionLevelCode', None)]
    ActionLevelCode = property(__get_action_level)
    def __get_event_start_local(self):
        return self.event_container._to_localtime(self.EventStartTimeUTC)
    EventStartTimeLocal = property(__get_event_start_local)
    def __get_event_end_local(self):
        endtime = self.EventEndTimeUTC
        if endtime is None:
            # An explicit end time was not set, return the max end time.
            endtime = self.EventMaxEndTimeUTC
        return self.event_container._to_localtime(endtime)
    EventEndTimeLocal = property(__get_event_end_local)
    def __get_event_max_end_local(self):
        return self.event_container._to_localtime(self.EventMaxEndTimeUTC)
    EventMaxEndTimeLocal = property(__get_event_max_end_local)
    def __get_event_starts_in(self):
        if self.EventStartTimeLocal is None or self.EventStartTimeLocal == MAXTIME:
            return None
        starts_in = self.EventStartTimeLocal - time.time()
        if starts_in < 0:
            starts_in = 0.0
        return starts_in
    EventStartsIn = property(__get_event_starts_in)
    def __repr__(self):
        return str(self.__event_attrs__)
        
##
# Class providing the SOAP interface.
class Endpoint(RemoteWebServiceProxy):
    def start(self):
        super(Endpoint, self).start()
        for method in self._proxy.methods.values():
            # Setting the namespace in this manner is required to 
            # build SOAP payload that the EnergyConnect service
            # will grok.
            method.namespace = EVENT_NS
        self._proxy.soapproxy.config.buildWithNamespacePrefix = 0
        return
    # Dumps SOAP transaction details to console.
    def debugOn(self):
        self._proxy.soapproxy.config.debug = 1
        return
    def debugOff(self):
        self._proxy.soapproxy.config.debug = 0
        return
        
class Site(CompositeNode):
    def __init__(self):
        self._scheduler = None
        self._known_events = []        
        self._last_update = 0.0
        super(Site, self).__init__()
        return
    def configure(self, cd):
        set_attribute(self, 'user', REQUIRED, cd)
        set_attribute(self, 'pwd', REQUIRED, cd)
        set_attribute(self, 'site_code', REQUIRED, cd)
        set_attribute(self, 'period', 60, cd, int)
        set_attribute(self, 'enable_poll', '1', cd, int)
        set_attribute(self, 'debug', '0', cd, int)
        self._encode_request_params()
        super(Site, self).configure(cd)
        return
    def configuration(self):
        cd = super(Site, self).configuration()
        get_attribute(self, 'user', cd)
        get_attribute(self, 'pwd', cd)
        get_attribute(self, 'site_code', cd)
        get_attribute(self, 'period', cd)
        get_attribute(self, 'enable_poll', cd)
        get_attribute(self, 'debug', cd)
        return cd
    def start(self):
        super(Site, self).start()
        # first poll takes place 60 secondes after starting, 
        # but continues at a frequency of self.period
        self._scheduler = scheduler.after(60, self.poll)
        return
    def poll(self):
        if self.enable_poll:
            if self.debug:
                msglog.log(
                    'EnergyConnect', msglog.types.INFO,
                    'Polling Endpoint'
                )
            try:
                resp = self.parent.GetEventNotification(
                        self.user_enc,
                        self.password_enc,
                        self.site_code_enc
                    )
                self.distribute_response(resp)
            except: #@fixme - exceptions raised from SOAP Proxy?
                msglog.exception()
            self._last_update = time.time()
        else:
            if self.debug:
                msglog.log(
                    'EnergyConnect', msglog.types.INFO,
                    'Endpoint polling disabled.'
                )
        self._scheduler = scheduler.after(self.period, self.poll)
        return
    def send_ack(self, event, r_code):
        # The response is built from the original event.
        response = self._build_event_notification_response(
                event, 
                r_code
            )
        self.parent.SendEventNotificationResponse(
                self.user_enc,
                self.password_enc,
                intType(1, 'eventNotificationResponseCount'),
                response
            )
        if self.debug:
            event_id = event['EventID']
            msglog.log(
                'EnergyConnect', msglog.types.INFO,
                'Sent status response %d for event %s.' % (r_code, event_id)
            )
        return
    def distribute_response(self, rsp):
        self._last = rsp
        for event in self._get_events(rsp):
            event_id = event.get('EventID')
            if event_id in self._known_events:
                continue
            self._known_events.append(event_id)
            event_type = event.get('EventCode').split('_')[0]
            consumers = [c for c in self._get_event_consumers() \
                if c.event_type == event_type]
            for consumer in consumers:
                consumer.update(event)
        return
    def _get_event_consumers(self):
        return [child for child in self.children_nodes() \
            if isinstance(child, DREventContainer)]
    def _get_events(self, rsp):
        try:
            count = int(rsp['eventNotificationCount'])
        except:
            msglog.exception()
            return []
        if count == 0:
            return []
        # yes - it's deeeep.  Grab the container
        event_container = rsp['eventCollection']['EventNotifications']
        event_list = event_container['EventNotification']['EventNotification']
        if not isinstance(event_list, list):
            event_list = [event_list]
        return event_list
    def _build_event_notification_response(self, event, response_code):
        inner_enr = structType(typed=0)
        inner_enr._name = 'EventNotificationResponse'
        for attr in event:
            if attr in ['EventID', 'SiteCode', 'ResponseCode']:
                inner_enr._addItem(attr, event[attr])
        inner_enr._addItem('ResponseCode', response_code)
        outer_enr = structType(typed=0)
        outer_enr._name = 'EventNotificationResponse'
        outer_enr._addItem('EventNotificationResponse', inner_enr)
        enr_array = structType(typed=0)
        enr_array._name = 'EventNotificationResponses'
        enr_array._addItem('EventNotificationResponse', outer_enr)
        ec = structType(typed=0)
        ec._name = 'eventResponseCollection'
        ec._addItem('EventNotificationResponses', enr_array)
        return ec
    def _encode_request_params(self):
        self.user_enc = stringType(self.user, 'userName')
        self.password_enc = stringType(self.pwd, 'password')
        self.site_code_enc = stringType(self.site_code, 'siteID')
        return
        
class DREventContainer(CompositeNode):
    def __init__(self):
        self._pdo_lock = Lock()
        # The "Null Event".  We delegate to this event when no other
        # events are active\scheduled.
        # time nodes are used for determining current localtime offset from utc.
        self.__utctime_node = None
        self.__localtime_node = None
        self.ack_map = {}
        CompositeNode.__init__(self)
        return
    def configure(self, cd):
        super(DREventContainer, self).configure(cd)
        # ILR, DSR, RTD, EconOpp
        set_attribute(self, 'event_type', REQUIRED, cd)
        set_attribute(self, 'compliance_ack_node', REQUIRED, cd, as_deferred_node)
        return
    def configuration(self):
        cd = super(DREventContainer, self).configuration()
        get_attribute(self, 'event_type', cd)
        get_attribute(self, 'compliance_ack_node', cd, as_node_url)
        return cd
    def start(self):
        self._events = [DREvent(self)]
        self._pdo = _PDO(self)
        if self._pdo.events:
            for evt in self._pdo.events:
                event_obj = DREvent(self, eval(evt))
                if event_obj.EventEndTimeLocal > time.time():
                    self._events.append(event_obj)
                else:
                    msglog.log(
                        'EnergyConnect', msglog.types.INFO,
                        'Purging expired event (%s) from persistent data.' % event_obj.EventID
                    )
            self._sort_events()
            self._persist()
        super(DREventContainer, self).start()
        return
    def update(self, event):
        event_id = event.get('EventID')
        for e in self._events:
            if e.EventID == event_id:
                # We already know about this event.
                # this check may seem redundant - but is used to protect
                # us across restarts where there are pending events.
                if not self.ack_map.has_key(event_id):
                    # resend acks after a framework restart.  In practice,
                    # events usually cease to exist on the server side after
                    # being ack'd, but in practice, this could change.
                    self._send_ack(event)
                    self.ack_map[event_id] = True
                return
        event_obj = DREvent(self, event)
        # no need to add stale (already expired) events.
        if not event_obj.is_expired():
            event_id = event_obj.EventID
            msglog.log(
                'EnergyConnect', msglog.types.INFO,
                'Received %s event %s.' % (self.event_type, event_id)
            )
            if self.compliant():
                self._events.append(event_obj)
                self._sort_events()
                self.ack_map[event_id] = True
            self._persist()
        self._send_ack(event, event_obj.is_expired())
        return
    def destroy_event(self, event):
        for e in self._events:
            if e.EventID == event.EventID:
                self._events.remove(e)
                self._persist()
                if self.debug:
                    msglog.log(
                        'EnergyConnect', msglog.types.INFO,
                        'Event %s has expired.' % e.EventID
                    )
                break
        return
    ##
    # @fixme - provide a mechanism to allow the user to change their mind.
    # ie., use event_delivered to change compliance feedback on known events.
    # Based on initial conversations with EnergyConnect, it doesn't sound like
    # they're ready to deal with this, yet.
    def compliant(self):
        try:
            compliant = int(self.compliance_ack_node.get())
        except:
            msglog.exception()
            compliant = 0
        return compliant
    def _send_ack(self, event, expired=False):
        # Our ack could be a nack. 
        # Comliant == 100, non-compliant == 101.
        c_map = {0:101, 1:100}
        if expired:
            r_code = 101
        else:
            r_code = c_map.get(self.compliant(), 101)
        self.parent.send_ack(
                event, 
                r_code
            )
        return
    def _persist(self):
        self._pdo_lock.acquire()
        try:
            events = []
            for evt in self._events:
                # The "Null Event" is uniquely identified as having 
                # an EventStartTimeUTC == MAXTIME.
                if evt.EventStartTimeUTC != MAXTIME:
                    events.append(repr(evt))
            self._pdo.events = events
            self._pdo.save()
        finally:
            self._pdo_lock.release()
        return
    def _sort_events(self):
        self._events.sort(
                lambda x,y: cmp(x.EventStartTimeUTC, 
                                y.EventStartTimeUTC)
            )
        return
    def _to_localtime(self, secs_utc):
        if secs_utc in [MAXTIME, None]:
            # No conversion necessary.
            return secs_utc
        offset_from_utc = self.utc - self.localtime
        return secs_utc - (offset_from_utc)
    def __getattr__(self, name):
        try:
            attr = self.__dict__[name]
        except KeyError:
            # Delegate to the active event object.  
            # If no other events are scheduled, then this
            # will be the "Null Event".
            attr = getattr(self.__dict__['_events'][0], name)
        return attr
    def __get_pending_count(self):
        return len([x for x in self._events if (x.EventPending or x.EventActive)])
    PendingEventsCount = property(__get_pending_count)
    def __utc_time(self):
        if self.__utctime_node is None:
            self.__utctime_node = as_node('/services/time/UTC')
        return self.__utctime_node.get()
    utc = property(__utc_time)
    def __local_time(self):
        if self.__localtime_node is None:
            self.__localtime_node = as_node('/services/time/local')
        return self.__localtime_node.get()
    localtime = property(__local_time)
    def __get_debug(self):
        return self.parent.debug
    debug = property(__get_debug)
        
class DREventProperty(CompositeNode):
    def __init__(self):
        self.__cached_result = Result(None, 0, 0, 0)
        super(DREventProperty, self).__init__()
        return
    def configure(self, cd):
        super(DREventProperty, self).configure(cd)
        # Supported Event prop_types:
        #   * EventID
        #   * SiteCode
        #   * EventCode
        #   * ActionLevelCode
        #   * EventStartTimeUTC
        #   * EventEndTimeUTC
        #   * EventMaxEndTimeUTC
        #   * EventStartTimeLocal
        #   * EventEndTimeLocal
        #   * EventMaxEndTimeLocal
        #   * EventStartsIn
        #   * EventPending
        #   * EventActive
        #   * PendingEventsCount
        set_attribute(self, 'prop_type', self.name, cd)
        return
    def configuration(self):
        cd = super(DREventProperty, self).configuration()
        get_attribute(self, 'prop_type', cd)
        return cd
    def get(self, skipCache=0):
        return self.get_result(skipCache).value
    def get_result(self, skipCache=0):
        value = getattr(self.parent, self.prop_type)
        if value != self.__cached_result.value:
            self.__cached_result = Result(
                    value, 
                    time.time(), 
                    0, 
                    self.__cached_result.changes+1
                )
        return self.__cached_result
        
""" Misc Notes and example transactions follow:

Took 0.00264692306519 seconds to load pickled Formation
>>> 
>>> 
>>> 
>>> from mpx.lib.node import as_node
>>> ec = as_node('/services/EnergyConnect')
>>> u = stringType('user id 1', 'userName')
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
NameError: name 'stringType' is not defined
>>> p = stringType('pwd 1', 'password')
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
NameError: name 'stringType' is not defined
>>> s = stringType('simon002', 'siteID')
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
NameError: name 'stringType' is not defined
>>> 
>>> from SOAPpy.Types import *
>>> 
>>> u = stringType('user id 1', 'userName')
>>> p = stringType('pwd 1', 'password')
>>> s = stringType('simon002', 'siteID')
>>> ec._proxy.soapproxy.config=1
>>> ec.GetEventNotification(u,p,s)
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  File "/usr/lib/broadway/mpx/lib/soap/soap_proxy.py", line 42, in __call__
    results = getattr(self.__target, self.__name)(*args, **keywords)
  File "/usr/lib/python2.2/site-packages/SOAPpy/Client.py", line 470, in __call__
    return self.__r_call(*args, **kw)
  File "/usr/lib/python2.2/site-packages/SOAPpy/Client.py", line 492, in __r_call
    self.__hd, self.__ma)
  File "/usr/lib/python2.2/site-packages/SOAPpy/Client.py", line 354, in __call
    config = self.config, noroot = self.noroot)
  File "/usr/lib/python2.2/site-packages/SOAPpy/SOAPBuilder.py", line 635, in buildSOAP
    return t.build()
  File "/usr/lib/python2.2/site-packages/SOAPpy/SOAPBuilder.py", line 109, in build
    typed = self.config.typed
AttributeError: 'int' object has no attribute 'typed'
>>> 
Unhandled exception in thread:
Traceback (most recent call last):
  File "/opt/pkg/usr/lib/python2.2/threading.py", line 423, in __bootstrap
  File "/opt/pkg/usr/lib/python2.2/threading.py", line 432, in __stop
  File "/opt/pkg/usr/lib/python2.2/threading.py", line 242, in notifyAll
  File "/opt/pkg/usr/lib/python2.2/threading.py", line 224, in notify
TypeError: 'NoneType' object is not callable
watchdog: Signaling children to exit.
watchdog: Waiting for children to exit:...done.
[root@bert mpxadmin]$ /etc/rc.mfw -i
watchdog: Starting child process.
/usr/lib/broadway/mpx/system/system.py:207: DeprecationWarning: mpx.service.aliases.factory has been deprecated, please use mpx.lib.node.Aliases
Took 0.00259590148926 seconds to load pickled Formation
>>> import SOAPpy
>>> from SOAPpy.Types import *
>>> from mpx.lib.node import as_node
>>> 
>>> ec = as_node('/services/EnergyConnect')
>>> ec._proxy.soapproxy.config.debug = 1
>>> u = stringType('user id 1', 'userName')
>>> p = stringType('pwd 1', 'password')
>>> s = stringType('simon002', 'siteID')
>>> r = ec.GetEventNotification(u,p,s)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV'}
In dump. obj= <SOAPpy.Types.stringType siteID at 138342052>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType siteID at 138342052> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV'}
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 623
SOAPAction: "http://eservices.energyconnectinc.com/GetEventNotification"
************************************************************************

*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<GetEventNotification SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<siteID xsi:type="xsd:string">simon002</siteID>
</GetEventNotification>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:03:34 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 430

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>2007</GetEventNotificationResult><eventNotificationCount>0</eventNotificationCount><eventCollection/></GetEventNotificationResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:03:34 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 430
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>2007</GetEventNotificationResult><eventNotificationCount>0</eventNotificationCount><eventCollection/></GetEventNotificationResponse></s:Body></s:Envelope>
************************************************************************
>>> 
>>> ec._proxy.methods()
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
TypeError: 'dict' object is not callable
>>> eventnamespace = 'http://eservices.energyconnectinc.com/'
>>> for m in ec._proxy.methods.values():
...     print m.namespace
... 
None
None
>>> for m in ec._proxy.methods.values():
...     m.namespace = eventnamespace
... 
>>> r = ec.GetEventNotification(u,p,s)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType siteID at 138342052>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType siteID at 138342052> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 682
SOAPAction: "http://eservices.energyconnectinc.com/GetEventNotification"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<ns1:GetEventNotification xmlns:ns1="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<siteID xsi:type="xsd:string">simon002</siteID>
</ns1:GetEventNotification>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:06:02 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 430

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>2007</GetEventNotificationResult><eventNotificationCount>0</eventNotificationCount><eventCollection/></GetEventNotificationResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:06:02 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 430
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>2007</GetEventNotificationResult><eventNotificationCount>0</eventNotificationCount><eventCollection/></GetEventNotificationResponse></s:Body></s:Envelope>
************************************************************************
>>> s
<SOAPpy.Types.stringType siteID at 138342052>
>>> s._data
'simon002'
>>> s._data = 'simon003'
>>> r = ec.GetEventNotification(u,p,s)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType siteID at 138342052>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType siteID at 138342052> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 682
SOAPAction: "http://eservices.energyconnectinc.com/GetEventNotification"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<ns1:GetEventNotification xmlns:ns1="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<siteID xsi:type="xsd:string">simon003</siteID>
</ns1:GetEventNotification>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:06:43 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 430

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>2007</GetEventNotificationResult><eventNotificationCount>0</eventNotificationCount><eventCollection/></GetEventNotificationResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:06:43 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 430
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>2007</GetEventNotificationResult><eventNotificationCount>0</eventNotificationCount><eventCollection/></GetEventNotificationResponse></s:Body></s:Envelope>
************************************************************************
>>> 
>>> 
>>> m
<SOAPpy.wstools.WSDLTools.SOAPCallInfo instance at 0x8bebfcc>
>>> m.namespace
'http://eservices.energyconnectinc.com/'
>>> c = ec._proxy.soapproxy.config
>>> c.buildWithNamespacePrefix
1
>>> c.buildWithNamespacePrefix = 0
>>> r = ec.GetEventNotification(u,p,s)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType siteID at 138342052>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType siteID at 138342052> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 670
SOAPAction: "http://eservices.energyconnectinc.com/GetEventNotification"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<GetEventNotification xmlns="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<siteID xsi:type="xsd:string">simon003</siteID>
</GetEventNotification>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:10:44 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 1153

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>1000</GetEventNotificationResult><eventNotificationCount>2</eventNotificationCount><eventCollection><EventNotifications><EventNotification><EventNotification><EventID>ffd61f28-3444-4b88-9b94-b3f44ae580e5</EventID><SiteCode>simon003</SiteCode><EventCode>ILR_Start</EventCode><ActionLevelCode>Red</ActionLevelCode><EventStartTimeUTC>2008-06-20T13:00:00Z</EventStartTimeUTC><EventMaxEndTimeUTC>2008-06-20T17:00:00Z</EventMaxEndTimeUTC></EventNotification><EventNotification><EventID>2ceca2b3-0a07-42b8-a063-4f5cb87fdd97</EventID><SiteCode>simon003</SiteCode><EventCode>ILR_Start</EventCode><ActionLevelCode>Red</ActionLevelCode><EventStartTimeUTC>2008-06-21T13:00:00Z</EventStartTimeUTC><EventMaxEndTimeUTC>2008-06-21T17:00:00Z</EventMaxEndTimeUTC></EventNotification></EventNotification></EventNotifications></eventCollection></GetEventNotificationResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:10:44 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 1153
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><GetEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/"><GetEventNotificationResult>1000</GetEventNotificationResult><eventNotificationCount>2</eventNotificationCount><eventCollection><EventNotifications><EventNotification><EventNotification><EventID>ffd61f28-3444-4b88-9b94-b3f44ae580e5</EventID><SiteCode>simon003</SiteCode><EventCode>ILR_Start</EventCode><ActionLevelCode>Red</ActionLevelCode><EventStartTimeUTC>2008-06-20T13:00:00Z</EventStartTimeUTC><EventMaxEndTimeUTC>2008-06-20T17:00:00Z</EventMaxEndTimeUTC></EventNotification><EventNotification><EventID>2ceca2b3-0a07-42b8-a063-4f5cb87fdd97</EventID><SiteCode>simon003</SiteCode><EventCode>ILR_Start</EventCode><ActionLevelCode>Red</ActionLevelCode><EventStartTimeUTC>2008-06-21T13:00:00Z</EventStartTimeUTC><EventMaxEndTimeUTC>2008-06-21T17:00:00Z</EventMaxEndTimeUTC></EventNotification></EventNotification></EventNotifications></eventCollection></GetEventNotificationResponse></s:Body></s:Envelope>
************************************************************************
>>> r
{'eventNotificationCount': '2', 'eventCollection': {'EventNotifications': {'EventNotification': {'EventNotification': [{'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}, {'EventID': '2ceca2b3-0a07-42b8-a063-4f5cb87fdd97', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-21T13:00:00Z', 'EventCode': 'ILR_Start', 'EventMaxEndTimeUTC': '2008-06-21T17:00:00Z', 'SiteCode': 'simon003'}]}}}, 'GetEventNotificationResult': '1000'}
>>> 
>>> 
>>> 
>>> def get_events(response):
...     event_list = response.eventCollection.EventNotifications.EventNotification.EventNotification
...     if not isinstance(event_list, list):
...         event_list = [event_list]
...     return event_list
... 
>>> def get_event_details(event):
...     details = {'EventID':None,
...                'SiteCode':None,
...                'EventCode':None,
...                'ActionLevelCode':None,
...                'EventStartTimeUTC':None,
...                'EventEndTimeUTC':None,
...                'EventMaxEndTimeUTC':None}
...     for k in details.keys():
...         if hasattr(event, k):
...             details[k] = event[k]
...     return details
... 
>>> 
>>> 
>>> def bld_enr(event_details, response_code):
...     inner_enr = SOAPpy.Types.structType()
...     inner_enr._name = 'EventNotificationResponse'
...     for k in event_details:
...         if event_details[k] is not None:
...             inner_enr._addItem(k, event_details[k])
...     inner_enr._addItem('ResponseCode', response_code)
...     outer_enr = SOAPpy.Types.structType()
...     outer_enr._name = 'EventNotificationResponse'
...     outer_enr._addItem('EventNotificationResponse', inner_enr)
...     
...     enr_array = SOAPpy.Types.structType()
...     enr_array._name = 'EventNotificationResponses'
...     enr_array._addItem('EventNotificationResponse', outer_enr)
...     
...     ec = SOAPpy.Types.structType()
...     ec._name = 'eventResponseCollection'
...     ec._addItem('EventNotificationResponses', enr_array)
...     return ec
...     
... 
>>> 
>>> ec
<opt.energyconnect.Endpoint object at 0x88c4734>
>>> e = get_events(r)[0]
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  File "<stdin>", line 2, in get_events
AttributeError: 'dict' object has no attribute 'eventCollection'
>>> e
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
NameError: name 'e' is not defined
>>> r
{'eventNotificationCount': '2', 'eventCollection': {'EventNotifications': {'EventNotification': {'EventNotification': [{'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}, {'EventID': '2ceca2b3-0a07-42b8-a063-4f5cb87fdd97', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-21T13:00:00Z', 'EventCode': 'ILR_Start', 'EventMaxEndTimeUTC': '2008-06-21T17:00:00Z', 'SiteCode': 'simon003'}]}}}, 'GetEventNotificationResult': '1000'}
>>> type(r)
<type 'dict'>
>>> 
>>> def get_events(response):
...     #event_list = response.eventCollection.EventNotifications.EventNotification.EventNotification
...     event_list = response['eventCollection']['EventNotifications']['EventNotification']['EventNotification']
...     if not isinstance(event_list, list):
...         event_list = [event_list]
...     return event_list
... 
>>> e = get_events(r)[0]
>>> e
{'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}
>>> r = bld_enr(e, '100')
>>> r
<SOAPpy.Types.structType eventResponseCollection at 1077951204>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077951060>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}}}
>>> r
<SOAPpy.Types.structType eventResponseCollection at 1077951204>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077951060>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}}}
>>> c = intType(1, 'eventNotificationResponseCount')
>>> c
<SOAPpy.Types.intType eventNotificationResponseCount at 1077950764>
>>> c._data
1
>>> ec.SendEventNotificationResponse(u,p,c,r)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType eventResponseCollection at 1077951204>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077951060>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}}}
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.structType eventResponseCollection at 1077951204>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077951060>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}}} tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077951060>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}}
In dump. tag= EventNotificationResponses
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077951060>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}} tag= EventNotificationResponses ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://eservices.energyconnectinc.com/': 'ns1', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077963028>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077972468>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ActionLevelCode': 'Red', 'EventStartTimeUTC': '2008-06-20T13:00:00Z', 'EventCode': 'ILR_Start', 'ResponseCode': '100', 'EventMaxEndTimeUTC': '2008-06-20T17:00:00Z', 'SiteCode': 'simon003'} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://eservices.energyconnectinc.com/': 'ns1', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd'}
In dump. obj= ffd61f28-3444-4b88-9b94-b3f44ae580e5
In dump. tag= EventID
In dump_string.
In dumper.
In dump. obj= Red
In dump. tag= ActionLevelCode
In dump_string.
In dumper.
In dump. obj= 2008-06-20T13:00:00Z
In dump. tag= EventStartTimeUTC
In dump_string.
In dumper.
In dump. obj= ILR_Start
In dump. tag= EventCode
In dump_string.
In dumper.
In dump. obj= 2008-06-20T17:00:00Z
In dump. tag= EventMaxEndTimeUTC
In dump_string.
In dumper.
In dump. obj= simon003
In dump. tag= SiteCode
In dump_string.
In dumper.
In dump. obj= 100
In dump. tag= ResponseCode
In dump_string.
In dumper.
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 1503
SOAPAction: "http://eservices.energyconnectinc.com/SendEventNotificationResponse"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsd2="http://www.w3.org/2000/10/XMLSchema"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<SendEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<eventNotificationResponseCount xsi:type="xsd2:int">1</eventNotificationResponseCount>
<xsd:eventResponseCollection>
<xsd:EventNotificationResponses>
<xsd:EventNotificationResponse>
<xsd:EventNotificationResponse>
<EventID xsi:type="xsd:string">ffd61f28-3444-4b88-9b94-b3f44ae580e5</EventID>
<ActionLevelCode xsi:type="xsd:string">Red</ActionLevelCode>
<EventStartTimeUTC xsi:type="xsd:string">2008-06-20T13:00:00Z</EventStartTimeUTC>
<EventCode xsi:type="xsd:string">ILR_Start</EventCode>
<EventMaxEndTimeUTC xsi:type="xsd:string">2008-06-20T17:00:00Z</EventMaxEndTimeUTC>
<SiteCode xsi:type="xsd:string">simon003</SiteCode>
<ResponseCode xsi:type="xsd:string">100</ResponseCode>
</xsd:EventNotificationResponse>
</xsd:EventNotificationResponse>
</xsd:EventNotificationResponses>
</xsd:eventResponseCollection>
</SendEventNotificationResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:17:08 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>2000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:17:08 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>2000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
************************************************************************
'2000'
>>> 
>>> 
>>> 
>>> 
>>> 
>>> def bld_enr(event_details, response_code):
...     inner_enr = SOAPpy.Types.structType()
...     inner_enr._name = 'EventNotificationResponse'
...     for k in event_details:
...         #if event_details[k] is not None:
...         if k in ['EventID', 'SiteCode', 'ResponseCode']:
...             inner_enr._addItem(k, event_details[k])
...     inner_enr._addItem('ResponseCode', response_code)
...     outer_enr = SOAPpy.Types.structType()
...     outer_enr._name = 'EventNotificationResponse'
...     outer_enr._addItem('EventNotificationResponse', inner_enr)
...     
...     enr_array = SOAPpy.Types.structType()
...     enr_array._name = 'EventNotificationResponses'
...     enr_array._addItem('EventNotificationResponse', outer_enr)
...     
...     ec = SOAPpy.Types.structType()
...     ec._name = 'eventResponseCollection'
...     ec._addItem('EventNotificationResponses', enr_array)
...     return ec
...     
... 
>>> r = bld_enr(e, '100')
>>> r
<SOAPpy.Types.structType eventResponseCollection at 1077942356>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}}
>>> 
>>> r
<SOAPpy.Types.structType eventResponseCollection at 1077942356>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}}
>>> dir(r)
['EventNotificationResponses', '__doc__', '__getitem__', '__init__', '__len__', '__module__', '__nonzero__', '__repr__', '__str__', '_addItem', '_asdict', '_aslist', '_attrs', '_cache', '_checkValueSpace', '_data', '_fixAttr', '_getActor', '_getAttr', '_getItemAsList', '_getMustUnderstand', '_keyord', '_keys', '_marshalAttrs', '_marshalData', '_name', '_ns', '_placeItem', '_setActor', '_setAttr', '_setAttrs', '_setMustUnderstand', '_type', '_typeName', '_typed', '_validNamespaceURI', '_validURIs']
>>> r._type
'struct'
>>> r._typed
1
>>> ec.SendEventNotificationResponse(u,p,c,r)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType eventResponseCollection at 1077942356>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}}
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.structType eventResponseCollection at 1077942356>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}} tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}
In dump. tag= EventNotificationResponses
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}} tag= EventNotificationResponses ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://eservices.energyconnectinc.com/': 'ns1', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://eservices.energyconnectinc.com/': 'ns1', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd'}
In dump. obj= ffd61f28-3444-4b88-9b94-b3f44ae580e5
In dump. tag= EventID
In dump_string.
In dumper.
In dump. obj= simon003
In dump. tag= SiteCode
In dump_string.
In dumper.
In dump. obj= 100
In dump. tag= ResponseCode
In dump_string.
In dumper.
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 1221
SOAPAction: "http://eservices.energyconnectinc.com/SendEventNotificationResponse"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsd2="http://www.w3.org/2000/10/XMLSchema"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<SendEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<eventNotificationResponseCount xsi:type="xsd2:int">1</eventNotificationResponseCount>
<xsd:eventResponseCollection>
<xsd:EventNotificationResponses>
<xsd:EventNotificationResponse>
<xsd:EventNotificationResponse>
<EventID xsi:type="xsd:string">ffd61f28-3444-4b88-9b94-b3f44ae580e5</EventID>
<SiteCode xsi:type="xsd:string">simon003</SiteCode>
<ResponseCode xsi:type="xsd:string">100</ResponseCode>
</xsd:EventNotificationResponse>
</xsd:EventNotificationResponse>
</xsd:EventNotificationResponses>
</xsd:eventResponseCollection>
</SendEventNotificationResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:23:01 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>2000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:23:01 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>2000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
************************************************************************
'2000'
>>> 
>>> 
>>> r._typed  
1
>>> r._typed = 0
>>> r._typed
0
>>> ec.SendEventNotificationResponse(u,p,c,r)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType eventResponseCollection at 1077942356>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}}
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.structType eventResponseCollection at 1077942356>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}} tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}
In dump. tag= EventNotificationResponses
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077943684>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}} tag= EventNotificationResponses ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077940588>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://eservices.energyconnectinc.com/': 'ns1', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077955212>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://www.w3.org/1999/XMLSchema': 'xsd', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= ffd61f28-3444-4b88-9b94-b3f44ae580e5
In dump. tag= EventID
In dump_string.
In dumper.
In dump. obj= simon003
In dump. tag= SiteCode
In dump_string.
In dumper.
In dump. obj= 100
In dump. tag= ResponseCode
In dump_string.
In dumper.
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 1213
SOAPAction: "http://eservices.energyconnectinc.com/SendEventNotificationResponse"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsd2="http://www.w3.org/2000/10/XMLSchema"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<SendEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<eventNotificationResponseCount xsi:type="xsd2:int">1</eventNotificationResponseCount>
<eventResponseCollection>
<xsd:EventNotificationResponses>
<xsd:EventNotificationResponse>
<xsd:EventNotificationResponse>
<EventID xsi:type="xsd:string">ffd61f28-3444-4b88-9b94-b3f44ae580e5</EventID>
<SiteCode xsi:type="xsd:string">simon003</SiteCode>
<ResponseCode xsi:type="xsd:string">100</ResponseCode>
</xsd:EventNotificationResponse>
</xsd:EventNotificationResponse>
</xsd:EventNotificationResponses>
</eventResponseCollection>
</SendEventNotificationResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:24:33 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>2000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:24:33 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>2000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
************************************************************************
'2000'
>>> 
>>> 
>>> 
>>> 
>>> def bld_enr(event_details, response_code):
...     inner_enr = SOAPpy.Types.structType(typed=0)
...     inner_enr._name = 'EventNotificationResponse'
...     for k in event_details:
...         #if event_details[k] is not None:
...         if k in ['EventID', 'SiteCode', 'ResponseCode']:
...             inner_enr._addItem(k, event_details[k])
...     inner_enr._addItem('ResponseCode', response_code)
...     outer_enr = SOAPpy.Types.structType(typed=0)
...     outer_enr._name = 'EventNotificationResponse'
...     outer_enr._addItem('EventNotificationResponse', inner_enr)
...     
...     enr_array = SOAPpy.Types.structType(typed=0)
...     enr_array._name = 'EventNotificationResponses'
...     enr_array._addItem('EventNotificationResponse', outer_enr)
...     
...     ec = SOAPpy.Types.structType(typed=0)
...     ec._name = 'eventResponseCollection'
...     ec._addItem('EventNotificationResponses', enr_array)
...     return ec
... 
>>> r = bld_enr(e, '100')
>>> r
<SOAPpy.Types.structType eventResponseCollection at 1077961020>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077968964>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}}
>>> ec.SendEventNotificationResponse(u,p,c,r)
In build.
In dump. obj= <SOAPpy.Types.stringType userName at 138436236>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType userName at 138436236> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.stringType password at 138437500>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.stringType password at 138437500> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764>
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.intType eventNotificationResponseCount at 1077950764> tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType eventResponseCollection at 1077961020>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077968964>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}}
In dump. tag= None
In dump_instance. obj= <SOAPpy.Types.structType eventResponseCollection at 1077961020>: {'EventNotificationResponses': <SOAPpy.Types.structType EventNotificationResponses at 1077968964>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}} tag= None ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077968964>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}}
In dump. tag= EventNotificationResponses
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponses at 1077968964>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}} tag= EventNotificationResponses ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077948772>: {'EventNotificationResponse': <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'}
In dump. tag= EventNotificationResponse
In dump_instance. obj= <SOAPpy.Types.structType EventNotificationResponse at 1077952748>: {'EventID': 'ffd61f28-3444-4b88-9b94-b3f44ae580e5', 'ResponseCode': '100', 'SiteCode': 'simon003'} tag= EventNotificationResponse ns_map= {'http://schemas.xmlsoap.org/soap/encoding/': 'SOAP-ENC', 'http://schemas.xmlsoap.org/soap/envelope/': 'SOAP-ENV', 'http://eservices.energyconnectinc.com/': 'ns1'}
In dump. obj= ffd61f28-3444-4b88-9b94-b3f44ae580e5
In dump. tag= EventID
In dump_string.
In dumper.
In dump. obj= simon003
In dump. tag= SiteCode
In dump_string.
In dumper.
In dump. obj= 100
In dump. tag= ResponseCode
In dump_string.
In dumper.
*** Outgoing HTTP headers **********************************************
POST /EventCacheService/EventCacheService.svc HTTP/1.0
Host: 166.139.96.132
User-agent: SOAPpy 0.12.0 (http://pywebsvcs.sf.net)
Content-type: text/xml; charset="UTF-8"
Content-length: 1189
SOAPAction: "http://eservices.energyconnectinc.com/SendEventNotificationResponse"
************************************************************************
*** Outgoing SOAP ******************************************************
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
  SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsd2="http://www.w3.org/2000/10/XMLSchema"
  xmlns:xsi="http://www.w3.org/1999/XMLSchema-instance"
  xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:xsd="http://www.w3.org/1999/XMLSchema"
>
<SOAP-ENV:Body>
<SendEventNotificationResponse xmlns="http://eservices.energyconnectinc.com/" SOAP-ENC:root="1">
<userName xsi:type="xsd:string">user id 1</userName>
<password xsi:type="xsd:string">pwd 1</password>
<eventNotificationResponseCount xsi:type="xsd2:int">1</eventNotificationResponseCount>
<eventResponseCollection>
<EventNotificationResponses>
<EventNotificationResponse>
<EventNotificationResponse>
<EventID xsi:type="xsd:string">ffd61f28-3444-4b88-9b94-b3f44ae580e5</EventID>
<SiteCode xsi:type="xsd:string">simon003</SiteCode>
<ResponseCode xsi:type="xsd:string">100</ResponseCode>
</EventNotificationResponse>
</EventNotificationResponse>
</EventNotificationResponses>
</eventResponseCollection>
</SendEventNotificationResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>
************************************************************************
code= 200
msg= OK
headers= Connection: close
Date: Thu, 19 Jun 2008 21:26:21 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398

content-type= text/xml; charset=utf-8
data= <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>1000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
*** Incoming HTTP headers **********************************************
HTTP/1.? 200 OK
Connection: close
Date: Thu, 19 Jun 2008 21:26:21 GMT
Server: Microsoft-IIS/6.0
X-Powered-By: ASP.NET
X-AspNet-Version: 2.0.50727
Cache-Control: private
Content-Type: text/xml; charset=utf-8
Content-Length: 398
************************************************************************
*** Incoming SOAP ******************************************************
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SendEventNotificationResponseResponse xmlns="http://eservices.energyconnectinc.com/"><SendEventNotificationResponseResult>1000</SendEventNotificationResponseResult></SendEventNotificationResponseResponse></s:Body></s:Envelope>
************************************************************************
'1000'
>>> r = _
>>> r
'1000'
>>> 
"""
        
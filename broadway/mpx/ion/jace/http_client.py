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
from mpx.lib.node import CompositeNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.threading import Lock
from mpx.lib.threading import Condition
from mpx.lib.threading import ImmortalThread

from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import Exception

from mpx.service.network.async.message.request import Request
from mpx.service.network.async.connection import monitor
from mpx.service.network.async.connection.channel import Channel

from mpx.service.network.utilities.counting import Counter

from mpx.lib import Result
from mpx.lib import msglog

from mpx.lib.msglog.types import INFO
from mpx.lib.msglog.types import WARN

from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent

from mpx.lib.thread_pool import ThreadPool

from moab.linux.lib import uptime

from Queue import Queue as _Queue
from Queue import Empty
import base64
import cStringIO
import time
import sys

TESTING_THROTTLE = 0
BACKLOGGED_LIMIT = 10
PYTHON_VERSION = tuple(map(int, sys.version.split(' ')[0].split('.')))
MAJOR = 0
MINOR = 1
BASE_URL = 'http://%s/prism/xml%s'
debug = 1

class Queue(_Queue):
    ##
    # The Queue.Queue.get() api changed between 2.2 and 2.5.
    # 2.5 supports an optional timeout to the blocking get()
    def __init__(self, *args):
        _Queue.__init__(self, *args)
        if PYTHON_VERSION[MAJOR] > 2 or PYTHON_VERSION[MINOR] > 2:
            self.__legacy = False
        else:
            self.__legacy = True
        return
    def get(self, block=True, timeout=None):
        if not self.__legacy:
            return _Queue.get(self, block, timeout)
        # 2.2
        if block and timeout is None:
            #block indefinitely
            #return super(Queue, self).get()
            _Queue.get(self)
        if timeout:
            endtime = uptime.secs() + timeout
            while not self.qsize():
                remaining = endtime - uptime.secs()
                if remaining <= 0.0:
                    break
        ##
        # we've either timed out or data is available.
        # either immediately return the data or raise Queue.Empty
        #return super(Queue, self).get(False)
        return _Queue.get(self, False)
##
# This module to be refactored to rely on generic 
# services.network.async Transaction and TransactionManager
# support.
class Transaction(object):
    def __init__(self, tm, channel=None, callback=None):
        self._id = id(self)
        self._request_count = 0
        self.tm = tm
        self.set_channel(channel)
        self.set_callback(callback)
        self.send_time = None
        return
    def set_request(self, request):
        self.request = request
        return
    def set_channel(self, channel):
        self.channel = channel
        return
    def set_timeout(self, timeout):
        self.timeout = timeout
        return
    def completion_handler(self, cb):
        try:
            if self._callback:
                self._callback(self)
        except:
            msglog.exception(prefix = 'Handled')
        return
    def set_callback(self, callback):
        self._callback = callback
        return
    def remove_callback(self):
        self._callback = None
        return
    def build_request(self, url, data=None, headers={}, version='HTTP/1.1'):
        request = Request(url, data, headers, version)
        request.add_header('Host', request.get_host())
        request.add_state_listener(self.completion_handler)
        self.set_request(request)
        self._request_count += 1
        return request
    def send_request(self):
        channel = Channel(self.tm._monitor)
        self.set_channel(channel)
        channel.socket = None
        channel.setup_connection(
            self.request.get_host(),
            self.request.get_port(),
            self.request.get_type()
            )
        channel.send_request(self.request)
        self.send_time = uptime.secs()
        return
    def request_sent(self):
        return self.send_time is not None
    def request_age(self):
        return uptime.secs() - self.send_time
    def has_response(self):
        return self.request.has_response()
    def get_response(self):
        return self.request.get_response()
    def is_complete(self):
        if not self.request.has_response():
            return False
        response = self.request.get_response()
        return response.is_complete()
    def is_expired(self):
        try:
            return self.request_age() > self.timeout
        except:
            return True
    def succeeded(self):
        return self.is_complete() and self.get_response().handled_properly()
    def reset(self):
        self.channel.reset_channel()
        return
    def cancel(self):
        msglog.log('broadway', WARN, '%r closing channel' % self)
        try: 
            self.channel.close()
        except:
            msglog.exception(prefix = 'Handled')
        return
    def __get_tid(self):
        return (self._id, self._request_count)
    tid = property(__get_tid)
##
# Singleton to manage access to network of Jaces
class TransactionManager(object):
    __instance = None
    def __init__(self, timeout=2.0):
        if TransactionManager.__instance is None:
            TransactionManager.__instance = TransactionManager.__impl(timeout)
            self.__dict__['_TransactionManager__instance'] = TransactionManager.__instance
            self.__instance.start()
        return
    def __getattr__(self, attr):
        # Delegate to implementation
        return getattr(self.__instance, attr)
    def __setattr__(self, attr, value):
        # Delegate to implementation
        return setattr(self.__instance, attr, value)
    class __impl(ImmortalThread):
        tm_counter = Counter(0)
        def __init__(self, timeout=2.0):
            self.timeout = timeout
            self.stations = {}
            self._monitor = monitor.ChannelMonitor(self.timeout)
            self.tm_number = self.tm_counter.increment()
            self._response_tp = ThreadPool(1, 'Jace Response Pool')
            self._pending_responses = Queue()
            self._callbacks = {}
            self._running = False
            self._sync_get_lock = Lock()
            self._last_sync_get = uptime.secs()
            self._cv = Condition()
            ImmortalThread.__init__(self, None, None, 'Jace Transaction Manager')
            return
        def start(self):
            if not self._monitor.is_running():
                self._monitor.start_monitor()
            self._running = True
            self._synchronous_transaction = Transaction(self, None, self._bump_cv)
            self._synchronous_transaction.set_timeout(self.timeout)
            ImmortalThread.start(self)
            return
        def stop(self):
            msglog.log('Jace', INFO, 'Stop Jace Prism Transaction Manger')
            if self._monitor.is_running():
                self._monitor.stop_monitor()
            self._running = False
            return
        def run(self):
            msglog.log('Jace', INFO, 'Starting Jace Prism Transaction Manger.')
            while self._running:
                try:
                    self.send_loop()
                    self.response_loop()
                except:
                    msglog.log('Jace', WARN, 'Jace Transaction Manager - error sending next.')
                    msglog.exception()
            return
        def transaction_completion_handler(self, transaction):
            self.tm_number = self.tm_counter.increment()
            try:
                tid = transaction.tid
                s_id, callback = self._callbacks.get(tid)
                if callback:
                    del self._callbacks[tid]
                    self._pending_responses.put((callback, transaction.get_response()))
            except:
                msglog.exception()
            # recycle the transaction for reuse within the queue
            self.stations.get(s_id).put_transaction(transaction)
            return
        def add_station(self, station):
            s_id = station.get_id()
            self.stations[s_id] = station
            return
        def get_synchronous(self, station, rqst):
            self._sync_get_lock.acquire()
            try:
                t = self._synchronous_transaction
                hdr = self._get_auth_header(station)
                hdr['Connection'] = 'close'
                t.build_request(rqst.url, None, hdr)
                self._cv.acquire()
                try:
                    response = ETimeout()
                    try:
                        t.send_request()
                        self._cv.wait(self.timeout)
                        self._last_sync_get = uptime.secs()
                        if t.is_expired():
                            t.cancel()
                        else:
                            response = t.get_response()
                    except:
                        t.cancel()
                finally:
                    self._cv.release()
                return response
            finally:
                self._sync_get_lock.release()
            return
        def _bump_cv(self, transaction):
            # transaction isn't used
            self._cv.acquire()
            self._cv.notify()
            self._cv.release()
            return
        def send_loop(self):
            for s_id, station in self.stations.items():
                for i in range(station.transaction_limit):
                    try:
                        t, rqst = station.get_next()
                    except Empty:
                        break
                    hdr = self._get_auth_header(station)
                    hdr['Connection'] = 'close'
                    t.build_request(rqst.url, None, hdr)
                    self._callbacks[t.tid] = (s_id, rqst.callback)
                    t.send_request()
            return
        def response_loop(self):
            while 1:
                try:
                    callback, rsp = self._pending_responses.get(False)
                    callback(rsp)
                except Empty:
                    return
                except:
                    msglog.log('Jace', WARN, 'Unexpected error in response_loop')
                    msglog.exception()
            return
        def _get_auth_header(self, station):
            return {"Authorization":
                    "Basic %s" % station.base64string}
                    
class JaceRequest(object):
    def __init__(self, url, last_update=0.0, ttl=None, callback=None):
        self.url = url
        self.last_update = last_update
        self.ttl = ttl
        self.callback = callback
        return
    def set_last_update(self, last_update):
        self.last_update = last_update
        return
    def set_callback(self, callback):
        self.callback = callback
        return
        
class Station(CompositeNode):
    def __init__(self):
        self._base64string = None
        self._group_lock = Lock()
        self._request_q = Queue()
        self._transaction_q = Queue()
        self._backed_up = False
        self.__s_id = id(self)
        super(Station, self).__init__()
        return
    def configure(self, cd):
        super(Station, self).configure(cd)
        set_attribute(self, 'host', REQUIRED, cd)
        set_attribute(self, 'port', 80, cd, int)
        set_attribute(self, 'connection_type', 'http', cd)
        set_attribute(self, 'user', REQUIRED, cd)
        set_attribute(self, 'password', REQUIRED, cd)
        set_attribute(self, 'timeout', 2.0, cd, int)
        set_attribute(self, 'transaction_limit', 2, cd, int)
        # reset _base64string - just in case user\password changed
        self._base64string = None
        return
    def configuration(self):
        cd = super(Station, self).configuration()
        get_attribute(self, 'host', cd)
        get_attribute(self, 'port', cd)
        get_attribute(self, 'connection_type', cd)
        get_attribute(self, 'user', cd)
        get_attribute(self, 'password', cd)
        get_attribute(self, 'timeout', cd)
        get_attribute(self, 'transaction_limit', cd)
        return cd
    def start(self):
        self.tm = TransactionManager()
        self.tm.add_station(self)
        self._setup_transactions()
        super(Station, self).start()
        return
    def _setup_transactions(self):
        self._transactions = []
        for i in range(self.transaction_limit):
            t = self._setup_transaction(self.tm.transaction_completion_handler)
            t.set_timeout(self.timeout)
            self._transaction_q.put(t)
            self._transactions.append(t)
        return
    def _setup_transaction(self, callback):
        t = Transaction(self.tm, None, callback)
        t.set_timeout(self.timeout)
        return t
    def put_request(self, rqst):
        self._request_q.put(rqst)
        return
    def put_transaction(self, transaction):
        self._transaction_q.put(transaction)
        return
    def get_next(self):
        try:
            transaction = self._transaction_q.get(False)
            self._backed_up = False
        except Empty:
            if self._backed_up:
                self.recycle_expired_transactions()
                transaction = self._transaction_q.get(False)
            else:
                self._backed_up = True
                raise
        now = uptime.secs()
        fresh = []
        while 1:
            try:
                rqst = self._request_q.get(False)
                if (now - rqst.last_update) > rqst.ttl:
                    break
                fresh.append(rqst)
            except Empty:
                rqst = None
                break
        map(self._request_q.put, fresh)
        if rqst is None:    
            self.put_transaction(transaction)
            raise Empty                    
        return (transaction, rqst)
    def recycle_expired_transactions(self):
        cnt = 0
        for t in self._transactions:
            if t.is_expired():
                t.cancel()
                tid = t.tid
                try:
                    s_id, callback = self.tm._callbacks.get(tid)
                except:
                    # callback is gone
                    callback = None
                if callback:
                    try:
                        callback(ETimeout())
                    except:
                        msglog.exception(prefix = 'Handled')
                    del self.tm._callbacks[tid]
                cnt += 1
                self.put_transaction(t)
        return
    def add_request(self, rqst):
        if rqst.callback:
            self._request_q.put(rqst)
        else:
            return self.tm.get_synchronous(self, rqst)
    def get_id(self):
        return self.__s_id
    def _get_base64string(self):
        if self._base64string is None:
            self._base64string = base64.encodestring(
                '%s:%s' % (self.user, self.password)
            )[:-1]
        return self._base64string
    base64string = property(_get_base64string)
    
class ValueObj(object):
    def __init__(self, value):
        self.__value = value
        super(ValueObj, self).__init__()
        return
    def get(self, name):
        if isinstance(self.__value, dict):
            value = self.__value.get(name, None)
        else:
            value = getattr(self.__value, name, None)
        if value:
            value = fix_up_value(value.get_tag_value())
        return value

class UpdateMixin(object):
    def update_continuous(self, rsp):
        value = None
        if rsp is not None:
            if not isinstance(rsp, Exception):
                if not rsp.is_complete():
                    rsp.await_completion(self.station.timeout)
                rsp = rsp.read()
                value = self.decode(rsp)
            self.update_cache(ValueObj(value))
            if not self.event_has_subscribers():
                # don't keep on, keepin on.
                return
            self._rqst.set_last_update(uptime.secs())
        else:
            self._rqst.set_callback(self.update_continuous)
        self.station.add_request(self._rqst)
        return
    # a single-shot update
    def update(self):
        value = None
        rqst = JaceRequest(self.url)
        rsp = self.station.add_request(rqst)
        if not isinstance(rsp, Exception):
            if not rsp.is_complete():
                rsp.await_completion()
            rsp = rsp.read()
            value = self.decode(rsp)
        self.update_cache(ValueObj(value))
        return
    def decode(self):
        pass
    def update_cache(self):
        pass

class Device(CompositeNode, UpdateMixin):
    def __init__(self):
        self._subscription_lock = Lock()
        self._subscribed = 0
        self._subscribers = {}
        self._last_value = None
        self._last_rcvd = None
        self._decode_indexes = {}
        return
    def configure(self, cd):
        super(Device, self).configure(cd)
        set_attribute(self, 'ttl', 60, cd, int)
        set_attribute(self, 'swid', '', cd)
        return
    def configuration(self):
        cd = super(Device, self).configuration()
        get_attribute(self, 'ttl', cd)
        get_attribute(self, 'swid', cd)
        return cd
    def start(self):
        if self.swid:
            self.url = BASE_URL % (self.station.host, self.swid)
            self._rqst = JaceRequest(self.url, ttl=self.ttl)
        super(Device, self).start()
        return
    def can_bundle(self):
        return bool(self.swid)
    def subscribe(self, name, func):
        self._subscription_lock.acquire()
        try:
            ##
            # if there are multiple external consumers, they are subscribed
            # via event producing child node.
            self._subscribers[name] = func
            self._subscribed += 1
            if self._last_value and (uptime.secs() - self._last_rcvd) < self.ttl:
                try:
                    value = self._last_value.get(name)
                    func(value)
                except:
                    pass
            if self._subscribed == 1:
                self.update_continuous(None)
        finally:
            self._subscription_lock.release()
        return
    def unsubscribe(self, name):
        self._subscription_lock.acquire()
        try:
            assert self._subscribed, 'Cannot decrement subscribers below 0'
            del self._subscribed[name]
            self._subscribed -= 1
        finally:
            self._subscription_lock.release()
        return
    def event_has_subscribers(self):
        return bool(self._subscribed)
    def _load_indexes(self, data):
        d_len = len(data)
        for name in self._subscribers.keys():
            index = offset = 0
            for l in data:
                if l.count('<'+name+'>'):
                    break
                index += 1
            for l in data[index:]:
                if l.count('<value>'):
                    break
                offset += 1
            if (index+offset) > d_len:
                index = offset = None
            self._decode_indexes[name] = (index, offset)
        return
    def _get_indexes(self, name):
        return self._decode_indexes.get(name, (None, None))
    def _have_indexes(self):
        indexes = self._decode_indexes.keys()
        for interest in self._subscribers.keys():
            if interest not in indexes:
                return False
        return True
    def decode(self, data_s):
        if data_s.startswith('<!--'):
            data_s = data_s[(data_s[1:].find('<')+1):]
        data = data_s.split('\n')
        if not self._have_indexes():
            self._load_indexes(data)
        values = {}
        for name in self._subscribers.keys():
            index,offset = self._get_indexes(name)
            try:
                if not data[index].count(name) or not data[index+offset].count('value'):
                    return self._decode_slow(data_s)
                l = data[index+offset]
                values[name] = l.split('>')[1].split('<')[0]
            except:
                return self._decode_slow(data_s)
        return values
    def _decode_slow(self, data):
        try:
            data_o = xml2code(data)
        except:
            data_o = None
        return data_o
    def update_cache(self, value_obj):
        for name, func in self._subscribers.items():
            value = value_obj.get(name)
            func(value)
        self._last_value = value
        self._last_rcvd = uptime.secs()
        return
    def _get_station(self):
        return self.parent
    station = property(_get_station)
    
class DeviceProperty(CompositeNode, EventProducerMixin, UpdateMixin):
    _release_cmd_base = ''
    _ovrd_cmd_base = ''
    def __init__(self):
        # overridden by subclasses
        self._pv_index = None
        self._last_rcvd = 0.0
        self._last_rcvd_dlta = 0.0
        self._cached_value = None
        self._cached_result = None
        self._prop_values = None
        self._subscription_lock = Lock()
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        return
    def configure(self, cd):
        super(DeviceProperty, self).configure(cd)
        set_attribute(self, 'swid', REQUIRED, cd)
        set_attribute(self, 'prop_type', REQUIRED, cd)
        set_attribute(self, 'prop_name', self.name, cd)
        set_attribute(self, 'node_root', 'nodeDump', cd)
        set_attribute(self, 'value_key', 'presentValue', cd)
        set_attribute(self, 'bundle', 1, cd, int)
        set_attribute(self, 'ttl', 60, cd, int)
        set_attribute(self, 'read_only', 1, cd, int)
        return
    def configuration(self):
        cd = super(DeviceProperty, self).configuration()
        get_attribute(self, 'swid', cd)
        get_attribute(self, 'prop_type', cd)
        get_attribute(self, 'prop_name', cd)
        get_attribute(self, 'node_root', cd)
        get_attribute(self, 'value_key', cd)
        get_attribute(self, 'bundle', cd)
        get_attribute(self, 'ttl', cd)
        get_attribute(self, 'read_only', cd)
        return cd
    def start(self):
        for prop_name in PROPERTIES.get(self.prop_type, ()):
            if prop_name == self.prop_name:
                # this property will be returned via a get()
                # to this node
                continue
            p = Prop()
            cd = {'name':prop_name,
                  'parent':self}
            p.configure(cd)
            p.start()
        if self.node_root == 'nodeDump' and self.value_key == 'presentValue':
            setattr(self, 'decode', self._decode_fast)
        else:
            setattr(self, 'decode', self._decode_slow)
        self.url = BASE_URL % (self.station.host, self.swid)
        self._rqst = JaceRequest(self.url, ttl=self.ttl)
        self._configure_set()
        super(DeviceProperty, self).start()
        return
    def _configure_set(self):
        if self.read_only:
            return
        self._ovrd_cmd = self._ovrd_cmd_base % (self.station.host, self.swid)
        self._release_cmd = self._release_cmd_base % (self.station.host, self.swid)
        setattr(self, 'set', self._set)
        return
    def get_property_value(self, prop_name):
        if self._prop_values is None:
            self._load_property_value()
        return self._prop_values.get(prop_name, '')
    def _load_property_value(self):
        rsp = self.station.add_request(JaceRequest(self.url))
        if isinstance(rsp, Exception):
            return
        self._prop_values = {}
        if not rsp.is_complete():
            rsp.await_completion()
        data = rsp.read()
        if data.startswith('<!--'):
            data = data[(data[1:].find('<')+1):]
        data_o = self._decode_slow(data)
        for prop in self.children_nodes():
            if not isinstance(prop, Prop):
                continue
            try:
                value = fix_up_value(getattr(data_o, prop.name).get_tag_value())
            except:
                value = ''
            self._prop_values[prop.name] = value
        return
    def _decode_fast(self, data):
        value = None
        data = data.split('\n')
        if self._pv_index is None:
            cnt = 0
            for l in data:
                if l.count('presentValue'):
                    self._pv_index = cnt
                    break
                cnt += 1
        else:
            try:
                l = data[self._pv_index]
            except:
                value = self._decode_slow(data)
                if value:
                    value = fix_up_value(value)
                return value
        if l.count('presentValue') == 0:
            value = self._decode_slow(data)
        else:
            try:
                value = l.split('>')[1].split('<')[0]
            except:
                value = self._decode_slow(data)
        if value:
            value = fix_up_value(value)
        return value
    def _decode_slow(self, data):
        try:
            data_o = xml2code(data)
        except:
            data_o = None
        return data_o
    def event_subscribe(self, *args):
        self._subscription_lock.acquire()
        try:
            already_subscribed = self.event_has_subscribers()
            EventProducerMixin.event_subscribe(self, *args)
            if self.parent.can_bundle() and self.bundle:
                self.parent.subscribe(self.prop_name, self.update_cache)
            elif not already_subscribed:
                self.update_continuous(None)
                if self._cached_result and \
                    (uptime.secs() - self._cached_result.timestamp) < self.ttl:
                    self._trigger_cov(
                        self._cached_result.value, self._cached_result.value, time.time()
                    )
        finally:
            self._subscription_lock.release()
        return
    def event_unsubscribe(self, *args):
        self._subscription_lock.acquire()
        try:
            EventProducerMixin.event_unsubscribe(self, *args)
            if self.parent.can_bundle() and self.bundle:
                self.parent.unsubscribe(self.prop_name)
        finally:
            self._subscription_lock.release()
        return
    def _trigger_cov(self, old_value, new_value, t):
        cov = ChangeOfValueEvent(self, old_value, new_value, t)
        self.event_generate(cov)
        return
    def get(self, skipCache=0):
        v = self.get_result(skipCache).value
        if isinstance(v, Exception):
            raise ETimeout
        return v
    def get_result(self, skipCache=0):
        dt = uptime.secs() - self._last_rcvd
        if dt > self.ttl or self._cached_value is None:
            # data is stale
            self.update() # blocks
        return self._cached_result
    def update_cache(self, value):
        now = uptime.secs()
        if isinstance(value, ValueObj):
            value = value.get(self.prop_name)
        if value is None or isinstance(value, Exception):
            value = ETimeout()
        if value != self._cached_value:
            if self.event_has_subscribers():
                self._trigger_cov(self._cached_value, value, time.time())
            self._cached_value = value
        if self._cached_result is None:
            changes = 0
        else:
            changes = self._cached_result.changes + 1
        self._cached_result = Result(
            self._cached_value, self._last_rcvd, changes
            )
        self._last_rcvd = now
        return
    def has_cov(self):
        return 1
    def _set(self, value):
        if value in (None,'None'):
            url = self._release_cmd
        else:
            url = self._ovrd_cmd + str(value)
        self.station.add_request(JaceRequest(url))
        return
    def _get_station(self):
        return self.parent.parent
    station = property(_get_station)
    
# @fixme - improve type support - enumerations, etc..
def fix_up_value(value):
    value_map = {'true':1,'false':0}
    try:
        value = float(value)
    except:
        value = value_map.get(value, str(value))
    return value
    
class AnalogInput(DeviceProperty):
    pass
        
class AnalogOutput(DeviceProperty):    
    _ovrd_cmd_base = 'http://%s/command/invoke?swid=%s&command=manualSet&arg='
    _release_cmd_base = 'http://%s/command/invoke?swid=%s&command=manualAuto'
    
class AnalogOverride(DeviceProperty):
    _ovrd_cmd_base = 'http://%s/command/invoke?swid=%s&command=override&arg='
    _release_cmd_base = 'http://%s/command/invoke?swid=%s&command=cancel'
    def configure(self, cd):
        super(AnalogOverride, self).configure(cd)
        setattr(self, 'value_key', 'isActive')
        return
                
class BinaryInput(DeviceProperty):
    pass
        
class BinaryOutput(DeviceProperty):
    _ovrd_cmd_base = 'http://%s/command/invoke?swid=%s&command='
    _release_cmd_base = 'http://%s/command/invoke?swid=%s&command=manualAuto'
    def _set(self, value):
        if value in ('1', 1):
            url = self._ovrd_cmd + 'manualActive'
        elif value in ('0', 0):
            url = self._ovrd_cmd + 'manualInactive'
        elif value in ('None', None):
            url = self._release_cmd
        else:
            raise EInvalidValue('value', value, 'Bad value passed to set')
        self.station.add_request(JaceRequest(url))
        return
        
class BinaryOverride(DeviceProperty):
    _ovrd_cmd_base = 'http://%s/command/invoke?swid=%s&command=override&arg='
    _release_cmd_base = 'http://%s/command/invoke?swid=%s&command=cancel'
    def configure(self, cd):
        super(BinaryOverride, self).configure(cd)
        setattr(self, 'value_key', 'overrideValue')
        return
 
class MultiStateInput(DeviceProperty):
    pass
        
class MultiStateOverride(DeviceProperty):
    _ovrd_cmd_base = 'http://%s/command/invoke?swid=%s&command=override&arg='
    _release_cmd_base = 'http://%s/command/invoke?swid=%s&command=cancel'
    def configure(self, cd):
        super(MultiStateOverride, self).configure(cd)
        setattr(self, 'value_key', 'overrideValue')
        return

class MultiStateOutput(DeviceProperty):	
    _ovrd_cmd_base = 'http://%s/command/invoke?swid=%s&command=manualSet&arg='
    _release_cmd_base = 'http://%s/command/invoke?swid=%s&command=manualAuto'

class Schedule(DeviceProperty):	
    def configure(self, cd):
        super(Schedule, self).configure(cd)
        setattr(self, 'value_key', 'isActive')
        return
        
class Logic(DeviceProperty):
    pass
    
class Comparison(DeviceProperty):
    pass
    
class Math(DeviceProperty):
    pass
    
class AnalogCmd(DeviceProperty):
    def configure(self, cd):
        super(AnalogCmd, self).configure(cd)
        setattr(self, 'value_key', 'value')
        return
    
class OccupancyToBoolean(DeviceProperty):        
    def configure(self, cd):
        super(OccupancyToBoolean, self).configure(cd)
        setattr(self, 'node_root', 'boolValue')
        setattr(self, 'value_key', 'value')
        return
        
##
# The configuration of UserDefined's differs slightly
# in that, the fields are not standardized.  A node_root
# and get_param *must* be supplied - this provides the
# capability of accessing any element in the XML.
#
# UserDefined Jace property nodes are read-only
#
class UserDefined(DeviceProperty):
    pass
    
class Prop(CompositeNode):		
    def get(self):
        return self.parent.get_property_value(self.name)
    
PROPERTIES = {
    'AnalogInput':(
        'eventState','reliability','units',
        'presentValue','description',
        ),
    'AnalogCmd':(
        'description','maxValue','commandText',
        'minValue',
        ),
    'AnalogOutput':(
        'eventState','reliability','outOfService', 
         'units', 'presentValue','description',
         'relinquishDefault'
        ),
    'AnalogOverride':(
        'inOverride','overrideTime','overrideValue',
         'activeText','inactiveText',
         ),
    'BinaryInput':(
        'eventState','reliability','outOfService',
        'presentValue','activeText','inactiveText',
        'description',
        ),
    'BinaryOutput':(
        'eventState','reliability','presentValue', 
        'active','inactive','description',
        'relinquishDefault',
        ),
    'BinaryOverride':(
        'inOverride', 'overrideTime','overrideValue', 
        'active','inactive',
        ),
    'MultiStateInput':(
        'eventState', 'reliability','outOfService',
        'presentValue',
        ),
    'MultiStateOverride':(
        'inOverride', 'overrideTime', 'overrideValue',
        'activeText', 'inactiveText',
        ),
    'MultiStateOutput':(
        'eventState', 'reliability', 'presentValue',
        ),
    'Schedule':(
        'isActive',
        ),
    'Logic':(
        'description','presentValue','reliability',
        'function','outOfService',
        ),
    'Comparison':(
        'description','presentValue',
        ),
    'Math':(
        'description','presentValue'
        ),
    'OccupancyToBoolean':(),
    'UserDefined':()
    }
    
##    
# Python recipe - takes an xml doc and maps element\value
# to object property.
class Tag(object):
    def __init__(self, name, args=[]):
        arglist = name.split(" ")
        self._name = arglist[0]
        self._kw = {}
        self._args = args
        if len(arglist)>1:
            kw={}
            for i in arglist[1:]:
                try:
                    key, val = i.split("=")
                except:
                    pass
                kw[key] = val
            self._kw = kw
        return
    def __len__(self):
        return len(self._args)
    def __str__(self):
        if self._args == []:
            if self._kw == {}:
                txt = "<"+self._name+"/>"
            else:
                txt ="<"+self._name
                for i in self._kw.keys():
                    txt += " "+str(i)+"="+str(self._kw[i])+" "
                txt = txt[:-1]+"/>"
        else:
            if self._kw == {}:
                txt = "<"+self._name+">"
            else:
                txt = "<"+self._name
                for i in self._kw.keys():
                    txt += " "+str(i)+"="+str(self._kw[i])+" "
                txt = txt[:-1]+">"
            for arg in self._args:
                txt += str(arg)
            txt += "</"+self._name+">"
        return txt
    def __repr__(self):
        return str(self)
    def __getitem__(self,key):
        rslt = None
        if type(key) == type(0):
            rslt = self._args[key]
        elif type(key) == type(""):
            rslt = self._kw[key]
        return rslt
    def __setitem__(self,key,value):
        if type(key) == type(0):
            if key < len(self._args):
                self._args[key] = value
            else:
                self._args.insert(key, value)
        else:
            self._kw[key] = value
        return
    def keys(self):
        return self._kw.keys()
    def tags(self):
        lst=[]
        for i in range(len(self)):
            try:
                lst.append(self[i]._name)
            except:
                pass
        return lst
    def get_tag_by_name(self,strg):
        lst=[]
        for i in range(len(self)):
            try:
                if self[i]._name==strg:
                    lst.append(self[i])
            except:
                pass
        if len(lst) == 1:
            return lst[0]
        else:
            return lst
    def __getattr__(self,key):
        try:
            return self.get_tag_by_name(key)
        except:
            if self.__dict__.has_key(key):
                return self.__dict__[key]
            else:
                raise AttributeError, "Name does not exist '%s.'" % (key)
        return
    def append(self, val):
        self._args.append(val)
        return
    def get_tag_value(self):
        return self._args[0]

def xml2code(xml_data):
    data = xml_data.replace("[","<lbracket/>").replace("]","<rbracket/>")
    data = data.replace("\n","").replace('"',"'")
    data = data.replace("?>","?/>").replace("-->","--/>")
    data = data.replace("</","[]endtag[").replace("/>","[]mptytag[")
    data = data.replace("<","[]starttag[").replace(">","[]closetag[")
    data = data.split("[")
    outstr = ''
    i = -1
    lendata = len(data)
    while i < lendata - 1:
        i += 1
        x = data[i]
        x = x.strip()
        if len(x)==0:
            continue
        if x[0] == "]":
            if x[1] == "s":
                outstr += 'Tag("'+data[i+1]+'",['
                i = i + 2
                if data[i][0:2]=="]m":
                    outstr += ']),'
            elif x[1] == "e":
                outstr += ']),'
                i = i+2
        else:
            outstr +='"'+x+'",'
    outstr = "Tag('root',["+outstr+"])"
    outstr = outstr.replace(",)",")")
    return eval(outstr)[0]


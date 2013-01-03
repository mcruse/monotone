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
from threading import Event
from threading import Lock
from mpx.lib import msglog
from mpx.lib.neode.node import ConfigurableNode
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.configure import as_boolean
from mpx.componentry import implements
from mpx.service.network.async.connection import monitor
from mpx.service.network.async.connection.channel import Channel
from mpx.service.network.async.message.request import Request
from mpx.service.network.utilities.counting import Counter
from mpx.service.equipment.utilities import Dictionary
from exceptions import ETransactionTimeout
from interfaces import *

class LocationController(object):
    IDEALBACKLOG = 5
    MAXPARALLELCHANNELS = 10
    MAXTRANSPERCHANNEL = 250
    ZOMBIETIMEOUT = 900
    def __init__(self, monitor, host, port, protocol = 'http', debug = 0):
        self.monitor = monitor
        self.host = host
        self.port = port
        self.protocol = protocol
        self.debug = debug
        self.free_channels = []
        self.active_channels = Dictionary()
        self.inactive_channels = Dictionary()
        self.parallel_channels = Counter()
        self.pending_transactions = []
        self.inflight_transactions = Dictionary()
        self.state_lock = Lock()
        self.debugout('Instantiated', 2)
    def is_transaction_pending(self,sid):
        for tran in self.pending_transactions:
            if(tran.sid == sid):
                return(True)
        return(False)
    
    def recruit_and_send(self):
        self.state_lock.acquire()
        self.debugout('Pending Transactions in recruit and send are :%d' %(len(self.pending_transactions)))
        try:
            openchannel = self._recruit_channel()
        finally:
            self.state_lock.release()
        if openchannel:
            self.debugout('Initiating a transaction by recruit and send' )
            self.initiate_next_transaction()
        else:
            self.debugout('Recruit channel returns None. Unable to init a transaction by recruit and send')
            
        
        
    def add_transaction(self, transaction):
        self.state_lock.acquire()
        self.debugout('Pending Transactions are :%d' %(len(self.pending_transactions)))
        try:
            self.debugout('[%s] Adding transaction', 3)
            transaction.set_manager(self)
            openchannel = self._recruit_channel()
            self.pending_transactions.append(transaction)     
        finally:
            self.state_lock.release()
        if openchannel:
            self.initiate_next_transaction()
        else:
            self.debugout('Recruit channel returns None. Pending transactions =%d' %(len(self.pending_transactions)))
    
                     
    def initiate_next_transaction(self):
        self.state_lock.acquire()
        try:
            channel = self._activate_channel()
            if channel is not None:
                transaction = self._activate_transaction()
        finally:
            self.state_lock.release()
        if channel is None:
            message = 'Activate channel returned None to initiate next.'
            message += '\n\t\t-- %r\n'
            self.debugout(message, 1, self)
        else:
            transaction.set_channel(channel)
            message = '[%s] Initiating transaction.'
            self.debugout(message, 3)
            if channel.response_count() > self.MAXTRANSPERCHANNEL:
                message = '[%s] Configuring transaction to close channel:'
                message += '\n\t%r\n\t%r\n'
                self.debugout(message, 1, transaction, channel)
                transaction.close_when_done()
            transaction.initiate()
    def handle_completed_transaction(self, transaction):
        self.debugout('[%s] Handling completed transaction', 3)
        self.state_lock.acquire()
        try:
            self._deactivate_transaction(transaction)
            self._deactivate_channel(transaction.channel)
            if self.pending_transactions:
                initiatenext = (self.inactive_channels or 
                                self._recruit_channel())
            else:
                initiatenext = False
                self._free_channel(transaction.channel)
        finally:
            self.state_lock.release()
        if self.debug > 1:
            message = '[%s] completed: ' % self
            message += '%s' % transaction.stats()[1:-1]
            self.msglog(message, msglog.types.DB, False)
        if initiatenext:
            self.initiate_next_transaction()
    def handle_failed_transaction(self, transaction):
        try:
            self.state_lock.acquire()
            try:
                # Changes for CSCtg33093 (b.Avoid getting the channel number, if channel is None)
                if(transaction.channel != None ):
                    transaction.channel.accepting_requests(False)
            finally:
                self.state_lock.release()
            message = 'Handling failed transaction %r' % transaction
            self.msglog(message, msglog.types.WARN)
        finally:
            self.handle_completed_transaction(transaction)
    def _activate_transaction(self):
        assert self.state_lock.locked()
        transaction = self.pending_transactions.pop(0)
        tid = transaction.transaction_number
        self.inflight_transactions[tid] = transaction
        return transaction
    def _deactivate_transaction(self, transaction):
        assert self.state_lock.locked()
        tid = transaction.transaction_number
        try:
            self.inflight_transactions.pop(tid)
        except KeyError:
            self.debugout('Transaction %r not in active list', 1, transaction)
            return False
        else: 
            return True
    def _recruit_channel(self):
        assert self.state_lock.locked()
        if not self.free_channels:
            self._manage_channels()
            channel = None
        if self.free_channels:
            channel = self.free_channels.pop()
            cid = channel.channel_number
            self.inactive_channels[cid] = channel
        return channel
    def _free_channel(self, channel):
        assert self.state_lock.locked()
        cid = channel.channel_number
        if self.inactive_channels.has_key(cid):
            self.inactive_channels.pop(cid)
            if channel.accepting_requests():
                self.free_channels.append(channel)
    def _activate_channel(self):
        assert self.state_lock.locked()
        if not self.inactive_channels:
            channel = self._recruit_channel()
        else:
            cid, channel = self.inactive_channels.popitem()
        if channel is not None:
            self.active_channels[channel.channel_number] = channel
        return channel
    def _deactivate_channel(self, channel):
        assert self.state_lock.locked()
        # Changes for CSCtg33093 (b.Avoid getting the channel number, if channel is None)
        if(channel == None):
            return(False)
        cid = channel.channel_number
        try: 
            self.inactive_channels[cid] = self.active_channels.pop(cid)
        except KeyError:
            self.debugout('Channel %r not in active list', 1, channel)
            return False
        else:
            if not channel.accepting_requests():
                self.inactive_channels.pop(cid)
                self.parallel_channels.decrement()
                if not channel.is_closed():
                    channel.close()
                self.debugout('Channel %r decommissioned.', 1, channel)
            return True
    def _manage_channels(self):
        assert self.state_lock.locked()
        for cid, channel in self.active_channels.items():
            message = 'Location channel management removing %r from active.'
            if not channel.accepting_requests():
                self.debugout(message % channel, 1)
                self.active_channels.pop(cid)
                self.parallel_channels.decrement()
        maxchannels = self.MAXPARALLELCHANNELS
        numpending = len(self.pending_transactions)
        numchannels = self.parallel_channels.value
        if numchannels == 0:
            createchannel = True
        elif numchannels >= maxchannels:
            createchannel = False
        elif (numpending / numchannels) > self.IDEALBACKLOG:
            createchannel = True
        else:
            createchannel = False
        if createchannel:
            channel = Channel(self.monitor, self.debug)
            channel.setup_connection(self.host, self.port, self.protocol)
            self.free_channels.append(channel)
            self.parallel_channels.increment()
        return
    def msglog(self, message, mtype = msglog.types.INFO, autoprefix = False):
        if autoprefix:
            message = '%s %s' % (self, message)
        msglog.log('broadway', mtype, message)
    def debugout(self, message, debuglevel = 1, *args):
        if debuglevel <= self.debug:
            if self not in args:
                if message.count('%') == len(args):
                    message = '%s ' + message
                args = (self,) + args
            return self.msglog(message % args, msglog.types.DB)
    def __repr__(self):
        status = ['Controller']
        status.append('[%s:%d]' % (self.host, self.port))
        channels = self.parallel_channels.value
        active = len(self.active_channels)
        inactive = len(self.inactive_channels)
        free = len(self.free_channels)
        pending = len(self.pending_transactions)
        inflight = len(self.inflight_transactions)
        channelmsg = '%d Channels (%dA %dI %dF)'
        status.append(channelmsg % (channels, active, inactive, free))
        status.append('Transactions (%dA %dP)' % (inflight, pending))
        return '<%s>' % (' '.join(status))
    def __str__(self):
        classname = self.__class__.__name__
        channels = self.parallel_channels.value
        status = '(%d => %s:%d)' % (channels, self.host, self.port)
        return '%s %s' % (classname, status)

class TransactionManager(object):
    QUEUEDEBUG = False
    def __init__(self, monitor, debug = 0):
        self.monitor = monitor
        self.debug = debug
        self.controllers = Dictionary()
        self.controller_lock = Lock()
        super(TransactionManager, self).__init__()
    def _get_controller(self, host, port, protocol):
        location = (host, port)
        self.controller_lock.acquire()
        try:
            if not self.controllers.has_key(location):
                self.controllers[location] = LocationController(
                    self.monitor, host, port, protocol, self.debug)
        finally:
            self.controller_lock.release()
        return self.controllers.get(location)
    def create_transaction(self, request,sid):
        controller = self._get_controller(request.get_host(), 
                                          request.get_port(), 
                                          request.get_type())
        
        if(controller.is_transaction_pending(sid)):
            if self.debug or self.QUEUEDEBUG: 
                msglog.log('broadway',msglog.types.DB,'Already Pending transaction, so not adding transaction. sid=%s' %(sid))
            controller.recruit_and_send()
            return(None)
            
        transaction = Transaction(request,sid=sid)
        
        if self.debug or self.QUEUEDEBUG:
            before = repr(controller)
        controller.add_transaction(transaction)
        if self.debug or self.QUEUEDEBUG:
            after = repr(controller)
            message = 'Controller before and after adding transaction:\n'
            message += '    - Before: %s\n' % (before[1:-1])
            message += '    - After: %s\n' % (after[1:-1])
            msglog.log('broadway', msglog.types.DB, message)
        return transaction

class Transaction(object):
    transaction_counter = Counter()
    timeout = 300
    def __init__(self, request = None, channel = None, **kw):
        self.transaction_number = self.transaction_counter.increment()
        self.debug = 0
        self.sid=None
        if(kw.has_key('sid')):
            self.sid = kw.get('sid')    
        self.manager = None
        self.request = None
        self.channel = None
        if request:
            self.set_request(request)
        if channel:
            self.set_channel(channel)
        self._state_listeners = []
        self._complete = Event()
        self._complete.clear()
        self._close_when_done = False
        self._transaction_initiated = None
        self._transaction_completed = None
        self._transaction_created = time.time()
    def set_manager(self, manager):
        self.manager = manager
    def close_when_done(self):
        self._close_when_done = True
        self.request.add_header('Connection', 'close')
    def add_state_listener(self, callback):
        self._state_listeners.append(callback)
        if self.is_complete():
            self._run_callbacks()
    def notify_complete(self):
        self._complete.set()
        if self.debug > 3:
            message = 'Transaction complete:'
            message += '\n\tTransaction: %r' % self
            message += '\n\tRequest: %r' % self.request
            message += '\n\tResponse: %r' % self.get_response()
            message += '\n\tOver channel: %r\n' % self.channel
            msglog.log('broadway', msglog.types.DB, message)
        if self._close_when_done:
            if self.debug > 2:
                message = 'Transaction closing channel:'
                message += '\n\tTransaction: %r' % self
                message += '\n\tChannel: %r' % self.channel
                msglog.log('broadway', msglog.types.DB, message)
            elif self.debug:
                message = '%s closing %s' % (self, self.channel)
                msglog.log('broadway', msglog.types.DB, message)
            self.channel.close()
        self._run_callbacks()
        if self.manager:
            self.manager.handle_completed_transaction(self)
    def handle_timeout(self):
        if self.manager:
            message = '%s notifying manager of timeout' % self
            msglog.log('broadway', msglog.types.INFO, message)
            self.manager.handle_failed_transaction(self)
        else:
            message = 'Transaction handling timeout has no manager: %r'
            msglog.log('broadway', msglog.types.WARN, message % self)
    def handle_error(self):
        warning = msglog.types.WARN
        msglog.log('broadway', warning, 
                   'Transaction handling error: %r' % self)
        if not self.is_complete() and self.manager:
            msglog.log('broadway', warning, 'Incomplete, will notify manager')
            self.manager.handle_failed_transaction(self)
    def _run_callbacks(self):
        while self._state_listeners:
            listener = self._state_listeners.pop(0)
            try:
                listener(self)
            except:
                msglog.exception()
        assert len(self._state_listeners) == 0
    def await_completion(self, timeout = None):
        self._complete.wait(timeout)
        return self.is_complete()
    def is_complete(self):
        return self._complete.isSet()
    def set_request(self, request):
        self.request = request
        if request is not None:
            self.request.add_state_listener(self.notify_response_ready)
    def set_response(self, response):
        self.response = response
        self.response.add_state_listener(self.notify_reader_ready)
    def set_reader(self, reader):
        self.reader = reader
        self.reader.add_state_listener(self.notify_response_complete)
    def set_channel(self, channel):
        self.channel = channel
        self.debug = channel.debug
    def set_timeout(self, timeout):
        self.timeout = timeout
    def initiate(self):
        if self.debug > 3:
            message = 'Transaction initiating %s:' % time.ctime()
            message += '\n\tTransaction: %r' % self
            message += '\n\tRequest: %r' % self.request
            message += '\n\tOver channel: %r\n' % self.channel
            msglog.log('broadway', msglog.types.DB, message)
        self._transaction_initiated = time.time()
        self.channel.send_request(self.request)
        if self.debug > 3:
            message = 'Transaction added request to channel %s:' % time.ctime()
            message += '\n\tTransaction: %r' % self
            message += '\n\tRequest: %r' % self.request
            message += '\n\tOver channel: %r\n' % self.channel
            msglog.log('broadway', msglog.types.DB, message)
        if self._close_when_done:
            self.channel.accepting_requests(False)
    def request_sent(self):
        return self._transaction_initiated is not None
    def request_age(self):
        assert self.request_sent()
        return time.time() - self._transaction_initiated
    def transaction_age(self):
        return time.time() - self._transaction_created
    def has_response(self):
        return self.request.has_response()
    def get_response(self):
        return self.request.get_response()
    def notify_response_ready(self, request):
        assert request is self.request
        self.set_response(request.get_response())
    def notify_reader_ready(self, response):
        assert response is self.response
        self.set_reader(response.get_reader())
    def notify_response_complete(self, reader):
        assert reader is self.reader
        self._transaction_completed = time.time()
        self.notify_complete()
    def is_expired(self):
        if self.is_complete():
            return False
        if self.timeout is None:
            return False
        return self.transaction_age() > self.timeout
    def succeeded(self):
        if self.is_complete():
            return self.response.handled_properly()
        elif self.is_expired():
            detail = 'Older than %d seconds' % self.timeout
            raise ETransactionTimeout(self, detail)
        return False
    def cancel(self):
        if not self.is_complete() and self.manager:
            self.manager.handle_failed_transaction()
        msglog.log('broadway', msglog.types.WARN, '%r closing channel' % self)
        try: 
            self.channel.close()
        except:
            msglog.exception(prefix = 'Handled')
    def stats(self):
        status = ['Transaction #%d' % self.transaction_number]
        if self.request_sent():
            status.append('(HTTP %s)' % self.get_response().get_status())
            status.append('(%f sec flight)' % self.get_flighttime())
        else:
            status.append('(pending)')
        return '<%s>' % ' '.join(status)
    def get_flighttime(self):
        if self.request_sent():
            return self._transaction_completed - self._transaction_initiated
    def __repr__(self):
        information = []
        if self.request_sent():
            tinitiated = time.ctime(self._transaction_initiated)
            information.append('request: %s' % tinitiated)
            if self.is_complete():
                tcompleted = time.ctime(self._transaction_completed)
                information.append('response: %s' % tcompleted)
                respstatus = self.get_response().get_status()
                if self.succeeded():
                    information.append('success: %s' % respstatus)
                else:
                    information.append('failure: %s' % respstatus)
                flighttime = (self._transaction_completed - 
                              self._transaction_initiated)
                information.append('flight time: %f sec' % flighttime)
            else:
                if self.is_expired():
                    information.append('response expired')
                else:
                    information.append('response pending')
        else:
            information.append('not initiated')
        information = ['(%s)' % detail for detail in information]
        classname = self.__class__.__name__
        transactionnumber = self.transaction_number
        information.insert(0, '%s #%d' % (classname, transactionnumber))
        return '<%s>' % (' '.join(information))

class AnsychronousSubscriptionTransport(ConfigurableNode):
    implements(ITransporter)
    def __init__(self, *args):
        self.monitor = monitor.ChannelMonitor()
        self.transaction_manager = TransactionManager(self.monitor)
        super(AnsychronousSubscriptionTransport, self).__init__(*args)
    def start(self):
        if not self.monitor.is_running():
            self.monitor.start_monitor()
            self.transaction_manager.debug = self.debug
        super(AnsychronousSubscriptionTransport, self).start()
    def stop(self):
        if self.monitor.is_running():
            self.monitor.stop_monitor()
        super(AnsychronousSubscriptionTransport, self).stop()
    def configure(self, config):
        set_attribute(self, 'chunked_data', 0, config, as_boolean)
        set_attribute(self, 'debug', 0, config, as_boolean)
        set_attribute(self, 'content_type', 'text/html', config)
        set_attribute(self, 'timeout', None, config, float)
        super(AnsychronousSubscriptionTransport, self).configure(config)
    def configuration(self):
        config = super(AnsychronousSubscriptionTransport, self).configuration()
        get_attribute(self, 'chunked_data', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'content_type', config)
        get_attribute(self, 'timeout', config, str)
        return config
    def transport(self, target, data, **kw):
        self.debug_msglog('initiating transport to target: %r' % target)
        sid=None
        if(kw.has_key('sid')):
            sid=kw['sid']
        request = Request(target)
        request.add_header('Host', request.get_host())
        contenttype = getattr(data, 'mimetype', self.content_type)
        request.add_header('Content-Type', contenttype)
        if not isinstance(data, str):
            data = self._convert_to_string(data)
        request.set_data(data)
        return self.transaction_manager.create_transaction(request,sid)
    def debug_msglog(self, dbmessage, dblevel = 1):
        if self.is_debuglevel(dblevel):
            self.msglog(dbmessage, msglog.types.DB)
    def msglog(self, message, mtype = msglog.types.INFO):
        msglog.log('broadway', mtype, '[%s] %s' % (self, message))
    def is_debuglevel(self, level = 1):
        return level <= self.debug
    def __repr__(self):
        return '<%s %r at %#x>' % (self.__class__.__name__, self.url, id(self))
    def __str__(self):
        return '%s' % (self.__class__.__name__)

def convert_to_string(data):
    if isinstance(data, str):
        return data
    elif hasattr(data, 'read'):
        return data.read()
    raise ValueError('Cannot convert to string.', data)

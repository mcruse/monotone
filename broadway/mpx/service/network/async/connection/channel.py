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
import socket
import string
import select
from threading import Lock
from errno import EISCONN
from errno import EINPROGRESS
from errno import EALREADY
from errno import EWOULDBLOCK
from errno import errorcode
from M2Crypto import SSL
from cStringIO import StringIO
from mpx.lib import msglog
from asynchat import async_chat as AsyncChat
from mpx.service.network.async.message.response import Response
from mpx.service.network.async.message.request import Request
from mpx.service.network.async.message.header import HeaderDictionary
from mpx.service.network.utilities.counting import Counter

class Channel(AsyncChat, object):
    """
        Sender instantiates class with target URL and socket map.
        Socket map is dictionary of asynchronous connections, like 
        this client, that are being managed together.
        
        Once instantiated, the HTTP Client will have created and connected 
        a socket to the target host and port.  Response data should then be 
        added to the client.  This is done by calling 'push(data)', or 
        'push_with_producer(producer)'.
        
        Use 'push' when data is of type string, and is not a producer 
        instance.
        
        Use 'push_with_producer' to push data already contained within a 
        producer type object.  Producer type objects have 'more' method 
        which returns partial data, allowing it to be output as it is 
        sent.
    """
    ac_out_buffer_size = 1 << 16
    channel_counter = Counter()
    
    def __init__(self, map, debug = 0):
        AsyncChat.__init__(self)
        self.channel_number = self.channel_counter.increment()
        self.monitor = self._map = map
        self.debug = debug
        self._fileno = None
        self._keep_alive = 1
        self._using_ssl = False
        self._ssl_context = None
        self._pending_requests = []
        self._sending_requests = []
        self._current_response = None
        self._is_connected = False
        self._connection_initiated = False
        self._accepting_requests = True
        self._is_closed = False
        self._header_buffer = StringIO()
        self._constate_lock = Lock()
        self.reset_terminator()
        self._setup_counters()
        self._born_on = self._last_use = time.time()
    def _setup_counters(self):
        self.request_counter = Counter()
        self.response_counter = Counter()
        self.bytes_out = Counter()
        self.bytes_in = Counter()
        self.read_calls = Counter()
        self.readable_calls = Counter()        
        self.write_calls = Counter()
        self.writable_calls = Counter()
        self.buffer_refills = Counter()
        self.refill_skips = Counter()
    def get_statistics(self):
        requests = float(self.request_counter.value)
        responses = float(self.response_counter.value)
        bytesin = float(self.bytes_in.value)
        bytesout = float(self.bytes_out.value)
        readcalls = float(self.read_calls.value)
        readablecalls = float(self.readable_calls.value)
        writecalls = float(self.write_calls.value)
        writablecalls = float(self.writable_calls.value)
        refills = float(self.buffer_refills.value)
        refillskips = float(self.refill_skips.value)
        messages = ['Number of requests: %d' % requests]
        messages.append('Number of responses: %d' % responses)
        messages.append('Bytes read: %d' % bytesin)
        messages.append('Bytes written: %d' % bytesout)
        messages.append('Calls to read: %d' % readcalls)
        messages.append('Calls to readable: %d' % readablecalls)
        messages.append('Calls to write: %d' % writecalls)
        messages.append('Calls to writable: %d' % writablecalls)
        messages.append('Calls to refill buffer: %d' % refills)
        messages.append('Skipped calls to refill buffer: %d' % refillskips)
        averages = []
        if requests:
            # Changes for CSCtg33093 (a.Avoid division by zero) 
            bytesperrequest = bytesin / requests
            readsperrequest = readcalls / requests
            bytesperread=readablesperread=0
            if(readcalls):
                bytesperread = bytesin / readcalls
                readablesperread = readablecalls / readcalls
            averages.append('Bytes per request: %0.1f' % bytesperrequest)
            averages.append('Reads per request: %0.1f' % readsperrequest)
            averages.append('Readables per read: %0.1f' % readablesperread)
            averages.append('Bytes per read: %0.1f' % bytesperread) 
        if responses:
            # Changes for CSCtg33093 (a.Avoid division by zero) 
            bytesperresponse = bytesout / responses
            writesperresponse = writecalls / responses
            refillsperresponse = refills / responses
            bytesperwrite=writablesperwrite=0
            if(writecalls):
                bytesperwrite = bytesout / writecalls
                writablesperwrite = writablecalls / writecalls
            bytesperrefill=responsesperrefill=0
            if(refills):
                bytesperrefill = bytesout / refills
                responsesperrefill = responses / refills
            
            averages.append('Bytes per response: %0.1f' % bytesperresponse)
            averages.append('Writes per response: %0.1f' % writesperresponse)
            averages.append('Writables per write: %0.1f' % writablesperwrite)
            averages.append('Bytes per write: %0.1f' % bytesperwrite)
            averages.append('Refills per response: %0.1f' % refillsperresponse)
            averages.append('Bytes per refill: %0.1f' % bytesperrefill)
            averages.append('Responses per refill: %0.1f' % responsesperrefill)
        formatted = ['Server channel statistics']
        for message in messages:
            label, value = message.split(': ')
            formatted.append('  --%s: %s' % (label.ljust(25), value))
        formatted.append('    Calculated averages')
        for average in averages:
            label, value = average.split(': ')
            formatted.append('      --%s: %s' % (label.ljust(25), value))
        return '\n'.join(formatted)
    def is_closed(self):
        return self._is_closed
    def request_count(self):
        return self.request_counter.value
    def response_count(self):
        return self.response_counter.value
    def last_used(self):
        return self._last_use
    def created(self):
        return self._born_on
    def get_socket(self):
        return self.socket
    def file_descriptor(self):
        return self._fileno
    def should_monitor_writable(self):
        return self.writable()
    def should_monitor_readable(self):
        return self.readable()
    def reset_channel(self):
        self._current_response = None
        self._header_buffer.seek(0)
        self._header_buffer.truncate()
        self.reset_terminator()
    def reset_terminator(self):
        self.set_terminator('\r\n\r\n')
    def accepting_requests(self, value = None):
        if value is not None:
            self._accepting_requests = value
        return self._accepting_requests and not self._is_closed
    def send_request(self, request):
        if self._is_closed:
            raise TypeError('Cannot send request over closed channel.')
        self._pending_requests.append(request)
        if not self._connection_initiated:
            self.setup_connection(request.get_host(), 
                                  request.get_port(), 
                                  request.get_type())
        self._last_use = time.time()
        self.monitor.check_channels()
        self.request_counter.increment()
    #===============================================================================
    #  Several connection-related methods have been overridden 
    #  in order to support dynamically distinguishing between 
    #  and supporting secure connections, and to prevent the 
    #  channel's file descriptor from being added to the monitor
    #  prematurely.  That 'create_socket' automatically added the 
    #  socket's FD to the socket map is a bug because select 
    #  performed on unconnected sockets register as readable and 
    #  writable; reading from such a socket, however, will return 
    #  '', causing it to be closed, and writing to it generates 
    #  an I/O, also causing it to be closed.
    #  
    #  NOTE that another option is to use the connection flags
    #  in readable / writable decisions, preventing unconnected 
    #  channel from being added to socket map.
    #===============================================================================
    def setup_connection(self, host, port, connectiontype):    
        self._constate_lock.acquire()
        try:
            if connectiontype == 'http':
                self._using_ssl = False
            elif connectiontype == 'https':
                self._using_ssl = True
            else:
                raise TypeError('Unknown connection type', connectiontype)
            if self.socket is None:
                self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            if not self._connection_initiated:
                self.connect((host, port))
                self._connection_initiated = True
            elif not (host, port) == self.addr:
                raise TypeError('Channel can only connect to one address.')
        finally:
            self._constate_lock.release()
        self.monitor.add_channel(self)
    def create_socket(self, family, stype):
        assert self.socket is None, 'Socket already created.'
        self.family_and_type = family, type
        if self._using_ssl:
            connection = self._create_secure_socket(family, stype)
        else:
            connection = self._create_insecure_socket(family, stype)
        self.set_socket(connection)
    def _create_insecure_socket(self, family, type):
        connection = socket.socket(family, type)
        connection.setblocking(0)
        return connection
    def _create_secure_socket(self, family, stype):
        self._ssl_context = SSL.Context()
        connection = SSL.Connection(self._ssl_context)
        return connection
    def set_socket(self, connection):
        self.socket = connection
        self._fileno = connection.fileno()
    def connect(self, address):
        assert not self._connection_initiated, 'Cannot connect twice.'
        self.connected = False
        try:
            if self._using_ssl:
                self.socket.setblocking(1)
                try:
                    self.socket.connect(address)
                finally:
                    self.socket.setblocking(0)
                errorvalue = 0
            else:
                errorvalue = self.socket.connect_ex(address)
        except:
            message = 'Failed to connect to address %s.  Exception follows.'
            self.msglog(message % (address,), msglog.types.WARN)
            self.handle_error()
            raise
        else:
            self.addr = address
            if errorvalue in (0, EISCONN):
                self.connected = True
                self.handle_connect()
            elif errorvalue not in (EINPROGRESS, EALREADY, EWOULDBLOCK):
                message = 'Failed to connect to address %s.'
                self.msglog(message % (address,), msglog.types.WARN)
                raise socket.error, (errorvalue, errorcode[errorvalue])
    def refill_buffer(self):
        outgoing = len(self.producer_fifo)
        while self._pending_requests:
            request = self._pending_requests.pop(0)
            self._sending_requests.append(request)
            # Bypass AsyncChat's push because it automatically calls initiate
            self.producer_fifo.push(request.get_outgoing_producer())
        if len(self.producer_fifo) > outgoing:
            self.buffer_refills.increment()
        else:
            self.refill_skips.increment()
        return AsyncChat.refill_buffer(self)
    def found_terminator(self):
        if self._current_response is None:
            self._header_buffer.seek(0)
            responseline = self._header_buffer.readline()
            version, status, reason = crack_responseline(responseline)
            if status == 100:
                # Continue header, meaningless.
                self.reset_channel()
                return
            headerlines = self._header_buffer.readlines()
            headers = HeaderDictionary.from_strings(headerlines)
            request = self._sending_requests.pop(0) 
            response = Response(version, status, reason.strip(), headers)
            request.set_response(response)
            self._current_response = response
        self._current_response.found_terminator()
        self._handle_response_update()
    def _handle_response_update(self):
        if self._current_response.is_complete():
            self.reset_channel()
            self.response_counter.increment()
        else:
            self.set_terminator(self._current_response.get_terminator())
    def collect_incoming_data(self, data):
        if not data:
            raise ValueError('Collecting empty data!')
        if self._current_response:
            self._current_response.collect_incoming_data(data)
        else:
            self._header_buffer.write(data)
    def writable(self):
        self.writable_calls.increment()
        return AsyncChat.writable(self) or len(self._pending_requests)
    def readable(self):
        self.readable_calls.increment()
        return AsyncChat.readable(self)
    def handle_connect(self):
        self._is_connected = True
    def handle_write (self):
        AsyncChat.handle_write(self)
    def send(self, data):
        self.write_calls.increment()
        result = AsyncChat.send(self, data)
        self.bytes_out.increment(result)
        return result
    def recv(self, buffer_size):
        self.read_calls.increment()
        data=''
        try:
            data = AsyncChat.recv(self, buffer_size)
            self.bytes_in.increment(len(data))
        except :
            msglog.exception(prefix='Handled')        
        return data
    def handle_read(self):
        AsyncChat.handle_read(self)
    def handle_close(self):
        if self._current_response:
            self._current_response.handle_close()
            self._handle_response_update()
        AsyncChat.handle_close(self)
    def close(self):
        self._is_closed = True
        self._is_connected = False
        self.monitor.remove_channel(self)
        sock = self.socket
        if sock:
            sock.close()
        self.debug_msglog('closed')
        pending = self._pending_requests[:]
        sending = self._sending_requests[:]
        self._pending_requests = []
        self._sending_requests = []
        self.debug_msglog('%d requests in pending.' % len(pending))
        for request in pending:
            self.debug_msglog('Pending %r' % request)
            if request.has_response():
                self.debug_msglog('Pending %r' % request)
        self.debug_msglog('%d requests in sending.' % len(sending))
        for request in sending:
            self.debug_msglog('Sending %r' % request)
        if self.is_debuglevel(1):
            self.log_statistics()
    def debug_msglog(self, message, level = 1):
        if self.is_debuglevel(level):
            self.msglog(message, msglog.types.DB)
    def log_statistics(self):
        self.msglog('\n%s\n' % self.get_statistics(), msglog.types.DB)
    def is_debuglevel(self, level):
        return level <= self.debug
    def msglog(self, message, mtype = msglog.types.INFO):
        msglog.log('broadway', mtype, '[%s] %s' % (self, message))
    def handle_error(self):
        try:
            messages = ['Handling error.']
            messages.append('Closing connection.')
            messages.append('Exception follows.')
            self.msglog('  '.join(messages), msglog.types.ERR)
            msglog.exception(prefix = 'Handled')
        finally:
            self.close()
    #####
    #   Semi-crazy method that is working around a sort-of bug within 
    #   asyncore.  When using select-based I/O multiplexing, the POLLHUP 
    #   the socket state is indicated by the socket becoming readable, 
    #   and not by indicating an exceptional event.
    #   
    #   When using POLL instead, the flag returned indicates precisely 
    #   what the state is because "flags & select.POLLHUP" will be true.
    #   
    #   In the former case, when using select-based I/O multiplexing, 
    #   select's indication that the the descriptor has become readable 
    #   leads to the channel's handle read event method being invoked.  
    #   Invoking receive on the socket then returns an empty string, 
    #   which is taken by the channel as an indication that the socket 
    #   is no longer connected and the channel correctly shuts itself 
    #   down.
    #   
    #   However, asyncore's current implementation of the poll-based 
    #   I/O multiplex event handling invokes the channel's 
    #   handle exceptional data event anytime "flags & POLLHUP" is true.  
    #   While select-based multiplexing would only call this method when 
    #   OOB or urgent data was detected, it can now be called for POLLHUP 
    #   events too.
    #   
    #   Under most scenarios this is not problematic because poll-based 
    #   multiplexing also indicates the descriptor is readable and 
    #   so the handle read event is also called and therefore the 
    #   channel is properly close, with only an extraneous invocation 
    #   to handle exceptional event being a side-effect.  Under certain 
    #   situations, however, the socket is not indicated as being 
    #   readable, only that it has had an exceptional data event.  It 
    #   believe this occurs when the attemtp to connect never succeeds, 
    #   but a POLLHUP does.  Previously this lead to a busy loop, which 
    #   is what this method fixes.
    ###
    def handle_expt(self):
        if self._is_closed:
            message = 'Handle exceptional event called on closed channel.'
            self.msglog(message, msglog.types.INFO)
            if self.monitor.has_channel(self):
                message = 'Channel %r (fd %d) still being monitoed.  '
                message += 'Close will be invoked explicitly.'
                message = message % (self, self.file_descriptor())
                self.msglog(message, msglog.types.WARN)
                self.close()
                message = 'Handle exceptional event forced close.'
            else:
                message = 'Handle exception event ignored: channel closed'
        else:
            message = 'Channel %r (fd %d) handling exceptional event.  '
            message = message % (self, self.file_descriptor())
            self.msglog(message, msglog.types.INFO)
            try:
                readable, writable, exc = select.select([self._fileno], 
                                                        [self._fileno], 
                                                        [self._fileno], 0)
                flags, handlers = [], []
                if readable:
                    flags.append('readable')
                    handlers.append(self.handle_read_event)
                if writable:
                    flags.append('writable')
                    handlers.append(self.handle_write_event)
                if exc:
                    flags.append('exception')
                message = 'Select indicates: %s' % string.join(flags, ', ')
                self.msglog(message, msglog.types.INFO)
                while handlers and not self._is_closed:
                    handler = handlers.pop(0)
                    try: 
                        handler()
                    except:
                        self.handle_error()
            finally:
                if not self._is_closed:
                    self.close()
                    message = 'Channel with exceptional event still open.  '
                    message += 'Invoked close explicitly to avoid loop.'
                    self.msglog(message, msglog.types.WARN)
            message = 'Exceptional event handled by %s' % repr(self)
        self.msglog(message, msglog.types.INFO)
    def __repr__(self):
        status = ['%s #%d' % (self.__class__.__name__, self.channel_number)]
        try:
            information = []
            if self._is_closed:
                information.append('closed')
            elif self._connection_initiated:
                if self._is_connected:
                    connectiondata = 'connected '
                else:
                    connectiondata = 'connecting '
                if self._using_ssl:
                    connectiondata += 'SSL '
                connectiondata += 'socket [%d]' % self.file_descriptor()
                information.append(connectiondata)
            else:
                information.append('no connection')
            information.append('%d requests' % self.request_counter.value)
            information.append('%d responses' % self.response_counter.value)
            if self.addr is not None:
                try:
                    information.append('%s:%d' % self.addr)
                except TypeError:
                    information.append(repr(self.addr))
            status.extend(['(%s)' % info for info in information])
        except:
            msglog.exception(prefix = 'Handled')
        return '<%s at %#x>' % (' '.join(status), id(self))
    def __str__(self):
        return '%s #%d' % (self.__class__.__name__, self.channel_number)

def crack_responseline(responseline):
    try:
        [version, status, reason] = responseline.split(None, 2)
    except ValueError:
        try:
            [version, status], reason = responseline.split(None, 1), ""
        except ValueError:
            # empty version will cause next test to fail and status
            # will be treated as 0.9 response.
            version = ""
    if not version.startswith('HTTP/'):
        raise ValueError('Version does not start with HTTP/')
    status = int(status)
    if status < 100 or status > 999:
        raise ValueError('Invalid status code', status)
    return version, status, reason


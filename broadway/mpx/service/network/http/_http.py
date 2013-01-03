"""
Copyright (C) 2001 2002 2003 2008 2009 2010 2011 Cisco Systems

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
import os
import re
import struct
import string
import sys
import time
import Queue
import asyncore
from cStringIO import StringIO
from asynchat import async_chat as AsyncChat
from errno import EWOULDBLOCK
from urllib import unquote
from mpx import properties
from mpx.lib import msglog,socket
from mpx.lib.threading import Lock
from mpx.lib.threading import Event
from mpx.service.network.http.responders import Responder
from mpx.service.network.utilities.counting import Counter
from mpx.service.network.async.connection.trigger import Trigger
from _request import Request
from _request import crack_request

VERSION_STRING = properties.RELEASE
_tmp_dir = properties.get('TEMP_DIR')

# Map of all sockets used by Redusa (so other threads can use asyncore to).
REDUSA_SOCKET_MAP = {}

class Channel(AsyncChat, object):
    request_manager = Request.singleton.request_manager
    ac_out_buffer_size = 1 << 16
    current_request = None
    channel_counter = Counter()
    linger = struct.pack("ii",0,0)
    def __init__(self, server, conn, addr):
        self.channel_number = Channel.channel_counter.increment()
        self.addr = addr
        self.server = server
        # Leaving out connection and map because we set them below.
        AsyncChat.__init__(self)
        self._map = REDUSA_SOCKET_MAP
        self._in_buffer = ''
        self._current_request = None
        self._null_request = _NullRequest()
        self._request_queue = [self._null_request]
        self._keep_alive = 1
        self._last_use = int(time.time())
        self.check_maintenance()
        self.set_socket(conn, self._map)
        self.socket.setblocking(0)
        self._is_connected = True
        self.connected = True
        self._setup_counters()
        self.reset()
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
            bytesperrequest = bytesin / requests
            bytesperread = bytesin / readcalls
            readsperrequest = readcalls / requests
            readablesperread = readablecalls / readcalls
            averages.append('Bytes per request: %0.1f' % bytesperrequest)
            averages.append('Reads per request: %0.1f' % readsperrequest)
            averages.append('Readables per read: %0.1f' % readablesperread)
            averages.append('Bytes per read: %0.1f' % bytesperread) 
        if responses:
            bytesperresponse = bytesout / responses
            bytesperwrite = bytesout / writecalls
            writesperresponse = writecalls / responses
            refillsperresponse = refills / responses
            bytesperrefill = bytesout / refills
            responsesperrefill = responses / refills
            writablesperwrite = writablecalls / writecalls
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
    def set_socket(self, sock, map = None):
        AsyncChat.set_socket(self, sock, map)
        # Ensure that we never block waiting for a socket to close.
        self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,self.linger)
    def server_name(self):
        return self.server.name
    def close_when_done(self):
        self._keep_alive = 0
    def reset_terminator(self):
        self.set_terminator('\r\n\r\n')
    def reset(self):
        self._current_request = None
        self.reset_terminator()
    def request_handled(self,request):
        if request is self._request_queue[0]:
            self.server.response_ready(self)
    def writable(self):
        self.writable_calls.increment()
        return AsyncChat.writable(self) or self._request_queue[0].writable()
    def refill_buffer(self):
        responsecount = self.response_counter.value
        requests = self._request_queue
        while requests[0].writable():
            self.response_counter.increment()
            self.producer_fifo.push(requests.pop(0).out)
        if requests[0] is self._null_request and not self._keep_alive:
            self.producer_fifo.push(None)
        if responsecount < self.response_counter.value:
            # Discards final call to make averages more pertinent
            self.buffer_refills.increment()
        else:
            self.refill_skips.increment()
        return AsyncChat.refill_buffer(self)
    def readable (self):
        # Use of accepting requests here keeps from blocking asyncore.
        self.readable_calls.increment()
        return (AsyncChat.readable(self) and 
                self.request_manager.accepting_requests())
    def __repr__(self):
        ar = AsyncChat.__repr__(self)[1:-1]
        return '<%s channel#: %s requests:%s>' % (ar,self.channel_number,
                                                  self.request_counter)
    def __str__(self):
        ar = AsyncChat.__repr__(self)[1:-1]
        return ('%s, Channel #%s, requests processed: %s' %
                (ar,self.channel_number,self.request_counter))
    def check_maintenance(self):
        if not self.channel_number % self.server.maintenance_interval:
            self.maintenance()
    def maintenance(self):
        self.kill_zombies()
    def kill_zombies(self):
        now = int(time.time())
        for channel in self._map.values():
            if isinstance(channel, Channel):
                if (now - channel._last_use) > channel.server.zombie_timeout:
                    channel.die_if_zombie()
    def die_if_zombie(self):
        if self.writable():
            self._last_use = int(time.time())
        else:
            self.close()
    def send(self,data):
        self.write_calls.increment()
        bytecount = 0
        if self._is_connected:
            bytecount = AsyncChat.send(self, data)
        self.bytes_out.increment(bytecount)
        self.server.bytes_out.increment(bytecount)
        return bytecount
    def recv(self,buffer_size):
        self.read_calls.increment()
        try:
            result = AsyncChat.recv(self,buffer_size)
        except MemoryError:
            sys.exit("Out of Memory!")
        bytecount = len(result)
        self.bytes_in.increment(bytecount)
        self.server.bytes_in.increment(bytecount)
        return result
    def handle_error(self):
        t,v = sys.exc_info()[:2]
        if t is SystemExit:
            raise t,v
        msglog.exception(msglog.types.ERR,None,'Handled')
        self.close()
    def log(self,*args):
        pass
    def collect_incoming_data(self,data):
        if self._current_request:
            # we are receiving data (probably POST data) for a request
            self._current_request.collect_incoming_data(data)
        else:
            # we are receiving header (request) data
            self._in_buffer += data
    def found_terminator(self):
        self._last_use = int(time.time())
        if self._current_request:
            self._current_request.found_terminator()
        else:
            header, self._in_buffer = self._in_buffer, ''
            lines = string.split(header, '\r\n')
            while lines and not lines[0]:
                lines.pop(0)
            if not lines:
                self.close_when_done()
                return
            request = lines.pop(0)
            try:
                command,uri,version = crack_request(request)
            except:
                if self.server.debug:
                   self.log_info( "Ignoring malformed HTTP request: " + request )
                return
            if '%' in request:
                request = unquote(request)            
            if command is None:
                self.log_info('Bad HTTP request: %s' % repr(request),'error')
                return
            header = _join_headers(lines)
            self._current_request = Request(self, request, command, 
                                            uri, version, header)
            requests = self._request_queue
            requests.insert(len(requests) - 1, self._current_request)
            self.request_counter.increment()
            self.server.total_requests.increment()
            self._current_request.found_terminator()
    def push_with_producer(self,producer):
        self.producer_fifo.push(producer)
    def log_info(self,message,type=msglog.types.INFO):
        if type == msglog.types.DB and not self.server.debug:
            return
        prefix = '%s, Channel %s' % (self.server, self.channel_number)
        msglog.log(prefix, type, message)
    def log_statistics(self):
        self.log_info('\n%s\n' % self.get_statistics(), msglog.types.DB)
    def close(self):
        self._is_connected = False
        if self._current_request:
            try:
                self._current_request.handle_close()
            except:
                msglog.exception(prefix = 'Handled')
        AsyncChat.close(self)
        self.log_info('closed.', msglog.types.DB)
    def add_channel (self, map=None):
        if map is None:
            map = REDUSA_SOCKET_MAP
        assert map is REDUSA_SOCKET_MAP, 'Hack assumes that the map argument is None...'
        return asyncore.dispatcher.add_channel(self, map)
    def del_channel (self, map=None):
        if map is None:
            map = REDUSA_SOCKET_MAP
        assert map is REDUSA_SOCKET_MAP, 'Hack assumes that the map argument is None...'
        return asyncore.dispatcher.del_channel(self, map)

class _NullRequest(object):
    def writable(self):
        return False
    def readable(self):
        return False
    def handle_close(self):
        pass

##
# @fixme computing ip address.  should use mpx.lib.ifconfig.ip_address and 
# pass in the interface eth0, eth1
class HTTPServer(asyncore.dispatcher):
    PROTOCOL = "HTTP"
    SERVER_IDENT = '%s Server (%s)' % (PROTOCOL, VERSION_STRING)
    channel_class = Channel
    event_channel = Trigger(REDUSA_SOCKET_MAP)
    def __init__(self,ip,port,user_manager,realm,authentication,
                 maintenance_interval=25,zombie_timeout=600,debug=0):
        self.debug = debug
        self.name = ip
        self.port = port
        self.user_manager = user_manager
        self.realm = realm
        self.authentication = authentication
        self.maintenance_interval = maintenance_interval
        self.zombie_timeout = zombie_timeout
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
        # Note the double-reference for backwards comatibility.
        self.request_handlers = self.handlers = []
        self.response_handlers = []
        self.set_reuse_addr()
        self.bind((ip,port))
        self.listen(1024)
        host,port = self.socket.getsockname()
        try:
            if not ip:
                self.log_info('Computing default hostname',msglog.types.WARN)
                ip = socket.gethostbyname(socket.gethostname())
            self.name = socket.gethostbyaddr(ip)[0]
        except socket.error:
            self.name = ip
            self.log_info('Cannot do reverse lookup',msglog.types.WARN)
        self.total_clients = Counter()
        self.total_requests = Counter()
        self.exceptions = Counter()
        self.bytes_out = Counter()
        self.bytes_in  = Counter()
        self.log_info('Started')
    def protocol(self):
        return self.PROTOCOL
    def __str__(self):
        name = self.name
        if not name:
            name = self.SERVER_IDENT
        if self.port:
            name = '%s:%s' % (name,self.port)
        return name
    def log_info(self,message,type=msglog.types.INFO):
        if type == msglog.types.DB and not self.debug:
            return
        msglog.log(str(self),type,message)
    def writable(self):
        return 0
    def response_ready(self, channel):
        self.event_channel.trigger_event()
    def handle_read(self):
        pass
    def readable(self):
        return self.accepting
    def handle_connect(self):
        pass
    def handle_accept(self):
        self.total_clients.increment()
        try:
            conn,addr = self.accept()
        except socket.error:
            # linux: on rare occasions we get a bogus socket back from
            # accept.  socketmodule.c:makesockaddr complains that the
            # address family is unknown.  We don't want the whole server
            # to shut down because of this.
            self.log_info('warning: server accept() threw an exception',
                          msglog.types.WARN)
            return
        except TypeError:
            # unpack non-sequence.  this can happen when a read event
            # fires on a listening socket, but when we call accept()
            # we get EWOULDBLOCK, so dispatcher.accept() returns None.
            # Seen on FreeBSD3.
            self.log_info('warning: server accept() threw EWOULDBLOCK',
                          msglog.types.WARN)
            return
        self.channel_class(self,conn,addr)
    def install_handler(self,handler,back=0):
        if isinstance(handler, Responder):
            self.install_response_handler(handler, back)
        else:
            self.install_request_handler(handler, back)
    def remove_handler(self, handler):
        if isinstance(handler, Responder):
            self.remove_response_handler(handler)
        else:
            self.remove_request_handler(handler)
    def install_request_handler(self, handler, back=0):
        if handler not in self.request_handlers:
            if back:
                self.request_handlers.append(handler)
            else:
                self.request_handlers.insert(0,handler)
    def remove_request_handler(self, handler):
        self.request_handlers.remove(handler)
    def install_response_handler(self, responder, back=0):
        if responder not in self.response_handlers:
            if back or responder.isumbrella():
                self.response_handlers.append(responder)
            else:
                self.response_handlers.insert(0, responder)
    def remove_response_handler(self, responder):
        self.response_handlers.remove(responder)
        
    #
    # REDUSA_SOCKET_MAP HACK:
    #
    # This section forces a Redusa specific socket_map so it will play nice
    # with with other threads that use asyncore.
    #
    def add_channel (self, map=None):
        assert map is None, 'Hack assumes that the map argument is None...'
        return asyncore.dispatcher.add_channel(self, REDUSA_SOCKET_MAP)
    def del_channel (self, map=None):
        assert map is None, 'Hack assumes that the map argument is None...'
        return asyncore.dispatcher.del_channel(self, REDUSA_SOCKET_MAP)

# merge multi-line headers
# [486dx2: ~500/sec]
def _join_headers(headers):
    r = []
    for i in range(len(headers)):
        if headers[i][0] in ' \t':	
            r[-1] = r[-1] + headers[i][1:]
        else:
            r.append(headers[i])
    return r

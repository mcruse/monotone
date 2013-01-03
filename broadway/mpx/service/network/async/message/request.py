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
import string
import asynchat
from threading import Event
from urllib2 import Request as _Request
from urllib import splitnport
from mpx.lib import msglog
from mpx.service.network.http.producers import SimpleProducer
from mpx.service.network.http.producers import ChunkedProducer
from mpx.service.network.http.producers import CompositeProducer
from mpx.service.network.http.producers import HookedProducer
from mpx.service.network.http.producers import GlobbingProducer
from mpx.service.network.async.message.header import Header
from mpx.service.network.async.message.header import HeaderDictionary

class Request(_Request, object):
    def __init__(self, url, data = None, headers = {}, version = 'HTTP/1.1'):
        self._setupflags()
        self._debuglevel = 0
        self._response = None
        self._cookies = []
        self._request_line = None
        self._header_producer = None
        self._body_producer = None
        self._outgoing_producer = None
        self._state_listeners = []
        _Request.__init__(self, url, None, headers)
        self.headers = HeaderDictionary.from_name_value_dict(self.headers)
        self._set_version(version)
        self.set_data(data)
    def _setupflags(self):
        self._headers_built = Event()
        self._headers_built.clear()
        self._has_response = Event()
        self._has_response.clear() 
    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        status.append('at %#x' % id(self))
        information = [self.get_full_url()]
        if self.has_response():
            information.append('handled')
        else:
            information.append('pending')
        status.extend(['(%s)' % info for info in information])
        return '<%s>' % (' '.join(status))
    def is_persistent(self):
        return not self._will_close
    def is_idempotent(self):
        return not self.get_method().lower() != 'post'
    def get_version(self):
        return self.version
    def get_port(self):
        if self.port is None:
            self.get_host()
        return self.port
    def get_host(self):
        _Request.get_host(self)
        if self.port is None:
            if self.get_type() == 'http':
                default = 80
            elif self.get_type() == 'https':
                default = 443
            else:
                raise ValueError('Unsupported type.', self.get_type())
            self.host, self.port = splitnport(self.host, default)
        return self.host
    def get_method(self):
        if self.has_data():
            return "POST"
        else:
            return "GET"
    def has_response(self):
        return self._has_response.isSet()
    def add_state_listener(self, callback):
        self._state_listeners.append(callback)
    def await_response(self, timeout = None):
        self._has_response.wait(timeout)
        return self.has_response()
    def get_response(self):
        return self._response
    def has_header(self, name):
        return self.headers.has_header_named(name)
    def get_header(self, name, default = None):
        if not isinstance(self.headers, HeaderDictionary):
            return _Request.get_header(self, name, default)
        return self.headers.get_header_value(name, default)
    def get_debuglevel(self):
        return self._debuglevel
    def get_outgoing_producer(self):
        if not self._outgoing_producer:
            self._build_outgoing_producer()
        return self._outgoing_producer
    def will_close(self):
        return self._will_close    
    def add_header(self, name, value):
        self._assert_modifiable()
        header = Header(name, value)
        self.headers.add_header(header)
    def add_cookie(self, cookie):
        self._assert_modifiable()
        self._cookies.append(cookie)
    def set_data(self, data):
        self._assert_modifiable()
        self.data = data
        if self.data is not None:
            if isinstance(self.data, str):
                self.add_header('Content-Length', str(len(self.data)))
            else:
                self.add_header('Transfer-Encoding', 'chunked')
    def set_debuglevel(self, level):
        self._assert_modifiable()
        self._debuglevel = level
    def set_response(self, response):
        self._response = response
        self._has_response.set()
        while self._state_listeners:
            listener = self._state_listeners.pop(0)
            try:
                listener(self)
            except:
                msglog.log('broadway', msglog.types.WARN, 
                           'Invocation of response listener failed.')
                msglog.exception(prefix = 'Handled')
        assert len(self._state_listeners) == 0
    def is_readonly(self):
        return self._headers_built.isSet()
    def is_modifiable(self):
        return not self.is_readonly()
    def _assert_modifiable(self):
        if not self.is_modifiable():
            raise Exception('HTTP Request can no longer be modified.')
    def _set_version(self, version):
        self._assert_modifiable()
        self.version = version.upper().strip()
        if self.version == 'HTTP/1.0':
            self._version = 10
        elif self.version.startswith('HTTP/1.'):
            self._version = 11   # use HTTP/1.1 code for HTTP/1.x where x>=1
        elif self.version == 'HTTP/0.9':
            self._version = 9
        else:
            raise ValueError('Unknown version.', self.version)
    def _set_connection_behaviour(self):
        connection = self.get_header('connection', '').lower()
        if self._version == 11:
            if connection.find("close") >= 0:
                self._will_close = True
            else:
                self._will_close = False
        elif self.has_header('keep-alive'):
            self._will_close = False
        elif connection.find("keep-alive") >= 0:
            self._will_close = False
        else:
            pconnection = self.get_header('proxy-connection', '').lower()
            if pconnection.find("keep-alive") >= 0:
                self._will_close = False
            else:
                self._will_close = True
        return self._will_close
    def _build_requestline(self):
        if not self._request_line:
            self._request_line = '%s %s %s' % (self.get_method(), 
                                               self.get_selector(), 
                                               self.get_version())
        return self._request_line
    def _build_header_producer(self):
        if self._header_producer is None:
            self._headers_built.set()
            headers = self.headers.to_strings()
            headers.insert(0, self._build_requestline())
            headers += [cookie.output() for cookie in self._cookies]
            headers = string.join(headers + ['\r\n'], '\r\n')
            self._header_producer = SimpleProducer(headers)
        return self._header_producer
    def _build_body_producer(self):
        if self._body_producer is None:
            outgoing_producer = self.data
            if self.has_header('content-length'):
                outgoing_producer = SimpleProducer(outgoing_producer)
            encoding = self.get_header('content-encoding', '')
            if encoding.lower() == 'chunked':
                outgoing_producer = StreamingProducer(outgoing_producer)
                outgoing_producer = ChunkedProducer(outgoing_producer)
            self._body_producer = outgoing_producer
        return self._body_producer
    def _build_outgoing_producer(self):
        if not self._outgoing_producer:
            outgoing_producers = [self._build_header_producer()]
            body_producer = self._build_body_producer()
            if body_producer is not None:
                outgoing_producers.append(body_producer)
            outgoing_fifo = asynchat.fifo(outgoing_producers)
            outgoing_producer = CompositeProducer(outgoing_fifo)
            if self.get_debuglevel() > 0:
                outgoing_producer = HookedProducer(outgoing_producer, self.log)
            outgoing_producer = GlobbingProducer(outgoing_producer)
            self._outgoing_producer = outgoing_producer
        return self._outgoing_producer
    def log(self, bytes):
        message = 'Client request [%s] sent %d bytes to %s'
        msglog.log('broadway', msglog.types.DB, 
                   message % (self._build_requestline(), bytes))


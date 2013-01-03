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
from threading import Event
from mpx.service.network.async.message.readers import ContentReader
from mpx.service.network.async.message.readers import ChunkedContentReader
from mpx.service.network.async.message.readers import ClosingContentReader

class Response(object):
    def __init__(self, version, status, reason, headers):
        self._content_reader = None
        self._chunked = None
        self._will_close = None
        self._content_length = None
        self._has_reader = Event()
        self._state_listeners = []
        self.configure(version, status, reason, headers)
    def configure(self, version, status, reason, headers):
        self._set_version(version)
        self._set_status(status)
        self._set_reason(reason)
        self._set_headers(headers)
        self._set_connection_behaviour()
    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        status.append('at %#x' % id(self))
        information = ['%s %s %s' % (self.status, self.reason, self.version)]
        if self.is_complete():
            information.append('complete')
        else:
            information.append('loading')
        status.extend(['(%s)' % info for info in information])
        return '<%s>' % (' '.join(status))      
    def read(self, bytes = -1):
        return self._content_reader.read(bytes)
    def getvalue(self):
        return self._content_reader.getvalue()
    def await_completion(self, timeout = None):
        self._has_reader.wait()
        self._content_reader.await_completion(timeout)
        return self._content_reader.is_complete()
    def get_reader(self):
        return self._content_reader
    def add_state_listener(self, callback):
        self._state_listeners.append(callback)
    def is_complete(self):
        return self._has_reader.isSet() and self._content_reader.is_complete()
    def will_close(self):
        return self._will_close
    def get_terminator(self):
        return self._content_reader.get_terminator()
    def get_header(self, name, default = None):
        return self.headers.get_header_value(name, default)
    def has_header(self, name):
        return self.headers.has_header_named(name)
    def handle_close(self):
        self._content_reader.handle_close()
    def collect_incoming_data(self, data):
        self._content_reader.collect_incoming_data(data)
    def found_terminator(self):
        if not self._content_reader:
            self._setup_reader()
            self._has_reader.set()
            while self._state_listeners:
                listener = self._state_listeners.pop(0)
                try:
                    listener(self)
                except:
                    msglog.exception()
        self._content_reader.found_terminator()
    def get_version(self):
        return self.version
    def get_status(self):
        return self.status
    def get_status_number(self):
        return int(self.get_status())
    def get_status_category(self):
        return _status_category(self.get_status_number())
    def handled_properly(self):
        statusnumber = self.get_status_number()
        return statusnumber >= 200 and statusnumber < 300
    def get_reason(self):
        return self.reason
    def _set_version(self, version):
        self.version = version.strip()
        if self.version == 'HTTP/1.0':
            self._version = 10
        elif self.version.startswith('HTTP/1.'):
            self._version = 11   # use HTTP/1.1 code for HTTP/1.x where x>=1
        elif self.version == 'HTTP/0.9':
            self._version = 9
        else:
            raise ValueError('Unknown version.', self.version)
    def _set_status(self, status):
        self.status = status
    def _set_reason(self, reason):
        self.reason = reason.strip()
    def _set_headers(self, headers):
        self.headers = headers
    def _setup_reader(self):
        encoding = self.get_header('transfer-encoding')
        if encoding and encoding.lower() == "chunked":
            self._chunked = 1
        else:
            self._chunked = 0
            length = self.get_header('content-length')
            if length and not self._chunked:
                try: 
                    self._content_length = int(length)
                except ValueError:
                    self.length = None
        if self._chunked:
            self._content_reader = ChunkedContentReader()
        elif self._content_length is not None:
            self._content_reader = ContentReader(self._content_length)
        elif self.will_close():
            self._content_reader = ClosingContentReader()
        else:
            raise TypeError('Unknown content management.')
    def _set_connection_behaviour(self):
        connection = self.get_header('connection', '').lower()
        if self.version == 11:
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

def _status_category(status):
    if status >= 100 and status < 200:
        return 'Informational'
    elif status >= 200 and status < 300:
        return 'Successful'
    elif status >= 300 and status < 400:
        return 'Redirection'
    elif status >= 400 and status < 500:
        return 'Client Error'
    elif status >= 500 and status < 600:
        return 'Server Error'
    raise ValueError('Invalid status', status)


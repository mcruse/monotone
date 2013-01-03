"""
Copyright (C) 2002 2003 2008 2010 2011 Cisco Systems

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
import base64
import select
import StringIO
import urlparse
import string
from httplib import FakeSocket
from mpx import properties
from mpx.lib import socket
from mpx.lib.configure import REQUIRED, set_attribute, \
     get_attribute, as_boolean
from mpx.lib.exceptions import ETimeout
from mpx.service.data import Transporter
from mpx.lib import msglog
from _transporter_exceptions import ETransporter
from mpx.service.network.http.producers import StreamingProducer, \
     ChunkedProducer, SimpleProducer
     
HTTP_PORT = 80
HTTPS_PORT = 443

##
# Generic HTTP post transporter.
#
class HTTPPostTransporter(Transporter):
    def configure(self, config):
        set_attribute(self, 'post_url', REQUIRED, config)
        set_attribute(self, 'chunked_data', 0, config, as_boolean)
        set_attribute(self, 'debug', 0, config, as_boolean)
        set_attribute(self, 'content_type', 'text/html', config)
        set_attribute(self, 'timeout', None, config, float)
        set_attribute(self, 'user', '', config)
        set_attribute(self, 'password', '', config)
        if not self.chunked_data:
            msglog.log('broadway', msglog.types.WARN, 
                       'Exporter will not stream because chunked_data=0')
        url_tuple = urlparse.urlsplit(self.post_url)
        self._server = string.split(url_tuple[1],':')[0]
        if url_tuple[0] == 'http':
            self._port = HTTP_PORT
            self._secure = False
        else:
            self._port = HTTPS_PORT
            self._secure = True
        if ':' in url_tuple[1]:            
            self._port = int(string.split(url_tuple[1],':')[1])
        self._url = urlparse.urlunsplit(('','') + url_tuple[2:])
        Transporter.configure(self, config)
    def configuration(self):
        config = Transporter.configuration(self)
        get_attribute(self, 'post_url', config)
        get_attribute(self, 'chunked_data', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'content_type', config)
        get_attribute(self, 'timeout', config, str)
        return config
    def msglog(self,msg,force=0):     
        if self.debug or force:
            msglog.log('broadway.mpx.service.data.http_post_transporter',
                       msglog.types.DB,'%s -> %s' % (self.name,msg)) 
    def start(self):
        if not self.chunked_data:
            msglog.log('broadway',msglog.types.WARN,
                       'Chunking disabled in exporter, will not stream data')
        return Transporter.start(self)
    ##
    # @todo Check response for chunked transports to see if error
    #       code 411 (length required) is returned and resend correctly
    #       if so, logging warning and changing config not to chunk.
    def transport(self, data):
        # ********************************
        # *** WARNING WILL ROBINSON!!! ***
        # Construct the header as a single TCP/IP "message".  Some (all?)
        # webservers close the connection if the header is not recieved
        # in a single call to recv() on their socket.
        header  = 'POST %s HTTP/1.1\r\n' % self._url
        header += 'Host: %s:%s\r\n' % (self._server,self._port)
        header += 'Content-Type: %s\r\n' % self.content_type
        if self.user:
            header += 'Authorization: Basic %s\r\n' % \
                self._build_base64string(self.user, self.password)
        header += 'Connection: close\r\n'
        if type(data) == type(''):
            header += 'Content-Length: %s\r\n' % len(data)
            producer = SimpleProducer(data)  
        elif self.chunked_data:
            producer = ChunkedProducer(StreamingProducer(data))
            header += 'Transfer-Encoding: chunked\r\n'
        else:
            self.msglog('Reading data for transport')
            buffer = StringIO.StringIO()
            read = data.read(1024)
            while read:
                buffer.write(read)
                read = data.read(1024)
            buffer.seek(0)
            producer = StreamingProducer(buffer)
            header += 'Content-Length: %s\r\n' % buffer.len
            self.msglog('Data read, going to transport %s bytes' % buffer.len)
        header += '\r\n'
        s = self._get_ready_socket()
        self.msglog('Going to write to server')
        data = header
        # Doing output polls to make sure that we do not hang
        while data:
            try:
                data = data[s.send(data):]
            except ETimeout:
                s.close()
                tp = msglog.types.WARN
                msglog.log('broadway.mpx.service.data.http_post_transporter',
                           tp,'HTTP Post transport failed.  Send Timed out.')
                raise
            if not data:
                data = producer.more()
        self.msglog('Going to read from server')
        response = StringIO.StringIO()
        # Doing input polls to make sure we dont hang.
        loop = 1
        data = ''
        while loop:
            try:
                data = s.recv(1024)
            except ETimeout:
                s.close()
                print len(data)
                print data
                tp = msglog.types.WARN
                msglog.log('broadway.mpx.service.data.http_post_transporter',
                           tp,'HTTP Post transport failed.  Receive Timed out.')
                raise
            except:
                # @fixme - there's an issue with recv()'ing from SafetySockets and the other 
                # end closing.  See Roundup issue 33.  See if we have enough to data to ack
                # the POST.
                response.write(data)
                if response.len == 0:
                    # we got nothing - raise so that we retry.
                    msglog.exception()
                    raise
                break
            loop = len(data)
            response.write(data)

        s.close()
        self.msglog('Done reading from server')
        response.seek(0)
        headers = string.split(response.read(),'\r\n\r\n')
        while headers:
            header = headers.pop(0)
            if string.split(header,'\r\n')[0].find(' 200 ') >= 0:
                break
        else:
            response.seek(0)
            raise ETransporter(('Error response from %s: "%s"') % 
                               (response.read(), self.post_url))
        self.msglog('Received valid response from server')
        return
    def _get_ready_socket(self):
        sock = socket.safety_socket(self.timeout, socket.AF_INET, socket.SOCK_STREAM)
        self.msglog('Going to connect to server')
        sock.connect((self._server, self._port))
        http_sock = sock
        if self._secure:
            realsock = sock
            if hasattr(sock, '_sock'):
                realsock = sock._sock
            ssl = socket.ssl(
                realsock, 
                properties.PRIVATE_KEY_FILE, 
                properties.CERTIFICATE_PEM_FILE
            )
            http_sock = FakeSocket(sock, ssl)
        return http_sock
        
    def _build_base64string(self, user, password):
        s = base64.encodestring(
            '%s:%s' % (user, password)
        )[:-1]
        return s

def factory():
    return HTTPPostTransporter()

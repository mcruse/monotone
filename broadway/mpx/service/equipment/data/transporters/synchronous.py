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
import urlparse
import string
import StringIO
from mpx.lib import msglog
from mpx.lib import socket
from mpx.lib.exceptions import ETimeout
from mpx.lib.neode.node import ConfigurableNode
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.configure import as_boolean
from mpx.componentry import implements
from mpx.service.network.http.producers import SimpleProducer
from mpx.service.network.http.producers import ChunkedProducer
from mpx.service.network.http.producers import StreamingProducer
from interfaces import *

class HTTPPostTransporter(ConfigurableNode):
    implements(ITransporter)
    
    def configure(self, config):
        set_attribute(self, 'chunked_data', 0, config, as_boolean)
        set_attribute(self, 'debug', 0, config, as_boolean)
        set_attribute(self, 'content_type', 'text/html', config)
        set_attribute(self, 'timeout', None, config, float)
        if not self.chunked_data:
            msglog.log('broadway', msglog.types.WARN, 
                       'Exporter will not stream because chunked_data=0')
        super(HTTPPostTransporter, self).configure(config)
    def configuration(self):
        config = super(HTTPPostTransporter, self).configuration()
        get_attribute(self, 'chunked_data', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'content_type', config)
        get_attribute(self, 'timeout', config, str)
        return config
    def msglog(self,msg,force=0):     
        if self.debug or force:
            msglog.log('broadway.mpx.service.data.http_post_transporter',
                       msglog.types.DB,'%s -> %s' % (self.name,msg)) 
    def transport(self, datastream, target):
        targeturl = _TargetURL(target)
        contenttype = getattr(datastream, 'mimetype', self.content_type)
        header  = 'POST %s HTTP/1.1\r\n' % targeturl.get_url()
        header += 'Host: %s:%s\r\n' % (targeturl.get_server(),targeturl.get_port())        
        header += 'Content-Type: %s\r\n' % contenttype
        header += 'Connection: close\r\n'
        if isinstance(datastream, str):
            header += 'Content-Length: %s\r\n' % len(datastream)
            producer = SimpleProducer(datastream)  
        elif self.chunked_data:
            producer = ChunkedProducer(StreamingProducer(datastream))
            header += 'Transfer-Encoding: chunked\r\n'
        else:
            if not isinstance(datastream, StringIO.StringIO):
                self.msglog('Reading data for transport')
                buffer = StringIO.StringIO()
                read = datastream.read(1024)
                while read:
                    buffer.write(read)
                    read = datastream.read(1024)
            else: 
                buffer = datastream
            buffer.seek(0)
            producer = StreamingProducer(buffer)
            header += 'Content-Length: %s\r\n' % buffer.len
            self.msglog('Data read, going to transport %s bytes' % buffer.len)
        header += '\r\n'
        s = socket.safety_socket(self.timeout,socket.AF_INET,socket.SOCK_STREAM)
        self.msglog('Going to connect to server')
        s.connect((targeturl.get_server(), targeturl.get_port()))
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
        while loop:
            try:
                data = s.recv(1024)
            except ETimeout:
                s.close()
                tp = msglog.types.WARN
                msglog.log('broadway.mpx.service.data.http_post_transporter',
                           tp,'HTTP Post transport failed.  Receive Timed out.')
                raise
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
            raise TypeError(
                'Error response from %s: "%s"' % (
                    response.read(), targeturl.get_target()))
        return

class _TargetURL(object):
    def __init__(self, target_url):
        self.target_url = target_url
        url_tuple = urlparse.urlsplit(self.target_url)
        self.server = string.split(url_tuple[1],':')[0]
        self.port = 80
        if ':' in url_tuple[1]:            
            self.port = int(string.split(url_tuple[1],':')[1])
        self.url = urlparse.urlunsplit(('','') + url_tuple[2:])
    def get_target(self):
        return self.target_url
    def get_url(self):
        return self.url
    def get_server(self):
        return self.server
    def get_port(self):
        return self.port


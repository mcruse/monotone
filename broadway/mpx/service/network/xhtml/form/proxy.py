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
import urllib
import string
import socket
import urlparse
from StringIO import StringIO
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.service.network.xhtml import xmldata
DEBUG = False

class HTMLFormProxy(CompositeNode):
    def __init__(self, *args):
        self.port = 80
        self.action = None
        self.server = None
        self.method = None
        self.inputs = None
        self.urlpath = None        
        self.results = None
        self.timeout = None
        self.current_method = None
        self.contenttype = "application/x-www-form-urlencoded"
        super(HTMLFormProxy, self).__init__(*args)
    def start(self):
        urltuple = urlparse.urlsplit(self.action)
        self.server = string.split(urltuple[1],':')[0]
        if ':' in urltuple[1]:
            self.port = int(string.split(urltuple[1],':')[1])
        self.urlpath = urlparse.urlunsplit(('','') + urltuple[2:])
        super(HTMLFormProxy, self).start()
    def configure(self, config):
        self.action = config.get('action', self.action)
        self.method = config.get('method', self.method)
        self.timeout = config.get('timeout', self.timeout)
        if self.inputs is None:
            self.inputs = InputSet()
            self.inputs.configure({'name': 'Inputs', 'parent': self})
        if self.results is None:
            self.results = xmldata.XMLDataNode()
            self.results.configure({'name': 'Results', 'parent': self})
        if self.timeout is not None:
            try:
                self.timeout = float(self.timeout)
            except:
                error = "'timeout' must be number or None, not %r."
                raise ValueError(error % self.timeout)
        super(HTMLFormProxy, self).configure(config)
    def configuration(self):
        config = super(HTMLFormProxy, self).configuration()
        config['action'] = self.action
        config['method'] = self.method
        config['timeout'] = str(self.timeout)
        return config
    def set(self, method = None):
        query = self.inputs.get()
        if not query:
            # Do not use POST if no data being sent
            self.current_method = 'GET'
        elif str(method) != str(None):
            # Slight hack allows "None" to be used in 
            # place of None so that it works well 
            # when invoked via the NodeBrowser.
            self.current_method = method.upper()
        else:
            self.current_method = self.method.upper()
        querystring = urllib.urlencode(query)
        httprequest = self.generate_request(querystring)
        httpresponse = self.send_request(httprequest)
        response = string.split(httpresponse, '\r\n\r\n', 1)[1]
        self.results.set(response)
    def get(self):
        return self.current_method
    def generate_request(self, data):
        requestpath = self.urlpath
        method = self.current_method
        if method == 'POST':
            content = data
        else:
            if data:
                requestpath += '?%s' % data
            content = ''
        headers  = ['%s %s HTTP/1.1' % (method, requestpath), 
                    'Host: %s:%s' % (self.server, self.port), 
                    'Content-Type: %s' % self.contenttype, 
                    'Connection: close']
        if content:
            headers.append('Content-length: %d' % len(content))
        header = '\r\n'.join(headers)
        return '\r\n\r\n'.join([header, content])
    def send_request(self, request):
        if DEBUG:
            print 'Sending request: \n%s\n' % request
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.timeout is not None:
            connection.settimeout(self.timeout)
        connection.connect((self.server, self.port))
        connection.send(request)
        response = StringIO()
        data = connection.recv(4096)
        while data:
            response.write(data)
            data = connection.recv(4096)
        if DEBUG:
            print 'Got response: \n%s\n' % response.getvalue()
        return response.getvalue()

class InputSet(CompositeNode):
    def get(self):
        query = {}
        for input in self.children_nodes():
            try:
                value = input.get()
            except:
                msglog.log('broadway', msglog.types.WARN, 
                           'Form proxy has failed to get '
                           'value for input "%s"' % input.name)
                msglog.exception(prefix='handled')
            else:
                if value not in ('', None):
                    query[input.name] = value
        return query


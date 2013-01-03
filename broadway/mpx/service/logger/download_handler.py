"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
import time

from mpx.lib import msglog

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import EInternalError

from mpx.lib.node import as_node

from mpx.service.network.http.producers import StreamingProducer
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response

from download_exporters import exporter_factory

class LogDownloadHandler(RequestHandler):
    def __init__(self):
        RequestHandler.__init__(self)
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default /log_download_service
    #
    # @see mpx.lib.service.RequestHandler#configure
    #
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', REQUIRED, config)
        if self.request_path[-1] != '/':
            self.request_path += '/'
        set_attribute(self, 'gm_time', 1, config, as_boolean)
        RequestHandler.configure(self, config)
        self.time_function = time.localtime
        if self.gm_time:
            self.time_function = time.gmtime
        return
    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.RequestHandler#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        return config

    def match(self, path):
        if path.startswith(self.request_path):
            return 1
        return 0

    def download_all(self, request, log, query):
        start_time = 0
        end_time = time.time()
        format = query['format']
        formatter = exporter_factory(format, log)
        self.download_log(request, log, start_time, end_time, formatter)
        return

    def download_slice(self, request, log, query):
        start_time = float(query['from'])
        end_time = float(query['to'])
        format = query['format']
        formatter = exporter_factory(format, log)
        self.download_log(request, log, start_time, end_time, formatter)
        return
    
    def download_sequence(self, request, log, query):
        start = query.get('from', 0)
        end = query.get('to', None)
        format = query.get('format', 'CSV')
        formatter = exporter_factory(format, log)
        if end is not None:
            data = log[int(start): int(end)]
        else: 
            data = log[int(start):]
        self.download_data(request, log, data, formatter)
        return
    
    def download_log(self, request, log, start_time, end_time, formatter):
        data = log.get_slice('timestamp', start_time, end_time)
        self.download_data(request, log, data, formatter)
        return
    
    def download_data(self, request, log, data, formatter):
        response = Response(request)
        response.set_header('Content-Type','application/octet-stream')
        response.set_header(
            'Content-Disposition', 'attachment; filename="%s.csv"' % log.name)
        output = formatter.format(data)
        if not output:
            return request.reply(204)
        if type(output) != type(''):
            output = StreamingProducer(output)
        response.push(output)
        response.done()
        request._DynamicLogHandler__success = True
        return

    ##
    # Called by http_server each time a request comes in whose url mathes one
    # of the paths this handler said it was interested in. 
    #
    # @param request  <code>Request</code> object from the http_server.  To
    #                  send resonse call <code>request.send(html)</code> where
    #                  <code>html</code> is the text response you want to send.
    # @fixme Handle exceptions gracefully and report them back to the client.
    def handle_request(self, request):
        request._DynamicLogHandler__success = False
        path = request.get_path()
        if request.has_query():
            query = request.get_query_dictionary()
            log_name = ""
            if (query.has_key('node_url')):
                log_name = query['node_url']
            else:
                if path[-1] == '/':
                    path = path[0:-1]
                log_name = path[len(self.request_path):]
                log_name = os.path.join('/services/logger', log_name)
            #use as_node to follow Aliases
            log_node = as_node(log_name)
            if (query.has_key('action')):
                action = query['action']
                if action == 'download_all':
                    self.download_all(request, log_node, query)
                elif action == 'download_slice':
                    self.download_slice(request, log_node, query)
                elif action == 'download_sequence':
                    self.download_sequence(request, log_node, query)
        if not request._DynamicLogHandler__success:
            raise EInternalError('Failed to handle request.')
        return

"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import as_node, as_node_url
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.data import _exporter
from mpx.lib.exceptions import ERangeError
from mpx.service.network.http.response import Response

def _days_to_seconds(days):
    return float(days) * 86400
def _seconds_to_days(seconds):
    return str(seconds / 86400)

class _TimeStore(PersistentDataObject):
    def __init__(self, node):
        self.last_time = 0
        PersistentDataObject.__init__(self, node)
    def get_last_time(self):
        if 'last_time' not in self.loaded():
            self.load()
        return self.last_time
    def set_last_time(self, time):
        self.last_time = time
        self.save()

class Exporter(RequestHandler):
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default /enerwise
    #
    # @see mpx.lib.service.RequestHandler#configure
    #
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '/enerwise', config)
        set_attribute(self, 'minimum_backup', 1, config, _days_to_seconds)
        set_attribute(self, 'type', 'exporter', config)
        set_attribute(self, 'log', REQUIRED, config, as_node)
        RequestHandler.configure(self, config)
        self.time = _TimeStore(self)

    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.RequestHandler#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'minimum_backup', config, _seconds_to_days)
        get_attribute(self, 'type', config)
        get_attribute(self, 'log', config, as_node_url)
        return config
    
    def match(self, path):
        if path == self.request_path:
            return 1
        else:
            return 0

    def _add_child(self, child):
        if child.type == _exporter.ChildrenTypes.FORMATTER:
            self.formatter = child
        RequestHandler._add_child(self, child)
        
    def match(self, path):
        if path.startswith('/enerwise'):
            return 1
        return 0
    
    ##
    # Get list of regular expressions for the different
    # request paths that this handler wants to handle.
    #
    # @return List of paths.
    #
    def listens_for(self):
        path_list = [self.request_path]
        return path_list
    
    def scheduled_time(self):
        return self._scheduled_time
    
    ##
    # Called by http_server each time a request comes in whose url mathes one of
    # the paths this handler said it was interested in. 
    #
    # @param request  <code>Request</code> object from the http_server.  To send
    #                  resonse call <code>request.send(html)</code> where
    #                  <code>html</code> is the text response you want to send.
    # @fixme Handle exceptions gracefully and report them back to the client.
    # @fixme Don't convert the incoming values (as soon as we refactor the core
    #        ions).
    # @fixme After override, load the parent page instead of displaying the message.
    def _handle_request(self, request):
        response = Response(request)
        start_time = self.time.get_last_time()
        self._scheduled_time = start_time
        end_time = int(time.time())
        data = []
        try:
            if self.debug:
                msglog.log('enerwise', msglog.types.DB, 'slice from %s to %s' % (start_time, end_time))
            data.extend(self.log.get_slice('timestamp', start_time, end_time))
        except ERangeError, e:
            msglog.exception(msglog.types.WARN, None, 'Handled')
            end_time = e.good_end
            data.extend(self.log.get_slice('timestamp', start_time, end_time))
        self.time.set_last_time(end_time)
        lowest_time = self.log.get_first_logged_value('timestamp')
        if ((end_time - lowest_time) > self.minimum_backup * 2):
            if self.debug:
                msglog.log('enerwise',msglog.types.DB, 'Trimming log before: %s' % \
                           (end_time - self.minimum_backup))
            self.log.trim_lt('timestamp', end_time - self.minimum_backup)
        if not data:
            response.send('No New Data')
        else:
            response.send(self.formatter.format(data))
    
    def handle_request(self, request):
        return self._handle_request(request)

##
# Intaciates and returns RequestHandler.  Allows
# for uniform instaciation of all classes defined
# in framwork.
#
# @return Instance of RequestHandler defined in this module.
#
def factory():
    return Exporter()

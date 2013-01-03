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
import time
import urllib
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, as_boolean
from mpx.lib.node import as_node, as_node_url
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.data import _exporter
from mpx.lib.exceptions import ERangeError
from mpx.service.network.http.response import Response
from mpx.service.network.http.producers import StreamingProducer
from mpx.lib import msglog

class _TimeStore(PersistentDataObject):
    def __init__(self, node):
        self.last_time = {}
        PersistentDataObject.__init__(self, node)
    def get_last_time(self, id, default = 0):
        if 'last_time' not in self.loaded():
            self.load()
        return self.last_time.get(id, default)
    def set_last_time(self, id, time):
        self.last_time[id] = time
        self.save()

class Exporter(RequestHandler):
    def __init__(self):
        self.formatter = None
        RequestHandler.__init__(self)
    def configure(self, config):
        set_attribute(self, 'request_path', REQUIRED, config)
        set_attribute(self, 'gm_time', 0, config, as_boolean)
        RequestHandler.configure(self, config)
        self.time = _TimeStore(self)
        self.time_function = time.localtime
        if self.gm_time:
            self.time_function = time.gmtime
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        return config

    def match(self, path):
        if path == self.request_path:
            return 1
        return 0
    def _add_child(self, child):
        if isinstance(child,_exporter.Formatter):
            if self.formatter is not None:
                raise EInvalidValue('child',child,('Only one formatter can ' +
                                                   'be added to an Exporter'))
            self.formatter = child
        RequestHandler._add_child(self, child)
    def scheduled_time(self):
        return self._scheduled_time
    def handle_request(self, request):
        response = Response(request)
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        logname = urllib.unquote_plus(request_data['log'][0])
        lognode = as_node('/services/logger/%s' % logname)
        if request_data.has_key('start'):
            startvalue = float(urllib.unquote_plus(request_data['start'][0]))
        else: startvalue = self.time.get_last_time(logname)

        if request_data.has_key('end'):
            endvalue = float(urllib.unquote_plus(request_data['end'][0]))
        else: endvalue = int(time.time())

        try: data = lognode.get_slice('timestamp', startvalue, endvalue)
        except ERangeError, e:
            msglog.exception(msglog.types.WARN, None, 'Handled')
            response.send('Too much data, try slice from ' +
                          '%s to %s' % (startvalue, e.good_end))
        else:
            self.time.set_last_time(logname, endvalue)
            if hasattr(self.formatter,'MIME_TYPE'):
                response.set_header('Content-Type',self.formatter.MIME_TYPE)
            else: response.set_header('Content-Type','text/plain')

            output = self.formatter.format(data)
            if not output:
                return request.reply(204)
            if type(output) != type(''):
                output = StreamingProducer(output)
            response.push(output)
            response.done()

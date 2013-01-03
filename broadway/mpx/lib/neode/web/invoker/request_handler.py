"""
Copyright (C) 2010 2011 Cisco Systems

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
from mpx.lib.eventdispatch import Event
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.service.network.http.response import Response

class NodeMethodInvoker(CompositeNode):
    def configure(self, config):
        self.setattr('path', config.get('path','/invoker'))
        super(NodeMethodInvoker, self).configure(config)
        self.debug = 1
    def configuration(self):
        config = super(NodeMethodInvoker, self).configuration()
        config['path'] = self.getattr('path')
        return config
    def match(self, path):
        return path.startswith(self.path)
    def handle_request(self, request):
        response = Response(request)
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        if not (request_data.has_key('type') and
                request_data.has_key('id') and
                request_data.has_key('method')):
            response.error(400, 'Missnig required param type, id, or method.')
            return
        id = urllib.unquote_plus(request_data.get('id')[0])
        if request_data.get('type')[0] == 'node':
            target = as_node(id)
        elif request_data.get('type')[0] == 'event':
            target = Event.get_event(id)
        else:
            response.error(400, 'Unknown type.')
            return
        methodname = urllib.unquote_plus(request_data.get('method')[0])
        method = getattr(target, methodname)
        args = urllib.unquote_plus(request_data.get('args', ['()'])[0])
        args = eval(args)
        keywords = urllib.unquote_plus(request_data.get('keywords', ['{}'])[0])
        keywords = eval(keywords)
        result = method(*args, **keywords)
        result = repr(result)
        self.message('Invoking %s on %s with %s, %s, returned %s' % (
                         methodname, id, args, keywords, result))
        response.send(result)
    def message(self, message, mtype = 'debug'):
        if mtype == 'debug' and not self.debug:
            return
        print 'NodeMethodInvoker: %s' % message

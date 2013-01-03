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
from mpx.lib.neode.node import CompositeNode
from mpx.www.w3c.dom.interfaces import IDomNode
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import ComponentLookupError
from mpx.service.network.http.response import Response

class NodeViewer(CompositeNode):

    def configure(self, config):
        self.setattr('path', config.get('path','/nodeviewer'))
        super(NodeViewer, self).configure(config)

    def configuration(self):
        config = super(NodeViewer, self).configuration()
        config['path'] = self.getattr('path')
        return config

    def match(self, path):
        return path.startswith(self.path)

    def get_node(self, path):
        if path[-1] == '/':
            path = path[0:-1]
        node_url = path[len(self.path):] or '/'
        return self.nodespace.as_node(urllib.unquote(node_url))

    def handle_request(self, request):
        user = request.user_object()
        response = Response(request)
        node = self.get_node(request.get_path())
        try:
            domnode = IDomNode(node)
            webnode = IWebContent(domnode)
        except ComponentLookupError, error:
            response['Content-Type'] = 'text/plain'
            response.send_error(404, 'No adapter for requested node.')
        else:
            response.send(webnode.render())

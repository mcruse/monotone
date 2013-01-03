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
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.neode.node import CompositeNode
from mpx.lib.datatype.serialize.interfaces import IBroadways
from mpx.service.network.http.response import Response

class SerializationHandler(CompositeNode):
    def __init__(self, *args):
        super(SerializationHandler, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/IBroadways'))
        super(SerializationHandler, self).configure(config)
    def configuration(self):
        config = super(SerializationHandler, self).configuration()
        config['path'] = self.getattr('path')
        return config
    def start(self):
        super(SerializationHandler, self).start()
    def stop(self):
        super(SerializationHandler, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def handle_request(self, request):
        request_data = request.get_post_data_as_dictionary()
        request_data.update(request.get_query_string_as_dictionary())
        requesturi = request.get_path()
        nodeuri = requesturi[len(self.path):]
        if '%' in nodeuri:
            nodeuri = urllib.unquote(nodeuri)
        response = Response(request)
        if request_data:
            node = self.nodespace.as_node(nodeuri)
            generator = IBroadways(node)
            if request_data.has_key('dumps'):
                return response.send(generator.dumps())
            elif request_data.has_key('loads'):
                snippet = urllib.unquote(request_data['snippet'][0])
                generator.loads(snippet)
        document = HTMLgen.SimpleDocument()
        dumpform = HTMLgen.Form(requesturi)
        dumpform.submit.name = 'dumps'
        dumpform.submit.value = 'Get configuration'
        loadform = HTMLgen.Form(requesturi)
        loadinput = HTMLgen.Textarea('', name='snippet')
        loadform.append(loadinput)
        loadform.submit.name = 'loads'
        loadform.submit.value = 'Load configuration'
        document.append(dumpform)
        document.append(loadform)
        return response.send(str(document))

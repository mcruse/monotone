"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.lib.configure import as_boolean
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response

html = """
    <html>
        <head>
            <title>Response</title>
        </head>
        <body>
            <h1>%s</h1>
        </body>
    </html>
"""

class POSTWriter(CompositeNode):
    def __init__(self, *args):
        self.provides_security = False
        self.delay = 0
        self.stdout = 0
        self.silent = 0
        self.echo = 0
        self.outputdata = 1
        super(POSTWriter, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/postwriter'))
        self.delay = int(config.get('delay', self.delay))
        requires_authorization = config.get('requires_authorization', False)
        self.setattr('requires_authorization', 
                     as_boolean(requires_authorization))
        super(POSTWriter, self).configure(config)
    def configuration(self):
        config = super(POSTWriter, self).configuration()
        config['path'] = self.getattr('path')
        config['delay'] = str(self.delay)
        config['requires_authorization'] = str(self.requires_authorization)
        return config
    def start(self):
        self.provides_security = not self.requires_authorization
        super(POSTWriter, self).start()
    def stop(self):
        super(POSTWriter, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def logdata(self, data):
        if self.silent:
            return
        message = 'POSTWriter received %d bytes:' % len(data)
        if self.outputdata:
            message += '\n\t%r' % data
        if self.delay:
            message += '\n\tresponse delay: %s seconds\n' % self.delay
        if self.stdout:
            print message
        else:
            msglog.log('broadway', msglog.types.DB, message)
    def handle_request(self, request):
        response = Response(request)
        postdata = request.get_data().read_all()
        self.logdata(postdata)
        if self.delay:
            time.sleep(self.delay)
        if self.echo:
            responsedata = postdata
        else:
            responsedata = 'Read: %s bytes of content.' % len(postdata)
        response.send(html % responsedata)

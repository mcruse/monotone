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
import string
import urllib
from HTMLgen import HTMLgen
from mpx.service.alarms2.alarm import Alarm
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.dom.interfaces import IDomNode
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.configure import set_attribute
from mpx.lib.configure import as_boolean
from mpx.lib import msglog

class CloudHandler(CompositeNode):
    def configure(self, config):
        self.setattr('path', config.get('path','/cloud'))
        self.setattr('manager', config.get('manager','/services/Cloud Manager'))
        set_attribute(
            self, 'provides_security', True, config, as_boolean)
        super(CloudHandler, self).configure(config)
    def configuration(self):
        config = super(CloudHandler, self).configuration()
        config['path'] = self.getattr('path')
        config['manager'] = self.getattr('manager')
        return config
    def start(self):
        self.manager = self.nodespace.as_node(self.manager)
        super(CloudHandler, self).start()
    def stop(self):
        self.manager = self.nodespace.as_node_url(self.manager)
        super(CloudHandler, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def handle_request(self, request):
        data = request.get_data().read_all()
        if request.get_query_string_as_dictionary().has_key('formation'):
            result = self.manager.handle_formation_update(data)
            self.message('Updated formation')
        else:
            try: result = self.manager.handle_remote_event(data)
            except Exception, error:
                request.error(300, str(error))
                raise
        request.reply(200, str(result))
    def message(self, data, mtype='debug'):
        print 'CloudHandler: ' + data

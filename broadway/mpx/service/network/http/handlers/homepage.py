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
import string
from mpx.lib.node import as_node
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.request_handler import _IF_MODIFIED_SINCE

class HomepageHandler(CompositeNode):
    def __init__(self, *args):
        self.request_path = '/myhome'
        self.default_home = '/'
        self.security_manager = None
        self.user_manager = None
        super(HomepageHandler, self).__init__(*args)
    def configure(self, config):
        self.request_path = config.get('request_path', self.request_path)
        self.default_home = config.get('default_home', self.default_home)
        return super(HomepageHandler, self).configure(config)
    def configuration(self):
        config = super(HomepageHandler, self).configuration()
        config['request_path'] = self.request_path
        config['default_home'] = self.default_home
        return config
    def start(self):
        self.security_manager = as_node('/services/Security Manager')
        self.user_manager = self.security_manager.user_manager
        return super(HomepageHandler, self).start()
    def stop(self):
        self.security_manager = None
        self.user_manager = None
    def match(self, path):
        return path.startswith(self.request_path) and path.count('.') == 0
    def handle_request(self, request):
        path = request.get_path()
        slashcount = path.count('/')
        if slashcount == 1:
            userobject = request.user_object()
            usernode = self.user_manager.user_from_object(userobject)
        elif slashcount == 2:
            splitpath = path.split('/')
            usernode = self.user_manager.get_user(splitpath.pop())
            path = string.join(splitpath, '/')
        else:
            message = 'Path "%s" illegal.  ' % path
            message += 'Must be of form "/%s[/username]".' % self.request_path
            raise TypeError(message)
        homepage = getattr(usernode, 'homepage', self.default_home)
        request.set_path(homepage)
        #prevent caching
        request.remove_header(_IF_MODIFIED_SINCE)
        request['cache-control'] = 'no-cache'
        return request.send_to_handler(skip = self)

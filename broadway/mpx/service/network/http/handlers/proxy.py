"""
Copyright (C) 2011 Cisco Systems

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
import inspect
import asynchat

import asyncore
import socket
import string

from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.exceptions import Unauthorized
from mpx.lib.neode.node import CompositeNode
from mpx.lib._singleton import _ReloadableSingleton
from mpx.lib.exceptions import ENoSuchName
from mpx.service.network.http.response import Response
primitives = set([str, int, float, long, unicode, list, tuple, bool])


class PROXYHandler(CompositeNode):
    """
        Handles requests that needs to be proxied to tomcat server.
    """
    def __init__(self, *args):
        self.secured = True
        self.provides_security = True 
        self.security_manager = None
        super(PROXYHandler, self).__init__(*args)
    def configure(self, config): 
        self.setattr('path', config.get('path','/GlobalNavigator'))
        super(PROXYHandler, self).configure(config)
    def configuration(self):
        config = super(PROXYHandler, self).configuration()
        config['path'] = self.getattr('path')
        return config
    def start(self):
        self.security_manager = as_node("/services/Security Manager")
        super(PROXYHandler, self).start()
    def stop(self):
        self.security_manager = None
        super(PROXYHandler, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def invoke(self, target, methodname, *params):
        node = self.nodespace.as_node(target)
        method = getattr(node, methodname)
        return method(*params)
    def get_attribute(self, target, attr):
        node = self.nodespace.as_node(target)
        return getattr(node, attr)
    def set_attribute(self, target, attr, value):
        node = self.nodespace.as_node(target)
        return setattr(node, attr, value)
        
    def handle_request(self, request):
        path = request.get_path()                   
        requestedPage = "/services" + path[len(self.path):]
        
        #if self.secured:
        #    try:
        #        #policies = self.security_manager.policy_manager.
        #        #        get_context_policies(requestedPage)
        #        
        #        #for policy in policies:
        #        #    msglog.log("*******************************", 
        #        #        msglog.types.INFO, policy.context)
        #    
        #        node = self.security_manager.as_secured_node(requestedPage)
        #    
        #    except Unauthorized, error:
        #        request["Content-Type"] = 'text/html'
        #        request.reply_code = 403
        #        request.done()
        #        return
        #    except ENoSuchName:
        #        pass
        
        cookies = request.get_cookie_dictionary()
        newCookies = "".join([str(key) + "=" + str(cookies[key]) + "; " for key in cookies])
        opener = urllib.FancyURLopener()
        opener.addheader("Cookie", newCookies)
        postData = ''
        
        if int(request.get_header('Content-Length', 0)) > 0:
            request.get_data().seek(0)
            postData = request.get_data().read_all()
            
        #data = urllib.urlencode(postData)
        hc = opener.open("http://localhost:8080" + path, postData)
                                         
        html = hc.read()
        hc.close()
        headerInfo = hc.info()
        try:
            request["Content-Type"] = headerInfo['Content-Type']
        except KeyError:
            request["Content-Type"] = 'text/html'
            pass
            
        request.push(html)
        #else:
        #    request["Content-Type"] = 'text/html'
        #    request.reply_code = 403
                
        request.done()

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
from mpx.service.network.http.responders import status
from mpx.service.network.http.responders import Responder

class UnauthorizedResponder(Responder):
    """
        Handle authentication related issues, such as unauthenticated 
        users, by handling all HTTP 401 error codes and redirecting 
        client to login page instead.
    """
    def __init__(self):
        self.loginpage = "login.html"
        self.homepage = "home.html"
        super(UnauthorizedResponder, self).__init__()
    def configure(self, config):
        self.loginpage = config.get("login", self.loginpage)
        super(UnauthorizedResponder, self).configure(config)
    def configuration(self):
        config = super(UnauthorizedResponder, self).configuration()
        config["login"] = self.loginpage
        return config    
    def match(self, code):
        return code == 401
    def handle_response(self, request):
        self.last_request = request
        request["Location"] = self.loginpage
        if request.get_command() == "GET":
            destination = urllib.quote(request.get_path())
        else:
            destination = self.homepage
        request["Location"] += "?destination=%s" % destination
        request.setreply(302, "Redirect to log-in page.")
        request.send_to_responder(self)

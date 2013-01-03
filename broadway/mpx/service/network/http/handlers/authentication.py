"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.node import as_node
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_internal_node
from mpx.lib.user import EPasswordExpired
from mpx.service.user_manager import EAuthenticationFailed
from moab.user import manager
from moab.user.pamlib import PAMError 
from mpx.service.network.http.response import Cookie
from mpx import properties as Properties
from mpx.service.security.user import UserManager
class Authenticator(CompositeNode):
    """
        Handler provides functionality supporting user log-in and 
        log-out operations.
        
        The purpose of this handler is to work around normal security 
        requirements of the web-server, allowing requests to this URL 
        to be made with or without credentials, and potenially with 
        incorrect credentials.  The reason one might want to send a 
        request with incorrect credentials is because doing so, and 
        having the server respond with a normal response, is a trick 
        that can be used to log off a user once they've signed in.
        
        Handler operates in three different modes.  First it will 
        accept /login GET requests with no credentials, and read 
        and return the HTML form for user login.  If a query-string 
        parameter specifying a "destination" is provided with 
        the request, the returned form will contain a hidden field 
        specifying that value back to the login handler on POST.
        
        Second, it will accept /login POST requests with user 
        credentials, which is validates.  After validating, the 
        response sets cookies containing credentials in a redirect 
        handling sending the browser to the home page or a different 
        page if one is supplied via the "destination" form field.
        
        Finally, it accepts /logout requests which it responds to by 
        clearing the authentication cookies and returning the login 
        form, along with an explanatory message. 
    """
    def __init__(self):
        self.manager = None
        self.provides_security = True
        self.template = ""
        self.templateurl = "/templates/login.html"
        self.request_paths = ("/login", "/logout", "/update_password")
        super(Authenticator, self).__init__()
    def configure(self, config):
        self.templateurl = config.get("template", self.templateurl)
        super(Authenticator, self).configure(config)
    def configuration(self):
        config = super(Authenticator, self).configuration()
        config["template"] = self.templateurl
        return config
    def start(self):
        self.users = as_node("/services/Security Manager/Users")
        self.manager = self.parent.server.user_manager
        self.template = self.parent.read_resource(self.templateurl)
        return super(Authenticator, self).start()
    def match(self, path):
        return path.startswith(self.request_paths)
    def handle_request(self, request):
        self.last_request = request
        if request.get_path().startswith("/login"):
            if request.get_command() == "POST":
                self.handle_login(request)
            else:                
                self.handle_form(request)
        elif request.get_path().startswith("/logout"):
            self.handle_logout(request)
        elif request.get_path().startswith("/update_password"):
            self.handle_update_password(request)
        else:
            raise TypeError("path not recognized: %s" % request.get_path())
        request['Content-Type'] = 'text/html; charset=UTF-8'
        return request.done()
    def handle_form(self, request, authstatus="", message="", details=""):
        """
            Handler invoked as GET indicates that user is 
            entering login page and needs authorization form.
        """
        parameters = request.get_query_dictionary()
        if request.get_command() == "POST":
            # If authentication fails login-handler will delegate 
            # the request to this method, but it will be a POST.
            postdata = request.get_post_data()
            parameters.update(postdata)
        destination = parameters.get("destination", "/")
        destination = urllib.quote(destination, '/')
        templateargs = {"status-type": authstatus, 
                        "status-message": message, 
                        "status-detail": details, 
                        "request-destination": destination}
        request.push(self.template % templateargs)
    def handle_login(self, request):
        parameters = request.get_query_dictionary()
        destination = parameters.get("destination", "/")
        if parameters.has_key("password"):
            msg = "Unsafe use of query-string for user credentials: %r."
            msglog.log("broadway", msglog.types.WARN, msg % (parameters,))
        parameters.update(request.get_post_data())
        # POST value for destination overrides query-string if both provided.
        destination = parameters.get("destination", destination)
        destination = urllib.quote(destination, '/')
        username = parameters.get("username", "")
        password = parameters.get("password", "")
        sessionManager = as_internal_node('/services/session_manager')
        try:
            if Properties.get_boolean('PAM_ENABLE'):
                user = self.manager.user_from_pam(username, password)
            else:
                user = self.manager.user_from_cleartext(username, password)
            user.password_expired()
        except PAMError, e:
            msglog.exception(prefix="Handled")
            self.handle_form(request, "warning", "Authentication failure", e)
        except EAuthenticationFailed:
            msglog.log("broadway", msglog.types.WARN, 
                       "Failed login attempt: %r" % username)
            self.handle_form(request, "warning", 
                             "Authorization failed", 
                             "Invalid username/password.  Please try again.")
        except EPasswordExpired, e:
            msglog.exception(prefix="Handled")
            self.handle_form(request, "update_password", "Please update your password", 
                             "Password expired. Please update your password.")
        else:
            if self.parent.server_type != "HTTPS":
                msg = "Session for %r authorized using insecure channel."
                msglog.log("broadway", msglog.types.WARN, msg % username)
            sid = sessionManager.create( username,password)
            cookies = [Cookie("CUSER", username)]
            cookies.append(Cookie("SID", sid))
            cookies.append(Cookie("CRYPT", user.crypt()))
            self.assign_cookies(cookies, request)
            #Get the user details with username
            usrhomepage = self.users.get_user(username).homepage
            #if destination is equal to / then assign usrhomepage to destination
            if destination == '/':
                destination = usrhomepage
            self.setup_redirect(request, destination)
    def handle_update_password(self, request):
        parameters = request.get_query_dictionary()
        parameters.update(request.get_post_data())
        
        # POST value for destination overrides query-string if both provided.
        username = parameters.get("username", "")
        password = parameters.get("password", "")
        newpwd = parameters.get("newpwd", "")
        confirm_newpwd = parameters.get("confirm_newpwd", "")
        
        try:
            if Properties.get_boolean('PAM_ENABLE'):
                user = self.manager.user_from_pam(username, password)
            else:
                user = self.manager.user_from_cleartext(username, password)
        except (PAMError, EAuthenticationFailed):
            msglog.exception(prefix="Handled")
            msg = "Invalid old password. Enter correct old password for authentication."
            self.handle_form(request, "update_password", "Authentication Failed", msg)
        else:
            if newpwd == confirm_newpwd:
                try:
                    user.set_password(newpwd)
                except EInvalidValue, e:
                    msglog.exception(prefix="Handled")
                    msg = "".join(e[1].splitlines())
                    self.handle_form(request, "update_password", 
                                     "Invalid new password. Please try again", msg)
                else:
                    msg = "Password updated successfully for %s." % (username)
                    msglog.log("broadway", msglog.types.INFO, msg)
                    self.handle_form(request, "information", msg)
            else:
                msg = "Updating password failed for %s. The new password does not match."
                msglog.log("broadway", msglog.types.WARN, msg % username)
                self.handle_form(request, "update_password", "New password(s) mismatch", 
                                 "The new password(s) does not match. Please try again.")
    def handle_logout(self, request):
        sm = as_internal_node("/services/session_manager")
        cookies = [Cookie("CUSER", "EXPIRED")]
        session_id = request.get_cookie("SID")
        if session_id:
            sm.destroy(session_id)
        cookies.append(Cookie("CRYPT", "EXPIRED"))
        cookies.append(Cookie("SID", "EXPIRED"))
        self.assign_cookies(cookies, request)
        self.handle_form(request, "information", "You have logged out.")
    def assign_cookies(self, cookies, request):
        for cookie in cookies:
            cookie.add_attribute("path", "/")
            if self.parent.server_type == "HTTPS":
                cookie.add_attribute("secure", "True")
        map(request.add_cookie, cookies)
    def debugout(self, message, *args, **kw):
        level = kw.get("level", 1)
        if level < self.debug:
            return
        message = "%s: %s" % (self.name, message % args)
        msglog.log('broadway', msglog.types.DB, message)
    def setup_redirect(request, destination, message=None):
        request["Location"] = urllib.unquote(destination)
        request.setreply(302, message)
    setup_redirect = staticmethod(setup_redirect)


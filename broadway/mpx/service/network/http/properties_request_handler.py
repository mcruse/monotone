"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import re

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response
from mpx import properties
##
# @implements mpx.service.network.http.RequestHandlerInterface
#
class PropertiesRequestHandler(RequestHandler):
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default /properties
    #
    # @see mpx.lib.service.RequestHandler#configure
    #
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '^/properties$', config) 
        RequestHandler.configure(self, config)

    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        return config
    
    
    def match(self, path):
        if re.match(self.request_path,path):
            return 1
        return 0
    
    ##
    # Called by http_server each time a request comes in whose url mathes one of
    # the paths this handler said it was interested in. 
    #
    # @param request  <code>Request</code> object from the http_server.  To send
    #                  Create a Response object response = Response(request)
    #                  response.send(html)
    #                  <code>html</code> is the text response you want to send.
    # @fixme Handle exceptions gracefully and report them back to the client.
    # @fixme Don't convert the incoming values (as soon as we refactor the core
    #        ions).
    # @fixme After override, load the parent page instead of displaying the
    #        message.    
    def handle_request(self, request):
        header_style = "color:#FFFFFF;font-size:20px;font-weight:bold;background:#898989;"
        header_style += 'text-align:center;'
        html = '<html><head>\n'
        html += '<link rel="stylesheet"  type="text/css" href="/stylesheets/main.css">'
        html += '\n</head><body>\n'
        if self.enabled:
            index = 1
            html += '<table width="100%"><tr><td bgColor="#aaaaaa">\n'
            html += '<table width="100%" cellspacing="1" cellpadding="10" border="0">'
            html += '<tr><td style="%s" ' % header_style
            html +=  'width="35%">Name</td>\n'
            html += '<td style="%s" ' % header_style
            html += 'width="65%">Value</td></tr>\n' 
            dict= properties.as_dictionary()
            props = dict.keys()
            props.sort()
            
            for p in props:
                if (index%2) > 0:
                    bgColor = "#EEEEEE"
                else:
                    bgColor = "#FFFFFF"
                index += 1
                html += '<tr><td style="color:#000000;font-weight:bold"'
                html += ' bgColor="%s" align="right">%s</td><td bgColor="%s" align="left"><font color="#000FFF">%s</font></td></tr>\n' % (bgColor,p,bgColor,dict[p])
            html += '</table>'
            html += '</td></tr></table>'
           
            
        else:
            html += '<span class="disabled_msg">Sorry, the handler for your request is currently disabled</span>'
        
        html += "</body></html>"
        response = Response(request)
        response.send(html)
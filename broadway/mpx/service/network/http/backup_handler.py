"""
Copyright (C) 2007 2008 2009 2011 Cisco Systems

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
from producers import FileProducer
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.node import as_node, as_deferred_node, as_internal_node
from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response
from mpx.lib import msglog
from mpx.service.configuration.backup import backup_class
from mpx.lib.exceptions import Unauthorized

class BackupHandler(RequestHandler):
    REDIRECT = ('<html>\n<head>\n' +
                '<META HTTP-EQUIV="Window-target" CONTENT="_top">\n' +
                '<META http-equiv="Refresh" content="0; Url=%s" >\n' +
                '<title>%s</title>\n</head>\n<body></body>\n</html>')
    def __init__(self):
        RequestHandler.__init__(self)
        self.b_service = as_deferred_node('/services/backup_registry')
    ##
    # Configures HTTP handler.
    #
    # @param config  Dictionary containing parameters and values from
    #                the configuration tool.
    # @key request_path  Regular expression for url requests that
    #                    should be forwarded to this handler.
    # @default /backup_service
    #
    # @see mpx.lib.service.RequestHandler#configure
    #
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '/backup', config)
        self.secured = as_internal_node("/services").secured
        RequestHandler.configure(self, config)
        return
    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.RequestHandler#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'secured', config)
        return config

    def match(self, path):
        return path.startswith(self.request_path)

    # read tar contents, set application content type and allow download
    def download_backup(self, request, file):
        response = Response(request)
        response.set_header('Content-Type','application/octet-stream')
        response.set_header('Content-Disposition',
                            'attachment; filename="%s.tgz"' %
                             file.f_name)
        response.push(FileProducer(file))
        response.done()
        return
    ##
    # Called by http_server each time a request comes in whose url mathes one
    # of the paths this handler said it was interested in. 
    #
    # @param request  <code>Request</code> object from the http_server.  To
    #                  send resonse call <code>request.send(html)</code> where
    #                  <code>html</code> is the text response you want to send.
    # @fixme Handle exceptions gracefully and report them back to the client.
    def handle_request(self, request):
        backup = ['All']
        path = request.get_path()
        if path[-1] == '/':
            path = path[0:-1]
        path, params, query, fragment = request.split_uri()
        path = path[len(self.request_path):]
        while path and path[0] == '/':
            path = path[1:]
        backup_name = path
        if request.has_query():
            query = request.get_query_dictionary()
            if (query.has_key('arg_cnt')):
                arg_cnt = query['arg_cnt']
                for i in range(arg_cnt):
                    arg = query['arg%d' % i+1]
                    if arg in backup_class.values():
                        backup.append(arg)
            if not backup:
                backup.append(str(backup_class[max(backup_class.keys())])) # ALL always the last in the list
        b_service = self.b_service
        if self.secured:
            b_service = self.as_node("/services/Security Manager").as_secured_node(self.b_service)
        try:
            file = b_service.generate_backup(backup_name, backup)
        except Unauthorized, e:
            request.error(403, "Permission Denied: %s"%e)
        self.download_backup(request, file)
        return
    
    def get_backup_class_options(self):
        return self.b_service.get_registered_classes()
    
    def redirect(self, request):
        url = 'system.html?preventCache=%f' % time.time()
        request.push(BackupHandler.REDIRECT % (url,self.name))
        request.done()
        
def factory():
    return BackupHandler()
        

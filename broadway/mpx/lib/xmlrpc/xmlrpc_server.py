"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import SocketServer
import xmlrpclib

import SocketServer, BaseHTTPServer
import xmlrpclib
import sys
import string

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            params, method = xmlrpclib.loads(data)

            tokens = string.split(method, ':')
            object_name = ''
            method_name = ''
            if len(tokens) < 2:
                #  if not object.method sent, then return the 
                #  method names of the named 'object'
                #  Call the default object and request
                #  it to return a list of methods in named
                #  object.
                object_name = 'mpx.lib.xmlrpc.default_object'
                object_method = 'query_method_names'
                params = tuple(tokens)
            else:
                object_name = tokens[0]
                method_name = tokens[1]
            
            # generate response
            try:
                # The dumps function requires that the response is a
                # single entry in a tuple.
                response = (self.call(method_name, params),)
            except:
                # report exception back to server
                exc_type,exc_value,exc_traceback = sys.exc_info()
                response = xmlrpclib.dumps(
                    xmlrpclib.Fault(1, "%s:%s" % (exc_type,exc_value))
                    )
            else:
                response = xmlrpclib.dumps(
                    response,
                    methodresponse=1
                    )
        except:
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection (from Skip Montanaro)
            self.wfile.flush()
            self.connection.shutdown(1)

    def call(self, method, params):
        # override this method to implement RPC methods
        print "CALL", method, params
        return params

    
## Sample XMLRPC Server used to test clients
class TestRequestHandler(RequestHandler):
    #Override method:
    def call(self, method, params):

        print "Dispatching: ", method, params
        try:
            return {'test' : 'testvalue', 'testkey1'  : 'testValue2'}
        
            server_method = getattr(self, method)
        except:
            raise AttributeError, "Server does not contain XML-RPC procedure %s" % method
        return server_method(method, params)

    def dump_methodcall(self, method, params):
        return xmlrpclib.dumps(params[1:], params[0])

    def dump_params(self, method, params):
        return xmlrpclib.dumps(params)

    def test(self, method, nr):
        return nr

    def dump_response(self, method, params):
        response = self.call(params[0], tuple(params[1:]))
        return xmlrpclib.dumps(response)


if __name__ == '__main__':
    server = SocketServer.TCPServer(('', 8020), TestRequestHandler)
    server.serve_forever()
        

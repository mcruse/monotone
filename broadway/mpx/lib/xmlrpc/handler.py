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
import SocketServer
import xmlrpcserver
import xmlrpclib

class TestRequestHandler(xmlrpcserver.RequestHandler):
    
    def call(self, method, params):
        print "Dispatching: " , method, params
        try:
            server_method = getattr(self, method)
        except:
            raise AttribError, "Server does not have XML-RPC procedure %s" % method
        return server_method(method, params)

    def dump_params(self, method, params):
        return xmlrpclib.dumps(params)
    

    def dump_methodcall(self, method, params):
        return xmlrpclib.dumps(params[1:], params[0])

    def test(self, method, nr):
        return nr
    
    def dump_response(self, method, params):
        response = self.call(params[0], tuple(params[1:]))
        return xmlrpclib.dumps(response)
    
    
    
if __name__ == '__main__':
    server = SocketServer.TCPServer(('', 8000),TestRequestHandler) 
    server.serve_forever()
    
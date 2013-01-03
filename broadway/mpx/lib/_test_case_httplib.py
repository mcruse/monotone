"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main
from mpx.lib.exceptions import ETimeout
from mpx.lib.threading import Thread
from mpx.lib import httplib,socket

class TestCase(DefaultTestFixture):
    STARTING_PORT=8080
    def __init__(self,*args):
        self._port = self.STARTING_PORT
        DefaultTestFixture.__init__(self,*args)
    def setUp(self):
        self._server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._server_connection = None
        self._bind()
    def tearDown(self):
        try:
            if self._server_connection:
                try:
                    self._server_connection.close()
                except:
                    self._server_connection.shutdown()
        finally:
            try:
                self._server.close()
            except:
                self._server.shutdown()
        return
    def _bind(self):
        while 1:
            try:
                self._server.bind(('localhost',self._port))
            except socket.error,why:
                if why[0] != 98:
                    raise why
                self._port += 1
            else:
                break
        return
    def _listen(self,count=1):
        self._server.listen(1)
    def _connect(self,socket):
        socket.connect(('localhost',self._port))
    def _accept(self,socket):
        conn,addr = self._server.accept()
        return conn
    def test_read_write(self):
        self._listen()
        client = httplib.HTTPConnection('localhost',self._port,1)
        respond(self._server,'response')
        client.request('get','/index.html')
        response = client.getresponse()
        data = response.read()
        self.failUnless(data == 'response','Wrong response returned: %s' % data)
    def test_timeout(self):
        self._listen()
        client = httplib.HTTPConnection('localhost',self._port,1)
        client.request('get','/index.html')
        try:
            client.getresponse()
        except ETimeout:
            pass
        else:
            self.fail('Attempt to get response should have failed.')

def respond(server,response='response'):
    t = Thread(target=_accept_and_respond,args=(server,response))
    t.start()
def _accept_and_respond(server,response):
    conn,addr = server.accept()
    data = conn.recv(1024)
    conn.send(('HTTP/1.1 200 OK\r\nContent-Length: %s\r\n\r\n%s') % 
              (len(response),response))
    conn.close()
        
    
if __name__ == '__main__':
    main()
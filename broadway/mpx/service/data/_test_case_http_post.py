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
import string
from mpx_test import DefaultTestFixture, main
from mpx.lib.node import CompositeNode
from mpx.service.data import http_post_transporter
from mpx.lib.threading import Thread
from mpx.lib import socket
from mpx.lib.exceptions import ETimeout

class TestCase(DefaultTestFixture):
    STARTING_PORT=8080
    def __init__(self,*args):
        self._port = self.STARTING_PORT
        DefaultTestFixture.__init__(self,*args)
    def setUp(self):
        self._server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._server_connection = None
        self._bind()
        parent = CompositeNode()
        parent.configure({'name':'parent','parent':None})
        self._transporter = http_post_transporter.HTTPPostTransporter()
        self._transporter.configure({'name':'transporter','parent':parent,
                                     'post_url':'http://localhost:%s/test' % 
                                     self._port,'timeout':'1'})
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
    def _accept(self):
        conn,addr = self._server.accept()
        return conn
    def test_conect_fail(self):
        try:
            self._transporter.transport('Test Data')
        except socket.error,why:
            self.failUnless(why[0] == 111, 'Wrong exception: %s' % why)
        else:
            self.fail('Transport should have raised connection error')
    def test_transport(self):
        self._listen()
        thread = Thread(target=self._transporter.transport,args=('Test Data',))
        thread.start()
        conn = self._accept()
        data = ''
        more = conn.recv(1024)
        while more:
            data += more
            more = conn.recv(1024)
        self.failUnless(string.split(data,'\r\n\r\n')[-1] == 'Test Data',
                        'Transport sent wrong data: %s' % data)
        conn.send('HTTP/1.1 200 OK\r\n\r\n')
        conn.close()
    def test_timeout(self):
        self._listen()
        try:
            self._transporter.transport('Test Data')
        except ETimeout:
            pass
        else:
            self.fail('Transport call should have timed out.')        

if __name__ == '__main__':
    main()
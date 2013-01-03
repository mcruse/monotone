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
from mpx_test import DefaultTestFixture, main
from mpx.lib import socket
from mpx.lib.exceptions import ETimeout
from mpx.lib.threading import Thread

class TestCase(DefaultTestFixture):
    STARTING_PORT=8080
    def __init__(self,*args):
        self._port = self.STARTING_PORT
        DefaultTestFixture.__init__(self,*args)
    def setUp(self):
        self._server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._server_connection = None
        self._bind()
    def tearDown(self):
        try:
            if self._server_connection:
                try:
                    self._server_connection.close()
                except:
                    self._server_connection.shutdown()
            try:
                self._client.close()
            except:
                self._client.shutdown()
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
    def _listen(self):
        self._server.listen(1)
    def _connect(self):
        self._client.connect(('localhost',self._port))
    def _accept(self):
        self._server_connection,addr = self._server.accept()
    def test_connect(self):
        try:
            self._connect()
        except socket.error,why:
            if why[0] != 111:
                raise why
        else:
            self.fail('Connecting to non-listenting socket did not fail')
        self._listen()
        self._connect()
        try:
            self._server.accept(1)
        except ETimeout:
            self.fail('Accepting socket which we connected to failed')
    def test_accept(self):
        self._listen()
        try:
            s,addr = self._server.accept(1)
        except ETimeout:
            pass
        self._connect()
        try:
            s,addr = self._server.accept(1)
        except ETimeout:
            self.fail('Unexpected timeout on accept')
        else:
            s.send('shane')
            try:
                self._client.recv(5,1)
            except ETimeout:
                self.fail('Data written from server unreadable')
            self._client.send('shane')
            try:
                s.recv(5,1)
            except ETimeout:
                self.fail('Data written from client unreadable')
        return
    def test_recv(self):
        self._listen()
        self._connect()
        try:
            self._client.recv(5,.1)
        except ETimeout:
            pass
        else:
            self.fail('Timeout did not occur during read of not data')
        self._accept()
        try:
            self._client.recv(5,.1)
        except ETimeout:
            pass
        else:
            self.fail('Timeout did not occur during read of not data')
        self._server_connection.send('shane')
        if self._client.recv(1,1) != 's':
            self.fail('Recv did not read what server sent')
        if self._client.recv(4,1) != 'hane':
            self.fail('Recv did not read what server sent')
        try:
            self._client.recv(5,.1)
        except ETimeout:
            pass
        else:
            self.fail('Timeout did not occur during read of not data')
        return
if __name__ == '__main__':
    main()

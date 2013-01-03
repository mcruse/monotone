"""
Copyright (C) 2003 2004 2006 2010 2011 Cisco Systems

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
import time
import poplib
from mpx_test import DefaultTestFixture, main
from mpx.lib.node import CompositeNode
from mpx.service.data import smtp_transporter
from mpx.lib.threading import Thread
from mpx.lib import socket,pause
from mpx.lib.exceptions import ETimeout

class TestCase(DefaultTestFixture):
    STARTING_PORT=8081
    def __init__(self,*args):
        self._port = self.STARTING_PORT
        DefaultTestFixture.__init__(self,*args)
    def setUp(self):
        self._server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._server_connection = None
        self._bind()
        self._parent = CompositeNode()
        self._parent.configure({'name':'parent','parent':None})
        self._transporter = smtp_transporter.SMTPTransporter()
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
    def test_connect_fail(self):
        self._transporter.configure({'host':'localhost','port':self._port,
                                     'sender':'test@envenergy.com',
                                     'recipients':'junk@envenergy.com',
                                     'timeout':'1','name':'test',
                                     'parent':self._parent})
        self._transporter.start()
        try:
            self._transporter.transport('Test Data')
        except socket.error,why:
            self.failUnless(why[0] == 111, 'Wrong exception: %s' % why)
        else:
            self.fail('Transport should have raised connection error')
    def DISABLED_test_authenticating(self):
        unique = time.time()
        self._transporter.configure({'host':'tacos.dyndns.org',
                                     'sender':'%s@export.com' % unique,
                                     'recipients':'mailreceiver@tacos.dyndns.org',
                                     'subject':str(unique),'timeout':'1',
                                     'authenticate':'1',
                                     'username':'mailsender',
                                     'password':'airborne',
                                     'name':'test','parent':self._parent})
        self._transporter.start()
        self._transporter.transport('Test')
        pause(30)
        pop = poplib.POP3('tacos.dyndns.org')
        try:
            pop.user('mailreceiver')
            pop.pass_('env123')
            count = len(pop.list()[1])
            received = 0
            for i in range(0,count):
                message = pop.retr(i+1)[1]
                pop.dele(i+1)
                for line in message:
                    if (line.startswith('Subject: ') and 
                        line[9:].strip() == str(unique)):
                        received = 1
                        break
        finally:
            pop.quit()
        self.failUnless(received,'Failed to retrieve email, it may be a ' + 
                        'problem with the SMTP server and not the transporter.')
    def DISABLED_test_non_authenticating(self):
        unique = time.time()
        self._transporter.configure({'host':'localhost',
                                     'sender':'%s@export.com' % unique,
                                     'recipients':'mailreceiver@tacos.dyndns.org',
                                     'subject':str(unique),'timeout':'1',
                                     'authenticate':'0',
                                     'name':'test','parent':self._parent})
        self._transporter.start()
        self._transporter.transport('Test')
        pause(30)
        pop = poplib.POP3('tacos.dyndns.org')
        try:
            pop.user('mailreceiver')
            pop.pass_('env123')
            count = len(pop.list()[1])
            received = 0
            for i in range(0,count):
                message = pop.retr(i+1)[1]
                pop.dele(i+1)
                for line in message:
                    if (line.startswith('Subject: ') and 
                        line[9:].strip() == str(unique)):
                        received = 1
                        break
        finally:
            pop.quit()
        self.failUnless(received,'Failed to retrieve email, it may be a ' + 
                        'problem with the SMTP server and not the transporter.')
    def test_timeout(self):
        self._listen()
        self._transporter.configure({'host':'localhost','port':self._port,
                                     'sender':'test@envenergy.com',
                                     'recipients':'junk@envenergy.com',
                                     'timeout':'1','name':'test',
                                     'parent':self._parent})
        self._transporter.start()
        try:
            self._transporter.transport('Test Data')
        except ETimeout:
            pass
        else:
            self.fail('Transport call should have timed out.')        

if __name__ == '__main__':
    main()

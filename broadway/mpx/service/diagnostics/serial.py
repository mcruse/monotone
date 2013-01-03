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
import array
from test import Test

from mpx.lib.node import as_node

from ion import Factory

class _PortTester(Test):
    def __init__(self, port1, port2):
        self.port1 = as_node('/interfaces/'+port1)
        self.port2 = as_node('/interfaces/'+port2)
        # it's just a helper class that is part of the Serial Tests
        super(_PortTester, self).__init__()
        self._test_name = 'SerialTester'
        return
        
    def _test_ports(self, sender, receiver):
        err = 0
        test_message = array.array('c')
        test_message.fromstring('Greetings from your fellow port')
        m_len = len(test_message)
        rcvd_message = array.array('c')
        
        sender.write(test_message)
        try:
            receiver.read(rcvd_message, m_len, 1)
        except:
            err = 1
            
        if not err and rcvd_message != test_message:
            err = 1
        
        if err:
            self.log('ERROR: ports (%s:%s) failed to communicate.' %
                (self.port1.name, self.port2.name))
        return err
        
    def runtest(self):
        self.log('Testing serial ports (%s:%s).' % 
            (self.port1.name, self.port2.name))
            
        if self.port1.is_open() or self.port2.is_open():
            self.log('ERROR: ports (%s:%s) must NOT be in use prior to testing.' %
                (self.port1.name, self.port2.name))
            self._nerrors += 1
            return
            
        self.port1.open()
        self.port1.drain()
        self.port2.open()
        self.port2.drain()
        cd1 = self.port1.configuration()
        cd2 = self.port2.configuration()
        
        for baud in [1200, 2400, 4800, 9600, 19200, 38400, 57600]:
            cd1['baud'] = baud
            self.port1.configure(cd1)
            cd2['baud'] = baud
            self.port2.configure(cd2)
            self.log('Testing serial ports (%s:%s) at %d baud.' %
                (self.port1.name, self.port2.name, baud))
            
            self._nerrors += self._test_ports(self.port1, self.port2)
            self._nerrors += self._test_ports(self.port2, self.port1)
        
        self.port1.close()
        self.port2.close()
        
        self.log('ERROR: Serial ports (%s:%s) %d errors and %d warnings.' % 
            (self.port1.name, self.port2.name, self._nerrors, self._nwarnings))
        return self.passed()

class SerialTester(Test):
    def __init__(self, **kw):
        super(SerialTester, self).__init__(**kw)
        self._test_name = 'SerialTester'
        self._rs232test = _PortTester('com1', 'com2')
        self._rs485test_a = _PortTester('com3', 'com4')
        self._rs485test_b = _PortTester('com5', 'com6')
        return
        
    def runtest(self):
        for serialtest in [self._rs232test, self._rs485test_a, self._rs485test_b]:
            serialtest.runtest()
            self._nerrors += serialtest.nerrors
            self._nwarnings += serialtest.nwarnings
        self.log('Serial test, found %d errors and %d warnings.\n' %
            (self._nerrors, self._nwarnings))
        return self.passed()
        
f = Factory()
f.register('SerialTester', (SerialTester,))
        
        
        
        
        


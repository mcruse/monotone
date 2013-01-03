"""
Copyright (C) 2002 2004 2010 2011 Cisco Systems

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

import time
import array

##
# Test cases to exercise the property classes.
#

from mpx.lib.exceptions import EOverflow
from mpx.lib.exceptions import EInvalidValue

import array
import struct
from mpx.lib.modbus.tcp_management import kill_a_server
from mpx.ion.modbus import generic, tcp_ip_line_handler
from mpx.ion.modbus.server import server, tcp_ip_server
from mpx.lib.modbus.base import buffer as _buffer
from mpx.ion.host import eth
from mpx.ion.host.eth import ip
import random

rand = random.Random(42)

class TestCase(DefaultTestFixture):
    def __init__(self, other):
        DefaultTestFixture.__init__(self, other)
        self.eth0 = None
        self.ip = None
        self.server = None
        self.client = None
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.eth0 = eth.factory()
        self.eth0.configure({'name':'eth0', 'parent':None, 'dev':'eth0'})
        self.ip = ip.factory()
        self.ip.configure({'name':'ip', 'parent':self.eth0})
        self.lhs = tcp_ip_server.TcpIpServer()
        self.lhs.configure({'name':'tcpserver', 'parent':self.ip,
                            'port':8502, 'debug':0})
        self.server = server.ServerDevice()
        self.server.configure({'name':'server', 'parent':self.lhs,
                               'address':255, 'debug':0})
        self.lhc = tcp_ip_line_handler.TcpIpClient()
        self.lhc.configure({'name':'tcpclient', 'parent':self.ip,
                            'ip':self.ip.address, 'port':8502, 'debug':0})
        self.client = generic.Device()
        self.client.configure({'name':'client', 'parent':self.lhc,
                               'address':255, 'debug':0})
        return

    def tearDown(self):
        try:
            if hasattr(self,'server'):
                del self.server
            if hasattr(self,'client'):
                del self.client
            if hasattr(self,'lhc'):
                del self.lhc
            if hasattr(self,'lhs'):
                self.lhs.server.server_thread.should_die()
                self.lhs.server.close_connection()
                kill_a_server(self.lhs.server.server_thread)
                while self.lhs.server.server_thread.isAlive():
                    time.sleep(0.01)
                # @fixme WHY IS THIS COMMENTED?
                #self.lhs.server.server_thread.exit()
                del self.lhs.server.server_thread
                del self.lhs.server
                del self.lhs
            if hasattr(self,'ip'):
                del self.ip
            if hasattr(self,'eth0'):
                del self.eth0
        finally:
            DefaultTestFixture.tearDown(self)
        return

    def start(self):
        self.eth0.start()
        while self.lhs.server.ready() == 0:
            time.sleep(0.01)
            pass
        return

    def test_add_holding_register_1(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'int', 
                      'length':'1',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'int', 
                       'length':'1',
                       'read_only':'0', 'debug':0})
        self.start()
        for v in (0,1,-1,555,-555, 32767, -32767):
            hrs.set(v)
            bv = hrc.get(1)
            if v != bv:
                print v, bv
                raise 'bad get from client for int holding register'
        for v in (0,1,-1,555,-555, 32767, -32767):
            hrc.set(v)
            bv = hrs.get(1)
            if v != bv:
                print v, bv
                raise 'bad set from client to server for int holding register'

    def test_add_holding_register_2(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'int', 
                      'length':'2',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'int', 
                       'length':'2',
                       'read_only':'0', 'debug':0})
        self.start()
        for v in (0,1,-1,555,-555, 32767, -32767, 65535, -65535, 65536, -65536, 0x7FFFFFFF, -1):
            hrs.set(v)
            b = hrc.get(1)
            if v != b:
                raise 'bad value get client from server for long holding register'
        for v in (0,1,-1,555,-555, 32767, -32767, 65535, -65535, 65536, -65536, 0x7FFFFFFF, -1):
            hrc.set(v)
            if v != hrs.get(1):
                raise 'bad value set client to server for long holding register'

    def test_holding_register_float_4(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'IEEE float', 
                      'length':'2',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'IEEE float', 
                       'length':'2',
                       'read_only':'0', 'debug':0})
        self.start()
        for i in range(0,100):
            v = rand.random()
            hrs.set(v)
            b = hrc.get(1)
            if abs(v - b) >  0.0001:
                print v, b
                raise 'bad value conversion for float holding register'
        for i in range(0,100):
            v = rand.random()
            hrc.set(v)
            if abs(v - hrs.get(1)) >  0.0001:
                raise 'bad buffer conversion for float holding register'

    def test_holding_register_float_8(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'IEEE float', 
                      'length':'4',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'IEEE float', 
                       'length':'4',
                       'read_only':'0', 'debug':0})
        self.start()
        for i in range(0,100):
            v = rand.random()
            hrs.set(v)
            b = hrc.get(1)
            if abs(v - b) >  0.0001:
                print v, b
                raise 'bad value conversion for float holding register'
        for i in range(0,100):
            v = rand.random()
            hrc.set(v)
            if abs(v - hrs.get(1)) >  0.00001:
                raise 'bad buffer conversion for float holding register'
            
    def test_hiint_loint(self):
        hrs1 = server.HoldingRegister()
        hrs1.configure({'name':'hr1',
                      'parent':self.server,
                      'register':'40001',
                      'type':'hiint', 
                      'length':'1',
                      'read_only':'0', 'debug':0})
        hrs2 = server.HoldingRegister()
        hrs2.configure({'name':'hr2',
                      'parent':self.server,
                      'register':'40001',
                      'type':'loint', 
                      'length':'1',
                      'read_only':'0', 'debug':0})
        hrc1 = generic.HoldingRegister() #client holding reg
        hrc1.configure({'name':'hrc1',
                       'parent':self.client,
                       'register':'40001',
                       'type':'hiint', 
                       'length':'1',
                       'read_only':'0', 'debug':0})
        hrc2 = generic.HoldingRegister() #client holding reg
        hrc2.configure({'name':'hrc2',
                       'parent':self.client,
                       'register':'40001',
                       'type':'loint', 
                       'length':'1',
                       'read_only':'0', 'debug':0})
        self.start()
        for v1 in (0,1,-1,127,-127, 64, -64):
            hrs1.set(v1)
            for v2 in (0,1,-1,127,-127, 64, -64):
                hrs2.set(v2)
                bv = hrc1.get(1)
                if v1 != bv:
                    print v1, bv
                    raise 'bad get from client for hiint holding register'
                bv = hrc2.get(1)
                if v2 != bv:
                    print v2, bv
                    raise 'bad get from client for loint holding register'
        for v2 in (0,1,-1,127,-127, 64, -64):
            hrs2.set(v2)
            for v1 in (0,1,-1,127,-127, 64, -64):
                hrs1.set(v1)
                bv = hrc2.get(1)
                if v2 != bv:
                    print v2, bv
                    raise 'bad get from client for loint holding register'
                bv = hrc1.get(1)
                if v1 != bv:
                    print v1, bv
                    raise 'bad get from client for lhiint holding register'
        for v1 in (0,1,-1,127,-127, 64, -64):
            hrc1.set(v1)
            for v2 in (0,1,-1,127,-127, 64, -64):
                hrc2.set(v2)
                bv = hrs1.get(1)
                if v1 != bv:
                    print v1, bv
                    raise 'bad set from client to server for int holding register'
                bv = hrs2.get(1)
                if v2 != bv:
                    print v2, bv
                    raise 'bad set from client to server for int holding register'

    def test_modulo(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'modulo', 
                      'length':'4',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'modulo', 
                       'length':'4',
                       'read_only':'0', 'debug':0})
        self.start()
        for i in range(0,100):
            v = rand.random() * 9999999999999999L
            v = long(v)
            hrs.set(v)
            b = hrc.get(1)
            if abs(v - b) >  0:
                print v, b
                raise 'bad value conversion for module holding register'
        for i in range(0,100):
            v = rand.random() * 9999999999999999L
            v = long(v)
            hrc.set(v)
            if abs(v - hrs.get(1)) >  0:
                raise 'bad buffer conversion for module holding register'

    def test_powerlogic(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'PowerLogic Energy', 
                      'length':'4',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'PowerLogic Energy', 
                       'length':'4',
                       'read_only':'0', 'debug':0})
        self.start()
        for i in range(0,100):
            v = rand.random() * 9999999999999L
            hrs.set(v)
            b = hrc.get(1)
            if abs(v - b) >  0.01:
                print '########### ', v, b, v-b
                raise 'bad value conversion for power logic holding register'
        for i in range(0,100):
            v = rand.random() * 9999999999999L
            hrc.set(v)
            if abs(v - hrs.get(1)) >  0.01:
                raise 'bad buffer conversion for power logic holding register'
           
    def test_time_3(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'time', 
                      'length':'3',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'time', 
                       'length':'3',
                       'read_only':'0', 'debug':0})
        self.start()
        for v in (0,1,-1,555,-555, 32767, -32767):
            t = time.time() + v
            hrs.set(t)
            b = hrc.get(1)
            if abs(t - b) >  1:
                print '########### ', t, b, t-b
                raise 'bad value conversion for power logic holding register'
        for v in (0,1,-1,555,-555, 32767, -32767):
            t = time.time() + v
            hrc.set(t)
            b = hrs.get(1)
            if abs(t - b) >  1:
                print '##########', t, b, t-b
                raise 'bad buffer conversion for power logic holding register'
    def test_time_6(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'time', 
                      'length':'6',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'time', 
                       'length':'6',
                       'read_only':'0', 'debug':0})
        self.start()
        for v in (0,1,-1,555,-555, 32767, -32767):
            t = time.time() + v
            hrs.set(t)
            b = hrc.get(1)
            if abs(t - b) >  1:
                print '########### ', t, b, t-b
                raise 'bad value conversion for power logic holding register'
        for v in (0,1,-1,555,-555, 32767, -32767):
            t = time.time() + v
            hrc.set(t)
            b = hrs.get(1)
            if abs(t - b) >  1:
                print '##########', t, b, t-b
                raise 'bad buffer conversion for power logic holding register'
            
                  #'hibyte' :{1:(ConvertRegister.register_hibyte, ConvertValue.convert_hibyte)},
                  #'lobyte' :{1:(ConvertRegister.register_lobyte, ConvertValue.convert_lobyte)},
                  #'loint'  :{1:(ConvertRegister.register_as_loint, ConvertValue.convert_loint)},
                  #'hiint'  :{1:(ConvertRegister.register_as_hiint, ConvertValue.convert_hiint)},
                  #'lochar' :{1:(ConvertRegister.register_as_lochar, ConvertValue.convert_lochar)},
                  #'hichar' :{1:(ConvertRegister.register_as_hichar, ConvertValue.convert_hichar)},
                  #'word'   :{1:(ConvertRegister.register_as_word, ConvertValue.convert_ushort)},
                  #'dword'  :{2:(ConvertRegister.register_as_ulong, ConvertValue.convert_ulong)},
                  #'string' :{0:(ConvertRegister.register_as_string, ConvertValue.convert_string)},
                  #'zstring':{0:(ConvertRegister.register_as_zstring, ConvertValue.convert_zstring)},
                  #'modulo' :{1:(ConvertRegister.register_as_modulo_10000_1, ConvertValue.convert_modulo_1),
                             #2:(ConvertRegister.register_as_modulo_10000_2, ConvertValue.convert_modulo_2),
                             #3:(ConvertRegister.register_as_modulo_10000_3, ConvertValue.convert_modulo_3),
                             #4:(ConvertRegister.register_as_modulo_10000_4, ConvertValue.convert_modulo_4)},
                  #'PowerLogic Energy':{3:(ConvertRegister.register_as_power_logic_3, ConvertValue.convert_power_logic_3),
                                       #4:(ConvertRegister.register_as_power_logic_4, ConvertValue.convert_power_logic_4)},
                  #'time'   :{3:(ConvertRegister.register_as_time_3, ConvertValue.convert_time_3),
                             #6:(ConvertRegister.register_as_time_6, ConvertValue.convert_time_6)}}
#
# Support a standalone excecution.
#
    def test_dl06_energy_4(self):
        hrs = server.HoldingRegister()
        hrs.configure({'name':'hr',
                      'parent':self.server,
                      'register':'40001',
                      'type':'DL06 Energy', 
                      'length':'4',
                      'read_only':'0', 'debug':0})
        hrc = generic.HoldingRegister() #client holding reg
        hrc.configure({'name':'hrc',
                       'parent':self.client,
                       'register':'40001',
                       'type':'DL06 Energy', 
                       'length':'4',
                       'read_only':'0', 'debug':0})
        self.start()
        for v in (0,1,555, 32767, 65535, 65536):
            hrs.set(v)
            b = hrc.get(1)
            if v != b:
                raise 'bad value get client from server for megawatt holding register'
        for v in (0,1,555, 32767, 65535, 65536):
            hrc.set(v)
            if v != hrs.get(1):
                raise 'bad value set client to server for megawatt holding register'

if __name__ == '__main__':
    main()

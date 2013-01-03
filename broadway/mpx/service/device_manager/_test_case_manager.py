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
from mpx_test import DefaultTestFixture
from mpx_test import main

from mpx.lib.node import as_internal_node

from manager import DeviceManager
from manager import UDINS

from udi import UniqueDeviceIdentifier

class UniqueTestIdentifier(UniqueDeviceIdentifier):
    pass
UniqueTestIdentifier.extend_key_map('port','address')

class TestCase(DefaultTestFixture):
    def __init__(self, *args, **kw):
        DefaultTestFixture.__init__(self, *args ,**kw)
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.new_node_tree()
        self.dm = None
        return
    def tearDown(self):
        self.del_node_tree()
        DefaultTestFixture.tearDown(self)
        return
    def add_dm(self):
        self.dm = DeviceManager()
        self.dm.configure({'parent':as_internal_node('/services')})
        return
    def test_instanciate_udins(self):
        UDINS()
        return
    def test_instanciate_device_manager(self):
        DeviceManager()
        return
    def test_add_dm(self):
        self.add_dm()
        return
    def test_udi_methods(self):
        self.add_dm()
        udi1 = self.dm.udi_from_kw(UniqueDeviceIdentifier,
                                   device_class='udi')
        udi2 = self.dm.udi_from_kw(UniqueDeviceIdentifier,
                                   device_class='udi')
        self.assert_comparison('udi2', 'is', 'udi1')
        udi3 = UniqueDeviceIdentifier(device_class='udi')
        self.assert_comparison('udi3', '==', 'udi1')
        self.assert_comparison('udi3', 'is not', 'udi1')
        udi4 = self.dm.udi_from_udi(udi3)
        self.assert_comparison('udi4', 'is', 'udi1')
        test_1_1 = self.dm.udi_from_kw(UniqueTestIdentifier,
                                       device_class='test',
                                       port='/interfaces/com1',
                                       address=1)
        test_1_2 = self.dm.udi_from_kw(UniqueTestIdentifier,
                                       device_class='test',
                                       port='/interfaces/com1',
                                       address=2)
        self.assert_comparison('test_1_2', 'is not', 'test_1_1')
        test_2_1 = self.dm.udi_from_kw(UniqueTestIdentifier,
                                       device_class='test',
                                       port='/interfaces/com2',
                                       address=1)
        test_2_2 = self.dm.udi_from_kw(UniqueTestIdentifier,
                                       device_class='test',
                                       port='/interfaces/com2',
                                       address=2)
        self.assert_comparison('test_2_2', 'is not', 'test_2_1')
        
        self.assert_comparison('test_2_1', 'is not', 'test_1_1')
        self.assert_comparison('test_2_2', 'is not', 'test_1_2')
        test_1_1b = self.dm.udi_from_kw(UniqueTestIdentifier,
                                        device_class='test',
                                        port='/interfaces/com1',
                                        address=1)
        test_1_2b = self.dm.udi_from_kw(UniqueTestIdentifier,
                                        device_class='test',
                                        port='/interfaces/com1',
                                        address=2)
        test_2_1b = self.dm.udi_from_kw(UniqueTestIdentifier,
                                        device_class='test',
                                        port='/interfaces/com2',
                                        address=1)
        test_2_2b = self.dm.udi_from_kw(UniqueTestIdentifier,
                                        device_class='test',
                                        port='/interfaces/com2',
                                        address=2)
        self.assert_comparison('test_1_1', 'is', 'test_1_1b')
        self.assert_comparison('test_1_2', 'is', 'test_1_2b')
        self.assert_comparison('test_2_1', 'is', 'test_2_1b')
        self.assert_comparison('test_2_2', 'is', 'test_2_2b')
        return
    def test_monitor_from_methods_and_start(self):
        self.add_dm()
        monitor1 = self.dm.monitor_from_kw(UniqueDeviceIdentifier,
                                           device_class='udi')
        monitor2 = self.dm.monitor_from_kw(UniqueDeviceIdentifier,
                                           device_class='udi')
        self.assert_comparison('monitor2', 'is', 'monitor1')
        monitor_1_1 = self.dm.monitor_from_kw(UniqueTestIdentifier,
                                              device_class='test',
                                              port='/interfaces/com1',
                                              address=1)
        monitor_1_2 = self.dm.monitor_from_kw(UniqueTestIdentifier,
                                              device_class='test',
                                              port='/interfaces/com1',
                                              address=2)
        self.assert_comparison('monitor_1_1', 'is not', 'monitor_1_2')
        monitor_2_1 = self.dm.monitor_from_udi(
            UniqueTestIdentifier(
                device_class='test',
                port='/interfaces/com2',
                address=1
                )
            )
        monitor_2_2 = self.dm.monitor_from_udi(
            UniqueTestIdentifier(
                device_class='test',
                port='/interfaces/com2',
                address=2
                )
            )
        self.assert_comparison('monitor_2_1', 'is not', 'monitor_2_2')
        instance_list = [monitor1, monitor_1_1, monitor_1_2, monitor_2_1,
                         monitor_2_2]
        node_list = self.dm.dynamic_container().children_nodes()
        while node_list:
            node = node_list.pop()
            self.assert_comparison('node', 'in', 'instance_list')
            instance_list.remove(node)
        self.assert_comparison('instance_list', '==', '[]')
        # Start will cause the monitors to "register" with the Device Manager.
        as_internal_node('/').start()
        return
    def test_start(self):
        self.add_dm()
        self.dm.start()
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

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
##
# Test cases to exercise the BIN multi-port classes.
#

from mpx_test import DefaultTestFixture, main

import struct
import time
import array
import types

from mpx.lib.exceptions import EOverflow
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.node import CompositeNode
from mpx.lib.bacnet import network, server, data, tag

from mpx.lib.bacnet._exceptions import *
from mpx.service.network.bacnet import BIN
from mpx.service.network.bacnet.BIN import *

class Nothing(object):
    pass

def dummy():
    return

class TestCase(DefaultTestFixture):
    def test_BACnetSingleport(self):
        my_internetwork = BACnetInterNetwork()
        my_internetwork.configure({'parent':None, 'name':'internetwork', 'debug':0})
        my_configuration = BIN_Configuration()
        my_configuration.configure({'parent':my_internetwork, 'name':'Configuration','debug':0})
        my_services = BIN_Services()
        my_services.configure({'parent':my_internetwork, 'name':'Services','debug':0})
        my_ip = BIN_IP()
        my_ip.configure({'parent':my_configuration, 'name':'IP', 'network':1, 'port':47809, 'debug':0})
        my_comport = BIN_port()
        my_comport.configure({'parent':my_ip, 'name':'eth0', 'debug':0})
        my_comport._who_is_thread = dummy
        my_internetwork.start()
        try:
            my_comport.running
        except:
            raise Exception('failed to start comport')
        if len (my_configuration._interfaces) != 1:
            raise Exception('failed to create interface object')
        if len(my_configuration._carriers) != 1:
            raise Exception('failed to register carrier node')
        my_comport._who_is_thread = None
        my_internetwork.stop()
        if my_comport.running:
            raise Exception('failed to stop internetwork')

    def test_BACnetMultiport(self):
        my_internetwork = BACnetInterNetwork()
        my_internetwork.configure({'parent':None, 'name':'internetwork', 'debug':0})
        my_configuration = BIN_Configuration()
        my_configuration.configure({'parent':my_internetwork, 'name':'Configuration','debug':0})
        my_services = BIN_Services()
        my_services.configure({'parent':my_internetwork, 'name':'Services','debug':0})
        my_ip = BIN_IP()
        my_ip.configure({'parent':my_configuration, 'name':'IP', 'network':1, 'port':47809, 'debug':0})
        my_comport = BIN_port()
        my_comport.configure({'parent':my_ip, 'name':'eth0', 'debug':0})
        my_comport._who_is_thread = dummy
        my_ip1 = BIN_IP()
        my_ip1.configure({'parent':my_configuration, 'name':'IP1', 'network':2, 'port':47810, 'debug':0})
        my_comport1 = BIN_port()
        my_comport1.configure({'parent':my_ip1, 'name':'eth0', 'debug':0})
        my_comport1._who_is_thread = dummy
        # create Devices node and devices for each channel and a virtual device
        my_devices = BIN_Devices()
        my_devices.configure({'parent':my_internetwork, 'name':'Devices','debug':0})
        my_internetwork.start()
        try:
            my_comport.running
        except:
            raise Exception('failed to start comport')
        try:
            my_comport1.running
        except:
            raise Exception('failed to start comport1')
        if len (my_configuration._interfaces) != 2:
            raise Exception('failed to create interface object')
        if len(my_configuration._carriers) != 2:
            raise Exception('failed to register carrier node')
        # create client device for one interface
        d = network._DeviceInfo()
        d.instance_number = int(1)
        d.object_type = 8
        d.max_apdu_len = 1476
        d.can_recv_segments = 0
        d.can_send_segments = 0
        d.vendor_id = 95
        d.network = int(1)
        d.address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47809)))
        d.readPropertyFallback = 0  
        d.mac_network = int(1)
        d.mac_address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47809)))
        #add this text device to the device table and attempt to access it
        DeviceTable[1] = d
        # request devices under an interface
        if len(my_ip._get_device_table()) != 1:
            raise Exception('Device Table missing device')
        if len(my_ip1._get_device_table()) != 0:
            raise Exception('Device table should be empty')
        if len(my_internetwork.all_devices()) != 1:
            raise Exception('Should be one device in table')
        # create client device for other interface
        d = network._DeviceInfo()
        d.instance_number = int(2)
        d.object_type = 8
        d.max_apdu_len = 1476
        d.can_recv_segments = 0
        d.can_send_segments = 0
        d.vendor_id = 95
        d.network = int(2)
        d.address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47810)))
        d.readPropertyFallback = 0  
        d.mac_network = int(2)
        d.mac_address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47810)))
        #add this text device to the device table and attempt to access it
        DeviceTable[2] = d
        # request devices under an interface
        if len(my_ip._get_device_table()) != 1:
            raise Exception('Device Table for interfance 1 missing device')
        if len(my_ip1._get_device_table()) != 1:
            raise Exception('Device Table for interface 2 missing device')
        if len(my_internetwork.all_devices()) != 2:
            raise Exception('Should be two devices in table')
        # shut things down in an orderly manner
        my_comport._who_is_thread = None
        my_comport1._who_is_thread = None
        my_internetwork.stop()
        if my_comport.running:
            raise Exception('failed to stop internetwork')
        if my_comport1.running:
            raise Exception('failed to stop internetwork')

    def test_BACnetMultiportServer(self):
        my_internetwork = BACnetInterNetwork()
        my_internetwork.configure({'parent':None, 'name':'internetwork', 'debug':0})
        my_configuration = BIN_Configuration()
        my_configuration.configure({'parent':my_internetwork, 'name':'Configuration','debug':0})
        my_services = BIN_Services()
        my_services.configure({'parent':my_internetwork, 'name':'Services','debug':0})
        my_ip = BIN_IP()
        my_ip.configure({'parent':my_configuration, 'name':'IP', 'network':1, 'port':47809, 'debug':0})
        my_comport = BIN_port()
        my_comport.configure({'parent':my_ip, 'name':'eth0', 'debug':0})
        my_comport._who_is_thread = dummy
        my_ip1 = BIN_IP()
        my_ip1.configure({'parent':my_configuration, 'name':'IP1', 'network':2, 'port':47810, 'debug':0})
        my_comport1 = BIN_port()
        my_comport1.configure({'parent':my_ip1, 'name':'eth0', 'debug':0})
        my_comport1._who_is_thread = dummy
        # create Devices node and devices for each channel and a virtual device
        my_devices = BIN_Devices()
        my_devices.configure({'parent':my_internetwork, 'name':'Devices','debug':0})
        # set up Server Device objects for each interface and for a Virtual network
        my_device = ServerDevice()
        my_device.configure({'parent':my_devices, 'name':'95001', 'network':1, 'debug':0})
        my_group = ServerObjectTypeGroup()
        my_group.configure({'parent':my_device, 'name':'8', 'debug':0})
        my_device_object = ServerObjectInstance()
        my_device_object.configure({'parent':my_group, 'name':'95001', 'debug':0})
        #Max APDU length
        my_p62 = ServerPropertyInstance()
        my_p62.configure({'parent':my_device_object, 'name':'62', 'value':1468, 'debug':0})
        #Vendor Indentifier
        my_p120 = ServerPropertyInstance()
        my_p120.configure({'parent':my_device_object, 'name':'120', 'value':95, 'debug':0})
        #Segmentaion Supported
        my_p107 = ServerPropertyInstance()
        #Segmentaion Supported
        my_p107.configure({'parent':my_device_object, 'name':'107', 'value':0, 'debug':0})
        #APDU Segment Timeout
        my_p10 = ServerPropertyInstance()
        my_p10.configure({'parent':my_device_object, 'name':'10', 'value':2000, 'debug':0})
        #APDU Timeout
        my_p11 = ServerPropertyInstance()
        my_p11.configure({'parent':my_device_object, 'name':'11', 'value':4000, 'debug':0})
        #Number of APDU Retries
        my_p73 = ServerPropertyInstance()
        my_p73.configure({'parent':my_device_object, 'name':'73', 'value':3, 'debug':0})

        my_device = ServerDevice()
        my_device.configure({'parent':my_devices, 'name':'95002', 'network':2, 'debug':0})
        my_group = ServerObjectTypeGroup()
        my_group.configure({'parent':my_device, 'name':'8', 'debug':0})
        my_device_object = ServerObjectInstance()
        my_device_object.configure({'parent':my_group, 'name':'95001', 'debug':0})
        #Max APDU length
        my_p62 = ServerPropertyInstance()
        my_p62.configure({'parent':my_device_object, 'name':'62', 'value':1468, 'debug':0})
        #Vendor Indentifier
        my_p120 = ServerPropertyInstance()
        my_p120.configure({'parent':my_device_object, 'name':'120', 'value':95, 'debug':0})
        #Segmentaion Supported
        my_p107 = ServerPropertyInstance()
        #Segmentaion Supported
        my_p107.configure({'parent':my_device_object, 'name':'107', 'value':0, 'debug':0})
        #APDU Segment Timeout
        my_p10 = ServerPropertyInstance()
        my_p10.configure({'parent':my_device_object, 'name':'10', 'value':2000, 'debug':0})
        #APDU Timeout
        my_p11 = ServerPropertyInstance()
        my_p11.configure({'parent':my_device_object, 'name':'11', 'value':4000, 'debug':0})
        #Number of APDU Retries
        my_p73 = ServerPropertyInstance()
        my_p73.configure({'parent':my_device_object, 'name':'73', 'value':3, 'debug':0})

        my_device = ServerDevice()
        my_device.configure({'parent':my_devices, 'name':'95003', 'network':3, 'debug':0})
        my_group = ServerObjectTypeGroup()
        my_group.configure({'parent':my_device, 'name':'8', 'debug':0})
        my_device_object = ServerObjectInstance()
        my_device_object.configure({'parent':my_group, 'name':'95001', 'debug':0})
        #Max APDU length
        my_p62 = ServerPropertyInstance()
        my_p62.configure({'parent':my_device_object, 'name':'62', 'value':1468, 'debug':0})
        #Vendor Indentifier
        my_p120 = ServerPropertyInstance()
        my_p120.configure({'parent':my_device_object, 'name':'120', 'value':95, 'debug':0})
        #Segmentaion Supported
        my_p107 = ServerPropertyInstance()
        #Segmentaion Supported
        my_p107.configure({'parent':my_device_object, 'name':'107', 'value':0, 'debug':0})
        #APDU Segment Timeout
        my_p10 = ServerPropertyInstance()
        my_p10.configure({'parent':my_device_object, 'name':'10', 'value':2000, 'debug':0})
        #APDU Timeout
        my_p11 = ServerPropertyInstance()
        my_p11.configure({'parent':my_device_object, 'name':'11', 'value':4000, 'debug':0})
        #Number of APDU Retries
        my_p73 = ServerPropertyInstance()
        my_p73.configure({'parent':my_device_object, 'name':'73', 'value':3, 'debug':0})
        
        # start system
        my_internetwork.start()
        print DeviceTable

        try:
            my_comport.running
        except:
            raise Exception('failed to start comport')
        try:
            my_comport1.running
        except:
            raise Exception('failed to start comport1')
        if len (my_configuration._interfaces) != 2:
            raise Exception('failed to create interface object')
        if len(my_configuration._carriers) != 2:
            raise Exception('failed to register carrier node')
        # Check for proper values in Device Table for Server objects
        if len(my_ip._get_device_table()) != 1:
            raise Exception('Device Table missing server device')
        if len(my_ip1._get_device_table()) != 1:
            raise Exception('Device Table 1 missing server device')
        print my_internetwork.all_devices()
        if len(my_internetwork.all_devices()) != 2:
            raise Exception('Should be two devices under interfaces')
        if len(DeviceTable) != 3:
            raise Exception("Virtual Device is not in Device Table")
        # create client device for one interface
        d = network._DeviceInfo()
        d.instance_number = int(1)
        d.object_type = 8
        d.max_apdu_len = 1476
        d.can_recv_segments = 0
        d.can_send_segments = 0
        d.vendor_id = 95
        d.network = int(1)
        d.address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47809)))
        d.readPropertyFallback = 0  
        d.mac_network = int(1)
        d.mac_address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47809)))
        #add this text device to the device table and attempt to access it
        DeviceTable[1] = d
        # request devices under an interface
        if not my_ip._get_device_table().get(1):
            raise Exception('Device Table missing client device 1')
        if len(my_ip1._get_device_table()) != 1:
            raise Exception('Device Table 1 has wrong number of devices')
        if len(my_internetwork.all_devices()) != 3:
            raise Exception('Should be three devices under interfaces')
        # create client device for other interface
        d = network._DeviceInfo()
        d.instance_number = int(2)
        d.object_type = 8
        d.max_apdu_len = 1476
        d.can_recv_segments = 0
        d.can_send_segments = 0
        d.vendor_id = 95
        d.network = int(2)
        d.address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47810)))
        d.readPropertyFallback = 0  
        d.mac_network = int(2)
        d.mac_address = network.Addr(inet_aton('127.0.0.1') + pack('!H', int(47810)))
        #add this text device to the device table and attempt to access it
        DeviceTable[2] = d
        # request devices under an interface
        if len(my_ip._get_device_table()) != 2:
            raise Exception('Device Table for interfance 1 missing device')
        if len(my_ip1._get_device_table()) != 2:
            raise Exception('Device Table for interface 2 missing device')
        if len(my_internetwork.all_devices()) != 4:
            raise Exception('Should be four devices under interfaces')
        if len(DeviceTable) != 5:
            raise Exception("Device Table should contain 5 devices")
        # shut things down in an orderly manner
        my_comport._who_is_thread = None
        my_comport1._who_is_thread = None
        my_internetwork.stop()
        if my_comport.running:
            raise Exception('failed to stop internetwork')
        if my_comport1.running:
            raise Exception('failed to stop internetwork')

    def test_BACnetMultiportNetworkConflict(self):
        my_internetwork = BACnetInterNetwork()
        my_internetwork.configure({'parent':None, 'name':'internetwork', 'debug':0})
        my_configuration = BIN_Configuration()
        my_configuration.configure({'parent':my_internetwork, 'name':'Configuration','debug':0})
        my_services = BIN_Services()
        my_services.configure({'parent':my_internetwork, 'name':'Services','debug':0})
        my_ip = BIN_IP()
        my_ip.configure({'parent':my_configuration, 'name':'IP', 'network':1, 'port':47809, 'debug':0})
        my_comport = BIN_port()
        my_comport.configure({'parent':my_ip, 'name':'eth0', 'debug':0})
        my_comport._who_is_thread = dummy
        my_ip1 = BIN_IP()
        my_ip1.configure({'parent':my_configuration, 'name':'IP1', 'network':1, 'port':47810, 'debug':0})
        my_comport1 = BIN_port()
        my_comport1.configure({'parent':my_ip1, 'name':'eth0', 'debug':0})
        my_comport1._who_is_thread = dummy
        my_internetwork.start()
        try:
            my_comport.running
        except:
            pass
        else:
            raise Exception('failed to NOT start comport')
        try:
            my_comport1.running
        except:
            pass
        else:
            raise Exception('failed to NOT start comport1')
        if len (my_configuration._interfaces) != 0:
            raise Exception('failed to NOT create interface object')
        if len(my_configuration._carriers) != 0:
            raise Exception('failed to NOT register carrier node')
        my_comport._who_is_thread = None
        my_comport1._who_is_thread = None
        my_internetwork.stop()

if __name__ == '__main__':
    main()

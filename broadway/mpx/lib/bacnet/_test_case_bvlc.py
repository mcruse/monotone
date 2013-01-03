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
##
# Test cases to exercise the bvlc class.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib.exceptions import EOverflow
from mpx.lib.bacnet.npdu import Addr
from mpx.lib.exceptions import EInvalidValue

import mpx.lib.bacnet.bvlc
from mpx.lib.bacnet.bvlc import *
from mpx.lib.bacnet.bvlc import _str_as_ulong, _str_as_ushort, _ulong_as_str, _ulong_as_ip_format_str
from mpx.lib.bacnet.bvlc import _ip_format_str_as_ulong, _ushort_as_str, _bvlc_length
from mpx.lib.bacnet.bvlc import _test_case_support
import struct

from mpx.lib import pause, msglog
from mpx.lib.bacnet import npdu, network
from mpx.lib.bacnet.npdu import NPDU, Addr

import mpx.lib.bacnet._bvlc
from mpx.lib.bacnet._bvlc import _recv_queue
from mpx.lib.bacnet._bvlc import bvlc_send as send

class FakeInterface:
    def __init__(self):
        self.type = "IP"
        self.name = "fake"
        self.interface_id = -1
        self.network = 1
        self.addr = Addr('\x0a\x00\x01\x50\xba\xc0')
        self.broadcast = Addr('\x0a\x00\x01\xff\xba\xc0')
        self.our_ip_address = 0x7f000001
        self.our_ip_port = 0xbca0
        self.is_open = 1
        _test_case_support(self)

class TestCase(DefaultTestFixture):
    def test_empty(self):
        BroadcastDistributionTable(FakeInterface())
        fdt = ForeignDeviceTable()
        Result()
        ReadBroadcastDistributionTableAck()
        fdt._stop_ticking()
        
    def test_Result(self):
        Result(0x0000)
        Result(0x0010)
        Result(0x0020)
        Result(0x0030)
        Result(0x0040)
        Result(0x0050)
        Result(0x0060)
        
        try:
            Result(0x0061)
            raise 'Result failed to detect result code too large'
        except EInvalidValue, e:
            Result(decode='\x81\x00\x06\x00\x00\x00')
            try:
                Result(decode='\x81\x00\x07\x00\x00\x00\x00')
                raise 'Result failed to detect too long packet'
            except EInvalidValue, e:
                try:
                    Result(decode='\x81\x01\x06\x00\x00\x00')
                    raise 'Result failed to detect wrong frame type'
                except EInvalidValue, e:
                    pass
                
    def test_WriteBroadcastDistributionTable(self):
        try:
            WriteBroadcastDistributionTable()
            raise 'WriteBroadcastDistributionTable failed to detect null parameters'
        except EInvalidValue, e:
            a = '\x81\x01\x00\x22\x0b\x00\x01\x02\xBA\xC2\xFF\xFF\xFF\xFF\x0a\x00\x01\x02\xBA\xC2\xFF\xFF\xFF\xFF\x0a\x00\x01\xf8\xBA\xC0\xFF\xFF\xFF\xFF'
            WriteBroadcastDistributionTable(decode=a)
            
    def test_BroadcastDistributionTable(self):
        a = '\x81\x01\x00\x22\x0b\x00\x01\x02\xBA\xC2\xFF\xFF\xFF\xF0\x0a\x00\x01\x02\xBA\xC2\xFF\xFF\xFF\xFF\x0a\x00\x01\xf8\xBA\xC0\xFF\xFF\xFF\xFF'
        b = WriteBroadcastDistributionTable(decode=a)
        c = BroadcastDistributionTable(FakeInterface())
        c.write_new_table_contents(b)
        d = c.as_text()
        e = BroadcastDistributionTable(FakeInterface())
        e.from_text(d)
        f = WriteBroadcastDistributionTable(e)
        if f.encoding <> a:
            raise 'BroadcastDistributionTable conversion failure'
        if d != e.as_text():
           raise 'BroadcastDistributionTable text conversion failure'
        
       

    def test_ReadBroadcastDistributionTable(self):
        a = '\x81\x02\x00\x04'
        b = ReadBroadcastDistributionTable(decode=a)
        c = ReadBroadcastDistributionTable()
        if c.encoding <> a:
            raise 'ReadBroadcastDistributionTable failed to encode'
        if b.encoding <> a:
            raise 'ReadBroadcastDistributionTable failed to decode'
        pass

    def test_ReadBroadcastDistributionTableAck(self):
        a = '\x81\x01\x00\x22\x0b\x00\x01\x02\xBA\xC2\xFF\xFF\xFF\xF0\x0a\x00\x01\x02\xBA\xC2\xFF\xFF\xFF\xFF\x0a\x00\x01\xf8\xBA\xC0\xFF\xFF\xFF\xFF'
        a = '\x81\x01\x00\x22\x0b\x00\x01\x02\xba\xc2\xff\xff\xff\xf0\x0a\x00\x01\x02\xba\xc2\xff\xff\xff\xff\x0a\x00\x01\xf8\xba\xc0\xff\xff\xff\xff'
        b = WriteBroadcastDistributionTable(decode=a)
        fi = FakeInterface()
        c = BroadcastDistributionTable(fi)
        c.write_new_table_contents(b)
        d = c.read_table()
        e = '\x81\x03\x00\x22\x0b\x00\x01\x02\xba\xc2\xff\xff\xff\xf0\x0a\x00\x01\x02\xba\xc2\xff\xff\xff\xff\x0a\x00\x01\xf8\xba\xc0\xff\xff\xff\xff'
        if d.encoding <> e:
            raise 'ReadBroadcastDistributionTableAck failure'
        pass

    def test_ForwardedNPDU(self):
        a = '\x81\x04\x00\x20\x55\xAA\x05\xA0\xBA\xC01234567890123456789012'
        b = ForwardedNPDU(decode=a)
        if b.encoding != a:
            raise 'ForwardedNPDU failed to decode encoding'
        if b.length != 32:
            raise 'ForwardedNPDU failed to decode length'
        if b.originating_address.address != Addr('\x55\xAA\x05\xA0\xBA\xC0').address:
            raise 'ForwardedNPDU failed to decode address'
        if b.npdu != a[10:]:
            raise 'ForwardedNPDU failed to decode ndpu'
        c = ForwardedNPDU(Addr('\x55\xAA\x05\xA0\xBA\xC0'), a[10:])
        if c.encoding != a:
            raise 'ForwardedNPDU failed to encode'
        pass

    def test_RegisterForeignDevice(self):
        a = '\x81\x05\x00\x06\x00\xff'
        b = Addr('\x55\xAA\x05\xA0\xBA\xC0')
        c = RegisterForeignDevice(b, decode=a)
        if c.encoding != a:
            raise 'RegisterForeignDevice failed to decode encoding'
        if c.foreign_device_address.address != b.address:
            raise 'RegisterForeignDevice failed to decode addr'
        if c.time_to_live != 255:
            raise 'RegisterForeignDevice failed to decode time_to_live'
        d = RegisterForeignDevice(b, 255)
        if d.encoding != a:
            raise 'RegisterForeignDevice failed to encode encoding'
        if d.foreign_device_address.address != b.address:
            raise 'RegisterForeignDevice failed to encode addr'
        if d.time_to_live != 255:
            raise 'RegisterForeignDevice failed to encode time_to_live'
        pass

    def test_ReadForeignDeviceTable(self):
        a = '\x81\x06\x00\x04'
        b = ReadForeignDeviceTable(decode=a)
        c = ReadForeignDeviceTable()
        if c.encoding <> a:
            raise 'ReadForeignDeviceTable failed to encode'
        if b.encoding <> a:
            raise 'ReadForeignDeviceTable failed to decode'
        pass

    def test_ReadForeignDeviceTableAck(self):
        a = Addr('\x55\xAA\x05\xA0\xBA\xC0')
        b = RegisterForeignDevice(a, 255)
        c = ForeignDeviceTable()
        c.register_foreign_device(b)
        d = c.read_table()
        e = '\x81\x07\x00\x0e\x55\xaa\x05\xa0\xba\xc0\x00\xff\x01\x1d'
        if d.encoding <> e:
            raise 'ReadForeignDeviceTableAck failure'
        pass

    def test_DeleteForeignDeviceTableEntry(self):
        a = Addr('\x55\xAA\x05\xA0\xBA\xC0')
        b = RegisterForeignDevice(a, 255)
        c = ForeignDeviceTable()
        c.register_foreign_device(b)
        d = '\x81\x08\x00\x0a\x55\xAA\x05\xA0\xBA\xC0'
        d = DeleteForeignDeviceTableEntry(decode=d)
        e = c.delete_entry(d)
        if e.encoding != Result(0x0000).encoding:
            raise 'DeleteForeignDeviceTableEntry failed to delete'
        e = c.delete_entry(d)
        if e.encoding != Result(0x0050).encoding:
            raise 'DeleteForeignDeviceTableEntry deleted the same object twice'
        pass

    def test_DistributeBroadcastToNetwork(self):
        a = '\x81\x09\x00\x200123456789012345678901234567'
        b = DistributeBroadcastToNetwork(decode=a)
        if b.length != len(a):
            raise 'DistributeBroadcastToNetwork failed to decode length'
        if b.npdu != a[4:]:
            raise 'DistributeBroadcastToNetwork failed to decode npdu'
        if b.encoding != a:
            raise 'DistributeBroadcastToNetwork failed to decode encoding'
        c = DistributeBroadcastToNetwork(a[4:])
        if c.length != b.length:
            raise 'DistributeBroadcastToNetwork failed to encode length'
        if c.npdu != b.npdu:
            raise 'DistributeBroadcastToNetwork failed to encode npdu'
        if c.encoding != b.encoding:
            raise 'DistributeBroadcastToNetwork failed to encode'
        pass

    def test_OriginalBroadcastNPDU(self):
        a = '\x81\x0B\x00\x200123456789012345678901234567'
        b = OriginalBroadcastNPDU(decode=a)
        if b.encoding != a:
            raise 'OriginalBroadcastNPDU failed to decode encoding'
        if b.length != len(a):
            raise 'OriginalBroadcastNPDU failed to decode length'
        if b.npdu != a[4:]:
            raise 'OriginalBroadcastNPDU failed to decode npdu'
        c = OriginalBroadcastNPDU(a[4:])
        if c.length != b.length:
            raise 'OriginalBroadcastNPDU failed to encode length'
        if c.npdu != b.npdu:
            raise 'OriginalBroadcastNPDU failed to encode npdu'
        if c.encoding != b.encoding:
            raise 'OriginalBroadcastNPDU failed to encode'
        pass

    def test_FDT(self):
        n = network.open_interface('IP', 'lo', 1)
        a = '\x81\x05\x00\x06\x00\x05'
        b = Addr('\x55\xAA\x05\xA0\xBA\xC0')
        c = RegisterForeignDevice(b, decode=a)
        f = ForeignDeviceTable()
        f.register_foreign_device(c)
        for x in range(30):
            pause(1.0)
            if len(f.entries) == 0:
                raise 'Foreign device table tick failure, early removal'
        pause(10.0)
        if len(f.entries) != 0:
            raise 'Foreign device table tick failure to remove device'
        #e = '\x81\x0B\x20\x000123456789012345678901234567'
        #o = OriginalBroadcastNPDU(decode=e)
        #r = Addr('\xAA\x55\x05\xA0\xBA\xC0')
        #f.forward_original_broadcast_message(n.network, r, o.npdu)
        #how do I check to see if it made it?
        #g = '\x81\x04\x20\x00\x55\xAA\x05\xA0\xBA\xC01234567890123456789012'
        #h = ForwardedNPDU(decode=g)
        #f.broadcast_forwarded_message(n.network, r, h)
        #f.distribute(n.network, r, h)
        f._stop_ticking()
        network.close_interface(n)
        pass
    
    def test_ulong_as_str(self):
        a = _ulong_as_str(12345678)
        if a != '\x00\xbcaN':
            raise '_ulong_as_str failed equal'
        try:
            a = _ulong_as_str(1234567891283478912374L)
        except EInvalidValue, e:
            return
        raise '_ulong_as_str failed to detect to number too large'

    def test_ushort_as_str(self):
        a = _ushort_as_str(12345)
        if a != '\x30\x39':
           raise '_ushort_as_str failed equal test'
        try:
            a = _ushort_as_str(1234567890)
        except EInvalidValue, e:
            return
        raise '_ushort_as_str failed to detect to number too large'

    def test_str_as_ulong (self):
        a = _str_as_ulong('\x00\xbcaN')
        if a != 12345678:
            raise '_str_as_ulong failed equal'
        pass
    
    def test_str_as_ushort (self):
        a = _str_as_ushort('\x30\x39')
        if a != 12345:
            raise '_str_as_ushort failed equal'
        pass
    
    def test_ulong_as_ip_format_str (self):
        a = _ulong_as_ip_format_str(12345678)
        if a != '0.188.97.78':
            raise '_ulong_as_ip_format_str failed equal'
        a = _ulong_as_ip_format_str(0)
        if a != '0.0.0.0':
            raise '_ulong_as_ip_format_str failed 0.0.0.0'
        a = _ulong_as_ip_format_str(4294967295L)
        if a != '255.255.255.255':
            raise '_ulong_as_ip_format_str failed 255.255.255.255'
        pass

    def test_ip_format_str_as_ulong (self):
        a = _ip_format_str_as_ulong('0.188.97.78')
        if a != 12345678:
            raise '_ip_format_str_as_ulong failed equal'
        a = _ip_format_str_as_ulong('0.0.0.0')
        if a != 0:
            raise '_ip_format_str_as_ulong failed 0'
        a = _ip_format_str_as_ulong('255.255.255.255')
        if a != 4294967295L:
            raise '_ip_format_str_as_ulong failed 4294967295L'
        pass
    
    def test_bvlc_length (self):
        a = '\x81\x00\x00\x06\x00\x00'
        b = _bvlc_length(a)
        if b != 6:
            raise '_bvlc_length failed equal'
        a = '\x81\x00\x00\x00\x00\x00'
        b = _bvlc_length(a)
        if b != 0:
            raise '_bvlc_length failed 0'
        a = '\x81\x00\xFF\xFF\x00\x00'
        b = _bvlc_length(a)
        if b != 65535:
            raise '_bvlc_length failed 65535'
        pass
    def _service_bbt_queue(self):
        pass
    
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

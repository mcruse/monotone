"""
Copyright (C) 2002 2003 2004 2005 2007 2010 2011 Cisco Systems

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
# BACnet Broadcast Managment Device (BBMD)
# 
import types
import struct
import threading
from mpx.lib.threading import Lock, Semaphore, ImmortalThread

from mpx.lib import pause, msglog
from mpx.lib.bacnet import npdu, network
from mpx.lib.bacnet.network import _network_map
from mpx.lib.bacnet.npdu import NPDU, Addr
from mpx.lib.exceptions import EInvalidValue, ETypeError
from _bvlc import _recv_queue
from _bvlc import bvlc_send as send
import time
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.debug import dump
from mpx.lib.scheduler import scheduler

debug = 0

def _dump_send(network, address, msg):
    print "BBMD send: network =", network
    print "BBMD send: address =", Addr(address)
    dump(msg, "BBMD send:")

# the following series of classes represent the various kinds of BACnet messages

##
# Result code BVLT message
# Consists of:
#    2 octet result_code
#    4 octet ip_mask
class Result:
    ##
    # instantiated in two ways:
    #   use "decode=" to derive from raw binary string:
    # @param raw string containing encoded entry
    #   or use integer parameters:
    # @param result_code
    def __init__(self, result_code=0, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        else:
            self.result_code = result_code
            self.encode()

    def decode(self, buffer):
        if len(buffer) != 6:
            raise EInvalidValue('decode', buffer, text='length of buffer must be 6')
        self.encoding = buffer
        if ord(self.encoding[1]) != 0x00:
            raise EInvalidValue('function_code', self.encoding[1], text='Result function code must be 0')
        self.result_code  =  _str_as_ushort(self.encoding[4:6])

    def encode(self, code=None):
        if code:
            self.result_code = code
        if self.result_code > 0x0060:
            raise EInvalidValue('result_code', self.result_code)
        self.encoding = chr(0x81) + \
                        chr(0x00) + \
                        chr(0x00) + \
                        chr(0x06) + \
                        _ushort_as_str(self.result_code)

##
# Write the Broadcast Distribution Table to BBMD memory message
# contains a list of BDT entries
# instance variables:
#   encoding   the binary string representation of the message
#   entries    a List of BDT_Entry's
#   number_of_entries  the, ah, number of entries
#   length     the raw message length
class WriteBroadcastDistributionTable:
    ##
    # instantiated in two ways:
    #   use "decode=" to derive from raw binary string:
    # @param raw string containing encoded entry
    #   or parameters:
    # @param bdt the broadcast distribution table
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 1:
            self.encode(args[0])
        else:
            raise EInvalidValue('args', args, text='requires BDT table  or decode')

    def decode(self, buffer):
        if len(buffer) < 4:
            raise EInvalidValue('buffer', buffer, text='length of buffer must at least 4')
        self.encoding = buffer  #just a default encoding
        self.length = _bvlc_length (self.encoding)
        if self.length != len(buffer):
            raise EInvalidValue('buffer', buffer, text='length field mismatch')
        self.number_of_entries = (self.length - 4) / 10
        self.entries = [];
        for i in range(self.number_of_entries):
            self.entries.append(BDT_Entry(decode=self.encoding[i*10+4:i*10+14]))

    def encode(self, bdt):
        proxy = ReadBroadcastDistributionTableAck()  #cheater, cheater....
        for entry in bdt.entries:
            proxy.append(entry)
        self.encoding = '\x81\x01' + proxy.encoding[2:] #pumpkin eater...

##
# Read the Broadcast Distribution Table from BBMD memory message
# contains a list of BDT entries
# instance variables:
#   encoding   the binary string representation of the message
class ReadBroadcastDistributionTable:
    ##
    # instantiated in two ways:
    #   use "decode=" to derive from raw binary string:
    # @param raw string containing encoded entry
    #   or no parameters to create a new message
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 0:
            self.encode()
        else:
            raise EInvalidValue('args', args, text='requires no parameters or decode')

    def decode(self, buffer):
        self.encoding = buffer
        #incoming messages are delt with in the service routine

    def encode(self):
        self.encoding = chr(0x81) + \
                        chr(0x02) + \
                        chr(0x00) + \
                        chr(0x04)
##
# The Read Broadcast Distribution Table Acknowledgement message
# contains a list of BDT entries
# instance variables:
#   encoding   the binary string representation of the message
#   length     the raw message length
#   entries    a list of bdt_entries
class ReadBroadcastDistributionTableAck:
    ##
    # instantiated to an empty table message:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 0:
            self.encode()
        else:
            raise EInvalidValue('requires no parameters or decode=')

    def decode(self, buffer):
        self.encoding = buffer
        self.length = _bvlc_length(buffer)
        self.entries = []
        for i in range(4, self.length, 10):
            self.entries.append(BDT_Entry(decode=buffer[i:i+10]))

    def encode(self):
        self.header_encoding = chr(0x81) + chr(0x03)
        self.length = 4
        self.length_encoding = chr(0x00) + chr(0x04)
        self.tail_encoding = ''
        self.encoding = self.header_encoding + \
                        self.length_encoding + \
                        self.tail_encoding
        self.entries = []
                        
    ##
    # Add an additional table entry to the message:
    def append(self, bdt_entry):
        self.entries.append(bdt_entry)
        self.tail_encoding += bdt_entry.encoding
        self.length += 10
        self.length_encoding = struct.pack('!H', self.length)
        self.encoding = self.header_encoding + \
                        self.length_encoding + \
                        self.tail_encoding

##
# Used to forward broadcast messages to BBMD and FDs
# 
class ForwardedNPDU:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 2:
            self.encode(args[0], args[1])
        else:
            raise ETypeError('requires addr and ndpu or decode')

    def decode(self, buffer):
        self.encoding = buffer
        self.length = _bvlc_length (buffer)
        self.originating_address = Addr(buffer[4:10])
        self.npdu = buffer[10:]

    def encode(self, addr, npdu):
        self.length = len(npdu) + 10
        self.originating_address = addr
        self.npdu = npdu
        self.encoding = chr(0x81) + \
                        chr(0x04) + \
                        chr((self.length >> 8) & 0xff) + \
                        chr(self.length & 0xff) + \
                        addr.address + \
                        npdu
##
# Used to register or re-register a foreign device in the FDT table
# 
class RegisterForeignDevice:
    def __init__(self, addr, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(addr, keywords['decode'])
        elif len(args) == 1:
            self.encode(addr, args[0])
        else:
            raise ETypeError('requires addr and ndpu or decode')

    def decode(self, addr, buffer):
        self.encoding = buffer
        self.foreign_device_address = addr
        self.time_to_live = _str_as_ushort(buffer[4:6])

    def encode(self, addr, ttl):
        self.foreign_device_address = addr
        self.time_to_live = ttl
        self.encoding = chr(0x81) + \
                        chr(0x05) + \
                        chr(0x00) + \
                        chr(0x06) + \
                        _ushort_as_str(ttl)

class ReadForeignDeviceTable:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 0:
            self.encode()
        else:
            raise ETypeError('requires no args or decode')

    def decode(self, buffer):
        self.encoding = buffer
        #incoming messages are delt with in the service routine

    def encode(self):
        self.encoding = chr(0x81) + \
                        chr(0x06) + \
                        chr(0x00) + \
                        chr(0x04)
        
#@todo implement decoding of incoming RFDT Ack message
class ReadForeignDeviceTableAck:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 0:
            self.encode()
        else:
            raise ETypeError('requires no parameters or decode=')

    def decode(self, buffer):
        self.encoding = buffer
        self.length = _bvlc_length(buffer)
        self.entries = []
        for i in range(4, self.length, 10):
            self.entries.append(FDT_Entry(decode=buffer[i:i+10]))

    def encode(self):
        self.header_encoding = chr(0x81) + chr(0x07)
        self.length = 4
        self.length_encoding = chr(0x00) + chr(0x04)
        self.tail_encoding = ''
        self.encoding = self.header_encoding + \
                        self.length_encoding + \
                        self.tail_encoding
                        
    def append(self, fdt_entry):
        self.tail_encoding += fdt_entry.encoding
        self.length += 10
        self.length_encoding = struct.pack('!H', self.length)
        self.encoding = self.header_encoding + \
                        self.length_encoding + \
                        self.tail_encoding

##
# Used to remove a foreign device in the FDT table
# 
class DeleteForeignDeviceTableEntry:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 2:
            self.encode(args[0])
        else:
            raise ETypeError('requires addr or decode')

    def decode(self, buffer):
        self.encoding = buffer
        self.foreign_device_address = Addr(buffer[4:10])

    def encode(self, addr):
        self.foreign_device_address = addr
        self.encoding = chr(0x81) + \
                        chr(0x08) + \
                        chr(0x00) + \
                        chr(0x0A) + \
                        addr.address

##
# Used to forward broadcast messages to BBMD and FDs
# 
class DistributeBroadcastToNetwork:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 1:
            self.encode(args[0])
        else:
            raise ETypeError('requires ndpu or decode')

    def decode(self, buffer):
        self.encoding = buffer
        self.length = _bvlc_length (buffer)
        self.npdu = buffer[4:]

    def encode(self, npdu):
        self.length = len(npdu) + 4
        self.npdu = npdu
        self.encoding = chr(0x81) + \
                        chr(0x09) + \
                        chr((self.length >> 8) & 0xff) + \
                        chr(self.length & 0xff) + \
                        npdu

class OriginalBroadcastNPDU:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 1:
            self.encode(args[0])
        else:
            raise ETypeError('requires ndpu or decode')

    def decode(self, buffer):
        self.encoding = buffer
        self.length = _bvlc_length (buffer)
        self.npdu = buffer[4:]

    def encode(self, npdu):
        self.length = len(npdu) + 4
        self.npdu = npdu
        self.encoding = chr(0x81) + \
                        chr(0x0B) + \
                        chr((self.length >> 8) & 0xff) + \
                        chr(self.length & 0xff) + \
                        npdu
                        
# End of messages
# Broadcast Distribution Table and entry object follow:

##
# Entry in the Broadcast Distribution Table (BDT)
# Consists of:
#    4 octet ip_address
#    2 octet ip_port
#    4 octet ip_mask
class BDT_Entry:
    ##
    # instantiated in three ways:
    #   use "decode=" to derive from raw binary string:
    # @param raw string containing encoded entry
    #   use "from_text=" to derive from text form:
    # @param list of strings containing entry values
    #   or use integer parameters:
    # @param address integer of ip address
    # @param port default=0xBAC0
    # @param distribution_mask integer of ip broadcast mask (usually 0xFFFFFFFF, Clause J.4.3.2)
    def __init__(self, address=None, port=0xBAC0, distribution_mask=None, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
            return
        elif keywords.has_key('from_text'):
            self.from_text(keywords['from_text'])
            return
        elif address is None or distribution_mask is None:
            raise TypeError('Requires 3 args or decode')
        self.encode(address, port, distribution_mask)
        
    def __cmp__(self, other):
        if self.ip_address == other.ip_address:
            if self.ip_port == other.ip_port:
                if self.ip_mask == other.ip_mask:
                    return 0
                else:
                    return cmp(self.ip_mask, other.ip_mask)
            else:
                return cmp(self.ip_port, other.ip_port)
        return cmp(self.ip_address, other.ip_address)

    def decode(self, buffer):
        if len(buffer) != 10:
            raise ETypeError('BDT entries must be 10 octets long')
        self.encoding = buffer
        self.ip_address = _str_as_ulong  (self.encoding[0:4])
        self.ip_port    = _str_as_ushort (self.encoding[4:6])
        self.ip_mask    = _str_as_ulong  (self.encoding[6:10])

    def encode(self, address, port, distribution_mask):
        self.ip_address = address
        self.ip_mask = distribution_mask
        self.ip_port = port
        self.encoding = _ulong_as_str  (self.ip_address) + \
                        _ushort_as_str (self.ip_port)    + \
                        _ulong_as_str  (self.ip_mask)
    ##
    # return the address, port values as a Addr object
    def asBBMDaddress(self):
        ip = long(self.ip_address) | (0xffffffffL ^ long(self.ip_mask))
        ip &= 0xffffffffL
        return Addr(struct.pack('!LH', ip, self.ip_port )) #six byte

    ##
    # answer a three element list of text strings that represent the object
    def as_text(self):
        return (_ulong_as_ip_format_str(self.ip_address), 
                str(self.ip_port), 
                _ulong_as_ip_format_str(self.ip_mask),)
        
    ##
    # instantiate the object from a three element list of text strings
    def from_text(self, list):
        self.encode(_ip_format_str_as_ulong(list[0]),
                    int(list[1]),
                    _ip_format_str_as_ulong(list[2]))

##
# The BBMD table (BDT)
# 
class BroadcastDistributionTable:
    ##
    # Initialize the object.
    #
    def __init__(self, interface, *args, **keywords):
        self.interface = interface
        self.ourBDTentry = None
        self.entries = []
        self.node = None #supervising ion
        # @fixme ADD SELF
        self.reports = {}
        #self.network = 0  #init with network interface number?
        if keywords.has_key('from_text'):
            self.from_text(keywords['from_text'])
        elif len(args) > 0:
            raise ETypeError('requires no parameters or "from_text="')
        if self.ourBDTentry is None: #used by broadcast_forwarded_message
            self._set_our_bdt_entry()

    def _set_our_bdt_entry(self):
        network = self.interface.network
        if (self.entries): #we have a table
            for entry in self.entries:
                if (entry.ip_address == \
                    BBMD_servers[network].our_ip_address) and \
                    (entry.ip_port == BBMD_servers[network].our_ip_port):
                    self.ourBDTentry = entry
                    break
        #if self.ourBDTentry is None:
            #entry = BDT_Entry(_str_as_ulong(self.interface.addr.address[0:4]),
                              #_str_as_ushort(self.interface.addr.address[4:6]),
                              #0xFFFFFFFF)
            #self.entries.append(entry)
            #self.ourBDTentry = entry
    ##
    # replace the table contents with a new list
    # j.2.2
    def write_new_table_contents(self, WBDT_message):
        try:
            allow = 1
            try:
                allow = self.node.allow_external_table_editor
            except:
                pass
            if allow:
                self.ourBDTentry = None
                self.entries = WBDT_message.entries
                answer = Result(0x0000) #default response that everything was ok
                try:
                    if self.node: #persist the data
                        self.node.save_table(self.as_text())
                except: #don't disturb proper response code
                    msglog.exception()
            else:
                raise EPermission('Supervising node: %s will not allow external editor' % self.node.name)
        except:
            msglog.exception()
            answer = Result(0x0010) #nak
        return answer

    ##
    # return a ReadBroadcastDistributionTableAck message 
    # which contains the contents of the BDT
    # j.2.3
    def read_table(self):
        try: #generate an ack with the contents of the table
            answer = ReadBroadcastDistributionTableAck()
            for entry in self.entries:
                answer.append(entry)
        except:
            msglog.exception()
            answer = Result(0x0020)  #default to NAK
        return answer
    
    ##
    # forward a broadcast message to all BBMDs (and Foreign devices)
    # j.4.5
    def forward_original_broadcast_message(self, network, addr,
                                           original_message_npdu):
        if (self.entries): #we have a table
            #msg = ForwardedNPDU(addr, original_message_npdu).encoding
            for entry in self.entries:
                msg = ForwardedNPDU(addr, original_message_npdu).encoding
                if (entry.ip_address !=
                    BBMD_servers[network].our_ip_address) or \
                    (entry.ip_port != BBMD_servers[network].our_ip_port):
                    if debug > 1:
                        _dump_send(network, entry.asBBMDaddress().address, msg)
                    send(network, entry.asBBMDaddress().address, msg)
                    
    ##
    # locally broadcast a forwarded message from another BBMD (or Foreign device)
    # j.4.5
    def broadcast_forwarded_message(self, network, forwarded_message_packet):
        if self.ourBDTentry is None:
            self._set_our_bdt_entry()
        if self.ourBDTentry:
            if self.ourBDTentry.ip_mask & 1:  #our mask indicates directed broadcasts are not used
                if debug > 1:
                    _dump_send(network, self.interface.broadcast.address,
                               forwarded_message_packet.encoding)
                send(network, self.interface.broadcast.address,
                     forwarded_message_packet.encoding)
            else:
                if debug > 1:
                    print "The f---ing thing did not go"
        else:
            if debug > 1:
                print "WE have no entry for ourself in the BDT but received a request to broadcast"
    ##
    # distribute a broadcast message to all BBMDs from a foreign device
    # is also used to send a RegisterForeignDevice to a remote BBMD when we are a Foreign Device
    # j.4.5
    def distribute(self, network, addr, forwarded_message):
        if (self.entries): #we have a table
            for entry in self.entries:
                msg = forwarded_message.encoding
                if ((entry.ip_address !=
                     BBMD_servers[network].our_ip_address) or \
                    (entry.ip_port != BBMD_servers[network].our_ip_port)):
                    if debug > 1:
                        _dump_send(network, entry.asBBMDaddress().address, msg)
                    send(network, entry.asBBMDaddress().address, msg)
                    
    ##
    # answer a list of lists with text representations of the table values
    # j.4.5
    def as_text(self):
        answer = []
        if (self.entries):
            for entry in self.entries:
                answer.append(entry.as_text())
        return answer

    ##
    # set the contents of the table from a list of lists of strings
    # j.4.5
    def from_text(self, lists, node=None):
        if node:
            self.node = node
        self.entries = []
        self.ourBDTentry = None
        if (lists):
            for entry in lists:
                self.entries.append(BDT_Entry(from_text=entry))
    ##
    # query all BBMDs in the table and prepare a report
    def report(self, network):
        self.reports = {}
        answer = []
        if (self.entries):
            msg = ReadBroadcastDistributionTable().encoding
            for entry in self.entries:
                if debug > 1:
                    _dump_send(network, entry.asBBMDaddress().address, msg)
                a=network
                b=entry.asBBMDaddress().address
                c=msg
                send(a,b,c)
            timeout = 0
            _module_lock.acquire()
            try:
                while (len(self.reports.keys()) < len(self.entries)) and \
                      (timeout < 10):
                    _module_lock.release()
                    pause(0.5)
                    timeout += 1
                    _module_lock.acquire()
                for entry in self.entries:
                    status = 'no response'
                    if self.reports.has_key(entry.asBBMDaddress().address):
                        status = 'ok'
                        if self.entries != \
                           self.reports[entry.asBBMDaddress().address]:
                            status = 'mismatch'
                    string = entry.as_text()
                    answer.append((string[0], string[1], string[2], status,))
            finally:
                try:
                    _module_lock.release()
                except:
                    pass
        return answer

    def read_broadcast_distributioan_table_ack(self, network, addr, ack):
        _module_lock.acquire()
        try: self.reports[addr.address] = ack.entries
        finally: _module_lock.release()
    
    ##
    # update all the BBMDs to match the new table contents
    def update_bbmds(self,network, list):
        global our_ip_address
        global our_ip_port
        if self.node:
            if self.node.hasattr('allow_external_table_editor'):
                if not self.node.allow_external_table_editor:
                    return #the supervising node will not allow the table to change
        self.from_text(list) #update our own table first
        try:
            if self.node: #persist the data
                self.node.save_table(list)
        except: #don't disturb proper response code if failed
            msglog.exception()
        if (self.entries):
            msg = WriteBroadcastDistributionTable(self).encoding
            for entry in self.entries:
#                if ((entry.ip_address != our_ip_address) or (entry.ip_port != our_ip_port)):
                #msg = WriteBroadcastDistributionTable(self).encoding
                if debug > 1:
                    _dump_send(network, entry.asBBMDaddress().address, msg)
                send(network, entry.asBBMDaddress().address, msg)
        pass
    ##
    # get table contents from another BBMD
    def get_bdt_from(self, network, ip_address, ip_port):
        a = _ip_format_str_as_ulong(ip_address)
        p = int(ip_port)
        addr = Addr(_ulong_as_str(a) + _ushort_as_str(p))
        try:
            _module_lock.acquire()
            self.reports = {}
        finally:
            _module_lock.release()
        if debug > 1:
            _dump_send(network, addr.address,
                       ReadBroadcastDistributionTable().encoding)
        send(network, addr.address, ReadBroadcastDistributionTable().encoding)
        timeout = 0
        _module_lock.acquire()
        try:
            while (len(self.reports.values()) < 1) and (timeout < 10):
                _module_lock.release()
                pause(0.5)
                timeout += 1
                _module_lock.acquire()
        finally:
            try:
                _module_lock.release()
            except:
                pass
        _module_lock.acquire()
        try:
            if (len(self.reports.values()) > 0):
                self.entries = self.reports.values()[0]
        finally:
            _module_lock.release()
        return self.report(network)
            
        
        
##
# Entry in the Foreign Device Table (FDT)
# Consists of:
#    Addr object
#       4 octet ip address
#       2 octet ip port
#    2 octet ttl time to live
#    2 octet seconds_remaining
class FDT_Entry:
    ##
    # instantiated in two ways:
    #   use "decode=" to derive from raw binary string:
    # @param raw string containing encoded entry
    #   or use  parameters:
    # @param addr Addr object of ip address
    # @param ttl  Time To Live in seconds
    # @param sec_rem  Seconds remaining
    def __init__(self, addr=None, ttl=None, sec_rem=None, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
            return
        elif addr is None or ttl is None:
            raise TypeError('Requires 2 or 3 args or decode')
        self.encode(addr, ttl, sec_rem)
        return

    def decode(self, buffer):
        if len(buffer) != 10:
            raise ETypeError('BDT entries must be 10 octets long')
        self.encoding          = buffer
        self.addr              = Addr(self.encoding[0:6])
        self.ttl               = _str_as_ushort (self.encoding[6:8])
        self.seconds_remaining = _str_as_ushort  (self.encoding[8:10]) + 30

    def encode(self, addr, ttl, sec_rem=None):
        self.seconds_remaining = sec_rem
        if sec_rem == None:
            self.seconds_remaining = ttl + 30  #30 second grace period
        self.addr = addr
        self.ttl  = ttl
        self.encoding = self.addr.address + \
                        _ushort_as_str (self.ttl)    + \
                        _ushort_as_str (self.seconds_remaining)

    def as_text(self):
        return (_ulong_as_ip_format_str(_str_as_ulong(self.addr.address[0:4])),
                str(_str_as_ushort(self.self.addr.address[4:6])),
                _ushort_as_str(self.ttl),
                _ushort_as_str(self.seconds_remaining))
    
    def tick(self):
        if (self.seconds_remaining > 0):
            self.seconds_remaining -= 1
            if debug > 4:
                print self.seconds_remaining
                print 'FDT tick'
                
        return self.seconds_remaining <= 0
        
##
# The Foreign Device table (FDT)
# 
class ForeignDeviceTable:
    ##
    # Initialize the object.
    #
    def __init__(self, *args, **keywords):
        self.entries = {}
        #self.network = 0  #init with network interface number?
        if keywords.has_key('from_text'):
            self.from_text(keywords['from_text'])
        elif len(args) > 0:
            raise ETypeError('requires no parameters or "from_text="')
        self._start_ticking()

    ##
    # add or renew a foreign device entry in the table
    # j.2.2
    def register_foreign_device(self, RFD_message):
        try:
            answer = Result(0x0000) #default response that everything was ok
            entry = FDT_Entry(RFD_message.foreign_device_address, RFD_message.time_to_live)
            self.entries [RFD_message.foreign_device_address.address] = entry
            if debug > 2:
                print "BBMD Register foreign device"
        except:
            msglog.exception()
            answer = Result(0x0030)
        return answer

    ##
    # return the contents of the FDT
    # j.2.3
    def read_table(self):
        try:
            answer = ReadForeignDeviceTableAck()
            for key in self.entries.keys():
                answer.append(self.entries[key])
        except:
            msglog.exception()
            answer = Result(0x0040)  #NAK
        return answer
    
    ##
    # delete a foreign device from the table
    # j.2.9
    def delete_entry(self, dfdte_message):
        if self.entries.has_key(dfdte_message.foreign_device_address.address):
            del self.entries[dfdte_message.foreign_device_address.address]
            answer = Result(0x0000)
        else:
            answer = Result(0x0050) #nak
        return answer

    ##
    # forward a broadcast message to all Foreign devices
    # j.4.5
    def forward_original_broadcast_message(self, network, addr, original_message_npdu):
        forwarded_message = ForwardedNPDU(addr, original_message_npdu)
        msg = forwarded_message.encoding
        for key in self.entries.keys():
            if debug > 1:
                _dump_send(network, self.entries[key].addr.address, msg)
            send(network, self.entries[key].addr.address, msg)
                    
    ##
    # locally send a forwarded message to a Foreign device
    # j.4.5
    def broadcast_forwarded_message(self, network, forwarded_message):
        msg = forwarded_message.encoding
        for key in self.entries.keys():
            if debug > 1:
                _dump_send(network, self.entries[key].addr.address, msg)
            send(network, self.entries[key].addr.address, msg)
            
    ##
    # distribute a forward message to other foreign devices from a foreign device
    # j.4.5
    def distribute(self, network, addr, forwarded_message):
        msg = forwarded_message.encoding
        for key in self.entries.keys():
            entry = self.entries[key]
            if (entry.addr != addr):
                if debug > 1:
                    _dump_send(network, self.entries[key].addr.address, msg)
                send(network, entry.addr.address, msg)
    ##
    # answer a list of lists with text representations of the table values
    # j.4.5
    def as_text(self):
        answer = []
        for key in self.entries.keys():
            answer.append(self.entries[key].as_text())
        return answer
    ##
    # set the contents of the table from a list of lists
    # j.4.5
    def from_text(self, lists):
        pass
    ##
    # signal that semaphore to run the tock
    def _tick(self):
        self.semaphore.release()
        scheduler.seconds_from_now_do(1.0, self._tick)
        if debug > 4:
            print 'FDT tick'
    ##
    # tick off the remaining time in the table entries
    # runs once a second
    # j.4.5
    def _tock(self):
        while 1:
            try:
                self.semaphore.acquire()
                #scheduler.seconds_from_now_do(1.0, self._tick)
                _module_lock.acquire()
                try:
                    if debug > 4:
                        print 'FDT tock'
                    if (self.entries):
                        for key in self.entries.keys():
                            entry = self.entries[key]
                            if entry.tick():  #time to remove
                                try:
                                    del self.entries[key]
                                    if debug > 4:
                                        print "timeout on foreign device"
                                except:
                                    pass
                finally:
                    _module_lock.release()
            except:
                if msglog:
                    msglog.exception()
                    msglog.log('broadway', msglog.types.INFO,
                       'FDT timer thread restarting\n')
                    pause(10.0)
    ##
    # start the tick thread to decrement FDT entries
    def _start_ticking(self):
        if debug > 4:
            print 'start ticking'
        self.semaphore = Semaphore(0)
        self._scheduler = scheduler
        scheduler.seconds_from_now_do(1.0, self._tick)
        # @fixme Switching to Thread object caused
        #        mpx/lib/bacnet/_test_case_bvlc.py to hang after completing.
        #        Figure out why, and switch over the Thread object.
        threading._start_new_thread(self._tock,())
    def _stop_ticking(self):
        if self._scheduler:
            self._scheduler.enabled = 0

class BBMD_Server:
    ##
    # Initialize the object.
    #
    def __init__(self, interface):
        self.name = 'mpx.lib.bacnet.bvlc.' + str(interface.name)
        self.bdt = BroadcastDistributionTable(interface)  #create the bdt
        self.fdt = ForeignDeviceTable()
        self.our_ip_address = _str_as_ulong(interface.addr.address[0:4])
        self.our_ip_port = _str_as_ushort(interface.addr.address[4:6])
        self.broadcast_address = interface.broadcast
        self.enable = 0
        self.report_bdt = None
        self.register_as_foreign_device=None
    def bbmd_enabled(self, flag=None):
        if flag is not None:
            self.enable = flag
            try:
                self.bdt.node.save_enable_bbmd_flag(flag)
            except: #don't disturb proper response code if failed
                msglog.exception()
        return self.enable

# end of objects
# module procedures follow:

def _service_bbmd_queue( BBMD_queue ):
    #loop forever getting messages from the queue and servicing them
    global _module_lock

    while 1:
        # a tuple of network number, Addr, string
        a_message = BBMD_queue.get()

        #process the incoming message
        answer = None

        network = a_message[0]
        addr = Addr(a_message[1])
        message_string = a_message[2]

        if debug > 1:
            print "BBMD recv: network=",network
            print "BBMD recv: from=",addr
            dump(message_string, "BBMD recv")

        if not BBMD_servers.has_key(network):
            continue

        bbmd = BBMD_servers[network]

        bdt = bbmd.bdt
        fdt = bbmd.fdt

        if ord(message_string[0]) != 0x81:  #not bvlc frame
            # @fixme Just log it and toss the message.
            raise EInvalidValue('frame_type',
                                ord(message_string[0]),
                                text='Not a BVLC frame')
        # extract the 'BVLC Function' octet
        bvlc_function = ord(message_string[1]) 
    
        if   (bvlc_function == 0x0A): #OriginalUnicastNPDU
            if debug > 2:
                print "BBMD rcvd: OriginalUnicastNPDU:",network
        elif (bvlc_function == 0x0B): #OriginalBroadcastNPDU
             if debug > 2:
                 print "BBMD rcvd: OriginalBroadcastNPDU:",network
             if bbmd.enable:
                 obn = OriginalBroadcastNPDU(decode=message_string).npdu
                 if debug > 2:
                     print "BBMD send: ForwardedNPDU network:",network
                     print "BBMD send: for=",addr
                     dump(obn, "BBMD npdu")
                 bdt.forward_original_broadcast_message(network, 
                                                        addr, 
                                                        obn)
                 fdt.forward_original_broadcast_message(network,
                                                        addr,
                                                        obn)
        elif (bvlc_function == 0x00): #Result
            if debug > 2:
                print "BBMD rcvd: Result:",network
            pass
        elif (bvlc_function == 0x01): #WriteBroadcastDistributionTable
            if debug > 2:
                print "BBMD rcvd: WriteBroadcastDistributionTable:",network
            answer = bdt.write_new_table_contents(
                WriteBroadcastDistributionTable(decode=message_string))
        elif (bvlc_function == 0x02): #ReadBroadcastDistributionTable
            if debug > 2:
                print "BBMD rcvd: ReadBroadcastDistributionTable:",network
            answer = bdt.read_table()
        elif (bvlc_function == 0x03): #ReadBroadcastDistributionTableAck
            if debug > 2:
                print "BBMD rcvd: ReadBroadcastDistributionTableAck:",network
            if bbmd.report_bdt:
                bbmd.report_bdt.read_broadcast_distributioan_table_ack(
                    network, 
                    addr, 
                    ReadBroadcastDistributionTableAck(
                    decode=message_string))
        elif (bvlc_function == 0x04): #ForwardedNPDU
            if debug > 2:
                print "BBMD rcvd: ForwardedNPDU network",network
        
            if bbmd.enable:
                fnpdu = ForwardedNPDU(decode=message_string)
                if debug > 2:
                    print "BBMD Broadcast ForwardedNPDU network",network
                    print "BBMD broadcast for=", fnpdu.originating_address
                    dump(fnpdu.npdu, "BBMD npdu")
                bdt.broadcast_forwarded_message(network, fnpdu)
                fdt.broadcast_forwarded_message(network, fnpdu)
        elif (bvlc_function == 0x05): #RegisterForeignDevice
            if debug > 2:
                print "BBMD rcvd: RegisterForeignDevice network",network
            if bbmd.enable:
                answer = fdt.register_foreign_device(
                      RegisterForeignDevice(addr, decode=message_string))
        elif (bvlc_function == 0x06): #ReadForeignDeviceTable
            answer = fdt.read_table()
        elif (bvlc_function == 0x07): #ReadForeignDeviceTableAck
            pass
        elif (bvlc_function == 0x08): #DeleteForeignDeviceTableEntry
            answer = fdt.delete_entry(DeleteForeignDeviceTableEntry(
                decode=message_string))
        elif (bvlc_function == 0x09): #DistributeBroadcastToNetwork
            if debug > 2:
                print "BBMD rcvd: DistributeBroadcastToNetwork network",\
                      network
            if bbmd.enable:
                try:
                    dbtn = DistributeBroadcastToNetwork(
                        decode=message_string)
                    answer = ForwardedNPDU (addr, dbtn.npdu)
                    bdt.distribute(network, addr, answer)
                    fdt.distribute(network, addr, answer)
                    #locally broadcast the forwared npdu
                    addr = Addr(bbmd.broadcast_address)
                except:
                    msglog.exception()
                    answer = Result(0x0060)
        else:
            if debug > 2:
                print "BBMD rcvd: Unknown message"
        if (answer):
            if debug > 1:
                _dump_send(network, addr.address, answer.encoding)
            send(network, addr.address, answer.encoding)

_module_lock = Lock()
BBMD_servers = {}
BBMD_thread_started = 0
The_BBMD_Server = None

class _BBMD_Server(ImmortalThread):
    def __init__(self, queue):
        ImmortalThread.__init__(self, name='BBMD')
        self.queue = queue
        if debug: print 'init BBMD Server '
    def reincarnate(self):
        msglog.log('broadway',msglog.types.INFO,
                    'BBMD restarting\n')
    def run(self):
        if debug: print '_BBMD_Server: run'
        while 1:
            _service_bbmd_queue(self.queue)

##
# The Register As Foreign Device thread
#
#

    

RAFD_thread_started = 0
The_RAFD_thread = None

class _RAFD_Thread(ImmortalThread):
    def __init__(self, refresh_rate=900.0):
        ImmortalThread.__init__(self, name='RAFD')
        if debug: print 'init RAFD Server '
        self.semaphore = Semaphore(0)
        self._scheduler = scheduler
        self.refresh_rate = refresh_rate
        scheduler.seconds_from_now_do(30.0, self._tick)
    def reincarnate(self):
        msglog.log('broadway',msglog.types.INFO,
                    'RAFD restarting\n')
    def run(self):
        if debug: print '_RAFD_Thread: run'
        while 1:
            self._tock()
    def _tick(self):  #also call this start ticking after a stop
        self.semaphore.release()
        scheduler.enabled = 1
        scheduler.seconds_from_now_do(self.refresh_rate, self._tick)
        if debug > 4:
            print 'RAFD tick'
    def _tock(self):
        while 1:
            try:
                self.semaphore.acquire()
                _module_lock.acquire()
                try:
                    if debug > 4:
                        print 'RAFD tock'
                    for k in BBMD_servers.keys():
                        b = BBMD_servers[k]
                        if b.register_as_foreign_device:
                            # send a new RAFD packet to remote BBMD
                            msg = RegisterForeignDevice(None, self.refresh_rate)
                            if debug > 4: print 'RAFD update TTL'
                            b.bdt.distribute(k, None, msg)
                finally:
                    _module_lock.release()
            except:
                if msglog:
                    msglog.exception()
                    msglog.log('broadway', msglog.types.INFO,
                       'RAFD timer thread restarting\n')
                    pause(10.0)
    def _stop_ticking(self):
        if self._scheduler:
            self._scheduler.enabled = 0

##
# The BBMD service thread
#   start_bbmd_service creates empty Broadcast Distribution and Foreign Device
#   tables and starts a thread upon which the BBMD service runs
# @param interface= the IP network interface object or None
# @param initial_table= a list or lists of text strings describing the BDT or None
# The method is invoked for each interface. 
#
def start_bbmd_service (interface=None, initial_table=None, node=None, register_as_foreign_device=None):
    global BBMD_servers
    global BBMD_thread_started, RAFD_thread_started
    global The_BBMD_Server
    try:
        if interface:
            if not BBMD_servers.has_key(interface.network):
                BBMD_servers[interface.network] = BBMD_Server(interface)
                BBMD_servers[interface.network].bdt.node = node
            if initial_table:
                BBMD_servers[interface.network].bdt.from_text(initial_table, node)
            if register_as_foreign_device:
                BBMD_servers[interface.network].register_as_foreign_device=1
            BBMD_servers[interface.network].bbmd_enabled(1)
            #still needs to be enabled, either by bbmd node or external call
    except:
        raise ETypeError('BBMD failed to initialize table')

    if not BBMD_thread_started:
        BBMD_thread_started = 1
        The_BBMD_Server = _BBMD_Server(_recv_queue)
        try:
            if debug: print 'BBMD_Server: about to start'
            The_BBMD_Server.start()
        except:
            raise ETypeError('BBMD thread failed to start')
        #_bbmd_service( queue)  #single threaded test mode
    if register_as_foreign_device:
        if not RAFD_thread_started:
            RAFD_thread_started = 1
            The_RAFD_thread = _RAFD_Thread()
            try:
                The_RAFD_thread.start()
            except:
                raise EInvalidValue('RAFD thread failded to start')

##
#  Get the contents of the bdt for an interface as a list of lists of text
# @param network = the key (name/number) of the desired ip network interface
#
def get_bdt_for(network):
    if BBMD_servers.has_key(network):
        try:
            return BBMD_servers[network].bdt.as_text()
        except:
            raise ETypeError('BDT as text failed')
    return []
##
#   Clear the BBMD_Enable flag which prevents BBMD transmits
#   while leaving the service thread running to support the editor functions
def disable_bbmd (network):
    if BBMD_servers.has_key(network):
        BBMD_servers[network].bbmd_enabled(0)
    
##
#   Set the BBMD_Enable flag which allows the transmission of forwarded packets
def enable_bbmd(network):
    if BBMD_servers.has_key(network):
        BBMD_servers[network].bbmd_enabled(1)

##
# Retrieve the BBMD_enable flag status
# 0 = disabled
# 1 = enabled
# -1 = who the f--k are you talking about
def bbmd_status(network):
    if BBMD_servers.has_key(network):
        return BBMD_servers[network].bbmd_enabled()
    return -1

##
# Retrieve the BBMD table from a device and validate
# @todo protect against simultaneous calls
def get_bdt_from(network, ip_address, ip_port):
    try:
        interface = _network_map[network]
        rp = BroadcastDistributionTable(interface)
        rp.entries = [] #eliminate the default entry of our own address for reporting
        BBMD_servers[network].report_bdt = rp
        answer = BBMD_servers[network].\
                 report_bdt.get_bdt_from(network, ip_address, ip_port)
        BBMD_servers[network].report_bdt = None
    except:
        msglog.exception()
        answer = [('error', 'error', 'error', 'error',)]
    return answer

##
# Write the BBMD tables defined in the list
# @param network _network.map key of network (an integer)
# @param list of lists defining the bbmd table data
def update_bbmds(network, list):
    try:
        if not BBMD_servers[network].register_as_foreign_device: #block us from updating a table
            bdt = BroadcastDistributionTable(_network_map[network])
            bdt.update_bbmds(network, list)
    except:
        msglog.exception()
        raise ETypeError('Update BBMDS failed')
##
# Validate the BBMD tables against the list
# @todo protect against simultaneous calls
def validate_bbmds(network, list):
    try:
        BBMD_servers[network].report_bdt = \
            BroadcastDistributionTable(_network_map[network])
        BBMD_servers[network].report_bdt.from_text(list)
        answer = BBMD_servers[network].report_bdt.report(network)
        BBMD_servers[network].report_bdt = None
    except:
        msglog.exception()
        answer = [('error', 'error', 'error', 'error',)]
    return answer

# helper functions to convert between strings and integers of various lengths
def _str_as_ulong (string): #network order
    return struct.unpack('!L', string)[0]
    
def _str_as_ushort (string): #network order
    return struct.unpack('!H', string)[0]
    
def _ulong_as_str (int): #network order
    if (int >= 0x100000000L):
        raise EInvalidValue('_ulong_as_str', str(int), 'parameter too large')
    return struct.pack('!L', int)

def _ulong_as_ip_format_str (int):
    answer = str((int >> 24) & 0xff) + '.' + \
             str((int >> 16) & 0xff) + '.' + \
             str((int >> 8)  & 0xff) + '.' + \
             str(int & 0xff)
    return answer

def _ip_format_str_as_ulong (string):
    ip_string = string
    answer = 0L
    index = ip_string.find('.')
    i = 0
    while index > 0:
        i += 1
        answer *= 256L
        v = int(ip_string[0:index])
        if v > 255:
            raise ETypeError('ip value greater than 255')
        answer += v
        ip_string = ip_string[index+1:]
        index = ip_string.find('.')
    if i <> 3:
        raise ETypeError('ipstring format bad: %s' % string)
    answer *= 256L
    answer += int(ip_string)
    return answer

def _ushort_as_str (int): #network order
    if (int >= 0x10000):
        raise EInvalidValue('_ulong_as_str', str(int), 'parameter too large')
    return struct.pack('!H', int)

# convert between binary strings in little-endian order and integers of various lengths
def _bvlc_length (bvlc_message):
    return struct.unpack('!H', bvlc_message[2:4])[0]

def _test_case_support(interface):
    BBMD_servers[interface.network] = BBMD_Server(interface)

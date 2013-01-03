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
# http://code.activestate.com/recipes/409689/
import struct
import socket
import sys
import time
import os

datalen = 56
BUFSIZE = 1500

class Packet(object):

    """Creates ICMPv4 and v6 packets.
    
    header
        two-item sequence containing the type and code of the packet,
        respectively.
    version
        Automatically set to version of protocol being used or None if ambiguous.
    data
        Contains data of the packet.  Can only assign a subclass of basestring
        or None.

    packet
        binary representation of packet.
    
    """

    header_table = {
                0 : (0, 4),
                #3 : (15, 4),  Overlap with ICMPv6
                3 : (15, None),
                #4 : (0, 4),  Deprecated by RFC 1812
                5 : (3, 4),
                8 : (0, 4),
                9 : (0, 4),
                10: (0, 4),
                11: (1, 4),
                12: (1, 4),
                13: (0, 4),
                14: (0, 4),
                15: (0, 4),
                16: (0, 4),
                17: (0, 4),
                18: (0, 4),

                1 : (4, 6),
                2 : (0, 6),
                #3 : (2, 6),  Overlap with ICMPv4
                #4 : (2, 6),  Type of 4 in ICMPv4 is deprecated
                4 : (2, None),
                128: (0, 6),
                129: (0, 6),
                130: (0, 6),
                131: (0, 6),
                132: (0, 6),
                133: (0, 6),
                134: (0, 6),
                135: (0, 6),
                136: (0, 6),
                137: (0, 6),
             }

    def _setheader(self, header):
        """Set type, code, and version for the packet."""
        if len(header) != 2:
            raise ValueError("header data must be in a two-item sequence")
        type_, code = header
        try:
            max_range, version = self.header_table[type_]
        except KeyError:
            raise ValueError("%s is not a valid type argument" % type_)
        else:
            if code > max_range:
                raise ValueError("%s is not a valid code value for type %s" %\
                                     (type_, code))
            self._type, self._code, self._version = type_, code, version

    header = property(lambda self: (self._type, self._code), _setheader,
                       doc="type and code of packet")

    version = property(lambda self: self._version,
                        doc="Protocol version packet is using or None if "
                            "ambiguous")

    def _setdata(self, data):
        """Setter for self.data; will only accept a basestring or None type."""
        if not isinstance(data, basestring) and not isinstance(data, type(None)):
            raise TypeError("value must be a subclass of basestring or None, "
                            "not %s" % type(data))
        self._data = data

    data = property(lambda self: self._data, _setdata,
                    doc="data contained within the packet")

    def __init__(self, header=(None, None), data=None):
        """Set instance attributes if given."""
        #XXX: Consider using __slots__
        # self._version initialized by setting self.header
        self.header = header
        self.data = data

    def __repr__(self):
        return "<ICMPv%s packet: type = %s, code = %s, data length = %s>" % \
                (self.version, self.type, self.code, len(self.data))

    def create(self):
        """Return a packet."""
        # Kept as a separate method instead of rolling into 'packet' property so
        # as to allow passing method around without having to define a lambda
        # method.
        args = [self.header[0], self.header[1], 0]
        pack_format = "!BBH"
        if self.data:
            pack_format += "%ss" % len(self.data)
            args.append(self.data)
        # ICMPv6 has the IP stack calculate the checksum
        # For ambiguous cases, just go ahead and calculate it just in case
        if self.version == 4 or not self.version:
            args[2] = self._checksum(struct.pack(pack_format, *args))
        return struct.pack(pack_format, *args)

    packet = property(create,
                       doc="Complete ICMP packet")

    def _checksum(self, checksum_packet):
        """Calculate checksum"""
        byte_count = len(checksum_packet)
        #XXX: Think there is an error here about odd number of bytes
        if byte_count % 2:
            odd_byte = ord(checksum_packet[-1])
            checksum_packet = checksum_packet[:-1]
        else:
            odd_byte = 0
        two_byte_chunks = struct.unpack("!%sH" % (len(checksum_packet)/2),
                                        checksum_packet)
        total = 0
        for two_bytes in two_byte_chunks:
            total += two_bytes
        else:
            total += odd_byte
        total = (total >> 16) + (total & 0xFFFF)
        total += total >> 16
        return (~total) & 0xffff
        
    def parse(cls, packet):
        """Parse ICMP packet and return an instance of Packet"""
        string_len = len(packet) - 4 # Ignore IP header
        pack_format = "!BBH"
        if string_len:
            pack_format += "%ss" % string_len
        unpacked_packet = struct.unpack(pack_format, packet)
        type, code, checksum = unpacked_packet[:3]
        try:
            data = unpacked_packet[3]
        except IndexError:
            data = None
        return cls((type, code), data)

    parse = classmethod(parse)

def ping(addr, count=1, delay=1, timeout=1, verbose=False):
    if verbose:
        print "PING (%s): %d data bytes" % (addr,datalen)
    process_id = os.getpid()
    base_packet = Packet((8,0))
    rcvd = 0
    for seq_num in range(1, count+1):
    ## create ping packet - seq_num also used for sent count
        s = socket.socket(
            socket.AF_INET,
            socket.SOCK_RAW,
            socket.getprotobyname('icmp')
        )
        s.settimeout(timeout)
        try:
            s.connect((addr, 22))
            pdata = struct.pack("!HHd",process_id,seq_num,time.time())
            ## send initial packet 
            base_packet.data = pdata
            s.send(base_packet.packet)
            ## recv packet
            buf = s.recv(BUFSIZE)
            current_time = time.time()

            ## parse packet; remove IP header first
            r = Packet.parse(buf[20:])
        except:
            if verbose:
                print "ping %s: failure" % addr
            time.sleep(delay)
            continue
        ## parse ping data
        (ident,seq,timestamp) = struct.unpack("!HHd",r.data)

        ## calculate rounttrip time
        rtt =  current_time - timestamp
        rtt *= 1000
        rcvd += 1
        if verbose:
            print "ping %d bytes from %s: id=%s, seq=%u, rtt=%.3f ms" % \
                (len(buf),addr, ident, seq, rtt)
        time.sleep(delay)
    # return approx. percentage success.
    return int((float(rcvd) / seq_num) * 100)
    
if __name__=='__main__':
    import sys
    ping(sys.argv[1])
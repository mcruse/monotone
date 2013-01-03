"""
Copyright (C) 2008 2011 Cisco Systems

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
from __future__ import absolute_import

from time import time as _time
from time import mktime as _mktime
from string import split as _split
from random import randint as _randint
from re import compile as _compile

from mpx.lib.threading import Lock as _Lock

##
# Implement a ISO/IEC 11578:1996(E), Annex A compliant UUID as an immutable
# object.
#
class ISO_11578_UUID(object):
    # Strict regular expression to parse a string containing a human readable
    # UUID.
    _RE_ISO_11578_UUID = _compile("^(" + "[0-9a-zA-Z]"*8 + ")"
                                  "-(" + "[0-9a-zA-Z]"*4 + ")"
                                  "-(" + "[0-9a-zA-Z]"*4 + ")"
                                  "-(" + "[0-9a-zA-Z]"*4 + ")"
                                  "-(" + "[0-9a-zA-Z]"*12 + ")$")
    __lock = _Lock()
    # 
    # @todo Implement persistent storage via PDO and load from PDO iff the
    #       node (stored in the PDO) is unchanged.
    __lock.acquire()
    __global_clock_sequence = _randint(0,0x3FFF)
    __last_timestamp = _time()
    __lock.release()
    ##
    # @return A long integer that represents the number of seconds between
    #         October 15th, 1582 and January 1st, 1970.  Used to convert a UNIX
    #         based time reference to one relative to the UUID 'epoch'.
    # @fixme This is a only 'ballpark' number...
    def _calculate_gregorian_offset():
        local_epoch = _mktime((1970, 1, 1, 0, 0, 0, 0, 0, 0))
        local_epoch_anniversary = _mktime((1971, 1, 1, 0, 0, 0, 0, 0, 0))
        local_october_15th = _mktime((1970, 10, 15, 0, 0, 0, 0, 0, 0))
        seconds_per_year = local_epoch_anniversary - local_epoch
        return ((long(1970 - 1582) * long(seconds_per_year)) +
                long(local_october_15th))
    ##
    # A long integer that represents the number of seconds between
    # October 15th, 1582 and January 1st, 1970.  Used to convert a UNIX
    # based time reference to one relative to the UUID 'epoch'.
    #
    # @fixme This is a only 'ballpark' number...
    _GREGORIAN_OFFSET = _calculate_gregorian_offset()
    _calculate_gregorian_offset = staticmethod(_calculate_gregorian_offset)
    ##
    # Convert the number of seconds since January 1st, 1970 UTC to the
    # number of 100 ns periods since October 15th, 1582 UTC.
    # @param unix_timestamp A Python float representing the number of seconds
    #                       since January 1st, 1970 UTC.
    # @return A Python long representing the number of 100 ns periods since
    #         October 15th, 1582 UTC.
    def _uuid_timereference(unix_timestamp):
        # Adjust the integer and fractional parts individually to
        # increase the accuracy of the conversion.
        uuid_timereference = (long(unix_timestamp) +
                              ISO_11578_UUID._GREGORIAN_OFFSET)
        uuid_timereference *= 10**7 # Convert the time quantum from 1 second
                                    # to 100-ns
        # Add in the fractional part of the timestamp.
        fraction_of_a_second = unix_timestamp - int(unix_timestamp)
        fraction_of_a_second *= 10**7
        uuid_timereference += long(fraction_of_a_second)
        return uuid_timereference
    _uuid_timereference = staticmethod(_uuid_timereference)
    ##
    # Convert number of 100 ns periods since October 15th, 1582 UTC to the
    # number of seconds since January 1st, 1970 UTC.
    # @param uuid_timestamp A Python long representing the number of 100 ns
    #                       periods since October 15th, 1582 UTC.
    # @return A Python float representing the number of seconds since
    #         January 1st, 1970 UTC.
    def _unix_timereference(uuid_timestamp):
        unix_timestamp = uuid_timestamp
        unix_timestamp -= (ISO_11578_UUID._GREGORIAN_OFFSET * 10**7)
        unix_timestamp = float(unix_timestamp)
        unix_timestamp /= 10**7 # Convert the time quantum from 100 ns
                                # to 1 second
        return unix_timestamp
    _unix_timereference = staticmethod(_unix_timereference)
    ##
    # Manage the "persistent" Clock Sequence, accounting for clock changes.
    #
    # @param unix_timestamp A Python float representing the number of seconds
    #                       since January 1st, 1970 UTC.
    # @return The 16-bit clock-sequence appropriate for the generation
    #         of a new UUID.
    def _clock_sequence(klass, unix_timestamp):
        result = None
        klass.__lock.acquire()
        try:
            if unix_timestamp <= klass.__last_timestamp:
                klass.__global_clock_sequence = (
                    klass.__global_clock_sequence + 1) & 0x3FFF
            klass.__last_timestamp = unix_timestamp
            result = klass.__global_clock_sequence
        finally:
            klass.__lock.release()
        return result
    _clock_sequence = classmethod(_clock_sequence)
    ##
    # Initialize the time components of this UUID:
    #     time_low
    #     time_mid
    #     time_high_and_reserved.
    # @param unix_timestamp A Python float representing the number of seconds
    #                       since January 1st, 1970 UTC.
    def __init_time(self, unix_timestamp):
        uuid_timestamp = self._uuid_timereference(unix_timestamp)
        self.__time_low = uuid_timestamp & 0xFFFFFFFFL
        self.__time_mid = (uuid_timestamp >> 32) & 0xFFFFL
        self.__time_high_and_version = (uuid_timestamp >> 48)
        self.__time_high_and_version |= 0x1000 # Version 1.
        return
    ##
    # Initialize the clock_sequence components of this UUID:
    #     clock_seq_low
    #     clock_seq_high_and_reserved.
    # @param unix_timestamp A Python float representing the number of seconds
    #                       since January 1st, 1970 UTC.
    def __init_clock_seq(self, unix_timestamp):
        clock_seq = self._clock_sequence(unix_timestamp)
        # Encode clock_seq_low and the low 12 bits of
        # clock_seq_high_and_reserved.
        self.__clock_seq = clock_seq
        # Encode 'reserved' bits of clock_seq_high_and_reserved.
        self.__clock_seq |= 0x8000
        return
    ##
    # Initialize the node component of this UUID.
    def __init_node(self):
        # The fallback node algoruthms are not ISO 11578:1996(E) compliant
        # since only the MAC address is (almost) guaranteed to be unique in the
        # global namespace.
        self.__node = _get_node_from_mac()
        return
    ##
    # Initialize the node component of this UUID.
    def __new(self):
        unix_timestamp = _time()
        self.__init_time(unix_timestamp)
        self.__init_clock_seq(unix_timestamp)
        self.__init_node()
        return
    def __load(self, uuid):
        components = self._RE_ISO_11578_UUID.match(uuid)
        if components is None:
            raise ValueError('Not a valid ISO 11578:1996(E) UUID.')
        components = components.groups()
        self.__time_low = long(components[0],16)
        self.__time_mid = long(components[1],16)
        self.__time_high_and_version = long(components[2],16)
        self.__clock_seq = long(components[3],16)
        self.__node = long(components[4],16)
        return
    ##
    # Instantiate a new, ISO 11578:1996(E) compatible UUID.
    #
    # @param uuid An ISO_11578_UUID instance, or a string representing the UUID
    #             in the ISO 11578:1996(E) human readable format.
    # @default None If no uuid parameter is provided, then a unique UUID is
    #               instantiated.
    def __init__(self, uuid=None):
        self.__str = None
        self.__time_low = None
        self.__time_mid = None
        self.__time_high_and_version = None
        self.__clock_seq = None
        self.__node = None
        if uuid is None:
            self.__new()
        else:
            self.__load(str(uuid))
        return
    def __str__(self):
        if self.__str is None:
            self.__str = "%08x-%04x-%04x-%04x-%012x" % (
                self.__time_low,
                self.__time_mid,
                self.__time_high_and_version,
                self.__clock_seq,
                self.__node)
        return self.__str
    def __repr__(self):
        return "%r" % str(self)
    ##
    # @return The 128 bit, Python long integer representation of this UUID.
    def __long__(self):
        return ((long(self.__time_low << 96)) |
                (long(self.__time_mid << 80)) |
                (long(self.__time_high_and_version)) << 64 |
                (long(self.__clock_seq) << 48) |
                (long(self.__node)))
    def __cmp__(self, o):
        # Compare like a string so UUIDs and strings can be mixed and matched
        # in the same dictionary.
        return cmp(str(self), o)
    def __hash__(self):
        # Hash like a string so UUIDs and strings can be mixed and matched
        # in the same dictionary.
        # @warning It is important that UUID instances are immutable, otherwise
        #          using them as keys in dictionaries will break.
        return hash(str(self))

##
# Factory for generalized UUIDs.  This factory exists to dynamically support
# loading of multiple UUID types.
#
# @param uuid An instance of a UUID or a string representing the UUID in the
#             human readable format.
# @default None If no uuid parameter is provided, then a unique,
#               ISO 11578:1996(E) compliant UUID is instantiated.
#
# @todo Support loading UUIDs from human readable text complying to the
#       current NodeDef implementation as well.
def UUID(uuid=None):
    uuid = ISO_11578_UUID(uuid)
    return uuid

#
# Establish the best available mechanism to calculate the ISO NODE.  This may
# look like scary magic, but it is actually fairly straight forward.  As the
# module is loaded, it attempts to use each possible mechanism for calculating
# ISO NODE.  The methods are tried in order of preference, worst to best.
# Each mechanism that succeeds replaces the fall-back implementation.  The
# best, successful mechanism wins.

def _get_node():
    raise """\
Internal error, helper function should have been overloaded when the module
loaded."""

def _get_node_from_mac():
    return _node_from_mac

def _get_node_from_ip():
    return _node_from_ip

def _get_node_from_random():
    return _node_from_random

def _get_node_from_instance():
    return _node_from_instance

def _validate_node(a):
    if a < 0L:
        raise ValueError("a must be > 0L.")
    if a > 0xFFFFFFFFFFFFL:
        raise ValueError("a must be < FFFFFFFFFFFFL.")
    return

#
# Attempt to determine ISO NODE by using the Python instance of the
# ISO_11578_UUID class shifted left 16 bits and adding in the current process
# id.
#
_node_from_instance = None
try:
    from os import getpid as _getpid
    _node_from_instance = (long(id(ISO_11578_UUID)) << 16) + _getpid()
    _validate_node(_get_node_from_instance())
    _get_node = _get_node_from_instance
except:
    pass

#
# Attempt to determine ISO NODE by using the current machine's IP address
# class shifted left and adding in the current process id, depending on the
# size of the IP address (IPv4 vs. IPv6).
#
_node_from_ip = None
try:
    from ..ifconfig import ip_address as _ip_address
    for adapter_num in range(0, 10): 
        adapter = 'eth%u' % adapter_num 
        _node_from_ip = _ip_address(adapter)
except:
    _node_from_ip = None

if _node_from_ip is None:
    # mpx.lib.ifconfig.ip_address address failed, try a pure Python
    # mechanism.
    try:
        import socket as _socket
        _node_from_ip = _socket.gethostbyname(_socket.gethostname())
    except:
        _node_from_ip = None

if _node_from_ip is not None:
    try:
        _node_from_ip=map(long, _split(_node_from_ip,'.'))
        if len(_node_from_ip) < 4:
            raise "Internal error: IP address is less than 4 octets."
        # If using IPv4 the address will only be 4 octets.
        if len(_node_from_ip) == 4:
            from os import getpid as _getpid
            _node_from_ip.append((_getpid() >> 8) & 0xff)
            _node_from_ip.append(_getpid() & 0xff)
        # If IPv6 than the address could be less than 6 octets.
        if len(_node_from_ip) == 5:
            _node_from_ip.append(_getpid() & 0xff)
        # If using IPv6, the address could be longer than 6 octets.
        while len(_node_from_ip) > 6:
            _node_from_ip.pop()
        _node_from_ip=reduce(lambda x,y: (x<<8)+y, _node_from_ip, 0L)
        _validate_node(_get_node_from_ip())
        _get_node = _get_node_from_ip
    except:
        pass

#
# Attempt to determine ISO NODE by using the current machine's MAC address.
#
_node_from_mac = None
for adapter_num in range(0, 10): 
    adapter = 'eth%u' % adapter_num 
    try:
        from ..ifconfig import mac_address as _mac_address
        _node_from_mac = _mac_address(adapter)
        _node_from_mac=map(lambda x: long(x,16), _split(_node_from_mac,':'))
        _node_from_mac=reduce(lambda x,y: (x<<8)+y, _node_from_mac, 0L)
        _validate_node(_get_node_from_mac())
        _get_node = _get_node_from_mac
        break
    except:
        _node_from_mac = None

"""
Copyright (C) 2002 2007 2010 2011 Cisco Systems

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
# Functions relating to the configuration of IP interfaces.

from fcntl import ioctl
from struct import pack, unpack
from socket import socket, AF_INET, SOCK_DGRAM

try:
    IOCTL = None
    try:
        import IOCTL
        SIOCGIFADDR = IOCTL.SIOCGIFADDR
        SIOCGIFHWADDR = IOCTL.SIOCGIFHWADDR
        SIOCGIFNETMASK = IOCTL.SIOCGIFNETMASK
    except:
        import IN
        if (hasattr(IN,'SIOCGIFADDR') and
            hasattr(IN,'SIOCGIFHWADDR') and
            hasattr(IN,'SIOCGIFNETMASK')):
            SIOCGIFADDR = IN.SIOCGIFADDR
            SIOCGIFHWADDR = IN.SIOCGIFHWADDR
            SIOCGIFNETMASK = IN.SIOCGIFNETMASK
        else:
            SIOCGIFADDR = 35093
            SIOCGIFHWADDR = 35111
            SIOCGIFNETMASK = 35099
        del IN
finally:
    del IOCTL

##
# Return the IP address for an interface.
# @param interface A string representing the name of the interface.
# @value all 0.0.0.0
# @value lo The loopback device.
# @value eth0-eth255 An ethernet adapter.
# @value ppp0-ppp255 A PPP connection.
# @return A string representation of the interface's IP address.
def ip_address(interface):
    if interface == 'all':
        return '0.0.0.0'
    s = socket(AF_INET, SOCK_DGRAM)
    ifreq = pack('16s16s', interface, '')
    ifreq = ioctl(s.fileno(), SIOCGIFADDR, ifreq)
    addr = unpack('20x4B8x', ifreq)
    s.close()
    return '%d.%d.%d.%d' % addr

##
# Return the MAC address for an interface.
# @param interface A string representing the name of the interface.
# @value eth0-eth255 An ethernet adapter.
# @return A string representation of the interface's MAC address.
# @note Some interfaces (e.g. ppp0) don't have MAC addresses.
def mac_address(interface):
    s = socket(AF_INET, SOCK_DGRAM)
    ifreq = pack('16s16s', interface, '')
    ifreq = ioctl(s.fileno(), SIOCGIFHWADDR, ifreq)
    mac = unpack('18x6B8x', ifreq)
    s.close()
    return '%2.2x:%2.2x:%2.2x:%2.2x:%2.2x:%2.2x' % mac

##
# Return the IP netmask for an interface.
# @param interface A string representing the name of the interface.
# @value lo The loopback device.
# @value eth0-eth255 An ethernet adapter.
# @value ppp0-ppp255 A PPP connection.
# @return A string representation of the interface's IP address.
def ip_netmask(interface):
    s = socket(AF_INET, SOCK_DGRAM)
    ifreq = pack('16s16s', interface, '')
    ifreq = ioctl(s.fileno(), SIOCGIFNETMASK, ifreq)
    addr = unpack('20x4B8x', ifreq)
    s.close()
    return '%d.%d.%d.%d' % addr

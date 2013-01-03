"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
# Refactor 2/11/2007
import weakref
import socket
import os,struct
import interfaces
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.componentry import implements
from mpx.lib.ifconfig import ip_address
from mpx.lib.msglog.types import WARN

class utils:
    @staticmethod
    def get_default_ifname():
        ifname = 'eth0'
        fd = os.popen('/sbin/route -n')
        for line in fd.readlines()[2:]: #skip headers
            dest, gw, gm, flags, metric, ref, use, iface = line.split()
            if dest == '0.0.0.0':
                # entry with default route
                ifname = iface
                break
        fd.close()
        return ifname

    @staticmethod    
    def compute_my_ip_addr():
        my_ip='127.0.0.1'
        interface=utils.get_default_ifname()
        try:
            my_ip=ip_address(interface)
        except IOError, (errno, strerror):
                msglog.log('broadway', WARN, 'No ip address configured on this interface %s: Error %d: %s' % (interface, errno, strerror))
                msglog.log('broadway', msglog.types.INFO, 'Use "route add default <interface>" command to configure connected interface!')
        msglog.log('CloudManager',msglog.types.INFO,'Event Management Services are available on %s Interface, on IP=%s' %(interface,my_ip))
        return(my_ip)

class Event(object):    
    implements(interfaces.IEvent)
    EVENTS = weakref.WeakValueDictionary()
    LOCALORIGIN = utils.compute_my_ip_addr()

    def get_event(guid):
        try: return Event.EVENTS[guid]
        except KeyError: raise KeyError('Event "%s" does not exist.' % guid)
    get_event = staticmethod(get_event)

    def __init__(self, source, origin=None, guid=None):
        self.source = source
        if origin is None:
            origin = getattr(source, 'origin', self.LOCALORIGIN)
        self.origin = origin
        self.__GUID = UUID(guid)
        # setdefault is atomic...
        assigned = self.EVENTS.setdefault(self.GUID, self)
        if assigned is not self:
            raise ValueError('GUID %s already exists.' % self.GUID)
        super(Event, self).__init__(source, origin, guid)
    def get_guid(self):
        return str(self.__GUID)
    GUID = property(get_guid)
    def is_local(self):
        return self.origin == self.LOCALORIGIN
    def set_local(self):
        """
            Notify event that it is a local event, causing 
            it's 'origin' to be set to the current local origin.
            
            Used when persisted local events are restored from 
            storage to update restored event to reflect IP address 
            changes. 
        """
        self.origin = self.LOCALORIGIN
    def __str__(self):
        return '%s(%s) from %s.' % (type(self).__name__, self.GUID, self.origin)

import adapters

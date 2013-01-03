"""
Copyright (C) 2003 2011 Cisco Systems

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
# File Input / Output for Tracer internal files.
#

from mpx.lib.exceptions import *
from mpx.lib.tcs import frame, command, response
from mpx.lib import msglog
from mpx.lib.threading import Lock

debug = 0
MAX_ATTEMPTS = 5

_module_lock = Lock()

class TCSDevice:
    def __init__(self, number, lh):
        self.number = number
        self.type = None
        self.version = None
        self._master_schedule_file = None
        self.lh = lh

    def _get_type(self, retries=3):
        if debug: print '_get_type'
        a = self.lh.send_request_with_response(command.GetType(), self.number, retries)

        if a.__class__ in (response.GetTypeReply,):
            self.type = a.type()
            #self.version = a.version()
        else:
            if debug: print 'Unexpected Response to GetTypeAndValue', str(a) 
            raise EInvalidResponse('Unexpected Response to GetTypeAndValue', str(a))
        return self.type
    def get_type(self, retries=3):
        if debug: 'get_type'
        if self.type != None:
            return self.type
        self._get_type(retries)
        return self.type
    
    def _get_version(self, retries=3):
        if debug: print '_get_type'
        a = self.lh.send_request_with_response(command.GetVersion(), self.number, retries)

        if a.__class__ in (response.GetVersionReply,):
            self.version = a.version()
        else:
            if debug: print 'Unexpected Response to GetTypeAndValue', str(a) 
            raise EInvalidResponse('Unexpected Response to GetTypeAndValue', str(a))
        return self.version
    
    def get_version(self, retries=3):
        if debug: 'get_version'
        if self.version != None:
            return self.version
        self._get_version(retries)
        return self.version

    def get_point_map(self):
        self.point_map = {}
        pass
    def get_point(self, key):
        if self.point_map is None:
            self.get_point_map()
        if self.point_map.has_key(key):
            return self.point_map[key].get()
        return 'unknown point :'+str(key)

    def set_point(self, key, value):
        if self.point_map is None:
            self.get_point_map()
        if self.point_map.has_key(key):
            self.point_map[key].set(value)


def _test():
    from mpx.ion.host.port import factory
    p = factory()
    #configure a mpx2400 com1 port
    p.configure({'name':'port1', 'debug':1, 'flow_control':0, 'baud':9600, 'stop_bits':1, 'parent':None, 'dev':'/dev/ttyS4'})
    p.open()
    d = TCSDevice(248, p)
    print str(d)
    print str(d.get_type())

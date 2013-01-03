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
# Implementation of the NBM-2400 / NBM-4800 (aka RZ Mediator 2500.)

__all__ = ['factory']
from host import Host

class Geode(Host):
    _coprocessor_factory_path = 'mpx.ion.host.avr'  # controls the magic child swap
    def configure(self, config):
        if not self.port_map:
            config['ncounters'] = 4
            config['nDIs'] = 4
            config['nrelays'] = 2
            config['ndallas_busses'] = 4
            config['nGPIOs'] = 1
            config['port_map'] = {'console':'/dev/ttyS0',
                                  'com1':'/dev/ttyS8',
                                  'com2':'/dev/ttyS9',
                                  'com3':'/dev/ttySa',
                                  'com4':'/dev/ttySb',
                                  'com5':'/dev/ttySc',
                                  'com6':'/dev/ttySd'}
            config['eth_map'] = {'eth0':'eth0',
                                 'eth1':'eth1'}
            config['modem_map'] = {}
        Host.configure(self, config)

_host_singleton = None
##
# Instanciate a host object and configure it like an NBM-2400 / NBM-4800.
def factory():
    global _host_singleton
    if _host_singleton == None:
        _host_singleton = Geode()
    return _host_singleton

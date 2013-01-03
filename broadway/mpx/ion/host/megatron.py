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
# Implementation of the Mediator5000 (NBM-2500, NBM-5000).
# see geode.py for the mediator coprocessor related points
#
# Mediator5000 inherits from Host.  Stay with me, now...   
# Host steals all its children from from arm.py
# (specified in _coprocessor_factor_path) so this Mediator5000 class
# ends up with all the arm.py children (AIs, AOs, BIs, etc)
# AND they end up as children of /Interfaces.
# If that seems a little complicated.... it is.
# 

from host import Host

#print 'import megatron.py'

class Mediator5000(Host):
    _coprocessor_factory_path = 'mpx.ion.host.arm'  # controls the magic child swap
    def configure(self, config):
        #print 'configure megatron'
        if not self.port_map:
            config['ncounters'] = 4
            config['nAIs'] = 4
            config['nAOs'] = 3
            config['nDIs'] = 4
            config['nrelays'] = 2
            config['ndallas_busses'] = 2
            config['nCAN_busses'] = 1
            config['nGPIOs'] = 0
            config['port_map'] = {'console':'/dev/ttyS0',
                                  'com1':'/dev/ttyS2',
                                  'com2':'/dev/ttyS3',
                                  'com3':'/dev/ttyS4',
                                  'com4':'/dev/ttyS5',
                                  'com5':'/dev/ttyS6',
                                  'com6':'/dev/ttyS7'}
            config['eth_map'] = {'eth0':'eth0',
                                 'eth1':'eth1'}
        Host.configure(self, config)

_host_singleton = None
##
# Instanciate a host object and configure it like an Mediator 2400.
def factory():
    global _host_singleton
    if _host_singleton == None:
        _host_singleton = Mediator5000()
    return _host_singleton


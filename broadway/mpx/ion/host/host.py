"""
Copyright (C) 2001 2002 2003 2004 2010 2011 Cisco Systems

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
# Implementation of a generic host ION in the MPX framework.

__all__ = ['Host', 'factory']

import os
import ConfigParser

from mpx import properties

from mpx.lib import factory as _factory
from mpx.lib.node import CompositeNode
from mpx.lib.node import PublicInterface
from mpx.lib.configure import REQUIRED, set_attribute, set_attributes
from mpx.lib.configure import get_attribute
from mpx.lib.exceptions import EFileNotFound

from mpx.lib import msglog
from mpx.lib.msglog.types import INFO

##
# HOST for IO.
#
# @note Grabs all children of coprocessor and makes
#       them children of itself, hiding the coprocessor node.
class Host(CompositeNode,PublicInterface):
    _port_factory_path = 'mpx.ion.host.port'
    _internal_modem_factory_path = 'mpx.ion.host.modem.InternalModem'
    _eth_factory_path = 'mpx.ion.host.eth'
    def __init__(self):
        CompositeNode.__init__(self)
        self.coprocessor = None
        self.port_map = None
        self.eth_map = None
        self.modem_map = None
        return
    def cleanup_modem_configuration(self):
        if not self.modem_map :
            cf=properties.MPXINIT_CONF_FILE
            if not os.access(cf, os.F_OK):
                return
            if os.access(cf, os.R_OK|os.W_OK):
                f=open(cf, 'r')
                cp = ConfigParser.ConfigParser()
                cp.readfp(f)
                f.close()
            else:
                if not os.access(cf, os.R_OK):
                    raise EPermission(reason = 'Cannot read file %s' %  cf)
                elif not os.access(cf, os.W_OK):
                    raise EPermission(reason = 'Cannot write file %s' % cf)
            write_file = False
            if cp.has_section('dialin'):
                cp.remove_section('dialin')
                write_file = True
            if cp.has_section('dialout'):
                cp.remove_section('dialout')
                write_file = True
            if write_file == True:
                f=open(properties.MPXINIT_CONF_FILE, 'w')
                cp.write(f)
                f.close()
                msglog.log('broadway', INFO, 'Writting Modem info to mpxinit conf.')
            else:
                msglog.log('broadway', INFO, 'Not Writting modem info to mpxinit conf.')

    def start(self):
        CompositeNode.start(self)
        self.cleanup_modem_configuration()
        return
    ##
    # Configure object.
    #
    # @key ncounters  The number of counters on the coprocessor.
    # @default 0
    # @key nAIs  The number of analog inputs on the coprocessor.
    # @default 0
    # @key nAOs  The number of analog outputs on the coprocessor.
    # @default 0
    # @key nDIs  The number of digital inputs on the coprocessor.
    # @default 0
    # @key nrelays  The number of relays on the coprocessor.
    # @default 0
    # @key ndallas_busses  The number of dallas busses on the coprocessor.
    # @default 0
    # @key port_map  Dictionary mapping port names to physical ports.
    # @default None
    # @fixme Dynamically stub coprocessor children, move actual coprocessor
    #        initialization to start().
    def configure(self, dict):
        #print 'Start Host configure'
        CompositeNode.configure(self, dict)
        set_attribute(self, 'ncounters', 0, dict, int)
        set_attribute(self, 'nAIs', 0, dict, int)
        set_attribute(self, 'nAOs', 0, dict, int)
        set_attribute(self, 'nDIs', 0, dict, int)
        set_attribute(self, 'nrelays', 0, dict, int)
        set_attribute(self, 'ndallas_busses', 0, dict, int)
        set_attribute(self, 'nGPIOs', 0, dict, int)
        set_attribute(self, 'has_coprocessor',
                      self.ncounters or self.nDIs or
                      self.nrelays or self.ndallas_busses or self.nGPIOs or
                      self.nAIs or self.nAOs,
                      dict, int)
        # Attach the coprocessor and configure it.
        if self.has_coprocessor and not self.coprocessor:
            config = {}
            config['name'] = 'coprocessor'
            config['parent'] = self
            config['ncounters'] = self.ncounters
            config['nAIs'] = self.nAIs
            config['nAOs'] = self.nAOs
            config['nDIs'] = self.nDIs
            config['nrelays'] = self.nrelays
            config['ndallas_busses'] = self.ndallas_busses
            config['nGPIOs'] = self.nGPIOs
            self.coprocessor = _factory(self._coprocessor_factory_path)
            self.coprocessor.configure(config)

            # Move the coprocessor's IONs directly to the host.
            for node in self.coprocessor.children_nodes():
                node.parent = self
                self._add_child(node)

            # "Hide" the coprocessor ion.
            del self._children[self.coprocessor.name]
            #print 'coprocessor configure done'

        if self.port_map is None:
            print ' Attach and configure the serial ports.'

            # Attach and configure the serial ports.
            set_attribute(self, 'port_map', None, dict)
            if self.port_map:
                for name, dev in self.port_map.items():
                    port = _factory(self._port_factory_path)
                    config = {}
                    config['dev'] = dev
                    config['name'] = name
                    config['parent'] = self
                    port.configure(config)
                    del port
        if self.modem_map is None:
            # Attach and configure the serial modems.
            set_attribute(self, 'modem_map', None, dict)
            if self.modem_map:
                for name, dev in self.modem_map.items():
                    modem = _factory(self._internal_modem_factory_path)
                    config = {}
                    config['dev'] = dev
                    config['name'] = name
                    config['parent'] = self
                    modem.configure(config)
                    del modem
        if not self.eth_map:
           # Attach and configure the ethernet ports.
           set_attribute(self, 'eth_map', None, dict)
           if self.eth_map:
               for name, dev in self.eth_map.items():
                   eth = _factory(self._eth_factory_path)
                   config = {}
                   config['dev'] = dev
                   config['name'] = name
                   config['parent'] = self
                   eth.configure(config)
                   del eth

##
# Instanciate a host object for which the user can configure the I/O.
class Unknown(Host):
    def configure(self,config):
        if not self.port_map:
            if not config.has_key('port_map'):
                config['port_map'] = {}
            if not config.has_key('eth0_map'):
                # @fixme At some point this should be optional as well and
                #        host should be exposed as UserDefinable(Host).
                config['eth_map'] = {'eth0':'eth0'}
        Host.configure(self,config)
        return

##
# Instanciate a generic host object.
def factory():
    return Host()

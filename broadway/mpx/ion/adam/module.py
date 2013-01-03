"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
# @todo  Integrate the configuration methods.  (autocreate child IONs from
# configuration information?)
# @todo  Rename line_handler attribute to parent (see iod.py's TODO #6)?
# @todo  Work out the update_configuration stuff.

import string
from mpx.lib.node import CompositeNode
from mpx.lib.configure import REQUIRED, set_attribute
from bitopt import bitopt
from definitions import *

def hexb(value):
    return string.zfill(string.upper(hex(value)[2:]),2)

def chop(buf):
    return buf[3:len(buf)]

def getbits(val):
    b = ()
    for i in range (0,8):
        if (val&0x80):
            b = (1,) + b
        else:
            b = (0,) + b
        val = val << 1
    return b

def retval(val):
    return val

class FuncOpt:
    def __init__(self,name,func):
        self.name = name
        self.func = func
        self.default = 0

    def get(self,val):
        return self.func(val)

    def set(self,config,val):
        return config[self.name]

class Module(CompositeNode):
    # Mapping Module configuration to the ADAM configuration system.
    change_checksum = 'checksum status'
    change_address = 'new address'
    change_baud = 'baud'

    def __init__(self):
        self.checksum = bitopt(self.change_checksum,0x40,6,'disabled',
                               {0:'disabled',
                                1:'enabled'})
        self.addr = FuncOpt(self.change_address,retval)
        self.baudrate = bitopt(self.change_baud,0xff,0,9600,
                               {3:1200,
                                4:2400,
                                5:4800,
                                6:9600,
                                7:19200,
                                8:38400})
        self.attrdict = {self.addr:1,
                         self.checksum:7,
                         self.baudrate:5}

    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'version', None, config)
        set_attribute(self, 'address', REQUIRED, config, int)

        # Default to existing values from the configuration.
        self.addr.default = self.address
        self.baud.default = self.from_baud(self.port.baud)

        # Configure the physical module.
        self.module_configuration()

    # Return the entire dictionary.
    def configuration(self):
        # Standard attributes.
        config = CompositeNode.configuration(self)
        config.update({'version':self.version, 'address':self.address})
        buf = self.validate('2')
        for a in self.attrdict.keys():
            if getattr(self.attrdict[a]):
                i = self.attrdict[a]
                config[a.name] = a.get(int(buf[i:i+2],16))
        return config

    # FIX ME:  Needs to update the default configuration and reset the
    #          requested change attributes.  Needs to reconfigure the
    #          port for baud rate changes.
    def module_configuration(self,config):
        x = {1:0,3:1,5:2,7:3}
        i = [0,0,0,0]
        for a in self.attrdict.keys():
            if config.has_key(a.name):
                i[x[self.attrdict[a]]] = a.set(config,i[x[self.attrdict[a]]])
            else:
                i[x[self.attrdict[a]]] = i[x[self.attrdict[a]]] | a.default
        cmd = hexb(i[0])+hexb(i[1])+hexb(i[2])+hexb(i[3])

        self.validate(cmd,prefix='%')

        for a in self.attrdict.keys():
            if config.has_key(a.name):
                a.default = config[a.name]

    def attributes(self):
        l = ()
        for a in self.attrdict.keys():
            l = l + (a.name,)
        return l

    def command(self,subcmd,prefix='$'):
        return self.parent.command(prefix + hexb(self.addr.default) +
                                   subcmd + CR)

    def valid(self,buf,vchar):
        return(buf[0]==vchar)

    def validate(self,cmd,prefix='$',vchar='!'):
        buf = self.command(cmd,prefix)
        if not self.valid(buf,vchar):
            raise "ADAMInvalidResponse",(cmd,buf)
        return buf

    def ReadModuleName(self):
        return chop(self.validate('M'))

    def ReadFirmwareVersion(self):
        return chop(self.validate('F'))

def factory():
    from unknown import Unknown
    return Unknown()

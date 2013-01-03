"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
#=----------------------------------------------------------------------------
# hwinfo.py
#
# Maintiain some interesting info about a Mediator.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import os
import re

from avr_lib import *
from cmdexec import execute_command

class HardwareInfo:
    def __init__(self):
        self._avr_fw_rev = "No coprocessor present"
        self._geode_cpu = 0
        self._model = None
        self._mac_addrs = [None, None]
        self._serialno = None
        self._serialno_df = '????'
        self._serialno_cisco = '????'
        self._product_id = '????'
        self._assembly = '????'

        if not os.path.exists('/proc/mediator'):
            raise Exception('Missing /proc/mediator, is UMD loaded?')
        
        ###
        # Get the model.
        try:
            f = open('/proc/mediator/model')
            self._model = f.read().strip()
        finally:
            f.close()

        ###
        # Get eth0's mac address.
        try:
            f = open('/proc/mediator/mac0')
            self._mac_addrs[0] = f.read().strip()
        finally:
            f.close()

        ###
        # Get eth1's mac address, if applicable.
        if os.path.exists('/proc/mediator/mac1'):
            try:
                f = open('/proc/mediator/mac1')
                self._mac_addrs[1] = f.read().strip()
            finally:
                f.close()

        ###
        # Get the serial number.
        try:
            f = open('/proc/mediator/serial')
            self._serialno = f.read().strip()
        finally:
            f.close()
            
        self.detect_geode()
        self.load_eeprom_text()
        return

    # Used when we update MAC address during the preflight check.
    def reload_values(self):
        self.__init__()
        
    def detect_geode(self):
        detect_geode_re = re.compile("^.*Geode\s*.*?", re.IGNORECASE)

        f = open('/proc/cpuinfo', 'r')
        detected = 0
        self._geode_cpu = 0
        for line in f.xreadlines():
            detected = detect_geode_re.match(line)
            if detected:
                self._geode_cpu = 1
        f.close()

    def get_avr_version(self, avr_copro):
        if not self._model in ('TSWS', 'PC'):
            self._avr_fw_rev = avr_copro.version()
            
    def load_eeprom_text(self):
        rslt, text = execute_command("ns -p0 -b -T")
        text = text[0]
        if not rslt:
            raise Exception('Unable to load eeprom text')
        if text.find(';') >= 0:
            self._product_id, self._assembly = text.split(';')
            self._assembly = self._assembly.strip()
            
        rslt, text = execute_command("ns -p1 -b -T")
        text = text[0]
        if not rslt:
            raise Exception('Unable to load eeprom text')
        if text.find(';') >= 0:
            self._serialno_df, self._serialno_cisco = text.split(';')
            self._serialno_cisco = self._serialno_cisco.strip()
        return

    def set_mac_addr(self, which, address):
        if (which < 0 or which > 1):
            raise Exception('Ethernet port %d is out of range, must be 0 or 1' % which)
        
        if len(address) == 6:
            # prepend OUI
            address = '0008e4' + address
            
        if address.count(':') == 0:
            if len(address) != 12:
                raise Exception('Illegal value (%s) for Mac Address' % address)
            address = '%s:%s:%s:%s:%s:%s' % (address[0:2], address[2:4], address[4:6], address[6:8], address[8:10], address[10:])
        
        if len(address) != 17:
            raise Exception('Illegal value (%s) for Mac Address')
        
        result = os.system('/bin/ns -b -i -p%d -m %s' % (which, address))
        if not (result == 0):
            raise Exception('Unable to set the MAC address for eth%d' % which)

        try:
            f = open('/proc/mediator/mac%d' % which)
            self._mac_addrs[which] = f.read().strip()
        finally:
            f.close()

        return
    
    def restart_networking(self):
        os.system('ifconfig eth0 down 1>/dev/null 2>/dev/null')
        os.system('ifconfig eth1 down 1>/dev/null 2>/dev/null')
        os.system('/etc/rc.d/init.d/network restart 1>/dev/null 2>/dev/null')
        self.reload_values()
        return
    
    def set_serialno(self, serial):
        result = os.system('/bin/ns -b -n %s' % serial)
        if not (result == 0):
            raise Exception('Unable to set the serial number in EEPROM.')

        self._serialno = serial;
        return
    
    def set_serialno_df(self, serial):
        if len(serial) > 32:
            raise Exception('Serial number must be less than 32 characters')
        self._serialno_df = serial
        text = "%s\\;%s" % (self._serialno_df, self._serialno_cisco)
        result = os.system('/bin/ns -b -p1 -t %s' % text)
        if not (result == 0):
            raise Exception('Unable to set the Serial Number')
        return
    
    def set_serialno_cisco(self, serial):
        if len(serial) > 32:
            raise Exception('Serial number must be less than 32 characters')
        self._serialno_cisco = serial
        text = "%s\\;%s" % (self._serialno_df, self._serialno_cisco)
        result = os.system('/bin/ns -b -p1 -t %s' % text)
        if not (result == 0):
            raise Exception('Unable to set the Serial Number')
        return
    
    def set_pid(self, product_id):
        if len(product_id) > 32:
            raise Exception('Product ID must be less than 32 characters')
        self._product_id = product_id
        text = "%s\\;%s" % (self._product_id, self._assembly)
        result = os.system('/bin/ns -b -p0 -t %s' % text)
        if not (result == 0):
            raise Exception('Unable to set the Product ID')
        return
    
    def set_assembly(self, assembly):
        if len(assembly) > 32:
            raise Exception('Assembly ID must be less than 32 characters')
        self._assembly = assembly
        text = "%s\\;%s" % (self._product_id, self._assembly)
        result = os.system('/bin/ns -b -p0 -t %s' % text)
        if not (result == 0):
            raise Exception('Unable to set the Assembly ID')
        return
    
    def get_pid(self):
        return self._product_id
    
    def get_assembly(self):
        return self._assembly
    
    def avr_fw_rev(self):
        return self._avr_fw_rev
    
    def is_geode_based(self):
        return self._geode_cpu

    def mac_addr(self, which=0):
        return self._mac_addrs[which]

    def model(self):
        return self._model

    def serialno(self):
        return self._serialno
    
    def serialno_df(self):
        return self._serialno_df
    
    def serialno_cisco(self):
        return self._serialno_cisco

#=- EOF ----------------------------------------------------------------------

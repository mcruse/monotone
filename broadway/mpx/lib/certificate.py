"""
Copyright (C) 2002 2009 2010 2011 Cisco Systems

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
import os
import stat

from mpx.lib.exceptions import EInvalidValue, EConfigurationIncomplete
from mpx import properties


def get_host():
    val = os.popen("grep -e ^hostname %s 2>/dev/null | sed 's/hostname = //g'"
                   % properties.MPXINIT_CONF_FILE).read().strip()
    if not val:
        val = os.popen("hostname -s 2>/dev/null").read().strip()
        if not val:
            val = "localhost"
    return val

def get_domain():
    val = os.popen(
        "grep -e ^domain_name %s 2>/dev/null | sed 's/domain_name = //g'"
        % properties.MPXINIT_CONF_FILE
        ).read().strip()
    if not val:
        val = os.popen("hostname -d 2>/dev/null").read().strip()
    return val

def is_outdated(certfile):
    # @fixme Should be derived, ETC_DIR is part of the install only.
    mpxconf  =  properties.MPXINIT_CONF_FILE
    # @fixme Why not put this in a broadway/bin directory.
    
 
    if os.access(certfile,os.F_OK) and os.access(mpxconf,os.F_OK):
        if os.stat(mpxconf)[stat.ST_MTIME] > os.stat(certfile)[stat.ST_MTIME]:
            return 1
        else:
            return 0
    return 1
   
    

class CertificateConfiguration:
    def __init__(self, name, **keywords):
        if keywords:
            self.configure(keywords)
    
    def set_country(self, code):
        if len(code) != 2:
            raise EInvalidValue('code', code, 'Country code must be 2 letters')
        self.country = code
    
    def set_state(self, state):
        self.state = state
    
    def set_locality(self, locality):
        self.locality = locality
    
    def set_organization(self, org):
        self.organization = org
    
    def set_organizational_unit(self, unit):
        self.unit = unit
    
    def set_common_name(self, name):
        self.name = name
    
    def set_email(self, address):
        self.email = address
    
    def configure(self, config):
        if config.has_key('C'):
            self.set_country(config['C'])
        if config.has_key('ST'):
            self.set_state(config['ST'])
        if config.has_key('L'):
            self.set_locality(config['L'])
        if config.has_key('O'):
            self.set_organization(config['O'])
        if config.has_key('OU'):
            self.set_organizational_unit(config['OU'])
        if config.has_key('CN'):
            self.set_common_name(config['CN'])
        if config.has_key('emailAddress'):
            self.set_email(config['emailAddress'])
    
    def configuration(self):
        return {'C':self.country, 'ST':self.state, 
                'L':self.locality, 'O':self.organization, 
                'OU':self.unit, 'CN':self.name, 
                'emailAddress':self.email}
    
    def __eq__(self, other):
        if other.__class__ == self.__class__:
            return other.configuration() == self.configuration()
        return other == self.configuration()
    
    def configured(self):
        try:
            self.configuration()
        except(AttributeError):
            return 0
        return 1
           
    
    def formatted_output(self):
        string = '[ req ]\n'
        string += 'prompt = no\n'
        string += 'distinguished_name = req_distinguished_name\n'
        string += '[req_distinguished_name]\n'
        config = self.configuration()
        string += 'C\t=%s\n' % config['C']
        string += 'ST\t=%s\n' % config['ST']
        string += 'L\t=%s\n' % config['L']
        string += 'O\t=%s\n' % config['O']
        string += 'OU\t=%s\n' % config['OU']
        string += 'CN\t=%s\n' % config['CN']
        string += 'emailAddress\t=%s\n' % config['emailAddress']
        return string
        
        
    def formatted_output_to_file(self, file):
        data = self.formatted_output()
        opened = 0
        if type(file) == type(''):
            file = open(file, 'w')
            opened = 1
        try:
            file.write(data)
            file.flush()
        finally:
            if opened:
                file.close()

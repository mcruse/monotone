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
#!/usr/bin/env python-mpx

import sys
import os

from mpx.install import *
from mpx.install.filesystem import makedirs
from mpx import properties

LIB_DIR = properties.LIB_DIR
ETC_DIR = properties.ETC_DIR

class InstallPAMSecurityLib(InstallPackage):
    def __init__(self):
        InstallPackage.__init__( self,
                                 'broadway.moab.user',
                                 'PAM: Library Installer')
    
    def _add_pam_config(self):
        '''
            creats /etc/pam.d/mpxauth file which contains
            the PAM configuration for MPX authentication
        '''
        filename = ETC_DIR + '/pam.d/mpxauth'
        content = 'auth\trequired\tpam_unix.so\n'
        if os.path.exists(filename):
            return
        if not os.path.exists(os.path.join(ETC_DIR + '/pam.d')):
            os.system('mkdir ' + ETC_DIR + '/pam.d/')
        pamH = open(filename, 'w')
        pamH.write(content)
        pamH.close() 
        message = "installing PAM configuration files"
        self.options.normal_message(message)

    def _add_pam_config_for_passwd(self):
        '''
            creats /etc/pam.d/passwd file which contains
            the PAM configuration for UNIX passwd
        '''
        filename = ETC_DIR + '/pam.d/passwd'
        content = 'password\trequired\tpam_unix.so md5 shadow\n'
        if os.path.exists(filename):
            return
        if not os.path.exists(os.path.join(ETC_DIR + '/pam.d')):
            os.system('mkdir ' + ETC_DIR + '/pam.d/')
        pamH = open(filename, 'w')
        pamH.write(content)
        pamH.close() 
        message = "installing PAM config for UNIX passwd"
        self.options.normal_message(message)

    def install(self):
        self.options.normal_message("installing PAM configurations")
        self._add_pam_config()
        self.options.normal_message("installing PAM config for UNIX passwd")
        self._add_pam_config_for_passwd()

    def get_conflicts(self):
        return []   

def MAIN(args=sys.argv, stdout=sys.stdout, stderr=sys.stderr):
    save_argv=sys.argv
    save_stdout=sys.stdout
    save_stderr=sys.stderr
    sys.argv=args
    sys.stdout=stdout
    sys.stderr=stderr
    try:
        InstallPAM = InstallPAMSecurityLib()
        return InstallPAM.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

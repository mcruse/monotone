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
#!/usr/bin/env python-mpx

import sys
import os

from mpx.install import *
from mpx.install.filesystem import makedirs
from mpx import properties

BIN_DIR = properties.BIN_DIR
ETC_DIR = properties.ETC_DIR
#
# Register custom install directories as properties.  Really should be in
# a property hook of some sort so it'll get set in normal operation.
#
# These don't need to be properties per-se, but the do need to be
# re-mappable so installation can be tested on the workstation.
#
# Of course, this should really be a different application either
# separate from, or built on-top of rz.omega (or whatever
# sub-components it needs.)
TARGET_ROOT = properties.TARGET_ROOT
properties.define_default(
    'NS_BIN_DIR',
    os.path.join(TARGET_ROOT, 'bin'),
    'bin directory for ns of the opt.mfw.production package.'
    )
NS_BIN_DIR = properties.NS_BIN_DIR

properties.define_default(
    'PRODUCTION_DIR',
    os.path.join(TARGET_ROOT,
                 *('opt/moe25/usr/lib/python2.5/site-packages/production'.
                   split('/'))),
    'Root directory for the standalone opt.mfw.production'
    )

BIN_MODULES = ['__init__', 'avr_lib', 'bootlog', 'burnin_test',
               'cmdexec', 'config', 'counters_relays','dallas',
               'db_lib', 'db_server', 'ethernet', 'hw_test',
               'hwinfo', 'i2c', 'logger', 'memory','modem','msg',
               'production_test', 'serial', 'test_framework',
               'test_methods','usb','versioner']

class InstallMfwOpt(InstallPackage):
    def __init__(self):
        InstallPackage.__init__( self,
                                 'mfw.production',
                                 'MFW: RZ2500 Production Support',
                                 ['mfw.opt', 'broadway'] )

    def _update_site_package(self):
        makedirs(properties.PRODUCTION_DIR)
        for module in BIN_MODULES:
            os.system('rm -f %s/%s.py*' % (properties.PRODUCTION_DIR, module))
            file = InstallFile(self.options, module+".pyc")
            file.relocate(properties.PRODUCTION_DIR)
            file.chmod(0644)

    def _update_bin(self):
        os.system('rm -f %s/runtest' % (BIN_DIR))
        for bin in ['runtest', 'memtester', 'mediator_test', 'netperf']:
            file = InstallFile(self.options, bin)
            file.relocate(BIN_DIR)
            file.chmod(0770)
        file = InstallFile(self.options, 'ns')
        file.relocate(NS_BIN_DIR)
        file.chmod(0770)
        
    def _update_etc(self):
        os.system('rm -f %s/hw_test.conf' % (ETC_DIR))
        file = InstallFile(self.options, 'hw_test.conf')
        file.relocate(ETC_DIR)
        file.chmod(0664)
    
    def install(self):
        self.options.normal_message("installing opt.mfw.production")
        self._update_site_package()
        self._update_bin()
        self._update_etc()
        
    def upgrade(self):
        self.install()
        
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
        ip = InstallMfwOpt()
        return ip.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

"""
Copyright (C) 2003 2004 2006 2007 2008 2010 2011 Cisco Systems

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
import re

from mpx.install import *
from mpx import properties

SCRIPT_EXEC_LINE="#!/usr/bin/env python-mpx\n"
PYTHON_SHELL=re.compile(".*python[ 0-9].*")

class InstallMOAB( InstallPackage ):
    def __init__( self ):
        InstallPackage.__init__( self,
                                 'broadway.moab',
                                 'Broadway: MOE Abstraction Layer',
                                 ['broadway.moab.config_service',
                                  'broadway.moab.user'] )
        return
    def _remove_outofdate_files(self):
        self.options.normal_message("removing out of date MOE files")
        outofdate_files = ('/usr/lib/mpx/python/ioport.so',
                           '/usr/lib/python2.2/ioport.so')
        for f in outofdate_files:
            if os.path.exists(f) or os.path.islink(f):
                self.options.normal_message(
                    "unlinking out of date file: %s", f
                    )
                os.unlink(f)
        return
    def _update_moab_python_scripts(self):
        global SCRIPT_EXEC_LINE
        self.options.normal_message("upgrading existing MOE files")
        script_files = (
            os.path.join(properties.TARGET_ROOT, 'bin/logman'),
            os.path.join(properties.TARGET_ROOT, 'bin/mc'),
            os.path.join(properties.TARGET_ROOT, 'bin/mpx_igmp'),
            os.path.join(properties.TARGET_ROOT, 'bin/mpxconfig-lite'),
            os.path.join(properties.TARGET_ROOT, 'bin/serialtest'),
            os.path.join(properties.TARGET_ROOT, 'etc/rc.mpx'),
            os.path.join(properties.TARGET_ROOT, 'home/mpxadmin/is'),
            os.path.join(properties.TARGET_ROOT, 'usr/bin/avrversion'),
            )
        for s in script_files:
            if not os.path.exists(s):
                self.options.normal_message(
                    "%s does not exist.  Skipping upgrade.", s
                    )
                continue
            f = open(s,'r')
            line = f.readline(1024)
            f.close()
            if line == SCRIPT_EXEC_LINE:
                self.options.normal_message(
                    "%s already upgraded.", s
                    )
            elif PYTHON_SHELL.match(line):
                self.options.normal_message(
                    "Upgrading %s to use python-mpx", s
                    )
                tmp_file="%s-install.%s" % (s, os.getpid())
                os.rename(s, tmp_file)
                try:
                    src=open(tmp_file,'r')
                    dst=open(s,'w')
                    src.readline()
                    dst.write(SCRIPT_EXEC_LINE)
                    for line in src.xreadlines():
                        dst.write(line)
                    src.close()
                    dst.close()
                    os.unlink(tmp_file)
                    os.chmod(s, int('0755',8))
                except:
                    if os.path.exists(tmp_file):
                        if os.path.exists(s):
                            os.unlink(s)
                        os.rename(tmp_file,s)
                    raise
            else:
                self.options.normal_message(
                    "skipping %s, unrecognized shell: %s", (s, line[0:-1])
                    )
        return
    def install(self):
        self._remove_outofdate_files()
        self._update_moab_python_scripts()
        return
    def get_conflicts(self):
        return self.conflict_list    

def MAIN(args=sys.argv, stdout=sys.stdout, stderr=sys.stderr):
    save_argv=sys.argv
    save_stdout=sys.stdout
    save_stderr=sys.stderr
    sys.argv=args
    sys.stdout=stdout
    sys.stderr=stderr
    try:
        # MAIN()
        ip = InstallMOAB()
        return ip.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

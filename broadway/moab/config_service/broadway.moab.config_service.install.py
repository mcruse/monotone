"""
Copyright (C) 2003 2006 2010 2011 Cisco Systems

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
#-*-Python-*- Hint to [X]Emacs on colorization, etc...
from tools.lib import os, CommandKeywords
import sys, signal

from mpx.install import *
from mpx.install.filesystem import makedirs, chown

from mpx import properties

ROOT = properties.ROOT
LIB_DIR = properties.LIB_DIR
SBIN_DIR = properties.SBIN_DIR
MPX_UID = properties.MPX_UID
MPX_GID = properties.MPX_GID
DUP_DIR = os.path.realpath(os.path.join(LIB_DIR, 'moab/config_service'))
CONFIG_SCRIPT = os.path.realpath(os.path.join(SBIN_DIR, 'config_service'))
CONFIG_PYC =os.path.realpath(os.path.join(DUP_DIR,
                                          'config_service_startup.pyc'))

class InstallSelf(InstallPackage):
    def __init__(self):
        InstallPackage.__init__(self, "broadway.moab.config_service",
                                ('Broadway: MOE Abstraction Layer ' +
                                 'Configuration Service'),
                                ['broadway.moab.linux'])
        self.keywords = {}
        self.keywords.update(CommandKeywords.DEFAULTS)
        self.keywords["verbosity"] = (self.options.verbose + 1)
        self.keywords["debug"] = self.options.debug
        self.keywords["test"] = self.options.test
        return
    def install(self):
        #
        # Note:  Unfortunately the following two import statements have
        #        the side-effect of trying to create a directory under
        #        /var/mpx.  This isn't necessary when just trying to
        #        query this install script and in fact fails in some
        #        cases, so the imports were moved from the top of this
        #        script to here.
        #
        from moab.linux.lib.servicemgr import InittabManager
        from moab.linux.lib.servicemgr import InittabGroup
        
        chown(ROOT, MPX_UID, MPX_GID, recurse=1, ignore_errors=1)
        keywords = {}
        keywords.update(self.keywords)
        keywords.update({'ROOT':DUP_DIR})
        keywords[CommandKeywords.FATAL_KEY] = 1
        # Duplicate the config service so it will work after /usr/lib/broadway
        # is nuked.
        makedirs(DUP_DIR)
        os.system("cp *.pyc %s" % DUP_DIR, **keywords)
        chown(DUP_DIR, MPX_UID, MPX_GID, recurse=1, ignore_errors=1)
        os.system("chmod -R %o %s/*" % (0664, DUP_DIR), **keywords)
        # Create the config_service's custom launcher.
        create_pyscript(CONFIG_SCRIPT, CONFIG_PYC, **keywords)
        # Update inittab to include the new config service.
        inittab = InittabManager(**keywords)
        gname = 'MEDIATOR_CONFIGURATION_SERVICE'
        # Remove any existing mpx_igmp entry.
        for group in inittab.group_list:
            lines = group.text.split('\n')
            found = 0
            for i in range(0, len(lines)):
                line = lines[i]
                if line and line[0] != '#' and line.find('mpx_igmp') != -1:
                    lines[i] = "# %s # - %s" % (line, gname)
                    found = 1
            if found:
                text = lines.pop(0)
                for line in lines:
                    text = "%s\n%s" % (text, line)
                group.text = text
        # Add the Mediator Configuration Service.
        mcs = inittab.findgroup(gname)
        text = 'MCS:2345:respawn:%s' % CONFIG_SCRIPT
        if mcs is None:
            inittab.addgroup(InittabGroup(gname, text))
        else:
            mcs.text = text
        inittab.commit()
        return 0

def MAIN(args=sys.argv, stdout=sys.stdout, stderr=sys.stderr):
    save_argv=sys.argv
    save_stdout=sys.stdout
    save_stderr=sys.stderr
    sys.argv=args
    sys.stdout=stdout
    sys.stderr=stderr
    try:
        # MAIN()
        ip = InstallSelf()
        return ip.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

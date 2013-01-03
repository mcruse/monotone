"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

import os

import mpx

from filesystem import makedirs
from stat import *

ORIG_DIR = os.getcwd()
TEMP_DIR = mpx.properties.TEMP_DIR

class TestCase(DefaultTestFixture):
    VERBOSE=0
    def write(self, fmt, *args):
        if args:
            self.stdout.write(fmt % args)
        else:
            self.stdout.write(fmt)
        self.stdout.flush()
        return
    def writeln(self, fmt, *args):
        fmt = fmt + '%s'
        new_args = []
        new_args.extend(args)
        new_args.append('\n')
        self.write(fmt, *new_args)
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        os.chdir(TEMP_DIR)
        return
    def tearDown(self):
        os.chdir(ORIG_DIR)
        DefaultTestFixture.tearDown(self)
        return
    def test_simple_makedirs(self, quiet=0):
        if self.VERBOSE and not quiet:
            self.write("_test_simple_makedirs():")
        paths = (
            "one",
            "one/two",
            "one/two/three",
            "one/two/three/four",
            "one/two/three/four/five",
            )
        if self.VERBOSE and not quiet:
            self.write(" Creating")
        for path in paths:
            if self.VERBOSE and not quiet:
                self.write(" %s,", path)
            makedirs(path, verbosity=0)
            assert os.path.isdir(path), (
                "Failed to create %s" % (path,))
        if self.VERBOSE and not quiet:
            self.writeln(" done.")
        return
    # Note: This case is not run at the moment because we aren't sure
    #       if we want the behavior that it tries to enforce or not,
    #       that is the ability to call makedirs with the permissions
    #       bit specified and not have those permissions bits being
    #       affected by the global process umask.
    def _test_simple_makedirs_with_perms(self, quiet=0):
        test_perms = (0770, 0755, 0644)
        if self.VERBOSE and not quiet:
            cur_umask = os.umask(0)
            os.umask(cur_umask)
            print 'cur_umask is %x.' % cur_umask
        for p in test_perms:
            if self.VERBOSE and not quiet:
                self.write("_test_simple_makedirs_with_perms():")
            paths = (
                "one",
                )
            if self.VERBOSE and not quiet:
                self.write(" Creating")
            for path in paths:
                if self.VERBOSE and not quiet:
                    self.write(" %s,", path)
                makedirs(path, p, verbosity=0)
                assert os.path.isdir(path), (
                    "Failed to create %s" % (path,))
                stmode = S_IMODE(os.stat(path).st_mode)
                if p != stmode:
                    if self.VERBOSE and not quiet:
                        print os.system('ls -al .')
                    raise 'Requested mode was 0x%X - Actual mode is 0x%X.' % (p, stmode)
            self.writeln(" done.")
            os.system('chmod -R a+wxr one')
            os.system('rm -rf one')
        return
    def test_brokenlink_makedirs(self, quiet=0):
        if self.VERBOSE and not quiet:
            self.writeln("test_brokenlink_makedirs():")
        map = {
            "one":"one",
            "one/two":"one",
            "one/two/three":"one/two",
            "one/two/three/four":"one",
            "one/two/three/four/five":"one/two/three/four/five",
            }
        for dirpath, badlinkpath in map.items():
            dir,link = os.path.split(badlinkpath)
            if dir:
                # Create up to (but not including) the broken link.
                makedirs(dir, verbosity=0)
            assert not os.path.exists(badlinkpath), (
                "Internal test failure, %r appears to exist.")
            assert not os.path.islink(badlinkpath), (
                "Internal test failure, %r appears NOT to be a link.")
            # Now try to create the complete path which should replace the
            # broken link.
            if self.VERBOSE and not quiet:
                self.writeln("    Creating %s, replacing %s",
                             dirpath, badlinkpath)
            # Create the broken link.
            os.symlink("broken_link_points_here_which_does_not_exist",
                       badlinkpath)
            makedirs(dirpath, verbosity=0)
            os.removedirs(dirpath)
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    TestCase.VERBOSE=1
    main()

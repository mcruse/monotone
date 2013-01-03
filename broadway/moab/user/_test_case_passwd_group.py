"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import sys
import types

import manager

from manager import PasswdEntry
from manager import PasswdFile
from manager import GroupEntry
from manager import GroupFile

class TestCase(DefaultTestFixture):
    VERBOSE = 0
    MODULE_DIRECTORY = manager.__file__
    MODULE_DIRECTORY = os.path.realpath(MODULE_DIRECTORY)
    MODULE_DIRECTORY = os.path.dirname(MODULE_DIRECTORY)
    GROUP_FILE = os.path.join(MODULE_DIRECTORY, 'group')
    PASSWD_FILE = os.path.join(MODULE_DIRECTORY, 'passwd')
    def output(self, fmt, *args):
        if self.VERBOSE:
            sys.stderr.write(fmt % args)
            sys.stderr.flush()
    #
    # I want the first 6 tests to run before the others, that's why
    # there names contain numbers.
    #
    def test_1_GroupEntry(self, quiet=0):
        if not quiet: self.output('\ntest_1_GroupEntry:')
        result = GroupEntry()
        return result
    def test_2_GroupFile(self, quiet=0):
        if not quiet: self.output('\ntest_2_GroupFile:')
        result = GroupFile(self.GROUP_FILE)
        return result
    def test_3_PasswdEntry(self, quiet=0):
        if not quiet: self.output('\ntest_3_PasswdEntry:')
        result = PasswdEntry()
        return result
    def test_4_PasswdFile(self, quiet=0):
        if not quiet: self.output('\ntest_4_PasswdFile:')
        result = PasswdFile(self.PASSWD_FILE)
        return result
    def test_5_load_group(self, quiet=0):
        if not quiet: self.output('\ntest_5_load_group:')
        gf = self.test_2_GroupFile(1)
        gf.load()
        return gf
    def test_6_load_passwd(self, quiet=0):
        if not quiet: self.output('\ntest_6_load_passwd:')
        pf = self.test_4_PasswdFile(1)
        pf.load()
        return pf
    #
    # These tests can run in any order...
    #
    def test_root_in_group(self, quiet=0):
        if not quiet: self.output('\ntest_root_in_group:')
        gf = self.test_5_load_group(1)
        if 'root' not in gf:
            raise "Root's not in /etc/group.  Fat chance..."
        return
    def test_root_in_passwd(self, quiet=0):
        if not quiet: self.output('\ntest_root_in_passwd:')
        pf = self.test_6_load_passwd(1)
        if 'root' not in pf:
            raise "Root's not in /etc/passwd.  Fat chance..."
        return
    def test_ROOT_not_in_group(self, quiet=0):
        if not quiet: self.output('\ntest_ROOT_not_in_group:')
        gf = self.test_5_load_group(1)
        if 'ROOT' in gf:
            raise "ROOT's in /etc/group.  Fat chance..."
        return
    def test_root_group_password(self, quiet=0):
        if not quiet: self.output('\ntest_root_group_password:')
        pf = self.test_6_load_passwd(1)
        if not pf['root'].password_matches_crypt('c8h10n4o2'):
            raise 'Valid password failed.'
        return
    def test_invalid_root_group_password(self, quiet=0):
        if not quiet: self.output('\ntest_root_group_password:')
        pf = self.test_6_load_passwd(1)
        if pf['root'].password_matches_crypt('MPX'):
            raise 'Invalid password accepted.'
        return
    def test_ROOT_not_in_passwd(self, quiet=0):
        if not quiet: self.output('\ntest_ROOT_not_in_passwd:')
        pf = self.test_6_load_passwd(1)
        if 'ROOT' in pf:
            raise "ROOT's in /etc/passwd.  Fat chance..."
        return
    def test_root_user_password(self, quiet=0):
        if not quiet: self.output('\ntest_root_user_password:')
        pf = self.test_6_load_passwd(1)
        if not pf['root'].password_matches_crypt('c8h10n4o2'):
            raise 'Valid password failed.'
        return
    def test_invalid_root_user_password(self, quiet=0):
        if not quiet: self.output('\ntest_root_user_password:')
        pf = self.test_6_load_passwd(1)
        if pf['root'].password_matches_crypt('MPX'):
            raise 'Invalid password accepted.'
        return
    def test_add_new_user(self, quiet=0):
        if not quiet: self.output('\ntest_add_new_user:')
        pf = self.test_6_load_passwd(1)
        entry = PasswdEntry()
        entry.user("new_user")
        entry.uid(pf.new_uid())
        entry.gid(entry.uid())
        entry.directory(pf.default_home(entry.user()))
        pf[entry.user()] = entry
        assert entry.user() in pf, (
            "__contains__ failed after a __setitem__."
            )
        found = pf[entry.user()]
        assert str(entry) == str(found), (
            "__getitem__ returned an entry that did not equate to " +
            "what was set."
            )
# Cause I'm lazy...
template_test = """
    def test_(self, quiet=0):
        if not quiet: self.output('\ntest_:')
        return
"""

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    TestCase.VERBOSE = 1
    main()

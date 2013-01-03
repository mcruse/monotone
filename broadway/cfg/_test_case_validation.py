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
from mpx_test import DefaultTestFixture

import os
import re

RE_TTYS1 = re.compile("^.*/dev/ttyS1.*$")

from mpx import properties

class TestCase(DefaultTestFixture):
    def _x500_callback(self, path, visit):
        os.path.walk(path, self._x500_callback_filter, None)
        return
    def _x500_callback_filter(self, arg, dirname, names):
        for dir in ('prelease.d',):
            if dir in names:
                names.remove(dir)
        for name in ('1500.xml', '2500.xml'):
            if name in names:
                self._x500_callback_visit(os.path.join(dirname, name))
        return
    def _x500_callback_visit(self, pathname):
        f = open(pathname,'r')
        iline = 1
        for line in f.xreadlines():
            if RE_TTYS1.match(line):
                # A 1500.xml or 2500.xml file contains a reference to
                # /dev/ttyS1, which does not exist.
                self._x500_failures.append(pathname)
                break
            iline += 1
        return
    def test_bug_5697(self):
        self._x500_failures = []
        self._x500_callback(properties.ROOT, self._x500_callback_visit)
        if self._x500_failures:
            message = """

README README README README README README README README README README

The following files contain default configurations for 1500 and 2500
Mediators but contain references to /dev/ttyS1 which is an invalid
device on those platforms.  At a bare minimum, /dev/ttyS1 should be
replaced with a correct reference (/dev/ttySe), but the truth is
that the file should be reviewed for all platform specific references
(/dev/*, counter, digital in, and relay configurations):
"""
            for pathname in self._x500_failures:
                message += "\n    %s" % pathname[len(properties.ROOT)+1:]
            message += """

README README README README README README README README README README"""
            self.fail(message)
        return

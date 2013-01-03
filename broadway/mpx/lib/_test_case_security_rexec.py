"""
Copyright (C) 2001 2002 2003 2010 2011 Cisco Systems

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
# Test cases to exercise the mpx.lib.security.RExec class.

from mpx_test import DefaultTestFixture, main

import warnings

from mpx.lib.security import RExec
from mpx.lib.exceptions import EConfigurationIncomplete

class TestCase(DefaultTestFixture):
    def _setUp(self):
        warnings.resetwarnings()
        self.rexec = RExec()
        return
    def _tearDown(self):
        if hasattr(self, 'rexec'):
            del self.rexec
        return
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self._setUp()
        return
    def tearDown(self):
        try:
            self._tearDown()
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_create(self):
        return
    def test_simple_reval(self):
        result = self.rexec.r_eval('1 + 1')
        if result != 2:
            raise 'Failed simple r_eval.'
        return
    def test_ok_python_imports(self):
        self._tearDown()
        for m in ('audioop', 'array', 'binascii', 'cmath', 'errno', 'imageop',
                  'marshal', 'math', 'md5', 'operator', 'parser', 're',
                  'select', 'strop', 'struct', 'time',
                  'marshal', '__builtin__', '__main__', 'sys', 'posix',
                  ):
            self._setUp()
            warnings.filterwarnings("ignore", '.*', DeprecationWarning)
            self.rexec.r_exec('import %s' % m)
    def test_scary_python_imports(self):
        self._tearDown()
        for m in ('socket', 'msglog', 'signal', 'SocketServer', 'mmap'):
            self._setUp()
            try: self.rexec.r_exec('import %s' % m)
            except ImportError: pass
            else: raise 'Failed to recognize a dangerous module: %s' % m

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

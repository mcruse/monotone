"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import sys

from cmdexec import execute_command
from test import Test

from ion import Factory

class MemoryTester(Test):
    def __init__(self, **kw):
        self.memory = 256
        self.iterations = 1
        self.memtester = '/usr/bin/memtester'
        super(MemoryTester, self).__init__(**kw)
        self._test_name = 'MemoryTester'
        return
        
    def runtest(self):
        self.log('Testing system RAM.')
        result, spewage = execute_command(self.testprog)
        if not result:
            self.log('ERROR: Memory test failed: %s' % spewage)
            self._nerrors += 1
        else:
            self.log('SUCCESS: Memory test passed: %s' % spewage)
        return self.passed()

    def _get_test_prog(self):
        return '%s %d %d' % \
            (self.memtester, self.memory, self.iterations)
    # testprog is a property so that "memory" and "iterations"
    # can easily be changed at runtime
    testprog = property(_get_test_prog)

f = Factory()
f.register('MemoryTester', (MemoryTester,))
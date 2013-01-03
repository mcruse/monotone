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
import time
import os

from mpx_test import DefaultTestFixture, main

from mpx import properties
from mpx.lib import log

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self._build_log('corrupt', log)
        return
    def _instantiate_log(self, name, module=log):
        self.log = module.Log(name)
        return
    def _build_log(self, name, module=log):
        self._instantiate_log(name, module=log)
        # __init__(self, name = None, position = None, sort_order = None):
        self.c2 = module.ColumnConfiguration('c2', 2, 'none')
        self.c3 = module.ColumnConfiguration('c3', 3, 'none')
        self.c4 = module.ColumnConfiguration('c4', 4, 'none')
        self.timestamp = module.ColumnConfiguration('timestamp', 0, 'ascending')
        self.reverse = module.ColumnConfiguration('reverse', 1, 'descending')
        self.length = 160
        reverse = self.length
        for count in range(0, 4):
            self.log.configure([self.timestamp, self.reverse, self.c2,
                                self.c3, self.c4])
            for i in range(0, 20):
                t = time.time()
                if count == 0 and i == 0:
                    self.t1 = t
                self.log.add_entry([t, reverse, 2, 3, 4])
                reverse -= 1
            
            self.log.configure([self.timestamp, self.reverse,
                                self.c2, self.c3])
            for i in range(0, 20):
                t = time.time()
                self.log.add_entry([t, reverse, 2, 3])
                reverse -= 1
        self.t2 = t
        return
    def test_open_bad_last_line(self):
        # Append garbage to the log file.
        f = open(self.log.filename,'a')
        f.write("Wow, what's this neato file?")
        f.close()
        # Re-instantiate the log object.
        self.log = self._instantiate_log(self.log.name, log)
        return
    def test_open_recover_good_file(self):
        r1 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r1.append(row)
        self.log.recover()
        r2 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r2.append(row)
        assert r1 == r2, "Recoverred log does not match the original."
        return
    def test_open_recover_bad_first_row(self):
        # Read the good log.
        r1 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r1.append(row)
        # Corrupt the first row.
        log = os.open(self.log.filename, os.O_WRONLY)
        os.write(log, '........')
        os.close(log)
        # Recover the log.
        self.log.recover()
        # Read the recovered log.
        r2 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r2.append(row)
        r1.pop(0) # Toss the row that was corrupt.
        assert r1 == r2, "Recoverred log does not match expected results."
        return
    def test_open_recover_bad_last_row(self):
        # Read the good log.
        r1 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r1.append(row)
        # Corrupt the last row.
        log = os.open(self.log.filename, os.O_WRONLY)
        junk = '??????????'
        os.lseek(log, -len(junk), 2)
        os.write(log, junk)
        os.close(log)
        # Recover the log.
        self.log.recover()
        # Read the recovered log.
        r2 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r2.append(row)
        r1.pop() # Toss the row that was corrupt.
        assert r1 == r2, "Recoverred log does not match expected results."
        return
    def test_open_recover_bad_odd_rows(self):
        # Read the good log.
        r1 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r1.append(row)
        # Corrupt every other row.
        junk = '\xde\xed\xbe\xef'
        input = open(self.log.filename, 'rb')
        output = os.open(self.log.filename, os.O_WRONLY)
        row = 0
        line = input.readline()
        while line:
            pos = input.tell()
            os.lseek(output, pos, 0)
            line = input.readline()
            row += 1
            if row & 1:
                os.write(output, junk)
        input.close()
        os.close(output)
        # Recover the log.
        self.log.recover()
        # Read the recovered log.
        r2 = []
        for row in self.log.get_slice(0, 0, 0x7fffffff, 1):
            r2.append(row)
        # Toss the all the corrupt rows.
        for icorrupt in range(len(r1)-1,0,-2):
            r1.pop(icorrupt)
        assert r1 == r2, "Recoverred log does not match expected results."
        return

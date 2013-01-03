"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import StringIO
import array
import string

from _data import CircularBuffer

class TestCase(DefaultTestFixture):
    ##
    # Sets up self.log who is configured to have columns:
    # timestamp, reverse, c2, c3, c4 for seqs 0-19, 40-59, 80-99, 120-139 
    # and columns timestamp, reverse, c2, c3 for seqs: 20-39, 60-79, 100-119,
    # 140-159
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self._buffer = StringIO.StringIO()
        self._circular = CircularBuffer(self._buffer,10)
        return
    def tearDown(self):
        try:
            self._circular.close()
            del(self._circular)
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_initialize(self):
        self._circular.initialize('\x00')
        self.failUnless(self._circular.tell() == 0,'Initialize failed to ' +
                        'return buffer to 0.')
        self.failUnless(len(self._circular) == 0, 'Circular failed to ' + 
                        'report correct buffer length')
    def test_read(self):
        data = ''
        for i in range(0,10):
            data += str(i)
        self._circular.write(data)
        self._circular.seek(0)
        self.failUnless(self._circular.read(1) == '0',
                        'Failed to read first byte')
        self.failUnless(self._circular.read(9) == data[1:], 
                        'Failed to read the remaining data')
        self.failUnless(self._circular.read(1) == '0',
                        'Failed to wrap correctly')
        self.failUnless(self._circular.read(10) == data[1:]+'0',
                       'Failed to wrap correctly on read that carried over')
        self.failUnless(len(self._circular.read(11)) == 10, 
                         'Returned more than length data')
    def test_write(self):
        self._circular.write('shane')
        self.failUnless(self._circular.tell() == 5,'Did not correctly ' + 
                        'return seek location after writing')
        self._circular.write('c'*10)
        self.failUnless(self._circular.tell() == 10, 
                        'Did not wrap correctly at end')
        self.failUnless(self._circular.read(10) == 'c'*10,
                        'Did not return correct data after write')
        self.failUnless(self._circular.tell() == 10, 'Did not wrap after read')
        self._circular.seek(10)
        self._circular.write('a')
        self._circular.seek(0)
        self.failUnless(self._circular.read(1) == 'a', 
                        'Did not write to beginning when at end')
        self.failUnless(len(self._circular) == 10, 
                        'Reported incorrect length')

if __name__ == '__main__':
    main()

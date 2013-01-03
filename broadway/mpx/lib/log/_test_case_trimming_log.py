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
##
# @todo  Need to add a test that does a trim greater than for a value
#        that crosses a seq barrier, then closes everything and re-opens 
#        it to make sure that the next entry added picks up with a previously
#        unused seq number.
from mpx_test import DefaultTestFixture, main

import os
import stat
import time

from mpx import properties
from mpx.lib import log

class TestCase(DefaultTestFixture):
    ##
    # Sets up self.log who is configured to have columns:
    # timestamp, reverse, c2, c3, c4 for seqs 0-19, 40-59, 80-99, 120-139 
    # and columns timestamp, reverse, c2, c3 for seqs: 20-39, 60-79, 100-119,
    # 140-159
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.log = log.TrimmingLog('trimming_test')
        # __init__(self, name = None, position = None, sort_order = None):
        self.c2 = log.ColumnConfiguration('c2', 1, 'none')
        self.c3 = log.ColumnConfiguration('c3', 2, 'none')
        self.c4 = log.ColumnConfiguration('c4', 3, 'none')
        self.timestamp = log.ColumnConfiguration('timestamp', 0, 'ascending')
        return
    def tearDown(self):
        try:
            self.log.destroy()
        finally:
            DefaultTestFixture.tearDown(self)
    def test_trim(self):
        logfile = None
        min = 250
        max = 500
        self.log.configure([self.timestamp, self.c2,
                                self.c3, self.c4], min, max)
        self.log.add_entry([time.time(), 2, 3, 4])
        self.first_seq = 0
        self.seq = 0
        pre_size = -1
        post_size = 0
        count = 3
        while count:
            pre_size = os.stat(self.log.filename)[stat.ST_SIZE]
            for i in range(0, 20):
                self.log.add_entry([time.time(), 2, 3, 4])
                self.seq += 1
            
            self.log.configure([self.timestamp,
                                self.c2, self.c3], min, max)
            for i in range(0, 20):
                self.log.add_entry([time.time(), 2, 3])
                self.seq += 1
            self.log.configure([self.timestamp, self.c2,
                                self.c3, self.c4], min, max)
            post_size = os.stat(self.log.filename)[stat.ST_SIZE]
            self.failIf(post_size > max * 1024, 'Trimming log has grown larger than max')
            if post_size < pre_size:
                self._test_trim_job()
                count -= 1
        else:
            self.failUnless(post_size >= min, 'Trim trimmed log to smaller than min')
    
    def _test_trim_job(self):
        start_seq = self.log.get_first_record()['_seq']
        self.failIf(start_seq <= self.first_seq, 'Trim did not trim first record')
        self.first_seq = start_seq
        self.failUnless(self.log[-1:][0]['_seq'] == self.seq, 'Last seq is incorrect')
    
if(__name__ == '__main__'):    
    main()

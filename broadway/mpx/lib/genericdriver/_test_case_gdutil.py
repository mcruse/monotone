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
"""
_test_case_gdutil.py
"""

import os
import sys
import time

import gdutil as gu

from mpx_test import DefaultTestFixture, main

class TestCase(DefaultTestFixture): 
    def test_get_lock(self):
        l = gu.get_lock()
        l.acquire()
        l.release()
    #
    def test_get_time(self):
        t1 = gu.get_time()
        time.sleep(1.1)
        t2 = gu.get_time()

        diff = t2 - t1

        if diff < 1 or diff > 2:
            raise "Difference out of range.  Should be ~1.1, got %f" % diff
    #
    def test_gdexception(self):
        t = gu.GDException("testexception")
        try:
            raise t
        except Exception,e:
            estr = str(e)
            assert estr == "testexception", "Did not get expected string representation of exception"

        t = gu.GDTimeoutException("timeoutexception")
        try:
            raise t
        except Exception,e:
            estr = str(e)
            assert estr == "timeoutexception", "Did not get expected string representation of exception"

        t = gu.GDConnectionClosedException("connectionclosedexception")
        try:
            raise t
        except Exception,e:
            estr = str(e)
            assert estr == "connectionclosedexception", "Did not get expected string representation of exception"

        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        

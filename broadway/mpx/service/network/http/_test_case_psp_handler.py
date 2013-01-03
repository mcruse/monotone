"""
Copyright (C) 2004 2006 2010 2011 Cisco Systems

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
from StringIO import StringIO
import os
from mpx_test import DefaultTestFixture, main
from psp_handler import _Include
import re

class TestCase(DefaultTestFixture):
    def test_1(self):
        dh = _Include('')
        l = '   <%@ include file="somefile.psp" %>'
        if not dh.match(l):
            self.fail('Should have matched')
    def test_filematch_single(self):
        dh = _Include('')
        l = "   <%@ include file='somefile.psp' %>"
        dh._get_filename(l)
    def test_filematch_double(self):
        dh = _Include('')
        l = '   <%@ include file="somefile.psp" %>'
        dh._get_filename(l)
    def test_process(self):
        try:       
            f = None
            fn = "test_case_psp_handler.psp"
            f = open(fn,'w')
            dh = _Include('')            
            l = '   <%@ include file="test_case_psp_handler.psp" %>'
            dh.process(f,l)
        finally:
            if f:
                f.close()
            if os.path.isfile(fn):
                os.remove(fn)
    def test_psp_regx(self):
        tests = []
        tests.append({'test':'test.psp','result':1})
        tests.append({'test':'test.html','result':0})
        tests.append({'test':'/somedir/another_level/test.html','result':0})
        tests.append({'test':'/somedir/another_level/test.psp','result':1})        
        i = _Include('')
        file = 'Test.psp'
        for t in tests:
            s = i.regx_psp.search(t['test'])
            if t['result']:
                if not s:
                    self.fail('Failed to match psp regular expression')
            else:
                if s:
                    self.fail('Failed to match psp regular expression')                    

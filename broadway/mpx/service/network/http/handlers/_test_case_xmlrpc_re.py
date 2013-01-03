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
from mpx_test import DefaultTestFixture,main
import re

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.xmlrpc_path = '/xmlrpc'   
        self.XMLRPCv2_path = '/XMLRPCv2'
        self.XMLRPCv2_re = '^%s$|^%s/.*'

    def test_xmlrpcv1_1(self):        
        p = '^%s$' % self.xmlrpc_path
        path = '/xmlrpc'
        if not re.search(p,path):
            raise Exception('Failed:%s' % path)
        
    def test_XMLRPCv2_1(self):
        p = self.XMLRPCv2_re % (self.XMLRPCv2_path,self.XMLRPCv2_path)
        path = '/XMLRPCv2'
        if not re.search(p,path):
            raise Exception('Failed:%s' % path)
        
    def test_XMLRPCv2_2(self):
        p = self.XMLRPCv2_re % (self.XMLRPCv2_path,self.XMLRPCv2_path)
        path = '/XMLRPCv2/RNA'
        if not re.search(p,path):
            raise Exception('Failed:%s' % path)
       
        
if(__name__ == '__main__'):
    main()

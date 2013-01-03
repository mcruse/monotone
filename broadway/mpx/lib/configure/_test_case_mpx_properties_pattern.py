"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
import re
from mpx_test import DefaultTestFixture,main
import mpx
from _attributes import _pattern as pattern

class TestCase(DefaultTestFixture):
    def __init__(self,*args,**kw):
        args = (self,) + args
        DefaultTestFixture.__init__(*args, **kw)
        self.test =  ( 
           ('${mpx.properties.HTTP_ROOT}',1,'beginnig of line test'),
           (' ${mpx.properties.HTTP_ROOT}',1,'space before '),
           (' sadfsaasdf sdfsad \${mpx.properties.HTTP_ROOT}',0,'words then a slash'),
           (' \${mpx.properties.HTTP_ROOT}',0,'space then a slash'),
           ('some test ${mpx.properties.HTTP_ROOT} ',1,''),
           ('      ${mpx.properties.HTTP_ROOT} ',1,''),
           ('\${mpx.properties.HTTP_ROOT} ${mpx.properties.HTTP_ROOT} ',1,''),
           ('${mpx.properties.HTTP_ROOT} \${mpx.properties.HTTP_ROOT} ',1,''),
           ('${mpx.properties.HTTP_ROOT } ',0,''),
           ('${mpx.properties.http_root} ',0,''),
           ('${mpx.properties.http_root } ',0,''),
           ('',0,''),
           ('${mpx.properties.HTTP_ROOT} ${mpx.properties.HTTP_ROOT} ',1,'')
           )
    def _test(self,test,flag,msg):
        m = re.match(pattern,test)
        result = 0
        if m:
            result = 1
            #print '\"%s\"'%test
            #print m.groups()
            #while m:
            #    s = '%s%s'%(m.groups()[0],eval(m.groups()[2]))
            #    test = re.sub(pattern,s,test)
            #    m = re.match(pattern,test)
             
        if flag != result:
            self.fail('No match found for %s:"%s"' % (msg,test))        
    def test_1(self):
        t,f,m = self.test[0]
        self._test(t,f,m)
    def test_2(self):
        t,f,m = self.test[1]
        self._test(t,f,m)
    def test_3(self):
        t,f,m = self.test[2]
        self._test(t,f,m)    
    def test_4(self):
        t,f,m = self.test[3]
        self._test(t,f,m)
    def test_5(self):
        t,f,m = self.test[4]
        self._test(t,f,m)
    def test_6(self):
        t,f,m = self.test[5]
        self._test(t,f,m)
    def test_7(self):
        t,f,m = self.test[6]
        self._test(t,f,m)
    def test_8(self):
        t,f,m = self.test[7]
        self._test(t,f,m)
    def test_9(self):
        t,f,m = self.test[8]
        self._test(t,f,m)
    def test_10(self):
        t,f,m = self.test[9]
        self._test(t,f,m)
    def test_11(self):
        t,f,m = self.test[10]
        self._test(t,f,m)
    def test_12(self):
        t,f,m = self.test[11]
        self._test(t,f,m)
    def test_13(self):
        t,f,m = self.test[12]
        self._test(t,f,m)


#test =  (
#           ('${mpx.properties.HTTP_ROOT}',0,'beginnig of line test'),
#           (' ${mpx.properties.HTTP_ROOT}',0,'space before '),
#           (' sadfsaasdf sdfsad \${mpx.properties.HTTP_ROOT}',0,'words then a slash'),
#           (' \${mpx.properties.HTTP_ROOT}',0,'space then a slash'),
#           ('some test ${mpx.properties.HTTP_ROOT} ',1,''),
#           ('      ${mpx.properties.HTTP_ROOT} ',1,''),
#           ('\${mpx.properties.HTTP_ROOT} ${mpx.properties.HTTP_ROOT} ',1,''),
#           ('${mpx.properties.HTTP_ROOT} \${mpx.properties.HTTP_ROOT} ',1,''),
#           ('${mpx.properties.HTTP_ROOT } ',0,''),
#           ('${mpx.properties.http_root} ',0,''),
#           ('${mpx.properties.http_root } ',0,''),
#           ('',0,''),
#           ('${mpx.properties.HTTP_ROOT} ${mpx.properties.HTTP_ROOT} ',1,'')
#           )

#index = 1

#for t in test:
#    f = lambda self:self._test("%s,%s,%s" % (t[0],t[1],t[2]))  
#    function_name = 'test_%s' % index
#    print function_name
#    print t[0]
#    setattr(TestCase,'test_%s' % index,f)
#    index += 1
#    f = None
    
if(__name__ == '__main__'):    
    main()

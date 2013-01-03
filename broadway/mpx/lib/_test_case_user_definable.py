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
from mpx_test import DefaultTestFixture, main
from mpx.lib.user_definable import factory

_configure = {'name':'test','parent':'tp',
              'factory':'mpx.lib._test_case_user_definable.TestNode',
              'attributes':[{'name':'attr1','definition':'attr 1'},
                            {'name':'attr2','definition':'attr 2'}]}

class TestNode:
    def __init__(self):
        self._state = 'initialized'
    def configure(self,config):
        assert config['name'] == 'test','Name not passed in correctly'
        assert config['parent'] == 'tp','Wrong parent passed in'
        assert config['attr1'] == 'attr 1','Attribute 1 not passed in'
        assert config['attr2'] == 'attr 2','Attribute 2 not passed in'
        self._state = 'configured'
    def configuration(self):
        config = {'name':'test','parent':'tp',
                  'attr1':'attr 1','attr2':'attr 2'}
        return config
    def get(self, skipCache=0):
        return 1
    def start(self):
        pass
class TestCase(DefaultTestFixture):
    def setUp(self):
        self._chimera = factory()
        self._chimera.configure(_configure)
    def tearDown(self):
        del(self._chimera)
    def test_configure(self):
        self.failUnless(self._chimera._state == 'configured',
                        'Did not configure correctly')
    def test_configuration(self):
        for name,value in self._chimera.configuration().items():
            if name is not 'attributes':
                self.failUnless(value == _configure[name],'Bad configuration')
            else:
                self.failUnless(len(value) == len(_configure['attributes']),
                                'Attributes wrong length')
    def test_get(self):
        self.failUnless(self._chimera.get == self._chimera._node.get,
                        'Chimera failed to copy over callable attribute')
    
if __name__ == '__main__':
    main()

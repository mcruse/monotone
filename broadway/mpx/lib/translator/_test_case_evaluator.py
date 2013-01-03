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
from mpx_test import DefaultTestFixture

import math

from evaluator import Converter
from evaluator import Evaluator

from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.node import CompositeNode

class ConstantNode(CompositeNode):
    def __init__(self):
        self.value = None
        return
    def configure(self,cd):
        CompositeNode.configure(self,cd)
        set_attribute(self,'value',self.value,cd)
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self,'value',cd,str)
        return cd
    def get(self,*args):
        return self.value
    def set(self,value,*args):
        self.value = value
        return

def e_factory(name='test',parent=None,variables=None,statement='None', **kw):
    e = Evaluator()    
    cd = {'name':name,
          'parent':parent,
          'variables':variables,
          'statement':statement,
          }
    cd.update(kw)
    e.configure(cd)
    return e

def c_factory(name='test',parent=None,value=None,statement='None', **kw):
    c = Converter()    
    cd = {'name':name,
          'parent':parent,
          'value':value,
          'statement':statement,
          }
    cd.update(kw)
    c.configure(cd)
    return c

class TestCase(DefaultTestFixture):
    def test_1_instantiate(self):
        Evaluator()
        return
    def test_2_simpleevals(self):
        e = e_factory(variables=[{'node_reference':'1', 'vn':'one'},],
                      statement='one')
        e.start()
        assert e.get() == '1'
        e = e_factory(variables=[{'node_reference':'1', 'vn':'one'},],
                      statement='int(one)')
        e.start()
        assert e.get() == 1
        e = e_factory(variables=[{'node_reference':'1', 'vn':'one'},
                                 {'node_reference':'2', 'vn':'two'}],
                      statement='one+two')
        e.start()
        assert e.get() == '12'
        e = e_factory(variables=[{'node_reference':'1', 'vn':'one'},
                                 {'node_reference':'2', 'vn':'two'}],
                      statement='int(one)+int(two)')
        e.start()
        assert e.get() == 3
        return
    def test_3_nodeevals(self):
        pie = ConstantNode()
        pie.configure({'name':'pie','parent':None,'value':math.pi})
        e = e_factory(variables=[{'node_reference':pie, 'vn':'one'},],
                      statement='one')
        e.start()
        assert e.get() == math.pi
        pie.set('hello')
        assert e.get() == 'hello'
        pie.set({'int':3,'str':'three'})
        e = e_factory(variables=[{'node_reference':pie, 'vn':'enum'},],
                      statement='enum["str"]')
        assert e.get() == 'three'
        e = e_factory(variables=[{'node_reference':pie, 'vn':'enum'},],
                      statement='enum["int"]')
        assert e.get() == 3
        return
    def test_4_converter(self):
        enum = ConstantNode()
        enum.configure({'name':'enum','parent':None,'value':{
                    'int':1,'str':'one', 'float':1.0
                    }})
        c = c_factory(value=enum,statement='value["str"]')
        assert c.get() == 'one'
        class MockBACNetEnum:
            def __init__(self,text,value):
                self.__str=text
                self.__int=int(value)
                return
            def __repr__(self):
                return repr({'str':self.__str, 'int':self.__int})
            def __str__(self):
                return self.__str
            def __int__(self):
                return self.__int
        enum=MockBACNetEnum('foo',2)
        c = c_factory(value=enum,statement='str(value)')
        assert c.get() == 'foo'
        c = c_factory(value=enum,statement='int(value)')
        assert c.get() == 2
        return


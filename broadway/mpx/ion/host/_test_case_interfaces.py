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
import os

from mpx_test import DefaultTestFixture, main

from mpx.lib import factory
from mpx.lib.node import CompositeNode, as_node_url

def _dump_cd(n,d=None):
    if d is None:
        d = {}
    d[as_node_url(n)]=n.configuration()
    if hasattr(n, 'children_nodes'):
        l = n.children_names()
        l.sort()
        for cname in l:
            c = n.get_child(cname)
            _dump_cd(c,d)
    return d

class TestCase(DefaultTestFixture):
    def _helper_test_interfaces(self, name):
        F = 'mpx.ion.host.mediator_%s' % name
        host = factory(F)
        n = CompositeNode()
        n.configure({'name':name, 'parent':None})
        host.configure({'name':'interfaces', 'parent':n})
        _dump_cd(n) # Compare this...
        return
    def test_s1(self):
        self._helper_test_interfaces('s1')
        return
    def test_1200(self):
        self._helper_test_interfaces('1200')
        return
    def test_1500(self):
        self._helper_test_interfaces('1500')
        return
    def test_2400(self):
        self._helper_test_interfaces('2400')
        return
    def test_2500(self):
        self._helper_test_interfaces('2500')
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()


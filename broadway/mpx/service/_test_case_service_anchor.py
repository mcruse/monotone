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

import mpx.lib # Bootstraping...

from mpx.service import _Anchor

class TestCase(DefaultTestFixture):
    ##
    # Ensure that the _Anchor() node that impliments the '/services'
    # node can be instantiated and that it includes all of the
    # required implicit children:  'garbage_collector', 'session_manager',
    #                              'time' and 'User Manager'
    #
    # This test also will fail if there are unexpected implicit children.
    # @note The actual '/services' factory uses a singleton.  This
    #       should be investigated as it limits the ease of assembling and
    #       desctroying complete namespaces.
    # @note Currently the implicit children are hard coded in the _Acnhor
    #       class.  It would be good to establish a mechanism for
    #       "applications" to register implicit children, allowing for more
    #       flexibility.
    def test_new(self):
        service_anchor = _Anchor()
        children_names = service_anchor.children_names()
        # Verify that the implicit children exists...
        implicit_children = ['garbage_collector', 'session_manager',
                             'User Manager', 'Subscription Manager', 'time',
                             'Interactive Service']
        for child in children_names:
            if child in implicit_children:
                implicit_children.remove(child)
            else:
                raise ("Unexpected implicit child %r, please fix which ever"
                       " is broken, this test case, or"
                       " mpx.service._Anchor") % child
        if implicit_children:
            if len(implicit_children) == 1:
                text = "child"
                value = implicit_children[0]
            else:
                text = "children"
                value = ""
                while implicit_children:
                    child = implicit_children.pop(0)
                    value += child
                    if implicit_children:
                        value += ", "
            raise "Missing implicit %s %s." % (text, value)
        return

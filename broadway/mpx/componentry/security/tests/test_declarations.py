"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.componentry import query_multi_adapter
from mpx.componentry.security import SecurityInformation
from mpx.componentry.security import secured_by
from mpx.componentry.security import ISecure
from mpx.lib.exceptions import Forbidden
from mpx.lib.exceptions import Unauthorized
from mpx.lib.neode.node import CompositeNode

class Node(CompositeNode):
    security = SecurityInformation()
    secured_by(security)
    security.make_public('show_name')
    def show_name(self):
        print self.name
    security.protect('get_name', 'View')
    def get_name(self):
        return self.name
    security.protect('set_name', 'Override')
    def set_name(self, name):
        self.name = name

from mpx.lib.node import as_node
try:
    test = as_node('/services/Security Test')
except KeyError:
    test = CompositeNode()
    test.configure({'name': 'Security Test', 'parent': '/services'})

try:
    node = as_node('/services/Security Test/Node')
except KeyError:
    node = Node()
    node.configure({'name': 'Node', 'parent': test})

sm = as_node('/services/Security Manager')
securednodes = []
assecurednodes = []
users = sm.user_manager.get_users()
for user in users:
    securednodes.append(query_multi_adapter((node, user), ISecure))
    assecurednodes.append(sm.as_secured_node('/services/Security Test/Node', user))

node1a = securednodes[5]
node1b = assecurednodes[5]
node1a.show_name()
node1b.show_name()
node1a.get_name()
node1b.get_name()
node1a.set_name('Node Renamed 2')
node1b.set_name('Node Renamed 2')


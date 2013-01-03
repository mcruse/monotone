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
from mpx.componentry.tests import verify_class
from mpx.lib.neode.interfaces import INode
from mpx.lib.neode.interfaces import IChildNode
from mpx.lib.neode.interfaces import IParentNode
from mpx.lib.neode.interfaces import IGettable
from mpx.lib.neode.interfaces import ISettable
from mpx.lib.neode.interfaces import IInspectable
from mpx.lib.neode.interfaces import IModifiable
from mpx.lib.neode.interfaces import IConfigurable
from mpx.lib.neode.interfaces import IEnableAble
from mpx.lib.neode.interfaces import IRunnable
from mpx.lib.neode.interfaces import INodeSpace
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.neode.interfaces import IDeferredNode
from mpx.lib.neode.interfaces import IService
from mpx.lib.neode.interfaces import IRootNode
from mpx.lib.neode.interfaces import IAlias
from mpx.lib.neode.interfaces import IAliases
from mpx.lib.neode.node import NodeSpace
from mpx.lib.neode.node import ConfigurableNode
from mpx.lib.neode.node import CompositeNode
from mpx.lib.neode.node import RootNode

assert verify_class(INode, ConfigurableNode), 'fails interface verify'
assert verify_class(IChildNode, ConfigurableNode), 'fails interface verify'
assert verify_class(IInspectable, ConfigurableNode), 'fails interface verify'
assert verify_class(IModifiable, ConfigurableNode), 'fails interface verify'
assert verify_class(IConfigurable, ConfigurableNode), 'fails interface verify'
assert verify_class(IEnableAble, ConfigurableNode), 'fails interface verify'
assert verify_class(IRunnable, ConfigurableNode), 'fails interface verify'
assert verify_class(IConfigurableNode, ConfigurableNode), 'fails interface verify'

assert verify_class(INode, CompositeNode), 'fails interface verify'
assert verify_class(IChildNode, CompositeNode), 'fails interface verify'
assert verify_class(IParentNode, CompositeNode), 'fails interface verify'
assert verify_class(IInspectable, CompositeNode), 'fails interface verify'
assert verify_class(IModifiable, CompositeNode), 'fails interface verify'
assert verify_class(IConfigurable, CompositeNode), 'fails interface verify'
assert verify_class(IEnableAble, CompositeNode), 'fails interface verify'
assert verify_class(IRunnable, CompositeNode), 'fails interface verify'
assert verify_class(IConfigurableNode, CompositeNode), 'fails interface verify'
assert verify_class(ICompositeNode, CompositeNode), 'fails interface verify'

assert verify_class(INode, RootNode), 'fails interface verify'
assert verify_class(IChildNode, RootNode), 'fails interface verify'
assert verify_class(IParentNode, RootNode), 'fails interface verify'
assert verify_class(IInspectable, RootNode), 'fails interface verify'
assert verify_class(IModifiable, RootNode), 'fails interface verify'
assert verify_class(IConfigurable, RootNode), 'fails interface verify'
assert verify_class(IEnableAble, RootNode), 'fails interface verify'
assert verify_class(IRunnable, RootNode), 'fails interface verify'
assert verify_class(IConfigurableNode, RootNode), 'fails interface verify'
assert verify_class(ICompositeNode, RootNode), 'fails interface verify'
assert verify_class(IRootNode, RootNode), 'fails interface verify'

assert verify_class(INodeSpace, NodeSpace), 'fails interface verify'

nodespace = NodeSpace()
root = nodespace.create_node(RootNode)
root.configure({'name': '/', 'parent': None})

services = nodespace.create_node(CompositeNode)
services.configure({'parent': root, 'name': 'services'})
am = nodespace.create_node(CompositeNode)
am.configure({'parent': services, 'name': 'Alarm Manager'})

io = nodespace.create_node(CompositeNode)
io.configure({'parent': root, 'name': 'interfaces'})

aliases = nodespace.create_node(CompositeNode)
aliases.configure({'parent': root, 'name': 'aliases'})


from mpx.www.w3c.dom.interfaces import IDomNode
from mpx.www.w3c.dom.interfaces import IDomDocument
from mpx.www.w3c.dom.interfaces import IDomElement
from mpx.lib.neode.framework.node.dom.adapters import DomConfigurableNode
from mpx.lib.neode.framework.node.dom.adapters import DomCompositeNode
from mpx.lib.neode.framework.node.dom.adapters import DomDocument
from mpx.lib.neode.framework.node.dom.adapters import DomSpaceDocument
from mpx.lib.neode.framework.node.dom.adapters import DomElement

assert verify_class(IDomNode, DomConfigurableNode), 'fails interface verify'
assert verify_class(IDomNode, DomCompositeNode), 'fails interface verify'
assert verify_class(IDomDocument, DomDocument), 'fails interface verify'
assert verify_class(IDomDocument, DomSpaceDocument), 'fails interface verify'
assert verify_class(IDomElement, DomElement), 'fails interface verify'

domroot = IDomDocument(root)
am = domroot.firstChild.firstChild

domroot.getElementsByTagName('services')

from xml.dom import ext
ext.Print(domroot)

from mpx.lib.neode.framework.node.html import adapters
from mpx.www.w3c.xhtml.interfaces import IWebContent
domweb = IWebContent(domroot)



file = open('/var/www/sgreen/dev/output/domweb.html', 'w')
file.write(domweb.render())
file.close()

print domweb.render()




domservices = IDomElement(services)
sweb = IWebContent(domservices)
file = open('/var/www/sgreen/dev/output/sweb.html', 'w')
file.write(sweb.render())
file.close()

print sweb.render()






domroot.firstChild.removeChild(am)
assert am.node.parent is None, 'Did not clear parent!'
assert am.parentNode is None, 'Did not clear parent!'
















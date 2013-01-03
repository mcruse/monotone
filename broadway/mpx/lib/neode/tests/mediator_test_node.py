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
from mpx.lib.neode.dom.adapters import DomConfigurableNode
from mpx.lib.neode.dom.adapters import DomCompositeNode
from mpx.lib.neode.dom.adapters import DomDocument
from mpx.lib.neode.dom.adapters import DomSpaceDocument
from mpx.lib.neode.dom.adapters import DomElement

domroot = IDomDocument(root)
am = domroot.firstChild.firstChild

domroot.getElementsByTagName('services')

from mpx.lib.neode.html import adapters
from mpx.www.w3c.xhtml.interfaces import IWebContent
domweb = IWebContent(domroot)

print domweb.render()




domservices = IDomElement(services)
sweb = IWebContent(domservices)
print sweb.render()






domroot.firstChild.removeChild(am)
assert am.node.parent is None, 'Did not clear parent!'
assert am.parentNode is None, 'Did not clear parent!'



class InterfaceA(Interface): pass


class AdaptsConfigurable(object):
    implements(InterfaceA)
    adapts(IConfigurableNode)


register_adapter(AdaptsConfigurable)


class AdaptsComposite(object):
    implements(InterfaceA)
    adapts(ICompositeNode)


register_adapter(AdaptsComposite)











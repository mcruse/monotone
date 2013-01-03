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
import string
from xml import dom
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.www.w3c.dom.interfaces import IDomNode
from mpx.www.w3c.dom.interfaces import IDomDocument
from mpx.www.w3c.dom.interfaces import IDomElement
from mpx.www.w3c.dom.interfaces import IDomNodeList
from mpx.www.w3c.dom.bases import DomNodeList
from mpx.lib.neode.interfaces import INodeSpace
from mpx.lib.neode.interfaces import IRootNode
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.neode.interfaces import IGettable
from _utilities import AttrNodeMap, AttrNode

class DomConfigurableNode(object):
    __doc__ = IDomNode.__doc__

    implements(IDomNode)
    adapts(IConfigurableNode)

    def __init__(self, node):
        self.node = node
        self._type = dom.Node.ELEMENT_NODE
        super(DomConfigurableNode, self).__init__(node)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_node_class(self):
        return type(self.node)
    nodeClass = property(__get_node_class)

    def __get_node_classname(self):
        klass = self.nodeClass
        return string.join((klass.__module__, klass.__name__), '.')
    nodeClassName = property(__get_node_classname)

    def __get_node_id(self):
        return self.node.url
    nodeID = property(__get_node_id)

    def __get_node_type(self):
        return self._type
    nodeType = property(__get_node_type)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_parent_node(self):
        if self.node.parent is None:
            return None
        try: parent = IDomNode(self.node.parent)
        except TypeError, error:
            print 'IDomNode(node.parent) failed: ' + str(error)
            print '\treturning None for parent.'
            parent = None
        return parent
    parentNode = property(__get_parent_node)

    def __get_owner_document(self):
        return IDomDocument(self.node.nodespace)
    ownerDocument = property(__get_owner_document)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_attributes(self):
        config = self.node.configuration()
        config.setdefault('class', self.nodeClassName)
        config.setdefault('id', self.nodeID)
        if self.parentNode is not None:
            config['parent'] = self.parentNode.nodeID
        return AttrNodeMap.from_dict(config)
    attributes = property(__get_attributes)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_previous_sibling(self):
        if self.node.parent is None:
            return None
        index = self.node.parent.get_index(self.node)
        if index == 0: return None
        sibling_name = self.node.parent.children_names()[index - 1]
        return IDomNode(self.node.parent.get_child(sibling_name))
    previousSibling = property(__get_previous_sibling)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_next_sibling(self):
        if self.node.parent is None:
            return None
        index = self.node.parent.get_index(self.node)
        names = self.node.parent.children_names()
        sibling_index = index + 1
        if sibling_index >= len(names): return None
        sibling_name = names[sibling_index]
        return IDomNode(self.node.parent.get_child(sibling_name))
    nextSibling = property(__get_next_sibling)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_local_name(self):
        return self.node.name
    localName = property(__get_local_name)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_prefix(self):
        if self.node.parent is None:
            return None
        return self.node.parent.url
    prefix = property(__get_prefix)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_namespace_uri(self):
        return None
    namespaceURI = property(__get_namespace_uri)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_node_name(self):
        return self.node.name
    nodeName = property(__get_node_name)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_node_value(self):
        if IGettable.providedBy(self.node):
            return self.node.get()
        return
    nodeValue = property(__get_node_value)

    def hasAttributes(self):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        return True

    def isSameNode(self, other):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        if type(other) is type(self):
            other = other.node
        return self.node.get_nodespace().as_node(other) is self.node

    def normalize(self):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        raise Exception("Function not implemented.")

    def cloneNode(self, deep):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        raise Exception("Function not implemented.")

    childNodes = []
    firstChild = None
    lastChild = None
    def hasChildNodes(self):
        return False
    def appendChild(self, newChild):
        raise Exception('Invalid operation on ConfigurableNode.')
    def insertBefore(self, newChild, refChild):
        raise Exception('Invalid operation on ConfigurableNode.')
    def removeChild(self, oldChild):
        raise Exception('Invalid operation on ConfigurableNode.')
    def replaceChild(self, newChild, oldChild):
        raise Exception('Invalid operation on ConfigurableNode.')

register_adapter(DomConfigurableNode)

class DomCompositeNode(DomConfigurableNode):
    __doc__ = IDomNode.__doc__

    # implements(IDomNode)
    adapts(ICompositeNode)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_child_nodes(self):
        children = self.node.children_nodes()
        return map(IDomNode, children)
    childNodes = property(__get_child_nodes)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_first_child(self):
        child = self.node.get_child(self.node.children_names()[0])
        return IDomNode(child)
    firstChild = property(__get_first_child)

    # See mpx.www.w3c.dom.interfaces.IDomNode
    def __get_last_child(self):
        child = self.node.get_child(self.node.children_names()[-1])
        return IDomNode(child)
    lastChild = property(__get_last_child)

    def hasChildNodes(self):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        return len(self.node.children_nodes()) and True

    def appendChild(self, newChild):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        if type(newChild) is type(self):
            newChild = newChild.node
        self.node.add_child(newChild)

    def insertBefore(self, newChild, refChild):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        if type(newChild) is type(self):
            newChild = newChild.node
        if type(refChild) is type(self):
            refChild = refChild.node
        location = None
        if refChild is not None:
            location = self.node.get_index(refChild)
        self.node.add_child(newChild, location)

    def removeChild(self, oldChild):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        if type(oldChild) is type(self):
            oldChild = oldChild.node
        oldChild.prune()

    def replaceChild(self, newChild, oldChild):
        "See mpx.www.w3c.dom.interfaces.IDomNode"
        if type(newChild) is type(self):
            newChild = newChild.node
        if type(oldChild) is type(self):
            oldChild = oldChild.node
        location = self.node.get_index(oldChild)
        self.removeChild(oldChild)
        self.node.add_child(newChild, location)

class DomElement(DomCompositeNode):
    """
        Element is a subclass of Node, so inherits all
        the attributes of that class.
    """
    implements(IDomElement)
    # adapts(ICompositeNode)

    tagName = DomCompositeNode.localName

    def getElementsByTagName(self, tagName):
        nodes = self.node.descendants_nodes()
        nodes = [node for node in nodes if node.name == tagName]
        return DomNodeList(map(IDomElement, nodes))

    def getElementsByTagNameNS(self, namespaceURI, tagName):
        tagName = string.join([namespaceURI,tagName], ':')
        return self.getElementsByTagName(tagName)

    def hasAttribute(self, name):
        return self.node.configuration().has_key(name)

    def hasAttributeNS(self, namespaceURI, localName):
        name = string.join([namespaceURI,localName], ':')
        return self.hasAttribute(name)

    def getAttribute(self, name):
        return str(self.node.configuration().get(name, ''))

    def getAttributeNode(self, attrname):
        return AttrNode(attrname, self.getAttribute(attrname))

    def getAttributeNS(self, namespaceURI, localName):
        name = string.join([namespaceURI,localName], ':')
        return self.getAttribute(name)

    def getAttributeNodeNS(self, namespaceURI, localName):
         name = string.join([namespaceURI,localName], ':')
         return self.getAttributeNode(name)

    def removeAttribute(self, name):
        raise Exception("Not yet supported.")

    def removeAttributeNode(self, oldAttr):
        raise Exception("Not yet supported.")

    def removeAttributeNS(self, namespaceURI, localName):
        raise Exception("Not yet supported.")

    def setAttribute(self, name, value):
        config = self.node.configuration()
        config[name] = value
        self.node.configure(config)

    def setAttributeNode(self, newAttr):
        self.setAttribute(newAttr.name, newAttr.value)

    def setAttributeNodeNS(self, newAttr):
        self.setAttributeNode(newAttr)

    def setAttributeNS(self, namespaceURI, qname, value):
        name = string.join([namespaceURI,localName], ':')
        self.setAttribute(name, value)

register_adapter(DomElement, [ICompositeNode], IDomElement)

class DomDocument(DomElement):
    __doc__ = IDomDocument.__doc__

    implements(IDomDocument)
    adapts(IRootNode)

    def __init__(self, node):
        super(DomDocument, self).__init__(node)
        self._type = dom.Node.DOCUMENT_NODE

    # See mpx.www.w3c.dom.interfaces.IDomDocument
    def __get_document_element(self):
        # Root is this object's node.
        return IDomNode(self.node)
    documentElement = property(__get_document_element)

    def __get_nodespace(self):
        return self.node.get_nodespace()
    nodespace = property(__get_nodespace)

    def getElementById(self, id):
        """
            ID is the node URL.
        """
        return IDomNode(self.nodespace.as_node(id))

    def createElement(self, tagName):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")
    def createElementNS(self, namespaceURI, tagName):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")
    def createTextNode(self, data):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")
    def createComment(self, data):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")
    def createProcessingInstruction(self, target, data):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")
    def createAttribute(self, name):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")
    def createAttributeNS(self, namespaceURI, qualifiedName):
        "See mpx.www.w3c.dom.interfaces.IDomDocument"
        raise Exception("Not implemented")

register_adapter(DomDocument, [IRootNode], IDomDocument)

class DomSpaceDocument(DomDocument):
    adapts(INodeSpace)

    def __init__(self, nodespace):
        super(DomSpaceDocument, self).__init__(nodespace.root)

register_adapter(DomSpaceDocument, [INodeSpace], IDomDocument)









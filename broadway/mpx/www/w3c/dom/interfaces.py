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
from mpx.componentry import Interface, Attribute

class IDomNode(Interface):
    """
        All of the components of an XML document are subclasses of Node.
    """
    
    nodeType = Attribute(
        """
            An integer representing the node type. Symbolic constants for 
            the types are on the Node object: ELEMENT_NODE, ATTRIBUTE_NODE, 
            TEXT_NODE, CDATA_SECTION_NODE, ENTITY_NODE, 
            PROCESSING_INSTRUCTION_NODE, COMMENT_NODE, DOCUMENT_NODE, 
            DOCUMENT_TYPE_NODE, NOTATION_NODE. This is a read-only attribute.
        """) 
    
    nodeClass = Attribute(
        """
            Reference to actual node class object.
        """)
    
    nodeClassName = Attribute(
        """
            Fully-qualified class name; dot-separated.
        """) 
    
    nodeID = Attribute(
        """
            Full Node URL.
        """)
    
    parentNode = Attribute(
        """
            The parent of the current node, or None for the document node. 
            The value is always a Node object or None. For Element nodes, 
            this will be the parent element, except for the root element, 
            in which case it will be the Document object. For Attr nodes, 
            this is always None. This is a read-only attribute.
        """) 
    
    attributes = Attribute(
        """
            A NamedNodeMap of attribute objects. Only elements have actual 
            values for this; others provide None for this attribute. 
            This is a read-only attribute.
        """) 
    
    previousSibling = Attribute(
        """
            The node that immediately precedes this one with the same parent. 
            For instance the element with an end-tag that comes just before 
            the self element's start-tag. Of course, XML documents are made 
            up of more than just elements so the previous sibling could be 
            text, a comment, or something else. If this node is the first 
            child of the parent, this attribute will be None. 
            This is a read-only attribute.
        """) 
    
    nextSibling = Attribute(
        """
            The node that immediately follows this one with the same parent. 
            See also previousSibling. If this is the last child of the parent, 
            this attribute will be None. This is a read-only attribute.
        """) 
    
    childNodes = Attribute(
        """
            A list of nodes contained within this node. 
            This is a read-only attribute.
        """)
    
    firstChild = Attribute(
        """
            The first child of the node, if there are any, or None. 
            This is a read-only attribute.
        """) 
    
    lastChild = Attribute(
        """
            The last child of the node, if there are any, or None. 
            This is a read-only attribute.
        """) 
    
    localName = Attribute(
        """
            The part of the tagName following the colon if there is one, 
            else the entire tagName. The value is a string.
        """)
    
    prefix = Attribute(
        """
            The part of the tagName preceding the colon if there is one, 
            else the empty string. The value is a string, or None
        """) 
    
    namespaceURI = Attribute(
        """
            The namespace associated with the element name. This will be a 
            string or None. This is a read-only attribute.
        """) 
    
    nodeName = Attribute(
        """
            This has a different meaning for each node type; see the DOM 
            specification for details. You can always get the information 
            you would get here from another property such as the tagName 
            property for elements or the name property for attributes. 
            For all node types, the value of this attribute will be 
            either a string or None. This is a read-only attribute.
        """) 
    
    nodeValue = Attribute(
        """
            This has a different meaning for each node type; see the DOM 
            specification for details. The situation is similar to 
            that with nodeName. The value is a string or None.
        """) 
    
    def hasAttributes():
        """
            Returns true if the node has any attributes.
        """ 
    
    def hasChildNodes():
        """
            Returns true if the node has any child nodes.
        """ 
    
    def isSameNode(other):
        """
            Returns true if other refers to the same node as this node. 
            This is especially useful for DOM implementations which use 
            any sort of proxy architecture, because more than one 
            object can refer to the same node.
            
            Note: This is based on a proposed DOM Level 3 API which is still 
            in the ``working draft'' stage, but this particular interface 
            appears uncontroversial. Changes from the W3C will not necessarily 
            affect this method in the Python DOM interface 
            (though any new W3C API for this would also be supported).
        """
    
    def appendChild(newChild):
        """
            Add a new child node to this node at the end of the 
            list of children, returning newChild.
        """ 
    
    def insertBefore(newChild, refChild):
        """
            Insert a new child node before an existing child. It must be the 
            case that refChild is a child of this node; if not, ValueError is 
            raised. newChild is returned. If refChild is None, it inserts 
            newChild at the end of the children's list.
        """ 
    
    def removeChild(oldChild):
        """
            Remove a child node. oldChild must be a child of this node; 
            if not, ValueError is raised. oldChild is returned on success. 
            If oldChild will not be used further, its unlink() 
            method should be called.
        """ 
    
    def replaceChild(newChild, oldChild):
        """
            Replace an existing node with a new node. It must be the case 
            that oldChild is a child of this node; if not, 
            ValueError is raised.
        """ 
    
    def normalize():
        """
            Join adjacent text nodes so that all stretches of text are stored 
            as single Text instances. This simplifies processing text from a 
            DOM tree for many applications. New in version 2.1.
        """ 
    
    def cloneNode(deep):
        """
            Clone this node. Setting deep means to clone all child 
            nodes as well. This returns the clone.
        """

class IDomElement(IDomNode):
    """
        Element is a subclass of Node, so inherits all 
        the attributes of that class.
    """
    
    tagName = Attribute(
        """
            The element type name. In a namespace-using document it may have 
            colons in it. The value is a string.
        """) 
    
    def getElementsByTagName(tagName):
        """
            Same as equivalent method in the Document class.
        """ 
    
    def getElementsByTagNameNS(namespaceURI, tagName):
        """
            Same as equivalent method in the Document class.
        """ 
    
    def hasAttribute(name):
        """
            Returns true if the element has an attribute named by name.
        """ 
    
    def hasAttributeNS(namespaceURI, localName):
        """
            Returns true if the element has an attribute named by 
            namespaceURI and localName.
        """
    
    def getAttribute(name):
        """
            Return the value of the attribute named by name as a string. 
            If no such attribute exists, an empty string is returned, 
            as if the attribute had no value.
        """ 
    
    def getAttributeNode(attrname):
        """
            Return the Attr node for the attribute named by attrname.
        """ 
    
    def getAttributeNS(namespaceURI, localName):
        """
            Return the value of the attribute named by namespaceURI 
            and localName as a string. If no such attribute exists, 
            an empty string is returned, as if the attribute had no value.
        """ 
    
    def getAttributeNodeNS(namespaceURI, localName):
        """
            Return an attribute value as a node, given a 
            namespaceURI and localName.
        """ 
    
    def removeAttribute(name):
        """
            Remove an attribute by name. No exception is raised if there 
            is no matching attribute.
        """ 
    
    def removeAttributeNode(oldAttr):
        """
            Remove and return oldAttr from the attribute list, if present. 
            If oldAttr is not present, NotFoundErr is raised.
        """ 
    
    def removeAttributeNS(namespaceURI, localName):
        """
            Remove an attribute by name. Note that it uses a localName, 
            not a qname. No exception is raised if there is no 
            matching attribute.
        """ 
    
    def setAttribute(name, value):
        """
            Set an attribute value from a string.
        """ 
    
    def setAttributeNode(newAttr):
        """
            Add a new attribute node to the element, replacing an existing 
            attribute if necessary if the name attribute matches. If a 
            replacement occurs, the old attribute node will be returned. 
            If newAttr is already in use, InuseAttributeErr will be raised.
        """ 
    
    def setAttributeNodeNS(newAttr):
        """
            Add a new attribute node to the element, replacing an existing 
            attribute if necessary if the namespaceURI and localName 
            attributes match. If a replacement occurs, the old attribute 
            node will be returned. If newAttr is already in use, 
            InuseAttributeErr will be raised.
        """ 
    
    def setAttributeNS(namespaceURI, qname, value):
        """
            Set an attribute value from a string, given a namespaceURI and 
            a qname. Note that a qname is the whole attribute name. 
            This is different than above.
        """ 

class IDomDocument(IDomNode):
    """
        A Document represents an entire XML document, including its 
        constituent elements, attributes, processing instructions, 
        comments etc. Remeber that it inherits properties from Node.
    """

    documentElement = Attribute(
        """
            The one and only root element of the document.
        """) 

    def createElement(tagName):
        """
            Create and return a new element node. The element is not 
            inserted into the document when it is created. You need to 
            explicitly insert it with one of the other methods such 
            as insertBefore() or appendChild().
        """ 

    def createElementNS(namespaceURI, tagName):
        """
            Create and return a new element with a namespace. The tagName 
            may have a prefix. The element is not inserted into the document 
            when it is created. You need to explicitly insert it with one of 
            the other methods such as insertBefore() or appendChild().
        """ 

    def createTextNode(data):
        """
            Create and return a text node containing the data passed as a 
            parameter. As with the other creation methods, this one does 
            not insert the node into the tree.
        """ 

    def createComment(data):
        """
            Create and return a comment node containing the data passed as 
            a parameter. As with the other creation methods, this one does 
            not insert the node into the tree.
        """ 

    def createProcessingInstruction(target, data):
        """
            Create and return a processing instruction node containing the 
            target and data passed as parameters. As with the other creation 
            methods, this one does not insert the node into the tree.
        """ 

    def createAttribute(name):
        """
            Create and return an attribute node. This method does not 
            associate the attribute node with any particular element. 
            You must use setAttributeNode() on the appropriate Element 
            object to use the newly created attribute instance.
        """ 

    def createAttributeNS(namespaceURI, qualifiedName):
        """
            Create and return an attribute node with a namespace. 
            The tagName may have a prefix. This method does not associate 
            the attribute node with any particular element. You must use 
            setAttributeNode() on the appropriate Element object to use 
            the newly created attribute instance.
        """ 

    def getElementsByTagName(tagName):
        """
            Search for all descendants: direct children, children's children, 
            etc., with a particular element type name.
        """ 

    def getElementsByTagNameNS(namespaceURI, localName):
        """
            Search for all descendants: direct children, children's children, 
            etc., with a particular namespace URI and localname. The 
            localname is the part of the namespace after the prefix.
        """

class IDomNodeList(Interface):
    """
        A NodeList represents a sequence of nodes. These objects are used in 
        two ways in the DOM Core recommendation: the Element objects provides 
        one as its list of child nodes, and the getElementsByTagName() and 
        getElementsByTagNameNS() methods of Node return objects with this 
        interface to represent query results.
        
        The DOM Level 2 recommendation defines one method and one 
        attribute for these objects.
    """
    
    length = Attribute(
        """
            The number of nodes in the sequence.
        """)
    
    def item(index):
        """
            Return the i'th item from the sequence, if there is one, or None. 
            The index i is not allowed to be less then zero or greater 
            than or equal to the length of the sequence.
        """
    
    def __getitem__(index):
        """
            In addition, the Python DOM interface requires that some 
            additional support is provided to allow NodeList objects 
            to be used as Python sequences. All NodeList implementations 
            must include support for __len__() and __getitem__(); 
            this allows iteration over the NodeList in for statements 
            and proper support for the len() built-in function.
        """
    
    def __len__():
        """
            See __getitem__.
        """
    
    def __setitem__(index, value):
        """
            If a DOM implementation supports modification of the document, 
            the NodeList implementation must also support the 
            __setitem__() and __delitem__() methods.
        """
    
    def __delitem__(index):
        """
            See __setitem__.
        """
 
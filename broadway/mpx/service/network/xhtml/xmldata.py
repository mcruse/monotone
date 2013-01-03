"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import cgi
from xml.dom import minidom
from mpx.lib import msglog
from mpx.lib.node import CompositeNode

class XMLDataNode(CompositeNode):
    def __init__(self, *args, **kw):
        self.xmldata = ''
        self.domdocument = None
        self.elementnode = None
        super(XMLDataNode, self).__init__(*args, **kw)
    def start(self):
        if not self.has_child('Element Node'):
            self.elementnode = ElementNode()
            self.elementnode.configure(
                {'name': 'Element Node', 'parent': self})
        else:
            self.elementnode = self.get_child('Element Node')
        super(XMLDataNode, self).start()
    def setValue(self, xmldata):
        self.domdocument = minidom.parseString(xmldata)
        self.elementnode.setValue(self.domdocument.documentElement)
        if isinstance(xmldata, unicode):
            xmldata = xmldata.encode('utf-8')
        self.xmldata = xmldata
    def getValue(self):
        return self.xmldata
    def set(self, xmldata):
        return self.setValue(xmldata)
    def get(self, escaped = True):
        xmldata = self.getValue()
        if escaped:
            xmldata = repr(xmldata)
        return xmldata

class ElementNode(CompositeNode):
    def __init__(self, *args):
        self.debug = 0
        self.element = None
        # Many elements of same name can share 
        # parent in XML documents.  The FW, 
        # however, requires that all nodes have 
        # a unique name within the set of nodes 
        # sharing that parent...all a node's children 
        # must have a unique name.
        # To DOM implementation to the FW implementations, 
        # the name given to a particular node includes 
        # the count of that particular element within its parent.
        self.nodeName = None
        self.nodeNumber = None
        self.dataNodes = []
        self.nodeGroups = {}
        self.childNodes = []
        self.attributes = {}
        super(ElementNode, self).__init__(*args)
    def configure(self, config):
        self.debug = int(config.get('debug', self.debug))
        self.element = config.get('element', self.element)
        self.nodeNumber = config.get('number', self.nodeNumber)
        if not config.has_key('name'):
            name = self.element.localName
            if self.nodeNumber is not None:
                name = '%s[%04d]' % (name, self.nodeNumber)
            config['name'] = name.encode('UTF-8')
        super(ElementNode, self).configure(config)
    def configuration(self):
        config = super(ElementNode, self).configuration()
        config['debug'] = str(self.debug)
        if self.nodeNumber is not None:
            config['number'] = str(self.nodeNumber)
        config['attributes'] = str(self.attributes)
        return config
    def children_nodes(self):
        # Overridden to return ordered list of child nodes
        return list(self.childNodes)
    def get_children(self, childtype):
        """
            Returns only those children of type 'childtype.'
            A child's "type" is the tag name of the DOM element 
            from which the child was created.  These names 
            cannot be used directly because there may be many 
            children of a particular type under a given parent.
        """
        # Note this method is inneficient given that 'childGroups' 
        # already exists and provides the same data direclty.  It 
        # has been chosen to remain unattached to the existence of 
        # the childGroups attribute, as it's possibe it may go away.
        return [node for node in self.childNodes if node.nodeName == childtype]
    def children_types(self):
        return [group.encode('ascii') for group in self.nodeGroups.keys()]
    def setValue(self, element):
        self.element = element
        self.nodeName = element.nodeName
        self.localName = element.localName
        if not isinstance(self.parent, ElementNode):
            self.element.normalize()
            self.debugout('normalized %s', self.element)
        elements = []
        self.dataNodes = []
        self.childNodes = []
        for domnode in self.element.childNodes:
            self.debugout('analyzing child %s', domnode)
            if domnode.nodeType == self.element.ELEMENT_NODE:
                self.debugout('child %s is element', domnode)
                elements.append(domnode)
            elif domnode.nodeType == self.element.TEXT_NODE:
                self.debugout('child %s is data', domnode)
                self.dataNodes.append(domnode)
        nodegroups = {}
        for domelement in elements:
            self.debugout('creating group for %s', domelement)
            nodegroup = nodegroups.setdefault(domelement.localName, [])
            nodegroup.append(domelement)
        for name,elements in nodegroups.items():
            nodenumber = 0
            for element in elements:
                name = element.localName
                if len(elements) > 1:
                    name = '%s [%04d]' % (name, nodenumber)
                name = name.encode('utf-8')
                if self.has_child(name):
                    node = self.get_child(name)
                    self.debugout('updating %s with %s', node, element)
                else:
                    config = {'parent': self, 'name': name}
                    node = ElementNode()
                    node.configure(config)
                    self.debugout('child node %s created', node)
                node.setValue(element)
                self.childNodes.append(node)
                nodenumber = nodenumber + 1
        self.nodeGroups = nodegroups
        for node in self.children_nodes():
            if node not in self.childNodes:
                self.debugout('pruning node %s', node)
                node.prune()
        # Note workaround for Python bug - empty override of default 
        # NS via "xmlns=''" attribute results in attribute named 
        # "xmlns" with value of None, not empty string as it should be.
        # Tricky workaround uses 'or' in encoding of value to get empty 
        # string iff value would otherwise be None.
        attritems = [(name.encode('utf-8'),(value or '').encode('utf-8')) 
                     for (name,value) in self.element.attributes.items()]
        self.attributes = dict(attritems)
        self.debugout('set attributes to %s', self.attributes)
    def start(self):
        if self.element is not None:
            self.setValue(self.element)
        return super(ElementNode, self).start()
    def isdebug(self, level = 1):
        return self.debug >= level
    def debugout(self, message, *varargs, **kw):
        level = kw.get('level', 1)
        if self.isdebug(level):
            if varargs:
                message = message % varargs
            msglog.log('broadway', msglog.types.DB, 
                       '%s -> %s' % (self, message))
        return
    def get(self):
        data = ''.join([textnode.data for textnode in self.dataNodes])
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        return data.strip()
    def showtree(self, level = 0, indentby = 2):
        label = '%s%s' % (''.ljust(level * indentby), self.name)
        print '%s%r' % (label.ljust(50), self.get())
        for child in self.children_nodes():
            child.showtree(level + 1, indentby)
        print label
    def reprtree(self, level = 0, indentby = 2):
        label = '%s%r' % (''.ljust(level * indentby), self)
        print '%s%r' % (label.ljust(50), self.get())
        for child in self.children_nodes():
            child.reprtree(level + 1, indentby)
        print label
    def findElementNodes(self, elements):
        """
            Accepts list of elements and returns list of 
            corresponding node objects.  Allows things like 
            passing DOM query results to tree and retrieving of 
            associated nodes.
        """
        try:
            elements.remove(self.element)
        except ValueError:
            nodes = []
        else:
            nodes = [self]
        nodegroups = [child.findElementNodes(elements) 
                      for child in self.children_nodes()]
        map(nodes.extend, nodegroups)
        return nodes
    def reprSubTree(node, indentby = 2):
        parents = []
        while isinstance(node, ElementNode):
            parents.append(node)
            node = node.parent
        level = 0
        labels = []
        parents.reverse()
        for level in range(len(parents)):
            parent = parents[level]
            labels.append((''.ljust(level * indentby), parent.name))
        for label in labels:
            print '%s<%s>' % label
        parents[-1].reprtree(level, indentby)
        labels.reverse()
        for label in labels:
            print '%s</ %s>' % label
    reprSubTree = staticmethod(reprSubTree)
    def __str__(self):
        classname = type(self).__name__
        nodename = self.name
        return '%s: "%s"' % (classname, nodename)
    def __repr__(self):
        classname = type(self).__name__
        nodename = self.name
        attrs = ' '.join(
            ['%s="%s"' % attritem for attritem in self.attributes.items()])
        return '<%s %s %s at %#x>' % (classname, nodename, attrs, id(self))



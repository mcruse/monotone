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
"""
    Classes which build node-subtrees from SOAP data input.
"""
from SOAPpy import Types
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
DEBUG = False

class SimpleDataNode(CompositeNode):
    def __init__(self, *args, **kw):
        self.attributes = {}
        self.datatype = None
        self.nodename = None
        self.datavalue = None
        self.parentnode = None
        super(SimpleDataNode, self).__init__(*args, **kw)
    def isConfigured(self):
        return bool(self.parent and self.name)
    def setParent(self, parent):
        if parent is not self.getParent():
            assert not self.isConfigured()
            self.parentnode = parent
        if self.getName() and not self.isConfigured():
            self.configure()
    def getParent(self):
        return self.parentnode
    def setName(self, name):
        if name != self.getName():
            self.nodename = name
        if self.getParent() and not self.isConfigured():
            self.configure()
    def configure(self, config = {}):
        config = config.copy()
        config.setdefault('name', self.getName())
        config.setdefault('parent', self.getParent())
        super(SimpleDataNode, self).configure(config)
    def configuration(self):
        config = super(SimpleDataNode, self).configuration()
        config['attributes'] = self.getAttributes()
        return config
    def getName(self):
        return self.nodename
    def getAttribute(self, name):
        return self.attributes[name]
    def setAttribute(self, name, value):
        self.attributes[name] = str(value)
    def hasAttribute(self, name):
        return self.attributes.has_key(name)
    def hasAttributes(self):
        return len(self.attributes)
    def getAttributes(self):
        return dict(self.attributes)
    def setType(self, datatype):
        self.datatype = datatype
    def getType(self):
        return self.datatype
    def testValue(self, value):
        try:
            self.asType(value)
        except ValueError:
            return False
        else:
            return True
    def asType(self, value):
        if self.datatype is not None:
            value = self.datatype(value)
        return value
    def setValue(self, value):
        self.datavalue = self.asType(value)
    def getValue(self):
        return self.datavalue
    def get(self):
        return self.getValue()
    def set(self, value):
        return self.setValue(value)

class SOAPDataNode(SimpleDataNode):
    def __init__(self, *args, **kw):
        self.soapdata = None
        super(SOAPDataNode, self).__init__(*args, **kw)
    def get(self):
        return super(SOAPDataNode, self).getValue()
    def set(self, value):
        return super(SOAPDataNode, self).setValue(value)
    def getValue(self):
        return self.soapdata
    def _nameFromData(self, soapdata):
        name = soapdata._name
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        self.setName(name)
    def _valueFromData(self, soapdata):
        value = soapdata._data
        if value is None:
            value = ''
        elif isinstance(value, unicode):
            value = value.encode('utf-8')
        self.set(value)
    def _attributesFromData(self, soapdata):
        for ((ns, name), value) in soapdata._attrs.items():
            if isinstance(name, unicode):
                name = name.encode('utf-8')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            self.setAttribute(name, value)
    def _childrenFromData(self, soapdata):
        for name in soapdata._keys():
            value = getattr(soapdata, name)
            if isinstance(name, unicode):
                name = name.encode('utf-8')
            if isinstance(value, Types.anyType):
                nodetype = SOAPDataNode
            else:
                if isinstance(value, unicode):
                    value = value.encode('utf-8')
                nodetype = SimpleDataNode
            if self.has_child(name):
                node = self.get_child(name)
                if not isinstance(node, nodetype):
                    node.prune()
                    node = nodetype()
            else:
                node = nodetype()
            node.setName(name)
            node.setValue(value)
            node.setParent(self)
    def setValue(self, soapdata):
        self.soapdata = soapdata
        if not self.getName():
            self._nameFromData(soapdata)
        datalevels = []
        curparent = self.getParent()
        while isinstance(curparent, SimpleDataNode):
            datalevels.append(curparent)
            curparent = curparent.getParent()
        if DEBUG:
            print '%s%s' % (''.ljust( 4 * len(datalevels)), self.getName())
        self._valueFromData(soapdata)
        self._attributesFromData(soapdata)
        self._childrenFromData(soapdata)

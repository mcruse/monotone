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
import StringIO
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.neode.tools import OGConfigurableNeodeAdapter
from mpx.lib.configure._xml_handler import _encode_xml as encode_xml
from mpx.lib.configure import parse_xml
from mpx.lib.configure import Iterator
from mpx.system.system import _load as load_node

from interfaces import *

class BroadwayConfigurableGenerator(object):
    implements(IBroadways)
    adapts(IConfigurableNode)
    
    nodeopen = "<node name='%s' node_id='%s' module='%s.%s' config_builder=''  inherant='false' description=''>"
    nodeclose = "</node>"
    configopen = "\t<config>"
    configclose = "\t</config>"
    propertyopenclose = "\t\t<property name='%s' value='%s'/>"
    
    def __init__(self, node):
        self.node = node
    
    def _xml_lines(self, levels = None):
        realnode = self.node
        while isinstance(realnode, OGConfigurableNeodeAdapter):
            realnode = realnode.node
        classname = realnode.__class__.__name__
        module = realnode.__class__.__module__
        xmllines = [self.nodeopen % (self.node.name, 0, module, classname)]
        xmllines.append(self.configopen)
        configuration = self.node.configuration()
        if configuration.has_key('parent'):
            del(configuration['parent'])
        if configuration.has_key('name'):
            del(configuration['name'])
        for name, value in configuration.items():
            if not isinstance(value, str):
                value = str(value)
            value = encode_xml(value)
            xmllines.append(self.propertyopenclose % (name, value))
        xmllines.append(self.configclose)
        xmllines.append(self.nodeclose)
        return xmllines
    
    def dumps(self, levels = None):
        return string.join(self._xml_lines(levels), '\n')
    
    def loads(self, data):
        datastream = StringIO.StringIO(data)
        xmlroot = parse_xml(datastream)
        xmlroot.parent = self.node.url
        crawler = Iterator(xmlroot)
        nodecount = 0
        while crawler.has_more():
            xmlnode = crawler.get_next_node()
            config = xmlnode.get_config()
            print 'Loading node %d: %s' % (nodecount, config)
            node = load_node(config)
            node.configure(config)
            nodecount += 1
        return nodecount
    
    def dump(self, datastream, levels = None):
        return datastream.write(self.dumps(levels))

register_adapter(BroadwayConfigurableGenerator)

class BroadwayCompositeGenerator(BroadwayConfigurableGenerator):
    implements(IBroadways)
    adapts(ICompositeNode)
    
    def dumps(self, levels = None):
        xmllines = super(BroadwayCompositeGenerator, self)._xml_lines(levels)
        nodeclose = xmllines.pop()
        if levels is not None:
            levels -= 1
        childdumps = []
        if levels != 0:
            children = self.node.children_nodes()
            generators = map(IBroadways, children)
            childdumps = [generator.dumps(levels) for generator in generators]
        xmllines.extend(childdumps)
        xmllines.append(nodeclose)
        return string.join(xmllines, '\n')
    
    def dump(self, datastream, levels = None):
        pass


register_adapter(BroadwayCompositeGenerator)

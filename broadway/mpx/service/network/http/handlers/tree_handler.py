"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node_url
from mpx.lib.node import as_node
from mpx.lib.node import Alias
from mpx.service.network.http.producers import LinesProducer
from mpx.service.network.http.handlers.filespace import FileSpace
debug = True

def treenode(node, children=True):
    description = {"name": node.name,
                   "path": as_node_url(node)}
    if children:
        description["children"] = []
        if hasattr(node, "children_nodes"):
            description["children"].extend({"_reference": as_node_url(child)} 
                                           for child in node.children_nodes())
    return description

def nodetree(node):
    return {"identifier": "path", 
            "label": "name", 
            "items": [treenode(node) for node in listnodes(node)]}

def listnodes(node):
    yield node
    if isinstance(node, Alias):
        children = ()
    elif isinstance(node, FileSpace):
        children = ()
    elif not node.has_method('children_nodes'):
        children = ()
    else:
        children = node.children_nodes()
    for child in children:
        for node in listnodes(child):
            yield node

def listurls(node):
    for node in listnodes(node):
        yield as_node_url(node)

def lineproducer(generator):
    if debug:
        return DebuggingLinesProducer(generator)
    return LinesProducer(generator)

class GeneratedList(object):
    maxlines = 1024
    def __init__(self, generator, linecount=100):
        self.linecount = linecount
        self.generator = generator
        super(GeneratedList, self).__init__()
    def __getslice__(self, start, end=None):
        if end is None:
            linecount = self.maxlines
        else:
            linecount = abs(end - start)
        lines = []
        for line in self.generator:
            lines.append(line)
            if len(lines) >= linecount:
                break
        return lines

class DebuggingLinesProducer(LinesProducer):
    def __init__(self, *args, **kw):
        self.bytesout = 0
        self.bytesmax = 0
        self.morecalls = 0
        LinesProducer.__init__(self, *args, **kw)
    def more(self, *args, **kw):
        data = LinesProducer.more(self, *args, **kw)
        self.morecalls += 1
        self.bytesout += len(data)
        self.bytesmax = max(self.bytesmax, len(data))
        if not data:
            message = "more() invoked %d times, %db max, %db total"
            print message % (self.morecalls, self.bytesmax, self.bytesout)
        return data

class TreeHandler(CompositeNode):
    def __init__(self):
        self.request_path = "/node-tree"
        super(TreeHandler, self).__init__()
    def configure(self, config):
        self.request_path = config.get('request_path', self.request_path)
        super(TreeHandler, self).configure(config)
    def configuration(self):
        config = super(TreeHandler, self).configuration()
        config["request_path"] = self.request_path
        return config
    def match(self, path):
        return path.startswith(self.request_path)
    def handle_request(self, request):
        nodeurl = request.get_path()[len(self.request_path):]
        node = as_node(nodeurl)
        generator = listurls(node)
        generated = GeneratedList(generator)
        request.push(lineproducer(generated))
        request.done()

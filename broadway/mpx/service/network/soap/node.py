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
from mpx.lib.node import CompositeNode
from mpx.service.network.soap.service import SOAPService
from mpx.service.network.soap.service import CurriedCallable

class SOAPServiceNode(CompositeNode):
    def __init__(self):
        self.serviceproxy = None
        self._children = {}
        CompositeNode.__init__(self)
    def configure(self, config):
        CompositeNode.configure(self, config)
        self.soapurl = config.get('soapurl')
        self.prefixnamespaces = config.get('prefixnamespaces', False)
        if isinstance(self.prefixnamespaces, str):
            self.prefixnamespaces = eval(self.prefixnamespaces)
        self.soapaction = config.get('soapaction')
        self.namespace = config.get('namespace')
    def start(self):
        self.serviceproxy = SOAPService(self.soapurl, self.namespace)
        self.serviceproxy.setsoapaction(self.soapaction)
        self.serviceproxy.namespace_prefixing(self.prefixnamespaces)
        CompositeNode.start(self)
    def __getattr__(self, name):
        if name in ('_children', 'discover_children_nodes'):
            raise AttributeError(name)
        return CurriedCallable(self.serviceproxy.invoke, name)


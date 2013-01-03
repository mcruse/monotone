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
import time
from os import path
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.lib.node import ConfigurableNode
from mpx.lib.exceptions import ENoSuchName
from mpx.service.network.xhtml.form import proxy
from mpx.service.network.soap import service
from mpx.service.network.soap import soapdata
from mpx.service.network.xhtml import xmldata

class AttributeNode(ConfigurableNode):
    def __init__(self, *args, **kw):
        self.nodeurl = None
        self.attribute = None
        super(AttributeNode, self).__init__(*args, **kw)
    def configure(self, config):
        self.nodeurl = config.get('nodeurl', self.nodeurl)
        self.attribute = config.get('attribute', self.attribute)
        super(AttributeNode, self).configure(config)
    def get(self):
        try:
            node = as_node(self.nodeurl)
        except ENoSuchName:
            return ''
        else:
            return node.attributes.get(self.attribute, '')

class CNEDispatch(CompositeNode):
    def __init__(self, *args, **kw):
        self.wsresponse = None
        self.soapnodes = None
        self.endnode = None
        self.startnode = None
        self.xmlnodes = None
        self.parseXML = False
        self.parseSOAP = True        
        self.serviceproxy = None
        self.currenttime = None
        self.password = None
        self.account = None
        self.namespace = None
        self.wsdlURL = None
        self.timeformat = '%Y-%m-%dT%H:%M:%S'
        super(CNEDispatch, self).__init__(*args, **kw)
    def configure(self, config):
        self.wsdlURL = config.get('WSDL', self.wsdlURL)
        self.account = config.get('account', self.account)
        self.password = config.get('password', self.password)
        self.namespace = config.get('namespace', self.namespace)
        self.timeformat = config.get('timeformat', self.timeformat)
        super(CNEDispatch, self).configure(config)
    def configuration(self):
        config = super(CNEDispatch, self).configuration()
        config['WSDL'] = self.wsdlURL
        config['account'] = self.account
        config['password'] = self.password
        config['namespace'] = self.namespace
        config['timeformat'] = self.timeformat
        return config
    def setup(self):
        dispatch = service.WSDLService(self.wsdlURL)
        namespace = dispatch.wsdlDocumentProxy.wsdl.targetNamespace
        if self.namespace is None:
            self.namespace = namespace
        dispatch.setNamespace(self.namespace)
        dispatch.disableNSPrefixing()
        dispatch.soapResultUnwrappingOff()
        dispatch.soapObjectSimplifyingOff()
        dispatch.debuggingOff()
        self.serviceproxy = dispatch
    def start(self):
        if not self.has_child('WS Response'):
            self.wsresponse = CompositeNode()
            self.wsresponse.configure({'parent': self, 
                                       'name': 'WS Response'})
            self.xmlnodes = xmldata.XMLDataNode()
            self.xmlnodes.configure({'name': 'XML Nodes', 
                                     'parent': self.wsresponse})
            self.soapnodes = soapdata.SOAPDataNode()
            self.soapnodes.configure({'name': 'SOAP Nodes', 
                                      'parent': self.wsresponse})
            

        else:
            self.wsresponse = self.get_child('WS Response')
            self.xmlnodes = self.wsresponse.get_child('XML Nodes')
            self.soapnodes = self.wsresponse.get_child('SOAP Nodes')
        if not self.has_child('Start time'):
            nodepath = path.join(as_node_url(self.soapnodes), 
                                 'GetAlertsResult/disp/emralert')
            self.startnode = AttributeNode()
            self.startnode.configure({'name': 'Start time', 
                                      'nodeurl': nodepath, 
                                      'attribute': 'start', 
                                      'parent': self})
            self.endnode = AttributeNode()
            self.endnode.configure({'name': 'End time', 
                                    'nodeurl': nodepath, 
                                    'attribute': 'end', 
                                    'parent': self})
        self.setup()
        super(CNEDispatch, self).start()
    def deprecated_start(self):
        if not self.has_child('WS Response'):
            self.wsresponse = xmldata.XMLDataNode()
            self.wsresponse.configure(
                {'name': 'WS Response', 'parent': self})
        else:
            self.wsresponse = self.get_child('WS Response')
        dispatch = service.SOAPService(self.serviceurl, self.namespace)
        dispatch.disableNSPrefixing()
        dispatch.setSoapAction(self.soapaction)
        dispatch.debuggingOff()
        dispatch.makeMethod('GetAlerts')
        dispatch.GetAlerts.appendArgument('UserName', 'string')
        dispatch.GetAlerts.appendArgument('Password', 'string')
        dispatch.GetAlerts.appendArgument('CurrentTime', 'string')
        self.serviceproxy = dispatch
        super(CNEDispatch, self).start()
    def deprecated_set(self, timestamp):
        if isinstance(timestamp, (int, float, long)):
            timetuple = time.localtime(timestamp)
            timestamp = time.strftime(self.timeformat, timetuple)
        elif timestamp in (None, 'None'):
            timestamp = time.strftime(self.timeformat)
        self.currenttime = timestamp
        self.serviceproxy.GetAlerts(self.account, 
                                    self.password, 
                                    self.currenttime)
        self.wsresponse.set(self.serviceproxy.GetAlerts.getResponseData())
    def set(self, timestamp = None):
        if isinstance(timestamp, (int, float, long)):
            timetuple = time.localtime(timestamp)
            timestamp = time.strftime(self.timeformat, timetuple)
        elif timestamp in (None, 'None'):
            timestamp = time.strftime(self.timeformat)
        self.currenttime = timestamp
        self.serviceproxy.GetAlerts(UserName=self.account, 
                                    Password=self.password, 
                                    CurrentTime=self.currenttime)
        if self.parseXML:
            self.xmlnodes.setValue(
                self.serviceproxy.GetAlerts.getResponseData())
        if self.parseSOAP:
            self.soapnodes.setValue(
                self.serviceproxy.GetAlerts.getResponse())
    def get(self):
        return self.currenttime

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
from mpx.lib.node import CompositeNode
from mpx.service.network.xhtml.form import proxy
from mpx.service.network.soap import service
from mpx.service.network.soap import soapdata
from mpx.service.network.xhtml import xmldata

class CNEPricing(CompositeNode):
    def __init__(self, *args, **kw):
        self.effectivedate = None
        self.wsresponse = None
        self.soapnodes = None
        self.xmlnodes = None
        self.parseXML = False
        self.parseSOAP = True
        self.serviceproxy = None
        self.priceCurve = None
        self.password = None
        self.account = None
        self.namespace = None
        self.wsdlURL = None
        self.dateformat = '%m/%d/%Y'
        super(CNEPricing, self).__init__(*args, **kw)
    def configure(self, config):
        self.priceCurve = config.get('priceCurve', self.priceCurve)
        self.wsdlURL = config.get('WSDL', self.wsdlURL)
        self.account = config.get('account', self.account)
        self.password = config.get('password', self.password)
        self.namespace = config.get('namespace', self.namespace)
        self.dateformat = config.get('dateformat', self.dateformat)
        super(CNEPricing, self).configure(config)
    def configuration(self):
        config = super(CNEPricing, self).configuration()
        config['WSDL'] = self.wsdlURL
        config['priceCurve'] = self.priceCurve
        config['account'] = self.account
        config['password'] = self.password
        config['namespace'] = self.namespace
        config['dateformat'] = self.dateformat
        return config
    def setup(self):
        pricing = service.WSDLService(self.wsdlURL)
        namespace = pricing.wsdlDocumentProxy.wsdl.targetNamespace
        if self.namespace is None:
            self.namespace = namespace
        pricing.setNamespace(self.namespace)
        pricing.disableNSPrefixing()
        pricing.soapResultUnwrappingOff()
        pricing.soapObjectSimplifyingOff()
        pricing.debuggingOff()
        self.serviceproxy = pricing
    def deprecated_setup(self):
        pricing = service.WSDLService(self.wsdlURL)
        pricing.debuggingOff()
        pricing.disableNSPrefixing()
        pricing.GetPrice.namespace = self.namespace
        pricing.GetPrice.clearArguments()
        pricing.GetPrice.appendArgument('strCurve', 'string')
        pricing.GetPrice.appendArgument('strEffectiveDate', 'string')
        pricing.GetPrice.appendArgument('CustAccount', 'string')
        pricing.GetPrice.appendArgument('Pwd', 'string')
        self.serviceproxy = pricing
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
        self.setup()
        super(CNEPricing, self).start()
    def deprecated_set(self, timestamp):
        if isinstance(timestamp, (int, float, long)):
            timetuple = time.localtime(timestamp)
            timestamp = time.strftime(self.dateformat, timetuple)
        elif timestamp in (None, 'None'):
            timestamp = time.strftime(self.dateformat)
        self.effectivedate = timestamp
        self.serviceproxy.GetPrice(
            self.priceCurve, self.effectivedate, self.account, self.password)
        self.wsresponse.set(self.serviceproxy.GetPrice.getResponse())
    def set(self, timestamp = None):
        if isinstance(timestamp, (int, float, long)):
            timetuple = time.localtime(timestamp)
            timestamp = time.strftime(self.dateformat, timetuple)
        elif timestamp in (None, 'None'):
            timestamp = time.strftime(self.dateformat)
        self.effectivedate = timestamp
        self.serviceproxy.GetPrice(
            strCurve=self.priceCurve, strEffectiveDate=self.effectivedate, 
            CustAccount=self.account, Pwd=self.password)
        response = self.serviceproxy.GetPrice.getResponse()
        if self.parseXML:
            self.xmlnodes.setValue(response.GetPriceResult)
        if self.parseSOAP:
            self.soapnodes.setValue(response)
    def get(self):
        return self.effectivedate


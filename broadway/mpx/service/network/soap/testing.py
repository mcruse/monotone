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
import time
from xml.dom import minidom
from mpx.service.network.constellation.soap import service
from mpx.service.network.constellation.andover import form

def asDom(text):
    return minidom.parseString(text)


def dispatchTimestamp(seconds = None):
    if seconds is None:
        seconds = time.localtime()
    return time.strftime(timeformat, seconds)

##
# Setup constants
dateformat = '%m/%d/%Y'
timeformat = '%Y-%m-%dT%H:%M:%S'
username = 'richards-zeta'
password = 'klfo04j6'
zone = 'AEP.ZONE.NA.PJMDA'
priceurl = 'http://lr-pricing-stage.constellation.com/dr/PriceWebService.asmx'
pricewsdl = 'http://lr-pricing-stage.constellation.com/dr/PriceWebService.asmx?WSDL'
eventwsdl = 'http://lr-dispatch-stage.constellation.com/dispatch/ServiceAlert.asmx?WSDL'
pricenamespace = 'http://lr-pricing.constellation.com'
priceaction = 'http://lr-pricing.constellation.com/GetPrice'    
dispatchurl = 'http://lr-dispatch-stage.constellation.com/dispatch/ServiceAlert.asmx'
dispatchns = 'http://lr-dispatch.constellation.com'
dispatchaction = 'http://lr-dispatch.constellation.com/GetAlerts'


##
# Pure SOAPpy impl using fixed WSDL
import time
from SOAPpy import WSDL
username = 'richards-zeta'
password = 'klfo04j6'
pricens = 'http://lr-pricing.constellation.com'
dispatchns = 'http://lr-dispatch.constellation.com'

def getTime(seconds = None):
    timeformat = '%Y-%m-%dT%H:%M:%S'
    localtime = time.localtime(seconds)
    return time.strftime(timeformat, localtime)


def getDate(seconds = None):
    dateformat = '%m/%d/%Y'
    localtime = time.localtime(seconds)
    return time.strftime(dateformat, localtime)


def getZone():
    return 'AEP.ZONE.NA.PJMDA'


evpx = WSDL.Proxy('/home/sgreen/workspace/source/sgreen/ServiceAlertV1.WSDL')
evpx.soapproxy.config.unwrap_results = 0
evpx.soapproxy.config.dumpSOAPOut = 1
evpx.soapproxy.config.dumpSOAPIn = 1
evpx.methods['GetAlerts'].namespace = dispatchns
evpx.soapproxy.config.buildWithNamespacePrefix = False

evpx.GetAlerts(UserName=username, Password=password, CurrentTime=getTime())
evpx.GetAlerts(Password=password, CurrentTime=getTime(), UserName=username)
evpx.GetAlerts(CurrentTime=getTime(), UserName=username, Password=password)


ppx = WSDL.Proxy('/home/sgreen/workspace/source/sgreen/PriceWebServiceV1.WSDL')
ppx.soapproxy.config.unwrap_results = 0
ppx.soapproxy.config.dumpSOAPOut = 1
ppx.soapproxy.config.dumpSOAPIn = 1
ppx.methods['GetPrice'].namespace = pricens
ppx.soapproxy.config.buildWithNamespacePrefix = False
ppx.GetPrice(strCurve=getZone(), 
             strEffectiveDate=getDate(), 
             CustAccount=username, Pwd=password)








##
# Setup pricing web-service proxy, and configure params
pricing = service.WSDLService(pricewsdl)
pricing.debuggingOn()
pricing.disableNSPrefixing()
pricing.GetPrice.namespace = pricenamespace
pricing.GetPrice.clearArguments()
pricing.GetPrice.appendArgument('strCurve', 'string')
pricing.GetPrice.appendArgument('strEffectiveDate', 'string')
pricing.GetPrice.appendArgument('CustAccount', 'string')
pricing.GetPrice.appendArgument('Pwd', 'string')



##
# Test setup fr Dave's code...
from mpx.service.network.constellation.soap import service
eventwsdl = 'http://m2.richards-zeta.com/wsdl/WSParticipantInterfaceEventsPolled.wsdl'
eventnamespace = 'http://eservices.energyconnectinc.com/'
username = 'user id 1'
password = 'pwd 1'
siteID = 'simon003'

event = service.WSDLService(eventwsdl)
event.debuggingOn()
event.disableNSPrefixing()
event.GetEventNotification.namespace = eventnamespace
event.GetEventNotification.clearArguments()
event.GetEventNotification.appendArgument('userName', 'string')
event.GetEventNotification.appendArgument('password', 'string')
event.GetEventNotification.appendArgument('siteID', 'string')
event.GetEventNotification(username, password, siteID)
response = event.GetEventNotification.getResponse()










##
# Setup dispatch web-service proxy, and configure params
dispatch = service.SOAPService(dispatchurl, dispatchns)
dispatch.disableNSPrefixing()
dispatch.setSoapAction(dispatchaction)
dispatch.debuggingOn()
dispatch.makeMethod('GetAlerts')
dispatch.GetAlerts.appendArgument('UserName', 'string')
dispatch.GetAlerts.appendArgument('Password', 'string')
dispatch.GetAlerts.appendArgument('CurrentTime', 'string')


##
# Invoke each once
pricing.GetPrice(zone, time.strftime(dateformat), username, password)
pr = pricing.GetPrice.getResponse()
dispatch.GetAlerts(username, password, dispatchTimestamp())
dr = dispatch.GetAlerts.getResponse()

##
# Invoke demand-response using timestamp with known events
tsdispatch = '2008-01-11T14:15:00'
tsdispatch = '2008-06-15T01:00:00'
dispatch.GetAlerts(username, password, tsdispatch)
dr2 = dispatch.GetAlerts.getResponseData()

##
# Invoke pricing using timestamp of alerts example
tspricing = '01/11/2008'
pricing.GetPrice(zone, tspricing, username, password)
pr2 = pricing.GetPrice.getResponse()

##
# Create DOM document objects from responses
drdom = asDom(dr2)
prdom = asDom(pr2)

from mpx.lib.node import CompositeNode
results = CompositeNode()
results.configure({'name': 'Results', 'parent': '/services/network'})
results.start()

def setupnodes(*elements):
    for childnode in results.children_nodes():
        if isinstance(childnode, form.ElementNode):
            childnode.prune()
    reload(form)
    domnodes = []
    for element in elements:
        domnode = form.ElementNode()
        domnode.configure({'element': element, 'parent': results})
        domnode.start()
        domnodes.append(domnode)
    return domnodes



drnode = setupnodes(drdom.documentElement)[0]
elements = drdom.getElementsByTagName('emralert')
alerts = drnode.findElementNodes(elements)
for alert in alerts:
    drnode.reprSubTree(alert)



domnodes = setupnodes(drdom.documentElement, prdom.documentElement)
drnode, prnode = domnodes

##
# Create DOM node instances and configure
drnode = form.ElementNode()
drnode.configure({'element': drdom.documentElement, 'parent': results})
drnode.start()

prnode = form.ElementNode()
prnode.configure({'element': prdom.documentElement, 'parent': results})
prnode.start()

drnode.reprtree()
prnode.reprtree()

alertelements = drdom.getElementsByTagName('emralert')
alerts = drnode.findnodes(alertelements)


drnode.update(drdom.documentElement)




results = dispatch.GetAlerts.invoke(username, password, tsdispatch)




pricing.GetPrice._clearParams()
pricing.setSoapAction(priceaction)
pricing.namespace_prefixing(False)
pricing.GetPrice._defineParam('strCurve', 'string')
pricing.GetPrice._defineParam('strEffectiveDate', 'string')
pricing.GetPrice._defineParam('CustAccount', 'string')
pricing.GetPrice._defineParam('Pwd', 'string')
pricing.GetPrice._setNamespace(pricenamespace)
pricing.debugSOAP(True)
pricing.GetPrice(zone, time.strftime(dateformat), username, password)

dispatch = SOAPService(dispatchurl, dispatchns)
dispatch.setsoapaction(dispatchaction)
dispatch.namespace_prefixing(False)
dispatch.makeMethod('GetAlerts')
dispatch.GetAlerts._defineParam('UserName', 'string')
dispatch.GetAlerts._defineParam('Password', 'string')
dispatch.GetAlerts._defineParam('CurrentTime', 'string')
dispatch.GetAlerts(username, password, dispatchTimestamp())



pricing.GetPrice.getArguments()
pricing.GetPrice.getArgumentNames()
pricing.GetPrice.getArgumentTypes()
pricing.GetPrice(zone, time.strftime(dateformat), username, password)






priceproxy = SOAPServiceNode()
priceproxy.configure({'name':'Pricing', 'parent': '/services/network', 
                    'soapurl': priceurl, 'soapaction': priceaction, 
                    'namespace': pricenamespace})
priceproxy.start()

priceproxy.configure({'name':'Pricing', 'parent': '/services/network', 
                    'soapurl': priceurl, 'soapaction': priceaction, 
                    'namespace': pricenamespace})
priceproxy.start()


dispatch = SOAPServiceNode()
dispatch.configure({'name':'Dispatch', 'parent': '/services/network', 
                    'soapurl': dispatchurl, 'soapaction': dispatchaction, 
                    'namespace': dispatchns})
dispatch.start()

priceproxy.GetPrice(('strCurve', 'strEffectiveDate', 'CustAccount', 'Pwd'), 
                    (zone, time.strftime(dateformat), username, password))

dispatch.GetAlerts(('UserName', 'Password', 'CurrentTime'), 
                   (username, password, time.strftime(timeformat)))




pricing.GetPrice._defineParam('strCurve', 'string')
pricing.GetPrice._defineParam('strEffectiveDate', 'string')
pricing.GetPrice._defineParam('CustAccount', 'string')
pricing.GetPrice._defineParam('Pwd', 'string')
pricing.GetPrice._setNamespace(pricenamespace)
pricing.debugSOAP(True)
pricing.GetPrice(zone, time.strftime(dateformat), username, password)

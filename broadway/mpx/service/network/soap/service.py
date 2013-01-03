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
    Wraps SOAPpy tools to integrate with FW and simplify 
    setup and usage.  Note that these tools are overkill 
    for typical SOAP services, but are useful where services 
    must be configured by hand and provide silly results...
"""
from xml.dom import minidom
from SOAPpy import Types
from SOAPpy import WSDL
from SOAPpy import SOAPProxy
from SOAPpy.Types import stringType
from SOAPpy.Client import SOAPAddress
from SOAPpy.wstools.WSDLTools import SOAPCallInfo

TYPES = {'boolean':         Types.booleanType, 
         'string':          str, 
         'str':             str, 
         'int':             int, 
         'integer':         int, 
         'float':           float}


def identityConversion(obj):
    return obj


def getType(name, default = None):
    return TYPES.get(name, default)


def applyType(typename, value, default = identityConversion):
    conversion = getType(typename)
    if conversion is None:
        conversion = default
    return conversion(value)


def asNamedParameter(value, paraminfo):
    typename = paraminfo.type[1]
    value = applyType(typename, value, str)
    return stringType(value, paraminfo.name)


def asDom(text):
    return minidom.parseString(text)


def dontParse(data, *args, **kw):
    return (data, ())


class TransportWrapper(object):
    def __init__(self, transport):
        self.transport = transport
        self.responsedata = None
        self.responsenamespace = None
        super(TransportWrapper, self).__init__()
    def __getattr__(self, name):
        return getattr(self.transport, name)
    def call(self, *args, **kw):
        data, ns = self.transport.call(*args, **kw)
        self.responsedata = data
        self.responsenamespace = ns
        return (data, ns)


class DataString(str):
    def __init__(self, name, attrs = {}):
        self.attrs = dict(attrs)

class CurriedCallable(object):
    def __init__(self, callableobject, *args, **kw):
        self.callable = callableobject
        self.curriedargs = args
        self.curriedkeywords = kw
    def __call__(self, *args, **kw):
        arguments = self.curriedargs + args
        keywords = self.curriedkeywords.copy()
        keywords.update(kw)
        return self.callable(*arguments, **keywords)

class SOAPMethod(object):
    def __init__(self, service, methodname):
        self.service = service
        self.response = None
        self.responsedata = None
        if hasattr(service, 'wsdlDocumentProxy'):
            self.soapCallInfo = service.wsdlDocumentProxy.methods[methodname]
        else:
            self.soapCallInfo = SOAPCallInfo(methodname)
        super(SOAPMethod, self).__init__(service, methodname)
    def getSOAPProxy(self):
        return self.service.soapServiceProxy
    soapProxy = property(getSOAPProxy)
    def getNamespace(self):
        return self.soapCallInfo.namespace
    def setNamespace(self, namespace):
        self.soapCallInfo.namespace = namespace
    namespace = property(getNamespace, setNamespace)
    def getLocation(self):
        return self.soapCallInfo.location
    def setLocation(self, location):
        self.soapCallInfo.location = location
    location = property(getLocation, setLocation)
    def getSOAPAction(self):
        return self.soapCallInfo.soapAction
    def setSOAPAction(self, location):
        self.soapCallInfo.soapAction = soapAction
    soapAction = property(getSOAPAction, setSOAPAction)
    def getArgumentNames(self):
        return tuple([param.name for param in self.soapCallInfo.inparams])
    def getArgumentTypes(self):
        return tuple([param.type for param in self.soapCallInfo.inparams])
    def getArguments(self):
        return list(self.soapCallInfo.inparams)
    def getArgument(self, index):
        return self.soapCallInfo.inparams[index]
    def appendArgument(self, name, type, namespace=None, *args):
        return self.soapCallInfo.addInParameter(name, type, namespace, *args)
    def removeArgument(self, argument):
        self.soapCallInfo.inparams.remove(argument)
    def clearArguments(self):
        self.soapCallInfo.inparams = []
    def invoke(self, *args, **kwargs):
        # Turn values passed in into named parameter args.
        arginfos = self.getArguments()
        argparams = tuple(map(asNamedParameter, args, arginfos[0:len(args)]))
        argvalues = args[len(argparams):]
        # Configure soap proxy with location and action of call
        curproxy = self.soapProxy.proxy
        curaction = self.soapProxy.soapaction
        curnamespace = self.soapProxy.namespace
        curtransport = self.soapProxy.transport
        transwrapper = TransportWrapper(curtransport)
        try:
            if self.soapCallInfo.location:
                self.soapProxy.proxy = SOAPAddress(self.soapCallInfo.location)
            if self.soapCallInfo.soapAction:
                self.soapProxy.soapaction = self.soapCallInfo.soapAction
            if self.soapCallInfo.namespace:
                self.soapProxy.namespace = self.soapCallInfo.namespace
            self.soapProxy.transport = transwrapper
            #self.soapProxy.config.returnAllAttrs = 1
            # Grab soap proxy's dynamically genertated callable
            methodname = self.soapCallInfo.methodName
            proxycallable = self.soapProxy.__getattr__(methodname)
            result = proxycallable(*(argparams + argvalues), **kwargs)
        finally:
            self.soapProxy.proxy = curproxy
            self.soapProxy.soapaction = curaction
            self.soapProxy.namespace = curnamespace
            self.soapProxy.transport = curtransport
        self.response = result
        self.responsedata = transwrapper.responsedata
    def getResponse(self):
        return self.response
    def getResponseData(self):
        return self.responsedata
    def getResponsePrimitive(self):
        return Types.simplify(self.getResponse())
    def __repr__(self):
        reprformat = '<bound %s.%s method %s of %s>'
        classname = type(self).__name__
        modulename = type(self).__module__
        methodname = self.soapCallInfo.methodName
        servicerepr = object.__repr__(self.service)
        return reprformat % (modulename, classname, methodname, servicerepr)
    def __str__(self):
        strformat = '<bound method %s(%s) of %s>'
        methodname = self.soapCallInfo.methodName
        argnames = self.getArgumentNames()
        servicestr = object.__str__(self.service)
        return strformat % (methodname, ', '.join(argnames), servicestr)
    def __call__(self, *args, **kwargs):
        self.invoke(*args, **kwargs)
        return self.getResponse()

class ProxyInterface(object):
    def __init__(self, nsdict):
        self.__dict__ = nsdict
    def __setattr__(self, name, value):
        raise Attribute('Cannot set attributes')

##
# For shared flags, such as simplify_objects, which 
# exists on both soapServiceProxy.config and 
# soapServiceProxy itself, the flag on soapServiceProxy 
# takes precedence.  It may even be that the one on config 
# only sets a default value and does not effect the behaviour 
# once a proxy has been created.
# Unwrap results simplify removes soapResult structure at top.

class SOAPService(object):
    soapServiceProxy = None
    def __init__(self, *args):
        self.methods = {}
        self._explicitMode = True
        self.setupProxies(*args)
        super(SOAPService, self).__init__()
    def getInterface(self):
        return ProxyInterface(self.methods)
    def debugging(self):
        return self.soapServiceProxy.config.debug
    def debuggingOn(self):
        self.soapServiceProxy.config.debug = 1
    def debuggingOff(self):
        self.soapServiceProxy.config.debug = 0
    def soapDebuggingOn(self):
        self.soapServiceProxy.config.dumpSOAPIn = 1
        self.soapServiceProxy.config.dumpSOAPOut = 1
    def soapDebuggingOff(self):
        self.soapServiceProxy.config.dumpSOAPIn = 0
        self.soapServiceProxy.config.dumpSOAPOut = 0
    def soapResultUnwrappingOn(self):
        self.soapServiceProxy.unwrap_results = 1
    def soapResultUnwrappingOff(self):
        self.soapServiceProxy.unwrap_results = 0
    def soapObjectSimplifyingOn(self):
        self.soapServiceProxy.simplify_objects = 1
    def soapObjectSimplifyingOff(self):
        self.soapServiceProxy.simplify_objects = 0
    def setExplicitMode(self, explicit = True):
        """
            Explicit mode controls how service treats 
            attempts to get non-existent attribute.  When 
            explicit mode is disabled, attempts to retrieve 
            non-existent attributes *atuomatically* generate meethod 
            stubs, assuming they are proxy methods.  The default 
            behaviour, however, is the have explicit mode enabled, 
            which means that attempts to access non-existent attributes 
            will result in AttributeError exceptions.  When in 
            this mode, use the "makeMethod(name)" function to 
            create proxy methods explicitly.
        """
        self._explicitMode = explicit
        return self._explicitMode
    def setupSoapProxy(self, soapurl, namespace):
        self.soapServiceUrl = soapurl
        self.soapServiceNamespace = namespace
        self.soapServiceProxy = SOAPProxy(soapurl, namespace)
        self.soapResultUnwrappingOff()
        self.soapObjectSimplifyingOff()
        return self.soapServiceProxy
    def setupProxies(self, *args):
        """
            Breaking out setup of proxy allows easy extension 
            by wrappers for other wannabe proxy-things within 
            SOAPpy package.
        """
        return self.setupSoapProxy(*args)
    def enableNSPrefixing(self):
        self.soapServiceProxy.config.buildWithNamespacePrefix = True
    def disableNSPrefixing(self):
        self.soapServiceProxy.config.buildWithNamespacePrefix = False
    def isNamespacePrefixing(self):
        return self.soapServiceProxy.config.buildWithNamespacePrefix
    def getNamespace(self):
        return self.soapServiceProxy.namespace
    def setNamespace(self, namespace):
        self.soapServiceProxy.namespace = namespace
    namespace = property(getNamespace, setNamespace)
    def getSoapAction(self):
        return self.soapServiceProxy.soapaction
    def setSoapAction(self, action):
        self.soapServiceProxy.soapaction = action
    soapAction = property(getSoapAction, setSoapAction)
    def enableDebug(self, **kw):
        soapInDebug = self.soapServiceProxy.config.dumpSOAPIn
        soapOutDebug = self.soapServiceProxy.config.dumpSOAPOut
        headersInDebug = self.soapServiceProxy.config.dumpHeadersIn
        headersOutDebug = self.soapServiceProxy.config.dumpHeadersOut
        globalDebug = self.soapServiceProxy.config.debug
        soapInDebug = kw.get('SOAP In', soapInDebug)
        soapOutDebug = kw.get('SOAP Out', soapOutDebug)
        headersInDebug = kw.get('Headers In', headersInDebug)
        headersOutDebug = kw.get('Headers Out', headersOutDebug)
        globalDebug = kw.get('Global', globalInDebug)
    def invoke(self, methodname, argnames, argvalues, **kw):
        arguments = map(NamedString, argnames, argvalues)
        method = getattr(self._proxy, methodname)
        result = method(*arguments, **kw)
        return result
    def makeMethod(self, name):
        if self.methods.has_key(name):
            raise TypeError('method already exists.')
        return self.methods.setdefault(name, SOAPMethod(self, name))
    def __getattr__(self, name):
        if self.methods.has_key(name):
            return self.methods[name]
        elif not self._explicitMode:
            return self.makeMethod(name)
        raise AttributeError(name)

class WSDLService(SOAPService):
    """
        WSDL describes SOAP service.  Proxy concept applied to 
        SOAPpy WSDLs is misleading.  The power of the WSDL 
        "proxy" is automatic discovery and, possibly, some 
        type-checking.  All real functionality is providedy by 
        SOAPService it basically configures.
    """
    def __init__(self, *args):
        self.wsdlDocumentUrl = None
        self.wsdlDocumentProxy = None
        super(WSDLService, self).__init__(*args)
    def setupSoapProxy(self, *args):
        self.soapServiceProxy = self.wsdlDocumentProxy.soapproxy
    def setupWsdlProxy(self, wsdlurl):
        self.wsdlDocumentUrl = wsdlurl
        self.wsdlDocumentProxy = WSDL.Proxy(self.wsdlDocumentUrl)
    def setupProxies(self, *args):
        self.setupWsdlProxy(*args)
        # Potential for nice coopoerative-super proxy-chaining...
        super(WSDLService, self).setupProxies(*args)
        self._setupWSDLMethods()
    def _setupWSDLMethods(self):
        methodNames = self.wsdlDocumentProxy.methods.keys()
        for name in methodNames:
            self.makeMethod(name)
        return methodNames

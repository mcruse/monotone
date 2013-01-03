"""
Copyright (C) 2001 2002 2003 2004 2007 2008 2009 2011 Cisco Systems

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
import types
import sys
import string
import urllib
import os
import re
import os.path
import random
import traceback
import SocketServer
from threading import Lock
from mpx import properties
from mpx.lib import xmlrpclib
from mpx.lib import msglog, thread
from mpx.lib.deferred import Deferred
from mpx.lib.magnitude import is_object, as_magnitude
from mpx.service.network.http.response import Response
from mpx.lib.node import as_node, as_internal_node
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import as_boolean
from mpx.service.network.http.request_handler import RequestHandler
from mpx.lib.exceptions import EInvalidCommand
from mpx.lib.exceptions import MpxException
from mpx.lib.exceptions import SecurityException
from mpx.lib.xmlrpc import XMLRPC_ObjectInterface, XMLRPC_Deploy

## Create a XMLRPC marshaller for None types
## This gets registered with the xmlrpclib
## and will get called whenever any Nones are used
def dump_None(self, value, write=None):
    if write is None:
        write = self.write
    write("<value><nil/></value>\n")
    return

##
#  Broadway XML-RPC Default Handler
#
# @notes This takes an XMLRPC request, finds a matching object
#        then calls the appropriate method.
#
#        Each object can be of a specific 'lifetime'.
#        Valid lifetimes are 'Session', 'Request', 'Runtime'
#        (Session lifetime is not enabled.)  A Request lifetime
#        will create a new object on each request.  A Runtime
#        lifetime will create only one for the entire runtime.
#
class XMLRPC_Handler(RequestHandler):
    def __init__(self):
        self.deployed_object_instances = {}
        self.__session_manager = None
        ## Register method to handle Null types
        xmlrpclib.Marshaller.dispatch[types.NoneType] = dump_None
        super(XMLRPC_Handler, self).__init__()
    def get_session_manager(self):
        if self.__session_manager is None:
            self.__session_manager = as_node('/services/session_manager')
        return self.__session_manager
    session_manager = property(get_session_manager)
    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '/xmlrpc', config)
        set_attribute(self, 'deployed_objects',[],config)
        set_attribute(self, 'debug', 0, config)
        # requires_authentication is deprecated; provides_security more obvious.
        provides_security = config.get('requires_authentication', 1)
        set_attribute(
            self, 'provides_security', provides_security, config, as_boolean)
        self.secured = as_internal_node("/services").secured
        RequestHandler.configure(self, config)
        if self.secured:
            rna_xmlrpc = 'mpx.lib.xmlrpc.rna_xmlrpc.SecuredXmlRpcHandler'
            rna_xmlrpc2 = 'mpx.lib.xmlrpc.rna_xmlrpc.SecuredXmlRpcHandler2'
        else:
            rna_xmlrpc = 'mpx.lib.xmlrpc.rna_xmlrpc.RNA_XMLRPC_Handler'
            rna_xmlrpc2 = 'mpx.lib.xmlrpc.rna_xmlrpc.RNA_XMLRPC_Handler2'
        ## Pre-Register important XMLRPC Objects such RNA
        ## rna_xmlrpc -- Default RNA over XMLRPC handler
        child = XMLRPC_Deploy()
        params = {'name':'rna_xmlrpc',
                  'alias':'rna_xmlrpc',
                  'class_name': rna_xmlrpc,
                  'lifetime':'Runtime',
                  'parent':self}
        child.configure(params)
        ## rna_xmlrpc2 -- Next Generation RNA over XMLRPC handler
        child = XMLRPC_Deploy()
        params = {'name':'rna_xmlrpc2',
                  'alias':'rna_xmlrpc2',
                  'class_name': rna_xmlrpc2,
                  'lifetime':'Runtime',
                  'parent':self}
        child.configure(params)
    ##
    # Get the configuration.http://search.netscape.com/search.psp?cp=clkussrp&charset=UTF-8&search=file
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    #
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'secured', config, str)
        return config
    ##
    # Get the list of paths (possibly regular expressions) that
    # this request_listener wants to have sent to it.
    #
    # @return List of paths.
    #
    def listens_for(self):
        return [self.request_path]
    def match(self, path):
        p = '^%s$' % self.request_path
        if re.search(p,path):
            return 1
        return 0
    ##
    # Called by http_server each time a request comes in whose url mathes one of
    # the paths this handler said it was interested in.
    #
    # @param request  <code>Request</code> object from the http_server.  To send
    #                  resonse c-all <code>request.send(html)</code> where
    #                  <code>html</code> is the text response you want to send.
    # The posted data will be the XMLRPC request.  It is parsed and the object:method
    #  name are used to find the object and method.
    #
    def handle_request(self, request):
        try:
            result = self.execute(request)
        except SecurityException:
            # Pass up handling chain for generic handling.
            raise
        except Exception, error:
            msglog.log("XML-RPC", msglog.types.WARN, 
                       "Exception caused action to fail.")
            msglog.exception(prefix="handled")
            result = error
        def respond(result):
            if isinstance(result, Exception):
                # Package exception into XML-RPC Fault instance.
                message = getattr(result, "message", "")
                if not message:
                    message = str(result)
                typename = type(result).__name__
                if typename == "instance":
                    typename = result.__class__.__name__
                faultstring = "%s: %s" % (typename, message)
                if isinstance(faultstring, unicode):
                    try:
                        faultstring = str(faultstring)
                    except UnicodeEncodeError:
                        faultstring = faultstring.encode('utf')
                result = xmlrpclib.Fault(1, faultstring)
            else:
                # Dumps requires tuple or Fault type.
                result = (result,)
            xmlresult = xmlrpclib.dumps(result, methodresponse=True)
            response = Response(request)
            response.set_header('Content-Length', len(xmlresult))
            response.set_header('Content-Type', 'text/xml')
            response.send(xmlresult)
            self.debugout("Response sent to client.")
        if isinstance(result, Deferred):
            self.debugout("Registering respond action with deferred.")
            result.register(respond)
        else:
            respond(result)
    def debugout(self, message, dblevel=1):
        if self.debug < dblevel:
            return
        msglog.log("XML-RPC", msglog.types.DB, message)
    def execute(self, request):
        data = request.get_data().read_all()
        if not data:
            raise MpxException('XML-RPC request has no POST data.')
        ## process xmlrpc, getting the name of the method
        ## and parameters
        params, method = xmlrpclib.loads(data)
        if request.user_object() is None and len(params):
                session_id = params[0]
                user = self.session_manager.get_user_from_sid(session_id)
                request.user_object(user)
        ## get the name of the object
        ## and the name of method
        ## They are delimited by a colon.
        if '.' in method:
            tokens = string.split(method, '.')
        elif ':' in method:
            tokens = string.split(method, ':')
        else:
            raise MpxException('Invalid XMLRPC Request: %r' % data)
        object_alias = tokens[0]
        method_name = tokens[1]
        # Call the requested object
        # and return response
        self.debugout("Calling %s.%s" % (object_alias, method_name))
        return self.call(object_alias, method_name, params)
    ## Call the requested method on object
    def call(self, alias, method, params):
        ## look for registered object matching URL
        ## if found, then send this request to named
        ## object.   If not found, raise exception.
        deployed_method = self._find_deployed_object_method(alias, method)
        self.debugout("Method found -> %s.%s" % (alias, method))
        ## call the method
        return deployed_method(*params)
    ## Provide method to allow for programatic adding of deployed objects
    #  @param alias_name The alias name for this object
    #  @param class_name The full path to the class to map to alias
    #  @param lifetime  THe lifetime of the object.  How long to keep it alive
    #                   This can be 'Runtime', 'Session' or 'Request'
    #
    def register_deployed_object(self, alias_name, class_name, lifetime='Runtime'):
        entry = {}
        entry['alias'] = alias_name
        entry['class'] = class_name
        entry['lifetime'] = lifetime
        self.deployed_objects.append(entry)
    ## Search for object matching alias and return
    #  the appropriate instance.   This takes into account
    #  any scoping rules enforced.
    #
    # @throws MpxException if object cannot be found
    # @return the function address of the object/method
    #
    def _find_deployed_object_method(self, alias_name, method_name):
        for o in self.deployed_objects:
            if o['alias'] == alias_name:
                self.debugout("Found Alias -> %s" % alias_name)
                # get the module name
                object_name = o['class']
                lifetime = o['lifetime']
                if lifetime == 'Runtime':
                    instance = self._create_or_reuse_object(object_name)
                elif lifetime == 'Session':
                    raise MpxException("Lifetime per session not supported.")
                else:
                    instance = self._create_instance(object_name)
                if self.debug:
                    self.debugout("Instance created -> %s" % alias_name)
                attrib = getattr(instance, method_name)
                self.debugout(
                    "Attribute found -> %s.%s" % (alias_name, method_name))
                return attrib
        raise MpxException('No deployed object named "%s".' % alias_name)
    ## Clear the instance cache for deployed object
    def flush_cache(self):
        self.deployed_object_instances.clear()
    ## Return a cached version of an object
    #  or create a new instance of named module
    #  and add to cache
    #  @param module_name complete path of module to create
    # @return an instance of named module
    def _create_or_reuse_object(self, object_name):
        inst = None
        if self.deployed_object_instances.has_key(object_name):
            inst = self.deployed_object_instances[object_name]
        else:
            inst = self._create_instance(object_name)
            self.deployed_object_instances[object_name] = inst
        return inst
    ## Create instance of object.   Parse the module and object
    #  name from object_name var.  Import the module and create object
    def _create_instance(self, object_name):
        index = object_name.rfind('.')
        mod = object_name[:index]
        obj = object_name[index+1:]
        ## do import
        self.debugout("Importing -> from %s import %s" % (mod, obj))
        exec('from %s import %s' % (mod, obj))
        return eval( obj + '()' )

##
# Instantiates and returns XMLRPC_Handler.  Allows
# for uniform instaciation of all classes defined
# in framwork.
#
# @return Instance of XMLRPC_Handler defined in this module.
#
def factory():
    return XMLRPC_Handler()



if __name__ == '__main__':
    server = xmlrpclib.Server('http://localhost/xmlrpc:80')
    params = {'test':'value', 'test22':'fdfdf'}
    result = server.do_test(params)
    print result


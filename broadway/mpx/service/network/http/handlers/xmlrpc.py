"""
Copyright (C) 2004 2007 2008 2010 2011 Cisco Systems

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

from mpx import properties

from mpx.lib import msglog
from mpx.lib import thread
from mpx.lib import xmlrpclib

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib.exceptions import EInvalidCommand
from mpx.lib.exceptions import MpxException

from mpx.lib.magnitude import as_magnitude
from mpx.lib.magnitude import is_object

from mpx.lib.node import as_node
from mpx.lib.node import as_internal_node

from mpx.lib.xmlrpc import XMLRPC_Deploy
from mpx.lib.xmlrpc import XMLRPC_ObjectInterface

from mpx.service.network.http.request_handler import RequestHandler
from mpx.service.network.http.response import Response

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
class XMLRPC(RequestHandler):

    def configure(self, config):
        # The request_path tells the http_server which url requests
        #   should be sent to this handler.  It can be a regular expression
        #   as defined in the documentation for the python re module.
        set_attribute(self, 'request_path', '/XMLRPCv2', config)
        set_attribute(self, 'debug', 0, config)
        # requires_authentication is deprecated; provides_security more obvious.
        provides_security = config.get('requires_authentication', 1)
        set_attribute(
            self, 'provides_security', provides_security, config, as_boolean)
        self.secured = as_internal_node("/services").secured
        set_attribute(self, 'authentication', 'basic', config)
        if self.authentication not in ('digest','basic','form'):
            raise EInvalidValue('authentication',self.authentication,
                                'Authentication scheme not recognized.')
        RequestHandler.configure(self, config)
        # create the inherient child RNA
        if not self.has_child('RNA'):
            rna = RNA()
            config = {'parent':self,'name':'RNA', 'log_n_exceptions':0}
            rna.configure(config)
        return
    ##
    # Get the configuration.
    #
    # @return Dictionary containing current configuartion.
    # @see mpx.lib.service.SubServiceNode#configuration
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'request_path', config)
        get_attribute(self, 'secured', config, str)
        get_attribute(self, 'provides_security', config)
        get_attribute(self, 'authentication', config)
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
        p = '^%s$|^%s/.*' % (self.request_path,self.request_path)
        if re.search(p,path):
            return 1
        return 0

    def handle_request(self, request):
        path = request.get_path().split('/')
        # if there is a child to call, should be the
        # 3rd element path
        if len(path) < 3:
            fault_xml = xmlrpclib.dumps(
                    xmlrpclib.Fault(1, "Invalid URL Path")
                    )
            response = Response(request)
            response.send(fault_xml)
        else:
            c = path[2]
            handler = self.get_child(c)
            handler.handle_request(request)


class RNA(RequestHandler):
    def __init__(self):
        ## Register method to handle Null types
        xmlrpclib.Marshaller.dispatch[types.NoneType] = dump_None
        self._root_node = as_node('/')
        self._security_manager = None
        self._secured = False
        super(RNA, self).__init__()

    def _as_node(self, nodeurl):
        if self._secured:
            return self._security_manager.as_secured_node(nodeurl)
        else:
            return as_node(nodeurl)

    def start(self):
        if getattr(self.parent, 'secured', False):
            self._security_manager = as_node('/services/Security Manager')
            self._secured = True
        return super(RNA, self).start()

    def stop(self):
        super(RNA, self).stop()
        self._secured = None
        self._secured_manager = None

    def configure(self, config):
        RequestHandler.configure(self, config)
        ##
        # @attribute log_n_exceptions:
        #   log_n_exceptions == 0 - don't log RNA exceptions
        #   log_n_exceptions <  0 - log all RNA exceptions
        #   log_n_exceptions >  0 - log LOG_N_EXCEPTIONS RNA exceptions and
        #                           then stop.
        set_attribute(self, 'log_n_exceptions', 0, config)
        return
    def configuration(self):
        config = RequestHandler.configuration(self)
        get_attribute(self, 'log_n_exceptions', config)
        return config
    def _get_data(self,request):
        data =  request.get_data().read_all()
        if not data:
            raise MpxException('could not get DATA parameter from posted data')
        return data
    def _exception_string(self,e):
        _print_exc_str = getattr(e,'_print_exc_str',None)
        if not _print_exc_str:
            s = StringIO.StringIO()
            traceback.print_exc(None,s)
            s.seek(0)
            _print_exc_str = s.read()
            del s
            if hasattr(e,'_print_exc_str'):
                e._print_exc_str = _print_exc_str
        return 'error: %s.%s%r\n%s' % (e.__class__.__module__,
                                       e.__class__.__name__,
                                       e.args,
                                       _print_exc_str)
    ## To allow for String types to be encoded they need to
    #  to have the token ++encode:TYPEOFENCODE++ set as the
    #  start of the string.  This is not XML, but a token
    #  before the data.  This is to not force an XML document
    #  to need to be created for each check.
    #
    def _invoke(self, service, method, *args):
        s = self._as_node(service)
        a = getattr(s, method)
        args_new = []
        args_new.extend( args )

        result=None
        result = apply(a, args_new)

        return result
    ##
    # Just for testing right now
    #
    #
    #
    #
    #
    def invoke(self,request):
        data =self._get_data(request)
        results = []
        # process xmlrpc, getting the name of the method
        # and parameters
        r = xmlrpclib.loads(data)
        params = r[0]
        method = r[1]
        for param in params:
            # since we are spliting on ":" I put in a place holder
            # for the mpx:// before I do a split the put it back after
            # since mpx:// has a ":"
            param = param.replace("mpx://",'$$PLACE_HOLDER$$')
            p_s = param.split(':')
            service = p_s[0].replace('$$PLACE_HOLDER$$','mpx://')
            method = p_s[1]
            try:
                result = self._invoke(service, method)
                results.append(result)
            except Exception, e:
                if self.log_n_exceptions:
                    msglog.exception()
                    if self.log_n_exceptions > 0:
                        self.log_n_exceptions -= 1
                results.append(self._exception_string(e))
        return results

    def handle_request(self, request):
        response = Response(request)
        response.set_header('Content-Type', 'text/xml')
        try:
            path = request.get_path().split('/')
            node_path = '/%s' % string.join(path[3:],'/')
            #
            #
            #
            # just for testing right now
            #
            #
            #
            if node_path == '' and len(path) < 4:
                results = self.invoke(request)
                xml = xmlrpclib.dumps((results,),methodresponse=1)
                response.set_header('Content-Length', len(xml))
                response.set_header('Content-Type', 'text/xml')
                response.send(xml)
            else:
                node = self._as_node(node_path)
                data = self._get_data(request)
                # process xmlrpc, getting the name of the method
                # and parameters
                params, method = xmlrpclib.loads(data)
                method_name = ''
                # get the name of the object
                # and the name of method
                m = getattr(node, method)
                if params == '':
                    params = None
                result = (apply(m,params),)
                if hasattr(result[0],'has_key'):
                    for k in result[0].keys():
                        if hasattr(result[0][k], 'has_key') \
                           and result[0][k].has_key('value') \
                           and isinstance(result[0][k]['value'],Exception):
                            result[0][k]['value'] = 'error: %s' % result[0][k]['value']
                xml = xmlrpclib.dumps(result,methodresponse=1)
                # XML-RPC Call was successful.
                # Send back the XML result to client
                response = Response(request)
                response.set_header('Content-Length', len(xml))
                response.set_header('Content-Type', 'text/xml')
                response.send(xml)
        except Exception,err:
            if self.log_n_exceptions:
                msglog.exception()
                if self.log_n_exceptions > 0:
                    self.log_n_exceptions -= 1
            try:
                faultString = """<exception>
<module>%s</module>
<class>%s.%s</class>
<str>%r</str>
</exception>""" % (err.__class__.__module__,
                   err.__class__.__module__,
                   err.__class__.__name__,
                   str(err))                
            except:
                msglog.exception()
                faultString = "%s" % err
            fault_xml = xmlrpclib.dumps(
                    xmlrpclib.Fault(1, faultString)
                    )
            response.set_header('Content-Length', len(fault_xml))
            response.send(fault_xml)

##
# Instantiates and returns XMLRPC.
# @return Instance of XMLRPC defined in this module.
def factory():
    return XMLRPC()


if __name__ == '__main__':
    server = xmlrpclib.Server('http://localhost/xmlrpc2:80')
    params = {'test':'value', 'test22':'fdfdf'}
    result = server.do_test(params)
    print result


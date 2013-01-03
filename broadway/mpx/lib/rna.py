"""
Copyright (C) 2001 2002 2003 2004 2005 2006 2007 2009 2010 2011 Cisco Systems

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
##
# @todo Support attributes.  This is accomplished by building an attribute
#       'dictionary' on the fly.  __getattr__ and __setattr__ could use the
#       dictionary to invoke 'special' set/get commands remotely.
# @todo Make that logical thing happen with the special methods/operators.
#       Remove them from the following list as they are implemented:<br>
# <code>
# Special methods for any class
# (s: self, o: other) 
#         (n/a) __init__(s, args) object instantiation 
#         (n/a) __del__(s)        called on object demise (refcount becomes 0)
#         __repr__(s)       repr() and `...` conversions
#         __str__(s)        str() and 'print' statement
#         __cmp__(s, o)     implements <, ==, >, <=, <>, !=, >=, is [not]
#         __hash__(s)       hash() and dictionary operations
#         __getattr__(s, name)  called when attr lookup doesn't find <name>
#         __setattr__(s, name, val) called when setting an attr
#                                   (inside, don't use "self.name = value"
#                                    use "self.__dict__[name] = val")
#         __delattr__(s, name)  called to delete attr <name>
#         __call__(self, *args) called when an instance is called as function.
# Operators
#       See list in the operator module. Operator function names are provided
#       with 2 variants, with or without  ading & trailing '__'
#       (eg. __add__ or add).
#       Numeric operations special methods 
#       (s: self, o: other)
#         s+o       =  __add__(s,o)         s-o        =  __sub__(s,o)
#         s*o       =  __mul__(s,o)         s/o        =  __div__(s,o)
#         s%o       =  __mod__(s,o)         divmod(s,o) = __divmod__(s,o)
#         pow(s,o)  =  __pow__(s,o)
#         s&o       =  __and__(s,o)         
#         s^o       =  __xor__(s,o)         s|o        =  __or__(s,o)
#         s<<o      =  __lshift__(s,o)      s>>o       =  __rshift__(s,o)
#         nonzero(s) = __nonzero__(s) (used in boolean testing)
#         -s        =  __neg__(s)           +s         =  __pos__(s)  
#         abs(s)    =  __abs__(s)           ~s         =  __invert__(s)(bitwise)
#         int(s)    =  __int__(s)           long(s)    =  __long__(s)
#         float(s)  =  __float__(s)
#         oct(s)    =  __oct__(s)           hex(s)     =  __hex__(s)
#         coerce(s,o) = __coerce__(s,o)
#         Right-hand-side equivalents for all binary operators exist;
#         are called when class instance is on r-h-s of operator:
#         a + 3  calls __add__(a, 3)
#         3 + a  calls __radd__(a, 3)
#       All seqs and maps, general operations plus: 
#       (s: self, i: index or key)
#         len(s)    = __len__(s)        length of object, >= 0. Length 0==false
#         s[i]      = __getitem__(s,i)  Element at index/key i, origin 0
#       Sequences, general methods, plus: 
#               s[i]=v           = __setitem__(s,i,v)
#               del s[i]         = __delitem__(s,i)
#               s[i:j]           = __getslice__(s,i,j)
#               s[i:j]=seq       = __setslice__(s,i,j,seq)
#               del s[i:j]       = __delslice__(s,i,j)   == s[i:j] = []
#               seq * n          = __repeat__(seq, n)
#               s1 + s2          = __concat__(s1, s2)
#       Mappings, general methods, plus 
#               hash(s)          = __hash__(s) - hash value for dictionary
#                                  references
#               s[k]=v           = __setitem__(s,k,v)
#               del s[k]         = __delitem__(s,k)a
# </code>
import select
import array
import atexit
import os
import socket
import sys
import types
import time
import urllib
import threading

LONG_CLOSE_POLL_WAIT = 0.1
SHORT_CLOSE_POLL_WAIT = 0.01
DEFAULT_CONNECT_TIMEOUT = 3
DEFAULT_TRANSACTION_TIMEOUT = 30

try:
    SocketTimeoutError = socket.timeout
    new_socket = socket.socket
except:
    class CompatibilitySocket(socket._SafetySocket):
        def settimeout(self, value):
            self._timeout = value
            return
    def new_socket(*args):
        return CompatibilitySocket(socket.socket(*args), 3600)
    class BogusException(Exception):
        pass
    SocketTimeoutError = BogusException

from configure import REQUIRED
from configure import get_attribute
from configure import set_attribute
from configure import set_attributes
from edtlib import edt_decode
from debug import dump
from exceptions import EInternalError
from exceptions import EInvalidCommand
from exceptions import EInvalidMessage
from exceptions import ENotImplemented
from exceptions import ERNATimeout
from exceptions import ENoSuchName
from exceptions import current_exception
from ifconfig import ip_address
from security import RExec

# @fixme Part of the Result marshalling hack.
from mpx.lib import Result
from mpx.lib import msglog
from mpx.lib.batch import RnaBatchManager
#hack, until the edt marshalling lib is worked out
from mpx.lib.stream import StreamingTupleWithCallback 

from mpx import properties as props
from os.path import join as jn
from M2Crypto import SSL


#from mpx.lib import node
node_imported = 0
def is_result_dict(result):
    if not isinstance(result, dict):
        return False
    if result.get('__base__') == "Result":
        return True
    return set(result) == set(("cached", "changes", "timestamp", "value"))

def is_exception_result(result):
    return result.exception and result.exception != 'None'    

##
#
# Returns 'Undefined' for entries with marshalling/unmarshalling issues
#
##
class Undefined:
    def __repr__(self):
        return 'Undefined'

##
# Stores a command for use by an object implementing
# <code>ProtocolInterface</code>.
#
class ProtocolCommand:
    ##
    # Initialize the object.
    #
    # @param service  The path to the <code>Node</code> that
    #                 this command is to be sent to.
    #
    # @param method  The method that is to be invoked on the
    #                <code>Node</code> this command is to be
    #                sent to.
    #
    # @param args  Tuple of arguments to be passed to the method
    #              that will be invoked.
    #
    def __init__(self,service,method,args,token=None):
        self.service = service
        self.method  = method
        self.args    = args
        self.token   = token
        return
##
# Stores the result from a command.
#
class ProtocolResult(object):
    ##
    # Initialize the object.
    #
    # @param service  The path to the <code>Node</code>
    #                 that the result came from.
    #
    # @param method  The name of the method invoked on
    #                remote <code>Node</code>.
    #
    # @param result  The result returned by the method invoked.
    #
    # @param exception  Any exception that occured while invoking
    #                   the method.
    #
    def __init__(self, service, method, result, exception=None):
        self.service = service
        self.method  = method
        self.result  = result
        self.exception = exception
        super(ProtocolResult, self).__init__()

## @imports mpx.service.network.rna.RNAHeader

##
# Generic Protocol Interface for communicating
# over a network.
#
class ProtocolInterface(object):
    ##
    # Initialize the object.
    #
    # @param transport  The object used to transport
    #                   information over the network.
    # @param header     The encapsulation of RNA header
    #                   RNAHeader contains 'meta' info about request
    # @see mpx.service.network.rna._protocol_factory()
    #
    # Default constructor is need to participate in factory
    #
    def __init__(self, transport=None, header=None):
        self.header = None
        self.transport = None
        self.setup(transport, header)
        super(ProtocolInterface, self).__init__()

    ##
    # All setting of transport and header after object creation
    def setup(self, transport, header):
        self.transport = transport
        self.header = header

    ##
    # Connect to remote system.
    #
    # @param arg  Argument to be passed to the
    #             transport's <code>connect</code>
    # @default None
    #
    def connect(self):
        self.transport.connect()

    ##
    # Disconnect from a remote system.
    #
    def disconnect(self):
        self.transport.disconnect()

    ##
    # Send a command to remote system.
    #
    # @param command  The {@link ProtocolCommand}
    #                 object to send.
    #
    def send_command(self,command):
        raise ENotImplemented

    ##class _BaseMessage:
    # Receive a command from a remote system.
    #
    # @return The {@link ProtocolCommand} received.
    #
    def recv_command(self):
        raise ENotImplemented

    ##
    # Send a result to a remote system's command.
    #
    # @param command the InvokeCommand object containing the
    #                current context
    # @param result  The {@link ProtocolResult} to
    #                send.
    #
    def send_result(self,command, result):
        raise ENotImplemented

    ##
    # Receive a result from a command sent to a remote
    # system.
    #
    # @return The {@link ProtocolResult} received.
    #class _BaseMessage:
    def recv_result(self):
        raise ENotImplemented


##
# Class for setting up any message to
# be sent or received.
#
# @see mpx.service.network.rna.RNAHeader
class _BaseMessage(object):
    SEP = ':'
    ISEP1 = 3
    ISEP2 = ISEP1 + 6 + 1
    ISEP3 = ISEP2 + 7 + 1
    MSG_TYPE = "MSG"
    CMD_TYPE = "UNSPEC"
    LENGTHFORMAT = "%07d"
    def __init__(self, header):
        self.len = 0
        self.text = ""
        self.buffer = None
        self.command = None
        self.header = header  # the RNAHeader 
        super(_BaseMessage, self).__init__()
    ##
    # Pack message class _BaseMessage:for sending.
    #
    # @param command  The InvokeCommand object representing the
    #                 command being sent.
    #
    # @param text  String representation of dictionary
    #              containing attributes of the command.
    #
    def pack(self, command, data):
        segments = [self.MSG_TYPE]
        segments.append(self.CMD_TYPE)
        segments.append(self.LENGTHFORMAT % len(data))
        segments.append(data)
        self.buffer = array.array("c")
        self.buffer.fromstring(self.SEP.join(segments))
    ##
    # Unpack a message that has been received and store
    # values in self.
    #
    def unpack(self):
        try:
            self.text = self.buffer
            self.len = len(self.text)
            self.buffer = None
        except:
            raise EInvalidMessage
    ##
    # Transfer message for sending into buffer.
    #
    # @return The buffer.
    #
    def tobuffer(self):
        if not self.buffer:
            self.pack(self.command, self.text)
        return self.buffer
    ##
    # Get message from buffer and store values in
    # self.
    #
    # @param buffer  The buffer to get the message
    #                out of.
    #
    def frombuffer(self, buffer):
        self.buffer = buffer
        self.unpack()
    ##
    # Send message in buffer to transport.
    #
    # @param send  Transport to send message to.
    #
    def totransport(self,send):
        # @fixme The name resolution of this send SCARES me. (mevans)
        send(self.buffer)
    ##
    # Get message out of transport and store in buffer.
    #
    # @param recv  Transport to get message out of.
    # @param timeout  Time to await reply before timing
    #                 out.
    #
    def fromtransport(self, recv, timeout):
        buffer = array.array('c')
        recv(self.header.len, timeout, buffer)            # "..."
        self.buffer = buffer
    ##
    # Format the execption for the client.  This should format
    # the exception in such a way the client will be able to understand
    # the type of exception, and any related messages associated with it.
    # This implemenation is used by 'Python' clients that handle executing 
    # code to duplicate the exception on the client side.
    # 
    # @param e   The Exception object or the 'string' type Exception
    # @param args The arguments associated with the Exception
    # @param tbo The 'Trace Back Object'
    #
    #
    import types
    def formatException(self, e, args, tbo):
        try:
            class_name = 'Exception'
            module_name = 'exceptions'
            if type(e) == types.StringType:
                assert not args
                args = (e,)
            elif type(e) in (types.ClassType,types.TypeType):
                class_name = e.__name__
                module_name = e.__module__
            else:
                class_name = e.__class__.__name__
                module_name = e.__class__.__module__
            if module_name == 'exceptions':
                exception = "raise %s%r" % (class_name, args)
            else:
                exception = "import %s\nraise %s.%s%r" % (module_name, 
                                                          module_name, 
                                                          class_name, args)
        except:
            exception = ("import mpx.lib.exceptions\n"
                         "raise mpx.lib.exceptions.EInternalError("
                         "'RNA failed to format actual exception')")
            msglog.exception(prefix="handled")
        return exception

# Holds a method invocation message.
#
# @implements ProtocolCommand
#
class _InvokeCommand(_BaseMessage):
    CMD_TYPE = 'INVOKE'
    SERIVCE_KEY = 'service'
    METHOD_KEY = 'method'
    ARGS_KEY = 'args'
    TOKEN_KEY = 'token'
    def __init__(self, header):
        self.service = None    # '/services/logger'
        self.method = None    # 'get_range'
        self.args = None    # '(column_name,start,end)'
        self.token = None    # A security token.
        super(_InvokeCommand, self).__init__(header)
    def __repr__(self):
        return "<%s at %#x>" %(self, id(self))
    def __str__(self):
        typename = self.__class__.__name__
        return "%s(%r, %r, %r)" % (typename, self.service, 
                                   self.method, self.args)
    ##
    # Pack method invocation for sending.
    #
    # @param service  The path to the <code>Node</code> to
    #                 invoke the method on.
    #
    # @param method  The name of the method to invoke.
    #
    # @param args  String representation of a tuple of
    #              arguments to be passed to the method.
    #
    # @param token  Security token.
    # @default None
    #
    # @see _BaseMessage#pack
    #
    def pack(self, command):
        command_dict = {self.SERIVCE_KEY: command.service,
                        self.METHOD_KEY: command.method,
                        self.ARGS_KEY: command.args,
                        self.TOKEN_KEY: repr(command.token)}
        return super(_InvokeCommand, self).pack(command, repr(command_dict))
    ##
    # Unpack a method invocation received and store
    # value in self.
    #
    # @see _BaseMessage#unpack
    #
    def unpack(self):
        result = super(_InvokeCommand, self).unpack()
        command_dict = eval(self.text.tostring())
        self.service = command_dict[self.SERIVCE_KEY]
        self.method = command_dict[self.METHOD_KEY]
        self.args = command_dict[self.ARGS_KEY]
        self.token = command_dict[self.TOKEN_KEY]
        return result
    ##
    # Return a tuple that represents the arguments needed for this command
    def get_arguments(self):
        return eval(self.args)

##
# Holds result from a method
# invocation message.
#
# @implements ProtocolResult
#
class _InvokeResult(_BaseMessage):
    CMD_TYPE = 'RESULT'
    SERIVCE_KEY = 'service'
    METHOD_KEY = 'method'
    RESULT_KEY = 'result'
    EXCEPTION_KEY = 'exception'
    def __init__(self, header):
        self.service = None    # '/services/logger'
        self.method = None    # 'get_range'
        self.result = None    # evaluatable result string, may raise
        self.exception = None
        super(_InvokeResult, self).__init__(header)
    def __repr__(self):
        if self.exception:
            value = "error: %s" % self.exception
        else:
            value = "result: %s" % self.result
        return "<%s %r at %#x>" % (self, value, id(self))
    def __str__(self):
        typename = self.__class__.__name__
        return "%s(%r, %r, %r)" % (typename, self.service, 
                                   self.method, self.args)
    ##
    # Package a result for sending.
    #
    # @param service  The path to the <code>Node</code> that
    #                 the result came from.
    # @param method  The name of the method that was invoked.
    # @param result  String representation of result, will be
    #                evaluated.
    # @param exception  String representation of any exception
    #                   that may have ocurred while invoking
    #                   the command.
    #
    # @see _BaseMessage#pack
    #
    def pack(self,command,result): # Exception!
        if getattr(result.result, '_has_magnitude_interface', 0):
            result.result = result.result.as_magnitude()
        elif isinstance(result.result, StreamingTupleWithCallback):
            result.result = tuple(result.result)
        command_dict = {self.SERIVCE_KEY: command.service,
                        self.METHOD_KEY: command.method,
                        self.RESULT_KEY: repr(result.result),
                        self.EXCEPTION_KEY: result.exception}
        result.result = repr(command_dict)
        return super(_InvokeResult, self).pack(command, result.result)
    ##
    # Unpack a result that has been received and
    # store values in self.
    #
    # @see _BaseMessage#unpack
    #
    def unpack(self):
        super(_InvokeResult, self).unpack()
        command_dict = eval(self.text.tostring())
        self.service = command_dict[self.SERIVCE_KEY]
        self.method = command_dict[self.METHOD_KEY]
        self.result = command_dict[self.RESULT_KEY]
        self.exception = command_dict[self.EXCEPTION_KEY]

_test = """
from mpx.lib import node
n = node.as_node('mpx://splay/services/time')
print n.get()
x = node.as_node('xmlrna://splay/services/time')
print x.get()
x.getx()
y = node.as_node('xmlrnas://splay/services/time')
print y.get()
y.getx()
"""

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme
# 0. mpx/lib/xmlrpclib/__init__ CSafe MARSHELLAR!
# 1. Rearrange to get rid of race conditions.
# 3. NOT SURE I LIKE CONFIGURE() METHOD.  DO SOME OBJs REQUIRE LATE "BINDING"?
# @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme @fixme
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

import xmlrpclib
import base64

class HTTPTransport:
    DEFAULT_PORT = 80
    class AuthTransport(xmlrpclib.Transport):
        def __init__(self,username,password):
            self.username = username
            self.password = password
        def request(self, host, handler, request_body, verbose=0):
            # issue XML-RPC request
            h = self.make_connection(host)
            if verbose:
                h.set_debuglevel(1)
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_user_agent(h)
            self.send_authorization_header(h)  
            self.send_content(h, request_body)
            errcode, errmsg, headers = h.getreply()
            if errcode != 200:
                raise xmlrpclib.ProtocolError(
                    host + handler,
                    errcode, errmsg,
                    headers
                    )
            self.verbose = verbose
            return self.parse_response(h.getfile())                
        def send_authorization_header(self,connection):
            h = base64.encodestring('%s:%s' % (self.username,self.password))
            connection.putheader('Authorization',' Basic %s' % h)
            return
    def __init__(self,**keywords):
        self.configure(keywords)
        return
    def configure(self,config):
        orig = config
        config = {}
        config.update(orig)
        set_attribute(self, 'host', REQUIRED, config)
        set_attribute(self, 'port', int(self.DEFAULT_PORT), config, int)
        set_attribute(self, 'scheme', 'http', config, int)
        set_attribute(self, 'node', REQUIRED, config)
        set_attribute(self, 'transport', None, config)
        self._uri = "%s://%s:%s/XMLRPCv2/RNA%s" % (
            self.scheme, self.host, self.port, os.path.join("/",self.node)
            )
        set_attribute(self, 'password', '', config)
        set_attribute(self, 'username', '', config)
        t = self.AuthTransport(self.username, self.password)
        config.update({'transport':t})
        set_attribute(self, 'transport', REQUIRED, config)
        self._server =  xmlrpclib.Server(self._uri, transport=t, verbose=0)
        return
    def connect(self):
        return
    def disconnect(self):
        return

class HTTPSTransport(HTTPTransport):
    DEFAULT_PORT = 443
    class AuthTransport(xmlrpclib.SafeTransport):
        def __init__(self,username,password):
            self.username = username
            self.password = password
        def request(self, host, handler, request_body, verbose=0):
            # issue XML-RPC request
            h = self.make_connection(host)
            if verbose:
                h.set_debuglevel(1)
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_user_agent(h)
            self.send_authorization_header(h)  
            self.send_content(h, request_body)
            errcode, errmsg, headers = h.getreply()
            if errcode != 200:
                raise xmlrpclib.ProtocolError(
                    host + handler,
                    errcode, errmsg,
                    headers
                    )
            self.verbose = verbose
            return self.parse_response(h.getfile())                
        def send_authorization_header(self,connection):
            h = base64.encodestring('%s:%s' % (self.username,self.password))
            connection.putheader('Authorization',' Basic %s' % h)
            return
    def configure(self,config):
        set_attribute(self, 'scheme', 'https', config, int)
        HTTPTransport.configure(self, config)
        return

class XMLRNAProtocol(ProtocolInterface):
    def __init__(self, transport=None, header=None):
        ProtocolInterface.__init__(self,transport, header)
        return
    def __repr__(self):
        return 'mpx.lib.rna.XMLRNAProtocol(%s)' % self.transport
    def extract_tag(self, line, response_dict):
        tag, line = line.split('>',1)
        tag = tag[1:]
        line = line[:-len(tag)-3]
        if line and (line[0] in ('"',"'")):
            # @fixme Use unrepr.py which is safer and in the public domain.
            line = eval(line)
        response_dict[tag] = line
        return
    def extract_exception(self, fault):
        exception_response = {
            'module':None,
            'name':None,
            'str':None,
            'traceback':None,
            }
        state = 'SEEK'
        for line in fault.faultString.split("\n"):
            line = line.strip()
            if line.startswith("<exception>"):
                assert state == 'SEEK'
                state = 'TAGS'
                continue
            if line.startswith("</exception>"):
                state = 'DONE'
                continue
            assert state == 'TAGS'
            self.extract_tag(line, exception_response)
        assert state == 'DONE'
        return exception_response
    def rmi(self, node, method, *args):
        try:
            return getattr(self.transport._server, method)(*args)
        except xmlrpclib.Fault, fault:
            if fault.faultCode == 1:
                try:
                    exception = fault
                    exception_response = self.extract_exception(fault)
                    module = exception_response['module']
                    klass =  exception_response['class']
                    text =  exception_response['str']
                    tb =  exception_response['traceback']
                    if module:
                        exec("import %s" % module)
                    if klass:
                        klass = eval(klass)
                        if not issubclass(klass, Exception):
                            raise ESecurityError(
                                "%r is not a subclass of Exception." %
                                klass
                                )
                        if text:
                            exception = eval("%s(%r)" % (klass, text))
                except:
                    import msglog
                    msglog.exception()
                    # fall through to reraise the original exception.
                else:
                    # @fixme Associate the traceback with the exception...
                    raise exception
        # Unrecognized fault, or exception we failed to parse.
        raise fault

##
# Class for sending and receiving commands from a
# remote system using text representations of objects.
#
# @implements ProtocolInterface
#
class SimpleTextProtocol(ProtocolInterface):
    ##
    # @see ProtocolInterface#__init__
    #
    def __init__(self, transport=None, header=None):
        self.close_poll_wait = LONG_CLOSE_POLL_WAIT
        self.synclock = threading.RLock()
        self.setup(transport, header)
        self._in_connect_err = False
        return
    ##
    # Get a string representation of this object.
    #
    # @return String representation of this object.
    def __repr__(self):
        return 'mpx.lib.rna.SimpleTextProtocol(%s)' % self.transport

    ##
    # @see #__repr__
    #
    def __str__(self):
        return self.__repr__()

    ##
    # @see ProtocolInterface#send_command
    #
    def send_command(self,command):
        
        c = _InvokeCommand(self.header)
        c.pack(command)
        c.totransport(self.transport.send)
        return
    ##
    # @see ProtocolInterface#recv_command
    #
    def recv_command(self):
        c = _InvokeCommand(self.header)
        c.fromtransport(self.transport.recv,-1)
        c.unpack()
        return c

    ##
    # @see ProtocolInterface#send_result
    #
    def send_result(self,command, result):
        r = _InvokeResult(self.header)
        r.pack(command,result)
        r.totransport(self.transport.send)
        return
    ##
    # @see ProtocolInterface#recv_result
    #
    def recv_result(self):
        # read the header to knonw how and how
        # much to read from transport ....
        # @note I'm not sure about this ...!!
        header = self.transport.read_header()
        r = _InvokeResult(header)
        r.fromtransport(self.transport.recv,-1)
        r.unpack()
        return r
    def _connect_transport(self):
        if self.transport.socket:
            # Some odd code to catch and handle sockets 
            # which have been closed by the server-side 
            # but not detected as closed by the client.
            fd = self.transport.socket.fileno()
            if fd == -1:
                if self.transport.debug:
                    message = "Disconnect %s transport: socket FD == -1"
                    msglog.debug(message % self)
                self.transport.disconnect()
            elif fd in select.select([fd], [], [], self.close_poll_wait)[0]:
                no_bytes= self.transport.flush_read_data()
                if not no_bytes:
                    if self.transport.debug:
                        message = "Disconnect %s transport: empty string."
                        msglog.debug(message % self)
                    self.transport.disconnect()
                else:
                    msglog.warn("Ignoring %s data: %r." % (self, no_bytes))
            else:
                self.close_poll_wait = SHORT_CLOSE_POLL_WAIT
        # Seemingly redundant check catches and 
        # reconnects connections closed above too.
        if not self.transport.socket:
            self.close_poll_wait = LONG_CLOSE_POLL_WAIT
            try:
                self.transport.connect()
            except:
                # Should not need to call this here, 
                # but it may be required for cleanup 
                # of SRNA failed connection and, until 
                # it's been verified that is not the case, 
                # it will continue to be called here.
                if not self._in_connect_err or self.transport.debug:
                    msglog.warn("Connect transport for %s failed." % self)
                    self._in_connect_err = True
                self.transport.disconnect()
                # Re-raise exception for additional handling 
                # and so caller knows invocation failed.
                raise
            else:
                self.transport.socket.setsockopt(socket.SOL_SOCKET, 
                                                 socket.SO_KEEPALIVE, 1)
        self._in_connect_err = False
        
    def _exchange_command(self, command):
        try:
            self.send_command(command)
            result = self.recv_result()
        except:
            message = "Exchange command failed for %s.  Exception follows."
            msglog.warn(message % self)
            msglog.exception(prefix="handled")
            self.transport.disconnect()
            raise
        return result
    def rmi(self, node, method, *args):
        command = ProtocolCommand(node, method, repr(args))
        self.synclock.acquire()
        try:
            self._connect_transport()
            result = self._exchange_command(command)
        except SocketTimeoutError:
            msglog.exception(prefix="handled")
            raise ERNATimeout()
        finally:
            self.synclock.release()
        try:
            # Could validate against the command...
            if is_exception_result(result):
                exec(result.exception)
            while 1:
                try:
                    result = eval(result.result)
                    break
                except NameError, error:
                    msglog.log('broadway',msglog.types.WARN,error)
                    import re
                    pattern  = 'name \'(.*)\' is not defined'
                    err_msg = '%s' % error
                    match = re.search(pattern, err_msg)
                    if match is None:
                        msg = 'No match found for pattern \'%s\' in error string \'%s\'' % (pattern, err_msg)
                        msglog.log('broadway',msglog.types.ERR,msg)
                        break
                    if match.group(1) == 'nan':
                        nan = float('nan')
                    else:
                        vars()[match.group(1)] = Undefined()
            # unmarshal
            if isinstance(result, dict):
                if result.has_key('edt__typ'):
                    result = edt_decode(result)
                elif is_result_dict(result):
                    result = Result.from_dict(result)
        except:
            msglog.exception()
            raise
        return result

class _RemoteMethod:
    def __init__(self, service, protocol, method):
        self.service = service
        self.protocol = protocol
        self.method = method
        return
    def __call__(self, *args):
        return self.protocol.rmi(self.service, self.method, *args)

class CachingFacade(object):
    """
        Base class for Facade types wishing to cache data 
        types of remote object attributes.
        
        Method names starting with 'cached' are inspectors.
        Inspectors ending with plural terms return corresponding 
        sets, whereas those ending with singular terms require 
        a name parameter and indicate whether that parameter 
        belongs to the corresponding set.
        
        Method names starting with 'cache' are modifiers, each 
        of which requires a name parameter to be added to the 
        apppropriate cache.
    """
    _cached_resources = {}
    def _cached_resource(klass, resource):
        return resource in klass._cached_resources
    _cached_resource = classmethod(_cached_resource)
    def _cache_resource(klass, resource):
        defaults = (set(), set(), set())
        return klass._cached_resources.setdefault(resource, defaults)
    _cache_resource = classmethod(_cache_resource)
    def __init__(self, resource):
        self._cached_attrs = self._cache_resource(resource)
        super(CachingFacade, self).__init__()
    def _cached_types(self):
        """
            Get typle of sets containing method names, property 
            names, and attribute names, in that order.
            
            Members of the returned tuple are set type objects 
            meant to be modified directly if desired.
        """
        return self._cached_attrs
    def _cached_methods(self):
        """
            Get set of cached method names.
            
            Returned set may be manipulated to add and/or remove 
            method names directly.  All object attributes that 
            are callable are considered methods.
        """
        return self._cached_types()[0]
    def _cached_properties(self):
        """
            Get set of cached property names.
            
            Returned set may be manipulated to add and/or remove 
            property names directly.  All object attributes that 
            are not callable are considered methods.
        """
        return self._cached_types()[1]
    def _cached_attributes(self):
        """
            Get set of cached attribute names.
            
            Returned set may be manipulated to add and/or remove 
            attributes names directly.  In theory this set is the 
            union of all methods and all properties.  In actuallity 
            the two may not always be true because Facades may 
            determine the existence of an attribute without knowing 
            whether the attribute callable or not. 
        """
        return self._cached_types()[2]
    def _cached_method(self, name):
        """
            Test whether attribute named 'name' is a cached method.
        """
        return name in self._cached_methods()
    def _cached_property(self, name):
        """
            Test whether attribute named 'name' is a cached property.
        """
        return name in self._cached_properties()
    def _cached_attribute(self, name):
        """
            Test whether attribute named 'name' is a cached attribute.
        """
        return name in self._cached_attributes()
    def _cache_method(self, name):
        """
            Add attribute named 'name' to list of method attributes.
            
            Added method names are automatically added to list of 
            attributes and removed from list of properties.
        """
        self._cached_methods().add(name)
        self._cached_properties().discard(name)
        self._cache_attribute(name)
    def _cache_property(self, name):
        """
            Add property named 'name' to list of property attributes.
            
            Added property names are automatically added to list of 
            attributes and removed from list of methods.
        """
        self._cached_properties().add(name)
        self._cached_methods().discard(name)
        self._cache_attribute(name)
    def _cache_attribute(self, name):
        """
            Add attribute named 'name' to list of attributes.
        """
        self._cached_attributes().add(name)

class _uninitialized:
    pass
UNINITIALIZED=_uninitialized()

class NodeFacade(CachingFacade):
    """
        Create facade for remote node resource identified 
        by path 'path'.  
        
        @param path
            Fully qualified resource identifier for remote 
            resource.  Typical URL form identifier such as 
            mpx://hostname:5150/path-to-service.
        @param service 
            The path to the node that this will be a facade for.
        @param protocol
            Object that implements <code>ProtocolInterface</code> that 
            will be used by the <code>NodeFacade</code> to interact 
            with a potentially remote system.
        
        Facades proxy interactions with remote object transparently.
        Attempts to access and manipulate attributes on a facade 
        are caught and used to create and manipulate proxies for 
        remote methods, and values of remote properties.
    """
    @property
    def parent(self):
        """parent attribute returns a NodeFacade to the remote node's
        parent Node.  If the remote node is '/', then parent returns
        None. (see CSCtd62463)
        """
        if self.__parent is UNINITIALIZED:
            parent_url = os.path.dirname(self.__path)
            if parent_url[-1] == ':':
                self.__parent = None
            else:
                self.__parent = NodeFacade(parent_url,
                                           os.path.dirname(self.__service),
                                           self.__protocol)
        return self.__parent
    def __init__(self, path, service, protocol):
        self.__parent = UNINITIALIZED
        self.__path = path
        self.__service = service
        self.__protocol = protocol
        # Create 'name' property so every attempt to view 
        # node's name does not result in remote method 
        # invocation.  This is acceptable in part because 
        # the facade's link to its remote node is broken 
        # if that node were renamed.  Potential proplem 
        # created in that renamed node error will not occur  
        # until subsequent invocation.
        if self.__service == "/":
            self.name = "/"
        else:
            prefix,sep,suffix = self.__service.rpartition("/")
            self.name = urllib.unquote_plus(suffix)
        super(NodeFacade, self).__init__(path)
    def __getattr__(self,name):
        return self.getattr(name)
    def callable(self, attr):
        # Todo: Depecreate this method.  Was added 
        # when existing has_method() method overlooked.
        return self.has_method(attr)
    def has_cov(self):
        return False
    def changing_cov(self):
        return False
    def get_destination(self):
        return self.__protocol.transport.network_location()
    def get_batch_manager(self):
        destination = self.get_destination()
        return RnaBatchManager.get_manager(destination)
    def hasattr(self, name):
        if not self._cached_attribute(name):
            if self.__invoke_method("hasattr", name):
                self._cache_attribute(name)
        return self._cached_attribute(name)
    def getattr(self, name):
        """
            Get value of attribute named 'name'.
            
            If attribute is method type, remote method instance 
            will be returned.  If attribute exists but is not 
            callable, the value is retrieved from the remote 
            instance.  If the remote object does not have an 
            attribute by that name, an Attribute Error is thrown.
        """
        if not self.hasattr(name):
            raise AttributeError("%s has no attribute %r" % (self, name))
        elif self.has_method(name):
            value = self.get_method(name)
        else:
            value = self.__invoke_method("getattr", name)
        return value
    def setattr(self, attr, value):
        return self.__invoke_method("setattr", attr, value)
    def has_method(self, name):
        if not self._cached_method(name):
            if not self._cached_property(name):
                if self.hasattr(name):
                    if self.__invoke_method("has_method", name):
                        self._cache_method(name)
                    else:
                        self._cache_property(name)
        return self._cached_method(name)
    def get_method(self, name):
        if not self.has_method(name):
            if self.hasattr(name):
                raise TypeError("%s attribute %r not callable" % (self, name))
            else:
                raise AttributeError("%s has no attribute %r" % (self, name))
        return self.__remote_method(name)
    def as_node_url(self):
        return self.__path
    ##
    # TODO: The existence of these methods is problematic 
    # when acting as facade for remote ConfigurableNode instance.
    # Such nodes do not support the children oriented methods and 
    # should therefore raise AttibuteErrors when accessed.  Future 
    # iteration may specialize availability based on target node type.
    def has_child(self, name):
        path = self.__child_path(name)
        if not self._cached_resource(path):
            # No type caches exist for Node with that path.
            if self.__invoke_method("has_child", name):
                # Verified child exist, initialize caches for it.
                self._cache_resource(path)
        return self._cached_resource(path)
    def get_child(self, name):
        if not self.has_child(name):
            # Raises exception if no such child.  
            # Fixme: auto-discovery
            raise ENoSuchName(name)
        # Ugly...
        from mpx.lib import node
        return node.as_node(self.__child_path(name))
    def children_nodes(self):
        return [self.get_child(name) for name in self.children_names()]
    def __child_path(self, name):
        """
            Get path for remote child node named 'name'.
            
            This is a convenience function used to generate paths 
            based on children names.  Note that this method does 
            no validation, and the path returns it not gauranteed 
            to exist.
        """
        path = self.__path 
        if path[-1] != '/':
            path += '/'
        return path + name
    def __remote_method(self, name):
        """
            Get Remote Method stub proxy for method named 'name'.
        """
        return _RemoteMethod(self.__service, self.__protocol, name)
    def __invoke_method(self, name, *args, **kw):
        """
            Call Remote Method stub for method named 'name', 
            passing variable length arguments 'args', and 
            keyword values 'kw'.
        """
        method = self.__remote_method(name)
        return method(*args, **kw)
    ##
    # Required so the Alias as_node() of a NodeFacade works correctly.
    def _public_interface(self):
        return self
    def __repr__(self):
        return 'mpx.lib.rna.NodeFacade(%r, %r,%r)' % (repr(self.__path), 
                                                      repr(self.__service), 
                                                      repr(self.__protocol))
    def __str__(self):
        typename = type(self).__name__
        return "%s(%r)" % (typename, self.__path)

##
# Generic Interface for all Transport
# classes.
#
class TransportInterface:
    ##
    # Send information to a remote <code>Node</code>.
    #
    # @param buffer  Buffer containing data to be sent
    #                to the remote <code>Node</code>.
    #
    def send(self,buffer):
        raise ENotImplemented

    ##
    # Receive information sent from a remote <code>Node</code>.
    #
    # @param len  The length of the information to be received.
    # @param timeout  The number of seconds to wait before timeout.
    # @param buffer  The buffer to put the result in.  Defaults to None.
    #
    def recv(self,len,timeout,buffer=None):
        raise ENotImplemented

    def drain(self):
        return

    ##
    # Read the RNAHeader from transport stream
    #
    # @see rna.service.network.rna#RNAHeader
    #
    def read_header(self):
        return

    ##
    # Called by a client to connect to a server.
    def connect(self):
        return

    ##
    # Called by a service to listen for clients.
    def listen(self, backlog=5):
        return

    ##
    # Called by a service to accept a connection from a client.
    def accept(self):
        return

##
# @implements TransportInterface
#
class StringTransport:
    def __init__(self):
        self.buffer = None

    def configure(self,dict):
        return

    def connect():
        return

    def disconnect():
        return

    ##
    # @see TransportInterface#send
    #
    def send(self,buffer):
        self.buffer = array.array('c')
        if type(buffer) == types.StringType:
            self.buffer.fromstring(buffer)
        else:
            self.buffer.extend(buffer)
        return

    ##
    # @see TransportInterface#send
    #
    def recv(self,len,timeout=0,buffer=None):
        if buffer == None:
            buffer = array.array('c')
        for i in range(0,len):
            buffer.append(self.buffer.pop(0))
        return buffer

    def drain(self):
        return


##
# @implements TransportInterface
class SimpleSocketTransport(object):
    ##
    # Initialize object.
    #
    # @param **keywords  Dictionary to configure
    #                    object.
    # @see #configure
    #
    def __init__(self,**keywords):
        self.socket = None
        self.listen_socket = None
        self.configure(keywords)
        super(SimpleSocketTransport, self).__init__()    
    def network_location(self):
        raise EAbstract
    ##
    # Get a string representaion of object.
    #
    # @return String representing object.
    #
    def __repr__(self):
        return ('mpx.lib.rna.SimpleSocketTransport(self.socket=%s,debug=%s)' %
                (repr(self.socket), repr(self.debug)))
    ##
    # @see #__repr__
    #
    def __str__(self):
        return self.__repr__()
    def __del__(self):
        self.destroy()
        return
    def destroy(self):
        for s in (self.socket, self.listen_socket):
            try:
                if s is not None:
                    s.shutdown(2)
            except:
                pass
        return
    ##
    # Configure object.
    #
    # @param config  Dictionary containing configuration.
    #
    def configure(self,config):
        set_attribute(self, 'debug', 0, config, int)
        return
    ##
    # Derived classes use this to implement the specific socket connection.
    def _bind_accept(self):
        raise EAbstract(self._connect)
    ##
    # Called by a service to listen for clients.
    def listen(self, backlog=5):
        self.listen_socket = self.socket
        self._bind_listen()
        self.listen_socket.listen(backlog)
        return
    ##
    # Servers call this to wait for a connection on a socket.  Self.socket
    # is set to the accepted socket.
    def accept(self):
        self.socket, self.address = self.listen_socket.accept()
        return self.socket, self.address
    ##
    # Instanciate a new socket object and connect it to the server.
    # @abstract
    def _connect(self):
        raise EAbstract(self._connect)
    ##
    # Client's call the to connect to an RNA server.
    def connect(self):
        if self.debug:
            print "%s.connect()" % self
        if self.socket:
            self.disconnect()
        self._connect()
        if self.debug:
            print "    self.socket =",self.socket
        return
    ##
    # Disconnect from remote system.SimpleSocketTransport
    #
    def disconnect(self):
        if self.debug:
            print "disconnect()"
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None
        elif self.debug:
            msglog.debug("mpx.lib.rna SimpleSocketTransport disconnect():"
                         "tried to close socket, but no socket to close!")
        return
    ##
    # Send message to remote system.
    #
    # @param buffer  Buffer containing message
    #                to send.
    #
    # @see TransportInterface#send
    #
    def send(self, buffer):
        if self.debug:
            print "send()"
        if not isinstance(buffer, str):
            buffer = buffer.tostring()
        sent = self.socket.send(buffer)
        if self.debug:
            dump(buffer, hdr=' > ')
        return sent
    ##
    # Receive message from remote system.
    #
    # @param length  The length of the message to
    #                receive.
    # @param timeout  The amount of time to wait for the
    #                 message before timing out.
    # @default 0  Ignore timeout.
    #
    # @param buffer  Buffer to put message into.
    # @default None
    #
    # @return Buffer containing message.
    def recv(self, length, timeout=0, buffer=None):        
        if self.debug:
            print "recv(", length, timeout, ")"
        ## if buffer not specified, then create
        ## a default buffer of type char
        if buffer == None:
            buffer = array.array("c")
        if self.debug:
            print "Expecting %d bytes" % length
        targetsize = len(buffer) + length
        while len(buffer) < targetsize:
            bytes = self.socket.recv(length)
            if bytes:
                length -= len(bytes)
            else:
                break
            buffer.fromstring(bytes)
        if self.debug:
            dump(buffer, hdr=' < ')            
        return buffer
    ##
    # Read RNAHeader from stream
    # @see TransportInterface#read_header
    #
    def read_header(self):
        from mpx.service.network.rna import RNAHeader
        return RNAHeader(self.socket)
    def drain(self):
        return

##
# This represents a socket session.  It is a partial reimplementation
#   of the SimpleSocketTransport, but does not have any of the methods
#   that are just used by a server.  This was done to facilitate 
#   multithreading of a socket service, not combining methods used by 
#   a server waiting for session requests with methods used by an actual
#   session into one object.
class SimpleSocketSession:
    def __init__(self,connection,addr=None,**keywords):
        self.socket = connection
        self.addr = addr
        self.configure(keywords)
        return
    def __repr__(self):
        return ('mpx.lib.rna.SimpleSocketSession(self.socket=%s,debug=%s)' %
                (repr(self.socket), repr(self.debug)))
    def __str__(self):
        return self.__repr__()
    def __del__(self):
        self.destroy()
        return
    def destroy(self):
        socket = self.socket
        self.socket = None
        try:
            if socket is not None:
                socket.shutdown(2)
        except:
            pass
        return
    def configure(self,config):
        set_attribute(self, 'debug', 0, config, int)
        return
    def _connect(self):
        raise EAbstract(self._connect)
    def connect(self):
        if self.debug:
            print "%s.connect()" % self
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None
        self._connect()
        if self.debug:
            print "    self.socket =",self.socket
        return
    def disconnect(self):
        if self.debug:
            print "disconnect()"
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None
        else:
            self.socket = None
            from mpx.lib import msglog
            msg = ('mpx.lib.rna SimpleSocketSession disconnect(): ' + 
                   'tried to close socket, but no socket to close!')
            msglog.log('broadway',msglog.types.WARN,msg)
        return
    def send(self,buffer):
        if self.debug:
            print "send()"
        if type(buffer) != types.StringType:
            buffer = buffer.tostring()
        self.socket.send(buffer)
        if self.debug:
            dump(buffer, hdr=' > ')
        return
    def recv(self,length,timeout=0,buffer=None):        
        if self.debug:
            print "recv(",length,timeout,")"
        if buffer == None:
            buffer = array.array('c')
        bytes_read = 0
        if self.debug:
            print "Expecting %d bytes" % length
        while (length):
            # get the next block
            s = self.socket.recv(length)
            # if block read is null, then
            # break out of loop
            if not s:
                break            
            # keep a count of the total bytes read
            length -= len(s)
            # append to output buffer
            buffer.fromstring(s)
        if self.debug:
            dump(buffer, hdr=' < ')            
        return buffer
    def read_header(self):
        from mpx.service.network.rna import RNAHeader
        return RNAHeader(self.socket)
    def drain(self):
        return
##
# @implements TransportInterface
class SimpleSocketService:
    ##
    # Initialize object.
    #
    # @param **keywords  Dictionary to configure
    #                    object.
    # @see #configure
    #
    def __init__(self,**keywords):
        self.debug = 0
        self.socket = None
        self.configure(keywords)
        return
    def __repr__(self):
        return ('mpx.lib.rna.SimpleSocketService(self.socket=%s,debug=%s)' %
                (repr(self.socket), repr(self.debug)))
    def __str__(self):
        return self.__repr__()
    def __del__(self):
        self.destroy()
        return
    def destroy(self):
        socket = self.socket
        self.socket = None
        try:
            if socket is not None:
                socket.shutdown(2)
        except:
            pass
        return
    def configure(self,config):
        set_attribute(self, 'debug', 0, config, int)
        self.debug = 1
        return
    def _bind_accept(self):
        raise EAbstract(self._bind_accept)
    def listen(self, backlog=5):
        self._bind_listen()
        self.socket.listen(backlog)
        return
    ##
    # Servers call this to wait for a connection on a socket.  Self.socket
    # is set to the accepted socket.
    def accept(self):
        return self.socket.accept()
    def accept_session(self):
        conn,addr = self.accept()
        if self.debug > 1:
            debug = 1
        else:
            debug = 0
        return SimpleSocketSession(conn, addr, debug=debug)

##
# @implements TransportInterface
class SimpleTcpTransport(SimpleSocketTransport):
    DEFAULT_PORT = 5150
    def __init__(self, **kw):
        self.host = kw.get("host", None)
        self.port = kw.get("port", self.DEFAULT_PORT)
        super(SimpleTcpTransport, self).__init__(**kw)
    def network_location(self):
        return (self.host, self.port)
    ##
    # Get a string representaion of object.
    #
    # @return String representing object.
    #
    def __repr__(self):
        return ('mpx.lib.rna.SimpleTcpTransport(host=%s,port=%s,debug=%s)' %
                (repr(self.host), repr(self.port), repr(self.debug)))
    ##
    # Configure object.
    #
    # @param config  Dictionary containing configuration.
    # @key host  The address of the host to connect to.
    # @required
    # @key port  The port to connect to on the host.
    # @default  5150
    # @key debug  Output debugging information.
    # @value 0;1
    # @default 0
    #
    def configure(self,config):
        SimpleSocketTransport.configure(self, config)
        set_attribute(self, 'interface', 'eth0', config)
        if self.interface is None:
            default_host = REQUIRED
        else:
            default_host = ip_address(self.interface)
        set_attribute(self, 'host', default_host, config)
        set_attribute(self, 'port', self.DEFAULT_PORT, config, int)
        self.connect_timeout = DEFAULT_CONNECT_TIMEOUT
        self.transaction_timeout = DEFAULT_TRANSACTION_TIMEOUT
        return
    def _connect(self):
        self.socket = None
        sock = new_socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.connect_timeout)
            sock.connect((self.host, self.port))
            sock.settimeout(self.transaction_timeout) # TOO LONG!
        except:
            sock.close()
            raise
        else:
            self.socket = sock
        return
    def _bind_listen(self):
        ##
        # Socket ready to accept connections
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET,
                                      socket.SO_REUSEADDR, 1)
        self.listen_socket.bind((self.host, self.port))
        sockname = self.listen_socket.getsockname()
        ##
        # The local host address accepting connections.
        self.__bound_address = sockname[0]
        ##
        # The local port on the local host address accepting connections.
        self.__bound_port = sockname[1]
        return
    def bound_port(self):
        if hasattr(self, '_SimpleTcpTransport__bound_port'):
            return self.__bound_port
        return None
    def flush_read_data(self):
        # This function assumes that there is data to be read
        bytes = self.socket.recv(4096)
        return len(bytes)

class SrnaClientTransport(SimpleTcpTransport):
    """ One instance of this class per remote RNA host NBM."""
    SSLVER_DEF = 'sslv23'
    def __init__(self, **kw):
        self.ssl_ctx = None
        super(SrnaClientTransport, self).__init__(**kw)
        return
    def destroy(self):
        self.disconnect()
        if self.ssl_ctx:
            try:
                self.ssl_ctx.close()
            except:
                msglog.exception(prefix="handled")
        self.ssl_ctx = None
    def __repr__(self):
        return ('mpx.lib.rna.SrnaClientTransport(host=%s,port=%s,debug=%s)' %
                (repr(self.host), repr(self.port), repr(self.debug)))
    def configure(self, config):
        SimpleTcpTransport.configure(self, config)
        set_attribute(self, 'security_level', 'NoSec', config)
        msglog.log('broadway', msglog.types.INFO, 'SrnaClientTransport.'\
                   'configure: interface is %s' % self.interface)
        self.cert_path = eval('props.SRNA_CERT_%s' % self.interface)
        self.key_path = eval('props.SRNA_KEY_%s' % self.interface)
        self.cacert_path = props.SRNA_CACERT
        return
    def _connect(self):
        # We expect to connect only very rarely (usually at boot time), so
        # put all Context init code in here:
        if self.ssl_ctx:
            self.ssl_ctx.close()
        self.ssl_ctx = None
        # else, use default cipher from M2Crypto, allegedly "strong"...
        try:
            self.ssl_ctx = SSL.Context(self.SSLVER_DEF)
            if self.security_level == 'Auth-Only':
                self.ssl_ctx.set_cipher_list('NULL')
            self.ssl_ctx.load_cert_chain(self.cert_path, self.key_path)
            self.ssl_ctx.set_verify(SSL.verify_peer, 10, 
                                    SSL.cb.ssl_verify_callback)
            self.ssl_ctx.load_verify_locations(self.cacert_path)
            self.ssl_ctx.set_info_callback()
        except:
            msglog.warn("Transport %s failed to setup SSL context." % self)
            msglog.exception(prefix="handled")
            self.ssl_ctx.close()
            self.ssl_ctx = None
            raise
        else:
            # Else redundant because of re-raise above, but...
            try:
                sock = SSL.Connection(self.ssl_ctx)
            except:
                msglog.warn("Transport %s failed to setup socket." % self)
                msglog.exception()
                raise
            else:
                # Else redundant because of re-raise above, but...
                try:
                    sock.connect((self.host, self.port))
                except:
                    sock.close()
                    sock = None
                self.socket = sock
        # If here then our socket was setup and connected.
        return self.socket
    def flush_read_data(self):
        # This function assumes that there is data to be read
        no_bytes = self.socket.pending()
        if(no_bytes == 0):
            return 0
        else:
            bytes = self.socket.recv(no_bytes)
            return no_bytes

# THIS CLASS IS NOT USED ANYWHERE IN THE CURRENT BUILD!: 03/24/10
#class SimpleTCPSession(SimpleSocketSession):
#    def configure(self,config):
#        SimpleSocketSession.configure(self,config)
#        set_attribute(self, 'host', default_host, config)
#        set_attribute(self, 'port', self.DEFAULT_PORT, config, int)
#    def _connect(self):
#        self.socket = None
#        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#        try:
#            sock.connect((self.host,self.port))
#        except:
#            sock.close()
#            raise
#        self.socket = sock
#        return

class SrnaSession(SimpleSocketSession):
    """ One instance of this class per remote RNA host NBM."""
    def destroy(self):
        try:
            self.socket.set_shutdown(SSL.SSL_RECEIVED_SHUTDOWN|SSL.SSL_SENT_SHUTDOWN)
            self.socket.close()
        except:
            pass # who cares, the world is ending anyway...
        finally:
            self.socket = None
        return
    def _connect(self): # define, else EAbstract error from superclass
        msglog.log('broadway', msglog.types.ERR, 'SrnaSession: _connect: '\
                   'SHOULD NEVER EVER GET HERE! Never call connect() on an '\
                   'SrnaSession object. SrnaSessions are created with '\
                   '_existing_ connections.')
        return


##
# @implements TransportInterface
class SimpleTcpService(SimpleSocketService):
    DEFAULT_PORT = 5150
    ##
    # Get a string representaion of object.
    #
    # @return String representing object.
    #
    def __repr__(self):
        return ('mpx.lib.rna.SimpleTcpService(port=%s,debug=%s)' %
                (repr(self.port), repr(self.debug)))
    ##
    # Configure object.
    #
    # @param config  Dictionary containing configuration.
    # @key host  The address of the host to connect to.
    # @required
    # @key port  The port to connect to on the host.
    # @default  5150
    # @key debug  Output debugging information.
    # @value 0;1
    # @default 0
    #
    def configure(self,config):
        SimpleSocketService.configure(self, config)
        set_attribute(self, 'interface', 'eth0', config)
        ##
        # TODO: FIX IN ConfigTool.
        # Because SSL socket server-sides use certificates that specify
        # their IP addresses, if we want to listen for RNA connections on more
        # than one interface (eg on eth0 _and_ eth1), we need to change 
        # ConfigTool to allow configuration of multiple instances of the RNA 
        # Service node, AND ban the use of "interface" = 'all'.
        # START KLUDGE:
        # If value of "interface" is 'all', then default to eth0:
        if self.interface == 'all':
            self.interface = 'eth0'
        # END KLUDGE
        if self.interface is None:
            default_host = REQUIRED
        else:
            default_host = ip_address(self.interface)
        set_attribute(self, 'port', self.DEFAULT_PORT, config, int)
        set_attribute(self, 'host', default_host, config)
        return
    def _bind_listen(self):
        ##
        # Socket ready to accept connections
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET,
                               socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        sockname = self.socket.getsockname()
        ##
        # The local host address accepting connections.
        self.__bound_address = sockname[0]
        ##
        # The local port on the local host address accepting connections.
        self.__bound_port = sockname[1]
        return
    def bound_port(self):
        if hasattr(self, '_SimpleTcpService__bound_port'):
            return self.__bound_port
        return None


class SrnaService(SimpleTcpService):
    SSLVER_DEF = 'sslv23'
    def __init__(self, **kw):
        self.ssl_ctx = None
        SimpleTcpService.__init__(self, **kw)
        # cannot call "super()" here because base class is _not_ "object"...
        return
    def destroy(self):
        SimpleTcpService.destroy(self)
        try:
            self.ssl_ctx.close()
        except:
            pass # who cares, the world is ending anyway...
        finally:
            self.ssl_ctx = None
        return
    def __repr__(self):
        return ('mpx.lib.rna.SrnaService(port=%s,debug=%s)' %
                (repr(self.port), repr(self.debug)))
    def configure(self,config):
        SimpleTcpService.configure(self, config)
        set_attribute(self, 'security_level', 'NoSec', config)
        msglog.log('broadway', msglog.types.INFO, 'SrnaService.'\
                   'configure: interface is %s' % self.interface)
        self.cert_path = eval('props.SRNA_CERT_%s' % self.interface)
        self.key_path = eval('props.SRNA_KEY_%s' % self.interface)
        self.cacert_path = props.SRNA_CACERT
        return
    def _bind_listen(self):
        # This method should be called only rarely (eg at boot time), so put
        # all socket and SSL.Context init in here:
        if self.socket:
            self.socket.close()
            self.socket = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.ssl_ctx:
            self.ssl_ctx.close()
            self.ssl_ctx = None
        self.ssl_ctx = SSL.Context(self.SSLVER_DEF)
        self.ssl_ctx.load_cert_chain(self.cert_path, self.key_path)
        self.ssl_ctx.load_verify_locations(self.cacert_path)
        self.ssl_ctx.set_client_CA_list_from_file(self.cacert_path)    
        self.ssl_ctx.set_verify(SSL.verify_peer \
                                | SSL.verify_fail_if_no_peer_cert, 10)
        self.ssl_ctx.set_session_id_ctx('SRNA')
        self.ssl_ctx.set_info_callback()
        if self.security_level == 'Auth-Only':
            self.ssl_ctx.set_cipher_list('NULL')
        self.ssl_ctx.set_tmp_dh(props.SRNA_DH1024)
        self.socket.bind((self.host, self.port))
        sockname = self.socket.getsockname()
        ##
        # The local host address accepting connections.
        self.__bound_address = sockname[0]
        ##
        # The local port on the local host address accepting connections.
        self.__bound_port = sockname[1]
        return
    def accept_session(self):
        sock, addr = self.accept()
        try:
            sslconn = SSL.Connection(self.ssl_ctx, sock)
            sslconn.setup_addr(addr)
            sslconn.setup_ssl()
            sslconn.set_accept_state()
            sslconn.accept_ssl()
        except:
            sslconn.clear()
            raise
        if self.debug > 1:
            debug = 1
        else:
            debug = 0
        return SrnaSession(sslconn, addr, debug=debug)

class RnaClientMgr(object):
    """Instantiates, maintains, and serves SimpleTextProtocol objects. Manages 
    at most one SimpleTextProtocol object per remote host."""
    debug = False
    def __init__(self):
        # key = host : value = SimpleTextProtocol object:
        self._protocols = {}
        self.synclock = threading.RLock()
        super(RnaClientMgr, self).__init__()
    def getSimpleTextProtocol(self, cd, scheme):
        message = 'RNA Client Manager %s SimpleTextProtocol: %r.'
        host = cd.get("host")
        if not host:
            raise ValueError("no host specified: %r" % (cd,))
        protocols = self._protocols
        # Atomic get operation, avoid lock 
        # altogether if host exists, since hosts 
        # are not normally removed once created.
        protocol = protocols.get(host)
        if not protocol:
            self.synclock.acquire()
            try:
                # Double check after lock.
                if host not in protocols:
                    if scheme == 'mpxao':
                        cd['security_level'] = 'Auth-Only' 
                        transport = SrnaClientTransport(**cd)
                    elif scheme == 'mpxfe':
                        cd['security_level'] = 'Full-Enc' 
                        transport = SrnaClientTransport(**cd)
                    elif scheme == "mpx":
                        transport = SimpleTcpTransport(**cd)
                    else:
                        message = ("getSimpleTextProtocol() requires "
                                   "valid scheme for host %r, not: %r.")
                        msglog.error(message % (host, scheme))
                        raise ValueError("Invalid scheme: %r" % scheme)
                    protocols[host] = SimpleTextProtocol(transport)
                    action = "CREATED"
                else:
                    action = "RETURNED"
                protocol = protocols[host]
            finally:
                self.synclock.release()
            msglog.inform(message % (action, host))
        elif self.debug:
            msglog.debug(message % ("RETURN", host))
        return protocol
    def clear(self):
        self.synclock.acquire()
        try:
            self._protocols.clear()
        finally:
            self.synclock.release()
    def destroy(self):
        self.clear()
    def _get_manager(self):
        if self.__hm is None:
            from mpx.service.cloud.hosts import NBMManager
            from mpx.lib.node import as_node
            for service in as_node('/services').children_nodes():
                if isinstance(service, NBMManager):
                    self.__hm = service
                    break
        return self.__hm
    hostmanager = property(_get_manager)

# There can be only one: Referenced only in function "from_path":
RNA_CLIENT_MGR = RnaClientMgr()

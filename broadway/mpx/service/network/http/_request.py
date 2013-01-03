"""
Copyright (C) 2003 2004 2006 2007 2008 2009 2010 2011 Cisco Systems

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
import md5
import cgi
import string
import types
import time
import re
import asynchat
import StringIO
import _http_date
from urllib import unquote,unquote_plus
from mpx import properties
from mpx.lib import threading,msglog
from mpx.lib.uuid import UUID
from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import Forbidden
from mpx.lib.exceptions import Unauthorized
from mpx.service.user_manager import User
from mpx.service.user_manager import EAuthenticationFailed
from mpx.service.network.http.response import Cookie
from mpx.service.network.utilities.counting import Counter
from _utilities import RequestThread
from _utilities import AdjustableQueue
from _utilities import RequestManager
import producers

Undefined = object()

VERSION_STRING = properties.RELEASE
class Digest:
    def __init__(self):
        raise ENotImplemented(Digest)

class RequestSingleton(object):
    METHODS = {'GET': False, 'HEAD': False, 'POST': True, 
               'PUT': True, 'TRACE': False, 'OPTIONS': False, 'DELETE': False}
    def __new__(klass):
        if not hasattr(klass, '_singleton'):
            klass._singleton = super(RequestSingleton, klass).__new__(klass)
            klass._singleton.initialize()
        return klass._singleton
    def method_allows_body(self, method):
        return self.METHODS[method.upper()]
    def initialize(self):
        self.request_counter = Counter()
        self.request_manager = RequestManager()
        self.responses = {100: "Continue",
                          101: "Switching Protocols",
                          200: "OK",
                          201: "Created",
                          202: "Accepted",
                          203: "Non-Authoritative Information",
                          204: "No Content",
                          205: "Reset Content",
                          206: "Partial Content",
                          300: "Multiple Choices",
                          301: "Moved Permanently",
                          302: "Moved Temporarily",
                          303: "See Other",
                          304: "Not Modified",
                          305: "Use Proxy",
                          400: "Bad Request",
                          401: "Unauthorized",
                          402: "Payment Required",
                          403: "Forbidden",
                          404: "Not Found",
                          405: "Method Not Allowed",
                          406: "Not Acceptable",
                          407: "Proxy Authentication Required",
                          408: "Request Time-out",
                          409: "Conflict",
                          410: "Gone",
                          411: "Length Required",
                          412: "Precondition Failed",
                          413: "Request Entity Too Large",
                          414: "Request-URI Too Large",
                          415: "Unsupported Media Type",
                          500: "Internal Server Error",
                          501: "Not Implemented",
                          502: "Bad Gateway",
                          503: "Service Unavailable",
                          504: "Gateway Time-out",
                          505: "HTTP Version not supported"}
        self.default_error = string.join(['<head>',
                                          '<title>Error response</title>',
                                          '</head>','<body>',
                                          '<h1>Error response</h1>',
                                          '<p>Error code %(code)d.',
                                          '<p>Message: %(message)s.',
                                          '</body>',''],'\r\n')
        return

class Request(object):
    """
        HTTP Request instances are created by Channels as incoming 
        HTTP requests are received.  At the time of creation, the 
        HTTP channel may or may not have read the full content of 
        the incoming request.
        
        Request instances themselves are created by the Channel 
        each time a new request-line is read.  The HTTP request 
        line consists of the HTTP command, version, and path.
        
        Receipt of the incoming request's headers or content are 
        not required in order to create Request instances.  Instead, 
        the Channel invokes various callbacks on Request instances it 
        creates in order to feed the remainder of the incoming request 
        to newly created Request instances.
        
        Once the request headers for a Request instance have been 
        fully received by the Request instance, the Request instance 
        enqueues itself for further processing on a separate therad.
        
        The handling of enqueued requests uses the resource path 
        associated with the Request in order to identify a matching 
        Request Handler, where matching means that the handler's 
        match() method returned True when passed the Request's URL.
        Once an appropriate Request Handler is found, the request 
        instance is passed to the handler for further processing.
        
        Request handlers process requests by using the Request 
        instance's headers to receive the full request contents, 
        and then acting on those contents accordingly.  Because 
        the request handling is done asynchronously, the handler 
        uses a FIFO instance the enqueue response information as 
        it is generated.
        
        Request handlers use the passed Request instance receive 
        the full request, including any POST information required 
        for processing.  As the handler processes the request, it 
        may push() producers--or simple strings--into the request's 
        outgoing content FIFO.  Upon completion, the handler invokes 
        request_handled() method to notify the request instance that 
        it is ready to begin processing the response.
        
        Request instances iterate through the list of available 
        Responder instances, or "response handlers", querying each 
        by passing the HTTP response code, or "status", to the 
        Responder instance's match() method.  The first Responder 
        instance indicate that it does match the reply, is then 
        passed the Request instance for handling via the Responder 
        instance's handle_response() method.
        
        Using a combination of information about the Request 
        instance, and content pushed into the Request instance 
        by the request handler, the Response handler generates 
        a   
          
        
        Once the handler has received the full 
        request content, and the action has been carried out and the 
        request content, it notifies the corresponding Request 
        instance.
        
        Once a new request has been fully received and handled, a 
        similar process is used to select and invoke the appropriate 
        response handler.  The default response handle is always 
        
             """
    reply_code = 200
    use_chunked = 1
    singleton = None
    prevent_replay = 0
    singleton = RequestSingleton()
    def __init__(self,channel,request,command,uri,version,headers):
        self.number = Request.singleton.request_counter.increment()
        self._channel = channel
        # Top line of the request, like GET /index.html HTTP/1.0 for example.
        self._request = request
        # Type of command, like GET for example.
        self._command = command
        # Requested resource, like /index.html for example.
        self._uri = uri
        # HTTP version, like 1.0 for example.
        self._version = version
        # String of headers exactly as recevied.  Headers included
        #   are all line after request and before double \r\n.
        self.request_header_lines = self._headers = headers
        self.request_headers = None
        self.response_headers = {
            'Server': 'WebServer/%s' % VERSION_STRING,
            'Date': _http_date.build_http_date(time.time())}
        self._split_uri = None
        self._query_dictionary = {}
        self.request_cookies = None
        self._outgoing = asynchat.fifo()
        self._outgoing_content_length = 0
        self._collector = None
        self._user_object = None
        self._authentication_scheme = None
        default = self.server.authentication.lower()
        self._default_scheme = default
        self._default_authentication = {'digest':self.digest_challenge,
                                        'basic':self.basic_challenge, 
                                        'form': self.form_challenge}[default]
        self.out = None
        self.response_length = 0
        self.response_cookies = []
        self.response_producer = None
        self.outgoing_producers = asynchat.fifo()
    def getserver(self):
        return self._channel.server
    server = property(getserver)
    def getchannel(self):
        return self._channel
    channel = property(getchannel)
    def get_address(self):
        return self._channel.addr[0]
    def server_name(self):
        return self.channel.server_name()
    ##
    # The following functions allow a request object to
    # be treated as a dictionary for setting/retrieving the
    # reply headers.
    #
    def __setitem__(self,key,value):
        self.response_headers[key] = value
    def __getitem__(self,key):
        return self.response_headers[key]
    def has_key(self,key):
        return self.response_headers.has_key(key)
    def add_cookie(self,cookie):
        self.response_cookies.append(cookie)
    def split_uri(self):
        if self._split_uri is None:
            self._split_uri = list(_split_uri(self._uri))
        return self._split_uri
    def get_header_with_regex(self,head_reg,group):
        match = self.get_header_match(head_reg)
        if match:
            return match.group(group)
        return match
    def get_header_match(self,head_reg):
        for line in self.request_header_lines:
            match = head_reg.match(line)
            if match and match.end() == len(line):
                return match
        return ''
    ##
    # Get the http command, ie PUT, POSt, etc.
    #
    # @return String command.
    def get_command(self):
        return self._command.upper()
    ##
    # @fixme this is a hack, we should have a better way
    # to tell the protocol
    def get_protocol(self):
        return self.server.protocol().lower()
    protocol = property(get_protocol)

    ##
    # Get the path part of the request URI.
    #
    # @return String containing path.
    def get_path(self):
        return self.split_uri()[0]
    def set_path(self, path):
        self.split_uri()[0] = path
    ##
    # Get parameters part of the reqeust URI.
    #
    # @return String containing parameters.
    # @note Parameters are separated from URI by
    #       a ';'.
    def get_parameters(self):
        return self.split_uri()[1]
    ##
    # Check to see if parameters were passed in.
    #
    # @return 1 if parameters passed, 0 otherwise.
    #
    def has_parameters(self):
        params = self.get_parameters()
        if params:
            return 1
        return 0
    ##
    # Get query part of the request URI.
    #
    # @return The query string.
    def get_query(self):
        return self.split_uri()[2]
    ##
    # Check to see if a query string was sent along
    # with the clients request.
    #
    # @return 1 if there is a query string.
    def has_query(self):
        query = self.get_query()
        if query:
            return 1
        return 0
    ##
    # Get query as a dictionary.
    #
    # @return Dictionary containing query entries.
    def get_query_dictionary(self):
        if self._query_dictionary or not self.has_query():
            return self._query_dictionary
        query = self.get_query()
        if query[0] == '?':
            query = query[1:]
        query = cgi.parse_qs(unquote_plus(query))
        self._query_dictionary = {}
        for key,value in query.items():
            dict = {key:value[0]}
            self._query_dictionary.update(dict)
        return self._query_dictionary.copy()
    def get_query_string_as_dictionary(self,unquote_value =1):
        dict = {}
        query = self.get_query()
        if query:
            if query[0] == '?':
                query = query[1:]
            if query[-1] == '&':
                query = query[0:-1]
            q = string.split(query,'&')
            for x in q:
                k,v = string.split(x,'=')
                if unquote_value ==1:
                    v = unquote_plus(v)
                if dict.has_key(unquote_plus(k)):
                    dict[unquote_plus(k)].append(v)
                else:
                    dict[unquote_plus(k)] =[v]
        return dict
    ##
    # Get post data as dictionary returns a dictionary of the post data.
    # It creates a dictionary of the post data from the name value pairs
    # It creates a key with the name and the value is a list of values
    # since a name can have mulitple values
    # @returns a dictionary with the name as the key and a list as the value
    def get_post_data_as_dictionary(self):
        dict = {}
        if int(self.get_header('Content-Length', 0)) > 0:
            self.get_data().seek(0)
            data = self.get_data().read_all()
            if data:
                if data[-1] == '&':
                    data = data[0:-1]
                tmp = string.split(data,'&')
                for x in tmp:
                    k,v = string.split(x,'=')
                    if dict.has_key(unquote_plus(k)):
                        dict[unquote_plus(k)].append(unquote_plus(v) )
                    else:
                        dict[unquote_plus(k)] =[unquote_plus(v)]
        return dict
    def get_post_data(self):
        data = {}
        post = self.get_post_data_as_dictionary()
        for key,value in post.items():
            if len(value) == 1:
                value = value[0]
            data[key] = value
        return data
    ##
    # Get the fragment part of request URI.
    #
    # @return String containing fragment.
    # @note A fragment is separated from URI
    #       by a '#'.
    def get_fragment(self):
        return self.split_uri()[3]
    ##
    # Get the data sent to server via
    # post or put.
    #
    # @return <code>_DataStream</code> object
    #         containing data sent to server.
    # @todo The DataStream object returned for
    #       each call to get_data is the same, this
    #       may need to change to prevent conflicts.
    def get_data(self):
        return self._collector
    def has_header(self, header):
        return self.get_header(header) is not None
    def has_cookie(self, name):
        return self.get_cookie(name) is not None
    ##
    # Get header value from clients request.
    #
    # @param header The name of the header to get.
    # @return Value for header, or None if specified
    #         header was not sent.
    def get_header(self, header, default=None):
        return self.get_headers().get(header.lower(), default)
    ##
    # Get all headers sent by clients request.
    #
    # @return List of header strings.
    def get_headers(self):
        if self.request_headers is None:
            items = []
            for line in self.request_header_lines:
                try:
                    name,sep,value = line.partition(":")
                except:
                    msglog.log('broadway', msglog.types.WARN, 
                               "Failed to parse header: %r" % line)
                else:
                    items.append((name.lower(), value.strip()))
            self.request_headers = dict(items)
        return self.request_headers
    def remove_header(self, head_reg):
        i = 0
        for line in self.request_header_lines:
            match = head_reg.match(line)
            if match and match.end() == len(line):
                del self.request_header_lines[i]
                self.request_headers = None
                self.request_cookies = None
                return
            i+=1
    def get_cookie(self, name, default=None):
        return self.get_cookies().get(name, default)
    def get_cookies(self):        
        if self.request_cookies is None:
            items = []
            header = self.get_header("cookie", "")
            for cookie in header.split(";"):
                name,separator,value = cookie.partition("=")
                if separator:
                    items.append((name.strip(), value.strip()))
            self.request_cookies = dict(items)
        for param in self._uri.split("&"):
            cookieItems = []
            
            if (param.find("selectedNode=") > -1 ):
                name,separator,value = param.partition("=")
                cookieItems.append(Cookie("selectedNode", value.strip()))
                map(self.add_cookie, cookieItems)
                
        return self.request_cookies     
    def get_cookie_dictionary(self):
        return dict(self.get_cookies())
    ##
    # Get all headers sent by client's request
    # as a dictionary of name, value pairs.
    #
    # @return Dictionary containing header data.
    def get_headers_dictionary(self):
        return dict(self.get_headers())
    ##
    # @note This function is called by asyncore/asynchat
    #       and therefore cannot be renamed.
    def collect_incoming_data(self,data):
        if not self._collector:
            raise Exception('Collect incoming called w/o collector')
        self._collector.collect_incoming_data(data)
    ##
    # @note This function is called by asyncore/asynchat
    #       and therefore cannot be renamed.
    # @todo Add support for chunking.  Set terminator
    #       to '\r\n', when found set to '\r\n' that will
    #       read in integer, evaluate, set terminator to
    #       integer value plus len('\r\n') then '\r\n' again
    #       to get next integer, repeat until 0 reached.
    def found_terminator(self):
        if self._collector:
            self._collector.found_terminator()
            self._channel.reset()
        else:
            if Request.singleton.method_allows_body(self.get_command()):
                self._collector = _DataStream()
                length = self.get_header('Content-Length')
                if not length:
                    self._collector.found_terminator()
                    self._channel.reset()
                else:
                    self._channel.set_terminator(int(length))
            else:
                self._collector = EmptyContentReader()
                self._collector.found_terminator()
                self._channel.reset()
            Request.singleton.request_manager.add_request(self)
    def handle_close(self):
        if self._collector:
            self._collector.close()
    def authenticated(self):
        return self.user_object() is not None
    def authenticate(self, scheme=None):
        challenge = self.get_challenge(scheme)
        challenge(self.server.realm)    
    def user_object(self, user_object=None):
        """
            Pull authenticated user object from request.
            
            Request authentication supports multiple mechanisms.  Both 
            BASIC and DIGEST authentication are supported, as well as 
            a cookie based scheme which uses CUSER and CRYPT cookies 
            to carry the user's name and name/password Unix crypt.
        """
        if user_object is not None:
            self._user_object = user_object
        elif self._user_object is None:
            if self.has_header("Authorization"):
                self._user_object = self.user_from_header()
            elif self.has_cookie("CUSER"):
                self._user_object = self.user_from_cookie()
        return self._user_object
    def user_from_header(self):
        manager = self.server.user_manager
        authorization = self.get_header('Authorization')
        scheme,auth = string.split(authorization.lstrip(),' ',1)
        scheme = scheme.lower()
        if scheme == 'basic':
            user = manager.user_from_rfc2617_basic(auth)
        elif scheme == 'digest':
            params = {}
            while '=' in auth:
                name,rest = string.split(auth.lstrip(),'=',1)
                rest = rest.lstrip()
                if rest[0] == '"':
                    begin = 1
                    end = rest.index('"',begin)
                else:
                    begin = 0
                    if ',' in rest:
                        end = rest.index(',')
                    else:
                        end = len(rest)
                params[name] = rest[begin:end]
                auth = rest[end + 2:]
            if params['uri'] != self.get_path():
                raise EAuthenticationFailed('Authorization URI does'
                                            ' not match request URI.')
            params['method'] = self.get_command()
            if not params.has_key('algorithm'):
                params['algorithm'] = 'MD5'
            if self.prevent_replay:
                params['nextnonce'] = UUID()
            validator = manager.validator_from_rfc2617_digest(**params)
            info = ''
            if params.has_key('cnonce'):
                A1 = validator.security_data()
                A2 = validator.message_data(uri='')
                digest = validator.digest(A1,A2)
                info += ('rspauth="%s", cnonce="%s"' %
                         (digest,params['cnonce']))
            if params.has_key('qop'):
                info += ', qop="%s"' % params['qop']
            if params.has_key('nc'):
                info += ', nc=%s' % params['nc']
            if params.has_key('nextnonce'):
                info += ', nextnonce="%s"' % params['nextnonce']
            if info:
                self['Authentication-Info'] = info
            user = validator.user
        else:
            raise EInvalidValue('scheme',scheme,'Not supported yet')
        self._authentication_scheme = scheme
        return user
    def user_from_cookie(self):
        manager = self.server.user_manager
        username = self.get_cookie("CUSER")
        usercrypt = self.get_cookie("CRYPT")
        self._authentication_scheme = "form"
        return manager.user_from_crypt(username, usercrypt)
    def authentication_scheme(self):
        if not self._user_object:
            self.user_object()
        return self._authentication_scheme
    def send_to_handler(self,skip=None):
        for handler in self.server.handlers:
            if (handler is not skip) and handler.match(self.get_path()):
                provides_security = getattr(handler,'provides_security',False)
                scheme = getattr(handler, "authentication", None)
                authenticate = self.get_challenge(scheme)
                public_resources = getattr(handler, 'public_resources', None)
                path = self.get_path()
                if path.startswith('/'):
                    path = path[1:]
                if (not provides_security and not 
                    self._has_minimum_authentication() and not
                    (public_resources and path.startswith(public_resources))):
                    authenticate(self.server.realm)
                else:
                    try:
                        handler.handle_request(self)
                    except Forbidden, error:
                        self.error(403, str(error))
                    except Unauthorized:
                            authenticate(self.server.realm)
                    except EAuthenticationFailed:
                        authenticate(self.server.realm)
                # Every choice in block results in response 
                # sent to client, so exit send-to-handler.
                return
        return self.error(404)
    def send_to_responder(self, skip=None):
        for responder in self.server.response_handlers:
            if (responder is not skip) and responder.match(self.reply_code):
                # This method should set my outgoing FIFO.
                responder.handle_response(self)
                return
        raise TypeError("No response handler registered.")
    def _has_minimum_authentication(self):
        try:
            scheme = self.authentication_scheme()
        except EAuthenticationFailed:
            return 0
        return bool(scheme)
    def get_challenge(self, scheme):
        if not scheme:
            return self._default_authentication
        scheme = scheme.lower()
        if scheme == "basic":
            return self.basic_challenge
        elif scheme == "digest":
            return self.digest_challenge
        return self._default_authentication
    def basic_challenge(self,realm):
        return self.challenge(realm,'basic')
    ##
    # Called whenever a new digest authentication needs to take place.
    def digest_challenge(self,realm,stale='false'):
        nonce = UUID()
        manager = self.server.user_manager
        self._user_object = manager.new_rfc2617_digest_user(nonce)
        domain = self.get_path()
        if len(domain) > 1:
            domain = domain[0:domain.rfind('/')]
        params = {'nonce':'"%s"' % nonce,'qop':'"auth"',
                  'domain':'"%s"' % domain,
                  'stale':'%s' % stale}
        self.challenge(realm,'digest',params)
    def form_challenge(self, *args):
        if self.get_command() == "GET":
            destination = self.get_path()
        else:
            destination = "/"

        parameterString = self.get_parameters()
        if ( parameterString != None ) :
            parameterString = parameterString[1:]
            params = dict([part.split('=') for part in parameterString.split('&')])
            cookies = []
            for k, v in params.items():
                cookies.append(Cookie(k, v))
            map(self.add_cookie, cookies)
                        
        self["Location"] = "/login?destination=%s" % destination
        self.reply(302, "Authentication required")
    def challenge(self,realm,scheme,params=None):
        if params is None:
            params = {}
        scheme = scheme[0].upper() + scheme[1:].lower()
        authenticate = '%s realm="%s"' % (scheme,realm)
        for name,value in params.items():
            authenticate += ' %s=%s' % (name,value)
        self['WWW-Authenticate'] = authenticate
        self.error(401)
    #CSCtf12664 - Meaningful error message when illegal operation performed
    def exception(self, message=None):
        msglog.exception(prefix="handled")
        self.server.exceptions.increment()
        try:
            self.error(500, message)
        except:
            msglog.exception(prefix="handled")
    ##
    # Push a producer or string onto stack of
    # outgoing producers.  If more than one
    # push is called, when done is called their data
    # will be put into response in a FIFO order.
    def push(self,thing):
        if isinstance(thing, str):
            if self.response_length is not None:
                self.response_length += len(thing)
            producer = producers.SimpleProducer(thing)
        else:
            producer = thing
            self.response_length = None
        self.outgoing_producers.push(producer)
    ##
    # Generate response string based on response
    # code passed in.
    #
    # @param code  The http code of the response.
    # @default 200 Response okay.
    def _response(self,code=200):
        message = Request.singleton.responses[code]
        self.reply_code = code
        return 'HTTP/%s %d %s' % (self._version,code,message)
    def error(self,code,message=None):
        self.reply_code = code
        if message is None:
            message = Request.singleton.responses[code]
            message = (Request.singleton.default_error %
                       {'code': code,'message': message})
        self['Content-Length'] = len(message)
        self['Content-Type'] = 'text/html'
        self.push(message)
        self.done()
    def respond(self, status, content=Undefined):
        """
            Use passed in string or producer, 'content', as 
            content of HTTP response with status code, 'status'.
        """
        if content is not Undefined:
            self.push(content)
        self.reply_code = status
        self.done()
    def reply(self,code,message=None):
        self.reply_code = code
        if message is not None:
            self['Content-Length'] = len(message)
            self['Content-Type'] = 'text/html'
            self.push(message)
        self.done()
    def setreply(self, code, message=None):
        self.reply_code = code
        if message is None:
            message = Request.singleton.responses[code]
        self.push(message)
    ##
    # Request has been handled and data is ready to be returned to client.
    # @todo Do a final check to make sure that proper authentication done
    #       by handler.
    def request_handled(self):
        self.send_to_responder()
    done = request_handled
    def response_handled(self):
        self._channel.request_handled(self)
    def writable(self):
        # Garantees return of boolean, not obj.
        return not not self.out
    def log(self, bytes, extrainfo=""):
        user_object = self._user_object
        if user_object is None:
            if self.has_header('Authorization'):
                try:
                    user_object = self.user_object()
                except EAuthenticationFailed:
                    username = "Unknown"
                except:
                    msglog.exception(prefix='Handled')
                    username = 'Invalid'
                else:
                    username = user_object.name()
            else:
                username = "Anonymous"
        else:
            username = user_object.name()
        message = "Request [%s] returned %d bytes to %s, code %d"
        message = message % (self._request, bytes, username, self.reply_code)
        if extrainfo:
            message = "%s\r%s\r" % (message, extrainfo)
        self._channel.log_info(message, msglog.types.DB)
class EmptyContentReader(object):
    def collect_incoming_data(self, data):
        raise Exception('Empty content reader cannot collect content.')
    def found_terminator(self):
        pass
    def read(self, *args):
        return ''
    def read_all(self, *args):
        return ''
    def seek(self, *args):
        pass
    def tell(self, *args):
        return 0
    def close(self):
        pass
class _DataStream:
    def __init__(self, length=None):
        self.length = length
        self.datastream = StringIO.StringIO()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._stream_closed = 0
        self._done_collecting = 0
    def collect_incoming_data(self, data):
        self._lock.acquire()
        try:
            current_index = self.datastream.tell()
            self.datastream.seek(0, 2)
            self.datastream.write(data)
            self.datastream.seek(current_index)
        finally:
            self._condition.notifyAll()
            self._lock.release()
    def found_terminator(self):
        self._lock.acquire()
        try:
            self._done_collecting = 1
            self._stream_closed = 1
        finally:
            self._condition.notifyAll()
            self._lock.release()
    def read(self, count=None, timeout=15.0):
        self._lock.acquire()
        try:
            data = ''
            while not data and timeout > 0:
                data = self.datastream.read(count)
                if data or self._done_collecting or self._stream_closed:
                    break
                else:
                    start_time = time.time()
                    self._condition.wait(timeout)
                    timeout -= time.time() - start_time
        finally:
            self._lock.release()
        if data or self._done_collecting:
            return data
        elif self._stream_closed:
            return ''
        else: raise ETimeout()
    def destructive_read(self, count=2147483647, timeout=2147483647):
        """
        A variant of read() that (by default) returns all available data
        and truncates the internal "data-stream" to avoid hemorrhaging memory
        when posting large files.
        """
        self._lock.acquire()
        try:
            data = ''
            while not data and timeout > 0:
                data = self.datastream.read(count)
                if data or self._done_collecting or self._stream_closed:
                    break
                else:
                    start_time = time.time()
                    self._condition.wait(timeout)
                    timeout -= time.time() - start_time
        finally:
            if self.datastream.pos == self.datastream.len:
                self.datastream.truncate(0)
            else:
                self.datastream = StringIO.StringIO(self.datastream.read())
            self._lock.release()
        if data or self._done_collecting:
            return data
        elif self._stream_closed:
            return ''
        else: raise ETimeout()
    def read_all(self,timeout=60):
        start_time = time.time()
        data = ''
        # timeout = None means no timeout should be there, for large files
        if timeout is None:
            timeout = 2147483647 #largest 32 bit signed number
        while timeout > 0:
            start_time = time.time()
            newdata = self.read(None, timeout)
            if not newdata:
                break
            data += newdata
            timeout -= time.time() - start_time
        return data
    def seek(self,index,whence = 0):
        self._lock.acquire()
        try:
            self.datastream.seek(index,whence)
        finally:
            self._lock.release()
    def tell(self):
        self._lock.acquire()
        try:
            position =  self.datastream.tell()
        finally:
            self._lock.release()
        return position
    def close(self):
        self._lock.acquire()
        try:
            self._stream_closed = True
        finally:
            self._condition.notifyAll()
            self._lock.release()

##
# Split a uri
#
# <path>;<params>?<query>#<fragment>
# path      params    query   fragment
_path_regex = re.compile(r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?')
def _split_uri(uri):
    m = _path_regex.match(uri)
    if m.end() != len(uri):
        raise ValueError, "Broken URI"
    return m.groups()
_REQUEST = re.compile('([^ ]+) ([^ ]+)(( HTTP/([0-9.]+))$|$)')
def crack_request(r):
    m = _REQUEST.match(r)
    if m.end() == len(r):
        if m.group(3):
            version = m.group(5)
        else:
            version = None
        return string.lower(m.group(1)),m.group(2),version
    return None,None,None

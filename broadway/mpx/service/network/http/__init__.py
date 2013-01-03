"""
Copyright (C) 2001 2002 2003 2007 2009 2011 Cisco Systems

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
import asyncore
import select
from mpx import properties
from mpx.lib import msglog, deprecated
from mpx.lib.node import Alias
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import ConfigurableNode
from mpx.lib.threading import ImmortalThread
from mpx.service import ServiceNode
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute,get_attribute,as_boolean
from mpx.lib.exceptions import EMissingAttribute,EInvalidValue
from request_handler import FileRequestHandler
from mpx.service.network.http.responders import RequestResponder
from mpx.service.network.http.handlers.authentication import Authenticator
import _http
import _request

def getpath(handler):
    if not hasattr(handler, "handle_request"):
        raise TypeError("getpath() expects handler, not: %r" % handler)
    if hasattr(handler, "request_path"):
        return handler.request_path
    if hasattr(handler, "path"):
        return handler.path
    return None

class HandlerAlias(Alias):
    """
        Extending standard Alias type functionality 
        so that any property will be proxied through to 
        node.  This is so that the handler methods, like 
        'match', 'handle_request', etc., are proxied.
    """
    def fromhandler(klass, handler):
        alias = klass()
        nodeurl = as_node_url(handler)
        alias.configure({"name": handler.name, "node_url": nodeurl})
        return alias
    fromhandler = classmethod(fromhandler)
    def __init__(self, *args, **kw):
        self.name = ""
        self.node_url = ""
        self.parent = None
        self._Alias__node = None
        super(HandlerAlias, self).__init__()
    def configure(self, config):
        if config.has_key("node"):
            self._Alias__node = config["node"]
        elif config.has_key("node_url"):
            set_attribute(self, "node_url", REQUIRED, config)
        return ConfigurableNode.configure(self, config)
    def configuration(self):
        config = super(HanlderAlias, self).configuration()
        if not config.get("node_url") and self._Alias__node:
            config["node_url"] = as_node_url(self._Alias__node)
        return config
    def _public_interface(self):
        if self._Alias__node:
            node = self._Alias__node
            if hasattr(node, "_public_interface"):
                node = node._public_interface()
        else:
            node = super(HandlerAlias, self)._public_interface()
        return node
    def __getattr__(self,name):
        if self._Alias__node is None:
            self._Alias__node = as_node(self.node_url)
        if not hasattr(self._Alias__node, name):
            raise AttributeError(name)
        return getattr(self._Alias__node, name)

class _RedusaThread(ImmortalThread):
    def __init__(self):
        ImmortalThread.__init__(self, name="Redusa Async Core")
        self._use_poll = 0
        try:
            select.poll()
            self._use_poll = 1
        except:
            msglog.log('broadway', msglog.types.INFO,
                       'Platform does not support poll().')
        return
    def run(self):
        # @note Added _http.REDUSA_SOCKET_MAP so other threads can safely use
        #       asyncore as well.
        asyncore.loop(30, self._use_poll, _http.REDUSA_SOCKET_MAP)
        return

class Server(ServiceNode):
    _thread = None
    _servers = {}
    servers = []
    # "Overridable" references, use self to lookup these references so
    # derived classes can override them.
    server_class = _http.HTTPServer
    server_type = 'HTTP'
    def __new__(klass, *args, **kw):
        server = super(Server, klass).__new__(klass, *args, **kw)
        klass.servers.append(server)
        return server
    def __init__(self):
        ServiceNode.__init__(self)
        self._added_thread_count = 0
        self._file_request_handler = None
        self.psp_handler = None
        self.authenticator = None
        self.request_responder = None
        self.request_manager = _request.RequestSingleton().request_manager
    def configure(self, config):
        set_attribute(self, 'debug', 0, config, int)
        set_attribute(self, 'ip', '', config)
        default = '${mpx.properties.%s_PORT}' % self.server_type
        set_attribute(self,'port',default,config,int)
        set_attribute(self,'user_manager',
                      as_node('/services/User Manager'),config,as_node)
        set_attribute(self,'authentication','form',config)
        if (self.authentication is not None and
            self.authentication not in ('digest','basic','form')):
            raise EInvalidValue('authentication',self.authentication,
                                'Authentication scheme not recognized.')
        set_attribute(self,'port',default,config,int)
        set_attribute(self, 'maintenance_interval', 25, config, int)
        set_attribute(self, 'zombie_timeout', 600, config, int)
        set_attribute(self, 'thread_count', 3, config, int)        
        if not self.has_child("Request Responder"):
            self._setup_request_responder()
        if not self.has_child("Authenticator"):
            self._setup_authentication_handler()
        if not self.has_child("PSP Handler"):
            self._setup_psp_handler()
        if not self.has_child("JSON-RPC Handler"):
            self._setup_json_handler()
        ServiceNode.configure(self, config)
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'ip', config)
        get_attribute(self, 'port', config, str)
        get_attribute(self, 'user_manager', config, as_node_url)
        get_attribute(self, 'authentication', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'maintenance_interval', config, str)
        get_attribute(self, 'zombie_timeout', config, str)
        get_attribute(self, 'thread_count', config, str)
        return config
    def _add_child(self, child):
        if self.has_child(child.name):
            existing = self.get_child(child.name)
            if isinstance(existing, HandlerAlias):
                msglog.log("broadway", msglog.types.WARN, 
                           "Removing %s before adding %s" % (existing, child))
                existing.prune()
        result = super(Server, self)._add_child(child)
        if self.is_running():
            self._setup_handler(child)
        return result
    def _setup_handler(self, handler):
        if hasattr(handler, "handle_request"):
            self._setup_request_handler(handler)
        elif hasattr(handler, "handle_response"):
            self._setup_response_handler(handler)
        else:
            msglog.log("broadway", msglog.types.WARN, 
                       "Handler type uknown: %s" % handler)
    def _setup_request_handler(self, handler):
        if not isinstance(handler, HandlerAlias):
            for server in self.servers:
                if server is not self:
                    if (not server.has_child(handler.name) and 
                        not server.handles_path(getpath(handler))):
                        message = "%s aliasing %r handler from %s."
                        msglog.log("broadway", msglog.types.INFO, 
                                   message % (server, getpath(handler), self))
                        alias = server.create_alias(handler)
                        if server.is_running():
                            server.server.install_request_handler(handler)
        if isinstance(handler, FileRequestHandler):
            self._file_request_handler = handler
            handler.setup_filesystem()
            back = True
        else:
            back = False
        self.server.install_request_handler(handler, back)
    def _setup_response_handler(self, handler):
        self.server.install_response_handler(handler)
    def request_handlers(self):
        return [child for child in 
                self.children_nodes() if 
                hasattr(child, "handle_request")]
    def response_handlers(self):
        return [child for child in 
                self.children_nodes() if 
                hasattr(child, "handle_response")]
    def handles_path(self, path):
        handlers = self.request_handlers()
        return any(getpath(handler) == path for handler in handlers)
    def _setup_server(self):
        self._added_thread_count = self.thread_count
        self.request_manager.add_threads(self._added_thread_count)
        self.server = self.server_class(self.ip, self.port,
                                        self.user_manager,self.name,
                                        self.authentication,
                                        self.maintenance_interval,
                                        self.zombie_timeout, self.debug)
        for handler in self.children_nodes():
            self._setup_handler(handler)
    def _setup_psp_handler(self):
        from mpx.service.network.http.psp_handler import factory
        self.psp_handler = factory()
        self.psp_handler.configure({'name':'PSP Handler','parent':self})
        return self.psp_handler
    def _setup_authentication_handler(self):
        self.authenticator = Authenticator()
        self.authenticator.configure({'name':'Authenticator','parent':self})
        return self.authenticator
    def _setup_json_handler(self):
        from mpx.service.network.http.handlers.jsonrpc import JSONRPCHandler
        self.json_handler = JSONRPCHandler()
        self.json_handler.configure({'name':'JSON-RPC Handler','parent':self})
        return self.json_handler
        
    def _setup_proxy_handler(self):
        from mpx.service.network.http.handlers.proxy import PROXYHandler
        self.proxy_handler = PROXYHandler()
        self.proxy_handler.configure({'name':'PROXY Handler','parent':self})
        return self.proxy_handler
  
  
    def _setup_request_responder(self):        
        self.request_responder = RequestResponder()
        self.request_responder.configure(
            {"name": "Request Responder", "parent": self})
        return self.request_responder
    def _teardown_server(self):
        self.request_manager.remove_threads(self._added_thread_count)
        self._file_request_handler = None
        self._added_thread_count = 0
        self.server.close()
    def send_to_file_handler(self,request):
        deprecated('Use request.send_to_handler(skip=self) instead')
        return self._file_request_handler.handle_request(request)
    def start(self):
        if not Server._servers.has_key(self.port):
            Server._servers[self.port] = self
            self._setup_server()
        if Server._thread is None:
            Server._thread = _RedusaThread()
            Server._thread.start()
        ServiceNode.start(self)
    def create_alias(self, handler):
        if self.debug:
            msglog.log("broadway", msglog.types.DB, 
                       "Aliasing %s within %s." % (handler, self))
        alias = HandlerAlias()
        config = {"parent": self, "name": handler.name,  "node": handler}
        alias.configure(config)
        return alias
    def stop(self):
        if Server._servers.has_key(self.port):
            del Server._servers[self.port]
            self._teardown_server()
        return ServiceNode.stop(self)
    def open_resource(self, path, mode="r"):
        """
            Returns open file-handle based on URL path.
            
            Allows callers to get file handles based on URLs 
            instead of file-system paths.
        """
        return self._file_request_handler._filesystem.open(path, mode)
    def read_resource(self, path):
        resource = self.open_resource(path, "r")
        content = resource.read()
        resource.close()
        return content
    def write_resource(self, path, data):
        resource = self.open_resource(path, "w")
        response = resource.write(data)
        resource.close()
        return response
    def append_resource(self, path, data):
        resource = self.open_resource(path, "a")
        response = resource.write(data)
        resource.close()
        return response


def factory():
    return Server()

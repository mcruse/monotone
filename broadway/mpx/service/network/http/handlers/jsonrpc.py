"""
Copyright (C) 2007 2009 2010 2011 Cisco Systems

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
import json
import urllib
import inspect
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import as_internal_node
from mpx.lib.exceptions import Unauthorized
from mpx.lib.neode.node import CompositeNode
from mpx.lib._singleton import _ReloadableSingleton
from mpx.service.network.http.response import Response
primitives = set([str, int, float, long, unicode, list, tuple, bool])

def getapi(instance, public=True):
    # Hack to get handle to inspectable node.
    if isinstance(instance, _ReloadableSingleton):
        instance = instance.as_node()
    # Mapping method-names to method-code objects.
    methods = inspect.getmembers(instance, inspect.ismethod)
    if public:
        methods = [(name,method) for name,method in 
                   methods if not name.startswith("_")]
    methods = [(name,inspect.getargspec(method)) for name,method in methods]
    descriptors = []
    for name,argspec in methods:
        args,varargs,kwargs,defaults = argspec
        if defaults:
            defaults = list(defaults)
        parameters = []
        for arg in reversed(args):
            if arg == "self":
                continue
            parameter = {"name": arg}
            if defaults:
                default = defaults.pop()
                if default is not None and type(default) not in primitives:
                    message = ("JSON API ignoring default value %r for"
                               " parameter %s of method %s on object %s."
                               "  Declaring parameter optional instead.")
                               
                    msglog.log("broadway", msglog.types.WARN, 
                               message % (default, arg, name, instance))
                else:
                    parameter["default"] = default
                parameter["optional"] = True
            parameters.append(parameter)
        parameters.reverse()
        if varargs:            
            for arg in varargs:
                parameter = {"name": arg}
                parameter["optional"] = True
                parameters.append(parameter)
        descriptors.append({"name": name, "parameters": parameters})
    return descriptors

class JSONRPCHandler(CompositeNode):
    """
        Handle JSON SMD and JSON-RPC requests.
        
        JSON SMD requests return standard API description for 
        objects, allowing client to build proxy instance.
        JSON RPC requests invoke methods on object using JSON-RPC 
        formatted request.
        
        dojo.require("dojo.rpc.JsonService");
        var time = new dojo.rpc.JsonService('/jsonrpc/services/time')
        time.get(1).addCallback(function(result) {
            console.log("result is:", result);
        });
    """
    def __init__(self, *args):
        self.security_manager = None
        super(JSONRPCHandler, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/jsonrpc'))
        self.secured = as_internal_node("/services").secured
        super(JSONRPCHandler, self).configure(config)
    def configuration(self):
        config = super(JSONRPCHandler, self).configuration()
        config['path'] = self.getattr('path')
        return config
    def start(self):
        self.security_manager = as_node("/services/Security Manager")
        super(JSONRPCHandler, self).start()
    def stop(self):
        self.security_manager = None
        super(JSONRPCHandler, self).stop()
    def match(self, path):
        return path.startswith(self.path)
    def invoke(self, target, methodname, *params):
        node = self.nodespace.as_node(target)
        method = getattr(node, methodname)
        return method(*params)
    def get_attribute(self, target, attr):
        node = self.nodespace.as_node(target)
        return getattr(node, attr)
    def set_attribute(self, target, attr, value):
        node = self.nodespace.as_node(target)
        return setattr(node, attr, value)
    def handle_request(self, request):
        path = request.get_path()
        nodeurl = path[len(self.path):]
        node = as_node(nodeurl)
        data = request.get_data().read_all()
        response = {"jsonrpc": "2.0"}
        if data:
            error = None
            try:
                jsonrpc = json.read(data)
            except json.ReadException, error:
                response["error"] = {"code": -32700}
            else:
                if "jsonrpc" in jsonrpc:
                    # If caller sends version, use it; should be 
                    # backwards compatible with earlier versions.
                    response["jsonrpc"] = jsonrpc["jsonrpc"]
                if self.secured:
                    node = self.security_manager.as_secured_node(node)
                try:
                    method = getattr(node, jsonrpc['method'])
                except AttributeError, error:
                    response["error"] = {"code": -32601}
                except Unauthorized, error:
                    request.reply_code = 403
                    response["error"] = {"code": -32601}
                else:
                    args = []
                    kwargs = {}
                    params = jsonrpc.get("params", [])
                    if isinstance(params, dict):
                        argitems = []
                        # Crazy JSON-RPC 2.0 says hash args can use 
                        # string integer representations as keys to 
                        # provide positional arguments using hash map.
                        for name in params.keys():
                            if name.isdigit():
                                position = int(name)
                                if position >= 0 and position <= 9:
                                    # Property name is integer position, 
                                    # strip from params dict and place in 
                                    # args sequence.
                                    value = params.pop(name)
                                    argitems.append((position, value))
                        # Place remaining properties into kwargs.
                        kwargs.update(params)
                        # Create sequence of positional args specified 
                        # by digit property name in params hash map.
                        args.extend([val for pos,val in sorted(argitems)])
                    elif isinstance(params, (list, tuple)):
                        args.extend(params)
                    else:
                        msglog.warn("Unknown param type: %r" % (params,))
                    try:
                        result = method(*args, **kwargs)
                    except ValueError, error:
                        response["error"] = {"code": -32602}
                        msglog.exception(prefix="handled")
                    except Exception, error:
                        response["error"] = {"code": -32603}
                        msglog.exception(prefix="handled")
            if error:
                errordict = response.setdefault("error", {"code": -32603})
                message = error.message
                if not message:
                    # Some silly internal errors don't include 
                    # a message.  This should be fixed.  Example: 
                    # as_node("/interfaces/relay1").set('a').
                    classname = error.__class__.__name__
                    message = "%s exception occurred." % classname
                errordict.setdefault("message", message)
                errordict.setdefault("data", error.args)
            else:
                if isinstance(result, dict) and type(result) is not dict:
                    # Case dict subclass to actual dict for JSON encoding.
                    result = dict(result)
                response["result"] = result
            response["id"] = jsonrpc.get("id", None)
        else:
            response["serviceType"] = "JSON-RPC"
            response["strictArgChecks"] = False
            response["methods"] = getapi(node, True)
            response["serviceURL"] = "%s%s" % (self.path, as_node_url(node))
        try:
            serialized = json.write(response)
        except:
            msglog.log("broadway", msglog.types.WARN, 
                       "JSON could not serialize: %r" % (response,))
            raise
        request["Content-Type"] = "application/json"
        request.push(serialized)
        request.done()

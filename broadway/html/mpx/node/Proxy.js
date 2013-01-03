/*
Copyright (C) 2009 2010 2011 Cisco Systems

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
*/
dojo.provide("mpx.node.Proxy");
dojo.require("dojo.rpc.JsonService");

mpx.node.createProxy = function(nodeurl) {
    console.debug("createProxy()", nodeurl, "->", "/jsonrpc" + nodeurl);
    var proxyurl = "/jsonrpc" + nodeurl;
    var nodeproxy = new dojo.rpc.JsonService(proxyurl);
    nodeproxy.strictArgChecks = false;
    return nodeproxy;
}

dojo.declare("mpx.node.Proxy", null, {
    nodeURL: "",
    nodeName: "", 
    parentURL: "", 
    nodeProxy: null, 
    constructor: function(args) {
        console.debug("mpx.node.Proxy()", args);
        if (dojo.isString(args)) {
            console.warn("mpx.node.Proxy() deprecated construction:", args);
            this.nodeURL = args;
        } else {
            this.nodeURL = args.nodeURL;
            this.nodeName = args.nodeName || "";
            this.parentURL = args.parentURL || "";
        }
        var nameStart = this.nodeURL.lastIndexOf("/");
        if (!this.parentURL)
            this.parentURL = this.nodeURL.slice(0, nameStart);
        if (!this.nodeName) {
            if (nameStart == 0)
                this.nodeName = "/";
            else
                this.nodeName = unescape(this.nodeURL.slice(nameStart + 1));
        }
        this.nodeProxy = mpx.node.createProxy(this.nodeURL);
        dojo.mixin(this, this.nodeProxy, this.properties);
    },
    properties: {
        declaredClass: "mpx.node.Proxy", 
        toString: function() {
            return this.declaredClass + "('" + this.nodeURL + "')";
        }, 
        getChild: function(name, synchronous) {
            var baseurl = this.nodeURL;
            if (baseurl[baseurl.length - 1] != "/")
                baseurl = baseurl + "/";
            var nodeurl = baseurl + escape(name);
            var proxy = new mpx.node.Proxy({nodeURL: nodeurl});
            if (synchronous) {
                return proxy;
            } else {
                var deferred = new dojo.Deferred();
                deferred.callback(proxy);
                return deferred;
            }
        }, 
        getParent: function(synchronous) {
            return new mpx.node.Proxy({nodeURL: this.parentURL});
        }, 
        getChildren: function() {
            var parent = this;
            var deferred = new dojo.Deferred();
            function handleChildren(names) {
                console.debug("Handling children names:", names);
                deferred.callback(names);
                return names;
            }
            function handleError(response) {
                console.error("Failed to get children names:", response);
                deferred.errback(response);
                return response;
            }
            function createProxies(names) {
                function getChild(name) {
                    return parent.getChild(name, true);
                }
                var proxies = dojo.map(names, getChild, parent);
                return proxies;
            }
            deferred.addCallback(createProxies);
            this.children_names().addCallbacks(handleChildren, handleError);
            return deferred;
        }
    }
});

/*
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
*/
dojo.provide("nbmweb.rss.Feed");
dojo.require("dojox.xml.parser");
dojo.require("nbmweb.rss.Rss");

dojo.declare("nbmweb.rss.Feed", null, {
    url: "",
    rss: null,  
    query: null, 
    method: "GET",
    xmldoc: null,  
    constructor: function(args) {
        dojo.mixin(this, args);
        if (!args.query)
            this.query = {};
    }, 
    param: function(name, value) {
        var current;
        if (dojo.isString(name)) {
            current = this.query[name];
            if (arguments.length == 2)
                this.query[name] = value;
        } else {
            current = dojo.clone(this.query);
            if (arguments.length == 1) {
                var query = name;
                for (name in query) {
                    this.param(name, query[name]);
                }
            }
        }
        return current;
    }, 
    load: function(query) {
        if (query)
            this.param(query);
        var args = dojo.clone(this.query);
        var deferred = dojo.xhrGet({
            url: this.url, 
            content: this.query, 
            preventCache: true,
            handleAs: "text", 
            method: this.method
        });
        deferred.addCallback(dojo.hitch(this, "parse"));
        return deferred;
    }, 
    parse: function(content) {
        if (dojo.isString(content))
            content = dojox.xml.parser.parse(content);
        this.xmldoc = content;
        var element = dojo.query("rss", this.xmldoc)[0];
        this.rss = new nbmweb.rss.Rss(element);
        return this.rss;
    }
});
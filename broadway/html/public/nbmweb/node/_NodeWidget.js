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
dojo.provide("nbmweb.node._NodeWidget");
dojo.require("dojo.data.ItemFileReadStore");
dojo.require("dijit._Widget");
dojo.require("mpx.node.asProxy");
dojo.require("nbmweb.properties");

dojo.declare("nbmweb.node._NodeWidget", dijit._Widget, {
    node: null,
    nodeURL: "", 
    startup: function() {
        console.log(this.asString("startup()"));
        if (this.node) {
            var node = this.node;
            this.node = null;
            this.attr("node", node);
        } else if (this.nodeURL) {
            var nodeURL = this.nodeURL;
            this.nodeURL = "";
            this.attr("nodeURL", nodeURL);
        }
        return this.inherited(arguments);
    }, 
    attr: function(name, value) {
        console.log(this.asString("attr("), name, value, ")");
        var node = this.node;
        var nodeURL = this.nodeURL;
        var result = this.inherited(arguments);
        if (nodeURL != this.nodeURL) {
            if (this.nodeURL)
                this.node = mpx.node.asProxy(this.nodeURL);
            else
                this.node = null;
        } else if (node != this.node) {
            if (this.node)
                this.nodeURL = this.node.nodeURL;
            else
                this.nodeURL = "";
        }
        if (node != this.node) {
            if (this.node)
                this.onNodeSet(this.node, node);
            else
                this.onNodeCleared(node);
            this.onNodeChanged(this.node, node);
        }
        return result;
    }, 
    onNodeSet: function(newNode, oldNode) {
        console.log(this.asString("onNodeSet("), newNode, ", ", oldNode, ")");
    }, 
    onNodeChanged: function(newNode, oldNode) {
        console.log(this.asString("onNodeChanged("),newNode,", ",oldNode,")");
    }, 
    onNodeCleared: function(oldNode) {
        console.log(this.asString("onNodeCleared("), oldNode, ")");
    }, 
    toString: function() {
        return this.declaredClass + "(" + this.node + ")";
    },
    asString: function(propname) {
        return this.declaredClass + "." + propname;
    }, 
    _changeNode: function(newNode) {
        if (dojo.isString(newNode))
            this.attr("nodeURL", newNode);
        else
            this.attr("node", newNode);
    }
});

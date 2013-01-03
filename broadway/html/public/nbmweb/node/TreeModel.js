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
dojo.provide("nbmweb.node.TreeModel");
dojo.require("dijit._Widget");
dojo.require("mpx.node.asProxy");

dojo.declare("nbmweb.node.TreeModel", dijit._Widget, {
    rootURL: "", 
    rootNode: null,
    postMixInProperties: function() {
        console.log("Setting up Model: ", this.rootURL);
        this.rootNode = mpx.node.asProxy(this.rootURL);
        return this.inherited(arguments);
    }, 
    toString: function() {
       return this.declaredClass + "(" + this.rootNode + ")"; 
    }, 
    getRoot: function(onItem) {
        if (onItem)
            onItem(this.rootNode);
        return this.rootNode;
    }, 
    mayHaveChildren: function(item) {
        console.log("mayHaveChildren", item);
        return dojo.exists("children_names", item);
    }, 
    getChildren: function(item, onComplete) {
        var deferred = item.getChildren();
        deferred.addCallback(onComplete);
        return deferred;
    }, 
    getIdentity: function(item) {
        return item.nodeURL;
    }, 
    getLabel: function(item) {
        return item.nodeName;
    }    
});
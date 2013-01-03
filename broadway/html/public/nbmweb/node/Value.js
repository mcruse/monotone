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
dojo.provide("nbmweb.node.Value");
dojo.require("dijit._Templated");
dojo.require("dijit.layout.ContentPane");
dojo.require("nbmweb.node._NodeWidget");
dojo.require("utils.display");

dojo.declare("nbmweb.node.Value", 
             [nbmweb.node._NodeWidget, dijit._Templated], {
    valueNode: null, 
    updatePeriod: 2, 
    templateString: "",
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb.node", "templates/Value.html"),
    onNodeChanged: function(newNode, oldNode) {
        dojo.attr(this.valueNode, "innerHTML", "");
        if (this.scheduled)
            clearTimeout(this.scheduled);
        this.scheduled = null;
        if (this.node && this.node.get)
            this.initiateRefresh();
        return this.inherited(arguments);
    }, 
    initiateRefresh: function() {
        var deferred = null;
        if (this.node && this.node.get) {
            var callback = dojo.hitch(this, "loadUpdate");
            var errback = dojo.hitch(this, "loadError");
            deferred = this.node.get();
            deferred.addCallbacks(callback, errback);
        }
        return deferred;
    }, 
    loadUpdate: function(response) {
        dojo.attr(this.valueNode, "innerHTML", response);
        this.scheduled = setTimeout(
            dojo.hitch(this, "initiateRefresh"), this.updatePeriod * 1000); 
        return response;
    }, 
    loadError: function(response) {
        utils.display.failure("Unable to get node value", response);
        this.scheduled = null;
        return response;
    }
});
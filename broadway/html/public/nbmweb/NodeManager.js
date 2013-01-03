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
dojo.provide("nbmweb.NodeManager");
dojo.require("dijit._Templated");
dojo.require("nbmweb.node._NodeWidget");
dojo.require("nbmweb.properties");

dojo.declare("nbmweb.NodeManager", 
             [nbmweb.node._NodeWidget, dijit._Templated], {
    templateString: "",
    nodeRows: null,
    nodeContext: "", 
    nodeActions: [], 
    widgetsInTemplate: true,
    templatePath: dojo.moduleUrl("nbmweb", "templates/NodeManager.html"),
    constructor: function(args, domNode) {
        this.nodeRows = new dojo.NodeList();
    }, 
    startup: function() {
        dojo.forEach(this.nodeActions, function(action, index) {
            var button = new dijit.form.Button({label: action});
            dojo.place(button.domNode, this.actionCell, "last");
        }, this);
        dojo.style(this.rowTemplate, "display", "none");
        return this.inherited(arguments);
    }, 
    onNodeChanged: function(newNode, oldNode) {
        this.nodeRows.orphan();
        this.nodeRows = new dojo.NodeList();
        if (this.node) {
            var deferred = this.node.children_names();
            deferred.addCallbacks(dojo.hitch(this, "_loadNames"), 
                                  dojo.hitch(this, "_loadError"));
        }
        return this.inherited(arguments);
    }, 
    _loadNames: function(response) {
        console.log(this.toString(), " received names: ", response);
        var classes = ["light", "dark"];
        dojo.forEach(names, function(name, index) {
            console.log("handling attribute: ", name)
            var row = dojo.clone(this.rowTemplate);
            dojo.query("th.name", row).attr("innerHTML", name);
            dojo.addClass(row, classes[index % 2]);
            this.nodeRows.push(row);
        }, this);
        this.nodeRows.style("display", "");
        this.nodeRows.place(this.rowTemplate, "after");
        return response;
    }, 
    _loadError: function(response) {
        utils.display.failure("Unable to get children names", response);
        return response;
    }
});

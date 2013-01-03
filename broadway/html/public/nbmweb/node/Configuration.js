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
dojo.provide("nbmweb.node.Configuration");
dojo.require("dojo.data.ItemFileReadStore");
dojo.require("dijit._Templated");
dojo.require("nbmweb.node._NodeWidget");
dojo.require("nbmweb.properties");

dojo.declare("nbmweb.node.Configuration", 
             [nbmweb.node._NodeWidget, dijit._Templated], {
    templateString: "",
    configurationRows: null, 
    widgetsInTemplate: false, 
    templatePath: dojo.moduleUrl(
        "nbmweb.node", "templates/Configuration.html"),
    constructor: function(args, domNode) {
        this.configurationRows = new dojo.NodeList();
    }, 
    startup: function() {
        dojo.style(this.rowTemplate, "display", "none");
        return this.inherited(arguments);
    }, 
    onNodeChanged: function(newNode, oldNode) {
        this.configurationRows.orphan();
        this.configurationRows = new dojo.NodeList();
        if (this.node) {
            var deferred = this.node.configuration();
            deferred.addCallbacks(dojo.hitch(this, "_loadConfig"), 
                                  dojo.hitch(this, "_loadError"));
        }
        return this.inherited(arguments);
    }, 
    _loadConfig: function(response) {
        console.log(this.toString(), " received update: ", response);
        var classes = ["light", "dark"];
        var names = nbmweb.properties.getNames(response);
        dojo.forEach(names, function(name, index) {
            console.log("handling attribute: ", name)
            var value = response[name];
            var row = dojo.clone(this.rowTemplate);
            dojo.query("th.name", row).attr("innerHTML", name);
            dojo.query("td.value", row).attr("innerHTML", value);
            dojo.addClass(row, classes[index % 2]);
            this.configurationRows.push(row);
        }, this);
        this.configurationRows.style("display", "");
        this.configurationRows.place(this.rowTemplate, "after");
        return response;
    }, 
    _loadError: function(response) {
        utils.display.failure("Unable to get node configuration", response);
        return response;
    }
});

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
dojo.provide("utils.configure.cloud");
dojo.require("utils.display");
dojo.require("utils.configure.node");
dojo.require("utils.configure.form");
dojo.require("utils.configure.templates");
dojo.require("nbmweb.EventSource");
//CSCte94385
dojo.require("nbmweb.edit.CreatePeer");

utils.configure.exporter.createNodeManager = function(table, configurator) {
    var manager = new utils.configure.exporter.Manager(table, configurator);
    dojo.byId(table).manager = manager;
    return manager;
}

dojo.declare("utils.configure.cloud.Manager",
             utils.configure.node.Manager, {
    constructor: function() {
        this.typeName = "Peer/Portal";
        this.createNodeHref = "/public/nbmweb/edit/forms/CreatePeer.html";
    },
    getRowTemplates: function() {
        return utils.configure.templates.cloudRowTemplates;
    },
    createNodeRows: function(names) {
        console.debug("Loading names:", this, names);
        var rows = new Array();
        this.nodes = new Array();
        dojo.forEach(names, function(name, index) {
           if(index == 0) { //Portal
        	   if(name == "")
        		   this.table.addRow(["*Portal Not Configured",""]);
        	   else
        		   this.table.addRow([name]);
           }
           else if(index == 1) { //Self Peer
        	   this.table.addRow([name,""]);
           }
           else // all other peers
        	   this.table.addRow([name]);
           this.nodes.push(name);
        }, this);
    }
});
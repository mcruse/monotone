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
dojo.provide("nbmweb.EventSource");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.CheckBox");

dojo.declare("nbmweb.EventSource", [dijit._Widget, dijit._Templated], {
    values: null, 
    templateString: null,
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb", "templates/EventSource.html"), 
    getValues: function() {
	var values = new Object();
        values.source = this.sourceNode.attr("value");
        values.events = this.getEvents();
        return values;
    }, 
    setValues: function(values) {
    	 if ("source" in values) {
            var name = "";
            var source = values.source || "";
            if (source.length) {
                var start = source.lastIndexOf("/") + 1;
                name = source.slice(start);
                var dropdown = dojo.byId("alarmsList");
                var option = document.createElement("option");
                option.innerHTML = name;
                option.value = source;
                dropdown.appendChild(option);
            }
            this.sourceNode.attr("value", source);
        }
        if ("events" in values)
            this.setEvents(values.events);
    }, 
    setEvents: function(events) {
        var names = ["raised", "accepted", "cleared", "closed"];
        if (dojo.indexOf(events, "all") != -1)
            events = names.slice();
        dojo.forEach(names, function(name, index) {
            var value = (dojo.indexOf(events, name) != -1);
            var field = this[name + "Node"];
            field.attr("value", value);
        }, this);
        if (events.length == names.length)
            this.allNode.attr("value", true);
        else
            this.allNode.attr("value", false);
    }, 
    updateAll: function() {
        if (this.allNode.attr("value"))
            this.setEvents(["all"]);
        else
            this.setEvents([]);
    }, 
    getEvents: function() {
    	 var names = ["raised", "accepted", "cleared", "closed"];
        var events = dojo.filter(names, function(name, index) {
            var field = this[name + "Node"];            
            return field.attr("value") == name;
        }, this);
        return events;
    }
});
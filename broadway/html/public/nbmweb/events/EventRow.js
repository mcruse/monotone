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
dojo.provide("nbmweb.events.EventRow");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit._Contained");

dojo.declare("nbmweb.events.EventRow", 
             [dijit._Widget, dijit._Templated, dijit._Contained], {
    origin: "", 
    source: "", 
    created: "", 
    disabled: false, 
    selected: false, 
    templateString: "", 
    widgetsInTemplate: false, 
    templatePath: dojo.moduleUrl("nbmweb.events", "templates/EventRow.html"),
    attributeMap: dojo.mixin({}, dijit._Widget.prototype.attributeMap, {
        origin: {node: "originCellNode", type: "innerHTML"}, 
        created: {node: "createdCellNode", type: "innerHTML"}
    }), 
    updateSelected: function() {
        this.attr("selected", this.rowSelector.attr("checked"));
    }, 
    disableActions: function() {
        this.rowSelector.attr("readonly", true);
    }, 
    enableActions: function() {
        this.rowSelector.attr("readonly", false);
    }, 
    _setSelectedAttr: function(value) {
        if (value == this.selected)
            return;
        this.selected = value;
        if (value)
            dojo.addClass(this.domNode, "selected");
        else
            dojo.removeClass(this.domNode, "selected");
        this.selected = value;
        this.rowSelector.attr("checked", value);
    }, 
    _setDisabledAttr: function(disabled) {
        if (disabled)
            this.rowSelector.attr("disabled", true);
        else if (!this.attr("selected"))
            this.rowSelector.attr("disabled", false);
        this.disabled = disabled;
    }
});


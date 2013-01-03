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
dojo.provide("nbmweb.edit.InputRow");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit._Contained");

dojo.declare("nbmweb.edit.InputRow", 
             [dijit._Widget, dijit._Templated, dijit._Contained], {
    label: "", 
    content: "", 
    input: null, 
    _rowStarted: false, 
    templateString: "", 
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb.edit", "templates/InputRow.html"), 
    attributeMap: dojo.mixin({}, dijit._Widget.prototype.attributeMap, {
        label: {node: "labelNode", type: "innerHTML"} 
    }),
    startup: function() {
        console.log(this.attr("id"), "startup()");
        dojo.forEach(this.containerNode.childNodes, function(item, index) {
            if (item.nodeName.toLowerCase() == "td") {
                while (item.firstChild)
                    this.containerNode.appendChild(item.firstChild);
                this.containerNode.removeChild(item);
            }
        }, this);
        this.input = this._findInput();
        this._rowStarted = true;
        return this.inherited(arguments);
    }, 
    reset: function() {
        this.input.reset();
    },
    _findInput: function() {
        var input;
        var dijits = dijit.findWidgets(this.containerNode);
        if (dijits.length) {
            if (dijits.length == 1) {
                input = dijits[0];
            } else {
                var inputs = dojo.query(".rowValue", this.containerNode);
                if (inputs.length != 1)
                    throw new Error("Ambiguous input field");
                input = dijit.byNode(inputs[0]);
            }
        }
        return input;
    }, 
    _setContentAttr: function(content) {
        if (content instanceof dijit._Widget)
            content = content.domNode;
        dojo.empty(this.containerNode);
        dojo.place(content, this.containerNode, "append");
        this.input = this._findInput();
        if (this.input && !this.attr("label")) {
            var name = this.input.attr("name");
            var label = name.charAt(0).toUpperCase();
            label = label + name.slice(1).toLowerCase();
            this.attr("label", label);
        }
    }, 
    _getContentAttr: function() {
        return dojo.attr(this.containerNode, "innerHTML");
    }, 
    _setNameAttr: function(name) {
        return this.input.attr("name", name);
    }, 
    _getNameAttr: function() {
        return this.input.attr("name");
    }, 
    _setValueAttr: function(value) {
        return this.input.attr("value", value);
    }, 
    _getValueAttr: function() {
        return this.input.attr("value");
    }, 
    _setDisabledAttr: function(disabled) {
        return this.input.attr("disabled", disabled);
    }, 
    _getDisabledAttr: function() {
        return this.input.attr("disabled");
    }, 
    _setReadOnlyAttr: function(readOnly) {
        return this.input.attr("readOnly", readOnly);
    }, 
    _getReadOnlyAttr: function() {
        return this.input.attr("readOnly");
    }
});
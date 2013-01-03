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
dojo.provide("nbmweb.edit.Node");
dojo.require("dijit._Widget");
dojo.require("dijit._Container");
dojo.require("dijit._Templated");
dojo.require("dijit.form.Form");
dojo.require("dijit.form.Button");
dojo.require("nbmweb.edit.DropDownSelect");
dojo.require("nbmweb.edit.BooleanInput");
dojo.require("nbmweb.edit.InputRow");

dojo.declare("nbmweb.edit.Node",
             [dijit._Widget, dijit._Templated, dijit._Container], {
    types: [],
    classes: [],
    disabled: false,
    readOnly: false,
    templateString: "",
    widgetsInTemplate: true,
    templatePath: dojo.moduleUrl("nbmweb.edit", "templates/Node.html"),
    constructor: function(args, nodeRef) {
        args = args || {};
        this.types = args.types || [];
        this.classes = args.classes || ["even", "odd"];
        console.log(this._descriptor(), " constructor()", args, nodeRef);
    },
    postCreate: function() {
        console.log(this._descriptor(), " postCreate()", arguments);
        dojo.forEach(this.containerNode.childNodes, function(item, index) {
            if (item.nodeName.toLowerCase() == "tbody") {
                console.log("Moving children of item to container: ", item);
                while (item.firstChild)
                    this.containerNode.appendChild(item.firstChild);
                this.containerNode.removeChild(item);
            }
        }, this);
        dojo.forEach(this.containerNode.childNodes, function(item, index) {
            if (item.nodeName.toLowerCase() == "td") {
                console.log("Moving children of item to container: ", item);
                while (item.firstChild)
                    this.containerNode.appendChild(item.firstChild);
                this.containerNode.removeChild(item);
            }
        }, this);
        return this.inherited(arguments);
    },
    startup: function() {
        console.log(this._descriptor(), " startup()");
        if (this._started) {
            console.log(this._descriptor(), " already started.");
            return;
        }
        var children = this.getChildren();
        var unstarted = dojo.filter(children, "return !item._started;");
        console.log("Starting children:", unstarted);
        dojo.forEach(unstarted, "item.startup();");

        var types = this.types;
        this.types = new Array();
        dojo.forEach(types, "this.addType(item);", this);
        if (this.types.length == 0)
            this.typeRow.attr("disabled", true);
        console.log(this.attr("id"), "startup()");

        var classes = this.classes;
        var classCount = classes.length;
        dojo.query("> tr", this.containerNode).forEach(function(row, index) {
            dojo.addClass(row, classes[index % classCount]);
        });
        return this.inherited(arguments);
    },
    reset: function() {
        dojo.forEach(this.getChildren(), "item.reset();");
    },
    addType: function(args) {
        this.typeSelector.addOption(args);
        this.types.push(args);
        if (this.types.length > 1)
            this.typeRow.attr("readOnly", false);
        else
            this.typeRow.attr("readOnly", true);
        this.typeRow.attr("disabled", false);
        dojo.style(this.typeRow.domNode, "display", "");
    },
    setType: function(value, enabled) {
        this.typeRow.attr("value", value);
        if (!enabled)
            this.typeRow.attr("disable", true);
        this.typeRow.attr("readOnly", true);
    },
    disableType: function() {
        this.typeRow.attr("disabled", true);
    },
    enableType: function() {
        this.typeRow.attr("disabled", false);
    },
    addField: function(dijit, label, index) {
        var row = new nbmweb.edit.InputRow({label: label || ""});
        row.attr("input", dijit);
        this.addChild(row, index);
        return row;
    },
    removeField: function(dijit) {
        var children = this.getChildren();
        var dijits = dojo.map(children, "return item.attr('input');");
        var index = dojo.indexOf(dijits, dijit);
        if (index > -1)
            this.removeChild(children[index]);
        return index;
    },
    onCommit: function(values) {
        console.log("onCommit()", this, values);
    },
    onCancel: function(values) {
        console.log("onCancel()", this, values);
    },
    addChild: function(child, index) {
        console.log(this.attr("id"), "addChild()", child, index);
        return this.inherited(arguments);
    },
    disableActions: function() {
        console.log(this.attr("id"), "Disabling actions.");
        this.commitButton.attr("disabled", true);
        this.cancelButton.attr("disabled", true);
    },
    enableActions: function() {
        console.log(this.attr("id"), "Enabling actions.");
        this.commitButton.attr("disabled", false);
        this.cancelButton.attr("disabled", false);
    },
    _onCommit: function(event) {
        dojo.stopEvent(event);
	console.log("_onCommit: value: ", this.attr("value"));
        //CSCte94385 - starts
        if (!this.validate(this.attr("value")))
        	return false;
        //CSCte94385 - ends
        this.disableActions();
        this.onCommit(this.attr("value"));
        return true;
    },
    //CSCte94385
    validate: function(values) {
    	console.log("default Node-validate");
    	if( (typeof values.name != "undefined") && (values.name.length >= 100) ) {
			alert("Error: Name must be less than 100 characters.");
			return false;
		}
		if(values.name.search('[&<>]') != -1) {
			alert("special chars &<> are not allowed in the 'Name' field");
			return false;
		}
		return true;
    },
    _onCancel: function(event) {
        this.disableActions();
        this.onCancel(this.attr("value"));
    },
    _getDialog: function() {
        return dijit.getEnclosingWidget(this.domNode.parentNode);
    },
    _getValueAttr: function() {
        var value = new Object();
        dojo.forEach(this.getChildren(), function(item, index) {
            if (!item.attr("disabled"))
                value[item.attr("name")] = item.attr("value");
        });
        return value;
    },
    _setReadOnlyAttr: function(value) {
        this.readOnly = value;
        dojo.forEach(this.getChildren(), "item.attr('readOnly', value);")
    },
    _setDisabledAttr: function(value) {
        this.disabled = value;
        dojo.forEach(this.getChildren(), "item.attr('disabled', value);")
    },
    _setValueAttr: function(value) {
        dojo.forEach(this.getChildren(), function(item, index) {
            var name = item.attr("name");
            if (name in value)
                item.attr("value", value[name]);
        });
        return this;
    },
    _descriptor: function() {
        var descriptor = "'" + this.declaredClass + "' object";
        if (this.attr("id"))
            descriptor += ' "' + this.attr("id") + '"';
        return "<" + descriptor + ">";
    }
});
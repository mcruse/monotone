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
/*********************************
 * Collection of methods for normalizing values of Form dijits 
 * and field dijits.
 * 
 * Turns checkboxes into boolean values, etc.
 *******************************/
dojo.provide("utils.configure.form");

utils.configure.form.getFields = function(form) {
    var fieldmap = new Object();
    dojo.forEach(form.getChildren(), function(item, index) {
        fieldmap[item.name] = item;
    });
    return fieldmap;
}

utils.configure.form.getValues = function(form) {
    var name;
    var value;
    var field;
    var values = new Object();
    var fields = utils.configure.form.getFields(form);
    for (name in fields) {
        if (name) {
            field = fields[name];
            if (field.type == "checkbox")
                value = field.attr("checked");
            else
                value = field.attr("value");
            values[name] = value;
        } else 
            console.log("Ignoring field because it has no name.");
    }
    return values;
}

utils.configure.form.update = function(form, values) {
    var fields = utils.configure.form.getFields(form);
    utils.configure.form.updateFields(fields, values);
    return form;
}

utils.configure.form.updateFields = function(fields, values) {
    var name;
    var value;
    var field;
    var current;
    var valueattr;
    var truevalues = (
        ["1", 1, "true", true, "True", "on", "On", "ON"]);
    var falsevalues = (
        ["0", 0, "false", false, "False", "off", "Off", "OFF"]);
    for (name in values) {
        console.debug("for (", name, "in", values, ")...");
        if (dojo.exists(name, fields)) {
            console.debug(name, "exists.");
            value = values[name];
            field = fields[name];
            console.debug(name, value, field);
            if (field.type == "checkbox") {
                console.debug("field.type == 'checkbox'");
                console.debug(dojo.indexOf(truevalues, value), 
                              dojo.indexOf(falsevalues, value));
                if (dojo.indexOf(truevalues, value) != -1)
                    value = true;
                else if (dojo.indexOf(falsevalues, value) != -1)
                    value = false;
                else
                    throw new Error("cannot convert '" + value + "' to bool");
                valueattr = "checked";
            } else
                valueattr = "value";
            console.debug(name, ".attr(", valueattr, ",", value, ")");
            field.attr(valueattr, value);
        }
    }
    return fields;
}


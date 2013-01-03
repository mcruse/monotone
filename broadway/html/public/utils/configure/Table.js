/*
Copyright (C) 2009 2010 2011 Cisco Systems

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
dojo.provide("utils.configure.Table");
dojo.require("utils.configure.templates");

dojo.declare("utils.configure.Table", null, {
    constructor: function(table, templates) {
        this.table = dojo.byId(table);
        this.thead = this.table.tHead;
        this.tbody = this.table.tBodies[0];
        this.tfoot = this.table.tFoot;
        this.templates = new Array();
        if (templates)
            dojo.forEach(templates, "this.addRowTemplate(item);", this);
        this.templateIndex = 0;
    },
    toString: function() {
        return this.declaredClass + "(" + this.table + ")";
    }, 
    addRowTemplate: function(template) {
        this.templates.push(template);
    }, 
    addRow: function(values, index) {
        if (typeof(index) == "undefined")
            index = this.getRowCount();
        var html = this.getTemplate(index);
        var placeHolder = this.tbody.insertRow(index);
        var row = dojo.place(html, placeHolder, "replace");
        dojo.forEach(values, function(value, index) {
            row.cells[index].innerHTML = value;
        });
        dojo.parser.parse(row);
    }, 
    updateRow: function(values, index) {
        console.debug("Update row:", this, values, index);
        if (typeof(index) == "undefined")
            throw new Error("updateRow() requires row index, not null");
    }, 
    getRow: function(index) {
        console.debug("Get row:", this, index);
        if (typeof(index) == "undefined")
            throw new Error("getRow() requires row index, not null");
    }, 
    deleteRow: function(index) {
        return this.tbody.deleteRow(index);
    }, 
    getTemplate: function(index) {
        return this.templates[index % this.templates.length];
    }, 
    getRowCount: function() {
        return this.tbody.rows.length;
    }, 
    deleteRows: function(start, end) {
        if (typeof(start) == "undefined")
            start = 0;
        if (typeof(end) == "undefined")
            end = this.getRowCount();
        // Note that pre-decrement used for zero-based row-index.
        while (end > start)
            this.deleteRow(--end);
    }
});

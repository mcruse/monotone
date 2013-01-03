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
dojo.provide("nbmweb.edit.CreateTrigger");
dojo.require("nbmweb.edit.Node");

dojo.declare("nbmweb.edit.CreateTrigger", nbmweb.edit.Node, {
    startup: function() {
        console.log(this.declaredClass, this.attr("id"), "startup()");
        if (!this._started) {
            this.types.push({
                label: "Comparison Trigger",
                value: "ComparisonTrigger"
            });
            this.types.push({
                label: "Bound Trigger",
                value: "BoundTrigger"
            });
        } else {
            console.log(this.attr("id"), " : already started.");
        }
        return this.inherited(arguments);
    },
	//CSCte94385
	validate: function(values) {
		console.log("validate: ", values);
		if(values.name.length >= 100) {
			alert("Error: Name must be less than 100 characters.");
			return false;
		}
        if(values.name.replace(/^\s+|\s+$/g,"").length==0) {
                alert("Error: Blank names not allowed.");
                return false;
        }
		if(values.name.search('[&<>]') != -1) {
			alert("special chars &<> are not allowed in the 'Name' field");
			return false;
		}
		
		//Disabled invalid char check.
		//if(values.name.match('[~!@#$%^&*/><]')) {
		//	alert("Error: Name should not have special characters like [~!@#$%^&*/><]");
		//	return false;
		//}
		//if(values.name.match('[^a-zA-Z0-9_]')) {
		//	alert("Error: Name should have only alphanumeric and '_' charaters.");
		//	return false;
		//}
		return true;
	}
});

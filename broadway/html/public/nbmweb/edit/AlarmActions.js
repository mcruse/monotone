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
dojo.provide("nbmweb.edit.AlarmActions");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.form.Button");

dojo.declare("nbmweb.edit.AlarmActions", [dijit._Widget, dijit._Templated], {
    value: "", 
    manager: null, 
    templateString: "", 
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb.edit", 
                                 "templates/AlarmActions.html"),
    loadAlarm: function() {
        var alarmName = this.attr("value");
		alarmName = decodeSplChars(alarmName);
        console.log("Loading alarm:", this, alarmName);
        return this.manager.refreshAlarmConfiguration(alarmName);
    }, 
    deleteAlarm: function() {
        var alarmName = this.attr("value");
		alarmName = decodeSplChars(alarmName);
        console.log("Deleting alarm:", this, alarmName);
        return this.manager.deleteAlarm(alarmName);
    }, 
    editAlarm: function() {
        var alarmName = this.attr("value");
		alarmName = decodeSplChars(alarmName);
        console.log("Editing alarm:", this, alarmName);
        return this.manager.editAlarm(alarmName);
    },
    triggerAlarm: function() {
        var alarmName = this.attr("value");
		alarmName = decodeSplChars(alarmName);
        console.log("Triggering alarm:", this, alarmName);
        return this.manager.triggerAlarm(alarmName);
    }, 
    clearAlarm: function() {
        var alarmName = this.attr("value");
		alarmName = decodeSplChars(alarmName);
        console.log("Clear alarm:", this, alarmName);
        return this.manager.clearAlarm(alarmName);
    }, 
    destroy: function() {
        console.log("I am being destroyed!!!!!!:", arguments);
        return this.inherited(arguments);
    }, 
    destroyRecursively: function() {
        console.log("I am being destroyed recursively!!!!!!:", arguments);
        return this.inherited(arguments);
    }
});   

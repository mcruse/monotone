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
if (typeof(events) == 'undefined') {
	var events = {};
}
dojo.declare("events.Event", null, {
    constructor: function(guid, source, origin) {
    	this.GUID = guid;
    	this.source = source;
    	this.origin = origin;
    }, 
    equals: function(other) {
        if (this.GUID != other.GUID)
            return false;
        if (this.source != other.source)
            return false;
        if (this.origin != other.origin)
            return false;
        return true;
    }, 
    update: function(event) {
        console.log("Update event:", this, event);
    }
});

dojo.declare("events.AlarmEvent", events.Event, {
    constructor: function(guid, name, source, origin, state, priority, details, timestamp) {
        this.name = name;
        this.priority = priority;
        this.state = state; 
        this.details = details; 
        this.time = timestamp;
    },
    equals: function(other) {
        if (this.inherited(arguments) && this.state == other.state)
            return true;
        else
            return false;
    },
    update: function(event) {
        this.state = event.state;
        this.time = event.time;
        this.details = event.details;
    }
});

events.FaultEvent = function(guid, title, source, origin, faulttype, state, details, timestamp) {
	this.superclass(guid, source, origin);
	this.title = title;
	this.faulttype = faulttype;
	this.state = state;
	this.details = details;
	this.time = timestamp;
}
tools.oo.extend(events.Event, events.FaultEvent);
events.FaultEvent.prototype.equals = function(other) {
	if (this.superclass.prototype.equals.call(this, other) && this.faulttype == other.faulttype && this.state == other.state) {
		return true;
	} else {
		return false;
	}
}
events.FaultEvent.prototype.update = function(event) {
	this.state = event.state;
	this.faulttype = event.faulttype;
	this.details = event.details;
	this.time = event.time;
}

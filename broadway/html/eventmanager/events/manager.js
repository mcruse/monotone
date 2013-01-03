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

events.Manager = function() {
    this.events = new Object();
    this.snoozing = new Object();
	this.last_updated = null;
	//filter
	this.filter_priority = "ALL"; //P1...P10
	this.filter_state = "ALL"; //ACCEPTED, CLEARED, RAISED, CLOSED
	this.filter_origin = ""; //any host name or ip address
	this.filter_name = ""; //
	this.filter_description = ""; //
	this.filter_from_date = "";
	this.filter_from_time = "";
	this.filter_to_date = "";
	this.filter_to_time = "";

	this.handle_events = function(eventItems) {
    	var update_time = new Date();
        for (var i = 0; i < eventItems.length; i++) {
			var event = eventItems[i];
			var existing = this.events[event.GUID];
        	if (existing) {
        	    if (!existing.equals(event)) {
        	        this.update_event(existing, event);
        	    }
        	} else {
        	    this.add_event(event);
        	}
        }
        this.updated(update_time);
    }

    this.add_event = function(event) {
    	this.events[event.GUID] = event;
    	// filter
    	if( !this.is_filter(event) )
    		this.event_added(event);
    }

    this.remove_event = function(event) {
    	if (typeof(event) == "string") {
    		event = this.events[event];
    	}
    	var event = this.events[event.GUID];
    	delete this.events[event.GUID];
    	// filter
    	if( !this.is_filter(event) )
    		this.event_removed(event);
    }
    // TO DO - check for state, description filter.
    this.update_event = function(existing, event) {
    	// fix for CSCtf80095
    	var old_visible = false;
    	if( !this.is_filter(existing) )
    		old_visible = true;
    	var new_visible = false;
    	if( !this.is_filter(event) )
    		new_visible = true;
    	existing.update(event);
    	// filter
    	if( old_visible )
    		this.event_updated(existing);
    	else if(!old_visible && new_visible)
    		this.event_added(existing);
    }
    //filter logic - return 'true' means that event will not be shown in ui
    this.is_filter = function(event) {
    	var description = "";
    	for (var i in event.details){
    		description += event.details[i];
    	}
    	if( !(( this.filter_priority == "ALL" || event.priority == this.filter_priority ) &&
    		( this.filter_state == "ALL" || event.state == this.filter_state ) &&
    		( this.filter_origin == "" || event.origin.indexOf(this.filter_origin) != -1 ) &&
    		( this.filter_name == "" || event.name.indexOf(this.filter_name) != -1 ) &&
    		( this.filter_description == "" || description.indexOf(this.filter_description) != -1 )
    		)
    	  )
    		return true;
    	//date, time logic
    	var event_date_part = event.time.toDateString();
		var event_time_part = event.time.toTimeString();
		/*if(this.filter_from_date != "" &&
				(new Date(this.filter_from_date) > new Date(event_date_part)) )
			return true;
		if(this.filter_to_date != "" &&
				(new Date(this.filter_to_date) < new Date(event_date_part)) )
			return true;*/
		if(this.filter_from_date != "" &&
				(new Date(this.filter_from_date + " " + this.filter_from_time) > event.time))
			return true;
		if(this.filter_to_date != "" &&
				(new Date(this.filter_to_date + " " +  this.filter_to_time) < event.time))
			return true;
		// bcoz it time string is 24 hour format so just string comparison is fine.
		// ** if it does not work then convert to Date and then compare
		/*if(this.filter_from_time != "" &&
				(new Date("1/1/2001 " + this.filter_from_time)).toTimeString() > event_time_part)
			return true;
		if(this.filter_to_time != "" &&
				(new Date("1/1/2001 " + this.filter_to_time)).toTimeString() < event_time_part)
			return true;*/
    	return false;
    }
    this.get_event = function(guid) {
    	return this.events[guid];
    }

    this.snooze_event = function(id, period) {
    	var event = this.get_event(id);
    	this.remove_event(event);
    	var manager = this;
    	function wakefunc() {manager.snooze_expire(event);}
    	var wakeup = window.setTimeout(wakefunc, period*1000);
    	this.snoozing[id] = [event, wakeup];
    }

    this.snooze_expire = function(event) {
    	if (event.id in this.snoozing)
    		delete this.snoozing[event.id];
    	if (!(event.id in this.events))
    		this.add_event(event);
    }

    this.unsnooze_event = function(id) {
    	var entry = this.snoozing[id];
    	if (!entry) return;
		window.clearTimeout(entry[1]);
		this.snooze_expire(entry[0]);
    }
    // Event hook methods.  Listeners register advice calls.
    this.event_added = function(event) {}
    this.event_removed = function(event) {}
    this.event_updated = function(event) {}
    this.updated = function(update_time) {
    	this.last_updated = update_time;
    }
}

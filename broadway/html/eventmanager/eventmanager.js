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
if (typeof(eventmanager) == 'undefined')
	var eventmanager = {};
if (typeof(events) == 'undefined')
	var events = {};
if (typeof(ui) == 'undefined')
	var ui = {};
if (typeof(data) == 'undefined')
	var data = {};
if (typeof(tools) == 'undefined')
	var tools = {};

loader.add_module('/eventmanager/tools/oo.js', tools, 'oo');
loader.add_module('/eventmanager/tools/scheduler.js', tools, 'scheduler');
loader.add_module('/eventmanager/data/communication.js', data, 'communication');
loader.add_module('/eventmanager/data/rss.js', data, 'rss');
loader.add_module('/eventmanager/events/factory.js', events, 'factory');
loader.add_module('/eventmanager/events/display.js', events, 'display');
loader.add_module('/eventmanager/ui/factory.js', ui, 'factory');
dojo.require('dojox.uuid.generateRandomUuid');

eventmanager.Application = function(url) {
	this.manager = new events.factory.create_event_manager();
	this.feed = new data.rss.Feed();
	this.table = null;
	this.clientid = null;
	this.make_request = tools.oo.bound_method(this, make_request);
	this.handle_response = tools.oo.bound_method(this, handle_response);
	this.handle_error = tools.oo.bound_method(this, handle_error);
    this.connection = new data.communication.Connection({
        url: url,
        type: "xml",
        method: "GET"
    });
    this.scheduler = new tools.scheduler.Scheduler(this.make_request);

	function handle_response(response) {
		if (this.period)
			this.scheduler.schedule(this.period);
		this.feed.parse(response);
		var rssitems = this.feed.get_rss_items();
		var eventItems = new Array();
		for (var i = 0; i < rssitems.length; i++) {
			var item = rssitems[i];
			var eventobj = events.factory.event_from_item(item);
			eventItems.push(eventobj);
		}
		if (rssitems.length > 0) {
			dojo.byId("acknowledge-selected").disabled = false;			
		}
		this.manager.handle_events(eventItems);
		this.table.refresh_display();
		return response;
	}
	//filter starts
	// TO DO -  ** we may need some lock until filter is finished, next event
	// 			response should not be processed.
	this.filterit = function() {
		//var filter_priority = document.getElementById("filter-priority");
		var priority_index = filter_priority.selectedIndex || 0;
        var priority_option = filter_priority.options[priority_index];

        //var filter_state = document.getElementById("filter-state");
		var state_index = filter_state.selectedIndex || 0;
        var state_option = filter_state.options[state_index];

        //var filter_origin = document.getElementById("filter-origin");
        var origin_text = filter_origin.value;

        //var filter_name = document.getElementById("filter-name");
        var name_text = filter_name.value;

        //var filter_description = document.getElementById("filter-description");
        var description_text = filter_description.value;
        var from_date_text = filter_from_date.value;
        var from_time_text = filter_from_time.value;
        var to_date_text = filter_to_date.value;
        var to_time_text = filter_to_time.value;
        // validate date, time
        if(from_date_text != "") {
        	if(isNaN(Date.parse(from_date_text + " 00:00 AM"))) {
        		alert("Error: 'from date' format is not valid.");
            	return;
        	}
        }
        if(to_date_text != "") {
        	if(isNaN(Date.parse(to_date_text + " 00:00 AM"))) {
        		alert("Error: 'to date' format is not valid.");
            	return;
        	}
        }
        if(from_time_text != "") {
        	if(isNaN(Date.parse("1/1/2001 " + from_time_text))) {
        		alert("Error: 'from time' format is not valid.");
            	return;
        	}
        }
        if(to_time_text != "") {
        	if(isNaN(Date.parse("1/1/2001 " + to_time_text))) {
        		alert("Error: 'to time' format is not valid.");
            	return;
        	}
        }
        if(from_date_text == "" && from_time_text != "") {
        	alert("Error: When 'from time' is specificed, 'from date' can not be blank.");
        	return;
        }
        if(to_date_text == "" && to_time_text != "") {
        	alert("Error: When 'to time' is specificed, 'to date' can not be blank.");
        	return;
        }
        if(from_date_text != "" && from_time_text == "")
        	filter_from_time.value = "00:00:00 AM";
        if(to_date_text != "" && to_time_text == "")
        	filter_to_time.value = "11:59:59 PM";

        // TO DO - for Origin, Name, Description
        /*if(this.manager.filter_priority == priority_option.value &&
        		this.manager.filter_state == state_option.value &&
        		this.manager.filter_origin == origin_text &&
        		this.manager.filter_name == name_text &&
        		this.manager.filter_description == description_text
        	) {
        	// Do Nothing because no filter changed.
        	return;
        }*/
        this.manager.filter_priority = priority_option.value
        this.manager.filter_state = state_option.value;
        this.manager.filter_origin = origin_text;
		this.manager.filter_name = name_text;
		this.manager.filter_description = description_text;
		this.manager.filter_from_date = from_date_text;
		this.manager.filter_from_time = from_time_text;
		this.manager.filter_to_date = to_date_text;
		this.manager.filter_to_time = to_time_text;

		this.table.clear_display();
		this.table.first_load_complete = false;
		this.table.page_index = 0;
		this.evt = new Array();
		for(var i in this.manager.events) {
			var evt_item = this.manager.events[i];
			this.evt.push(evt_item);
		}
		this.manager.events = {};
		this.manager.handle_events(this.evt);
		this.table.refresh_display();
	}
	this.filter_clear = function() {
		filter_priority.selectedIndex = 0;
		filter_state.selectedIndex = 0;
		filter_origin.value = "";
		filter_name.value = "";
		filter_description.value = "";
		filter_from_date.value = "";
		filter_to_date.value = "";
		filter_from_time.value = "";
		filter_to_time.value = "";
		this.filterit();
		// clear labels
		//clear_labels();
	}
	this.filter_reset = function() {
		filter_priority.value = this.manager.filter_priority;
		filter_state.value = this.manager.filter_state;
		filter_origin.value = this.manager.filter_origin;
		filter_name.value = this.manager.filter_name;
		filter_description.value = this.manager.filter_description;
		filter_from_date.value = this.manager.filter_from_date;
		filter_to_date.value = this.manager.filter_to_date;
		filter_from_time.value = this.manager.filter_from_time;
		filter_to_time.value = this.manager.filter_to_time;
		// clear labels
		//clear_labels();
	}
	//filter ends
	function handle_error(error) {
		console.error(error);
		// CSCte94039
		alert(error.responseText);
		return error;
	}

	function make_request(data, response_listener, error_listener) {
	    var args = {};
        if (data)
            args.method = "POST";
        args.data = data || {};
		if (!this.clientid)
			this.clientid = dojox.uuid.generateRandomUuid();
		args.data.clientid = this.clientid;
		var deferred = this.connection.send_request(args);
		deferred.addCallbacks(this.handle_response, this.handle_error);
		if (response_listener) {
		  deferred.addCallback(function(response) {
		      response_listener(response);
		      return response;
		  });
		}
		if (error_listener) {
          deferred.addErrback(function(error) {
              error_listener(error);
              return error;
          });
        }
		return deferred;
	}

	this.send_command = function(guid, command, onLoad, onError) {
		this.scheduler.cancel_scheduled();
        console.log("send_command()", this, guid, command, onLoad, onError);
        var data = {'command': command, 'guid': guid}
		return this.make_request(data, onLoad, onError);
	}

	this.start = function(interval) {
		this.period = interval;
		this.scheduler.schedule(0);
	}

	this.stop = function() {
		this.period = null;
		this.scheduler.cancel_scheduled();
	}

	this.pause = function() {
		this.scheduler.pause();
	}

	this.resume = function() {
		try {
			this.scheduler.resume();
		} catch (error) {
			alert('The check-box and scheduler are out of sync:' + error.toString());
		}
	}

	this.setup_interface = function() {
		if (this.table != null)
			throw new Error("UI already setup.");
		events.display.setup_templates();
		this.table = ui.factory.table_from_elements(
		    'events-table', 'rows-per-page', 'pagination');
	    dojo.connect(this.manager, 'event_added', this.table, 'add_row');
	    dojo.connect(this.manager, 'event_removed', this.table, 'remove_row');
	    dojo.connect(this.manager, 'event_updated', this.table, 'update_row');
	}
}


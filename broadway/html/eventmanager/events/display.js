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
events.display = {};
events.display.initialized = false;

events.display.setup_templates = function() {
	var alarmtemplate = document.getElementById('alarmtemplate');
	var faulttemplate = document.getElementById('faulttemplate');
	alarmtemplate.parentNode.removeChild(alarmtemplate);
	faulttemplate.parentNode.removeChild(faulttemplate);
	events.display.alarmtemplate = alarmtemplate;
	events.display.faulttemplate = faulttemplate;
	events.display.initialized = true;
}

events.display.create_event_row = function(eventobj) {
	if (!events.display.initialized)
		events.display.setup_templates();
	if (eventobj instanceof events.AlarmEvent) {
		return events.display.create_alarm_row(eventobj);
	} else if (eventobj instanceof events.FaultEvent) {
		return events.display.create_fault_row(eventobj);
	} else if (eventobj instanceof events.FaultEvent) {
		throw new Error('No row associated with this event type.');
	} else throw new Error('Unrecognized data type.');
}

events.display.create_alarm_row = function(eventobj) {
	var row = events.display.alarmtemplate.cloneNode(true);
	var select = row.getElementsByTagName('select')[0];
	var input = row.getElementsByTagName('input')[0];
	input.onchange = events.display.alarmtemplate.getElementsByTagName('input')[0].onchange;
	select.onchange = events.display.alarmtemplate.getElementsByTagName('select')[0].onchange;
	select.selectedIndex = null;
	row.id = eventobj.GUID;
	return row;
}

events.display.create_fault_row = function(eventobj) {
	var row = events.display.faulttemplate.cloneNode(true);
	var select = row.getElementsByTagName('select')[0];
	select.onchange = events.display.alarmtemplate.getElementsByTagName('select')[0].onchange;
	select.selectedIndex = null;	
	row.id = eventobj.GUID;
	return row;	
}

events.display.update_event_row = function(eventobj, row) {
	if (eventobj instanceof events.AlarmEvent) {
		return events.display.update_alarm_row(eventobj, row);
	} else if (eventobj instanceof events.FaultEvent) {
		return events.display.update_fault_row(eventobj, row);
	} else if (eventobj instanceof events.FaultEvent) {
		throw new Error('No row associated with this event type.');
	} else throw new Error('Unrecognized data type.');
}

events.display.update_alarm_row = function(eventobj, row) {
	var cells = events.display.get_row_cells(row);
	cells[1].innerHTML = eventobj.name;
	cells[2].innerHTML = eventobj.origin;
	cells[3].innerHTML = eventobj.priority;
	cells[4].innerHTML = eventobj.state;
	cells[5].innerHTML = eventobj.time;
	var details = eventobj.details.slice(0);
	var messages = events.display.create_messages(details.reverse());
	cells[6].replaceChild(messages, cells[6].firstChild);
	row.getElementsByTagName('select')[0].selectedIndex = null;	
}

events.display.create_messages = function(details) {
	var messages = document.createElement("ul");
	dojo.addClass(messages, "messages");
	for (var i=0; i < details.length; i++) {
		var message = document.createElement("li");
		dojo.addClass(message, "message");
		if (i==0 && details.length > 1) {
            var anchor = document.createElement("a");
            anchor.innerHTML = "+";
            message.appendChild(anchor);
            dojo.addClass(message, "newest");               
            dojo.addClass(messages, "expandible");
            var toggle = dojo.partial(
                events.display.toggle_expansion, messages);
            dojo.connect(anchor, "onclick", toggle);
	    } 
        var content = document.createElement("span");
		content.innerHTML = details[i];
		message.appendChild(content);
		messages.appendChild(message);
	}
	return messages;
}

events.display.toggle_expansion = function(messages) {
	if (dojo.hasClass(messages, "expandible")) {
		dojo.toggleClass(messages, "expanded");
	}
}

events.display.update_fault_row = function(eventobj, row) {
	var cells = events.display.get_row_cells(row);
	cells[1].innerHTML = eventobj.title;
	cells[2].innerHTML = eventobj.origin;
	cells[3].innerHTML = eventobj.faulttype.toUpperCase();
	cells[4].innerHTML = eventobj.state;
	cells[5].innerHTML = eventobj.time;
	var messages = events.display.create_messages(eventobj.details);
	cells[6].appendChild(messages);
	row.getElementsByTagName('select')[0].selectedIndex = null;
}

events.display.get_row_cells = function(row) {
	// Utility function builds cell array manually, IE7 cloned rows lose identity.
	var cells = new Array();
	for (var i = 0; i < row.childNodes.length; i++) {
		var cell = row.childNodes[i];
		if ((cell.nodeName.toUpperCase() == 'TD') 
			|| (cell.nodeName.toUpperCase() == 'TH')) {
			cells.push(cell);
		}
	}
	return cells;
}

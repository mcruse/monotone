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
loader.add_module('/eventmanager/events/event.js', events, 'Event');
loader.add_module('/eventmanager/events/manager.js', events, 'Manager');
events.factory = {};

events.factory.create_event_manager = function() {
	return new events.Manager();
}

events.factory.event_from_item = function (rssitem) {
	var categories = rssitem.categories;
    var guid = rssitem.guid;
    var source = rssitem.source;
   	var origin = rssitem.source;
	if (categories.indexOf('Alarm') != -1) {
		factory = events.factory.alarm_from_item;
	} else if (categories.indexOf('Fault') != -1) {
		factory = events.factory.fault_from_item;
	} else if (categories.indexOf('Event') != -1) {
		return new events.Event(guid, source, origin);
	} else {
		throw new Error('RSS Item is not an event');
	}
	return factory(guid, source, origin, rssitem);
}

events.factory.alarm_from_item = function(guid, source, origin, item) {
    var title_array = item.title.match(/(.*) \((.*)\): (.*)/);
    var name = title_array[1];
    var priority = title_array[2];
    var state = title_array[3];
    var details = item.details;
	var timestamp = new Date(Date.parse(item.pub_date));
	return new events.AlarmEvent(
		guid, name, source, origin, state, priority, details, timestamp);
}

events.factory.fault_from_item = function(guid, source, origin, item) {
    var title_array = item.title.match(/(.*) \((.*)\): (.*)/);
	var title = title_array[1];
	var faulttype = title_array[2];
	var state = title_array[3];
	var details = item.details;
	var timestamp = new Date(Date.parse(item.pub_date));
	return new events.FaultEvent(
		guid, title, source, origin, faulttype, state, details, timestamp);
}

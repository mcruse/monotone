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
if (typeof(data) == 'undefined') {
	var data = {};
}
data.rss = {};
dojo.require("dojox.xml.parser");

data.rss.Feed = function() {
	this.rsselement = null;
}
data.rss.Feed.prototype.parse = function(content) {
	if (typeof(content) == 'string') {
		content = dojox.xml.parser.parse(content);
	}
	this.rsselement = new data.rss.Rss(content);
}
data.rss.Feed.prototype.get_rss_element = function() {
	return this.rsselement;
}
data.rss.Feed.prototype.get_rss_channel = function() {
	return this.get_rss_element().get_rss_channel();
}
data.rss.Feed.prototype.get_rss_items = function() {
	return this.get_rss_channel().get_rss_items();
}

data.rss.Rss = function(rssxml) {
    /* Instances of this object represent a particular
    * RSS update; attributes and functions of this object
    * provide easy access to meaningful RSS constructs.
    */
    var rsselement = rssxml.getElementsByTagName('rss')[0];
    this.version = rsselement.getAttribute('version');
    this.channel = new data.rss.Channel(
        rsselement.getElementsByTagName('channel')[0]);
}
data.rss.Rss.prototype.get_rss_channel = function() {
	return this.channel;
}

data.rss.Channel = function(channel) {
    var title_element = channel.getElementsByTagName('title')[0]
	var link_element = channel.getElementsByTagName('link')[0];
	var desc_element = channel.getElementsByTagName('description')[0];

    this.title = title_element.firstChild.nodeValue;
	this.link = link_element.firstChild.nodeValue;
	this.description = desc_element.firstChild.nodeValue;

    this.items = new Array();
    var itemelements = channel.getElementsByTagName('item');
    for (var i = 0; i < itemelements.length; i++) {
        this.items[i] = new data.rss.Item(itemelements[i]);
    }
}
data.rss.Channel.prototype.get_rss_items = function() {
	return this.items;
}

data.rss.Item = function(item) {
	var title_element = item.getElementsByTagName('title')[0];
	var link_element = item.getElementsByTagName('link')[0];
	var guid_element = item.getElementsByTagName('guid')[0];
	var desc_element = item.getElementsByTagName('description')[0];
	var date_element = item.getElementsByTagName('pubDate')[0];
	var source_element = item.getElementsByTagName('source')[0];
	var categories = item.getElementsByTagName('category');

	this.title = title_element.firstChild.nodeValue;
	this.source = source_element.firstChild.nodeValue;
	this.link = link_element.firstChild.nodeValue;
	this.guid = guid_element.firstChild.nodeValue;
	
	this.description = desc_element.firstChild.nodeValue;
	var desclines = this.description.split(/<br.+>/);
	desclines = dojo.map(desclines, dojo.trim);
	desclines = dojo.filter(desclines, Boolean);
	this.details = desclines;
	
	this.pub_date = date_element.firstChild.nodeValue;
	this.categories = new Array();
	for (var i = 0; i < categories.length; i++) {
		var category = categories[i].firstChild.nodeValue;
		this.categories.push(category);
	}
}

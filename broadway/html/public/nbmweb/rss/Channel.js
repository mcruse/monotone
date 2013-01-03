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
dojo.provide("nbmweb.rss.Channel");
dojo.require("nbmweb.rss._Element");
dojo.require("nbmweb.rss.Item");

dojo.declare("nbmweb.rss.Channel", nbmweb.rss._Element, {
    link: "", 
    title: "", 
    guids: null, 
    items: null,
    description: "", 
    constructor: function(element) {
        this.guids = new Object();
        this.items = new dojo.NodeList();
        var titleNode = dojo.query("title", element)[0];
        var linkNode = dojo.query("link", element)[0];
        var descNode = dojo.query("description", element)[0];
        this.title = titleNode.firstChild.nodeValue;
        this.link = linkNode.firstChild.nodeValue;
        this.description = descNode.firstChild.nodeValue;
        dojo.query("item", element).forEach(function(item, index) {
            this.items.push(new nbmweb.rss.Item(item));
        }, this);
        this.updateMap();
    },
    byGuid: function(guid) {
        return this.byIndex(this.guids[guid]);
    }, 
    byIndex: function(index) {
        return this.items[index];
    }, 
    getItem: function(spec) {
        var item;
        if (dojo.isString(spec))
            item = this.byGuid(spec);
        else if (typeof(spec) == "number")
            item = this.byIndex(spec);
        else
            throw new Error("getItem() expects GUID or index, not: " + spec);
        return item;
    },
    getIndex: function(item) {
        if (!(item instanceof(nbmweb.rss.Item)))
            item = this.getItem(item);
        return this.guids[item.guid];
    }, 
    hasItem: function(item) {
        return typeof(this.getIndex(item)) == "number"; 
    }, 
    addItem: function(item) {
        var index = this.items.length;
        if (this.hasItem(item))
            index = this.getIndex(item);
        this.items[index] = item;
        this.guids[item.guid] = index;
        return index;
    }, 
    popItem: function(spec) {
        var item = this.getItem(spec);
        var index = this.getIndex(item.guid);
        this.items.splice(index, 1);
        this.updateMap();
        return item;
    }, 
    updateMap: function() {
        this.guids = new Object();
        this.items.forEach("this.guids[item.guid] = index;", this);
    }
});
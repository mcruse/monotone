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
dojo.provide("nbmweb.events.AlarmRow");
dojo.require("nbmweb.events.EventRow");

dojo.declare("nbmweb.events.AlarmRow", nbmweb.events.EventRow, {
    guid: "", 
    name: "", 
    state: "", 
    created: "", 
    priority: "", 
    history: null, 
    messages: null, 
    statusMessage: "", 
    templateString: "", 
    acknowledged: true, 
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb.events", "templates/AlarmRow.html"), 
    attributeMap: dojo.mixin({}, dijit._Widget.prototype.attributeMap, {
        name: {node: "nameCellNode", type: "innerHTML"}, 
        origin: {node: "originCellNode", type: "innerHTML"}, 
        state: {node: "stateCellNode", type: "innerHTML"}, 
        created: {node: "createdCellNode", type: "innerHTML"}
    }),
    constructor: function(kwArgs, srcNodeRef) {
        this.history = kwArgs.history || [];
        console.log("new " + this.declaredClass + "()", kwArgs, srcNodeRef);
    }, 
    startup: function() {
        this.attr("messages", this.history.slice(0).reverse());
        return this.inherited(arguments);
    }, 
    postMixInProperties: function() {
        if (!this.attr("guid"))
            this.attr("disabled");
        return this.inherited(arguments);
    }, 
    acknowledgeAlarm: function(event) {
        this.disableActions();
        var deferred = eventmanager.acknowledgeEvents([this.attr("guid")]);
        deferred.addBoth(dojo.hitch(this, function(response) {
            this.enableActions();
            return response;
        }));
    }, 
    disableActions: function() {
        this.acknowledgeButton.attr("readOnly", true);
        return this.inherited(arguments);
    }, 
    enableActions: function() {
        this.acknowledgeButton.attr("readOnly", false);
        return this.inherited(arguments);
    }, 
    clear: function() {
        var attrs = {
            guid: "", 
            name: "", 
            state: "",
            origin: "", 
            history: [], 
            created: "", 
            priority: "", 
            disabled: true, 
            selected: false, 
            acknowledged: false
        };
        this.attr(attrs);
    }, 
    _setGuidAttr: function(guid) {
        this.guid = guid;
        if (guid)
            this.attr("disabled", false);
        else
            this.attr("disabled", true);
        return;
    }, 
    _setDisabledAttr: function(disabled) {
        if (disabled == this.attr("disabled"))
            return;
        if (disabled)
            this.acknowledgeButton.attr("disabled", true);
        else if (!this.attr("selected"))
            this.acknowledgeButton.attr("disabled", false);
        return this.inherited(arguments);
    }, 
    _setSelectedAttr: function(value) {
        if (this.rowSelector.attr("disabled"))
            return;
        this.acknowledgeButton.attr("disabled", value);
        return this.inherited(arguments);
    },
    _setHistoryAttr: function(history) {
        if (this.history.join() == history.join())
            return;
        this.history = history;
        this.attr("messages", history.slice(0).reverse());
    }, 
    _setAcknowledgedAttr: function(value) {
        if (value) {
            this.rowSelector.attr("checked", false);
            this.rowSelector.attr("disabled", true);
            this.acknowledgeButton.attr("disabled", true);
        } else if (!this.attr("disabled")) {
            this.rowSelector.attr("disabled", false);
            this.acknowledgeButton.attr("disabled", false);
        }
        this.acknowledged = value;
    }, 
    _setPriorityAttr: function(priority) {
        if (priority) {
            if (dojo.isString(priority))
                priority = Number(priority.substr(1));
            if (isNaN(priority))
                priority = 1;
        } else {
            priority = 0;
        }
        this.priority = priority;
        if (priority) {
            priority = String(priority);
            if (priority.length < 2)
                priority = "0" + priority;
            priority = "P" + priority;
        } else {
            priority = "";
        }
        dojo.attr(this.priorityCellNode, "innerHTML", priority);
    }, 
    _setMessagesAttr: function(messages) {
        this.messages = messages.slice(0);
        var open = this.statusMessagePane.attr("open");
        var statusMessage = "";
        if (messages.length)
            statusMessage = messages.shift();
        this.statusMessagePane.attr("open", false);
        this.statusMessagePane.attr("toggleable", false);
        this.attr("statusMessage", statusMessage);
        dojo.empty(this.statusMessagesTableNode);
        if (messages.length) {
            dojo.forEach(messages, function(message, index) {
                var messageRow = dojo.create("tr", {
                    className: "statusMessageRow"
                }, this.statusMessagesTableNode);
                var messageCell = dojo.create("td", {
                    innerHTML: message, 
                    className: "statusMessageCell"
                }, messageRow, "last");
            }, this);
            this.statusMessagePane.attr("toggleable", true);
            this.statusMessagePane.attr("open", open);
        }
    }, 
    _setStatusMessageAttr: function(statusMessage) {
        if (!this.statusMessagePane.attr("open"))
            this.statusMessagePane.attr("title", statusMessage);
        this.statusMessage = statusMessage;
    }
});


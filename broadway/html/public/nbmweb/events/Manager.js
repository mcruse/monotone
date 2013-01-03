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
dojo.provide("nbmweb.events.Manager");
dojo.require("dojo.data.ItemFileWriteStore");
dojo.require("dijit._Widget");
dojo.require("utils.display");
dojo.require("mpx.node.Proxy");
dojo.require("nbmweb.events.EventsTable");

dojo.declare("nbmweb.events.Manager", dijit._Widget, {
    debug: 0,
    period: 5,
    pageSize: 0, 
    pageIndex: 0, 
    pageNumber: 1,
    eventCount: 0, 
    clientId: "", 
    display: null, 
    queryParams: null, 
    updatesOnly: false, 
    eventsTable: null, 
    updateHeader: null, 
    autoRefresh: false, 
    lastUpdated: null, 
    eventService: null, 
    descending: true, 
    sortField: "createdUTC", 
    sortDescending: true, 
    refreshLoopCounter: 0, 
    eventServiceUrl: "/services/Event Store", 
    constructor: function(args) {
        this.refreshLoopCounter = 0;
        this.store = new dojo.data.ItemFileWriteStore({
            data: {
                identifier: "id", 
                label: "name", 
                items: []
            }
        }); 
    }, 
    postMixInProperties: function() {
        console.log(this.attr("id"), "postMixinProperties()");
        if (!this.eventService) {
            var serviceUrl = this.eventServiceUrl;
            this.eventService = new mpx.node.Proxy({nodeURL: serviceUrl});
            console.log(this.id, "setup event service:", serviceUrl);
        }
        return this.inherited(arguments);
    }, 
    startup: function() {
        console.log(this.attr("id"), "startup()");
        this._setupSortHeaders();
        this.display = new nbmweb.events.EventsTable({
            store: this.store, 
            rowsPerPage: this.pageSize
        }, dojo.byId("events-table"));
        this._pageSizeConnection = dojo.connect(this.display, 
                                                "onRowsPerPageChanged", 
                                                this, "_setPageSizeAttr");
        this._pageNumberConnection = dojo.connect(this.display, 
                                                  "onPageChanged", 
                                                  this, "_setPageNumberAttr");
        this._sortChangeConnection = dojo.connect(this.display, 
                                                  "onSortChanged", 
                                                  this, "handleSortChange");
        
        var ackSelected = this.display.acknowledgeSelected;
        this._ackSelectedConnection = dojo.connect(ackSelected, 
                                                   "onClick", this, 
                                                   "acknowledgeSelected");
        this.display.startup();
        console.log(this.attr("id"), "startup() complete.");
        return this.inherited(arguments);
    }, 
    _addAlarmItem: function(item) {
        var itemValues = item.values;
        itemValues.id = item.id;
        itemValues.index = item.index;
        if (this.debug > 1)
            console.log("Creating item:", item, itemValues);
        this.store.newItem(itemValues);
    }, 
    _updateAlarmItem: function(newItem, oldItem) {
        var changed = 0;
        var itemValues = newItem.values;
        itemValues.index = newItem.index;
        for (var attr in itemValues) {
            if (attr != "id") {
                var newValues = itemValues[attr];
                if (!dojo.isArray(newValues))
                    newValues = [newValues];
                var oldValues = this.store.getValues(oldItem, attr);
                if (newValues.join() != oldValues.join()) {
                    this.store.setValues(oldItem, attr, newValues);
                    changed += 1;
                }
            }
        }
        if (this.debug > 1)
            console.log("Update item (new, old):", newItem, oldItem, changed);
    }, 
    refreshLoop: function(refreshLoopCount) {
        var delay = this.period;
        var clientId = this.attr("clientId");
        var pageSize = this.attr("pageSize");
        var startIndex = this.attr("pageIndex") * pageSize;
        var sorting = {
            attribute: this.attr("sortField"), 
            descending: this.attr("sortDescending")
        };
        var params = {
            count: pageSize, 
            start: startIndex, 
            sort: [sorting], 
            queryOptions: {}, 
            query: this.attr("queryParams")
        };
        if (clientId)
            params.clientId = clientId;
        if (this.attr("updatesOnly"))
            params.queryOptions.reset = false;
        else
            params.queryOptions.reset = true;
        this.attr("updatesOnly", true);
        var errorMessage = "";
        var onLoad = dojo.hitch(this, function(response) {
            if (this.debug)
                console.log("Response recieved:", response);
            if (refreshLoopCount) {
                if (refreshLoopCount != this.refreshLoopCounter) {
                    console.log("Response ignored: counter changed.");
                    return;
                }
            }
            errorMessage = "";
            var itemMap = new Object();
            var oldItems = new Object();
            dojo.forEach(response.items, "this[item.id] = item;", itemMap);
            // Rip through existing store items, removing those 
            // that are no longer part of the query results.
            // Build hash of existing items that are being updated, 
            // so a second store query by item ID can be skipped.
            this.store.fetch({
                scope: this, 
                onItem: function(item) {
                    var itemId = this.store.getIdentity(item);
                    if (!itemMap[itemId]) {
                        if (this.debug > 1)
                            console.log("Deleting item:", itemId, item);
                        this.store.deleteItem(item);
                    } else {
                        oldItems[itemId] = item;
                    }
                }
            });
            dojo.forEach(response.items, function(item, index) {
                var oldItem = oldItems[item.id];
                if (oldItem)
                    this._updateAlarmItem(item, oldItem);
                else
                    this._addAlarmItem(item);
            }, this);
            if (this.store.isDirty())
                this.store.save();
            if (response.clientId != this.attr("clientId")) {
                var oldId = this.attr("clientId");
                this.attr("clientId", response.clientId);
                console.log("Changed client ID:", oldId, response.clientId);
            }
            this.attr("eventCount", response.total);
            params.clientId = response.clientId;
            params.queryOptions.reset = false;
            if (this.debug > 1)
                console.log("Updated params:", params);
            this.updated();
            return response;
        });
        var onError = dojo.hitch(this, function(error) {
            var lastMessage = errorMessage;
            errorMessage = error.message;
            if (errorMessage != lastMessage)
                utils.display.failure("Load events failed.", errorMessage);
            console.log("Request failed:", errorMessage, error);
            return error;
        });
        var reschedule = dojo.hitch(this, function(response) {
            if (refreshLoopCount == this.refreshLoopCounter)
                this.scheduledRefresh = setTimeout(refresh, delay * 1000);
            else
                console.log("Stopped rescheduling: counter changed.");
            return response;
        });
        var refresh = dojo.hitch(this, function() {
            if (this.debug) 
                console.log("Requesting update:", params);
            var deferred = this.eventService.fetch(params);
            deferred.addCallbacks(onLoad, onError);
            if (refreshLoopCount)
                deferred.addBoth(reschedule);
            console.log(params);
        });
        refresh();
    }, 
    refresh: function() {
        this.refreshLoop(0);
    }, 
    startRefreshing: function() {
        this.refreshLoop(++this.refreshLoopCounter);
    }, 
    stopRefreshing: function() {
        this.refreshLoopCounter++;
        if (this.scheduledRefresh)
            clearTimeout(this.scheduledRefresh);
        this.scheduledRefresh = null;
    }, 
    updated: function() {
        this.lastUpdated = new Date();
        if (this.updateHeader)
            dojo.attr(this.updateHeader, "innerHTML", this.lastUpdated);
        return this.lastUpdated;
    }, 
    handleSortChange: function(attribute, descending) {
        var oldAttribute = this.attr("sortField");
        var oldDescending = this.attr("sortDescending");
        if (attribute == oldAttribute && oldDescending == descending)
            return;
        if (this._started) {
            this.stopRefreshing();
            this.deleteItems();
        }
        this.sortField = attribute;
        this.sortDescending = descending;
        if (this._started) {
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }
        console.log("Sort changed:", attribute, descending);
    }, 
    deleteItems: function() {
        this.display.selectAllRows.attr("checked", false);
        this.display.getSelected().forEach("item.attr('selected', false);");
        this.store.fetch({
            scope: this, 
            onComplete: function(items) {
                dojo.forEach(items, this.store.deleteItem, this.store);
            }
        });
        this.store.save();
        this.attr("updatesOnly", false);
    }, 
    _setAutoRefreshAttr: function(autoRefresh) {
        if (autoRefresh == this.autoRefresh)
            return;
        if (autoRefresh)
            this.startRefreshing();
        else
            this.stopRefreshing();
        this.autoRefresh = autoRefresh;
    }, 
    _setPageNumberAttr: function(pageNumber) {
        this.attr("pageIndex", Number(pageNumber) - 1);
    }, 
    _getPageNumberAttr: function() {
        return this.attr("pageIndex") + 1;
    }, 
    _setPageIndexAttr: function(pageIndex) {
        var oldIndex = this.attr("pageIndex");
        pageIndex = Number(pageIndex);
        if (pageIndex === oldIndex)
            return;
        if (this._started) {
            this.stopRefreshing();
            this.deleteItems();
        }
        this.pageIndex = pageIndex;
        if (this._started) {
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }
        console.log("Page index updated (new, old):", pageIndex, oldIndex);
    },  
    _setPageSizeAttr: function(pageSize) {
        var oldSize = this.attr("pageSize");
        pageSize = Number(pageSize);
        if (pageSize === oldSize)
            return;
        if (this._started) {
            this.stopRefreshing();
            this.deleteItems();
        }
        this.pageSize = pageSize;
        this._updatePageCount();
        if (this._started) {
        	this.attr("updatesOnly", false);
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }
        console.log("Page size updated (new, old):", pageSize, oldSize);
    }, 
    _setSortAttributeAttr: function(attribute) {
        var oldAttribute = this.attr("sortField");
        if (oldAttribute == attribute)
            return;
        if (this._started) {
            this.stopRefreshing();
            this.deleteItems();
        }
        this.sortField = attribute;
        if (this._started) {
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }
        var message = "Sort descending change (new, old):";
        console.log(message, attribute, oldAttribute);
    }, 
    _setSortDescendingAttr: function(isDescending) {
        var oldDescending = this.attr("sortDescending");
        if (oldDescending == isDescending)
            return;
        if (this._started) {
            this.stopRefreshing();
            this.deleteItems();
        }
        this.sortDescending = isDescending;
        if (this._started) {
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }
        var message = "Sort descending change (new, old):";
        console.log(message, isDescending, oldDescending);
    }, 
    _setQueryParamsAttr: function(query) {
        var oldQuery = this.attr("queryParams");
        if (this._started) {
            this.stopRefreshing();
            this.deleteItems();
        }
        this.queryParams = query;
        if (this._started) {
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }
        console.log("Query params changed (new, old):", query, oldQuery);
    }, 
    _updatePageCount: function() {
        var pageSize = this.attr("pageSize");
        var eventCount = this.attr("eventCount");
        var pageCount = Math.max(Math.ceil(eventCount / pageSize), 1);
        this.attr("pageCount", pageCount);
    }, 
    _setPageCountAttr: function(pageCount) {
        this.pageCount = pageCount;
        this.display.pagination.attr("pageCount", pageCount);
    }, 
    _setEventCountAttr: function(eventCount) {
        var oldCount = this.attr("eventCount");
        eventCount = Number(eventCount);
        if (eventCount === oldCount)
            return;
        this.eventCount = eventCount;
        this._updatePageCount();
    }, 
    _setupSortHeaders: function() {
        if (true)
            return;
        this.sortHeaders = dojo.query(".sortHeader", this.eventsTable);
        this.sortIcons = this.sortHeaders.query(".sortIcon");
        this.sortHeaders.onclick(dojo.hitch(this, function(evt) {
            var header = evt.target;
            var sortIcon = dojo.query(".sortIcon", header)[0];
            var sortField = dojo.attr(header, "abbr").toLowerCase();
            var descending = false;
            if (dojo.hasClass(sortIcon, "sortAscending"))
                descending = true;
            this.sortIcons.removeClass("sortAscending");
            this.sortIcons.removeClass("sortDescending");
            this.sortIcons.addClass("sortNone");
            dojo.removeClass(sortIcon, "sortNone");
            if (descending)
                dojo.addClass(sortIcon, "sortDescending");
            else
                dojo.addClass(sortIcon, "sortAscending");
            this.display.attr("sortField", sortField);
            this.display.attr("descending", descending);
        }));
    }, 
    acknowledgeSelected: function() {
        this.display.selectAllRows.attr("readOnly", true);
        var selected = this.display.getSelected();
        var uncheckAll = dojo.hitch(this, function() {
            this.display.selectAllRows.attr("readOnly", false);
            this.display.selectAllRows.attr("checked", false);
        }); 
        if (selected.length) {
            var guids = selected.map("return item.attr('guid');");
            selected.forEach("item.disableActions();");
            var deferred = this.acknowledgeEvents(guids);
            deferred.addBoth(function(response) {
                selected.forEach(function(item, index) {
                    item.attr("selected", false);
                    item.enableActions();
                });
                uncheckAll();
            });
        } else {
            uncheckAll();
        }
    }, 
    acknowledgeEvents: function(guids) {
        this.stopRefreshing();
        var deferred = dojo.xhrPost({ 
            url: "/syndication", 
            content: {
                guid: guids, 
                type: "none", 
                command: "acknowledge"
            }
        });
        deferred.addCallback(dojo.hitch(this, function(response) {
            console.log("Successfully acknowledged events:", guids, response);
            return response;
        }));
        deferred.addErrback(dojo.hitch(this, function(response) {
            console.log("Failed to acknowledge events:", guids, response);
            utils.display.failure("Failed to acknowledge events", response);
        }));
        deferred.addBoth(dojo.hitch(this, function(response) {
            if (this.attr("autoRefresh"))
                this.startRefreshing();
            else
                this.refresh();
        }));
        return deferred;
    }
});

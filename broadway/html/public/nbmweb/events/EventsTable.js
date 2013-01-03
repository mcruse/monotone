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
dojo.provide("nbmweb.events.EventsTable");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit._Container");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.Select");
dojo.require("dijit.form.CheckBox");
dojo.require("nbmweb.events.AlarmRow");
dojo.require("nbmweb.events.TablePager");

dojo.declare("nbmweb.events.EventsTable", 
             [dijit._Widget, dijit._Templated, dijit._Container], {
    debug: 0, 
    query: null, 
    store: null, 
    widgets: null, 
    rowCount: 0,
    rowsPerPage: 15, 
    pageCount: 1, 
    pageIndex: 0,
    pageNumber: 1, 
    queryOptions: null, 
    sortField: "created", 
    sortDescending: true, 
    templateString: "", 
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb.events", 
                                 "templates/EventsTable.html"),
    constructor: function(args, srcNodeRef) {
        console.log("Created event table.");
        this.items = new Object();
        this.widgets = new Object();
    }, 
    startup: function() {
        var result = this.inherited(arguments);
        this.setupChildren();
        if (this.store)
            this.refresh(true);
        return result;
    }, 
    setupChildren: function() {
        var pageSize = this.attr("rowsPerPage");
        var childIndex = this.getChildren().length;
        while (childIndex < pageSize)
            this.addChild(new nbmweb.events.AlarmRow({}), childIndex++);
        this.getChildren().slice(pageSize).forEach(function(item, index) {
            this.deleteRow(pageSize);
            this.removeChild(item);
            item.destroyRecursive();
        }, this);
    }, 
    getChildAt: function(index) {
        return this.getChildren()[index];
    }, 
    addItem: function(item) {
        var itemId = this.store.getIdentity(item);
        var itemRecord = this._getItemRecord(item);
        var itemIndex = this.store.getValue(item, "index");
        var children = this.getChildren();
        var rowWidget = children[children.length - 1];
        var oldId = rowWidget.attr("guid");
        if (oldId)
            delete(this.widgets[oldId]);
        else
            this.rowCount += 1;
        rowWidget.attr(itemRecord);
        this.widgets[itemId] = rowWidget;
        this.addChild(rowWidget, itemIndex);
    }, 
    removeItem: function(item) {
        var itemId = this.store.getIdentity(item);
        var widget = this.widgets[itemId];
        if (widget) {
            if (widget.attr("guid") == itemId) {
                widget.clear();
                this.addChild(widget, --this.rowCount);
            } else {
                console.log("removeItem() ignoring:", item);
            }
            delete(this.widgets[itemId]);
        }
    }, 
    addChild: function(widget, index) {
        if (this.debug > 1)
            console.log("addChild()", widget, index);
        var result = this.inherited(arguments);
        this.updateChildren();
        return result;
    }, 
    removeChild: function(child) {
        if (this.debug > 1)
            console.log("removeChild()", child);
        var result = this.inherited(arguments);
        this.updateChildren();
        return result;
    }, 
    deleteRow: function(/* indexes var-args */) {
        var children = this.getChildren();
        if (arguments.length)
            children = children.at.apply(children, arguments);
        children.forEach(function(item, index) {
            console.log("deleteRow() removing:", item, index);
            guid = item.attr("guid");
            if (guid) {
                delete(this.widgets[guid]);
                this.rowCount--;
            }
            item.clear();
            item.attr("disabled", true);
            this.addChild(item);
        }, this);
    },  
    refresh: function(firstFetch) {
        var kwArgs = dojo.mixin({
            scope: this, 
            onBegin: this._onRefreshBegin, 
            onItem: this._onCreateItemRow, 
            onComplete: this._onRefreshComplete
        }, this._getFetchParams());
        this.store.fetch(kwArgs);
        console.log("Store fetch initiated:", kwArgs);
    }, 
    attachStoreNotifications: function() {
        var connect = dojo.hitch(dojo, "connect", this.store);
        if (!this._onNewConn)
            this._onNewConn = connect("onNew", this, "_onNewItem");
        if (!this._onSetConn)
            this._onSetConn = connect("onSet", this, "_onSetItemValue");
        if (!this._onDeleteConn)
            this._onDeleteConn = connect("onDelete", this, "_onDeleteItem");
        return;
    }, 
    detachStoreNotifications: function() {
        if (this._onNewConn)
            dojo.disconnect(this._onNewConn);
        this._onNewConn = null; 
        if (this._onSetConn)
            dojo.disconnect(this._onSetConn);
        this._onSetConn = null; 
        if (this._onDeleteConn)
            dojo.disconnect(this._onDeleteConn);
        this._onDeleteConn = null;
    },  
    _setStoreAttr: function(store) {
        console.log(this.attr("id"), "setting store:", store);
        var firstStore = !this.store;
        if (!firstStore) {
            this.detachStoreNotifications();
            this.deleteRow();
        }
        this.store = store;
        if (store && this._started)
            this.refresh(firstStore);
        return;
    }, 
    _onRefreshBegin: function(size, request) {
        console.log("_onRefreshBegin()", size, request);
        this.detachStoreNotifications();
        this.deleteRow();
    }, 
    _onCreateItemRow: function(item, request) {
        console.log("_onCreateItemRow()", item, request);
        this._onNewItem(item, null);
    }, 
    _onRefreshComplete: function(nullItems, request) {
        console.log("_onRefreshComplete", nullItems, request);
        this.attachStoreNotifications();
    }, 
    _getFetchParams: function() {
        return {};
    }, 
    _getItemRecord: function(item) {
        var record = {
            guid: "", 
            name: "",
            state: "", 
            origin: "",
            created: "", 
            history: [], 
            priority: "", 
            categories: [], 
            acknowledged: false 
        };
        if (item) {
            dojo.mixin(record, {
                guid: this.store.getIdentity(item), 
                name: this.store.getValue(item, "name"),
                state: this.store.getValue(item, "state"), 
                origin: this.store.getValue(item, "origin"),
                created: this.store.getValue(item, "created"), 
                history: this.store.getValues(item, "history"), 
                priority: this.store.getValue(item, "priority"), 
                categories: this.store.getValues(item, "categories"), 
                acknowledged: this.store.getValue(item, "acknowledged") 
            });
        }
        return record;
    }, 
    _onNewItem: function(item, parentInfo) {
        if (this.debug > 1)
            console.log("_onNewItem()", item);
        this.addItem(item);
    }, 
    _onDeleteItem: function(item) {
        if (this.debug > 1)
            console.log("_onDeleteItem()", item);
        this.removeItem(item);
    }, 
    _onSetItemValue: function(item, attr, oldValue, newValue) {
        var itemId = this.store.getIdentity(item);
        var widget = this.widgets[itemId];
        if (widget) {
            if (dojo.isArray(newValue) && newValue.length == 1)
                newValue = newValue[0];
            if (attr == "index") {
                var oldRowIndex = this.getIndexOfChild(widget);
                if (oldRowIndex == newValue) {
                    if (this.debug > 1)
                        console.log("New index matches row index.");
                } else {
                    if (oldRowIndex > -1)
                        this.removeChild(widget);
                    this.addChild(widget, newValue);
                    console.log("Record index changed:", oldValue, newValue);
                }
            } else {
                widget.attr(attr, newValue);
            }
        }
        if (this.debug > 1)
            console.log("_onSetItemValue", attr, oldValue, newValue, widget);
    }, 
    updateChildren: function() {
        var odd = new dojo.NodeList();
        var even = new dojo.NodeList();
        this.getChildren().forEach(function(item, index) {
            if (index % 2)
                odd.push(item.domNode);
            else
                even.push(item.domNode);            
        });
        odd.removeClass("even").addClass("odd");
        even.removeClass("odd").addClass("even");
    }, 
    getSelected: function() {
        return this.getChildren().filter(function(item, index) {
            return item.attr("selected");
        });
    }, 
    toggleSelectAll: function() {
        var selected = this.selectAllRows.attr("checked");
        this.getChildren().forEach(function(item, index) {
            item.attr("selected", selected);
        });
    }, 
    toggleSort: function(evt) {
        var sortIcon = dojo.query(".sortIcon", evt.target);
        var descending = dojo.hasClass(sortIcon[0], "sortAscending");
        var icons = dojo.query(".sortIcon", this.tableHeaderRowNode);
        var sortAttribute = dojo.attr(evt.target, "abbr");
        icons.removeClass("sortAscending");
        icons.removeClass("sortDescending");
        icons.addClass("sortNone");
        if (descending)
            sortIcon.addClass("sortDescending");
        else
            sortIcon.addClass("sortAscending");
        this.onSortChanged(sortAttribute, descending)
        sortIcon.removeClass("sortNone");
    }, 
    onSortChanged: function(attribute, descending) {
        console.log(this.attr("id"), "sort changed:", attribute, descending);
    }, 
    onPageChanged: function(newNumber, oldNumber) {
        console.log(this.attr("id"), "page changed:", newNumber, oldNumber);
    }, 
    onRowsPerPageChanged: function(rowsPerPage, oldRowsPerPage) {
        console.log("Rows-per-page (new, old):", rowsPerPage, oldRowsPerPage);
    }, 
    _onSelectRowsPerPage: function() {
        var rowsPerPage = Number(this.selectRowsPerPage.attr("value"));
        var oldRowsPerPage = this.attr("rowsPerPage");
        this.attr("rowsPerPage", rowsPerPage);
        if (rowsPerPage != oldRowsPerPage) {
            this.setupChildren();
            this.onRowsPerPageChanged(rowsPerPage, oldRowsPerPage);
        }
    }
});
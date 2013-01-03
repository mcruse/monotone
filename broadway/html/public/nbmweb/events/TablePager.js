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
dojo.provide("nbmweb.events.TablePager");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.form.Button");

dojo.declare("nbmweb.events.TablePager", [dijit._Widget, dijit._Templated], {
    pageIndex: 0, 
    pageCount: 1, 
    disabled: false, 
    templateString: "", 
    widgetsInTemplate: true, 
    enabledFirstIcon: "/public/nbmweb/events/themes/First.gif", 
    disabledFirstIcon: "/public/nbmweb/events/themes/First-D.gif", 
    enabledPreviousIcon: "/public/nbmweb/events/themes/Previous.gif", 
    disabledPreviousIcon: "/public/nbmweb/events/themes/Previous-D.gif", 
    enabledNextIcon: "/public/nbmweb/events/themes/Next.gif", 
    disabledNextIcon: "/public/nbmweb/events/themes/Next-D.gif", 
    enabledLastIcon: "/public/nbmweb/events/themes/Last.gif", 
    disabledLastIcon: "/public/nbmweb/events/themes/Last-D.gif", 
    templatePath: dojo.moduleUrl("nbmweb.events", 
                                 "templates/TablePager.html"),
    constructor: function(args, domNode) {
        console.log(this.declaredClass, "constructor()", this, args, domNode);
    }, 
    startup: function() {
        console.log(this.attr("id"), "startup()", this);
        this.inherited(arguments);
        this.updatePagination();
    }, 
    getFirstPage: function() {
        return this.getFirstPageIndex() + 1;
    }, 
    getLastPage: function() { 
        return this.getLastPageIndex() + 1;
    }, 
    getNextPage: function() {
        return this.getNextPageIndex() + 1;
    }, 
    getPreviousPage: function() {
        return this.getPreviousPageIndex() + 1;
    }, 
    selectPage: function(pageNumber) {
        this.attr("pageNumber", pageNumber);
    }, 
    selectNextPage: function() {
        this.selectPage(this.getNextPage());
    }, 
    selectPreviousPage: function() {
        this.selectPage(this.getPreviousPage());
    }, 
    selectFirstPage: function() {
        this.selectPage(this.getFirstPage());
    }, 
    selectLastPage: function() {
        this.selectPage(this.getLastPage());
    }, 
    getNextPageIndex: function() {
        var nextPageIndex = this.attr("pageIndex") + 1;
        return Math.min(nextPageIndex, this.getLastPageIndex());
    }, 
    getPreviousPageIndex: function() {
        var previousPageIndex = this.attr("pageIndex") - 1;
        return Math.max(previousPageIndex, this.getFirstPageIndex());
    }, 
    getFirstPageIndex: function() {
        return 0;
    }, 
    getLastPageIndex: function() {
        return this.attr("pageCount") - 1;
    }, 
    onPageChanged: function(newPageNumber, oldPageNumber) {
        console.log("Page changed:", newPageNumber, oldPageNumber);
    }, 
    onPageIndexChanged: function(newPageIndex, oldPageIndex) {
        this.onPageChanged(newPageIndex + 1, oldPageIndex + 1);
    }, 
    _setDisabledAttr: function(disabled) {
        if (disabled) {
            this._disablePageForward();
            this._disablePageBackward();
        } else {
            if (this.attr("pageIndex") < this.getLastPageIndex())
                this._enablePageForward();
            if (this.attr("pageIndex") > this.getFirstPageIndex())
                this._enablePageBackward();
        }
        this.disabled = disabled;
    }, 
    _getPageNumberAttr: function() {
        return this.attr("pageIndex") + 1;
    }, 
    _setPageNumberAttr: function(pageNumber) {
        return this.attr("pageIndex", pageNumber - 1);
    }, 
    _setPageIndexAttr: function(pageIndex) {
        console.log("Setting page number: " + pageIndex, typeof(pageIndex));
        var oldPageIndex = this.attr("pageIndex");
        if (pageIndex == oldPageIndex)
            return;
        if (pageIndex > this.getLastPageIndex())
            throw new Error("Page number exceeds count: " + pageIndex);
        if (pageIndex < this.getFirstPageIndex())
            throw new Error("Page number doesn't exist: " + pageIndex);
        this.pageIndex = pageIndex;
        this.updatePagination();
        this.onPageIndexChanged(pageIndex, oldPageIndex);
    }, 
    _setPageCountAttr: function(pageCount) {
        console.log("Setting page count: ", pageCount);
        if (pageCount == this.pageCount)
            return;
        else if (pageCount < 1)
            throw new Error("Invalid page count: " + pageCount);
        this.pageCount = pageCount;
        this.updatePagination();
    }, 
    updatePagination: function() {
        var pageIndex = this.attr("pageIndex");
        var firstPageIndex = this.getFirstPageIndex();
        if (pageIndex <= firstPageIndex) {
            this._disablePageBackward();
            if (pageIndex != firstPageIndex)
                this.attr("pageIndex", firstPageIndex);
            pageIndex = firstPageIndex;
        } else {
            this._enablePageBackward();
        }
        var lastPageIndex = this.getLastPageIndex();
        if (pageIndex >= lastPageIndex) {
            this._disablePageForward();
            if (pageIndex != lastPageIndex)
                this.attr("pageIndex", lastPageIndex);
            pageIndex = lastPageIndex;
        } else {
            this._enablePageForward();
        }
        dojo.attr(this.pageCountNode, "innerHTML", this.attr("pageCount"));
        dojo.attr(this.pageNumberNode, "innerHTML", this.attr("pageNumber"));
    }, 
    _enablePageBackward: function() {
        var firstIcon = '<img src="' + this.enabledFirstIcon + '" />';
        var previousIcon = '<img src="' + this.enabledPreviousIcon + '" />';
        this.firstPageButton.attr("label", firstIcon);
        this.previousPageButton.attr("label", previousIcon); 
        this.firstPageButton.attr("disabled", false);
        this.previousPageButton.attr("disabled", false);
    }, 
    _disablePageBackward: function() {
        var firstIcon = '<img src="' + this.disabledFirstIcon + '" />';
        var previousIcon = '<img src="' + this.disabledPreviousIcon + '" />';
        this.firstPageButton.attr("label", firstIcon);
        this.previousPageButton.attr("label", previousIcon); 
        this.firstPageButton.attr("disabled", true);
        this.previousPageButton.attr("disabled", true);
    }, 
    _enablePageForward: function() {
        var nextIcon = '<img src="' + this.enabledNextIcon + '" />';
        var lastIcon = '<img src="' + this.enabledLastIcon + '" />';
        this.nextPageButton.attr("label", nextIcon);
        this.lastPageButton.attr("label", lastIcon); 
        this.nextPageButton.attr("disabled", false);
        this.lastPageButton.attr("disabled", false);
    }, 
    _disablePageForward: function() {
        var nextIcon = '<img src="' + this.disabledNextIcon + '" />';
        var lastIcon = '<img src="' + this.disabledLastIcon + '" />';
        this.nextPageButton.attr("label", nextIcon);
        this.lastPageButton.attr("label", lastIcon); 
        this.nextPageButton.attr("disabled", true);
        this.lastPageButton.attr("disabled", true);
    }
});
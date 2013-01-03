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
if (typeof(ui) == 'undefined') {
	var ui = {};
}
loader.add_module('/eventmanager/ui/table.js', ui, 'Table');
ui.factory = {};

ui.factory.table_from_elements = function(tableId, rowsId, paginationId) {
	var tableElement = document.getElementById(tableId);
	var rowsperpage = document.getElementById(rowsId);
	var pagination = document.getElementById(paginationId);    
	var pages = pagination.getElementsByTagName("ul")[0];
	var controls = pagination.getElementsByTagName("button");
	var previous = controls[0];
	var next = controls[1];
    var resultranges = pagination.getElementsByTagName("span");
    var firstresult = resultranges[0];
    var lastresult = resultranges[1];
    var totalresults = resultranges[2];
    // Initialize table and its rows-per-page value.
    var table = new ui.Table(tableElement);
    function update_rows_per_page() {
        var countindex = rowsperpage.selectedIndex || 0;
        var countoption = rowsperpage.options[countindex];
        table.set_rows_per_page(countoption.value);
    }
    update_rows_per_page();
    // Register pagination change handlers.
    dojo.connect(rowsperpage, 'onchange', update_rows_per_page);
    dojo.connect(previous,'onclick',dojo.hitch(table,"select_previous_page"));
    dojo.connect(next, 'onclick', dojo.hitch(table, "select_next_page"));
    
    function page_changed(newpage, oldpage) {
    	var pagelinks = pages.getElementsByTagName('li');
    	if (!isNaN(oldpage)) {
            var deselected = pagelinks[oldpage];
            dojo.removeClass(deselected, "selected");
    	}
    	var selected = pagelinks[newpage];
    	dojo.addClass(selected, "selected");
    }
    dojo.connect(table, 'page_changed', page_changed);
    
    function update_pagination_results() {
        var pagerange = table.get_current_page().range();
        var totalrange = table.tbody.rows.length;
        firstresult.innerHTML = String(pagerange[0] + 1);
        lastresult.innerHTML = String(pagerange[1]);
        totalresults.innerHTML = String(totalrange);
    }
    dojo.connect(table, 'page_changed', update_pagination_results);
    
    var handle = dojo.connect(table, "page_changed", function() {
        dojo.connect(table, 'row_added', update_pagination_results);
        dojo.connect(table, 'row_removed', update_pagination_results);
        dojo.disconnect(handle);
    });

    function setup_pages() {
        // Wipe out all links from page list.
        pages.innerHTML = "";
    	for (var i = 0; i < table.get_page_count(); i++) {
    	    var link = document.createElement("a");
    	    link.setAttribute("src", "/public/images/transparent.png");
    	    link.appendChild(document.createTextNode(String(i)));
    	    var item = document.createElement("li");
    	    item.appendChild(link);
    	    pages.appendChild(item);
    	}
    	page_changed(table.get_current_page().number);
    }
    dojo.connect(table, 'page_added', setup_pages);
    dojo.connect(table, 'page_removed', setup_pages);
    return table;
}

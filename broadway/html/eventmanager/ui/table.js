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
if (typeof(ui) == 'undefined') {
	var ui = {};
}

var display = {};
/*
 * TablePage objects represent a set of rows that are organized into a
 * "page" to be displayed.  The TablePage is inclusive of 'start_index', and
 * exclusive of 'end_index'.
**/
ui.TablePage = function(table, rowclasses, pagenumber, count) {
	this.table = table;
	this.thead = table.tHead;
	this.tbody = table.tBodies[0];
	this.classes = rowclasses;
	this.selected = 'selected';
	this.hidden = undefined;
	if (typeof(pagenumber) == 'string')
	    pagenumber = Number(pagenumber);
	this.number = pagenumber || 0;
	if (typeof(count) == 'string')
	    count = Number(count);
	this.count = count || NaN;
	this._start_index = (pagenumber * count) || 0;
}
ui.TablePage.prototype.start_index = function() {
	return this._start_index;
}
ui.TablePage.prototype.end_index = function() {
	var length = this.tbody.rows.length;
	if (isNaN(this.count)) {
		return length;
	} else
	    return Math.min(this.start_index() + this.count, length);
}
ui.TablePage.prototype.dead_index = function() {
	return Math.min(this.end_index(), this.tbody.rows.length);
}
ui.TablePage.prototype.get_rows = function() {
	var rows = new Array();
	for (var i = this.start_index(); i < this.dead_index(); i++) {
		rows.push(this.tbody.rows[i]);
	}
	return rows;
}
ui.TablePage.prototype.display = function() {
	for (var i=this.start_index(); i < this.dead_index(); i++) {
		var row = this.tbody.rows[i];
		this.display_row(row);
	}
	this.hidden = false;
}
ui.TablePage.prototype.hide = function() {
	for (var i=this.start_index(); i < this.dead_index(); i++) {
		var row = this.tbody.rows[i];
		this.hide_row(row);
		this.reset_row(row);
	}
	this.hidden = true;
}
ui.TablePage.prototype.display_row = function(row) {
    dojo.attr(row, "class", this.classes[row.sectionRowIndex % 2]);
	if (row.selected)
	    dojo.addClass(row, this.selected);
	else
	    row.selected = false;
	// Setting to empty string lets FF and IE use
	// the default display they like: table-row for FF,
	// and block for IE.
	dojo.style(row, "display", "");
}
ui.TablePage.prototype.hide_row = function(row) {
    dojo.style(row, "display", "none");
}
ui.TablePage.prototype.reset_row = function(row) {
	row = this.get_row(row);
	row.selected = false;
	var selectelements = row.getElementsByTagName('select');
	var inputelements = row.getElementsByTagName('input');
	if (selectelements.length) {
		selectelements[0].selectedIndex = null;
		selectelements[0].disabled = false;
	}
	if (inputelements.length) {
		inputelements[0].checked = false;
	}
}
ui.TablePage.prototype.range = function() {
	return [this.start_index(), this.end_index()];
}
ui.TablePage.prototype.is_full = function() {
	return this.tbody.rows.length > this.end_index();
}
ui.TablePage.prototype.is_empty = function() {
	return this.tbody.rows.length <= this.start_index();
}
ui.TablePage.prototype.contains = function(roworindex) {
	var index = this.get_row_index(roworindex);
	return (index >= this.start_index()) && (index < this.end_index());
}
ui.TablePage.prototype.select_row = function(rowindex) {
	if (this.hidden || !this.contains(rowindex))
	    return;
	var row = this.get_row(rowindex);
	var before = row.selected;
	row.selected = true;
	if (!before)
	    this.display_row(row);
}
ui.TablePage.prototype.deselect_row = function(rowindex) {
    if (this.hidden || !this.contains(rowindex))
        return;
	var row = this.get_row(rowindex);
	var before = row.selected;
	row.selected = false;
	if (before)
	    this.display_row(row);
}
ui.TablePage.prototype.get_selected_rows = function() {
	var selected = new Array();
	for (var i=this.start_index(); i < this.dead_index(); i++) {
		if (this.tbody.rows[i].selected) {
			selected.push(this.tbody.rows[i]);
		}
	}
	return selected;
}
ui.TablePage.prototype.get_row = function(roworindex) {
	if (typeof(roworindex) != 'number')
	    return roworindex;
	else
	    return this.tbody.rows[roworindex];
}
ui.TablePage.prototype.get_row_index = function(roworindex) {
    if (typeof(roworindex) == 'number')
        return roworindex;
    var row = this.get_row(roworindex);
    // Workaround Safari quirk where new rows have 0 section index.
    if (row.rowIndex == -1)
        return -1;
    else
        return row.sectionRowIndex;
}

ui.Table = function(table) {
    this.table = table;
	this.thead = table.tHead;
	this.tbody = table.tBodies[0];
    this.classes = ["light", "dark"];
    this.pages = [];
    this.page_index = 0;
    this.configured = false;
    this.sort_managers = new Array();
    this.row_comparison = undefined;
    this.rows_per_page = undefined;
    this.first_load_complete = false;

    this.configure = function() {
    	if (!this.configured)
    	    this.setup_sorting();
    	this.configured = true;
    }

    this.set_rows_per_page = function(count) {
    	if (count == this.rows_per_page)
    	    return;
    	this.select_page(0);
		this.rows_per_page = count;
		this.update_pagination();
		this.select_page(0);
    }

    this.get_page_count = function() {
    	return this.pages.length;
    }

    this.get_page = function(number) {
    	return this.pages[Number(number)];
    }

    this.get_current_page_number = function() {
        return this.page_index;
    }

    this.get_current_page = function() {
    	return this.get_page(this.page_index);
    }

    this.get_next_page = function() {
    	return this.get_page(this.page_index + 1);
    }

    this.get_previous_page = function() {
    	return this.get_page(this.page_index - 1);
    }

    this.get_first_page = function() {
    	return this.get_page(0);
    }

    this.get_last_page = function() {
    	return this.get_page(this.get_page_count() - 1);
    }

    this.get_rows_per_page = function() {
    	return this.rows_per_page;
	}

    this.select_page = function(number) {
    	if (!this.first_load_complete)
    	    return;
    	if (number < 0)
    	    number = 0;
    	else if (number > this.get_page_count() - 1)
    	    number = this.get_page_count() - 1;
    	var previous = this.page_index;
    	this.page_index = number;
    	this.update_display();
    	this.page_changed(number, previous);
    }

    this.select_next_page = function() {
    	this.select_page(this.page_index + 1);
    }

    this.select_previous_page = function() {
    	this.select_page(this.page_index - 1);
    }

    this.update_pagination = function() {
    	if (!this.first_load_complete)
    	    return;
    	this.pages = new Array();
    	while(this.add_page().is_full());
    	while(this.pages.length > 1 &&
    	      this.pages[this.pages.length -1].is_empty()) {
    		this.remove_page();
    	}
    	this.page_layout_updated(this.pages.length);
    }

    this.add_page = function() {
    	var page = new ui.TablePage(this.table, this.classes,
    								this.pages.length, this.rows_per_page);
    	this.pages.push(page);
    	this.page_added(page);
    	return page;
    }

    this.remove_page = function() {
    	var last = this.pages[this.pages.length - 1];
    	if (last == this.get_current_page()) {
    		this.select_previous_page();
   		}
    	this.pages.length = this.pages.length - 1;
    	this.page_removed(last);
    	return last;
    }
    // filter
    this.clear_display = function() {
		 //var oTableBody=document.getElementById("events-table-body");
		 //oTableBody.innerHTML = "";
		 var oTable=document.getElementById("events-table");
		 while(oTable.rows.length > 2)
		    oTable.deleteRow(oTable.rows.length-2);
    }
    // filter ends
    this.get_display_page = function() {
    	return this.pages[this.page_index];
    }

    this.update_display_page = function() {
    	this.get_display_page().display();
    }

    this.update_display = function() {
    	if (!this.pages.length)
    	    return;
    	var current = this.get_current_page_number();
    	for (var i=0; i < this.pages.length; i++) {
    		if (i == current)
    		    continue;
    		this.pages[i].hide();
    	}
    	this.update_display_page();
    }

    this.add_row = function(eventobj) {
    	if (!this.configured)
    	    this.configure();
    	if (this.pages.length > 0 &&
    	    this.pages[this.pages.length - 1].is_full())
    		this.add_page();
    	var row = events.display.create_event_row(eventobj);
    	row.style.display = 'none';
    	this.update_row(eventobj, row);
    	this.position_row(row);
    	this.row_added(row);
    }

    this.update_row = function(eventobj, newrow) {
    	var row = newrow || document.getElementById(eventobj.GUID);
    	events.display.update_event_row(eventobj, row);
    	if (!newrow) {
    		this.reposition_row(row);
    		this.row_updated(row);
    	}
    }

    this.deprecated_update_row = function(event, newrow) {
    	var row = newrow || document.getElementById(event.GUID);
    	for (var i = 0; i < row.childNodes.length; i++) {
    		var cell = row.childNodes[i];
    		if (!((cell.nodeName.toUpperCase() == 'TD') ||
    			  (cell.nodeName.toUpperCase() == 'TH')))
    			continue;
    		if ((cell.className in event) &&
    			(cell.innerHTML != event[cell.className])) {
    			cell.innerHTML = event[cell.className];
    		}
    	}
    	row.getElementsByTagName('select')[0].selectedIndex = null;
    	if (!newrow) {
    		this.reposition_row(row);
    		this.row_updated(row);
    	}
    }

    this.remove_row =  function(event) {
    	var row = document.getElementById(event.GUID);
    	var display = this.get_display_page();
    	var refresh = display.contains(row) || display.is_full();
    	row.parentNode.removeChild(row);
    	if (refresh)
    	    this.update_display_page();
    	if (this.pages.length > 1 &&
    	    this.pages[this.pages.length - 1].is_empty())
    		this.remove_page();
    	this.row_removed(row);
    }

    this.setup_sorting = function() {
    	var header = this.thead.rows[0];
    	var images = header.getElementsByTagName('img');
    	for (var i = 0; i < images.length; i++) {
    		var image = images[i];
    		var index = image.id.indexOf('sort');
    		if (index == -1)
    		    continue;
			var name = image.id.slice(0, index);
			var manager = new SortManager(name, image.parentNode.cellIndex,
			                              image, this.sort_by, name=="time");
			this.sort_managers.push(manager);
    	}
    }

    this.refresh_display = function() {
    	if (this.first_load_complete)
    	    return;
    	else
    	    this.first_load_complete = true;
    	this.configure()
    	this.sort_by();
    	this.update_pagination();
    	this.select_page(0);
    }

    function sort_by(manager, reverse) {
    	if (!manager) {
	    	var manager = this.sort_managers[this.sort_managers.length - 1];
	    	return manager.default_sort();
    	}
    	var name = manager.name;
    	var index = manager.index;
    	for (var i = 0; i < this.sort_managers.length; i++) {
    		if (this.sort_managers[i] !== manager) {
    			this.sort_managers[i].clear();
    		}
    	}
    	var rows = new Array();
    	for (var i = 0; i < this.tbody.rows.length; i++) {
    		rows.push(this.tbody.rows[i]);
    	}
    	var boundcompare = function(a, b) {
    		var params = [a, b];
    		if (reverse)
    		    params = [b, a];
    		return compare(get_value(params[0], index), get_value(params[1], index));
		}
		this.row_comparison = boundcompare;
		rows.sort(boundcompare);
		this.arrange_node_children(rows);
    }
    this.sort_by = tools.oo.bound_method(this, sort_by);

    this.find_row_index = function(row) {
        var index;
        // Safari uses 0 for section index of new rows.
        if (row.rowIndex == -1)
            index = -1;
        else
            index = row.sectionIndex;
    	if (this.row_comparison) {
    		if (index >= 0) {
    		    // Index > -1 means row exists.
    			// Checks to see if existing rows may stay in same location.
    			var compare_previous, compare_next;
    			var previous = index - 1;
    			var next = index + 1;
				if (previous >= 0) {
				    var previousrow = this.tbody.rows[previous];
					compare_previous = this.row_comparison(row, previousrow);
				} else
				    compare_previous = 0;
				if (next < this.tbody.rows.length) {
				    var nextrow = this.tbody.rows[next];
					compare_next = this.row_comparison(row, nextrow);
				} else
				    compare_next = 0;
				if (compare_previous >= 0 && compare_next <= 0)
				    return index;
    		}
	    	for (var i=0; i < this.tbody.rows.length; i++) {
	    		var compare = this.row_comparison(row, this.tbody.rows[i]);
	    		if (compare < 0)
	    		    return i;
	    	}
	    	return this.tbody.rows.length;
    	} else {
    	    console.warn("Finding row index before comparison available.");
    	    if (index >= 0)
    	        return index;
    	    else
    	        return this.tbody.rows.length;
    	}
    }

    this.position_row = function(row) {
        this.reposition_row(row, true);
    }

    this.reposition_row = function(row, isnew) {
    	var index = this.find_row_index(row);
    	// isnew flag compensates for Safari setting section
    	// index to 0 on newly created rows.
    	if (isnew || !this.tbody.rows.length ||
    	    (index != row.sectionRowIndex)) {
            var dummyrow = this.tbody.insertRow(index);
    		var display = this.get_display_page();
    		var contains_target = display && display.contains(index);
    		var contains_row = display && display.contains(row);
    		var full_update = contains_target && display.is_full();
			var page_update = contains_target || contains_row;

	    	if (!isnew)
	    	    row.parentNode.removeChild(row);
	    	row.style.display = 'none';
	    	dummyrow.parentNode.replaceChild(row,dummyrow);

	    	if (full_update)
	    	    this.update_display();
	    	else if (page_update)
	    	    this.update_display_page();
    	}
    }

    this.arrange_node_children = function(children) {
    	if (children.length > 0) {
	    	var parent = children[0].parentNode;
	    	for (var i = 0; i < children.length; i++) {
	    		parent.appendChild(children[i]);
	    	}
    	}
		this.update_display();
    }

    function compare(s1, s2) {
    	if (s1 < s2)
    	    return -1;
    	if (s1 > s2)
    	    return 1;
    	else
    	    return 0;
    }

	function date_value(datestr) {
		var date = new Date(datestr);
		return date.getTime();
	}

	function unknown_value(obj) {
	    return obj.valueOf();
	}

    var value_funcs = {'time': date_value};
    function get_value(row, index) {
		var cell;
    	if (row.cells.length > 0) {
    		cell = row.cells[index];
    	} else {
    		if (index == 0)
    		    cell = row.getElementsByTagName('th')[0];
    		else
    		    cell = row.getElementsByTagName('td')[index - 1];
    	}
    	var class_name = cell.className;
    	var cell_data = cell.innerHTML;
    	if (class_name in value_funcs) {
    		return value_funcs[class_name](cell_data);
    	} else
    	    return unknown_value(cell_data);
	}

    this.row_added = function(row) {}
    this.row_updated = function(row) {}
    this.row_removed = function(row) {}
    this.page_added = function(page) {}
    this.page_removed = function(page) {}
    this.page_changed = function(number, oldnumber) {}
    this.page_layout_updated = function(pagecount) {}
}

function SortManager(name, index, element, sort_handler, reverse_order) {
	reverse_order = reverse_order || false;
	this.name = name;
	this.index = index;
	this.element = element;
	this.sort_handler = sort_handler;
	this.original_class = this.element.className;
	this.ascending_class = 'down ' + this.original_class;
	this.descending_class = 'up ' + this.original_class;
	if (!reverse_order)
	    this.sortorder = ['original', 'ascending', 'descending'];
	else
	    this.sortorder = ['original', 'descending', 'ascending'];
	dojo.connect(element.parentNode, 'onclick', this, 'handle_click');
}
SortManager.prototype.set_ascending = function() {
	this.element.className = this.ascending_class;
	this.sort_handler(this, false);
}
SortManager.prototype.set_descending = function() {
	this.element.className = this.descending_class;
	this.sort_handler(this, true);
}
SortManager.prototype.clear = function() {
	this.element.className = this.original_class;
}
SortManager.prototype.reset = function () {
	this.element.className = this.original_class;
	this.sort_handler();
}
SortManager.prototype.default_sort = function() {
	this['set_' + this.sortorder[1]]();
}
SortManager.prototype.set_original = SortManager.prototype.reset;
SortManager.prototype.handle_click = function(target) {
	if (this.element.className == this[this.sortorder[0] + '_class']) {
		this['set_' + this.sortorder[1]]();
	} else if (this.element.className == this[this.sortorder[1] + '_class']) {
		this['set_' + this.sortorder[2]]();
	} else if (this.element.className == this[this.sortorder[2] + '_class']) {
		this['set_' + this.sortorder[0]]();
	}
}

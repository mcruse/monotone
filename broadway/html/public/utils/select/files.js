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
dojo.provide("utils.select.files");
utils.select.files.objWin = null;
utils.select.files.targetID = null;

utils.select.files.open = function(id) {
    if (arguments.length == 0)
        id = this.getAttribute('name');
    utils.select.files.targetID = id;
    var w = '600';
    var h = '600';
    var features = "height=1,width=1,resizeable,scrollbars";
    utils.select.files.objWin = window.open(
        "/webapi/fileSelector.html?savefunction=" + 
        "utils.select.files.handle_selected_file&" + 
        "selectfiles=html", "fileSelector", features);
    var height = window.screen.availHeight;
    var width = window.screen.availWidth;
    var left_point = parseInt(width/2) - parseInt(w/2);
    var top_point =  parseInt(height/2) - parseInt(h/2);
    utils.select.files.objWin.moveTo(left_point,top_point);
    utils.select.files.objWin.resizeTo(w,h);
    utils.select.files.objWin.focus();
}

utils.select.files.handle_selected_file = function() {
    var filesdoc = utils.select.files.objWin.document;
    var file_input = dojo.byId("file_name", filesdoc);
    var target_input = dojo.byId(utils.select.files.targetID);
    target_input.value = file_input.value;
    utils.select.files.objWin.close();
}

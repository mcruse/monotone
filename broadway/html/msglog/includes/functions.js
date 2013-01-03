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
function center(objWin,w,h){
    var height = window.screen.availHeight;
    var width = window.screen.availWidth;
    var left_point = parseInt(width/2) - parseInt(w/2);
    var top_point =  parseInt(height/2) - parseInt(h/2);
    objWin.moveTo(left_point,top_point);
    objWin.resizeTo(w,h);
    objWin.focus();
}

function create_window(name,url){
    var obj_win;
    var winHeight = 1;
    var winWidth = 1;
    var height = window.screen.availHeight;
    var width = window.screen.availWidth;
    var left_point = parseInt(width/2) - parseInt(winWidth/2);
    var top_point =  parseInt(height/2) - parseInt(winHeight/2);
    var parameters = '';
    parameters = '"height=' + winHeight.toString();
    parameters += ',width=' + winWidth.toString();
    parameters += '"';
    parameters = '"height=0,width=0";';
    var obj_win = window.open(url,name,"height=1,width=1");
    return obj_win;
}
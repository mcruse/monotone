/*
Copyright (C) 2008 2011 Cisco Systems

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
/* debug.js -- support for debug.html
 * $Name: mediator_3_1_2_branch $
 * $Id: debug.js 20101 2011-03-06 16:02:15Z bhagn $
 */
var debug_window = null;
var DEBUG_LOADED = false;
var messages = new Array();

function _get_query_string_args(){
  var args = new Object();
  var query_string = window.location.search.substring(1);
  var pairs = query_string.split("&");
  var name_value = null;
  var found = false;
  for(x=0;x<pairs.length;x++){
    if (pairs[x].indexOf('=') != -1){
      found = true;
      name_value = pairs[x].split('='); 
      args[name_value[0]] = decodeURIComponent(name_value[1]);
    } 
  }
  if (found == false){
    args = null;
  }
  return args;
}

function attrs(obj){ 
    for ( a in obj){
        msglog(a);
    }
}

function create_debug_window(){
    var name = 'debug';
    var obj_win;
    var winHeight = 200;
    var winWidth = 800;
    var height = window.screen.availHeight;
    var width = window.screen.availWidth;
    var left_point = parseInt(width/2) - parseInt(winWidth/2);
    var top_point =  parseInt(height/2) - parseInt(winHeight/2);
    var parameters = '"height=' + winHeight.toString();
    parameters += ',width=' + winWidth.toString();
    parameters += ',scrollbars=yes';
    parameters += ',resizeable=yes';
    parameters += ';"';
    var debug_path = '/webapi'; 
    //var debug_path = 'js'; 
    args = _get_query_string_args();
    if (args != null){  
      if (args['debug_path'] != null){
        debug_path = args['debug_path'];
      }
    }
    var obj_win = window.open(debug_path + '/' + 'debug.html',name,parameters);
    return obj_win;
}

var debug_window = create_debug_window();

function msglog(msg,t){
    if (typeof(msg )== 'string'){
        while (msg.indexOf('<') > 0 || msg.indexOf('>') > 0  ){
            msg = msg.replace('</','&lt/');
            msg = msg.replace('<','&lt;');
            msg = msg.replace('>','&gt;');
            
        }              
    }
   if(arguments.length >1){       
       log(msg,t)
   }
   else{
       log(msg); 
   }
 
}

function log(msg,t){

   if(arguments.length ==1){
       t = "info"   
   }
    if(DEBUG_LOADED){
        if (messages.length > 0){
             for(x=0;x< messages.length;x++){                 
                 debug_window.log(messages[x],t);
             }
             messages = [];
        }
        debug_window.log(msg,t);
    }
   else{
       messages[messages.length] = msg;
   }
}

function debug_window_watcher(){
   if(DEBUG_LOADED == false){
         setTimeout("debug_window_watcher()",500);
   }
   else{
      msglog("Debug window loaded");
   }

}

debug_window_watcher();

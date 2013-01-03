/*
Copyright (C) 2002 2010 2011 Cisco Systems

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
var START_DELAY=5000;
//default refresh rate
//var REFRESH_RATE=10000;
//var update = true;
var server_status = 'up';
var updating = false;

function get_last_seq_num(tbl){
    var seq_num;
    var cell;
    var row_index = 0;
    e = this.msglog.document.getElementById('sort_order');
    if (e.value.toLowerCase() == 'ascending'){
       row_index = tbl.rows.length -1;
    }    
    else{
       row_index = 1;
    }
    
    cell = tbl.rows[row_index].cells[0];
    var s = cell.getElementsByTagName('span')[0];
    seq_num = s.getAttribute('seq');
    return seq_num

}

function get_application(){
    var e;
    e = this.msglog.document.getElementById('application');
    return e.value
}

function get_type(){
    var e;
    e = this.msglog.document.getElementById('type');
    return e.value
}

function get_sort_order(){
    var e;
    e = this.msglog.document.getElementById('sort_order');
    return e.value
}

function handle_error(){
    if(this.control.document.getElementById("status")){
        this.control.document.getElementById("status").innerHTML = "Server is down....";
    }
    var e_status_td = this.control.document.getElementById("td_web_server_status");
    var e_status_text =  this.control.document.getElementById("web_server_status");
    server_status = 'down';
    e_status_td.setAttribute('bgcolor','#FF0000'); 
    e_status_text.innerHTML = 'WebServer Offline';
    done_updating();
}


// if loading of the image generates and error
// handle_error will get called and set server_status
function update_server_status(){
    if(this.control.document.getElementById("status")){
         this.control.document.getElementById("status").innerHTML = "Checking Server status...";
    }
    now = new Date();   
    var d = this.update_records.document;
    d.open();
    d.writeln('<html><body><script language="javascript">window.onError=null</script>')
    d.writeln('<img src="blank.png?now=' + now.getTime() + '" onError="this.handle_error()"></body></html>');
    d.close();   
}

function get_records_loop(){
   try{
       if (top.update && updating==false){
           start_update();
           update_server_status();
           setTimeout("update_location()",4000);      
       }
       setTimeout('get_records_loop()', top.REFRESH_RATE);
   }
   catch(e){ 
       alert(e);
       setTimeout('get_records_loop()', top.REFRESH_RATE);
   }
}

function start_update(){
    updating = true;
} 

function done_updating(){
    updating = false;
}

function update_location(){
     
      var e_status_td = this.control.document.getElementById("td_web_server_status");
      var e_status_text =  this.control.document.getElementById("web_server_status");
      var tbl = this.msglog.document.getElementById('msg_table');
      var seq_num = get_last_seq_num(tbl);
      var application = get_application();
      var type = get_type();
      var sort_order = get_sort_order();
      var location = '/msglog/get_records.html?seq_num=' + seq_num;
      location = location + '&application=' + application;
      location = location + '&type=' + type;
      location = location + '&sort_order=' + sort_order;
      if(server_status == 'up'){
          if(this.control.document.getElementById("status")){
             this.control.document.getElementById("status").innerHTML = "Getting new log entries..";
          }
          e_status_td.setAttribute('bgcolor','#999933');
          e_status_text.innerHTML = 'WebServer Online';
          this.update_records.location = location;
       }
       else{
          server_status = 'up';
      }
}


/*
Copyright (C) 2008 2010 2011 Cisco Systems

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
/*
Purpose: Widget superclass, all widgets are subclasses of this class.
$Name: mediator_3_1_2_branch $
$Id: widget.js 20250 2011-04-06 07:17:20Z bisarkar $
*/
function Widget(){
  this._name = '';
  this._z_index = '0';
  this.config_description ='';
}


Widget.prototype.configure = function (config){
  var x;  
  for (x in config){
    e = 'this._' + x + '="' + config[x] + '";';
    Widget_log("Widget.configure(), before eval of " + e);
    eval(e) ;
  }
}

Widget.prototype.after_config_table = function(){
  return;
}

Widget.prototype.create = function(){
  throw Error('Not Implemented');
}

Widget.prototype.init = function(element){
  throw Error('Not Implemented');
}


// called right before save to set up the init values
// of the widget.  The values that will get displayed before
// the widget get refreshed
Widget.prototype.set_init_values = function(element){}


Widget.prototype.configuration = function (){
  var x;
  var config = new Object();
  for (x in this){
    if (x.substring(0,1) == '_'){      
      Widget_log("Widget.configuration(), x=" + x);
      config[x.substring(1)] = eval('this.' + x);
      var searchStr = '"';
      var replaceStr = "&quot;";
      var re = new RegExp(searchStr, "gi");
      var tdata1 = config[x.substring(1)].replace(re, replaceStr);
      searchStr = "'";
      replaceStr = "&apos;";
      re = new RegExp(searchStr, "gi");
      config[x.substring(1)] = tdata1.replace(re, replaceStr);
    }
  }
  return config;
} 

Widget.prototype.get = function (){
  return this.element;
}

// Function: get_element
// Searches through the element types passed in 
// add looks for the "element" attribute in those
// if it finds one with the element attribute
// it returns the element if the element_name matches the 
// attribute value
// element - the element to search
// t - the type of elements to search through
// element_name - the name of the element to look for
function Widget_get_element(element,t,element_name){
  var index;
  var e = null;
  var elements = element.getElementsByTagName(t);
  for (index=0;index<elements.length;index++){
    if (elements[index].getAttribute('element') &&
        elements[index].getAttribute('element') == element_name){ 
      e = elements[index];
      break;
    }
  }
  return e
}

// Function: get_element
// Searches through the element types passed in 
// add looks for the "element" attribute in those
// if it finds one with the element attribute
// it returns the element if the element_name matches the 
// attribute value
// element - the element to search
// t - the type of elements to search through
// element_name - the name of the element to look for
Widget.prototype.get_element = function(element,t,element_name){
  var index;
  var e = null;
  var elements = element.getElementsByTagName(t);
  for (index=0;index<elements.length;index++){
    if (elements[index].getAttribute('element') &&
        elements[index].getAttribute('element') == element_name){ 
      e = elements[index];
      break;
    }
  }
  return e
}


Widget.prototype.add_row = function (table,name,value,readonly){
  var id;
  if (arguments.length <3){
    readonly = false;
  }
  var row_index = table.rows.length;
  table.insertRow(row_index);
  tr  =  table.rows[row_index];
  tr.insertCell(0);
  tr.cells[0].align = 'right';
  tr.cells[0].style.padding = '5';
  tr.cells[0].style.color = '#0000FF';
  tr.cells[0].innerHTML = name.replace(/_/g,' ') + ':';
  tr.insertCell(1);
  tr.cells[1].align = 'left';
  tr.cells[1].style.padding = '5';
  if (readonly){
    tr.cells[1].innerHTML = value;
  }
  else if (typeof(value) == 'function'){
    // @mevans - Use "this" as the object.
    c = value.apply(this,[]);
    tr.cells[1].appendChild(c);
   }
  else{
 
    input =  document.createElement('input');
    input.type = 'text';
    input.size = '75';    
    input.value =  value;
    id = this._name + '_' + name;
    input.id = id;
    if (eval('this.node_selector_' + name) != null){
      input.size = '60';
      var browse = document.createElement('img');
      browse.type ='image';
      browse.style.cursor = 'pointer';
      browse.src ='images/button_browse.gif';
      browse.value = 'Browse';
      browse.setAttribute('input_id',id); 
      // For IE
      if (document.all){
        browse.setAttribute('onclick',open_node_selector);
      }
      else{    
        browse.setAttribute('onclick','javascript:open_node_selector("' + id + '")');
      }
      tr.cells[1].appendChild (input);  
      tr.cells[1].appendChild (browse);      
    }
    else if (eval('this.sound_selector_' + name) != null){
      input.size = '60';
      var browse = document.createElement('img');
      browse.type ='image';
      browse.style.cursor = 'pointer';
      browse.src ='images/button_browse.gif';
      browse.value = 'Browse';
      browse.setAttribute('input_id',id); 
      // For IE
      if (document.all){
        browse.setAttribute('onclick',open_sound_selector);
      }
      else{    
        browse.setAttribute('onclick','javascript:open_sound_selector("' + id + '")');
      }
      tr.cells[1].appendChild (input);  
      tr.cells[1].appendChild (browse);      
    }
    else if (eval('this.image_selector_' + name) != null){
      input.size = '60';
      var browse = document.createElement('img');
      browse.type ='image';
      browse.style.cursor = 'pointer';
      browse.src ='images/button_browse.gif';
      browse.value = 'Browse';
      browse.setAttribute('input_id',id); 
      var query_string = '';
      var selector = this['image_selector_' + name];
  	  for (var attrname in selector) {
  	  	if (query_string.length > 0) 
  	  	  query_string += '&';
      	query_string += attrname + '=' + selector[attrname];
      }
      browse.setAttribute('querystring', query_string);
      // For IE
      if (document.all){
        browse.setAttribute('onclick',open_image_selector);
      }
      else{    
        browse.setAttribute('onclick','javascript:open_image_selector("' + id + '")');
      }
      tr.cells[1].appendChild (input);  
      tr.cells[1].appendChild (browse);      
    }
    else if (eval('this.html_selector_' + name) != null){
      input.size = '60';
      var browse = document.createElement('img');
      browse.type ='image';
      browse.style.cursor = 'pointer';
      browse.src ='images/button_browse.gif';
      browse.value = 'Browse';
      browse.setAttribute('input_id',id); 
      // For IE
      if (document.all){
        browse.setAttribute('onclick',open_html_selector);
      }
      else{    
        browse.setAttribute('onclick','javascript:open_html_selector("' + id + '")');
      }
      tr.cells[1].appendChild (input);  
      tr.cells[1].appendChild (browse);      
    }
    else if (eval('this.all_selector_' + name) != null){
      input.size = '60';
      var browse = document.createElement('img');
      browse.type ='image';
      browse.style.cursor = 'pointer';
      browse.src ='images/button_browse.gif';
      browse.value = 'Browse';
      browse.setAttribute('input_id',id); 
      // For IE
      if (document.all){
        browse.setAttribute('onclick',open_all_selector);
      }
      else{    
        browse.setAttribute('onclick','javascript:open_all_selector("' + id + '")');
      }
      tr.cells[1].appendChild (input);  
      tr.cells[1].appendChild (browse);      
    }
    else if (eval('this.color_selector_' + name) != null){
      input.size = '68';
      input.setAttribute('colorbox', name + '_colorbox');
      var colorbox = document.createElement('input');
      colorbox.setAttribute('id',name + '_colorbox');
      colorbox.setAttribute('name',name + '_colorbox');
      colorbox.style.fontSize = '0px';
      colorbox.style.width = '35px';
      colorbox.style.height = '35px';
      colorbox.style.margin = '0px 0px 0px 10px';
      colorbox.style.cursor = 'pointer';
      colorbox.style.backgroundColor = input.value;
      colorbox.style.border = '1px solid black';
      colorbox.setAttribute('input_id',id); 
      // For IE
      if (document.all){
        input.setAttribute('onchange',updateColorBox);
        colorbox.setAttribute('onclick',open_color_selector);
      }
      else{    
        input.setAttribute('onchange','javascript:updateColorBox("' + id + '")');
        colorbox.setAttribute('onclick','javascript:open_color_selector("' + id + '")');
      }
      tr.cells[1].appendChild (input);  
      tr.cells[1].appendChild (colorbox);      
    }
    else{
      tr.cells[1].appendChild (input);
    }
  }
  return table
}

Widget.prototype.get_desc = function (){
  var d =  document.createElement('div');
  d.setAttribute('width','100%'); 
  d.setAttribute('height','100%'); 
  d.align = 'left';
  d.style.padding = '5';
  d.style.backgroundColor = '#ffffff';
  d.innerHTML =this.config_description;
  return d
}


// name - name config element of the input widget that you want
// 
Widget.prototype.config_element = function(name){
  return document.getElementById(this._name + '_' + name)
}

Widget.prototype.config_table = function (){
  var d =  document.createElement('div');
  var t = document.createElement('table');
  t.setAttribute('border', '0');
  t.style.borderSpacing = '0';
  t.style.paddingTop = '10';
  t.style.paddingRight = '10';
  t.style.paddingBottom = '10';
  t.style.paddingLeft = '10';
  var config = this.configuration();
  var value = '';
  if(this.config_description != ''){
    d.appendChild(this.get_desc());
  }
  if (this._name.length >0 ){
     t =  this.add_row(t,'name',this._name,true);
  }
  var key;
  for ( key in config){
    if(key != 'name' ){
      if (eval('this.get_' + key + '_defaults')){        
        value = eval('this.get_' + key + '_defaults');     
      }  
      else{       
        value = config[key];              
      } 
      t = this.add_row(t,key,value);
    }
  }
  d.appendChild(t);
  return d
}

// Returns an attribute from a span - if the attribute is not
// found, attempt use default value from the constructor.  Provides
// reverse compatability for older widgets with new configuration options.
Widget.prototype.get_span_attr = function(span, attr_name){
    value = span.getAttribute(attr_name);
    if(value == null){
        // try to use constructor defaults
        value = this['_'+attr_name];
    }
    return value;
}

// used if there is a msglog
function Widget_log(m){
  try {
    if (console != undefined) {
      if (console['debug'] != undefined) {
	console.debug(m);
	return;
      }
    }
    if(parent.WebExpressEditor) {
      parent.msglog(m);
    }
    else if(window.opener && window.opener.msglog != null){
      window.opener.msglog(m);
    }
    else if(window.msglog){
      msglog(m);
    }
  }
  catch(ex) {}
}



var widget_loaded = true;

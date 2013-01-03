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

function SimpleNumber(){
  this.base = Widget;
  this.base();
  this._node = '';
  this._name = 'SimpleNumber';
  this._precision = '1';
  this._init_value = '??.?';
 }

SimpleNumber.prototype = new Widget;

SimpleNumber.prototype.init = function (element){   
  this._z_index =  element.getAttribute('zindex');    
  var s = element.getElementsByTagName('span')[0];
  this._node = s.getAttribute('node');
  this._precision = s.getAttribute('args'); 
  this._init_value = s.getAttribute('init_value');
}


SimpleNumber.prototype.init_element = function (){
  this.element = document.createElement('div');
  this.element.style.width = '50px';
  this.element.style.height = '15px';
  
  this.element.setAttribute('widget','SimpleNumber');
  this.element.setAttribute('zindex', this._z_index);
  var s = document.createElement('span');
  s.innerHTML = this._init_value;
  this.element.appendChild(s);
}

SimpleNumber.prototype.create = function (element){
  if (arguments.length ==1){
    this.element = element;
    this.init(element);
  }
  else{
    this.init_element();
  }
  this.element.childNodes[0].setAttribute('node',this._node);
  this.element.childNodes[0].setAttribute('init_value',this._init_value);
  this.element.childNodes[0].innerHTML = this._init_value;
  this.element.childNodes[0].setAttribute('display_function','precision');
  this.element.childNodes[0].setAttribute('args',this._precision);
}


function simple_number_factory(){
  return new SimpleNumber();
}

simple_number_loaded = true;

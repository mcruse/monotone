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
function SimpleText(){
  this.base = Widget;
  this.base();
  this._text = '';
  this._text_color = '';
  this._name = 'SimpleText';
  this._font_size = '';
 }

SimpleText.prototype = new Widget;

SimpleText.prototype.init_element = function (){
  this.element = null;
  this.element = document.createElement('div');
  this.element.setAttribute('ondblclick','delete_widget(this)'); 
  var s = document.createElement('span');
  s.innerHTML = '???';
  this.element.appendChild(s);
}


SimpleText.prototype.create = function (){
  this.init_element();
  this.element.childNodes[0].innerHTML = this._text;
  if(this._text_color != ''){
    this.element.childNodes[0].style.color = this._text_color;
  }
   if(this._font_size != ''){
    this.element.childNodes[0].style.fontSize = this._font_size;
  }  
}

function simple_text_factory(){
  return new SimpleText()
}

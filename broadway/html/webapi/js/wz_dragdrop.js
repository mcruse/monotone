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
/* Purpose: Drag and drop library.
$Name: mediator_3_1_2_branch $
$Id: wz_dragdrop.js 20101 2011-03-06 16:02:15Z bhagn $

/* This notice must be untouched at all times.

wz_dragdrop.js	v. 4.46
The latest version is available at
http://www.walterzorn.com
or http://www.devira.com
or http://www.walterzorn.de

Copyright (c) 2002-2003 Walter Zorn. All rights reserved.
Created 26. 8. 2002 by Walter Zorn <walter@kreuzotter.de>
Last modified: 10. 6. 2003

This DHTML & Drag&Drop Library adds Drag&Drop functionality
to the following types of html-elements:
- images, even if not positioned via layers,
  nor via stylesheets or any other kind of "hard-coding"
- relatively and absolutely positioned layers (DIV elements).
Moreover, it provides extended DHTML abilities.


This program is free software;
you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License
at http://www.gnu.org/copyleft/gpl.html for more details.
*/

// PATH TO THE TRANSPARENT 1*1 PX IMAGE (required by NS 4 as spacer)
var spacer = 'transparentpixel.gif';

//window.onerror = new Function('return true;');

// Optional commands on the html-page (g: may be used globally, i: individually)
var CLONE            = 'C10nE';        // i  img      clone image
var COPY             = 'C0pY';         // i  img      create copies
var DETACH_CHILDREN  = 'd37aCH';       // i  lyr      detach images
var HORIZONTAL       = 'H0r1Z';        // i  img,lyr  only horizontally draggable
var MAXHEIGHT        = 'm7x8I';        // i  img,lyr  maximum height limit, "
var MAXOFFBOTTOM     = 'm7xd0wN';      // i  img,lyr  downward offset limit
var MAXOFFLEFT       = 'm7x23Ft';      // i  img,lyr  leftward offset limit
var MAXOFFRIGHT      = 'm7x0Ff8';      // i  img,lyr  rightward offset limit
var MAXOFFTOP        = 'm7xu9';        // i  img,lyr  upward offset limit
var MAXWIDTH         = 'm7xW1';        // i  img,lyr  maximum width limit, use with resizable or scalable
var MINWIDTH         = 'm1nw1';        // i  img,lyr  minimum width limit, "
var MINHEIGHT        = 'm1n8I';        // i  img,lyr  minimum height limit, "
var NO_ALT           = 'no81T';        // gi img      disable alt and title attributes
var NO_SCROLL        = 'nO5cR';        // gi img,lyr  disable auto scroll functionality
var NO_DRAG          = 'N0d4Ag';       // i  img,lyr  disable draggability
var RESET_Z          = 'r35E7z';       // gi img,lyr  reset z-index when dropped
var RESIZABLE        = 'r5IZbl';       // gi img,lyr  resizable if <ctrl> or <shift> pressed
var SCALABLE         = 'SCLbl';        // gi img,lyr  scalable           "
var VERTICAL         = 'V3Rt1C';       // i  img,lyr  only vertically draggable

var dd_cursors = new Array(
	'c:move',
	'c:crosshair',
	'c:hand',
	'c:wait',
	'c:help',
	'c:n-resize',
	'c:ne-resize',
	'c:e-resize',
	'c:se-resize',
	'c:s-resize',
	'c:sw-resize',
	'c:w-resize',
	'c:nw-resize',
	'c:default'
);
for (var dd_i = dd_cursors.length; dd_i--;)
	eval('var CURSOR_' + (dd_cursors[dd_i].substring(2).toUpperCase().replace('-', '_')) + ' = "' + dd_cursors[dd_i] + '";');


function DDClass()
{
        if(!document.body) {alert("DDClass(), document.body not found for " + window.location);}
	this.n = navigator.userAgent.toLowerCase();
	this.db = (document.compatMode && document.compatMode.toLowerCase() != "backcompat")?
		document.documentElement
		: (document.body || null);
	this.op = (window.opera && document.getElementById);
	this.op6 = (this.op && !(this.db && this.db.innerHTML));
	if (this.op && !this.op6) document.onmousedown = new Function('e',
		'if (((e = e || window.event).target || e.srcElement).tagName == "IMAGE") return false;'
	);
	this.ie = this.n.indexOf("msie") != -1 && document.all && this.db && !this.op;
	this.iemac = this.ie && this.n.indexOf("mac")!=-1;
	this.ie4 = this.ie && !document.getElementById;
	this.n4 = (document.layers && typeof document.classes != "undefined");
	this.n6 = typeof window.getComputedStyle != "undefined" && typeof document.createRange != "undefined";
	this.kq = !this.n6 && this.n.indexOf("safar") >= 0 || this.n.indexOf("konq") >= 0;
	this.ce = document.captureEvents && document.releaseEvents;
	this.px = (this.n4 || this.op6)? '' : 'px';
}
var dd = new DDClass();

dd.Int = function(d_x, d_y)
{
	return isNaN(d_y = parseInt(d_x))? 0 : d_y;
};

dd.getWndW = function()
{
	return dd.Int(
		(dd.db && !dd.op && dd.db.clientWidth)? dd.db.clientWidth
		: (window.innerWidth || 770)
	);
};


dd.getWndH = function()
{
	return dd.Int(
		(dd.db && !dd.op && dd.db.clientHeight)? dd.db.clientHeight
		: (window.innerHeight || 500)
	);
};



dd.getScrollX = function()
{
	return dd.Int(window.pageXOffset || (dd.db? dd.db.scrollLeft : 0));
};



dd.getScrollY = function()
{
	return dd.Int(window.pageYOffset || (dd.db? dd.db.scrollTop : 0));
};



dd.getPageX = function(d_o)
{
	if (dd.n4 && d_o) return d_o.pageX || 0;
	var d_y = 0;
	while (d_o)
	{
		d_y += dd.Int(d_o.offsetLeft);
		d_o = d_o.offsetParent || null;
	}
	return d_y;
};



dd.getPageY = function(d_o)
{
	if (dd.n4 && d_o) return d_o.pageY || 0;
	var d_y = 0;
	while (d_o)
	{
		d_y += dd.Int(d_o.offsetTop);
		d_o = d_o.offsetParent || null;
	}
	return d_y;
};



dd.getCssX = function(d_o)
{
	if (dd.n4) return d_o.div? d_o.div.x : 0;
	if (dd.ie4) return d_o.div? d_o.css.pixelLeft : 0;
	var d_y = 0;
	if (d_o.div)
	{
		d_o.css.left = 0 + dd.px;
		d_y = d_o.x - dd.getPageX(d_o.div);
		d_o.css.left = d_y + dd.px;
	}
	return d_y;
};



dd.getCssY = function(d_o)
{
	if (dd.n4) return d_o.div? d_o.div.y : 0;
	if (dd.ie4) return d_o.div? d_o.css.pixelTop : 0;
	var d_y = 0;
	if (d_o.div)
	{
		d_o.css.top = 0 + dd.px;
		d_y = d_o.y - dd.getPageY(d_o.div);
		d_o.css.top = d_y + dd.px;
	}
	return d_y;
};



dd.getImgW = function(d_o)
{
	return d_o? dd.Int(d_o.width) : 0;
};



dd.getImgH = function(d_o)
{
	return d_o? dd.Int(d_o.height) : 0;
};



dd.getDivW = function(d_o)
{
	return dd.Int(
		dd.n4? (d_o.div? d_o.div.clip.width : 0)
		: d_o.div? (d_o.div.offsetWidth || d_o.css.pixelWidth || d_o.css.width || 0)
		: 0
	);
};



dd.getDivH = function(d_o)
{
	return dd.Int(
		dd.n4? (d_o.div? d_o.div.clip.height : 0)
		: d_o.div? (d_o.div.offsetHeight || d_o.css.pixelHeight || d_o.css.height || 0)
		: 0
	);
};



dd.getWH = function(d_o)
{
	d_o.w = dd.getDivW(d_o);
	d_o.h = dd.getDivH(d_o);
	if (d_o.css)
	{
		d_o.css.width = d_o.w + dd.px;
		d_o.css.height = d_o.h + dd.px;
		d_o.dw = dd.getDivW(d_o)-d_o.w;
		d_o.dh = dd.getDivH(d_o)-d_o.h;
		d_o.css.width = (d_o.w-d_o.dw) + dd.px;
		d_o.css.height = (d_o.h-d_o.dh) + dd.px;
	}
	else d_o.dw = d_o.dh = 0;
};



dd.getDiv = function(d_x, d_d)
{
	d_d = d_d || document;
	if (dd.n4)
	{
		if (d_d.layers[d_x]) return d_d.layers[d_x];
		for (var d_i = d_d.layers.length; d_i--;)
		{
			var d_y = dd.getDiv(d_x, d_d.layers[d_i].document);
			if (d_y) return d_y;
		}
	}
	if (dd.ie) return d_d.all[d_x] || null;
	if (d_d.getElementById) return d_d.getElementById(d_x) || null;
	return null;
};



dd.getImg = function(d_o, d_nm, d_xy, d_w)
{
	d_w = d_w || window;
	var d_img;
	if ((d_img = d_w.document.images[d_nm]) && d_img.name == d_nm)
	{
		if (d_xy)
		{
			if (dd.n4)
			{
				d_o.defx = d_img.x + dd.getPageX(d_w);
				d_o.defy = d_img.y + dd.getPageY(d_w);
			}
			else
			{
				d_o.defx = dd.getPageX(d_img);
				d_o.defy = dd.getPageY(d_img);
			}
		}
		return d_img;
	}
	if (dd.n4) for (var d_i = d_w.document.layers.length; d_i--;)
	{
		var d_y = dd.getImg(d_o, d_nm, d_xy, d_w.document.layers[d_i]);
		if (d_y) return d_y;
	}
	return null;
};



dd.getParent = function(d_o)
{
	if (dd.n4)
	{
		for (var d_p, d_i = dd.elements.length; d_i--;)
		{
			if (!((d_p = dd.elements[d_i]).is_image) && d_p.div && (d_p.div.document.layers[d_o.name] || d_p.div.document.images[d_o.imgname]))
				d_p.addChild(d_o, d_p.detach, 1);
		}
	}
	else
	{
		var d_p = d_o.is_image? dd.getImg(d_o, d_o.imgname) : (d_o.div || null);
		while (d_p && !!(d_p = d_p.offsetParent || d_p.parentNode || null))
		{
			if (d_p.ddObj)
			{
				d_p.ddObj.addChild(d_o, d_p.ddObj.detach, 1);
				break;
			}
		}
	}
};



dd.getCmd = function(d_o, d_cmd, d_cmdStr)
{
	var d_i = d_o.id.indexOf(d_cmd), d_j,
	d_y = (d_i >= 0)*1;
	if (d_y)
	{
		d_j = d_i+d_cmd.length;
		if (d_cmdStr) d_o.cmd += d_o.id.substring(d_i, d_j);
		d_o.id = d_o.id.substring(0, d_i) + d_o.id.substring(d_j);
	}
	return d_y;
};



dd.getCmdVal = function(d_o, d_cmd, d_cmdStr, int0)
{
	var d_i = d_o.id.indexOf(d_cmd), d_j,
	d_y = (d_o.id.indexOf(d_cmd) >= 0)? dd.Int(d_o.id.substring(d_o.id.indexOf(d_cmd)+d_cmd.length)) : int0? -1 : 0;
	if (!int0 && d_y || int0 && d_y >= 0)
	{
		d_j = d_i+d_cmd.length+d_y.toString().length;
		if (d_cmdStr) d_o.cmd += d_o.id.substring(d_i, d_j);
		d_o.id = d_o.id.substring(0, d_i) + d_o.id.substring(d_j);
	}
	return d_y;
};



dd.addElt = function(d_o, d_p)
{
	dd.elements[dd.elements.length] = dd.elements[d_o.name] = d_o;
	if (d_p) d_p.copies[d_p.copies.length] = d_o;
};



dd.mkWzDom = function()
{
	for (var d_i = dd.elements.length; d_i--;) dd.getParent(dd.elements[d_i]);
	for (d_i = dd.elements.length; d_i--;)
		if ((d_o = dd.elements[d_i]).children && !d_o.parent)
			for (var d_j = d_o.children.length; d_j--;)
				d_o.children[d_j].setZ(d_o.z+d_o.children[d_j].z, 1);
};



dd.initImg = function(d_o)
{
	d_o.nimg = (dd.n4 && d_o.div)? d_o.div.document.images[0] : (document.images[d_o.id+'NImG'] || null);
	if (!d_o.noalt && !dd.noalt && d_o.nimg && d_o.oimg)
	{
		d_o.nimg.alt = d_o.oimg.alt || '';
		if (d_o.oimg.title) d_o.nimg.title = d_o.oimg.title;
	}
};



dd.addProps = function(d_o)
{
	var d_i;
	if (!d_o.is_image)
	{
		if (dd.n6 && d_o.div)
		{
			d_o.defz = dd.Int((d_i = window.getComputedStyle(d_o.div, null)).getPropertyValue('z-index'));
			var d_c = d_i.getPropertyValue('background-color');
			if (d_c.indexOf('rgb') >= 0)
			{
				d_c = d_c.substring(0x4).split(',');
				d_o.bgColor = '#';
				for (var d_i = 0; d_i < d_c.length; d_i++) d_o.bgColor += parseInt(d_c[d_i]).toString(0x16);
			}
			else d_o.bgColor = d_c;
		}
		else if (d_o.div && d_o.div.currentStyle)
		{
			d_o.defz = dd.Int(d_o.div.currentStyle.zIndex);
			d_o.bgColor = d_o.div.currentStyle.backgroundColor;
		}
		else if (d_o.div)
		{
			d_o.defz = dd.Int((d_o.css || d_o.div).zIndex);
			d_o.bgColor = dd.n4? d_o.div.bgColor : (d_o.css.backgroundColor || d_o.css.background);
		}
		else d_o.defz = 0;
	}
	else
	{
		d_o.div = dd.getDiv(d_o.id);
		if (d_o.div && typeof d_o.div.style != "undefined") d_o.css = d_o.div.style;
		dd.initImg(d_o);
	}
	d_o.bgColor = d_o.bgColor || '';
	d_o.setZ(d_o.defz);
	d_o.cursor = d_o.cursor || dd.cursor || 'auto';
	d_o.setCursor(d_o.nodrag? 'auto' : d_o.cursor);
	d_o.visible = true;
};



dd.init = function()
{
	if (!(dd && (dd.n4 || dd.n6 || dd.ie || dd.op || dd.kq))) return;
	if (dd.op6) WINSZ(0x2);
	else if (dd.n6 || dd.ie || dd.op && !dd.op6 || dd.kq) dd.recalc(1);
	var d_drag = (document.onmousemove == DRAG),
	d_resize = (document.onmousemove == RESIZE);
	if (dd.loadFunc) dd.loadFunc();
	if (d_drag && document.onmousemove != DRAG) dd.setEvtHdl(1, DRAG);
	else if (d_resize && document.onmousemove != RESIZE) dd.setEvtHdl(1, RESIZE);
	if ((d_drag || d_resize) && document.onmouseup != DROP) dd.setEvtHdl(2, DROP);
	dd.setEvtHdl(0, PICK);
	if(dd.ie) dd.setEvtHdl(3, CONTEXT);
};



dd.setEvtHdl = function(d_typ, d_func)
{
	switch(d_typ) {
	  case 0:	
		if (document.onmousedown != d_func) dd.downFunc = document.onmousedown || null;
		document.onmousedown = d_func;
		break;
	  case 1:
		if (document.onmousemove != d_func) dd.moveFunc = document.onmousemove || null;
		document.onmousemove = d_func;
		break;
	  case 2:
		if (document.onmouseup != d_func) dd.upFunc = document.onmouseup || null;
		document.onmouseup = d_func;
		break;
	  case 3:
	  if (dd.ie) {
		if (document.oncontextmenu != d_func) dd.contextFunc = document.oncontextmenu || null;
		document.oncontextmenu = d_func;
	  } else {
	    document.addEventListener("contextmenu", d_func, true);
	  }
		break;
	}
	if (dd.ce)
	{
		//for NN4 & later
		//FIXTHIS: need to used W3C DOM event listner syntax here
		var d_e = (!d_typ)? Event.MOUSEDOWN : (d_typ == 1)? Event.MOUSEMOVE : Event.MOUSEUP;
		if (d_func) document.captureEvents(d_e);
		else document.releaseEvents(d_e);
	}
};



dd.evt = function(d_e)
{
	this.but = (this.e = d_e || window.event).which || this.e.button || 0;
	this.button = (this.e.type == 'mousedown')? this.but
		: (dd.e && dd.e.button)? dd.e.button
		: 0;
	this.type = this.e.type;
	this.src = this.e.target || this.e.srcElement || null;
	this.src.tag = (this.src.tagName || this.src).toString().toLowerCase();
	this.x = dd.Int(this.e.pageX || this.e.clientX || 0);
	this.y = dd.Int(this.e.pageY || this.e.clientY || 0);
	if (dd.ie || dd.kq)
	{
		this.x += dd.getScrollX() - ((dd.ie && !dd.iemac)? 1 : 0);
		this.y += dd.getScrollY() - ((dd.ie && !dd.iemac)? 1 : 0);
	}
	this.shiftKey = this.e.modifiers? (this.e.modifiers & Event.SHIFT_MASK)
		: (this.e.shiftKey || false);
	this.ctrlKey = this.e.modifiers? (this.e.modifiers & Event.CONTROL_MASK)
		: (this.e.ctrlKey || false);
};



dd.recalc = function(d_x)
{
	for (var d_o, d_i = dd.elements? dd.elements.length : 0; d_i--;)
	{
		if (!(d_o = dd.elements[d_i]).is_image && d_o.div)
		{
			dd.getWH(d_o);
			if (d_o.div.pos_rel)
			{
				var d_dx = dd.getPageX(d_o.div) - d_o.x, d_dy = dd.getPageY(d_o.div) - d_o.y;
				d_o.defx += d_dx;
				d_o.x += d_dx;
				d_o.defy += d_dy;
				d_o.y += d_dy;
				for (var d_p, d_j = d_o.children.length; d_j--;)
				{
					if (!(d_p = d_o.children[d_j]).detached && (d_o != d_p.defparent || !dd.getImg(d_p, d_p.imgname, 1)))
					{
						d_p.defx += d_dx;
						d_p.defy += d_dy;
						d_p.moveBy(d_dx, d_dy);
					}
				}
			}
		}
		else if (d_o.is_image && !dd.op6 && !dd.n4)
		{
			if (dd.n6 && d_x && !d_o.defw) d_o.resizeTo(d_o.defw = dd.getImgW(d_o.oimg), d_o.defh = dd.getImgH(d_o.oimg));
			var d_defx = d_o.defx, d_defy = d_o.defy;
			if (!(d_o.parent && d_o.parent != d_o.defparent) && (d_x || !d_o.detached || d_o.horizontal || d_o.vertical) && dd.getImg(d_o, d_o.imgname, 1))
				d_o.moveBy(d_o.defx-d_defx, d_o.defy-d_defy);
		}
	}
};



dd.n4RectVis = function(vis)
{
	for (var d_i = 0x4; d_i--;)
	{
		dd.rectI[d_i].visibility = dd.rectA[d_i].visibility = vis? 'show' : 'hide';
		if (vis) dd.rectI[d_i].zIndex = dd.rectA[d_i].zIndex = dd.z+0x2;
	}
};



dd.n4RectPos = function(d_o, d_x, d_y, d_w, d_h)
{
	d_o.x = d_x;
	d_o.y = d_y;
	d_o.clip.width = d_w;
	d_o.clip.height = d_h;
};



// NN4: draw img resize rectangle
dd.n4Rect = function(d_dx, d_dy)
{
	if (!dd.rectI)
	{
		dd.rectI = new Array();
		dd.rectA = new Array();
	}
	if (!dd.rectI[0])
	{
		for (var d_i = 0x4; d_i--;)
		{
			(dd.rectI[d_i] = new Layer(1)).bgColor = '#000000';
			(dd.rectA[d_i] = new Layer(1)).bgColor = '#ffffff';
		}
	}
	if (!dd.rectI[0].visibility || dd.rectI[0].visibility == 'hide') dd.n4RectVis(1);
	dd.obj.w = Math.max(dd.obj.w+d_dx, 1);
	dd.obj.h = Math.max(dd.obj.h+d_dy, 1);
	for (var d_i = 0x4; d_i--;)
	{
		dd.n4RectPos(dd.rectI[d_i], dd.obj.x + (!(d_i-1)? (dd.obj.w-1) : 0), dd.obj.y + (!(d_i-0x2)? (dd.obj.h-1) : 0), (d_i&1)? 1 : dd.obj.w, (d_i&1)? dd.obj.h : 1);
		dd.n4RectPos(dd.rectA[d_i], !(d_i-1)? dd.rectI[1].x+1 : (dd.obj.x-1), !(d_i-0x2)? dd.rectI[2].y+1 : (dd.obj.y-1), (d_i&1)? 1 : (dd.obj.w+0x2), (d_i&1)? dd.obj.h+0x2 : 1);
	}
};



dd.resizeBy = function(d_dx, d_dy)
{
	if (dd.n4 && dd.obj.is_image) dd.n4Rect(d_dx, d_dy);
	else dd.obj.resizeBy(d_dx, d_dy);
};



dd.setEmbedVis = function(d_vis)
{
	var d_o = new Array('iframe', 'applet', 'embed', 'object');
	for (var d_i = d_o.length; d_i--;)
	{
		var d_p = dd.ie? document.all.tags(d_o[d_i]) : document.getElementsByTagName? document.getElementsByTagName(d_o[d_i]) : null;
		if (d_p) for (var d_j = d_p.length; d_j--;)
		{
			var d_q = d_p[d_j];
			while (d_q.offsetParent || d_q.parentNode)
			{
				if ((d_q = d_q.parentNode || d_q.offsetParent || null) == dd.obj.div)
				{
					d_p[d_j].style.visibility = d_vis;
					break;
				}
			}
		}
	}
};



dd.maxOffX = function(d_x, d_y)
{
	return (
		(dd.obj.maxoffl >= 0 && (d_y = dd.obj.defx-dd.obj.x-dd.obj.maxoffl)-d_x > 0)? d_y
		: (dd.obj.maxoffr >= 0 && (d_y = dd.obj.defx-dd.obj.x+dd.obj.maxoffr)-d_x < 0)? d_y
		: d_x
	);
};



dd.maxOffY = function(d_x, d_y)
{
	return (
		(dd.obj.maxofft >= 0 && (d_y = dd.obj.defy-dd.obj.y-dd.obj.maxofft)-d_x > 0)? d_y
		: (dd.obj.maxoffb >= 0 && (d_y = dd.obj.defy-dd.obj.y+dd.obj.maxoffb)-d_x < 0)? d_y
		: d_x
	);
};



dd.inClientW = function(d_x, d_y)
{
	var d_sx = dd.getScrollX(),
	d_ww = dd.getWndW();
	return (
		((d_y = d_sx+0x2-dd.obj.x-dd.obj.w)-d_x > 0)? d_y
		: ((d_y = d_sx-0x2+d_ww-dd.obj.x)-d_x < 0)? d_y
		: d_x
	);
};



dd.inClientH = function(d_x, d_y)
{
	var d_sy = dd.getScrollY(),
	d_wh = dd.getWndH();
	return (
		((d_y = d_sy+0x2-dd.obj.y-dd.obj.h)-d_x > 0)? d_y
		: ((d_y = d_sy+d_wh-0x2-dd.obj.y)-d_x < 0)? d_y
		: d_x
	);
};



// The following two functions limit the size of the element when it is mouse-resized.
// Implemented 22.5.2003 by Gregor Lutolf <gregor@milou.ch>, modified by Walter Zorn
dd.limitW = function(d_dx, d_w)
{
	return (
		(dd.obj.minw-(d_w = dd.obj.w+d_dx) >= 0)? dd.obj.minw-dd.obj.w
		: (dd.obj.maxw >= 0 && dd.obj.maxw-d_w <= 0)? dd.obj.maxw-dd.obj.w
		: d_dx
	);
};



dd.limitH = function(d_dy, d_h)
{
	return (
		(dd.obj.minh-(d_h = dd.obj.h+d_dy) >= 0)? dd.obj.minh-dd.obj.h
		: (dd.obj.maxh >= 0 && dd.obj.maxh-d_h <= 0)? dd.obj.maxh-dd.obj.h
		: d_dy
	);
};



dd.reFalse = function()
{
	event.returnValue = false;
};





function DDObj(d_o, d_i)
{
	this.id = d_o;
	this.cmd = '';
	this.cpy_n = dd.getCmdVal(this, COPY);
	this.maxoffb = dd.getCmdVal(this, MAXOFFBOTTOM, 0, 1);
	this.maxoffl = dd.getCmdVal(this, MAXOFFLEFT, 0, 1);
	this.maxoffr = dd.getCmdVal(this, MAXOFFRIGHT, 0, 1);
	this.maxofft = dd.getCmdVal(this, MAXOFFTOP, 0, 1);

	for (var d_j = dd_cursors.length; d_j--;)
		if (dd.getCmd(this, dd_cursors[d_j], 1)) this.cursor = dd_cursors[d_j].substring(0x2);
	this.clone = dd.getCmd(this, CLONE, 1);
	this.detach = dd.getCmd(this, DETACH_CHILDREN);
	this.scalable = dd.getCmd(this, SCALABLE, 1);
	this.horizontal = dd.getCmd(this, HORIZONTAL);
	this.noalt = dd.getCmd(this, NO_ALT, 1);
	this.nodrag = dd.getCmd(this, NO_DRAG);
	this.noscroll = dd.getCmd(this, NO_SCROLL, 1);
	this.resizable = dd.getCmd(this, RESIZABLE, 1);
	this.re_z = dd.getCmd(this, RESET_Z, 1);
	this.vertical = dd.getCmd(this, VERTICAL);
	this.maxw = dd.getCmdVal(this, MAXWIDTH, 1, 1);
	this.minw = Math.abs(dd.getCmdVal(this, MINWIDTH, 1, 1));
	this.maxh = dd.getCmdVal(this, MAXHEIGHT, 1, 1);
	this.minh = Math.abs(dd.getCmdVal(this, MINHEIGHT, 1, 1));

	this.name = this.id + (d_i || '');
	this.oimg = dd.getImg(this, this.id, 1);
	this.is_image = !!this.oimg;
	this.copies = new Array();
	this.children = new Array();

	if (this.oimg)
	{
		this.imgname = this.id;
		this.id += 'div' + (d_i || '');
		this.w = dd.getImgW(this.oimg);
		this.h = dd.getImgH(this.oimg);
		this.dw = this.dh = 0;
		(this.cach = new Image()).src = this.defsrc = this.src = this.oimg.src;
		this.htm = '<img name="' + this.id + 'NImG"'+
			' src="' + this.defsrc + '" '+
			'width="' + this.w + '" height="' + this.h + '">';
		this.t_htm = '<div id="' + this.id +
			'" style="position:absolute;'+
			'left:' + (this.cssx = this.x = this.defx) + 'px;'+
			'top:' + (this.cssy = this.y = this.defy) + 'px;'+
			'width:' + this.w + 'px;'+
			'height:' + this.h + 'px;">'+
			this.htm + '<\/div>';
	}
	else
	{
		if (!!(this.div = dd.getDiv(this.id)) && typeof this.div.style != "undefined") this.css = this.div.style;
		dd.getWH(this);
		if (this.div)
		{
			this.div.ddObj = this;
			this.div.pos_rel = ((this.div.parentNode? this.div.parentNode.tagName : this.div.parentElement? this.div.parentElement.tagName : '').toString().toLowerCase().indexOf('body') == -1);
		}
		this.defx = this.x = dd.getPageX(this.div);
		this.defy = this.y = dd.getPageY(this.div);
		this.cssx = dd.getCssX(this);
		this.cssy = dd.getCssY(this);
	}
	this.defw = this.w || 0;
	this.defh = this.h || 0;
}



DDObj.prototype.moveBy = function(d_x, d_y, d_kds, d_o)
{
	if (!this.div) return;
	this.x += (d_x = dd.Int(d_x));
	this.y += (d_y = dd.Int(d_y));
	if (!d_kds || this.is_image || this.parent != this.defparent)
	{
		(d_o = this.css || this.div).left = (this.cssx += d_x) + dd.px;
		d_o.top = (this.cssy += d_y) + dd.px;
	}
	for (var d_i = this.children.length; d_i--;)
	{
		if (!(d_o = this.children[d_i]).detached) d_o.moveBy(d_x, d_y, 1);
		d_o.defx += d_x;
		d_o.defy += d_y;
	}
};



DDObj.prototype.moveTo = function(d_x, d_y)
{
	this.moveBy(dd.Int(d_x)-this.x, dd.Int(d_y)-this.y);
};



DDObj.prototype.hide = function(d_o)
{
	if (this.div) (this.css || this.div).visibility = "hidden";
	this.visible = false;
	for (var d_i = this.children.length; d_i--;)
		if (!(d_o = this.children[d_i]).detached) d_o.hide();
};



DDObj.prototype.show = function()
{
	if (this.div) (this.css ||  this.div).visibility = "visible";
	this.visible = true;
	for (var d_i = this.children.length; d_i--;)
		if (!(d_o = this.children[d_i]).detached) d_o.show();
};



DDObj.prototype.resizeTo = function(d_w, d_h, d_o)
{
	if (!this.div) return;
	d_w = (this.w = dd.Int(d_w))-this.dw;
	d_h = (this.h = dd.Int(d_h))-this.dh;
	if (dd.n4)
	{
		this.div.resizeTo(d_w, d_h);
		if (this.is_image)
		{
			(d_o = this.div.document).open();
			d_o.write('<img src="' + this.cach.src + '" width="' + d_w + '" height="' + d_h + '">');
			d_o.close();
			(this.nimg = d_o.images[0]).src = this.cach.src;
		}
	}
	else if (typeof this.css.pixelWidth != "undefined")
	{
		this.css.pixelWidth = d_w;
		this.css.pixelHeight = d_h;
		if (this.is_image)
		{
			(d_o = this.nimg.style).pixelWidth = d_w;
			d_o.pixelHeight = d_h;
		}
	}
	else
	{
		this.css.width = d_w + dd.px;
		this.css.height = d_h + dd.px;
		if (this.is_image)
		{
			(d_o = this.nimg).width = d_w;
			d_o.height = d_h;
			if (!d_o.complete) d_o.src = this.cach.src;
		}
	}
};



DDObj.prototype.resizeBy = function(d_dw, d_dh)
{
	this.resizeTo(this.w+dd.Int(d_dw), this.h+dd.Int(d_dh));
};



DDObj.prototype.swapImage = function(d_x, d_cp)
{
	if (!this.is_image || !this.nimg) return;
	if (this.cach.src != d_x) (this.cach = new Image()).src = d_x;
	this.nimg.src = this.cach.src;
	this.src = this.nimg.src;
	if (d_cp) for (var d_i = this.copies.length; d_i--;)
		this.copies[d_i].swapImage(this.cach.src);
};



DDObj.prototype.setBgColor = function(d_x, d_o)
{
	if (dd.n4 && this.div) this.div.bgColor = d_x;
	else if (this.css) this.css.background = d_x;
	this.bgColor = d_x;
};



DDObj.prototype.write = function(d_x, d_o)
{
	if (!this.div) return;
	if (dd.n4)
	{
		(d_o = this.div.document).open();
		d_o.write(d_x);
		d_o.close();
		dd.getWH(this);
	}
	else if (!dd.op6)
	{
		this.css.height = 'auto';
		this.div.innerHTML = d_x;
		if (!dd.ie4) dd.recalc();
		if (dd.ie4 || dd.n6) setTimeout('dd.recalc();', 0); // n6.0: double recalc required
	}
};



DDObj.prototype.copy = function(d_n, d_p)
{
	if (!this.oimg) return;
	d_n = d_n || 1;
	while (d_n--)
	{
		var d_l = this.copies.length,
		d_o = new DDObj(this.name+this.cmd, d_l+1);

		if (dd.n4)
		{
			d_o.id = (d_p = new Layer(d_o.w)).name;
			d_p.clip.height = d_o.h;
			d_p.visibility = 'show';
			(d_p = d_p.document).open();
			d_p.write(d_o.htm);
			d_p.close();
		}
		else if (dd.db.insertAdjacentHTML) dd.db.insertAdjacentHTML("AfterBegin", d_o.t_htm);
		else if (document.createElement && dd.db && dd.db.appendChild)
		{
			dd.db.appendChild(d_p = document.createElement('div'));
			d_p.innerHTML = d_o.htm;
			d_p.id = d_o.id;
			d_p.style.position = 'absolute';
			d_p.style.width = d_o.w + 'px';
			d_p.style.height = d_o.h + 'px';
			d_p.style.left = d_o.x + 'px';
			d_p.style.top = d_o.y + 'px';
		}
		else if (dd.db && dd.db.innerHTML) dd.db.innerHTML += d_o.t_htm;

		d_o.defz = 1+d_l;
		dd.addProps(d_o);
		d_o.original = this;
		dd.addElt(d_o, this);
		if (this.parent)
		{
			this.parent.addChild(d_o, this.detached);
			d_o.defparent = this.defparent;
		}
		d_o.moveTo(d_o.defx = this.defx, d_o.defy = this.defy);
		if (dd.n4) d_o.defsrc = d_o.src = this.defsrc;
		d_o.swapImage(this.src);
	}
};



DDObj.prototype.addChild = function(d_kd, detach, defp)
{
	if (typeof d_kd != "object") d_kd = dd.elements[d_kd];
	if (d_kd.parent && d_kd.parent == this || d_kd == this || !d_kd.is_image && d_kd.defparent && !defp) return;

	this.children[this.children.length] = this.children[d_kd.name] = d_kd;
	d_kd.detached = detach || 0;
	if (defp) d_kd.defparent = this;
	else if (this == d_kd.defparent && d_kd.is_image) dd.getImg(this, d_kd.imgname, 1);
	if (!d_kd.defparent || this != d_kd.defparent)
	{
		d_kd.defx = d_kd.x;
		d_kd.defy = d_kd.y;
	}
	if (!detach)
	{
		d_kd.defz = d_kd.defz+this.defz-(d_kd.parent? d_kd.parent.defz : 0)+(d_kd.is_image? 0 : 1);
		d_kd.setZ(d_kd.z+this.z-(d_kd.parent? d_kd.parent.z : 0)+(d_kd.is_image? 0 : 1), 1);
	}
	if (d_kd.parent) d_kd.parent.removeChild(d_kd, 1);
	d_kd.parent = this;
};



DDObj.prototype.removeChild = function(d_kd, d_newp)
{
	if (typeof d_kd != "object") d_kd = this.children[d_kd];
	var d_oc = this.children, d_nc = new Array();
	for (var d_i = 0; d_i < d_oc.length; d_i++)
		if (d_oc[d_i] != d_kd) d_nc[d_nc.length] = d_oc[d_i];
	this.children = d_nc;
	d_kd.parent = null;
	if (!d_newp)
	{
		d_kd.detached = d_kd.defp = 0;
		dd.getImg(d_kd, d_kd.imgname, 1);
	}
};



DDObj.prototype.attachChild = function(d_kd)
{
	(d_kd = (typeof d_kd != "object")? this.children[d_kd]: d_kd).detached = 0;
	d_kd.setZ(d_kd.defz + this.z-this.defz, 1);
};



DDObj.prototype.detachChild = function(d_kd)
{
	(d_kd = (typeof d_kd != "object")? this.children[d_kd]: d_kd).detached = 1;
};



DDObj.prototype.setZ = function(d_x, d_kds)
{
	if (d_kds)
	{
		var d_dz = d_x-this.z,
		d_i = this.children.length; while (d_i--)
			if (!(d_o = this.children[d_i]).detached) d_o.setZ(d_o.z+d_dz, 1);
	}
	dd.z = Math.max(dd.z, this.z = this.div? ((this.css || this.div).zIndex = d_x) : 0);
};



DDObj.prototype.maximizeZ = function()
{
	this.setZ(dd.z+1, 1);
};



DDObj.prototype.resetZ = function(d_o)
{
	if (this.re_z || dd.re_z)
	{
		this.setZ(this.defz);
		for (var d_i = this.children.length; d_i--;)
			if (!(d_o = this.children[d_i]).detached) d_o.setZ(d_o.defz);
	}
};



DDObj.prototype.setCursor = function(d_x)
{
	if (this.css) this.css.cursor = ((!dd.ie || dd.iemac) && d_x == 'hand')? 'pointer' : d_x;
};



DDObj.prototype.setDraggable = function(d_x)
{
	this.nodrag = !d_x*1;
	this.setCursor(d_x? this.cursor : 'auto');
};






function WINSZ(d_x)
{
	if (d_x)
	{
		if (dd.n4 || dd.op6 && d_x & 0x2)
		{
			dd.iW = innerWidth;
			dd.iH = innerHeight;
			if (dd.op6) setTimeout("WINSZ()", 0x1ff);
		}
		window.onresize = new Function('WINSZ();');
	}
	else if ((dd.n4 || dd.op6) && (innerWidth != dd.iW || innerHeight != dd.iH)) location.reload();
	else if (dd.op6) setTimeout("WINSZ()", 0x1ff);
	else if (!dd.n4) setTimeout('dd.recalc()', 0xa);
}
WINSZ(1);






// Page auto-scrolling functionality. Idea for this feature courtesy Cedric Savarese.
function DDScroll()
{
	if (!dd.obj || dd.obj.noscroll || dd.noscroll || dd.op || dd.ie4 || dd.whratio)
	{
		dd.scrx = dd.scry = 0;
		return;
	}
	var d_bnd = 0x19,
	d_sft = 0x2,
	d_ww = dd.getWndW(),
	d_wh = dd.getWndH(),
	d_wx = dd.getScrollX(),
	d_wy = dd.getScrollY();

	if (!dd.mousemoved)
	{
		if (dd.scrx || dd.scry)
		{
			if (!d_wx && dd.scrx < 0) dd.scrx = 0;
			if (!d_wy && dd.scry < 0) dd.scry = 0;
		}
	}
	else
	{
		dd.scrx = (dd.e.x > d_ww + d_wx - d_bnd)? Math.pow((dd.e.x - d_ww - d_wx + d_bnd) >>d_sft, 0x2)
			: (dd.e.x < d_wx + d_bnd)? -Math.pow((d_wx + d_bnd - dd.e.x) >>d_sft, 0x2)
			: 0;
		dd.scry = (dd.e.y > d_wh + d_wy - d_bnd)? Math.pow((dd.e.y - dd.getWndH() - d_wy + d_bnd) >>d_sft, 0x2)
			: (dd.e.y < d_wy + d_bnd)? -Math.pow((d_wy + d_bnd - dd.e.y) >>d_sft, 0x2)
			: 0;
	}
	if (dd.scrx || dd.scry)
	{
		window.scrollTo(
			d_wx+(dd.scrx = dd.obj.vertical? 0 : dd.maxOffX(dd.scrx = dd.obj.is_resized? dd.limitW(dd.scrx) : dd.scrx)),
			d_wy+(dd.scry = dd.obj.horizontal? 0 : dd.maxOffY(dd.scry = dd.obj.is_resized? dd.limitH(dd.scry) : dd.scry))
		);
		if (!dd.mousemoved)
		{
			dd.prex += (dd.scrx = dd.getScrollX()-d_wx);
			dd.prey += (dd.scry = dd.getScrollY()-d_wy);
			if (dd.obj.is_dragged) dd.obj.moveBy(dd.scrx, dd.scry);
			else dd.resizeBy(dd.scrx, dd.scry);
		}
	}
	dd.mousemoved = 0;
	window.setTimeout('DDScroll()', 0x33);
}






function PICK(d_ev)
{
	dd.e = new dd.evt(d_ev);
	// return if target is scrollbar
	if (dd.e.x >= dd.getWndW()+dd.getScrollX() || dd.e.y >= dd.getWndH()+dd.getScrollY()) return true;
	for (var d_o, d_cmp = -1, d_i = dd.elements.length; d_i--;)
	{
		d_o = dd.elements[d_i];
		if (dd.n4 && dd.e.but > 1 && dd.e.src == d_o.oimg && !d_o.clone) return false;
		if (d_o.visible && dd.e.but <= 2 && !d_o.nodrag && dd.e.x >= d_o.x && dd.e.x <= d_o.x+d_o.w && dd.e.y >= d_o.y && dd.e.y <= d_o.y+d_o.h)
		{
			if (d_o.z > d_cmp && dd.e.src.tag.indexOf('input') < 0 && dd.e.src.tag.indexOf('textarea') < 0)
			{
				d_cmp = d_o.z;
				dd.obj = d_o;
				var d_rsz = (dd.e.shiftKey || dd.e.ctrlKey) && (d_o.resizable || d_o.scalable || dd.resizable || dd.scalable);
			}
			dd.e.e.cancelBubble = true;
		}
	}
	if (dd.obj)
	{
		if (dd.op && !dd.op6)
		{
			(d_o = document.getElementById('OpBlUr')).style.pixelLeft = dd.e.x;
			d_o.style.pixelTop = dd.e.y;
			(d_o = d_o.children[0].children[0]).focus();
			d_o.blur();
		}
		else if (dd.ie && !dd.ie4)
		{
			if (document.selection && document.selection.empty) document.selection.empty();
			dd.db.onselectstart = dd.reFalse;
		}

		if (d_rsz)
		{
			dd.obj.setCursor('se-resize');
			dd.obj.is_resized = 1;
			dd.whratio = (dd.obj.scalable || dd.scalable && !dd.obj.resizable)? dd.obj.defw/dd.obj.defh
				: (dd.e.shiftKey && dd.e.ctrlKey)? dd.obj.w/dd.obj.h : 0;
			if (dd.ie)
			{
				if (dd.ie4)
				{
					window.dd_x = dd.getScrollX();
					window.dd_y = dd.getScrollY();
				}
				setTimeout(
					'if (dd.obj && document.selection && document.selection.empty)'+
					'{'+
						'document.selection.empty();'+
						'if (dd.ie4) window.scrollTo(window.dd_x, window.dd_y);'+
					'}'
				,0);
			}
			dd.setEvtHdl(1, RESIZE);
			dd.resizeBy(0, 0);
		}
		else if (!dd.obj.nodrag)
		{
			dd.obj.is_dragged = 1;
			dd.setEvtHdl(1, DRAG);
		}

		dd.setEvtHdl(2, DROP);
		dd.setEmbedVis('hidden');
		dd.obj.maximizeZ();
		dd.prex = dd.e.x;
		dd.prey = dd.e.y;
		if (window.my_PickFunc) my_PickFunc();
		DDScroll();

		return !(
			dd.obj.is_resized
			||
			dd.n4 && dd.obj.is_image
			||
			dd.n6 || dd.kq
		);
	}
	if (dd.downFunc) return dd.downFunc(d_ev);
	return true;
}



function DRAG(d_ev)
{
	if (!dd.obj || !dd.obj.visible) return true;
	if (dd.ie4 || dd.kq || dd.n6 || dd.obj.children.length > 0xf)
	{
		if (dd.wait) return false;
		dd.wait = 1;
		setTimeout('dd.wait = 0;', 0x5);
	}
	dd.e = new dd.evt(d_ev);
	if (dd.ie && !dd.e.but)
	{
		DROP(d_ev);
		return true;
	}

	dd.mousemoved = 1;
	var d_dx = dd.obj.vertical? 0 : dd.inClientW(dd.maxOffX(dd.e.x-dd.prex)),
	d_dy = dd.obj.horizontal? 0 : dd.inClientH(dd.maxOffY(dd.e.y-dd.prey));
	dd.obj.moveBy(d_dx, d_dy);

	if (window.my_DragFunc) my_DragFunc();
	dd.prex += d_dx;
	dd.prey += d_dy;
	return false;
}



function RESIZE(d_ev)
{
	if (!dd.obj || !dd.obj.visible) return true;
	if (dd.wait) return false;
	dd.wait = 1;
	setTimeout('dd.wait = 0;', 0x5);
	dd.e = new dd.evt(d_ev);
	if (dd.ie && !dd.e.but)
	{
		DROP(d_ev);
		return true;
	}

	dd.mousemoved = 1;
	var d_dx = dd.inClientW(dd.limitW(dd.e.x-dd.prex));
	if (!dd.whratio) var d_dy = dd.inClientH(dd.limitH(dd.e.y-dd.prey));
	else
	{
		d_dy = dd.inClientH(dd.limitH(Math.round((dd.obj.w+d_dx)/dd.whratio)-dd.obj.h));
		d_dx = Math.round((dd.obj.h+d_dy)*dd.whratio)-dd.obj.w;
	}
	dd.resizeBy(d_dx, d_dy);

	if (window.my_ResizeFunc) my_ResizeFunc();
	dd.prex += d_dx;
	dd.prey += d_dy;
	return false;
}



function DROP(d_ev)
{
	if (dd.obj)
	{
		if (dd.obj.is_dragged)
		{
			if (!dd.obj.is_image) dd.getWH(dd.obj);
		}
		else if (dd.n4)
		{
			if (dd.obj.is_image)
			{
				dd.n4RectVis(0);
				dd.obj.resizeTo(dd.obj.w, dd.obj.h);
			}
		}
		if (!dd.n4 && !dd.op6 || !dd.obj.is_image) dd.recalc();
		dd.setEvtHdl(1, dd.moveFunc);
		dd.setEvtHdl(2, dd.upFunc);
		if (dd.db) dd.db.onselectstart = null;
		dd.obj.setCursor(dd.obj.cursor);
		dd.setEmbedVis('visible');
		dd.obj.resetZ();
		if (window.my_DropFunc)
		{
			dd.e = new dd.evt(d_ev);
			my_DropFunc();
		}
		dd.mousemoved = dd.obj.is_dragged = dd.obj.is_resized = dd.whratio = 0;
		dd.obj = null;
	}
	dd.setEvtHdl(0, PICK);
	dd.setEvtHdl(3, CONTEXT);
}

function CONTEXT(d_ev)
{
	if(window.my_ContextFunc)
	{
		dd.e = new dd.evt(d_ev);
		my_ContextFunc();
	}
}

function SET_DHTML()
{
	dd.elements = new Array();
	for (var d_a = SET_DHTML.arguments, d_ai, d_htm = '', d_o, d_i = d_a.length; d_i--;)
	{
		if (dd.op6)
		{
			var d_t0 = (new Date()).getTime();
			while ((new Date()).getTime()-d_t0 < 0x99);
		}
		if (!(d_ai = d_a[d_i]).indexOf('c:')) dd.cursor = d_ai.substring(0x2);
		else if (d_ai == NO_ALT) dd.noalt = 1;
		else if (d_ai == NO_SCROLL) dd.noscroll = 1;
		else if (d_ai == RESET_Z) dd.re_z = 1;
		else if (d_ai == RESIZABLE) dd.resizable = 1;
		else if (d_ai == SCALABLE) dd.scalable = 1;
		else
		{
			d_o = new DDObj(d_ai);
			dd.addElt(d_o);
			d_o.defz = 1;
			d_htm += d_o.t_htm || '';
			if (d_o.oimg && d_o.cpy_n)
			{
				for (var d_j = 0; d_j < d_o.cpy_n;)
				{
					var d_p = new DDObj(d_o.name+d_o.cmd, ++d_j);
					dd.addElt(d_p, d_o);
					d_p.defz = d_o.defz+d_j;
					d_p.original = d_o;
					d_htm += d_p.t_htm;
				}
			}
		}
	}
    
	if (dd.n4 || dd.n6 || dd.ie || dd.op || dd.kq) {
      /*
      document.write((dd.n4? '<div style="position:absolute;"><\/div>\n'
                      : (dd.op && !dd.op6)? '<div id="OpBlUr" style="position:absolute;visibility:hidden;width:0px;height:0px;"><form><input type="text" style="width:0px;height:0px;"><\/form><\/div>'
		: '') + d_htm
                     );
      
       var div = document.createElement('div');
      div.style.position = 'absolute';
      
      dd.n4? document.body.appendChild(div):(dd.op && dd.op6)?:)
      */
    }

	dd.z = 0x32;

	for (d_i = dd.elements.length; d_i--;)
	{
		dd.addProps(d_o = dd.elements[d_i]);
		if (d_o.is_image && !d_o.original && !d_o.clone)
		{
			if (dd.n4) d_o.oimg.src = spacer;
			else d_o.oimg.style.visibility = 'hidden';
		}
	}
	dd.mkWzDom();

	if (window.onload) dd.loadFunc = window.onload;
	window.onload = dd.init;
	dd.setEvtHdl(0, PICK);
	if(dd.ie) dd.setEvtHdl(3, CONTEXT);
}



function ADD_DHTML(d_o)
{
	// layers only!
	d_o = new DDObj(d_o);
	dd.addElt(d_o);
	dd.addProps(d_o);
	dd.mkWzDom();
}








////////////////////////////////////////////////////////////
// If not needed, all code below this line may be removed



// For backward compatibility
dd.d = document;			// < v. 2.72
var RESET_ZINDEX = RESET_Z; // < 3.44
var KEYDOWN_RESIZE = RESIZABLE; // < 4.43
var CURSOR_POINTER = CURSOR_HAND; // < 4.44






////////////////////////////////////////////////////////////
// FUNCTIONS FOR EXTENDED SCRIPTING
// Use these for your own extensions,
// or to call functions defined elsewhere



/* my_PickFunc IS AUTOMATICALLY CALLED WHEN AN ITEM STARTS TO BE DRAGGED.
The following objects/properties are accessible from here:

- dd.e: current mouse event
- dd.e.property: access to a property of the current mouse event.
  Mostly requested properties:
  - dd.e.x: document-related x co-ordinate
  - dd.e.y: document-related y co-ord
  - dd.e.src: target of mouse event (not identical with the drag drop object itself).
  - dd.e.button: currently pressed mouse button. Left button: dd.e.button <= 1

- dd.obj: reference to currently dragged item.
- dd.obj.property: access to any property of that item.
- dd.obj.method(): for example dd.obj.resizeTo() or dd.obj.swapImage() .
  Mostly requested properties:
	- dd.obj.name: image name or layer ID passed to SET_DHTML();
	- dd.obj.x and dd.obj.y: co-ordinates;
	- dd.obj.w and dd.obj.h: size;
	- dd.obj.is_dragged: 1 while item is dragged, else 0;
	- dd.obj.is_resized: 1 while item is resized, i.e. if <ctrl> or <shift> is pressed, else 0

For more properties and details, visit the API documentation
at http://www.walterzorn.com/dragdrop/api_e.htm (english) or
http://www.walterzorn.de/dragdrop/api.htm (german)    */
function my_PickFunc()
{
	window.status = 'dd.elements.' + dd.obj.name + (dd.obj.is_dragged? ('.x = ' + dd.obj.x) : ('.w = ' + dd.obj.w)) + '      dd.elements.' + dd.obj.name + (dd.obj.is_dragged? ('.y = ' + dd.obj.y) : ('.h = ' + dd.obj.h));
}




/* my_DragFunc IS CALLED WHILE AN ITEM IS DRAGGED
See the description of my_PickFunc above for what's accessible from here. */
function my_DragFunc()
{
	window.status = 'dd.elements.' + dd.obj.name + '.x  = ' + dd.obj.x + '     dd.elements.' + dd.obj.name + '.y = ' + dd.obj.y;
}




/* my_ResizeFunc IS CALLED WHILE AN ITEM IS RESIZED
See the description of my_PickFunc above for what's accessible from here. */
function my_ResizeFunc()
{
	window.status = 'dd.elements.' + dd.obj.name + '.w  = ' + dd.obj.w + '     dd.elements.' + dd.obj.name + '.h = ' + dd.obj.h;
}




/* THIS ONE IS CALLED ONCE AN ITEM IS DROPPED
See the description of my_PickFunc for what's accessible from here.
Here may be investigated, for example, what's the name (dd.obj.name)
of the dropped item, and where (dd.obj.x, dd.obj.y) it has been dropped... */
function my_DropFunc()
{
	window.status = 'dd.elements.' + dd.obj.name + (dd.obj.is_dragged? ('    dropped at x = ' + dd.obj.x + '      y = ' + dd.obj.y) : ('    resized to w = ' + dd.obj.w + '     h = ' + dd.obj.h));
}

// added by LEG, 05-mar-30
function my_ContextFunc()
{
	window.status = 'dd.elements.' + dd.obj.name + (dd.obj.is_dragged? ('    dropped at x = ' + dd.obj.x + '      y = ' + dd.obj.y) : ('    resized to w = ' + dd.obj.w + '     h = ' + dd.obj.h));
}

var wz_dragdrop_loaded = true;

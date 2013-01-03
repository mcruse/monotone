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
/*
Purpose: Page refresh logic for web pages containing WebExpress widgets
Version: 1_0_dev_2

$Id: pagerefresh.js 20101 2011-03-06 16:02:15Z bhagn $
*/
//alert("pagerefresh.js, window.parent.WebExpressEditor=" + window.parent.WebExpressEditor);
if(!(window.parent && window.parent.WebExpressEditor)) {
  if(document.addEventListener) {
    //alert("startPageRefresh handler added by addEventListener");
    window.addEventListener("load",startPageRefresh,true);
    window.addEventListener("unload",stopPageRefresh,true);
  }
  else if(document.attachEvent) {
    //alert("startPageRefresh handler added by attachEvent");
    window.attachEvent("onload",startPageRefresh);
    window.attachEvent("onunload",stopPageRefresh);
  }
  else {
    //alert("startPageRefresh handler added by onload property");
    window.onload = startPageRefresh;
    window.onunload = stopPageRefresh;
  }
}
//window.onload = startPageRefresh;

function contextMenuHandler(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt) {
    if(evt.preventDefault) { //NN6 (or Mozilla?)
      evt.preventDefault();
    }
    evt.returnValue = false; //IE6
  }
}

var pageRefreshStarted = false;

var MEDIATOR = null;
var PAGEPROPSID = 'WebExpressPageProps';

function startPageRefresh(){
  //disable context menu (right-click) for this page when in WebExpressEditor
  if(window.parent && window.parent.WebExpressEditor) {
    var browserIE = new RegExp('internet explorer','gi');
    if(browserIE.test(navigator.appName)) {
      document.body.oncontextmenu = contextMenuHandler;
    }
    else {
      document.body.addEventListener("contextmenu", contextMenuHandler, true);
    }
  }

  //alert("startPageRefresh()");
  MEDIATOR = new Mediator();
  var page_properties = new PageProperties(MEDIATOR,3000,PAGEPROPSID);
  MEDIATOR.login();
  start_refresh_loop(page_properties);
  pageRefreshStarted = true;
}

function stopPageRefresh(){
  //disable context menu (right-click) for this page when in WebExpressEditor
  if(window.parent && window.parent.WebExpressEditor) {
    var browserIE = new RegExp('internet explorer','gi');
    if(browserIE.test(navigator.appName)) {
      document.body.oncontextmenu = contextMenuHandler;
    }
    else {
      document.body.addEventListener("contextmenu", contextMenuHandler, true);
    }
  }

  stop_page_refresh();
}

var pagerefresh_loaded = true;

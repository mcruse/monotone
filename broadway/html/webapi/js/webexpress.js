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
Purpose: WebExpress editor
$Name: mediator_3_1_2_branch $
$Id: webexpress.js 20744 2011-07-18 06:43:59Z bhagn $
*/
var HTML;
var WebExpressDebug = false;
var WebExpressEditor = true;
var WebExpressProtocol = window.location.protocol;
var WebExpressHostname = window.location.hostname;
var WebExpress_RETRIES = 0;
var WebExpress_MAX_RETRIES = 100;
var WIDGET_BORDER = '1px solid blue';
var CURRENT_ID = null;
var HTTP_ERRORS = new Object();
HTTP_ERRORS[400] = 'Bad Request';
HTTP_ERRORS[401] = 'Unauthorized';
HTTP_ERRORS[402] = 'Payment Required';
HTTP_ERRORS[403] = 'Forbidden';
HTTP_ERRORS[404] = 'Not Found';
HTTP_ERRORS[405] = 'Method Not Allowed';
HTTP_ERRORS[406] = 'Not Acceptable';
HTTP_ERRORS[407] = 'Proxy Authentication Required';
HTTP_ERRORS[408] = 'Request Timeout';
HTTP_ERRORS[409] = 'Conflict';
HTTP_ERRORS[410] = 'Gone';
HTTP_ERRORS[411] = 'Length Required';
HTTP_ERRORS[412] = 'Precondition Failed';
HTTP_ERRORS[413] = 'Request Entity Too Large';
HTTP_ERRORS[414] = 'Request-URI Too Long';
HTTP_ERRORS[415] = 'Unsupported Media Type';
HTTP_ERRORS[416] = 'Requested Range Not Satisfiable';
HTTP_ERRORS[411] = 'Expectation Failed';

var WebExpress_src_map = new Object();
WebExpress_src_map['widget'] = '/webapi/js/widget.js';
var WebExpress_request;
var WebExpressMsgTypes = new Object();
WebExpressMsgTypes.NORMAL = 'black';
WebExpressMsgTypes.ERROR = 'red';
var WebExpressMsgTimeout;
var startRetryCount = 600;
var IFRAMENAME = '';
var IFRAME = null;
var newElement = null;
var newWidgetFrag = null;
var newWidgetHolder = null;
var newWidgetID = '';
var qs = get_query_string_args();
if (qs['file']){
  FILE = qs['file'];
}
if(qs['showallfiles']){
  SHOWALLFILES = qs['showallfiles'];
}
else {
  SHOWALLFILES = 'false';
}
var SAVEDFILEURL = '';
var SAVEDFILENAME = '';

function WEmsglog(msg) {
  if(WebExpressDebug) {
    msglog(msg);
  }
}

//@@
// @function center							
// takes the window object and centers the window and sets focus to the window
// @param objWin a window object refrenece
// @param width width of the window
// @param height height of the window
// @return null
function center_window(objWin,w,h){
    var height = window.screen.availHeight;
    var width = window.screen.availWidth;
    var left_point = parseInt(width/2) - parseInt(w/2);
    var top_point =  parseInt(height/2) - parseInt(h/2);
    objWin.moveTo(left_point,top_point);
    objWin.resizeTo(w,h);
    objWin.focus();
}

function addElementToEditDocHead() {
  var editDoc = WebExpress_getEditDocument();
}

function addElementToEditDocBody() {
  var editDoc = WebExpress_getEditDocument();
}

function WebExpress_AddWidget(name,factory){
  var e = document.getElementById('WebExpressWidgets');
  e.options[e.options.length] = new Option(name,factory);
}

function WebExpress_getEditDocument(){
  var editDoc = null;
  //this seems to work in both IE and Mozilla
  editDoc = document.getElementById(IFRAMENAME).contentWindow.document;
  return editDoc
}

function WebExpress_in_scripts(script,scripts){
  var i;
  var found = false;
  for(i=0;i<scripts.length;i++){
    if (scripts[i].src == script){
      found = true;
      break;
   }
  }
  return found
}



function WebExpress_add_widget_script(doc,script){
  var scripts = doc.getElementsByTagName('script');
  var i;
  var found = false;
  for(i=0;i<scripts.length;i++){    
    if (scripts[i].src == script){
      found = true;
      break;
    }
  }
  if(found == false){
    var head = doc.getElementsByTagName('head')[0];
    scpt = doc.createElement('script');
    scpt.setAttribute('language','JavaScript');
    scpt.setAttribute('type','text/javascript');
    scpt.setAttribute('src',script);
    scpt.setAttribute('widget','true');
    head.appendChild(scpt); 
  }
}

var startPageRefreshNeeded = false;

//needed_scripts array format:
//[0]=script name, [1]=script URL, [2]=load completion flag
var needed_scripts = [['wz_dragdrop','/webapi/js/wz_dragdrop.js','wz_dragdrop_loaded',false],
		['sdk2','/webapi/js/sdk2.js','sdk2_loaded',false],
		['pagerefresh','/webapi/js/pagerefresh.js','pagerefresh_loaded',false],
                ['widget','/webapi/js/widget.js','widget_loaded',false]];

// WebExpress_add_scripts() -- Adds needed scripts to edit document for widget support and WebExpress editing
WebExpress_add_scripts.retryCount = 0;
WebExpress_add_scripts.scriptIndex = 0;
function WebExpress_add_scripts(){
  WEmsglog("WebExpress_add_scripts(), at top, scriptIndex=" + WebExpress_add_scripts.scriptIndex);
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  var editDoc = WebExpress_getEditDocument();
  var editHead = editDoc.getElementsByTagName('head')[0];

  for(;WebExpress_add_scripts.scriptIndex<needed_scripts.length;WebExpress_add_scripts.scriptIndex++){
    try{
      if(needed_scripts[WebExpress_add_scripts.scriptIndex][3] == false) {
        //first, if needed script exists in edit document, then move it to end of editHead childNodes array
        var found = false;
        for(var i = 0; i < editHead.childNodes.length; i++) {
          if(editHead.childNodes[i].nodeType == 1 && editHead.childNodes[i].tagName == 'SCRIPT') {
            if(needed_scripts[WebExpress_add_scripts.scriptIndex][1] == editHead.childNodes[i].getAttribute('src')) {
              WEmsglog("WebExpress_add_scripts(), moving " + needed_scripts[WebExpress_add_scripts.scriptIndex][1]);
              //var toEval = "editWin." + needed_scripts[WebExpress_add_scripts.scriptIndex][2] + " = null;";
              //eval(toEval);
              editHead.appendChild(editHead.childNodes[i]); //move script to end of editHead childNodes array
              needed_scripts[WebExpress_add_scripts.scriptIndex][3] = true;
              WebExpress_add_scripts.retryCount = 0;
	      found = true;
              break;
            }
          }
        }
        //if needed script doesn't exist in edit document, append it to end of editHead childNodes array
        if(!found) {
          //add missing script
          WEmsglog("WebExpress_add_scripts(), adding " + needed_scripts[WebExpress_add_scripts.scriptIndex][1]);
          WebExpress_add_scripts.retryCount = 0;
          scpt = editDoc.createElement('script');
          scpt.setAttribute('language','JavaScript');
          scpt.setAttribute('type','text/javascript');
          scpt.setAttribute('src',needed_scripts[WebExpress_add_scripts.scriptIndex][1]);
          scpt.setAttribute('WebExpress','true');
          editHead.appendChild(scpt); 
          needed_scripts[WebExpress_add_scripts.scriptIndex][3] = true;
        }
	//if pagerefresh script added, set flag to call startPageRefresh()
        if(needed_scripts[WebExpress_add_scripts.scriptIndex][0] == 'pagerefresh') {
          WEmsglog("WebExpress_add_scripts(), set flag to call startPageRefresh()");
          startPageRefreshNeeded = true;
	}
        window.setTimeout("WebExpress_add_scripts()",100);
        return;
      }//end if needed script not yet moved or added
      else {
        if(WebExpress_add_scripts.retryCount < startRetryCount) {
          var toEval = "editWin." + needed_scripts[WebExpress_add_scripts.scriptIndex][2];
          WEmsglog("WebExpress_add_scripts(), eval of " + toEval);
          if(!eval(toEval)) { //if script load not complete
            //wait for script load completion
            WEmsglog("WebExpress_add_scripts(), waiting for " +
              needed_scripts[WebExpress_add_scripts.scriptIndex][0] + " to load");
            WebExpress_add_scripts.retryCount++; 
            window.setTimeout("WebExpress_add_scripts()",100);
            return;
          }
        }
        else {
          alert("Timeout loading script " + needed_scripts[WebExpress_add_scripts.scriptIndex][0]);
        }
      }//end else
    }//end try
    catch(err){
      WEmsglog("WebExpress_add_scripts(), error: " + ex.name + ", " + ex.description);
    }
  } //end for
  //move remaining scripts to end of editHead childNodes array
  var moveDone = false;
  do {
    for(var i = 0; i < editHead.childNodes.length; i++) {
      if(editHead.childNodes[i].nodeType == 1 && editHead.childNodes[i].tagName == 'SCRIPT') {
        if(needed_scripts[0][1] == editHead.childNodes[i].getAttribute('src')) {
          //first required script found, end processing
          moveDone = true;
          break; //break for loop
        }
        else {
          //move script to end of editHead childNodes array
          WEmsglog("WebExpress_add_scripts(), moving " + editHead.childNodes[i].getAttribute('src'));
          editHead.appendChild(editHead.childNodes[i]);
          break; //break for loop
        }
      }
    }
  } while(!moveDone);

  document.getElementById('WebExpressWidgets').disabled = false;

  WebExpress_msg('Initializing drag&drop library...');
  window.setTimeout("WebExpress_startPhase4()",0);
}
 
//initialize drag and drop for edit document
function WebExpress_SET_DHTML(){
   WEmsglog("WebExpress_SET_DHTML(), at top");
   var iframe = document.getElementById(IFRAMENAME);
   iframe.contentWindow.SET_DHTML();
   iframe.contentWindow.my_PickFunc = WebExpress_my_PickFunc;
   iframe.contentWindow.my_DragFunc = WebExpress_my_DragFunc;
   iframe.contentWindow.my_DropFunc = WebExpress_my_DropFunc;
   iframe.contentWindow.my_ContextFunc = WebExpress_ConfigureWidget;
   var editDoc = WebExpress_getEditDocument();
   var divs = WebExpress_getDivs(editDoc);
   var i;
   for(i=0;i<divs.length;i++){
     var id = divs[i].getAttribute('id');
     divs[i].style.border = WIDGET_BORDER;
     iframe.contentWindow.ADD_DHTML(id);     
   }
}

//make element draggable
function WebExpress_ADD_DHTML(elementID){
  WEmsglog("WebExpress_ADD_DHTML(), at top");
  var iframe = document.getElementById(IFRAMENAME);
  var element = iframe.contentWindow.document.getElementById(elementID);
  element.style.border = WIDGET_BORDER;
  iframe.contentWindow.ADD_DHTML(elementID);
  // force widget container to resize to contents (overrides wz_dragdrop stuff)
  if(element.getAttribute('auto_resize')) {
    if(element.getAttribute('auto_resize') == 'true') {
      element.style.width = 'auto';
      element.style.height = 'auto';
    }
  }
  else {
    element.style.width = 'auto';
    element.style.height = 'auto';
  }
}
 

// This function create the widget in the iframe, it also
// adds it to the dragdrop library.
function WebExpress_CreateWidget(){
  var widget;
  if (document.getElementById('WebExpressWidgets').value != ''){
    var editDoc = WebExpress_getEditDocument();
    var editBody = editDoc.getElementsByTagName('body')[0];

    //create new widget in editor window
    widget = eval('new ' + document.getElementById('WebExpressWidgets').value);  
    if (widget.EDIT_DOC_HACK != undefined) {
      widget.edit_doc = editDoc;
    }
    widget.create();
    var element = widget.get();
    element.style.position = 'absolute';
    element.style.top = '5px';
    element.style.left = '5px';

    newWidgetID = WebExpress_getID();
    element.setAttribute('id',newWidgetID);

    //create temporary div element in editor window to hold newly created widget
    var wrapper_element = null;
    if (widget.EDIT_DOC_HACK == undefined) {
      wrapper_element = document.createElement('div');
    } else {
      wrapper_element = element.ownerDocument.createElement('div');
    }
    wrapper_element.appendChild(element);
    WEmsglog("WebExpress_CreateWidget(), wrapper_element.innerHTML=" + wrapper_element.innerHTML);

    //add widget javascript file to edit document
    WebExpress_add_widget_script(editDoc,WebExpress_src_map[widget._name]);

    //create temporary div element in edit document to hold newly created widget
    newWidgetHolder = editDoc.createElement('div');
    newWidgetHolder.setAttribute('id','NewWidgetHolder');

    //copy widget from editor window to edit document
    newWidgetHolder.innerHTML = wrapper_element.innerHTML;
    WEmsglog("WebExpress_CreateWidget(), newWidgetHolder.innerHTML=" + newWidgetHolder.innerHTML);
    editBody.appendChild(newWidgetHolder);

    //set timeout to allow element creation to complete
    var iframe = document.getElementById(IFRAMENAME); 
    iframe.contentWindow.setTimeout("parent.WebExpress_CreateWidget_Phase2()",0);
  }
  else {
      alert('Please pick a widget type in selection box and try again.');
  }
}

function WebExpress_CreateWidget_Phase2() {
  WEmsglog("WebExpress_CreateWidget_Phase2(), newWidgetID=" + newWidgetID);
  var editDoc = WebExpress_getEditDocument();
  var editBody = editDoc.getElementsByTagName('body')[0];
  var newElem = editDoc.getElementById(newWidgetID);

  //move new widget from holder to body
  editBody.appendChild(newElem);

  //set timeout to allow element creation to complete
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.setTimeout("parent.WebExpress_CreateWidget_Phase3()",0);
}

function WebExpress_CreateWidget_Phase3() {
  WEmsglog("WebExpress_CreateWidget_Phase3(), newWidgetID=" + newWidgetID);
  /*var editDoc = WebExpress_getEditDocument();
  var newElem = editDoc.getElementById(newWidgetID);
  if(newElem.getAttribute('widget') == 'GenericOverride') {
    var phelement = GenericOverrideGetElement(newElem,'div','placeholder');
    var outelement = GenericOverrideGetElement(newElem,'div','outercontainer');
    var tblelement = GenericOverrideGetElement(newElem,'table','widgettable');
    tblelement.rows[0].cells[0].setAttribute('width',phelement.offsetParent.offsetWidth);
    newElem.setAttribute('width',outelement.offsetWidth);
    var tblwidth = tblelement.rows[0].cells[0].getAttribute('width');
    tblwidth += tblelement.rows[0].cells[1].getAttribute('width');
    tblwidth += tblelement.rows[0].cells[2].getAttribute('width');
    //tblelement.setAttribute('width','300');
    Widget_log('WebExpress_CreateWidget_Phase3(), tblelement width=' + tblelement.getAttribute('width'));
    Widget_log('WebExpress_CreateWidget_Phase3(), newElem width=' + newElem.getAttribute('width'));
  }*/

  //make new widget draggable
  WebExpress_ADD_DHTML(newWidgetID);

  //get rid of temporary div element in edit document
  var editDoc = WebExpress_getEditDocument();
  var editBody = editDoc.getElementsByTagName('body')[0];
  var elem = editDoc.getElementById('NewWidgetHolder');
  editBody.removeChild(elem);

  //set pagedirty so new widget is refreshed
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.PAGE_PROPERTIES.setPageDirty(true);
}

//Returns a unique ID for a new widget in edit document
function WebExpress_getID(){
  var doc = WebExpress_getEditDocument(IFRAMENAME);
  var number = 1;
  var id = 'layer' + number.toString();
  var e = null;
  while(true){
    e = doc.getElementById(id)
    if (e == null){
        break;
    }
    else{
      number++;
      id = 'layer' + number.toString();
    }
  }
  return id  
}


function WebExpress_get_file_name(f){
  var splt = f.split('/');
  var n = splt[splt.length-1]
  return  n.substring(0,n.length-4)
}

function WebExpress_get_factory(f){
   var factory;
   factory = WebExpress_get_file_name(f) + '_factory()';
   return factory
}

function WebExpress_msg(msg,type){
  if (arguments.length == 1){
    type = WebExpressMsgTypes.NORMAL;
   }
   document.getElementById('msg').innerHTML = msg;
   document.getElementById('msg').style.color = type;
}

function WebExpress_start(){
  //WEmsglog("WebExpress_start(), at top");
  //add necessary scripts to editor window
  var scripts = document.getElementsByTagName('script');
  var i = 0;
  for(i=0;i<scripts.length;i++){
    if (scripts[i].src != null){
      WEmsglog("WebExpress_start(), scripts[i].src=>" + scripts[i].src + "<");
      var n = scripts[i].src.search('/webapi/js/widget.js');
      if (scripts[i].getAttribute('widget') != null &&  n ==-1){
        factory =  WebExpress_get_factory(scripts[i].src);
        widget = eval(factory);
        WebExpress_AddWidget(widget._name,factory);
        WebExpress_src_map[widget._name] = scripts[i].src;     
      }
    }
  } //end for scripts

  //create iframe for editing 
  var iFrameHolder = document.getElementById("editFrameHolder");
  var childFrame = document.createElement("iframe");
  IFRAMENAME = "editFrame";
  childFrame.setAttribute("id",IFRAMENAME);
  childFrame.setAttribute("name",IFRAMENAME);
  childFrame.setAttribute("title","content");
  childFrame.src = '/webapi/emptypage.html';
  childFrame.scrolling = 'auto';
  iFrameHolder.appendChild(childFrame);
  window.setTimeout("WebExpress_startPhase2();",0); //fixes IE appendChild() race
}

function WebExpress_startPhase2() {
  WEmsglog("WebExpress_startPhase2(), at top");
  WebExpress_msg('Loading "'+  FILE + '"...');
  //load iframe with target file
  var browserIE = new RegExp('internet explorer','gi');
  if(browserIE.test(navigator.appName)) {
    //Internet Explorer
    if(FILE != 'NEWFILE') {
      document.getElementById(IFRAMENAME).src = document.getElementById("editFrameHolder").getAttribute("editFile");
    }
    waitForIFrameToLoad();
  }
  else {
    //Netscape Navigator
    document.getElementById(IFRAMENAME).onload = WebExpress_startPhase3;
    if(FILE != 'NEWFILE') {
      document.getElementById(IFRAMENAME).src = document.getElementById("editFrameHolder").getAttribute("editFile");
    }
  }
}

function waitForIFrameToLoad() {
  WEmsglog("waitForIFrameToLoad(), at top");
  var iFrameDoc = document.getElementById(IFRAMENAME).contentWindow.document;
  if(iFrameDoc.readyState == "complete") {
    WebExpress_startPhase3();
  }
  else {
    window.setTimeout("waitForIFrameToLoad()",1);
  }
}

// WebExpress_startPhase3: Called after the editFrame loads.
function WebExpress_startPhase3() {
  WEmsglog("WebExpress_startPhase3(), at top");
  WebExpress_msg('Checking javascript files...');
  window.adjustEditPane();  // Calculate initial size.
  //save global reference to iframe
  IFRAME = document.getElementById(IFRAMENAME);
  //remove older versions of sdk
  var editDoc = WebExpress_getEditDocument();
  var scripts =  editDoc.getElementsByTagName('script');
  var sdkjs = new RegExp('sdk');
  var sdk2js = new RegExp('sdk2');
  for(var i=0;i<scripts.length;i++){
    if(sdkjs.test(scripts[i].src)) {
      if(!sdk2js.test(scripts[i].src)) {
        WEmsglog("WebExpress_startPhase3(), removing old sdk, src=" + scripts[i].src);
        scripts[i].parentNode.removeChild(scripts[i]);  
      }
    }
  } 
  //add required scripts
  WebExpress_add_scripts();
}

WebExpress_startPhase4.retryCount = 0;
function WebExpress_startPhase4() {
  WEmsglog("WebExpress_startPhase4(), at top");
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  if(WebExpress_startPhase4.retryCount < startRetryCount) {
    if(editWin.wz_dragdrop_loaded) {
      WebExpress_SET_DHTML();
      // IE
      var xaxis = document.getElementById('xaxis');
      var yaxis = document.getElementById('yaxis');
      var zaxis = document.getElementById('zaxis');
      if (document.all){
        xaxis.setAttribute('onkeypress',WebExpress_updateLocation);
        yaxis.setAttribute('onkeypress',WebExpress_updateLocation);
        zaxis.setAttribute('onkeypress',WebExpress_updateLocation);
      }
      else{
        yaxis.setAttribute('onkeypress','WebExpress_updateLocation(event)');
        xaxis.setAttribute('onkeypress','WebExpress_updateLocation(event)');
        zaxis.setAttribute('onkeypress','WebExpress_updateLocation(event)');
      }
      if(!(editWin.pageRefreshStarted == true)) {
        WEmsglog("WebExpress_startPhase4(), calling startPageRefresh()");
        editWin.startPageRefresh();
      }
      WebExpress_displayRefreshRate();
      WebExpress_msg(''); //clear message area
    }
    else {
      WebExpress_startPhase4.retryCount++;
      window.setTimeout("WebExpress_startPhase4()",100); //check every 100 ms.
    }
  }
  else {
    alert("Timeout initializing drag and drop library");
  }
}

function WebExpress_displayRefreshRate() {
    var editWin = document.getElementById(IFRAMENAME).contentWindow;
    var msecs = editWin.document.getElementById('WebExpressPageProps').getAttribute('refreshrate');
    var secs = msecs / 1000;
    document.getElementById('pagerefresh').value = secs + " seconds";
}

// returns all the div tags that are widget or part of drag and drop
function WebExpress_getDivs(myElement){
  var divs = myElement.getElementsByTagName('div');
  var rdivs = [];
   var i;
  for(i=0;i<divs.length;i++){
    if(divs[i].getAttribute('widget') || divs[i].getAttribute('webexpress_dd') ){
      rdivs[rdivs.length] = divs[i];
    }
  }
  return rdivs
}

function WebExpress_clean_href(el,re){
  try{
    var href = el.href.replace(re,'');
    el.href = href;  
  }
  catch(e){ 
    WEmsglog('Error:' + e.description);
  }

}

function WebExpress_clean_src(el,re){
  try{
    var src = el.src.replace(re,'');
    el.src = src;  
  }
  catch(e){ 
    WEmsglog('Error:' + e.description);
  }

}

function WebExpress_clean_style_background(el,re){
  try{
    var background = el.style.backgroundImage.replace(re,'');
    el.style.backgroundImage = null; 
    el.style.backgroundImage = background; 
 
  }
  catch(e){ 
    WEmsglog('Error:' + e.description);
  }

}

function WebExpress_remove_hostname(html_element){
  var host = window.location.host;
  var re = new RegExp('http:\/\/' + host,'g');
  var tags = new Array('img','a','div','script');
  var i = 0;
  var i2 = 0;
  for(i=0;i<tags.length;i++){
    var elements = html_element.getElementsByTagName(tags[i]);
    //alert(host + ": " + tags[i] + '.length=' + elements.length);
    for(i2=0;i2<elements.length;i2++){
      // href
      WebExpress_clean_href(elements[i2],re); 
      
      // src
      WebExpress_clean_src(elements[i2],re);
      
      // style.background
      WebExpress_clean_style_background(elements[i2],re);
      
    }
    
  }
  return html_element
}

var saveFileWinRef = null;
function WebExpress_SaveFileWin(){
  // IE, in IE you can't set onclick events to a string
  // you have to set it to a reference of a function 
  var w = '600';
  var h = '600';
  var features = "menubar=false;toolbar=false,height=1,width=1;resizeable,scrollbars";

  if(SHOWALLFILES == 'true') {
    saveFileWinRef = window.open("/webapi/fileSelector.html?openaftersave=true&selectfiles=all&savefunction=WebExpress_fileSelectorCloser&filename=" + FILE,
    "fileSelector",features);
  }
  else {
    saveFileWinRef = window.open("/webapi/fileSelector.html?openaftersave=true&selectfiles=html&savefunction=WebExpress_fileSelectorCloser&filename=" + FILE,
    "fileSelector",features);
  }
  
  var height = window.screen.availHeight;
  var width = window.screen.availWidth;
  var left_point = parseInt(width/2) - parseInt(w/2);
  var top_point =  parseInt(height/2) - parseInt(h/2);
  saveFileWinRef.moveTo(left_point,top_point);
  saveFileWinRef.resizeTo(w,h);
  saveFileWinRef.focus();
}

var helpWinRef = null;
function WebExpress_LaunchHelp(){
 // IE, in IE you can't set onclick events to a string
 // you have to set it to a reference of a function 
 var w = '600';
 var h = '600';
 var features = "menubar=true;toolbar=false,height=1,width=1;resizeable,scrollbars";
         
 helpWinRef = window.open("/webapi/WebExpressHelp.html","WebExpressHelp",features);
  
 var height = window.screen.availHeight;
 var width = window.screen.availWidth;
 var left_point = parseInt(width/2) - parseInt(w/2);
 var top_point =  parseInt(height/2) - parseInt(h/2);
 helpWinRef.moveTo(left_point,top_point);

 helpWinRef.resizeTo(w,h);
 helpWinRef.focus();
 
}

function WebExpress_needsClosingTag(el) {
  var closingTags = " head script style div span tr td tbody table em strong font a title ";
  return (closingTags.indexOf(" " + el.tagName.toLowerCase() + " ") != -1);
}

function WebExpress_needsHostNameClean(tagName, attributeName) {
  var cleanTags = " img a div script ";
  var cleanAttrs = " href src style ";
  return((cleanTags.indexOf(" " + tagName + " ") != -1) && (cleanAttrs.indexOf(" " + attributeName + " ") != -1));
}

var liveimgsindex = -1;
function WebExpress_getInnerHTML(objRef, n) {
    var obj;
    if (objRef) {
        if (typeof objRef == "string") {
            obj = document.getElementById(objRef);
        } else {
            obj = objRef;
        }
    } else {
        obj = (document.body.parentElement) ? 
            document.body.parentElement : document.body.parentNode;
    }

    //get imgs from edit document
    //will use for height and width attributes later
    //IE appears to have a bug that results in 0 values for some img attribute values in fragment
    var editDoc = WebExpress_getEditDocument();
    var liveimgs = editDoc.getElementsByTagName('img');

    var output = "";
    var i, j, group, txt;
    //if (n == 0) {
        //output += "Child Nodes of <" + obj.tagName .toLowerCase();
        //output += ">\n=====================\n";
    //}
    group = obj.childNodes;
    for (i = 0; i < group.length; i++) {
        switch (group[i].nodeType) {
            case 1: // Node.ELEMENT_NODE
		var myTag = group[i].tagName.toLowerCase();
		if(myTag == 'img') {
                  liveimgsindex++;
		}
                var closed = (!(group[i].hasChildNodes() || WebExpress_needsClosingTag(group[i])));
                output += "<" + group[i].tagName.toLowerCase();
		var attrs = group[i].attributes;
		for(j = 0; j < attrs.length; ++j) {
			var a = attrs.item(j);
			if(!a.specified) {
				continue;
			}
			var name = a.nodeName.toLowerCase();
			if(/_moz|contenteditable|_msh/.test(name)) { //strip certain unwanted attributes
				continue;
			}
			if(/ddobj/.test(name)) { //strip drag&drop attribute
				continue;
			}
			var value;
			if(name == 'onclick' || name == 'onload' || name == 'ondblclick') {
				var thisOnFunc = group[i][a.nodeName];
				// In IE, remove 'function anonymous () {' and '}' from thisOnClick
				// after changing it into a string by calling the toString() method
				value =
					thisOnFunc.toString().replace(/^([^\{]+)\{/g,'').replace(/\}$/,'').replace(/\n/g,'');
				output += " " + name + '=' + value;
				continue;
			}
			else if(name == 'style') {
				value = group[i].style.cssText;
			}
			else {
				//if(typeof group[i][a.nodeName] != 'undefined' && name != 'href' && name != 'src') {
				if(typeof group[i][a.nodeName] != 'undefined') {
					value = group[i][a.nodeName];
				}
				else {
					value = a.nodeValue;
				}
			}
			if(/(_moz|^$)/.test(value)) { //strip other unwanted attributes
				continue;
			}
			if(myTag == 'img' && name == 'height') {
                          //workaround possible IE bug
                          value = liveimgs[liveimgsindex].height;
			}
			if(myTag == 'img' && name == 'width') {
                          //workaround possible IE bug
                          value = liveimgs[liveimgsindex].width;
			}
			//remove protocol and hostname from certain URLs
			if(WebExpress_needsHostNameClean(myTag, name)) {
				var host = window.location.host;
				var re = new RegExp('http:\/\/' + host,'g');
				var tValue = value.replace(re,'');
				value = tValue;
			}
			output += " " + name + '="' + value + '"';
		}
		output += closed ? " />" : ">";
		if(group[i].childNodes.length > 0) {
			output += WebExpress_getInnerHTML(group[i], n+1);
		}
		if(!closed) {
			output += "</" + group[i].tagName.toLowerCase() + ">";
		}
                break;
            case 3: // Node.TEXT_NODE
		output += group[i].nodeValue;
                break;
            case 8: // Node.COMMENT_NODE
                output += "<!--" + group[i].nodeValue + "-->";
                break;
            default:
		//do nothing
		break;
        }
    }
    return output;
}

function WebExpress_save(filename, openfile){
  var msg;
  msg = "Do you really want to save?";
  if(confirm(msg)){
    var editDoc = WebExpress_getEditDocument();
    var html = editDoc.getElementsByTagName('html')[0];

    //hide widget borders in edit file
    var widgets = WebExpress_getDivs(html);
	var nodedisplays = new Array();
    for(var i=0;i<widgets.length;i++) {
      widgets[i].style.border = '0px none';
      var nodedisplay = Widget_get_element(widgets[i], 'div', 'nodedisplay');
      if (nodedisplay && !isNaN(Number(nodedisplay.innerHTML))) {
      	nodedisplays.push([nodedisplay, nodedisplay.innerHTML]);
      	nodedisplay.innerHTML = '####';
      }
    }

    //create temporary element in WebExpress document to hold copy of edit file
    var htmlHolder = html.cloneNode(true);

    //removed unwanted scripts from copy of edit file
    var scripts =  htmlHolder.getElementsByTagName('script');
    // Mozilla places JS_VERSION scripts in there for some reason
    // We just take them out
    var jsvers = new RegExp('JS_VERSION','g');
    var wzjs = new RegExp('wz_dragdrop');
    var wjs = new RegExp('\.wjs');
    for(var i = scripts.length - 1;i >= 0;i--){
      WEmsglog("WebExpress_save(), scripts[i].src=>" + scripts[i].src + "<");
      if(jsvers.test(scripts[i].innerHTML)) { //looking for JS_VERSION=1.3;
        WEmsglog("WebExpress_save(), found JS_VERSION");
        WEmsglog("WebExpress_save(), parentNode.tagName=" + scripts[i].parentNode.tagName);
        scripts[i].parentNode.removeChild(scripts[i]);  
      }
      if(wzjs.test(scripts[i].src)) { //looking for wz_dragdrop.js
        WEmsglog("WebExpress_save(), found wz_dragdrop");
        WEmsglog("WebExpress_save(), parentNode.tagName=" + scripts[i].parentNode.tagName);
        scripts[i].parentNode.removeChild(scripts[i]);  
      }
      if(wjs.test(scripts[i].src)) { //looking for unused .wjs scripts
        var found = false;
        for(var j = 0; j < widgets.length; j++) {
          var widgetwjs = new RegExp(widgets[j].getAttribute('widget') + '\.wjs');
          if(widgetwjs.test(scripts[i].src)) {
            WEmsglog("WebExpress_save(), found widget for this file");
            found = true;
            break;
          }
        }
        if(!found) {
          WEmsglog("WebExpress_save(), removing unused script " + scripts[i].src);
          WEmsglog("WebExpress_save(), parentNode.tagName=" + scripts[i].parentNode.tagName);
          scripts[i].parentNode.removeChild(scripts[i]);  
        }
      }
    } //end for each script

    liveimgsindex = -1;
    var head_text = WebExpress_getInnerHTML(
		        htmlHolder.getElementsByTagName('head')[0],0
			);
    var outer_html = editDoc.body.outerHTML;
    if (outer_html == undefined) {
      // IE, Safari & Chrome supports outerHTML:
      outer_html = "<body";
      for(var i=0; i<editDoc.body.attributes.length; i++) {
        var attr = editDoc.body.attributes[i];
        outer_html += " " + attr.name + "=\"" + attr.value + "\"";
      }
      outer_html += ">" + editDoc.body.innerHTML + "</body>";
    }
    //add document type for IE backwards compatibility (NN quirks)
    htmlHolder = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">' +
      '<html><head>' + head_text + '</head>' +
      outer_html + '</html>';
    //remove WebExpress server protocol and host information
    var loc = window.location;
    var re = new RegExp(loc.protocol+'\/\/' + loc.host,'g');
    htmlHolder = htmlHolder.replace(re,'');

    //do async PUT of file using XMLRPC interface
    WebExpress_request = null; //cleanup any previous request
    WebExpress_request = new MediatorXMLRPCRequest("WebExpress_reload");
    if(openfile) {
      WebExpress_request.setChangeHandler(WebExpress_save_status_with_open);
    }
    else {
      WebExpress_request.setChangeHandler(WebExpress_save_status);
    }
    
    var url = loc.protocol + '//' + loc.host + '/' + filename;
    SAVEDFILEURL = url;
    SAVEDFILENAME = filename;
    WebExpress_request.setURL(url);
    WebExpress_request.setMethod("PUT");
    WebExpress_request.create();
    WebExpress_request.open();
    WebExpress_request.send(htmlHolder);

    //Set all the widget borders back in edit file
    for(var i=0;i<widgets.length;i++){
      widgets[i].style.border = WIDGET_BORDER ;
    } 
    
    for (var i = 0; i < nodedisplays.length; i++) {
    	var elem_value = nodedisplays[i];
    	elem_value[0].innerHTML = elem_value[1];
    }

    return true;
  }
  else{
    WebExpress_msg('Save Canceled');
    return false;
  }
}

function WebExpress_reload(){
  //alert("File save complete");
}

function WebExpress_save_status(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    WEmsglog("WebExpress_save_status(), readyState=" + currentState);
    if (currentState == 4){
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204 
      var currentStatus = this.request.objXMLHTTP.status;
      WEmsglog("WebExpress_save_status(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        WebExpress_msg('File "'+  SAVEDFILENAME + '" was saved succesfully');
      } 
      else if(currentStatus == 201){
        WebExpress_msg('New file was created!');  
      }
      else{ 
        if(HTTP_ERRORS[currentStatus] != null){
          WebExpress_msg('Error: File was not saved!<br>');
          WebExpress_msg(HTTP_ERRORS[currentStatus]);
        }
        else{
          WebExpress_msg('Error: File was not saved!<br>');
          WebExpress_msg('Status Code:' + currentStatus);
        }   
      }
      if(this.request.bAsync == true) {
        clearTimeout(this.timer); //stop async timeout
        WEmsglog("WebExpress_save_status(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.timer = null;
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    WEmsglog("WebExpress_save_status(), error: " + ex.name + ", " + ex.description);
  }
}

function WebExpress_save_status_with_open(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    WEmsglog("WebExpress_save_status_with_open(), readyState=" + currentState);
    if (currentState == 4){
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204 
      var currentStatus = this.request.objXMLHTTP.status;
      WEmsglog("WebExpress_save_status_with_open(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        WebExpress_msg('File "'+  SAVEDFILENAME + '" was saved succesfully');
        window.setTimeout('WebExpress_openSavedFile()',1000);
      } 
      else if(currentStatus == 201){
        WebExpress_msg('New file was created!');  
        window.setTimeout('WebExpress_openSavedFile()',1000);
      }
      else{ 
        if(HTTP_ERRORS[currentStatus] != null){
          WebExpress_msg('Error: File was not saved!<br>');
          WebExpress_msg(HTTP_ERRORS[currentStatus]);
        }
        else{
          WebExpress_msg('Error: File was not saved!<br>');
          WebExpress_msg('Status Code:' + currentStatus);
        }   
      }
      if(this.request.bAsync == true) {
        clearTimeout(this.timer); //stop async timeout
        WEmsglog("WebExpress_save_status_with_open(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.timer = null;
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    WEmsglog("WebExpress_save_status_with_open(), error: " + ex.name + ", " + ex.description);
  }
}

function WebExpress_openSavedFile() {
  window.location = SAVEDFILEURL;
}

function WebExpress_DeleteFile(){
  var msg;
  msg = "Do you really want to delete?";
  if(FILE != 'NEWFILE') {
    if(confirm(msg)){
      var editDoc = WebExpress_getEditDocument();
      var widgets = WebExpress_getDivs(editDoc);
      //do async PUT of file using XMLRPC interface
      WebExpress_request = null; //cleanup any previous request
      WebExpress_request = new MediatorXMLRPCRequest();
      WebExpress_request.setChangeHandler(WebExpress_delete_status);
      var loc = window.location;
      var url = loc.protocol + '//' + loc.host + '/' + FILE;
      //SAVEDFILEURL = url;
      WebExpress_request.setURL(url);
      WebExpress_request.setMethod("DELETE");
      WebExpress_request.create();
      WebExpress_request.open();
      WebExpress_request.send('');

      //Set all the borders back
      for(var i=0;i<widgets.length;i++){
        widgets[i].style.border = WIDGET_BORDER ;
      } 
      WebExpress_msg('File Deleted!');
      window.setTimeout('WebExpress_goBackTwo()',1000);
      //return true;
    }
    else{
      WebExpress_msg('Delete Canceled');
      //return false;
    }
  }
}

function WebExpress_goBackTwo() {
  window.history.go(-2);
}

function WebExpress_delete_status(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    WEmsglog("WebExpress_delete_status(), readyState=" + currentState);
    if (currentState == 4){
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204 
      var currentStatus = this.request.objXMLHTTP.status;
      WEmsglog("WebExpress_delete_status(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        WebExpress_msg('File "'+  FILE + '" was deleted successfully');
        window.setTimeout('WebExpress_goBackTwo()',1000);
      } 
      else if(currentStatus == 201){
        WebExpress_msg('New file was created!');  
        window.setTimeout('WebExpress_goBackTwo()',1000);
      }
      else{ 
        if(HTTP_ERRORS[currentStatus] != null){
          WebExpress_msg('Error: File was not deleted!<br>');
          WebExpress_msg(HTTP_ERRORS[currentStatus]);
        }
        else{
          WebExpress_msg('Error: File was not deleted!<br>');
          WebExpress_msg('Status Code:' + currentStatus);
        }   
      }
      if(this.request.bAsync == true) {
        clearTimeout(this.timer); //stop async timeout
        WEmsglog("WebExpress_delete_status(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.timer = null;
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    WEmsglog("WebExpress_delete_status(), error: " + ex.name + ", " + ex.description);
  }
}

var FileOpsObjWin = null;

function WebExpress_FileOpsView() {
  var f = document.getElementById('theFile').value;   
  var myURL = window.location.protocol + '//' + window.location.host + '/' + f;
  var win = window.open(myURL,"WebExpressView");
}

function WebExpress_FileOpsCopy() {
  // IE, in IE you can't set onclick events to a string
  // you have to set it to a reference of a function 
  var w = '600';
  var h = '600';
  var features = "menubar=false;toolbar=false,height=1,width=1;resizeable,scrollbars";

  if(SHOWALLFILES == 'true') {
    FileOpsObjWin = window.open("/webapi/fileSelector.html?selectfiles=all&savefunction=WebExpress_FileOpsCopyCloser&filename=" +
      document.getElementById('theFile').value,"fileSelector",features);
  }
  else {
    FileOpsObjWin = window.open("/webapi/fileSelector.html?selectfiles=html&savefunction=WebExpress_FileOpsCopyCloser&filename=" +
      document.getElementById('theFile').value,"fileSelector",features);
  }

  var height = window.screen.availHeight;
  var width = window.screen.availWidth;
  var left_point = parseInt(width/2) - parseInt(w/2);
  var top_point =  parseInt(height/2) - parseInt(h/2);
  FileOpsObjWin.moveTo(left_point,top_point);
 
  FileOpsObjWin.resizeTo(w,h);
  FileOpsObjWin.focus();
 
}

function WebExpress_FileOpsCopyCloser() {
  var filename =  FileOpsObjWin.document.getElementById('file_name').value;
  //check for proper file name format before saving
  var htmAtEnd = (filename.length >= 4 && filename.slice(-4).toLowerCase() == '.htm') ? true : false;
  var htmlAtEnd = (filename.length >= 5 && filename.slice(-5).toLowerCase() == '.html') ? true : false;
  if(!(htmAtEnd || htmlAtEnd)) {
    alert('Filename must end with .htm or .html!');
  }
  else if(htmAtEnd && filename.length == 4){
    alert('Filename must have at least one character before .htm!');
  }
  else if(htmlAtEnd && filename.length == 5) {
    alert('Filename must have at least one character before .html!');
  }
  else if(filename == document.getElementById('theFile').value) {
    alert('Copy filename must be different from original filename!');
  }
  else {
    if (FileOpsObjWin.opener){
      if (filename == ''){
        alert('You must enter a file name to save the selection.');
      }
      else{
        //valid file name format
        FileOpsObjWin.close();
        FileOpsObjWin = null;
        WebExpress_FileOpsDoCopy(filename);
      }
    }
    else{
      alert('file name:' + filename);
    }
  }
}

function WebExpress_FileOpsDoCopy(toFile) {
  var msg;
  var fromFile = document.getElementById('theFile').value;
  msg = "Do you really want to copy?";
  if(fromFile != '.aaa' && fromFile != '') {
    if(confirm(msg)){
      //do async PUT of file using XMLRPC interface
      WebExpress_request = null; //cleanup any previous request
      WebExpress_request = new MediatorXMLRPCRequest('WebExpress_FileOpsCopyCompletion');
      WebExpress_request.setChangeHandler(WebExpress_FileOpsCopyStatus);
      var loc = window.location;
      var url = loc.protocol + '//' + loc.host + '/webapi/psp/filecopy.psp?tofile=' + toFile + '&fromfile=' + fromFile;
      //SAVEDFILEURL = url;
      SAVEDFILENAME = toFile;
      WebExpress_request.setURL(url);
      WebExpress_request.setMethod("GET");
      WebExpress_request.create();
      WebExpress_request.open();
      WebExpress_request.send('');

      //alert('File Copied!');
      //window.setTimeout('Admin_goBackTwo()',1000);
      //return true;
    }
    else{
      alert('Copy Canceled');
      //return false;
    }
  }
}

function WebExpress_FileOpsCopyCompletion(){
  //alert("File copy complete");
}

function WebExpress_FileOpsCopyStatus(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    WEmsglog("WebExpress_FileOpsCopyStatus(), readyState=" + currentState);
    if (currentState == 4){
      if(this.request.bAsync == true) {
        clearTimeout(this.timer); //stop async timeout
      }
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204 
      var currentStatus = this.request.objXMLHTTP.status;
      WEmsglog("WebExpress_FileOpsCopyStatus(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        alert('File "'+  document.getElementById('theFile').value + '" was copied to "' + SAVEDFILENAME + '" succesfully!');
        top.location.reload(true);
      } 
      else if(currentStatus == 201){
        alert('New file was created!');  
        top.location.reload(true);
      }
      else{ 
        if(HTTP_ERRORS[currentStatus] != null){
          alert('Error: File was not copied!<br>\n' + HTTP_ERRORS[currentStatus]);
        }
        else{
          alert('Error: File was not copied!\n' + 'Status Code:' + currentStatus);
        }   
      }
      if(this.request.bAsync == true) {
        WEmsglog("WebExpress_FileOpsCopyStatus(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.timer = null;
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    WEmsglog("WebExpress_FileOpsCopyStatus(), error: " + ex.name + ", " + ex.description);
  }
}

function WebExpress_FileOpsDelete() {
  var msg;
  var myFile = document.getElementById('theFile').value;
  msg = "Do you really want to delete?";
  if(myFile != '.aaa' && myFile !='') {
    if(confirm(msg)){
      //do async PUT of file using XMLRPC interface
      WebExpress_request = null; //cleanup any previous request
      WebExpress_request = new MediatorXMLRPCRequest('WebExpress_FileOpsDeleteCompletion');
      //WebExpress_request.setAsyncTimeout(250);
      WebExpress_request.setChangeHandler(WebExpress_FileOpsDeleteStatus);
      var loc = window.location;
      var url = loc.protocol + '//' + loc.host + '/' + myFile;
      //SAVEDFILEURL = url;
      WebExpress_request.setURL(url);
      WebExpress_request.setMethod("DELETE");
      WebExpress_request.create();
      WebExpress_request.open();
      WebExpress_request.send('');

      //WebExpress_msg('File Deleted!');
      //window.setTimeout('WebExpress_goBackTwo()',1000);
      //return true;
    }
  }
}

function WebExpress_FileOpsDeleteMultiple(deletefile) {
  if(deletefile != '.aaa' && deletefile !='') {
      //do async PUT of file using XMLRPC interface
      WebExpress_request = null; //cleanup any previous request
      WebExpress_request = new MediatorXMLRPCRequest('WebExpress_FileOpsDeleteMultipleCompletion');
      //WebExpress_request.setAsyncTimeout(250);
      WebExpress_request.setChangeHandler(WebExpress_FileOpsDeleteMultipleStatus);
      var loc = window.location;
      var url = loc.protocol + '//' + loc.host + '/' + deletefile;
      //SAVEDFILEURL = url;
      WebExpress_request.setURL(url);
      WebExpress_request.setMethod("DELETE");
      WebExpress_request.create();
      WebExpress_request.open();
      WebExpress_request.send('');
  }
}

function WebExpress_FileOpsDeleteMultipleCompletion(){
  //alert("File delete complete");
}

function WebExpress_FileOpsDeleteCompletion(){
  //alert("File delete complete");
}
function WebExpress_FileOpsDeleteStatus(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    WEmsglog("WebExpress_FileOpsDeleteStatus(), readyState=" + currentState);
    if (currentState == 4){
      if(this.request.bAsync == true) {
        clearTimeout(this.timer); //stop async timeout
      }
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204 
      var currentStatus = this.request.objXMLHTTP.status;
      WEmsglog("WebExpress_FileOpsDeleteStatus(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        alert('File "'+  document.getElementById('theFile').value + '" was deleted succesfully!');
        top.location.reload(true);
      } 
      else if(currentStatus == 201){
        alert('New file was created!');  
        top.location.reload(true);
      }
      else{ 
        if(HTTP_ERRORS[currentStatus] != null){
          alert('Error: File was not deleted!<br>\n' + HTTP_ERRORS[currentStatus]);
        }
        else{
          alert('Error: File was not deleted!\n' + 'Status Code:' + currentStatus);
        }   
      }
      if(this.request.bAsync == true) {
        WEmsglog("WebExpress_FileOpsDeleteStatus(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.timer = null;
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    WEmsglog("WebExpress_FileOpsDeleteStatus(), error: " + ex.name + ", " + ex.description);
  }
}

function WebExpress_FileOpsDeleteMultipleStatus(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    WEmsglog("WebExpress_FileOpsDeleteMultipleStatus(), readyState=" + currentState);
    if (currentState == 4){
      if(this.request.bAsync == true) {
        clearTimeout(this.timer); //stop async timeout
      }
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204 
      var currentStatus = this.request.objXMLHTTP.status;
      WEmsglog("WebExpress_FileOpsDeleteMultipleStatus(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        //alert('File "'+  document.getElementById('theFile').value + '" was deleted succesfully!');
        //top.location.reload(true);
      } 
      else if(currentStatus == 201){
        //alert('New file was created!');  
        //top.location.reload(true);
      }
      else if(currentStatus == 0){
        //do nothing, this is what is returned when timeout occurs?
      }
      else{ 
        if(HTTP_ERRORS[currentStatus] != null){
          alert('Error: File was not deleted!<br>\n' + HTTP_ERRORS[currentStatus]);
        }
        else{
          alert('Error: File was not deleted!\n' + 'Status Code:' + currentStatus);
        }   
      }
      if(this.request.bAsync == true) {
        WEmsglog("WebExpress_FileOpsDeleteMultipleStatus(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.timer = null;
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    WEmsglog("WebExpress_FileOpsDeleteMultipleStatus(), error: " + ex.name + ", " + ex.description);
  }
}

function WebExpress_clear_widget_colors(){
  var editDoc = WebExpress_getEditDocument();
  var divs = WebExpress_getDivs(editDoc);
  var i;
  for(i=0;i<divs.length;i++){
     divs[i].style.borderColor = 'blue';   
  }
}

function WebExpress_my_PickFunc(){
  CURRENT_ID = IFRAME.contentWindow.dd.obj.name;
  WebExpress_clear_widget_colors();
  var editDoc = WebExpress_getEditDocument();
  var dd = document.getElementById(IFRAMENAME).contentWindow.dd;
  editDoc.getElementById(dd.obj.name).style.borderColor = 'red';
  var x = document.getElementById('xaxis');
  var y = document.getElementById('yaxis');
  var z = document.getElementById('zaxis');
  var id =  document.getElementById('widget_id');
  var type =  document.getElementById('widget_type');
  id.innerHTML = dd.obj.name;
  // Might just be a drag and drop object
  if(editDoc.getElementById(dd.obj.name).getAttribute('widget')){
    type.innerHTML = editDoc.getElementById(dd.obj.name).getAttribute('widget');
  }
  else{
    type.innerHTML = '';
  }
  x.value = dd.obj.x;
  y.value = dd.obj.y;
  z.value = editDoc.getElementById(dd.obj.name).getAttribute('zindex');
  var element = eval('dd.elements.' + CURRENT_ID);
  element.setZ(editDoc.getElementById(dd.obj.name).getAttribute('zindex'));
  //debug stuff for window sizing
  WEmsglog("WebExpress_my_PickFunc(), editDoc.location=" + editDoc.location);
  if(document.compatMode) {
    WEmsglog("WebExpress_my_PickFunc(), editDoc.compatMode=" + editDoc.compatMode);
  }
  else {
    WEmsglog("WebExpress_my_PickFunc(), editDoc.compatMode undefined or null");
  }
  WEmsglog("WebExpress_my_PickFunc(), editDoc.body.offsetHeight=" + editDoc.body.offsetHeight + ", editDoc.body.offsetWidth=" + editDoc.body.offsetWidth);
  WEmsglog("WebExpress_my_PickFunc(), editDoc.body.scrollHeight=" + editDoc.body.scrollHeight + ", editDoc.body.scrollWidth=" + editDoc.body.scrollWidth);
  WEmsglog("WebExpress_my_PickFunc(), editDoc.body.clientHeight=" + editDoc.body.clientHeight + ", editDoc.body.clientWidth=" + editDoc.body.clientWidth);
  WEmsglog("WebExpress_my_PickFunc(), editDoc.body.parentNode.clientHeight=" + editDoc.body.parentNode.clientHeight + ", editDoc.body.parentNode.clientWidth=" + editDoc.body.parentNode.clientWidth);
  WEmsglog("WebExpress_my_PickFunc(), IFRAME.contentWindow.innerWidth=" + IFRAME.contentWindow.innerWidth + ", IFRAME.contentWindow.innerHeight=" + IFRAME.contentWindow.innerHeight + ", WndH=" + dd.getWndH() + ", WndW=" + dd.getWndW() + ", ScrollX=" + dd.getScrollX() + ", ScrollY=" + dd.getScrollY());
  if(dd.db) {
    WEmsglog("WebExpress_my_PickFunc(), dd.db=" + dd.db + ", dd.db.clientWidth=" + dd.db.clientWidth + ", dd.db.clientHeight=" + dd.db.clientHeight);
  }
  else {
    WEmsglog("WebExpress_my_PickFunc(), dd.db undefined or null");
  }
}

function WebExpress_my_DragFunc(){
  var x = document.getElementById('xaxis');
  var y = document.getElementById('yaxis');
  var dd = IFRAME.contentWindow.dd;
  x.value = dd.obj.x;
  y.value = dd.obj.y;
}

function WebExpress_my_DropFunc(){
  var editDoc = WebExpress_getEditDocument();
  var dd = IFRAME.contentWindow.dd;
  var element = eval('dd.elements.' + CURRENT_ID);
  element.setZ(editDoc.getElementById(dd.obj.name).getAttribute('zindex'));
}

function WebExpress_DeleteWidget(){
  var editDoc = WebExpress_getEditDocument();
  var editBody = editDoc.getElementsByTagName('body')[0];
  var msg = '';
  var element = editDoc.getElementById(CURRENT_ID);  
  if (CURRENT_ID != null){
    if (element.getAttribute('webexpress_dd') != null){
      msg = 'Element is not a widget, Are you sure you want to delete?';
    }
    else if(element.getAttribute('widget') != null){
      msg = 'Are you sure you want to delete widget with ID:' + element.getAttribute('id');
    }
    if(confirm(msg)){
      //set pagedirty so deleted widget is no longer refreshed
      var editWin = document.getElementById(IFRAMENAME).contentWindow;
      editWin.PAGE_PROPERTIES.setPageDirty(true);
      //delete widget
      editBody.removeChild(element);  
      WebExpress_clearCurrent();        
    }
  }
  else {
      alert('No widget selected for deletion, please select widget and try again.');
  }
}

function WebExpress_CopyWidget() {
  var widget;
  if (CURRENT_ID != null) {
    var editDoc = WebExpress_getEditDocument();
    var editBody = editDoc.getElementsByTagName('body')[0];
    var sourceElement = editDoc.getElementById(CURRENT_ID);

    //create new widget in editor window
    widget = eval('new ' + sourceElement.getAttribute('Widget') + '()');  
    if (widget.EDIT_DOC_HACK != undefined) {
      widget.edit_doc = editDoc;
    }
    widget.init(sourceElement);
    var config = widget.configuration();
    widget.configure(config);
    widget.create();
    var element = widget.get();
    element.style.position = 'absolute';
    element.style.top = '5px';
    element.style.left = '5px';

    newWidgetID = WebExpress_getID();
    element.setAttribute('id',newWidgetID);

    //create temporary div element in editor window to hold newly created widget
    var wrapper_element = null;
    if (widget.EDIT_DOC_HACK == undefined) {
      wrapper_element = document.createElement('div');
    } else {
      wrapper_element = element.ownerDocument.createElement('div');
    }
    wrapper_element.appendChild(element);
    WEmsglog("WebExpress_CopyWidget(), wrapper_element.innerHTML=" + wrapper_element.innerHTML);

    //add widget javascript file to edit document
    WebExpress_add_widget_script(editDoc,WebExpress_src_map[widget._name]);

    //create temporary div element in edit document to hold newly created widget
    newWidgetHolder = editDoc.createElement('div');
    newWidgetHolder.setAttribute('id','NewWidgetHolder');

    //copy widget from editor window to edit document
    newWidgetHolder.innerHTML = wrapper_element.innerHTML;
    WEmsglog("WebExpress_CopyWidget(), newWidgetHolder.innerHTML=" + newWidgetHolder.innerHTML);
    editBody.appendChild(newWidgetHolder);

    //set timeout to allow element creation to complete
    var iframe = document.getElementById(IFRAMENAME); 
    iframe.contentWindow.setTimeout("parent.WebExpress_CopyWidget_Phase2()",0);
  }
  else {
      alert('No widget selected for copy, please select widget and try again.');
  }
}

function WebExpress_CopyWidget_Phase2() {
  WEmsglog("WebExpress_CopyWidget_Phase2(), newWidgetID=" + newWidgetID);
  var editDoc = WebExpress_getEditDocument();
  var editBody = editDoc.getElementsByTagName('body')[0];
  var newElem = editDoc.getElementById(newWidgetID);

  //move new widget from holder to body
  editBody.appendChild(newElem);

  //set timeout to allow element creation to complete
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.setTimeout("parent.WebExpress_CopyWidget_Phase3()",0);
}

function WebExpress_CopyWidget_Phase3() {
  WEmsglog("WebExpress_CopyWidget_Phase3(), newWidgetID=" + newWidgetID);
  var editDoc = WebExpress_getEditDocument();
  var sourceElement = editDoc.getElementById(CURRENT_ID);
  var newElement = editDoc.getElementById(newWidgetID);

  //make new widget draggable
  WebExpress_ADD_DHTML(newWidgetID);

  //get rid of temporary div element in edit document
  var editDoc = WebExpress_getEditDocument();
  var editBody = editDoc.getElementsByTagName('body')[0];
  var elem = editDoc.getElementById('NewWidgetHolder');
  editBody.removeChild(elem);

  //set pagedirty so new widget is refreshed
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.PAGE_PROPERTIES.setPageDirty(true);
}

function WebExpress_clearCurrent(){
   CURRENT_ID = null;
   document.getElementById('xaxis').value ='';
   document.getElementById('yaxis').value = '';
   document.getElementById('zaxis').value = '';
   document.getElementById('widget_id').innerHTML = '';
   document.getElementById('widget_type').innerHTML = '';
}
 
function WebExpress_ConfigureWidget(){  
  var doc = WebExpress_getEditDocument();
  if (CURRENT_ID != null){
    var element =  doc.getElementById(CURRENT_ID);
    if (element.getAttribute('widget') != null){
      var src = WebExpress_src_map[element.getAttribute('widget')];
      var features = "scrollbars,resizable,height=1,width=1";     
      var win = window.open("/webapi/webexpress_config.html?id=" + CURRENT_ID + 
			'&showallfiles=' + SHOWALLFILES +
                            '&src=' + src  ,"WebExpressConfigure",features);
      center_window(win,"700","700");
      CURRENT_ELEMENT = element;  
    }
    else{
      alert('Element is not a widget and can not be configured');
    }
  }
  else{
    alert('No widget selected.');
  }
}

function WebExpress_ConfigurePage(){  
  var features = "scrollbars,resizable,height=1,width=1";     
  var win = window.open("/webapi/webexpress_configpage.html","WebExpressConfigurePage",features);
  center_window(win,"700","700");
}


function WebExpress_updateLocation(e){
  var RETURN_KEY = 13;
  var editDoc = WebExpress_getEditDocument();
  if(!e){
    var e = window.event;
  }
  if(e.keyCode == RETURN_KEY){    
    var x = document.getElementById('xaxis').value;
    var y = document.getElementById('yaxis').value;
    var z = document.getElementById('zaxis').value;
    var dd = IFRAME.contentWindow.dd;
    var element = eval('dd.elements.' + CURRENT_ID);
    element.moveTo(x,y);
    editDoc.getElementById(element.name).setAttribute('zindex',z);
    editDoc.getElementById(element.name).style.zIndex = z;
  }
} 

function WebExpress_fileSelectorCloser() {
  var filename =  saveFileWinRef.document.getElementById('file_name').value;
  //check for proper file name format before saving
  var htmAtEnd = (filename.length >= 4 && filename.slice(-4).toLowerCase() == '.htm') ? true : false;
  var htmlAtEnd = (filename.length >= 5 && filename.slice(-5).toLowerCase() == '.html') ? true : false;
  if(!(htmAtEnd || htmlAtEnd)) {
    alert('Filename must end with .htm or .html!');
  }
  else if(htmAtEnd && filename.length == 4){
    alert('Filename must have at least one character before .htm!');
  }
  else if(htmlAtEnd && filename.length == 5) {
    alert('Filename must have at least one character before .html!');
  }
  else {
    if (saveFileWinRef.opener){
      if (filename == ''){
        alert('You must enter a file name to save the file.');
      }
      else{
        //valid file name format
        if((saveFileWinRef.document.getElementById('opensavedfile') != null) && saveFileWinRef.document.getElementById('opensavedfile').checked) {
          var doFileOpen = true;
        }
        else {
          var doFileOpen = false;
        }
        if(WebExpress_save(filename, doFileOpen)) {
          saveFileWinRef.close();
          saveFileWinRef = null;
        }
      }
    }
    else{
      alert('file name:' + filename);
    }
  }
}

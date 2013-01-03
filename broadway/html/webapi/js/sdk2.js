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
 *
 * Purpose: Web API SDK, backwards compatible with sdk2.js
 *          this version implements asynchronous I/O
 *          by using the subscription manager.
 * Version: $Revision: 20101 $
 */

var SDK_debug_enabled = false; /* Add property to enable? */
var SDK_trace_enabled = false; /* Add property to enable? */
var Version_debug = false;

var SDK_trace_ignore = {
  "Deadband" : true,
  "Deadband.prototype.threshold" : true,
  "ENoActiveX" : true,
  "ENoSuchName" : true,
  "ENotLoggedIn" : true,
  "ERequestException" : true,
  "ERequestException.prototype.toString" : true,
  "ErrorResult" : true,
  "ErrorResult.prototype.toString" : true,
  "Log" : true,
  "Log.prototype.get_column_names" : true,
  "Log.prototype.get_range" : true,
  "MSXMLResult" : true,
  "MSXMLResult.prototype._get_array" : true,
  "MSXMLResult.prototype._get_double" : true,
  "MSXMLResult.prototype._get_fault" : true,
  "MSXMLResult.prototype._get_int" : true,
  "MSXMLResult.prototype._get_name" : true,
  "MSXMLResult.prototype._get_result" : true,
  "MSXMLResult.prototype._get_string" : true,
  "MSXMLResult.prototype._get_struct" : true,
  "MSXMLResult.prototype._get_value" : true,
  "MSXMLResult.prototype.get_result" : true,
  "Mediator" : true,
  "Mediator.prototype.get_node" : true,
  "Mediator.prototype.get_nodes" : true,
  "Mediator.prototype.get_target" : true,
  "Mediator.prototype.login" : true,
  "Mediator.prototype.logout" : true,
  "Mediator.prototype.set_target" : true,
  "MediatorLoginCompletion" : true,
  "MediatorXMLRPCRequest" : true,
  "MediatorXMLRPCRequest.prototype.completionHandler" : true,
  "MediatorXMLRPCRequest.prototype.create" : true,
  "MediatorXMLRPCRequest.prototype.getChangeHandler" : true,
  "MediatorXMLRPCRequest.prototype.getMethod" : true,
  "MediatorXMLRPCRequest.prototype.getNotifyFunction" : true,
  "MediatorXMLRPCRequest.prototype.getURL" : true,
  "MediatorXMLRPCRequest.prototype.onChangeHandler" : true,
  "MediatorXMLRPCRequest.prototype.open" : true,
  "MediatorXMLRPCRequest.prototype.parseResults" : true,
  "MediatorXMLRPCRequest.prototype.send" : true,
  "MediatorXMLRPCRequest.prototype.setChangeHandler" : true,
  "MediatorXMLRPCRequest.prototype.setMethod" : true,
  "MediatorXMLRPCRequest.prototype.setNotifyFunction" : true,
  "MediatorXMLRPCRequest.prototype.setURL" : true,
  "MpxException" : true,
  "MpxException.prototype.toString" : true,
  "Node" : true,
  "Node.prototype.children_names" : true,
  "Node.prototype.configuration" : true,
  "Node.prototype.get" : true,
  "Node.prototype.get_child" : true,
  "Node.prototype.has_child" : true,
  "Node.prototype.set" : true,
  "EntityManager" : true,
  "EntityManager.prototype.resolve_mount_paths" : true,
  "Nodes" : true,
  "Nodes.prototype.add_node" : true,
  "Nodes.prototype.get" : true,
  "Nodes.prototype.get_async" : true,
  "Nodes.prototype.subscription_create_polled" : true,
  "Nodes.prototype.subscription_destroy" : true,
  "Nodes.prototype.subscription_poll_changed" : true,
  "PageProperties" : true,
  "PageProperties.prototype.getPageDirty" : true,
  "PageProperties.prototype.get_mediator" : true,
  "PageProperties.prototype.get_refresh_rate" : true,
  "PageProperties.prototype.get_user_name" : true,
  "PageProperties.prototype.get_user_password" : true,
  "PageProperties.prototype.setPageDirty" : true,
  "PageProperties.prototype.set_mediator" : true,
  "PageProperties.prototype.set_refresh_rate" : true,
  "PageProperties.prototype.set_user_name" : true,
  "PageProperties.prototype.set_user_password" : true,
  "PageProperties.prototype.start" : true,
  "PageProperties.prototype.stop" : true,
  "RelayDriver" : true,
  "RelayDriver.prototype.get_min_off_time" : true,
  "RelayDriver.prototype.get_min_on_time" : true,
  "RelayDriver.prototype.set_min_off_time" : true,
  "RelayDriver.prototype.set_min_on_time" : true,
  "XMLHTTPResult" : true,
  "XMLHTTPResult.prototype._get_array" : true,
  "XMLHTTPResult.prototype._get_double" : true,
  "XMLHTTPResult.prototype._get_fault" : true,
  "XMLHTTPResult.prototype._get_int" : true,
  "XMLHTTPResult.prototype._get_name" : true,
  "XMLHTTPResult.prototype._get_result" : true,
  "XMLHTTPResult.prototype._get_string" : true,
  "XMLHTTPResult.prototype._get_struct" : true,
  "XMLHTTPResult.prototype._get_value" : true,
  "XMLHTTPResult.prototype.get_result" : true,
  "XMLRPCMessage" : true,
  "XMLRPCMessage.dataTypeOf" : true,
  "XMLRPCMessage.doArrayXML" : true,
  "XMLRPCMessage.doBooleanXML" : true,
  "XMLRPCMessage.doDateXML" : true,
  "XMLRPCMessage.doStructXML" : true,
  "XMLRPCMessage.doValueXML" : true,
  "XMLRPCMessage.getParamXML" : true,
  "XMLRPCMessage.prototype.addParameter" : true,
  "XMLRPCMessage.prototype.setMethod" : true,
  "XMLRPCMessage.prototype.xml" : true,
  "_check_login_status" : true,
  "_refresh_loop" : true,
  "as_deadband" : true,
  "as_log" : true,
  "as_relay_driver" : true,
  "center" : true,
  "dateToISO8601" : true,
  "delete_cookie" : true,
  "getCompleted" : true,
  "getMediatorXMLRPCState" : true,
  "getXmlHttpPrefix" : true,
  "get_cookie" : true,
  "get_elements" : true,
  "get_query_string_args" : true,
  "leadingZero" : true,
  "login_success" : true,
  "login_window" : true,
  "precision" : true,
  "refresh_elements" : true,
  "set_cookie" : true,
  "resolve_path" : true,
  "get_url_param": true,
  "start_refresh_loop" : true,
  "stop_page_refresh" : true,
  "update_changed_elements" : true,
  "update_element" : true,
  "update_elements" : true,
  "window_error" : true,
  "zzEnd" : true // Cheesy goodness that makes it easy to sort the list...
};

// Get noisy!
// SDK_trace_ignore = {};

var SDK_console = null;

String.prototype.startsWith = function(str) {return (this.match("^" + str) == str)}
String.prototype.endsWith = function(str) {return (this.match(str + "$") == str)}

function SDK_log(text){
  if (SDK_debug_enabled) {
    var now = new Date();
    var msg = now.toLocaleString() + ": " + String(text);
    try {
      if (window.console) {
	/* Safari */
	window.console.log(msg);
      }
      else {
	/* Everybody else, try using a window with a text/plain document. */
	try {
	  if ((SDK_console == null) || (SDK_console.closed)) {
	    SDK_console = window.open("", "SDK_log",
				      "width=600,height=300,resizable" +
				      ",scrollbars=yes");
	    SDK_console.document.open("text/plain");
	  }
	  SDK_console.document.writeln(msg);
	}
	catch (err) {
	  // alert(SDK_error_string(err));
	  /* OK, that failed. Try a pop-up.*/
	  alert(msg);
	}
      }
    }
    catch(err) {
      // alert(SDK_error_string(err));
    }
  }
}

function SDK_log_error(e) {
  SDK_log(SDK_error_string(e));
}

function SDK_error_string(e) {
  var stack = e.stack;
  var result = (e.name == null) ? "Unknown Error" : e.name ;
  if (e.message != null) {
    result += ": " + e.message;
  }
  if (e.fileName != null) {
    result += "\n  File: " + e.fileName;
    if (e.lineNumber != null) {
      result += ":" + String(e.lineNumber);
    }
  }
  return result;
}

function SDK_repr(o) {
  t = typeof(o);
  switch (t) {
  case "number":
    return String(o);
  case "string":
    var scratch = o;
    scratch = scratch.replace(RegExp('"','g'),'\\"');
    scratch = scratch.replace(RegExp('\n','g'),'\\n');
    return '"' + scratch + '"';
  case "undefined":
    return t;
  case "object":
    if (o == null) {
      return "null";
    }
    if (o.length == undefined) {
      return SDK_repr_as_associative_array(o);
    }
    return SDK_repr_as_simple_array(o);
  }
  return "unknown type: " + t;
}

function SDK_repr_as_associative_array(a) {
  var result = "{";
  var prev_separator = "";
  for (k in a) {
    result += prev_separator;
    result += String(k);
    result += ":";
    result += SDK_repr(a[k]);
    prev_separator = ", ";
  }
  result += "}";
  return result;
}

function SDK_repr_as_simple_array(a) {
  var result = "[";
  var prev_separator = "";
  for (k in a) {
    result += prev_separator;
    result += SDK_repr(a[k]);
    prev_separator = ", ";
  }
  result += "]";
  return result;
}

function SDK_props(e, onePerLine)
{
  if (e === null) {
    SDK_log("SDK_props called with null argument");
    return;
  }

  if (e === undefined) {
    SDK_log("SDK_props called with undefined argument");
    return;
  }

  var ns = ["Methods", "Fields", "Unreachables"];
  var as = [[], [], []]; // array of (empty) arrays of arrays!
  var p, j, i; // loop variables, several used multiple times

  var protoLevels = 0;

  for (p = e; p; p = p.__proto__)
  {
    for (i=0; i<ns.length; ++i)
      as[i][protoLevels] = [];
    ++protoLevels;
  }

  for(var a in e)
  {
    // Shortcoming: doesn't check that VALUES are the same in object and prototype.

    var protoLevel = -1;
    try
    {
      for (p = e; p && (a in p); p = p.__proto__)
        ++protoLevel;
    }
    catch(er) { protoLevel = 0; } // "in" operator throws when param to SDK_props() is a string

    var type = 1;
    try
    {
      if ((typeof e[a]) == "function")
        type = 0;
    }
    catch (er) { type = 2; }

    as[type][protoLevel].push(a);
  }

  function times(s, n) { return n ? s + times(s, n-1) : ""; }

  for (j=0; j<protoLevels; ++j)
    for (i=0;i<ns.length;++i)
      if (as[i][j].length)
        SDK_log(ns[i] + times(" of prototype", j) + ": " +
		(onePerLine ? "\n\n" : "") +
		as[i][j].sort().join(onePerLine ? "\n" : ", ") +
		(onePerLine ? "\n\n" : ""));
}

SDK_log("Loaded sdk2sm.js");

SDK_sid = null;
SDK_nodes = null;

function SDK_trace(name) {
  if (SDK_trace_enabled && SDK_trace_ignore[name] != true) {
    SDK_log(name);
  }
}

var refresh_engine = {
  /*
   * CONSTANTS:
   *
   * Refresh States:
   */
  INIT:0,
  CREATE_NODE_REFERENCE_TABLE:1,
  CREATE_POLLED_SUBSCRIPTION:2,
  POLL_CHANGES:3,
  /*
   * VARIABLES:
   */
  state:0
};

function window_error(e){
  SDK_trace("window_error");
  //alert("Javascript Error has occured!:\nERROR:" + e)
  return false;
}

window.onerror = window_error;
// Test for the correct Javascript
try{
  var h = document.getElementsByTagName("head")[0];
  var s;
  var JS_VERSION = 0;
  var  JS_VERSION_NEEDED = 1.3;
  s = document.createElement("script");
  s.setAttribute("language","javascript" + JS_VERSION_NEEDED);
  s.innerHTML = "JS_VERSION=" + JS_VERSION_NEEDED + ";";
  h.appendChild(s);
}
catch(e){
  var msg = "";
  for(m in e){
    msg = msg + " " + eval("e." + m) + "\n";
  }
  if (Version_debug == true){
    alert(msg);
  }
}

/********************************************************************
Exception Section
********************************************************************/

function MpxException(e){
  SDK_trace("MpxException");
  this.error = e;
  this.description = '';
  this.name = 'MpxException';
  this.type = 'MpxException';
  if(arguments.length > 1){
    this.description = arguments[1];
  }
}
MpxException.prototype.toString = function(){
  SDK_trace("MpxException.prototype.toString");
  return  "Error: " + this.error;
};

function ENoSuchName(e){
  SDK_trace("ENoSuchName");
  this.base = MpxException;
  this.base(e);
}

ENoSuchName.prototype = MpxException;

function ENotLoggedIn(e){
  SDK_trace("ENotLoggedIn");
  this.base = MpxException;
  this.base(e);
  this.name = 'ENotLoggedIn';
}
ENotLoggedIn.prototype = new MpxException;

//@@
// @function PageProperties
// @param mediator a mediator object
// @param refresh_rate the current refresh rate in milliseconds
// @param page_info_id the id attribute of div used to store properties
// @return null
// @note use the new method Example: var page_properties = new PageProperties(mediator,refresh_rate,page_info_id)
function PageProperties(mediator,refresh_rate,page_info_id){
  SDK_trace("PageProperties");
  switch(arguments.length) {
    case 1:
      this._refresh_rate = 2000;
      this._user_name = '';
      this._user_password = '';
      break;
    case 2:
      this._refresh_rate = arguments[1];
      this._user_name = '';
      this._user_password = '';
      break;
    case 3:
      this.element = null;
      this.element = document.getElementById(page_info_id);
      if(this.element) { //element found
	//alert("pageproperties element found");
        this._refresh_rate = this.element.getAttribute('refreshrate');
        this._user_name = this.element.getAttribute('username');
        this._user_password = this.element.getAttribute('userpassword');
      }
      else {
        this._refresh_rate = 2000;
        this._user_name = '';
        this._user_password = '';
        this.element = document.createElement('div');
        this.element.setAttribute('id',page_info_id);
        this.element.setAttribute('refreshrate',this._refresh_rate);
        this.element.setAttribute('username',this._user_name);
        this.element.setAttribute('userpassword',this._user_password);
        this.element.style.position = 'absolute';
        this.element.style.visibility = 'hidden';
        this.element.style.display = 'none';
        document.body.appendChild(this.element);
      }
      break;
    default:
      alert("PageProperties(), bad argument count");
      break;
  }
  this.mediator = mediator;
  this.timeout = null;
  this.nodeLen = 0;
  this.pagedirty = true;
  this.refresh = true;
}

//@@
// @method stop
// stops the page from refreshing
// @return null
PageProperties.prototype.stop = function(){
  SDK_trace("PageProperties.prototype.stop");
  this.refresh = false;
};

//@@
// @method start
// starts the page refreshing
// @return null
PageProperties.prototype.start = function(){
  SDK_trace("PageProperties.prototype.start");
  this.refresh = true;
};

//@@
// @method getPageDirty
// gets the page dirty status
// @return pagedirty
// @note boolean return value
PageProperties.prototype.getPageDirty = function(){
  SDK_trace("PageProperties.prototype.getPageDirty");
  return this.pagedirty;
};

//@@
// @method setPageDirty
// sets the page dirty status
// @param boolean
// @return null
PageProperties.prototype.setPageDirty = function(value){
  SDK_trace("PageProperties.prototype.setPageDirty");
  this.pagedirty = value;
};

//@@
// @method get_refesh_rate
// gets the refresh rate
// @return refresh rate
// @note in milliseconds
PageProperties.prototype.get_refresh_rate = function(){
  SDK_trace("PageProperties.prototype.get_refresh_rate");
  return this._refresh_rate;
};

//@@
// @method set_refesh_rate
// sets the refresh rate
// @param refresh_rate new refresh rate in milliseconds
// @return null
// @note in milliseconds
PageProperties.prototype.set_refresh_rate = function(rr){
  SDK_trace("PageProperties.prototype.set_refresh_rate");
  this._refresh_rate = rr;
  this.element.setAttribute('refreshrate',this._refresh_rate);
};

//@@
// @method get_user_name
// gets the username
// @return username
PageProperties.prototype.get_user_name = function(){
  SDK_trace("PageProperties.prototype.get_user_name");
  return this._user_name;
};

//@@
// @method set_user_name
// sets the username
// @param name
// @return null
PageProperties.prototype.set_user_name = function(name){
  SDK_trace("PageProperties.prototype.set_user_name");
  this._user_name = name;
  this.element.setAttribute('username',this._user_name);
};

//@@
// @method get_user_password
// gets the userpassword
// @return userpassword
PageProperties.prototype.get_user_password = function(){
  SDK_trace("PageProperties.prototype.get_user_password");
  return this._user_password;
};

//@@
// @method set_user_password
// sets the userpassword
// @param password
// @return null
PageProperties.prototype.set_user_password = function(password){
  SDK_trace("PageProperties.prototype.set_user_password");
  this._user_password = password;
  this.element.setAttribute('userpassword',this._user_password);
};

//@@
// @method get_mediator
// returns the mediator object
// @return object
PageProperties.prototype.get_mediator = function(){
  SDK_trace("PageProperties.prototype.get_mediator");
  return this.mediator;
};

//@@
// @method set_mediator
// sets the medaitor object used to refresh page
// @param mediator the mediator object
PageProperties.prototype.set_mediator = function(m){
  SDK_trace("PageProperties.prototype.set_mediator");
  this.mediator = m;
};

var PAGE_PROPERTIES = null;

/********************************************************************
Helper Function Section
********************************************************************/

//Cookies Section

//@@
// @function set_cookie
// This will set a cookie with the parameters provided
// @param name name of the cookie
// @param value value of the cookie
// @param [expires] expiration date of the cookie (defaults to end of current session)
// @param [path] path for which the cookie is valid (defaults to path of calling document)
// @param [domain] domain for which the cookie is valid (defaults to domain of calling document)
// @param [secure] boolean value indicating if the cookie transmission requires a secure transmission
// @note an argument defaults when it is assigned null as a placeholder
// @note a null placeholder is not required for trailing omitted arguments
function set_cookie(name, value, expires, path, domain, secure) {
  SDK_trace("set_cookie");
  var curCookie = name + "=" + escape(value) +
      ((expires) ? "; expires=" + expires.toGMTString() : "") +
      ((path) ? "; path=" + path : "") +
      ((domain) ? "; domain=" + domain : "") +
      ((secure) ? "; secure" : "");
  document.cookie = curCookie;
}

//@@
// @function get_cookie
// return string containing value of specified cookie or null if cookie does not exist
// @param name name of the desired cookie
// @return string or null
function get_cookie(name) {
  SDK_trace("get_cookie");
  var dc = document.cookie;
  var prefix = name + "=";
  var begin = dc.indexOf("; " + prefix);
  if (begin == -1) {
    begin = dc.indexOf(prefix);
    if (begin != 0) return null;
  }
  else{
    begin += 2;
    var end = document.cookie.indexOf(";", begin);
    if (end == -1){
      end = dc.length;
    }
  }
  return unescape(dc.substring(begin + prefix.length, end));
}

//@@
// @function delete_cookie
// deletes the cookie :
// @param name name of the cookie
// @param [path] path of the cookie (must be same as path used to create cookie)
// @param [domain] domain of the cookie (must be same as domain used to create cookie)
// @return null
// @note path and domain default if assigned null or omitted if no explicit argument proceeds
function delete_cookie(name, path, domain) {
  SDK_trace("delete_cookie");
  if (get_cookie(name)) {
    document.cookie = name + "=" +
    ((path) ? "; path=" + path : "") +
    ((domain) ? "; domain=" + domain : "") +
    "; expires=Thu, 01-Jan-70 00:00:01 GMT";
  }
}

//@@
// @function center
//
// takes the window object and centers the window and sets focus to the window
// @param objWin a window object refrenece
// @param width width of the window
// @param height height of the window
// @return null
function center(objWin,w,h){
  SDK_trace("center");
  var height = window.screen.availHeight;
  var width = window.screen.availWidth;
  var left_point = parseInt(width/2) - parseInt(w/2);
  var top_point =  parseInt(height/2) - parseInt(h/2);
  objWin.moveTo(left_point,top_point);
  objWin.resizeTo(w,h);
  objWin.focus();
}

//@@
// @function get_query_string_args
// returns an associative array of the query string arguments if any or  empty object
// @return associative array
function get_query_string_args(){
  SDK_trace("get_query_string_args");
  var args = new Object();
  var query_string = window.location.search.substring(1);
  var pairs = query_string.split("&");
  var name_value = null;
  for(x=0;x<pairs.length;x++){
    if (pairs[x].indexOf('=') != -1){
      name_value = pairs[x].split('=');
      args[name_value[0]] = decodeURIComponent(name_value[1]);
    }
  }
  return args;
}

/*******************************************************************
 * SDK Helper functions
 ******************************************************************/
//@@
// @function login_window
// opens a login window so the user can login
// @param get_mediator name of function to call to get a refrence to
// the mediator object
// @param callback name of the callback function you want called after
// login
// @note get_mediator and callback are strings to functions in your
// main page the login window uses the eval function to call your
// function
// @note  Example:  eval('window.opener.' + get_mediator + '()')
// @note  get_mediator should return a refrence to your mediator object
// @note  the callback function will be passed the mediator object
// that is logged in
// @return null
function login_window(get_mediator,callback){
  SDK_trace("login_window");
  var features = "menubar=false;toolbar=false,height=1,width=1";
  var win = window.open("/webapi/js/login.html?callback=" + callback + "&get_mediator=" + get_mediator
                    ,"login",features);
  center(win,"400","275");

}

//@@
// @function precision
// takes a float value and returns a float to the decimal places specified and then updates the given element
// @param element refrence to an HTML element
// @param value current value
// @param decimal_places the number of decimal_places to change to
// @param display_error value to display if there is an error
// @return null
function precision(e,v,decimal_places,display_error){
  SDK_trace("precision");
  var d_e = false;
  var args_len = arguments.length;
  //check arguments
  if(args_len < 3){
    decimal_places = 2;
  }
  else if(args_len == 4){
    d_e = display_error;
  }
  if (typeof(v) != "object" ){
    if(isNaN(v) == false){
      var x;
      var m;
      x = new Number(v);
      v = x.toFixed(decimal_places);
    }
  }
  update_element(e,v,d_e);
}

/********************************************************************
Mediator Section
********************************************************************/

//@@
// @function Mediator
// creates a mediator object to interact with
// @return null
// @note use the new method Example: var mediator = new Mediator()
function Mediator(){
  SDK_trace("Mediator");
  this.hostname = null;
  this.username = "";
  this.password = "";
  this.session = "";
  //If there are cookies for username and password try and login..
  if (get_cookie('username') != null && get_cookie('password') != null){
    try{
      this.login(get_cookie('username'),get_cookie('password'));
      this.username = get_cookie('username');
      this.password = get_cookie("password");
    }
    catch(e){
      delete_cookie("username");
      delete_cookie("password");
    }
  }
}

//@@
// @method set_target
// hostname of the machine you want to interact with
// @param hostname the hostname of the machine you want to interact with
// @example bob_m
// @return null
Mediator.prototype.set_target = function(hostname){
  SDK_trace("Mediator.prototype.set_target");
  this.hostname = hostname;
};

//@@
// @method get_target
// the hostname currently being used
// @return string
Mediator.prototype.get_target = function(){
  SDK_trace("Mediator.prototype.get_target");
  return this.hostname;
};

//@@
// @method get_node
// returns a node object
// @param path node path
// @example /services/time
// @return a Node object
Mediator.prototype.get_node = function(path, factory){
	factory = factory || Node;
	SDK_trace("Mediator.prototype.get_node");
	if(this.hostname != null){
		path = "mpx://" + this.hostname + path;
	}
	var node = new factory(this,path);
	return node;
};


//@@
// @method get_nodes
// returns a nodes object
// @param nodes array of node path
// @example ['/services/time,'/interfaces/com1...,etc]
// @return nodes object
Mediator.prototype.get_nodes =  function (n){
  SDK_trace("Mediator.prototype.get_nodes");
  var nodes = null;
  if (typeof(n) == "object"){
    nodes = new Nodes(this,n);
  }
  else{

    var args = "";
      for(x=0;x < arguments.length;x++){
        args +=  '"' + arguments[x] + '",';
      }
    args = args.substring(0,args.length-1);
    nodes = eval("new Nodes(this,"+ args +")");
  }
  return nodes;
};

function MediatorLoginCompletion() {
  SDK_trace("MediatorLoginCompletion");
  this.session = this.result;
}

//@@
// @method login
// logs into the host that is serving the webpages
// @param username username on the mediator that the webpage is being server from, not the target machine
// @param password users password
// @return a string that is the session
// @note The username is a user on the machine that the webpage is being served from, NOT the target machine
Mediator.prototype.login = function (/* Deprecated: username, password, */ completionHandlerName) {
  SDK_trace("Mediator.prototype.login");
  try{
    var request = null;
    var rna_call =  "rna_xmlrpc2:create_session";
    var msg = new XMLRPCMessage(rna_call);

    if (arguments.length > 1) {
    	var username = arguments[0];
    	var password = arguments[1];
        this.username = username;
    	this.password = password;
	    msg.addParameter(username);
	    msg.addParameter(password);
	    if (arguments.length == 3) {
	    	completionHandlerName = arguments[2];
	    }
    }
    var xml = msg.xml();
    if(typeof(completionHandlerName) != 'undefined') { //asynchronous
      request = new MediatorXMLRPCRequest(completionHandlerName);
      request.create();
      request.open();
      return request.send(xml);
    }
    else { //synchronous
      request = new MediatorXMLRPCRequest();
      request.create();
      request.open();
      try{
        this.session = request.send(xml);
      }
      catch(e){
	SDK_log_error(e);
        var err = e.error;
	if (err == undefined) {
	  throw e;
	}
        if(err.search('username') > -1){
          throw new MpxException(e.error,'username or password incorrect');
        }
        else{
          throw new MpxException(err,err);
        }
      }
    } //end else synchronous
  } //end try
  catch(e){
    if (e.type != null && e.type == "NoActiveX"){
      var features = "menubar=false;toolbar=false,height=1,width=1";
      var win = window.open("/webapi/js/activex_redirect.html","error",features);
      center(win,"500","300");
      return true;
    }
    else{
      throw e;
    }
  }
  return this.session;
};

//@@
// @method logout
// logs out of the current host
// @return null
Mediator.prototype.logout = function(){
  SDK_trace("Mediator.prototype.logout");
  this.session = "";
};

//@@
// @function Node
// creates a node to interact with
// @param mediator the mediator you use for this node
// @param path node path
// @return null
// @note use the new method Example: var node = new Node(mediator,path)
function Node(mediator,path){
  SDK_trace("Node");
  this.mediator = mediator;
  this.path = path;
}

//@@
// @method set
// sets the node to the value passed is
// @param value the new value
// @return null
Node.prototype.set =  function (v,completionHanderName){
  SDK_trace("Node.prototype.set");
  var rt = null;
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("set");
  msg.addParameter(v);
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method has_child
// returns true if node has chil
// @param child path to child
// @return boolean
Node.prototype.has_child =  function(child,completionHandlerName){
  SDK_trace("Node.prototype.has_child");
  var rt = "";
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("has_child");
  msg.addParameter(child);
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
    request.create();
    request.open();
    return request.send(xml);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
    request.create();
    request.open();
    return new Boolean(request.send(xml));
  }
};

//@@
// @method get_child
// returns a node for the child path passed in
// @param child path to child
// @return node
Node.prototype.get_child = function(child,completionHandlerName){
  SDK_trace("Node.prototype.get_child");
  var rt = "";
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("has_child");
  msg.addParameter(child);
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
    request.create();
    request.open();
    return request.send(xml);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
    request.create();
    request.open();
    rt = request.send(xml);
    if(rt == 1){
      var n = new Node(this.mediator,this.path + "/" + child);
    }
    else{
      throw new ENoSuchName('child path does not exsist');
    }
    return n;
  }
};

//@@
// @method children_names
// returns an array of children names
// @return array
Node.prototype.children_names = function(completionHandlerName){
  SDK_trace("Node.prototype.children_names");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("children_names");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method configuration
// returns an associative array of the current configuration
// @return associative array
Node.prototype.configuration = function(completionHandlerName){
  SDK_trace("Node.prototype.configuration");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("configuration");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

Node.prototype.get = function(completionHandlerName){
  SDK_trace("Node.prototype.get");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("get");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};


//@@
//@function EntityManager
//creates a specialized node to interact with
//@param mediator the mediator you use for this node
//@return null
function EntityManager(mediator){
	SDK_trace("EntityManager");
	this.mediator = mediator;
	this.path = "/services/Entity Manager";
}

//@@
//@method resolve_mount_paths
//returns the string translation\replacement
//@param entityPath the path to then entity of interest
//@return array
EntityManager.prototype.resolve_mount_paths = function(entityPath,completionHandlerName){
  SDK_trace("Node.prototype.set");
  var rt = null;
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("resolve_mount_paths");
  msg.addParameter(entityPath);
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

function _check_login_status(m){
  SDK_trace("_check_login_status");
  if (m.session == ""){
    throw new ENotLoggedIn('User not logged in');
  }
  else{
    return true;
  }
};


//@@
// @function Nodes
// an object that holds an array of nodes
// @param mediator the mediator to use to access all the nodes
// @return null
// @note use the new method Example: var nodes = new Nodes(mediator)
function Nodes(mediator){
  SDK_trace("Nodes");
  this.mediator = mediator;
  this.nodes = new Array();
  if (typeof(arguments[1]) == "object"){
    var nds = arguments[1];
    for(x=0;x<nds.length;x++){
      n = new Node(mediator,nds[x]);
      this.nodes[this.nodes.length] = n;
    }
  }
  else{
    var n = null;
    for(x=1;x< arguments.length;x++){
      n = new Node(mediator,arguments[x]);
      this.nodes[this.nodes.length] = n;
    }
  }
}

//@@
// @method add_node
// adds a node to the object
// @param node the node path to add to the object
// @return null
Nodes.prototype.add_node = function(n){
  SDK_trace("Nodes.prototype.add_node");
  this.nodes[this.nodes.length] = new Node(this.mediator,n);
};


//@@
// @method subscription_create_polled
// returns an SID to use to poll for changed values.
// @return A String representing the SID
Nodes.prototype.subscription_create_polled = function(completionHandlerName){
  SDK_trace("Nodes.prototype.subscription_create_polled");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:subscription_create_polled";
  var node_reference_table = {};

  _check_login_status(this.mediator);
  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  for (i = 0; i < this.nodes.length; i++) {
    node_reference_table[i] = this.nodes[i].path;
  }
  msg.addParameter(node_reference_table);
  
  if(PAGE_PROPERTIES!=null){
	  var rate = PAGE_PROPERTIES._refresh_rate;
	  var rpcStateLength = MediatorXMLRPCStateLength;
	  var subTime = rate*rpcStateLength/1000;
	  if(subTime>120){
		  msg.addParameter(subTime);//converting to secs
	  }else{
		  msg.addParameter(120);
	  }
  }
  
  xml = msg.xml();
  if (arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

Nodes.prototype.subscription_destroy = function(completionHandlerName){
  SDK_trace("Nodes.prototype.subscription_destroy");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:subscription_destroy";

  _check_login_status(this.mediator);
  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(SDK_sid);
  xml = msg.xml();
  if (arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method subscription_poll_changed
// returns an SID to use to poll for changed values.
// @return A String representing the SID
Nodes.prototype.subscription_poll_changed = function(completionHandlerName){
  SDK_trace("Nodes.prototype.subscription_poll_changed");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:subscription_poll_changed";
  var node_reference_table = {};

  _check_login_status(this.mediator);
  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(SDK_sid);
  xml = msg.xml();
  if (arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method get
// returns and an array of values that represent the current values of all the nodes
// @return array
Nodes.prototype.get_async = function(completionHandlerName){
  SDK_trace("Nodes.prototype.get_async");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke_batch_async";

  _check_login_status(this.mediator);
  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  for (x = 0;x < this.nodes.length;x++){
    msg.addParameter(this.nodes[x].path +":get");
  }
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method get
// returns and an array of values that represent the current values of all the nodes
// @return array
Nodes.prototype.get = function(completionHandlerName) {
  SDK_trace("Nodes.prototype.get");
  var rt = null;
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke_batch";

  _check_login_status(this.mediator);
  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  for (x = 0;x < this.nodes.length;x++){
    msg.addParameter(this.nodes[x].path +":get");
  }
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};


/********************************************************************
Factories Section
********************************************************************/

/***************************************************************
 * OverridableNode, which inherits from Node, and adds methods 
 * 'override', 'is_overriden', 'is_overriden_by', and 'clear_override'.
 */
function OverridableNode(mediator, path) {
	SDK_trace('OverridableNode');
	//path = '/services/TOV' + path;
	Node.call(this, mediator, path);
}
OverridableNode.prototype = new Node();

/****
 * Parameter 'value' is required, the remaining two are optional.
 * 'seconds' provides the number of seconds the override is to 
 * be in effect for; if not provided, the override will be indefinite.
 * 'clearvalue' may be used to set a non-default (non-None) clearing 
 * value to set the overriden point to on clear.
 */
OverridableNode.prototype._create_message = function(method) {
	method = method || "rna_xmlrpc2:invoke";
	var message = new XMLRPCMessage(method);
	message.addParameter(this.mediator.session);
	message.addParameter(this.path);
	return message;
}

OverridableNode.prototype._make_request = function(message, callback) {
	var request;
	if (typeof(callback) != 'undefined') {
		request = new MediatorXMLRPCRequest(callback);
	} else {
		request = new MediatorXMLRPCRequest();
	}
	request.create();
	request.open();
	return request.send(message.xml());
}

OverridableNode.prototype.override = function(value, seconds, callback) {
	var message = this._create_message();
	message.addParameter('override');
	message.addParameter(value);
	if ((typeof(seconds) == 'number') && (seconds >= 0)) {
		message.addParameter(seconds);
	}
	return this._make_request(message, callback)
}

OverridableNode.prototype.is_overridden = function(callback) {
	var message = this._create_message();
	message.addParameter('is_overridden');
	return this._make_request(message, callback)
}

OverridableNode.prototype.is_overriden_by = function(override_id, callback) {
	var message = this._create_message();
	message.addParameter('is_overridden_by');
	message.addParameter(override_id);
	return this._make_request(message, callback)
}

OverridableNode.prototype.clear_override = function(callback, override_id) {
	var message = this._create_message();
	message.addParameter('clear_override');
	if (typeof(override_id) == 'string') {
		message.addParameter(override_id);
	}
	return this._make_request(message, callback)
}

function as_overridable_node(node) {
	var mediator = node.mediator;
	var path = node.path;
	return new OverridableNode(mediator, path);
}

/****
 * End OverridableNode definition.
 ********************************************************************/


//Deadband
Deadband.prototype = new Node;

//@@
// @function Deadband
// creates a Deadband node to interact with
// @param mediator the mediator you use for this node
// @param path node path
// @return null
// @note use the new method Example: var node = new Deadband(mediator,path)
function Deadband(mediator,path){
  SDK_trace("Deadband");
   this.mediator = mediator;
   this.path = path;
}

//@@
// @method threshold
// getter/setter for the threshold of the deadband
// @param [value] optional paramater to specify set the thershold, if not passed in returns the current thershold
// @return number
Deadband.prototype.threshold = function(thresholdValue,completionHandlerName){
  SDK_trace("Deadband.prototype.threshold");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("threshold");
  if(arguments.length > 0 && arguments[0] != null){
    msg.addParameter(thresholdValue);
    //alert(msg.xml());
  }
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

Log.prototype = new Node;


function as_log(node){
  SDK_trace("as_log");
  var n = null;
  n = new Log(node.mediator,node.path);
  return n;

}


//@@
// @function Log
// creates a Log node to interact with
// @param mediator the mediator you use for this node
// @param path node path
// @return null
// @note use the new method Example: var node = new Log(mediator,path)
function Log(mediator,path){
  SDK_trace("Log");
   this.mediator = mediator;
   this.path = path;
}

//@@ NEEDS MORE
// @method get_range
// @return list
Log.prototype.get_range = function(column,start,end,completionHandlerName){
  SDK_trace("Log.prototype.get_range");
  //start = start/1000;
  //end = end/1000;
  var rt = "";
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("get_range2");
  msg.addParameter(column);
  msg.addParameter(start);
  msg.addParameter(end);
  //  msg.addParameter(1);
  xml = msg.xml();
  if(arguments.length == 4) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@ NEEDS MORE
// @method get_range
// @return list
Log.prototype.get_column_names = function(completionHandlerName){
  SDK_trace("Log.prototype.get_column_names");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("get_column_names");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};


//@@
// @function as_deadband
// factory function to create a deadband node
// @param a generic node
// @return a Deadband node
function as_deadband(node){
  SDK_trace("as_deadband");
  var n = null;
  n = new Deadband(node.mediator,node.path);
  return n;
}

//RelayDriver
RelayDriver.prototype = new Node;

//@@
// @function RelayDriver
// creates a RelayDriver node to interact with
// @param mediator the mediator you use for this node
// @param path node path
// @return null
// @note use the new method Example: var node = new RelayDriver(mediator,path)
function RelayDriver(mediator,path){
  SDK_trace("RelayDriver");
  this.mediator = mediator;
  this.path = path;
}

//@@
// @method set_min_off_time
// setter for the min_off_time of the relay_driver
// @param value to set the min_off_time
// @return number
RelayDriver.prototype.set_min_off_time = function(value,completionHandlerName){
  SDK_trace("RelayDriver.prototype.set_min_off_time");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("set_min_off_time");
  msg.addParameter(value);
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method get_min_off_time
// getter for the min_off_time of the relay_driver
// @return number
RelayDriver.prototype.get_min_off_time = function(completionHandlerName){
  SDK_trace("RelayDriver.prototype.get_min_off_time");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("get_min_off_time");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method get_min_on_time
// getter for the min_on_time of the relay_driver
// @return number
RelayDriver.prototype.get_min_on_time = function(completionHandlerName){
  SDK_trace("RelayDriver.prototype.get_min_on_time");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("get_min_on_time");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @method set_min_on_time
// setter for the min_on_time of the relay_driver
// @param value optional paramater to specify set the min_on_time
// @return number
RelayDriver.prototype.set_min_on_time = function(value,completionHandlerName){
  SDK_trace("RelayDriver.prototype.set_min_on_time");
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("set_min_on_time");
  msg.addParameter(value);
  xml = msg.xml();
  if(arguments.length == 2) { //asynchronous
    request = new MediatorXMLRPCRequest(completionHandlerName);
  }
  else { //synchronous
    request = new MediatorXMLRPCRequest();
  }
  request.create();
  request.open();
  return request.send(xml);
};

//@@
// @function as_relay_driver
// factory function to create a relay_driver node
// @param a generic node
// @return a RelayDriver node
function as_relay_driver(node){
  SDK_trace("as_relay_driver");
  var n = null;
  n = new RelayDriver(node.mediator,node.path);
  return n;
}

//ErrorResult
function ErrorResult(ErrorCode,ErrorString){
  SDK_trace("ErrorResult");
  this.ErrorCode = ErrorCode;
  this.ErrorString = ErrorString;
}

//ErrorResult toString
ErrorResult.prototype.toString = function(){
  SDK_trace("ErrorResult.prototype.toString");
  return "????";
}

//MSXMLResult
function MSXMLResult(xml_doc){
  SDK_trace("MSXMLResult");
  this.xml_doc = xml_doc;
}

//MSXMLResult get_result
MSXMLResult.prototype.get_result = function(){
  SDK_trace("MSXMLResult.prototype.get_result");
  var rt;
  var doc_node = this.xml_doc.documentElement;
  var e = doc_node.firstChild;
  if(e.nodeName == "params"){
    rt  = this._get_result(e.firstChild); //nodeName == param
  }
  else if(e.nodeName == "fault"){
    rt = this._get_fault(e);
  }
  return rt;
};

//MSXMLResult _get_result
MSXMLResult.prototype._get_result = function(element){
  SDK_trace("MSXMLResult.prototype._get_result");
  var v = element.firstChild; //nodeName == value
  rt = this._get_value(v);
  return rt;
};

//MSXMLResult _get_fault
MSXMLResult.prototype._get_fault = function(fault){
  SDK_trace("MSXMLResult.prototype._get_fault");
  var rt;
  var value = fault.firstChild; //nodeName == value
  rt = this._get_value(value);
  throw new MpxException(rt['faultString']);
};

//MSXMLResult _get_struct
MSXMLResult.prototype._get_struct= function(s){
  SDK_trace("MSXMLResult.prototype._get_struct");
  var result = {};
  var children = s.childNodes;
  var nchildren = children.length;
  for (var i=0; i<nchildren; i++) {
    var child = children.item(i);
    if (child.nodeName == "member") {
      var grandchildren = child.childNodes;
      var ngrandchildren = grandchildren.length;
      var name = null;
      var value = null;
      for (n=0; n<ngrandchildren; n++) {
	var grandchild = grandchildren.item(n);
	if (grandchild.nodeName == "name") {
	  // Get contents of <name>'s #text child.
	  name = grandchild.childNodes.item(0).nodeValue;
	}
	if (grandchild.nodeName == "value") {
	  value = this._get_value(grandchild);
	}
      }
      if (name == null || value == null) {
	SDK_log("Malformed member: name = " + SDK_repr(name) +
		"; value = " + SDK_repr(value));
	continue;
      }
      result[name] = value;
    }
  }
  return result;
};

//MSXMLResult _get_array
MSXMLResult.prototype._get_array = function(array){
  SDK_trace("MSXMLResult.prototype._get_array");
  var index;
  var rt = new Array();
  var data = array.firstChild; // nodeName == data
  var values = data.childNodes; // nodeName = value
  for(index=0;index<values.length;index++){
    rt[rt.length] = this._get_value(values[index]);
  }
  return rt;
};

//MSXMLResult _get_value
MSXMLResult.prototype._get_value = function(value){
  SDK_trace("MSXMLResult.prototype._get_value");
  var rt = "";
  var i = 0;
  var e = value.firstChild;
  if(e.nodeName == "array"){
    rt = this._get_array(e);
  }
  else if(e.nodeName == "double"){
    rt = this._get_double(e);
  }
  else if( e.nodeName == "int" || e.nodeName == "i4" || e.nodeName == "boolean"){
    rt = this._get_int(e);
  }
  else if(e.nodeName == "string"){
    rt = this._get_string(e);
  }
  else if(e.nodeName == "struct"){
    rt = this._get_struct(e);
    if(rt._has_magnitude_interface){
      rt = new EnumeratedValue(rt);
    }
  }
  else if(e.nodeName == "name"){
    rt = this._get_name(e);
  }
  return rt;
};

//MSXMLResult _get_string
MSXMLResult.prototype._get_string = function(e){
  SDK_trace("MSXMLResult.prototype._get_string");
  try{
      var v = e.firstChild.nodeValue;
  }
  catch(e){
      v = "";
  }
  var pattern = /.*error:.*/;
  if(pattern.test(v)){
    var index = 0;
    index = v.indexOf("error:") + 6;
    var err_string = v.substring(index,v.length);
    v = new ErrorResult(-99999,err_string);
  }
  //Test for UU encoding
  pattern = /^begin 666 -/;
  if (pattern.test(v)){
    v = unescape(v);
    alert(v);
  }
  return v;
};

//MSXMLResult _get_int
MSXMLResult.prototype._get_int = function(i){
  SDK_trace("MSXMLResult.prototype._get_int");
  return parseInt(i.firstChild.nodeValue);
};

//MSXMLResult _get_name
MSXMLResult.prototype._get_name = function(n){
  SDK_trace("MSXMLResult.prototype._get_name");
  return n.firstChild.nodeValue;
};

//MSXMLResult _get_double
MSXMLResult.prototype._get_double = function(d){
  SDK_trace("MSXMLResult.prototype._get_double");
  return parseFloat(d.firstChild.nodeValue);
};

//XMLHTTPResult
function XMLHTTPResult(xml_doc){
  SDK_trace("XMLHTTPResult");
  //alert(xml_doc);
   this.xml_doc = xml_doc;
}

//XMLHTTPResult get_result
XMLHTTPResult.prototype.get_result = function() {
  SDK_trace("XMLHTTPResult.prototype.get_result");
  var rt = null;
  var d = this.xml_doc.documentElement;
  var dLen = d.childNodes.length;
  for(var i = 0; i < dLen; i++) {
    var e = d.childNodes[i];
    if(e.nodeName == "params"){
      var eLen = e.childNodes.length;
      for(var j = 0; j < eLen; j++) {
        var p = e.childNodes[j];
        if(p.nodeName == "param") {
          rt  = this._get_result(p); //nodeName == param
          break;
        }
      } //end for
      break;
    } //end if nodeName == "params"
    else if (e.nodeName == "fault"){
      rt = this._get_fault(e);
      break;
    }
  }
  return rt;
};

//XMLHTTPResult _get_result
XMLHTTPResult.prototype._get_result = function(element){
  SDK_trace("XMLHTTPResult.prototype._get_result");
  var rt = null;
  var elementLen = element.childNodes.length;
  for(var i = 0; i < elementLen; i++) {
    var v = element.childNodes[i];
    if(v.nodeName == "value") {
      rt = this._get_value(v); //nodeName == "value"
      break;
    }
  }
  return rt;
};

//XMLHTTPResult _get_fault
XMLHTTPResult.prototype._get_fault = function(fault){
  SDK_trace("XMLHTTPResult.prototype._get_fault");
  var rt = null;
  var faultLen = fault.childNodes.length;
  for(var i = 0; i < faultLen; i++) {
    var value = fault.childNodes[i];
    if(value.nodeName == "value") {
      rt = this._get_value(value); //nodeName == value
      throw new MpxException(rt['faultString']);
      break;
    }
  }
  return rt;
};

//XMLHTTPResult _get_struct
XMLHTTPResult.prototype._get_struct= function(s){
  SDK_trace("XMLHTTPResult.prototype._get_struct");
  var result = {};
  var children = s.childNodes;
  var nchildren = children.length;
  for (var i=0; i<nchildren; i++) {
    var child = children.item(i);
    if (child.nodeName == "member") {
      var grandchildren = child.childNodes;
      var ngrandchildren = grandchildren.length;
      var name = null;
      var value = null;
      for (n=0; n<ngrandchildren; n++) {
	var grandchild = grandchildren.item(n);
	if (grandchild.nodeName == "name") {
	  // Get contents of <name>'s #text child.
	  name = grandchild.childNodes.item(0).nodeValue;
	}
	if (grandchild.nodeName == "value") {
	  value = this._get_value(grandchild);
	}
      }
      if (name == null || value == null) {
	SDK_log("Malformed member: name = " + SDK_repr(name) +
		"; value = " + SDK_repr(value));
	continue;
      }
      result[name] = value;
    }
  }
  return result;
};

//XMLHTTPResult _get_array
XMLHTTPResult.prototype._get_array = function(array){
  SDK_trace("XMLHTTPResult.prototype._get_array");
  var index;
  var rt = new Array();
  var j;
  var arrayLen = array.childNodes.length;
  for(var i = 0; i < arrayLen; i++) {
    var d = array.childNodes[i];
    if(d.nodeName == "data") {
      var dLen = d.childNodes.length;
      for(j = 0; j < dLen; j++) {
        var v = d.childNodes[j];
        if(v.nodeName == "value") {
          rt[rt.length] = this._get_value(v);
        } //end if nodeName == "value"
      } //end for j
      break;
    } //end if nodeName == "data"
  } //end for i
  return rt;
};

//XMLHTTPResult _get_value
XMLHTTPResult.prototype._get_value = function(value){
  SDK_trace("XMLHTTPResult.prototype._get_value");
  var rt = "";
  var done = false;
  var valueLen = value.childNodes.length;
  for(var i = 0; i < valueLen; i++) {
    var e = value.childNodes[i];
    switch(e.nodeName) {
      case "array":
        rt = this._get_array(e);
        done = true;
        break;
      case "double":
        rt = this._get_double(e);
        done = true;
        break;
      case "boolean":
      case "int":
      case "i4":
   	    rt = this._get_int(e);
        done = true;
        break;
      case "string":
        rt = this._get_string(e);
        done = true;
        break;
      case "struct":
        rt = this._get_struct(e);
        if(rt._has_magnitude_interface){
          rt = new EnumeratedValue(rt);
        }
        done = true;
        break;
      case "name":
        rt = this._get_name(e);
        done = true;
        break;
    } //end switch
    if(done)
      break;
  } //end for
  return rt;
};

//XMLHTTPResult _get_string
XMLHTTPResult.prototype._get_string = function(e){
  SDK_trace("XMLHTTPResult.prototype._get_string");
  var v = e.firstChild.nodeValue;
  var pattern = /.*error:.*/;
  if(pattern.test(v)){
    var index = 0;
    index = v.indexOf("error:") + 6;
    var err_string = v.substring(index,v.length);
    v = new ErrorResult(-99999,err_string);
  }
  //Test for UU encoding
  pattern = /^begin 666 -/;
  if (pattern.test(v)){
    v = unescape(v);
    alert(v);
  }
  return v;
};

//XMLHTTPResult _get_int
XMLHTTPResult.prototype._get_int = function(i){
  SDK_trace("XMLHTTPResult.prototype._get_int");
  return parseInt(i.firstChild.nodeValue);
};

//XMLHTTPResult _get_name
XMLHTTPResult.prototype._get_name = function(n){
  SDK_trace("XMLHTTPResult.prototype._get_name");
  return n.firstChild.nodeValue;
};

//XMLHTTPResult _get_double
XMLHTTPResult.prototype._get_double = function(d){
  SDK_trace("XMLHTTPResult.prototype._get_double");
  return parseFloat(d.firstChild.nodeValue);
};

/********************************************************************
XMLRPC Section
********************************************************************/
/*

xmlrpc.js beta version 1
Tool for creating XML-RPC formatted requests in JavaScript

Copyright 2001 Scott Andrew LePera
scott@scottandrew.com
http://www.scottandrew.com/xml-rpc

License:
You are granted the right to use and/or redistribute this
code only if this license and the copyright notice are included
and you accept that no warranty of any kind is made or implied
by the author.

*/

function XMLRPCMessage(methodname){
  SDK_trace("XMLRPCMessage");
  this.method = methodname||"system.listMethods";
  this.params = [];
  return this;
}

XMLRPCMessage.prototype.setMethod = function(methodName){
  SDK_trace("XMLRPCMessage.prototype.setMethod");
  if (!methodName) return;
  this.method = methodName;
};

XMLRPCMessage.prototype.addParameter = function(data){
  SDK_trace("XMLRPCMessage.prototype.addParameter");
  if (arguments.length==0) return;
  this.params[this.params.length] = data;
};

XMLRPCMessage.prototype.xml = function(){
  SDK_trace("XMLRPCMessage.prototype.xml");
  var method = this.method;
  // assemble the XML message header
  var xml = "";
  xml += "<?xml version=\"1.0\"?>\n";
  xml += "<methodCall>\n";
  xml += "<methodName>" + method+ "</methodName>\n";
  xml += "<params>\n";
  // do individual parameters
  for (var i = 0; i < this.params.length; i++){
    var data = this.params[i];
    xml += "<param>\n";
    xml += "<value>" + XMLRPCMessage.getParamXML(XMLRPCMessage.dataTypeOf(data),data) + "</value>\n";
    xml += "</param>\n";
  }
  xml += "</params>\n";
  xml += "</methodCall>";
  return xml;
};

XMLRPCMessage.dataTypeOf = function (o){
  SDK_trace("XMLRPCMessage.dataTypeOf");
  // identifies the data type
  var type = typeof(o);
  type = type.toLowerCase();
  switch(type){
    case "number":
      if (Math.round(o) == o) type = "i4";
      else type = "double";
      break;
    case "object":
      var con = o.constructor;
      if (con == Date) type = "date";
      else if (con == Array) type = "array";
      else type = "struct";
      break;
  }
  return type;
};

XMLRPCMessage.doValueXML = function(type,data){
  SDK_trace("XMLRPCMessage.doValueXML");
  var xml;
  switch(type) {
    case "int":
    case "i4":
    case "double":
      //numeric types should not have entity references
      xml = "<" + type + ">" + data + "</" + type + ">";
      break;
    default:
      //other types need to convert [&,<,>,",'] to entity references in data string
      //first convert any entity references back to equivalent characters
      var searchStr = "&quot;";
      var replaceStr = '"';
      var re = new RegExp(searchStr, "gi");
      var tdata1 = data.replace(re, replaceStr);
      searchStr = "&apos;";
      replaceStr = "'";
      re = new RegExp(searchStr, "gi");
      var tdata2 = tdata1.replace(re, replaceStr);
      searchStr = "&lt;";
      replaceStr = '<';
      re = new RegExp(searchStr, "gi");
      var tdata3 = tdata2.replace(re, replaceStr);
      searchStr = "&gt;";
      replaceStr = '>';
      re = new RegExp(searchStr, "gi");
      var tdata4 = tdata3.replace(re, replaceStr);
      searchStr = "&amp;";
      replaceStr = '&';
      re = new RegExp(searchStr, "gi");
      var tdata5 = tdata4.replace(re, replaceStr);
      //then convert all special characters to equivalent entity references
      searchStr = '&';
      replaceStr = "&amp;";
      re = new RegExp(searchStr, "gi");
      tdata4 = tdata5.replace(re, replaceStr);
      searchStr = '>';
      replaceStr = "&gt;";
      re = new RegExp(searchStr, "gi");
      tdata3 = tdata4.replace(re, replaceStr);
      searchStr = '<';
      replaceStr = "&lt;";
      re = new RegExp(searchStr, "gi");
      tdata2 = tdata3.replace(re, replaceStr);
      searchStr = "'";
      replaceStr = "&apos;";
      re = new RegExp(searchStr, "gi");
      tdata1 = tdata2.replace(re, replaceStr);
      searchStr = '"';
      replaceStr = "&quot;";
      re = new RegExp(searchStr, "gi");
      xml = "<" + type + ">" + tdata1.replace(re, replaceStr) + "</" + type + ">";
      break;
  }
  return xml;
};

XMLRPCMessage.doBooleanXML = function(data){
  SDK_trace("XMLRPCMessage.doBooleanXML");
  var value = (data==true)?1:0;
  var xml = "<boolean>" + value + "</boolean>";
  return xml;
};

XMLRPCMessage.doDateXML = function(data){
  SDK_trace("XMLRPCMessage.doDateXML");
  var xml = "<dateTime.iso8601>";
  xml += dateToISO8601(data);
  xml += "</dateTime.iso8601>";
  return xml;
};

XMLRPCMessage.doArrayXML = function(data){
  SDK_trace("XMLRPCMessage.doArrayXML");
  var xml = "<array><data>\n";
  for (var i = 0; i < data.length; i++){
    xml += "<value>" + XMLRPCMessage.getParamXML(XMLRPCMessage.dataTypeOf(data[i]),data[i]) + "</value>\n";
  }
  xml += "</data></array>\n";
  return xml;
};

XMLRPCMessage.doStructXML = function(data){
  SDK_trace("XMLRPCMessage.doStructXML");
  var xml = "<struct>\n";
  for (var i in data){
    xml += "<member>\n";
    xml += "<name>" + i + "</name>\n";
    xml += "<value>" + XMLRPCMessage.getParamXML(XMLRPCMessage.dataTypeOf(data[i]),data[i]) + "</value>\n";
    xml += "</member>\n";
  }
  xml += "</struct>\n";
  return xml;
};

XMLRPCMessage.getParamXML = function(type,data){
  SDK_trace("XMLRPCMessage.getParamXML");
  var xml;
  switch (type){
    case "date":
      xml = XMLRPCMessage.doDateXML(data);
      break;
    case "array":
      xml = XMLRPCMessage.doArrayXML(data);
      break;
    case "struct":
      xml = XMLRPCMessage.doStructXML(data);
      break;
	  case "boolean":
      xml = XMLRPCMessage.doBooleanXML(data);
      break;
    default:
      xml = XMLRPCMessage.doValueXML(type,data);
      break;
  }
  return xml;
};

function dateToISO8601(date){
  SDK_trace("dateToISO8601");
  // wow I hate working with the Date object
  var year = new String(date.getYear());
  var month = leadingZero(new String(date.getMonth()));
  var day = leadingZero(new String(date.getDate()));
  var time = leadingZero(new String(date.getHours())) + ":" + leadingZero(new String(date.getMinutes())) + ":" + leadingZero(new String(date.getSeconds()));

  var converted = year+month+day+"T"+time;
  return converted;
}

function leadingZero(n){
  SDK_trace("leadingZero");
  // pads a single number with a leading zero. Heh.
  if (n.length==1) n = "0" + n;
  return n;
}

function EnumeratedValue(ev){
  this.str = ev.str;
  this.num = parseFloat(ev.num);
}

EnumeratedValue.prototype.as_magnitude = function(){
  return this.num;
};

EnumeratedValue.prototype.toString = function(){
  return this.str;
};

function resolve_path(entityPath, nodePath, replaceText){
	SDK_trace("resolve_path");
	if(entityPath && (nodePath.indexOf("aliases") > 0)){
		nodePath = nodePath.replace(replaceText[0], replaceText[1]);
	}
	return nodePath;
}

function get_url_param(paramName){
	SDK_trace("get_url_param");
	paramName = paramName.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
	var regexS = "[\\?&]"+paramName+"=([^&#]*)";
	var regex = new RegExp( regexS );
	var results = regex.exec(window.location.href);
	if( results == null ){
		return "";
	}else{
		if(results[1].indexOf("aliases") < 0){
		  results[1] = "/aliases"+results[1];
		}
		return results[1];
	}
}

//@@
// @function start_refresh_loop
// start the refreshing of the page
// @param page_properties
// @return null
function start_refresh_loop(pp){
  SDK_trace("start_refresh_loop");
  PAGE_PROPERTIES = pp;
  PAGE_PROPERTIES.refresh_count = 0;
  //update the special factory elements
  _refresh_loop();
}

//@@
// @function start_refresh_loop
// start the refreshing of the page
// @param page_properties
// @return null
function stop_page_refresh() {
  SDK_trace("stop_page_refresh");
  try {
    SDK_nodes.subscription_destroy();
  }
  catch (e) {
    SDK_trace("stop_page_refresh error: '"  + e + "'");
  }
};

var factoryElements = null; //current list of factory elements
var nodeElements = null; //current list of elements with node paths
var nodePaths = null; //current list of node paths for elements with node paths

function login_success(m){
  SDK_trace("login_success");
  PAGE_PROPERTIES.set_mediator(m);
  start_refresh_loop(PAGE_PROPERTIES);
}

function new_nodes(){
  SDK_trace("new_nodes");
  var cnt = 0;
  var nodePath;
  var _elements = get_elements();
  for(x = 0; x < _elements.length; x++){
    nodePath = _elements[x].getAttribute('node');
    if(nodePath)
      cnt++;
  }
  return(cnt != PAGE_PROPERTIES.nodeLen)
}

function build_poll_group(){
  var x = 0;
  var index = 0;
  var factory_index = 0;
  var node;
  var nodes;
  var factory;
  var method;
  var path;
  var replaceText;
  var factory_results = new Array();
  var m = PAGE_PROPERTIES.get_mediator();
  var entityManager = new EntityManager(m);
  var _elements = get_elements();
  factoryElements = new Array();
  nodeElements = new Array();
  nodePaths = new Array();
  var entityPath = get_url_param("entity");
  
  try {
    replaceText = entityManager.resolve_mount_paths(entityPath); 
  } catch(e) {
    replaceText = ["",""];
  } 
  for (x=0;x<_elements.length;x++){
    if (_elements[x].getAttribute('factory') == null){
      nodePaths[index] = resolve_path(entityPath, _elements[x].getAttribute('node'), replaceText);
      nodeElements[index] = _elements[x];
      index++;
    }
    else{
      factoryElements[factory_index]= _elements[x];
      factory_index++;
    }
  }
  for (x=0;x<factoryElements.length;x++){
    path = factoryElements[x].getAttribute('node');
    node =  m.get_node(path);
    factory = factoryElements[x].getAttribute('factory');
    node = eval(factory + '( node)');
    method = factoryElements[x].getAttribute('method');
    factory_results[x] = eval('node.' + method + '()');
  }
  update_elements(factoryElements,factory_results);
  SDK_nodes = PAGE_PROPERTIES.mediator.get_nodes(nodePaths);
  SDK_sid = SDK_nodes.subscription_create_polled()
  PAGE_PROPERTIES.nodeLen = SDK_nodes.nodes.length;
}

function _refresh_loop(){
  SDK_trace("_refresh_loop");
  try{
    // if WebExpress has added or modified widgets it will mark the page as
    // dirty.  Force a new subscription to be created so that dynamic data
    // may be displayed via WebExpress
    if(PAGE_PROPERTIES.getPageDirty() == true){
        PAGE_PROPERTIES.setPageDirty(false);
        if(PAGE_PROPERTIES.refresh_count){
            stop_page_refresh();
        }
        build_poll_group();
    }
    if(PAGE_PROPERTIES.refresh == true){
         refresh_elements();
    }
    setTimeout("_refresh_loop()",PAGE_PROPERTIES._refresh_rate);
    PAGE_PROPERTIES.refresh_count++;
  }
  catch(e){
    if(e.type != null && e.type == 'MpxException'){
      if (e.name == 'ENotLoggedIn'){
        // call the login window and passing the names of
        // the function to return a the mediator object
        // the function to call back after login
        login_window("PAGE_PROPERTIES.get_mediator","login_success");
      }
      else{
        throw e;
      }
    }
    else{
      throw e;
    }
  }
}

function update_element(element,v,display_error){
  SDK_trace("update_element");
  if(arguments.length < 3){
    display_error = false;
  }
  var message;

  if(element.nodeName == "SPAN" ||
     element.nodeName == "TD" ||
     element.nodeName == "DIV"){
    element.innerHTML = v.toString();
  }
  else if(element.nodeName == "INPUT"){
    element.value =  v.toString();
  }

  if(display_error == true && typeof(v) == "object"){
      message = "ERROR CODE: " + v.ErrorCode + "\\n";
      message +=  v.ErrorString;
      element.setAttribute("onClick", "javascript:alert('" + message + "')");
  }
}

function update_elements(elements,results){
  SDK_trace("update_elements");
  var elements_index = 0;
  if(results != null){
    for (elements_index=0;elements_index<elements.length;elements_index++){
      if (elements[elements_index].getAttribute("display_function")!=null){
        var f = elements[elements_index].getAttribute("display_function");
        var args = "";
        if (elements[elements_index].getAttribute("args") != null){
          args = "," + elements[elements_index].getAttribute("args");
        }
        var func = f + "(elements[elements_index] ,results[elements_index]" + args + ")";
        eval(func);
      }
      else{
        update_element(elements[elements_index],results[elements_index]);
      }
    }
  }
  else{
    //msglog("No RESULTS");
  }
}

currentMediatorXMLRPCElements = null;

function update_changed_elements() {
	SDK_trace("update_changed_elements");
	var elements_index = null;
	if (this.result != null) {
		for (elements_index = 0; elements_index < SDK_nodes.nodes.length; ++elements_index) {
			if (this.result[elements_index] != undefined) {
				var result = this.result[elements_index];
				var node_element = nodeElements[elements_index];
				var display_function = node_element.getAttribute("display_function");
				if (display_function != null) {
					var display_args = node_element.getAttribute("args");
					var args = "";
					if (display_args != null) {
						args = "," + display_args;
					}
					var result_filter = node_element.getAttribute('result_filter');
					result_filter = result_filter || 'value';
					if (result_filter != '.') {
						result = result[result_filter];
					}
					var eval_func = display_function + '(node_element, result' + args + ')';
					eval(eval_func);
				}
				else {
					update_element(nodeElements[elements_index], result["value"]);
				}
			}
		}
	}
	else {
		SDK_log("update_changed_elements: this.result == null");
	}
}

function getCompleted() {
  SDK_trace("getCompleted");
  update_elements(currentMediatorXMLRPCElements, this.result);
}

function refresh_elements(){
  SDK_trace("refresh_elements");
  try{
      SDK_nodes.subscription_poll_changed("update_changed_elements");
  }
  catch(e){
      //after a save - f.e., poll group has to be rebuilt
      if(!SDK_nodes){
        build_poll_group();
      }
  }
}

function get_elements(){
  SDK_trace("get_elements");
  var nodes = new Array();
  var spans = document.getElementsByTagName("span");
  var images = document.getElementsByTagName("img");
  var inputs =  document.getElementsByTagName("input");
  var tds = document.getElementsByTagName("td");
  var divs =  document.getElementsByTagName("div");
  var index = 0;

  for (x =0;x<spans.length;x++){
    if(spans[x].getAttribute("node") != null){
      nodes[index] = spans[x];
      index++;
    }
  }
  for (x =0;x<images.length;x++){
    if(images[x].getAttribute("node") != null){
      nodes[index] = images[x];
      index++;
    }
  }

  for (x =0;x<inputs.length;x++){
    if(inputs[x].getAttribute("node") != null){
      nodes[index] = inputs[x];
      index++;
    }
  }

  for (x =0;x<tds.length;x++){
    if(tds[x].getAttribute("node") != null){
      nodes[index] = tds[x];
      index++;
    }
  }

  for (x =0;x<divs.length;x++){
    if(divs[x].getAttribute("node") != null){
      nodes[index] = divs[x];
      index++;
    }
  }
  return nodes;
}


/********************************************************************
HTTP Request Section
********************************************************************/


// Error objects
function ERequestException(e){
  SDK_trace("ERequestException");
    this.error = e;
    this.type = 'ERequestException';
}

ERequestException.prototype.toString = function(){
  SDK_trace("ERequestException.prototype.toString");
  return  "Error: " + this.error;
};

function ENoActiveX(e){
  SDK_trace("ENoActiveX");
    this.type = "ENoActiveX";
    this.base = ERequestException;
    this.base(e);
};

ENoActiveX.prototype =  new ERequestException;


function getXmlHttpPrefix() {
  SDK_trace("getXmlHttpPrefix");

  if (getXmlHttpPrefix.prefix)
    return getXmlHttpPrefix.prefix;
  var prefixes = ["MSXML4.XmlHttp","MSXML3.XmlHttp","MSXML2.XmlHttp",
		  "MSXML.XmlHttp","Microsoft.XmlHttp" ];
  var o;
  for (var i = 0; i < prefixes.length; i++) {
    try {

      // try to create the objects
      o = new ActiveXObject(prefixes[i]);
      return getXmlHttpPrefix.prefix = prefixes[i];
    }
    catch (ex) {
    }
  }
  throw new ENoActiveX("Could not find the Active X control");
}

var currentMediatorXMLRPCRequest = null;
var currentMediatorXMLRPCCompletion = null;

var MediatorXMLRPCStateLength = 10;
var MediatorXMLRPCState = new Array();

for(var i = 0; i < MediatorXMLRPCStateLength; i++) {
  var stateObj = new Object();
  stateObj.inuse = false;
  stateObj.name = "MediatorXMLRPCState[" + i + "]";
  stateObj.request = null;
  stateObj.callback = null;
  stateObj.completion = null;
  stateObj.parm1 = null;
  stateObj.parm2 = null;
  stateObj.parm3 = null;
  MediatorXMLRPCState.push(stateObj);
};

function getMediatorXMLRPCState() {
  SDK_trace("getMediatorXMLRPCState");
  var rt = null;
  for(var i = 0; i < MediatorXMLRPCStateLength; i++) {
    if(MediatorXMLRPCState[i].inuse == false) {
      MediatorXMLRPCState[i].inuse = true;
      rt = MediatorXMLRPCState[i];
      break;
    }
  }
  /*if(rt == null) {
    var msg = 'Request queue has filled up!\n'
	msg += 'The server maybe down, or \n'
	msg += 'each request is slow and the queue filled up!\n'
	msg += 'If the queue is filling up, lowering the refresh rate for the page might fix the problem'
    alert(msg);
  }*/
  return rt;
}

function MediatorXMLRPCRequest(completionHandlerName) {
  SDK_trace("MediatorXMLRPCRequest");
  this.url = "/xmlrpc";
  this.method = "POST";
  if(arguments.length == 0) {
    this.bAsync = false;
    this.completionhandlername = '';
  }
  else {
    this.bAsync = true;
    this.completionhandlername = completionHandlerName;
  }
  this.objXMLHTTP = null;
  this.stateObj = null;
  this.result = null;
  return this;
}

MediatorXMLRPCRequest.prototype.setURL = function(urlString){
  SDK_trace("MediatorXMLRPCRequest.prototype.setURL");
  if (!urlString) return;
  this.url = urlString;
};

MediatorXMLRPCRequest.prototype.getURL = function(){
  SDK_trace("MediatorXMLRPCRequest.prototype.getURL");
  return this.url;
};

MediatorXMLRPCRequest.prototype.setMethod = function(methodName){
  SDK_trace("MediatorXMLRPCRequest.prototype.setMethod");
  if (!methodName) return;
  this.method = methodName;
};

MediatorXMLRPCRequest.prototype.getMethod = function(){
  SDK_trace("MediatorXMLRPCRequest.prototype.getMethod");
  return this.method;
};

MediatorXMLRPCRequest.prototype.setNotifyFunction = function(notifyfunction){
  SDK_trace("MediatorXMLRPCRequest.prototype.setNotifyFunction");
  if (arguments.length==0) {
    this.bAsync = false;
    this.notifyFunction = null;
  }
  else {
    this.bAsync = true;
    this.notifyFunction = notifyfunction;
  }
};

MediatorXMLRPCRequest.prototype.getNotifyFunction = function(){
  SDK_trace("MediatorXMLRPCRequest.prototype.getNotifyFunction");
  return this.notifyFunction;
};

MediatorXMLRPCRequest.prototype.setChangeHandler = function(changeHandler){
  SDK_trace("MediatorXMLRPCRequest.prototype.setChangeHandler");
  if (arguments.length==0) {
    this.onChangeHandler = null;
  }
  else {
    this.onChangeHandler = changeHandler;
  }
};

MediatorXMLRPCRequest.prototype.getChangeHandler = function(){
  SDK_trace("MediatorXMLRPCRequest.prototype.getChangeHandler");
  return this.onChangeHandler;
};

// readyStates:
// 0-UNINITIALIZED
//     The object has been created, but not initialized (open method has not been called
// 1-LOADING
//    The object has been created, but the send method has not been called.
// 2-LOADED
//    The send method has been called and the status and headers are available,
//    but the response is not yet available.
// 3-INTERACTIVE
//    Some data has been received. You can call responseBody and responseText
//    to get the current partial results.
// 4-COMPLETED
//   All the data has been received, and the complete data is available in
//   responseBody and responseText.
// NOTE: we might be able to tell if the server is down if we never get
// an INTERACTIVE status!  There would have to be some sort of time out
MediatorXMLRPCRequest.prototype.onChangeHandler = function() {
  SDK_trace("MediatorXMLRPCRequest.prototype.onChangeHandler");
  try {
    var currentState = this.request.objXMLHTTP.readyState;
    if(currentState == 4) {
	    try{
	      if(this.request.bAsync == true) {
	        this.request.parseResults();
	        eval(this.request.completionhandlername).call(this.request);
	      }
		}catch(ex){
            if (ex.type == 'MpxException') {
                var error_string = ex.error;
                var compare_string = "ENotFound: ('subscription manager'";
                var error_substring = error_string.substring(0,compare_string.length);
                if (error_substring == compare_string) {
                    PAGE_PROPERTIES.setPageDirty(true);
                }
            }
		}
		this.request = null;
		this.inuse = false;
    }
  } //end try
  catch(ex) {
  }
};

MediatorXMLRPCRequest.prototype.completionHandler = function() {
  SDK_trace("MediatorXMLRPCRequest.prototype.completionHandler");
  /*if(this.notifyfunction) {
    this.notifyfunction.call(this);
  } */
};

MediatorXMLRPCRequest.prototype.create = function() {
  SDK_trace("MediatorXMLRPCRequest.prototype.create");
  try {
    this.stateObj = getMediatorXMLRPCState();
    this.stateObj.request = this;
    var browserIE = new RegExp('internet explorer','gi');
    if(browserIE.test(navigator.appName)) {
      this.objXMLHTTP = new ActiveXObject(getXmlHttpPrefix());
      var myFuncStr = this.stateObj.name + ".request.onChangeHandler.call(" + this.stateObj.name + ");";
      this.objXMLHTTP.onreadystatechange = function() {eval(myFuncStr)};
    }
    else {
      this.objXMLHTTP = new XMLHttpRequest();
      // some versions of Moz do not support the readyState property
      // and the onreadystate event so we patch it!
      if (this.objXMLHTTP.readyState == null) {
        this.objXMLHTTP.readyState = 1;
        this.objXMLHTTP.addEventListener("load",
	  function () {
	    this.objXMLHTTP.readyState = 4;
	    if (typeof this.objXMLHTTP.onreadystatechange == "function")
	      this.objXMLHTTP.onreadystatechange();
	  }, false);
      }
      else {
        var myFuncStr = this.stateObj.name + ".request.onChangeHandler.call(" + this.stateObj.name + ");";
        this.objXMLHTTP.onreadystatechange = function() {eval(myFuncStr)};
      }
    } //end else
  } //end try
  catch(e){
    if (e.type != null && (e.type == 'ERequestException' || e.type=='ENoActiveX')){
      throw e;
    }
    else {
      var msg = "Error trying to create HTTP Request Object";
      throw new ERequestException(msg);
    }
  }
};

MediatorXMLRPCRequest.prototype.open = function() {
  SDK_trace("MediatorXMLRPCRequest.prototype.open");
  this.objXMLHTTP.open(this.method,this.url,this.bAsync);
};

MediatorXMLRPCRequest.prototype.send = function(xml) {
  SDK_trace("MediatorXMLRPCRequest.prototype.send");
  this.objXMLHTTP.send(xml);
  if(this.bAsync == true) {
    return null;
  }
  else {
    this.parseResults();
    this.stateObj.request = null;
    this.stateObj.inuse = false;
    return this.result;
  }
};

MediatorXMLRPCRequest.prototype.parseResults = function() {
  SDK_trace("MediatorXMLRPCRequest.prototype.parseResults");
  var browserIE = new RegExp('internet explorer','gi');
  if(browserIE.test(navigator.appName)) {
    var results = new MSXMLResult(this.objXMLHTTP.responseXML);
  }
  else {
    //alert(this.objXMLHTTP.responseText);
    var results = new XMLHTTPResult(this.objXMLHTTP.responseXML);
  }
  this.result = results.get_result();
};

var sdk2_loaded = true;

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
dojo.provide("utils.handlers");

/*****************************
 * Define very simple handlers, primary for teseting purpseses.
 * 
 * Handlers accept up to three arguments; only the first argument 
 * is required.  The remaining arguments allow callers to proxy 
 * oir hitch their own recipients.
 * 
 * The first parameter may be null, a function which returns 
 **************************/

utils.handlers.onResponse = function(response, listener, attr) {
    console.debug("Response received:", response);
    utils.handlers.notify(response, listener, attr);
    return response;
}

utils.handlers.onError = function(response, listener, attr) {
    console.error("Request failed:", response);
    utils.handlers.notify(response, listener, attr);
    return response;
}

/******************************
 * Notify object of value by invoking object with value if 
 * attr is not provided.  If attr is provided it must be a 
 * string and will be used as the name of a variable set to 
 * the value on object.
 ****************************/
utils.handlers.notify = function(value, object, attr) {
    if (attr && !object)
        object = window;
    if (object) {
        if (attr)
            object[attr] = value;
        else
            object(value);
    }
}

/****************************
 * Create error handler with provided listener and attribute 
 * name for handlers to use on invocation.
 * 
 * Accepts boolean onError to indicate that the onError handler 
 * should be used.
 ****************************/
utils.handlers.makeHandler = function(object, attr, onError) {
    function handle(response) {
        if (onError)
            handler = utils.handlers.onError;
        else
            handler = utils.handlers.onResponse;
        return handler(response, object, attr);
    }
    return handle;
}

utils.handlers.multiplex = function(/* works with list of defererds */) {
    var deferreds = arguments;
    function multiplex(method, result) {
        dojo.forEach(deferreds, function(item) {
            item[method](result);
        });
        return result;
    }
    var deferred = new dojo.Deferred();
    var callback = dojo.hitch(multiplex, "callback");
    var errback = dojo.hitch(multiplex, "errback");
    deferred.addCallbacks(callback, errback);
    return deferred;
}
















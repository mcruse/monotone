/*
Copyright (C) 2009 2010 2011 Cisco Systems

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
dojo.provide("utils.display");
dojo.require("dojo.parser");
dojo.require("dijit.Dialog");
dojo.require("dijit.TitlePane");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.Textarea");
dojo.require("dijit.layout.ContentPane");

utils.display.dialogBox = null;
utils.display.messageBox = null;
utils.display.subscriptions = null;
utils.display.messageBoxes = [];

dojo.addOnLoad(function() {
    var dialog = new dijit.Dialog({preload: true, id: "message-box",
    	refocus: false});
    utils.display.dialogBox = dialog;
    var handle = dojo.connect(dialog, "onLoad", function() {
        console.log("Message display widget template loaded.");
        utils.display.messageBox = dijit.byId("message-content");
        utils.display.subscriptions = new Array();
        var subscribers = ["message", "warning", "failure", "success"];
        dojo.forEach(subscribers, function(item, index) {
            var topic = "/display/" + item;
            var subscription = dojo.subscribe(topic, utils.display[item]);
            utils.display.subscriptions.push(subscription)
        });        
        dojo.disconnect(handle);
    });    
    dialog.attr("href", "/public/utils/templates/message.html");
    dialog.startup();
});

utils.display.isLoaded = function() {
    return (utils.display.dialogBox && utils.display.dialogBox.isLoaded);
}

utils.display.getMessageBox = function() {
    return utils.display.messageBox;
}

utils.display.message = function(type, message, details) {
    if (!utils.display.isLoaded()) {
        var dialog = utils.display.dialogBox;
        var handle = dojo.connect(dialog, "onLoad", function() {
            utils.display.message(type, message, details);
            dojo.disconnect(handle);
        });
    } else {
        var msgbox = utils.display.getMessageBox();
        msgbox.display(type, message, details);
        return msgbox;
    }
}

utils.display.warning = function(message, details) {
    return utils.display.message("warning", message, details);
}

utils.display.failure = function(message, details) {
    return utils.display.message("error", message, details);
}

utils.display.success = function(message, details) {
    return utils.display.message("success", message, details);
}

utils.display.information = function(message, details) {
    return utils.display.message("information", message, details);
}

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
dojo.provide("nbmweb.Notification");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.form.Button");
dojo.require("dijit.TitlePane");
dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("nbmweb.StatusMessage");

dojo.declare("nbmweb.Notification", [dijit._Widget, dijit._Templated], {
    templateString: null,
    buttonAcknowledge: "OK", 
    widgetsInTemplate: true, 
    templatePath: dojo.moduleUrl("nbmweb", "templates/Notification.html"), 
    constructor: function(args) {
        console.log("nbmweb.Notification()", arguments);
        dojo.mixin(this, args);
    }, 
    acknowledge: function() {
        console.log("User acknowledged: ", this.status);
        this.destroyRecursive();
    }, 
    display: function(type, summary, detail) {
        console.log("show()", type, summary, detail);
        if (typeof(type) != "undefined")
            this.status.attr("type", type);
        if (typeof(summary) != "undefined")
            this.status.attr("content", summary);
        if (typeof(detail) != "undefined") {
            this.detail.attr("content", detail);
            dojo.removeClass(this.detail.domNode, "empty");
        } else {
            dojo.addClass(this.detail.domNode, "empty");
        }
        if (!this.dialog.open)
            this.dialog.show();
        else
            this.dialog.layout();
    }
});

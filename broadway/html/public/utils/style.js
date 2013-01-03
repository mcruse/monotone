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
/**********************************
 * Collection of functions providing browser-specific stylistic 
 * functionality.  Functions automatically attach themselves to 
 * the appropriate elements and events.
 * 
 * 99% of the functionality targetted at IE6 compatibility.
 * Note that there is an IE6 bug wherein background PNG images 
 * configured for transparency via filters capture all events of 
 * entire subtree.  Workarounds include specifying relative 
 * positioning for specific elements or, as this code does, 
 * shying away from PNG backgrounds and instead emulating the 
 * functionality by a generated DIV element which has no children.  
 ***********************************/
dojo.provide("utils.style");
dojo.require("utils.branding");

utils.style.connections = new Array();
utils.style.updaters = new Array();
dojo.addOnLoad(function() {utils.style.setup_workarounds();});

dojo.addOnLoad(function() {
    var branding = utils.branding;
    var title = [branding.company, branding.product];
    var footer = [branding.company, branding.product, branding.copyright];
    dojo.query("div#header .title").attr("innerHTML", branding.product);
    dojo.query("div#footer").attr("innerHTML", footer.join(" "));
    document.title = title.join(" ");
    window.sid = dojo.cookie("SID");
});

utils.style.setup_workarounds = function() {
    if (dojo.isIE) {
        utils.style.setup_ie_workarounds();
        document.attachEvent("onclick", notifyUserChange);
    } else {
    	document.addEventListener("click", notifyUserChange, true);
        console.log("setup_workarounds() doing nothing: not IE browser");
    }
}

notifyUserChange = function(event) {
	if(window.sid != dojo.cookie("SID")) {
		window.sid = dojo.cookie("SID");
		var user = dojo.cookie("CUSER");
		alert("WARNING: User has been switched to '" + user + "'");
	}
}

utils.style.setup_ie_workarounds = function() {
    if (dojo.isIE > 6 && dojo.isIE < 8)
        utils.style.setup_ie7_workarounds();
    else if (dojo.isIE <= 6)
        utils.style.setup_ie6_workarounds();
    else
        console.log("setup_ie_workarounds() doing nothing: version > 6");
}

utils.style.setup_ie7_workarounds = function() {
    if (dijit.byId("mainTabContainer")) {
        console.log("setting up IE7 content-tab resize workaround");
        utils.style.updaters.push(utils.style.update_content_tabs);
        utils.style.update_styles(true);
    } else 
        console.log("IE7 workaround doing nothing: no content-tabs");
}

utils.style.setup_ie6_workarounds = function() {
    if (!dojo.byId("footer"))
        throw new Error("Page missing required 'footer' element");
    utils.style.updaters.push(utils.style.update_footer);
    var primary = dijit.byId("primary-tabs");
    if (primary) {
        var loaded;
        function setuptabs() {
            utils.style.updaters.push(utils.style.update_primary_tabs);
            utils.style.update_primary_tabs(true);
            utils.style.update_styles(false);
            dojo.disconnect(loaded);
        }
        loaded = dojo.connect(primary, "onDownloadEnd", setuptabs);
    }
    // Don't manage stage for log-in page, hence the 'challenge' check.
    if (dojo.byId("stage") && !dojo.byId("challenge")) {
        utils.style.updaters.push(utils.style.update_stage);
    }
    // Schedule PNG fix after time lapse ensuring all PNGs loaded.
    setTimeout('utils.style.fix_png_images(null, null)', 3000);
    utils.style.update_styles(true);        
}

/*************************
 * Utility function attaches event logging to overview tab 
 * of security.html page.  Used to troubleshoot event theft 
 * in IE6.
 *************************/
utils.style.debug_events = function() {
    var tabs = dojo.query(
       "div.dijitTab", dijit.byId("mainTabContainer_tablist").domNode)
    var overview = dojo.query("ul", dojo.byId('tab1'))[0];
    function append(text) {
        var item = document.createElement("li");
        var text = document.createTextNode(text);
        item.appendChild(text);
        overview.appendChild(item);
    }
    function logevent(event) {
        append(event.target.nodeName +
               ": " + event.target.id + 
               ": " + event.target.className);
    }
    for (var i=0; i < tabs.length; i++) {
        var tab = tabs[i];
        var widget = dijit.getEnclosingWidget(tab);
        utils.style.connections.push(dojo.connect(tab, "onclick", logevent));
        utils.style.connections.push(
            dojo.connect(widget, "onClick", logevent));
    }
    utils.style.connections.push(
        dojo.connect(dojo.body(), "onclick", logevent));
}

/************************
 * Run through enqueued update functions, executing each.
 * Enqueuing of style updates ensures proper update order which, 
 * because many positions and sizes are based on other components, 
 * is critical.
 * 
 * On first-run, indicated by firstrun == true, setup event connections 
 * do that update is invoked every time page size changes.
 ************************/
utils.style.update_styles = function(firstrun) {
    // Run through list of positioning functions, executing each.
    // If this is the first run of update, attach future runs to 
    // body resize events.  If called by event handler, event object 
    // passed as first param.
    if (typeof(firstrun) != "boolean")
        throw new Error("update_styles() expects bool, not " + firstrun);
    if (firstrun) {
        invocation = "item(true);";
        // Create partial so callback gets boolean firstrun, not event.
        update = dojo.partial(utils.style.update_styles, false);
        utils.style.connections.push(
            dojo.connect(dojo.body(), "onresize", update));

    } else
        invocation = "item(false);";
    dojo.forEach(utils.style.updaters, invocation);
}

/*********************
 * Loop through all connections disconnecting them.
 * Cleans up dojo event attachments, run to avoid memory leaks.
 *********************/
utils.style.disconnect = function() {
    var connections = utils.style.connections;
    utils.style.connections = new Array();
    utils.sytle.updaters = new Array();    
    dojo.forEach(connections, "dojo.disconnect(item);");
}

utils.style.update_content_tabs = function(firstrun) {
    // Should be used by IE6 & IE7 to manage tab positioning 
    // for pages using content-tabs.
    var container = dijit.byId("mainTabContainer");
    var containernode = container.domNode;
    var contentnode = containernode.parentNode;
    var contentbox = dojo.contentBox(contentnode);
    var containerbox = dojo.marginBox(containernode);
    if (containerbox.h != contentbox.h)
        container.resize({h: contentbox.h});
}

/*****************************
 * IE does not support 'fixed' positioning.
 * 
 * Mimic fixed positioning for footer element by positioning 
 * it based on view-port values.
 *****************************/
utils.style.update_footer = function(firstrun) {
    if (firstrun) {
        dojo.style("footer", "position", "absolute");
        dojo.style("footer", "margin", 0);
        setTimeout('utils.style.update_styles(false)', 1000);        
    }
    var top = dijit.getViewport().h - 27;
    dojo.marginBox("footer", {l: 15, t: top, h: 13});
}

/**********************************
 * Manage size and placement of primary-tabs manually.
 * 
 * Primary tab sizing, and possibly absolutely positioned 
 * element sizing in general, not support properly by IE6.
 **********************************/
utils.style.update_primary_tabs = function(firstrun) {
    if (firstrun) {    
        var tabslist = dojo.query("ul.tabs", "primary-tabs")[0];
        var tabs = dojo.query("li.tab-button", tabslist);
        var links = tabs.query("a");
        var spans = tabs.query("span");
        var labels = spans.attr("innerHTML");
        // Set links to inline-block display to content width.
        links.style("display", "inline-block");
        // Fix the PNG transparency background.
        utils.style.fix_png_background(tabslist);
        // Hide weird extrusions.
        dojo.style(tabslist, "marginRight", 11);
        tabs.style("overflow", "hidden");
    }
    var width = dojo.marginBox("stage").w;
    dojo.marginBox("primary-tabs", {w: width});
    if (firstrun) {
        var height = dojo.style("primary-tabs", "height");
        dojo.contentBox("primary-tabs", {h: height});
    }
}

utils.style.update_stage = function(firstrun) {
    if (firstrun) {
        var top = dojo.style("stage", "top");
        var left = dojo.style("stage", "left");
        if (dojo.isString(top)) {
            if (top == "0")
                top = 0;
            else if (top.toLowerCase().indexOf("px") == -1)
                throw new Error("stage top must be 0 or pixles");
            else 
                top = Number(top.slice(0, -2));
        }
        if (dojo.isString(left)) {
            if (left == "0")
                left = 0;
            else if (left.toLowerCase().indexOf("px") == -1)
                throw new Error("stage left must be 0 or pixles");
            else 
                left = Number(left.slice(0, -2));
        }
        dojo.style("stage", "marginBottom", 0);
        dojo.marginBox("stage", {t: top, l: left});
        var panes = dojo.query("div#stage div.pane");
        dojo.forEach(panes, "utils.style.fix_content_background(item);");
    }
    var viewport = dijit.getViewport();
    var marginbox = dojo.marginBox("stage");
    var width = viewport.w - marginbox.l;
    var height = dojo.style("footer", "top") - marginbox.t - 8;
    dojo.marginBox("stage", {w: width, h: height});
    var contentbox = dojo.contentBox("stage");
    if (dojo.byId("navigation-pane")) {
        var top = dojo.style("navigation-pane", "top");
        dojo.marginBox("navigation-pane", {h: contentbox.h - top});
    }
    if (dojo.byId("contentarea")) {
        var top = dojo.style("contentarea", "top");
        var left = dojo.style("contentarea", "left");
        var areabox = {w: contentbox.w - left, h: contentbox.h - top};
        dojo.marginBox("contentarea", areabox);
    }
    if (dijit.byId("mainTabContainer"))
        dijit.byId("mainTabContainer").resize();
}

/**************************
 * Fix background of content-pane element that uses PNG image.
 * 
 * IE6 does not support PNG transparency directly.  Workaround 
 * uses 'filter' function to display PNG properly.  When applied 
 * to background of container element, however, all child elements 
 * events will be stolen by parent with filter-displayed background.
 * Workarounds include using relative positioning to enable event 
 * capture for specific ancestors or, as this approach takes, 
 * removal of PNG background, insertion of generated DIV element 
 * to which the background is attached, and setup of the new DIV.
 * Because the DIV element is generated and has no children, it 
 * does not override event capture of children.
 **************************/
utils.style.fix_content_background = function(pane) {
    // Wipe out content-pane background image and add new 
    // element with background that will not be parent of 
    // elements inside pane so that IE6 event bug, wherein 
    // all mouse events are stolen by parent with filter BG.
    var bgimage  = dojo.style(pane, "backgroundImage");
    if (bgimage.toLowerCase().indexOf(".png") == -1)
        return;
    var repeat = dojo.style(pane, "backgroundRepeat");
    dojo.style(pane, "backgroundImage", "none");
    var background = document.createElement("div");
    dojo.attr(background, "class", "background");
    dojo.style(background, "backgroundImage", bgimage);
    dojo.style(background, "backgroundRepeat", repeat);
    dojo.style(background, "overflow", "hidden");
    dojo.place(background, pane, "first");
    utils.style.fix_png_background(background);
    function resizebg() {
        var containerbox = dojo.marginBox(pane);
        dojo.contentBox(background, containerbox);
    }    
    utils.style.updaters.push(resizebg);
    resizebg();
}

utils.style.fix_png_images = function(image, rootnode) {
    // image may be an image element node, the ID of one, or null.
    // rootnode may be the root element of images to be fixed.
    var images;
    if (image)
        images = [dojo.byId(image)];
    else
        images = dojo.query("img", rootnode);
    for (var i=0; i < images.length; i++) {
        var image = images[i];
        var source = dojo.attr(image, "src");
        if (source.toLowerCase().indexOf(".png") == -1)
            continue;
        var width = dojo.style(image, "width");
        var height = dojo.style(image, "height");
        if (width == 0 || height == 0)
            continue;
        dojo.style(image, {
            width: width, 
            height: height, 
            filter: (
                "progid:DXImageTransform.Microsoft.AlphaImageLoader(" + 
                "src='" + source + "', sizingMethod='scale')"
            )
        });
        dojo.attr(image, "src", "/cues/themes/kubrick/images/spacer.gif");
    }
}

utils.style.fix_png_background = function(domnode) {
    var mode;
    var element = dojo.byId(domnode);
    var bgvalue  = dojo.style(element, "backgroundImage");
    if (!bgvalue.toLowerCase().indexOf(".png") == -1)
        return;
    var bgsource = bgvalue.substring(5, bgvalue.length-2);
    var repeat = dojo.style(element, "backgroundRepeat");
    if (repeat == "no-repeat")
        mode = "crop";
    else
        mode = "scale";
    dojo.style(element, {
        backgroundImage: 'url("/cues/themes/kubrick/images/spacer.gif")', 
        filter: ("progid:DXImageTransform.Microsoft.AlphaImageLoader(" + 
                 "src='" + bgsource + "', sizingMethod='" + mode + "')")
    });
};

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
dojo.provide("utils.configure.exporter");
dojo.require("utils.display");
dojo.require("utils.configure.node");
dojo.require("utils.configure.form");
dojo.require("utils.configure.templates");
dojo.require("nbmweb.EventSource");
//CSCte94385
dojo.require("nbmweb.edit.CreateExporter");
dojo.require("nbmweb.edit.DropDownSelect");

utils.configure.exporter.createNodeManager = function(table, configurator) {
    var manager = new utils.configure.exporter.Manager(table, configurator);
    dojo.byId(table).manager = manager;
    return manager;
}

dojo.declare("utils.configure.exporter.Manager",
             utils.configure.node.Manager, {
    constructor: function() {
        this.typeName = "Exporter";
        this.createNodeHref = "/public/nbmweb/edit/forms/CreateExporter.html";
    },
    getRowTemplates: function() {
        return utils.configure.templates.exportRowTemplates;
    },
    editFormatter: function(event) {
        var configure = "configure_formatter";
        var node = utils.configure.node.getTargetName(event);
        var deferred = this.openEditor({
            title: "Edit " + node,
            href: this.editNodeHref,
            onCommit: dojo.hitch(this.configurator, configure, node),
            loadValues: this.configurator.formatter_configuration(node, true)
        });
        deferred.addBoth(function(response) {
            console.log("editFormatter() callback handler:", node, response);
            return response;
        });
        return deferred;
    },
    editTransporter: function(event) {
        var node = utils.configure.node.getTargetName(event);
        var openEditor = dojo.hitch(this, this.openEditor);
        var configure = dojo.hitch(this.configurator, "configure_transporter", node);
        var loadConfig = this.configurator.transporter_configuration(node, true);
        loadConfig.addCallback(function(response) {
            console.log("Configuration loaded:", response);
            var href = "/public/nbmweb/edit/forms/";
            if (response.transport_type == "smtp")
                href += "EditTransporter.html";
            else if (response.transport_type == "ftp")
                href += "EditFtpTransporter.html";
            else if (response.transport_type == "sftp")
                href += "EditFtpTransporter.html";
            else if (response.transport_type == "http-post")
                href += "EditPostTransporter.html";
            else
                href += "EditTransporter.html";
            var deferred = openEditor({
                href: href,
                node: node,
                values: response,
                onCommit: configure,
                readOnly: ['nameInput'],
                title: "Edit " + node
            });
            deferred.addBoth(function(response) {
                console.log("exporter.editTransporter() callback:", node, response);
                return response;
            });
            return deferred;
        });
    }, 
    editSources: function(event) {
        var node = utils.configure.node.getTargetName(event);
        var dialog = new dijit.Dialog({title: node + " Export Triggers"});
        var handle = dojo.connect(dialog, "onLoad", this, function() {
            console.log("sources loaded...", this, event, node);
            var rows = new Array();
            var table = dojo.query("table.event-sources", dialog.domNode)[0];
            var tbody = dojo.query("tbody.configurations", table)[0];
            // Setup cancel-button handling to destroy dialog.
            var cancel = dijit.byId("cancel-button");
            function handleClose() {
                console.log("User cancelled edit.");
                dialog.destroyRecursive();
                dojo.disconnect(cancelHandle);
                dojo.disconnect(closeHandle);
            }
            var cancelHandle = dojo.connect(cancel, "onClick", handleClose);
            var closeHandle = dojo.connect(dialog.closeButtonNode, "onclick", handleClose);

            // Setup commit-button handling to configure triggers.
            var commit = dijit.byId("commit-button");
            var onCommit = dojo.connect(commit, "onClick", this, function() {
                console.log("User committing changes.");
                var config = dojo.map(rows, "return item.getValues();");
                console.log("Submitting trigger config: ", config);
                function cleanup(response) {
                    console.log("Cleaning up dialog...");
                    dialog.destroyRecursive();
                    return response;
                }
                function cb(response) {
                    var message = "Triggers configured";
                    console.log(message, ": ", response);
                    utils.display.success(message, response);
                    return response;
                }
                function eb(response) {
                    var message = "Unable to configure triggers";
                    console.log(message, ": ", response);
                    utils.display.failure(message, response);
                    return response;
                }
                var def = this.configurator.configure_triggers(node, config);
                //CSCtg73465 - reversed the callbacks order so that parent is not
                //              removed before success/failure message is shown.
                //def.addBoth(cleanup);
                def.addCallbacks(cb, eb);
                def.addBoth(cleanup);
                dojo.disconnect(onCommit);
            });
            // Setup configuration load handler to populate dialog.
            function populate(configs) {
                // Content is Manager instance.
                // 'config' is list of {source: nodeURL, events: []}
                // hashes.  The events member is a list of listened
                // to events.
                console.log("Trigger configuration: ", configs);
                dojo.forEach(configs, function(config, index) {
                    var index = tbody.rows.length;
                    var placeHolder = tbody.insertRow(index);
                    var row = new nbmweb.EventSource();
                    row.setValues(config);
                    row.startup();
                    var node = row.domNode;
                    node.id = config.source;
                    if(index == 0)
                        node.style.display = '';
                    dojo.addClass(node, "light");
                    dojo.place(row.domNode, placeHolder, "replace");
                    rows.push(row);
                }, this);
                return configs;
            }
            var callback = dojo.hitch(this, populate);
            var errback = function(response) {
                utils.display.failure("Unable to get sources.", response);
                return response;
            }
            var deferred = this.configurator.trigger_configuration(node);
            deferred.addCallbacks(callback, errback);
            dojo.disconnect(handle);
        });
        dialog.attr(
            "href", "/public/utils/configure/templates/editSources.html");
        dialog.startup();
        dialog.show();
    }
});
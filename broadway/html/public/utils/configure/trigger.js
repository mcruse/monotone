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
dojo.provide("utils.configure.trigger");
dojo.require("dijit.Dialog");
dojo.require("dojo.data.ItemFileWriteStore");
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.grid.cells.dijit");
dojo.require("utils.configure.node");
dojo.require("utils.configure.templates");
dojo.require("nbmweb.edit.CreateTrigger");
dojo.require("nbmweb.edit.DropDownSelect");


utils.configure.trigger.createNodeManager = function(table, configurator) {
    var manager = new utils.configure.trigger.Manager(table, configurator);
    dojo.byId(table).manager = manager;
    return manager;
};

utils.configure.trigger.parsedURL = function(nodeURL) {
    var parsed = {};
    var nameStart = nodeURL.lastIndexOf("/");
    var nodeName = nodeURL.slice(nameStart + 1);
    if (!nodeName)
        parsed.name = "/";
    else
        parsed.name = unescape(nodeName);
    parsed.parent = nodeURL.slice(0, nameStart);
    return parsed;
};

utils.configure.trigger.asItem = function(triggerURL) {
    var item = {url: triggerURL, selected: false};
    dojo.mixin(item, utils.configure.trigger.parsedURL(triggerURL));
    return item;
};

utils.configure.trigger.formatParent = function(parentURL) {
    return utils.configure.trigger.parsedURL(parentURL).name;
};

utils.configure.trigger.findTrigger = function(event) {
    var button;
    if (event.target)
        button = event.target;
    else if (event.currentTarget)
        button = event.currentTarget;
    else
        button = event;
    var node = button;
    while (node.nodeName.toLowerCase() != "tr")
        node = node.parentNode;
    var header = dojo.query("th.trigger-name", node)[0];
    var trigger = header.innerHTML;
    console.debug("findTrigger()", event, button, node, trigger);
    return trigger;
};

dojo.declare("utils.configure.trigger.Manager",
             utils.configure.node.Manager, {
    constructor: function() {
        this.typeName = "Trigger";
        this.editNodeHref = "";
        this.createNodeHref = "/public/nbmweb/edit/forms/CreateTrigger.html";
    },
    getRowTemplates: function() {
        return utils.configure.templates.triggerRows;
    },
    editNode: function(event) {
        var node = utils.configure.node.getTargetName(event);
        var openEditor = dojo.hitch(this, this.openEditor);
        var configure = dojo.hitch(this.configurator, "configure_node", node);
        var loadConfig = this.configurator.node_configuration(node, true);
        loadConfig.addCallback(function(response) {
            console.log("Configuration loaded:", response);
            var href = "/public/nbmweb/edit/forms/";
            if (response.type == "BoundTrigger")
                href += "EditBoundTrigger.html";
            else
                href += "EditComparisonTrigger.html";
            var deferred = openEditor({
                href: href,
                node: node,
                values: response,
                onCommit: configure,
                title: "Edit " + node
            });
            deferred.addBoth(function(response) {
                console.log("trigger.editNode() callback:", node, response);
                return response;
            });
            return deferred;
        });
    },
    editTargets: function(event, template) {
        var configurator = this.configurator;
        var managersURL = "/services/Alarm Managers";
        var targetPage = "/public/utils/configure/templates/editTargets.html";
        var triggerName = utils.configure.node.getTargetName(event);
        var targetStore = new dojo.data.ItemFileWriteStore({
            data: {
                items: [],
                label: "name",
                identifier: "url"
            }
        });
        var loadTargets = configurator.find_targets(true);
        loadTargets.addCallback(function(targetsResponse) {
            console.log("Target list loaded:", this, targetsResponse);
            dojo.forEach(targetsResponse, function(targetURL, index) {
                console.log("loadTargets() handling target:", targetURL);
                targetStore.fetchItemByIdentity({
                    identity: targetURL,
                    onItem: function(item) {
                        console.log("Load targets onItem()", item);
                        if (!item) {
                            item = utils.configure.trigger.asItem(targetURL);
                            item = targetStore.newItem(item);
                            console.log("Created target:", item);
                        } else {
                            console.log("Target exists:", item);
                        }
                    }
                });
            });
            targetStore.save();
            return targetsResponse;
        });
        var loadTargetted = configurator.trigger_targets(triggerName);
        loadTargetted.addCallback(function(selectedResponse) {
            console.log("Selected targets loaded:", this, selectedResponse);
            dojo.forEach(selectedResponse, function(targetURL, index) {
                console.log("loadTargetted() handling target:", targetURL);
                targetStore.fetchItemByIdentity({
                    identity: targetURL,
                    onItem: function(item) {
                        if (!item) {
                            item = utils.configure.trigger.asItem(targetURL);
                            item = targetStore.newItem(item);
                            console.log("Created target:", item);
                        }
                        console.log("Set selected:", item);
                        targetStore.setValue(item, "selected", true);
                    }
                });
            });
            targetStore.save();
            return selectedResponse;
        });
        function saveChanges() {
            console.log("Saving target changes:", this, arguments);
            if (dojo.isIE) {
                console.log("Manually updating store because...IE");
                var targetGrid = dijit.byId("targetGrid");
                if (targetGrid.store !== targetStore)
                    console.log("WARNING, targetGrid.store !== targetStore");
                for (var index=0; index < targetGrid.rowCount; index++) {
                    var item = targetGrid.getItem(index);
                    var gridValue = targetGrid.getCell(2).getValue(index);
                    var storeValue = targetStore.getValue(item, "selected");
                    if (gridValue != storeValue) {
                        var name = targetStore.getValue(item, "name");
                        targetStore.setValue(item, "selected", gridValue);
                        console.log("Store and grid did not match:", name);
                    }
                }
            }
            if (!targetStore.isDirty()) {
                console.log("No changes to commit.");
                return;
            }
            targetStore.fetch({onComplete: function(items, request) {
                console.log("Fetched items from store:", items, request);
                var selected = dojo.filter(items, function(item, index) {
                    return targetStore.getValue(item, "selected");
                });
                console.log("Filtered seleted items:", selected);
                var targets = dojo.map(selected, function(item, index) {
                    return targetStore.getValue(item, "url");
                });
                console.log("Retrieved target URLs:", targets);
                var cd = configurator.configure_targets(triggerName, targets);
                console.log("Invoked configure_targets():",
                            configurator, triggerName, targets);
                cd.addCallback(function(response) {
                    console.log("Targets configured:",
                                triggerName, targets, response);
                    return response;
                });
                cd.addErrback(function(response) {
                    console.log("Target configure failed:",
                                triggerName, targets, response);
                    return response;
                });
           }});
        }
        var dialog = new dijit.Dialog({
            preload: true,
            onCancel: removeThis,
            widgetsInTemplate: true,
            title: triggerName + " Targets"
        });

        function removeThis(){this.destroyRecursive()}

        dialog.attr("class", "editDialog");
        var connection = dojo.connect(dialog, "onLoad", this, function() {
            console.log("Targets page loaded:", this, arguments);
            var grid = dijit.byId("targetGrid");
            var commit = dijit.byId("targetCommit");
            var cancel = dijit.byId("targetCancel");

            function handleClose() {
                console.log("Target edit canceled:", arguments);
                dialog.destroyRecursive();
                dojo.disconnect(onCancel);
                dojo.disconnect(onClose);
            }
            
            var escHandle  = dojo.connect(dialog.domNode, "onkeypress", function(event){
                if(event.charOrCode == dojo.keys.ESCAPE){
                    console.debug("Escape trapped !!!");
                    dojo.stopEvent(event);
                    //handleClose();
                }
            });

            var onCancel = dojo.connect(cancel, "onClick", handleClose); 
            var onClose = dojo.connect(dialog.closeButtonNode, "onClick", handleClose); 
            var onCommit = dojo.connect(commit, "onClick", function(event) {
                console.log("Target edit committing:", arguments);
                dojo.disconnect(onCommit);
                saveChanges();
                dialog.destroyRecursive();
            });
            dojo.disconnect(connection);
            loadTargets.addCallback(function(response) {
                console.log("Load targets callback for dialog:", response);
                grid.setStore(targetStore);
                dialog.show();
                return response;
            });
            loadTargets.addErrback(function (response) {
                var summary = "Failed to load targets";
                var errorMessage = response;
                if (dojo.isObject(response) && response.message)
                    errorMessage = response.message;
                console.error(summary, ": ", response, errorMessage);
                dialog.destroyRecursive();
                utils.display.failure(summary, errorMessage);
                return response;
            });
        });
        dialog.attr("href", targetPage);
    }
});

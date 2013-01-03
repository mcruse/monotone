/*
Copyright (C) 2011 Cisco Systems

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
function getTrendPreferences(trend, srcButton){
    var inputMap = {
        "displayname": ["title"],
        "width": ["width"],
        "height": ["height"],
        "backgroundcolor": ["background", "color"],
        "textsize": ["text", "fontsize"],
        "textcolor": ["text", "color"],
        "textfont": ["text", "fontname"],
        "timespanvalue": ["timespan", "value"],
        "fromaxis1": ["y-axes", "0", "from"],
        "fromaxis1": ["y-axes", "1", "from"],
        "toaxis1": ["y-axes", "0", "to"],
        "toaxis1": ["y-axes", "1", "to"],
        "typeaxis1": ["y-axes", "0", "type"],
        "typeaxis2": ["y-axes", "1", "type"],
        "timespanunit": [],
        "timespanreference": [],
        "enableaxis1": [],
        "enableaxis2": []
    };
    var dialog = new dijit.Dialog({
        title: "Trend Preferences",
        href: "public/nbmweb/trends/TrendPreferencesTemplate.html",
        style: "width:650px",
        onLoad: function(){
            var proxy = new mpx.node.Proxy("/services/Trend Manager");
            var deferred = proxy.get_trend_preferences(trend);
            dojo.byId("trend").value = trend;
            deferred.addCallback(function(preferences){
                console.log(preferences);
                var axisstatus = new Array();
                axisstatus["0"] = axisstatus["false"] = "disabled";
                axisstatus["1"] = axisstatus["true"] = "enabled";
                var reference = new Array();
                reference["Mediator"] = reference["mediator"] = "Mediator";
                reference["utc"] = reference["UTC"] = "UTC";
                reference["browser"] = reference["Browser"] = "Browser";
                
                var form = dojo.byId("trendPreferencesForm");
                
                //populate all the fields from the response
                for (var input in inputMap) {
                    var value = preferences;
                    var arr = inputMap[input];
                    for (var i = 0; i < inputMap[input].length; i++) {
                        value = value[arr[i]];
                    }
                    if (arr.length != 0) 
                        dojo.byId(input).value = value;
                }
                //populate the point preferences table
                var ppTable = dojo.byId("pointPreferencesTable");
                var points = preferences["points"];
                for (var i = 0; i < points.length; i++) {
                    var tr = dojo.doc.createElement("tr");
                    var position = dojo.doc.createElement("td");
                    position.innerHTML = i + 1;
                    position.style.width = "20px";
                    position.style.background = "#D9E3E9";
                    position.style.textAlign = "center";
                    tr.appendChild(position);
                    
                    var name = dojo.doc.createElement("td");
                    name.innerHTML = points[i]["name"];
                    tr.appendChild(name);
                    
                    var color = dojo.doc.createElement("td");
                    var colorInput = new dijit.form.ValidationTextBox({
                        id: "colorpoint" + (i + 1),
                        regExp: "^\#([a-fA-F0-9]{6})$", 
                        name: "colorpoint" + (i + 1),
                        value: points[i]["color"]
                    });
                    inputMap[colorInput.id] = [];
                    color.appendChild(colorInput.domNode);
                    var colorButton = dojo.doc.createElement("button");
                    colorButton.id = "colorpoint" + (i + 1) + "button";
                    colorButton.style.height = "20px";
                    colorButton.onclick = function(){
                        open_color_selector(this.id.split("button")[0], this.id);
                        return false;
                    };
                    colorButton.style.background = points[i]["color"];
                    color.appendChild(colorButton);
                    tr.appendChild(color);
                    
                    var axis = dojo.doc.createElement("td");
                    var axisSelect = dojo.doc.createElement("select");
                    axisSelect.id = "axispoint" + (i + 1);
                    axisSelect.name = "axispoint" + (i + 1);
                    var option1 = dojo.doc.createElement("option");
                    option1.value = option1.innerHTML = "1";
                    axisSelect.appendChild(option1);
                    var option2 = dojo.doc.createElement("option");
                    option2.value = option2.innerHTML = "2";
                    axisSelect.appendChild(option2);
                    axisSelect.selectedIndex = (points[i]['y-axis'] - 1)
                    axis.appendChild(axisSelect);
                    inputMap[axisSelect.id] = [];
                    tr.appendChild(axis);
                    
                    ppTable.appendChild(tr);
                }
                if (points.length > 0) 
                    ppTable.style.display = "";
                
                dojo.byId("backgroundcolorbutton").style.background = preferences.background.color;
                dojo.byId("textcolorbutton").style.background = preferences.text.color;
                dijit.byId("timespanunit").setDisplayedValue(preferences.timespan.unit);
                dijit.byId("timereference").setDisplayedValue(reference[preferences["time-reference"]]);
                dijit.byId("enableaxis1").setDisplayedValue(axisstatus[preferences["y-axes"]["0"].enable]);
                dijit.byId("enableaxis2").setDisplayedValue(axisstatus[preferences["y-axes"]["1"].enable]);
                dijit.byId("typeaxis1").setDisplayedValue(preferences["y-axes"]["0"].type);
                dijit.byId("typeaxis2").setDisplayedValue(preferences["y-axes"]["1"].type);
            });
            deferred.addErrback(function(error){
                console.error("an error occurred!!" + error);
                utils.display.failure(error);
            });
        },
        onHide: function(){
            console.warn("destroying dialog");
            dojo.byId(srcButton).disabled = false;
            dialog.destroyRecursive();
        }
    });
    dialog.attr("class", "editDialog");
    
    var submitForm = function(){
        var deferred = dojo.xhrPost({
            form: dojo.byId("trendPreferencesForm")
        });
        deferred.addCallback(function(response){
            dojo.byId(srcButton).disabled = false;
            console.log("form submitted");
        });
        deferred.addErrback(function(error){
            dojo.byId(srcButton).disabled = false;
            console.warn(error);
            utils.display.failure("Request failed", error);
        });
    };
    
    var submit = new dijit.form.Button({
        label: "Commit",
        onClick: function(){
            var form = dijit.byId("trendPreferencesForm");
            if (form.isValid()) {
                submitForm();
                dialog.hide();
            }
            else {
                console.warn("form not valid");
                return false;
            }
        }
    });
    var cancel = new dijit.form.Button({
        label: "Cancel",
        onClick: function(){
            console.log("operation cancelled");
            dialog.hide();
        }
    });
    dialog.domNode.appendChild(submit.domNode);
    dialog.domNode.appendChild(cancel.domNode);
    dialog.startup();
    dialog.show();
}

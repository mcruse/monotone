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
dojo.provide("utils.configure.templates");
dojo.require("dijit.form.Form");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.TextBox");
dojo.require("dijit.form.CheckBox");
dojo.require("dijit.form.FilteringSelect");

utils.configure.templates.createNode = (
    '<form dojoType="dijit.form.Form" id="create-node" method="post" class="create-node">\n' +
    '    <table class="configuration">\n' +
    '        <tbody>\n' +
    '            <tr class="table-header">\n' +
    '                <th>Attribute</th>\n' +
    '                <th class="control">Value</th>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Name</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="name"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '        </tbody>\n' +
    '    </table>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="cancel-button">cancel</button>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="commit-button">create</button>\n' +
    '</form>'
);

utils.configure.templates.editNode = (
    '<form dojoType="dijit.form.Form" method="post" id="edit-node" class="edit-node">\n' +
    '    <table class="configuration">\n' +
    '        <tbody>\n' +
    '            <tr class="table-header">\n' +
    '                <th>Attribute</th>\n' +
    '                <th class="control">Value</th>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Name</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="name"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '        </tbody>\n' +
    '    </table>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="cancel-button">cancel</button>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="commit-button">commit</button>\n' +
    '</form>'
);

utils.configure.templates.editFormatter = (
    '<form dojoType="dijit.form.Form" method="post" id="edit-formatter" class="edit-node">\n' +
    '    <table class="configuration">\n' +
    '        <tbody>\n' +
    '            <tr class="table-header">\n' +
    '                <th>Attribute</th>\n' +
    '                <th class="control">Value</th>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Name</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="name"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '        </tbody>\n' +
    '    </table>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="cancel-button">cancel</button>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="commit-button">commit</button>\n' +
    '</form>'
);

utils.configure.templates.editTransporter = (
    '<form dojoType="dijit.form.Form" method="post" id="edit-transporter" class="edit-node">\n' +
    '    <table class="configuration">\n' +
    '        <tbody>\n' +
    '            <tr class="table-header">\n' +
    '                <th>Attribute</th>\n' +
    '                <th class="control">Value</th>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Name</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="name"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Username</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="username"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Authenticate</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.CheckBox" \n' +
    '                        type="checkbox" name="authenticate" />\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Password</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="password" name="password"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Domain</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="custom_domain"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Recipients</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="recipients"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>As attachment</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.CheckBox" \n' +
    '                        type="checkbox" name="as_attachment" />\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Subject</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="subject"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Subtype</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="subtype"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Host</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="host"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Timeout</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="timeout"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Port</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="port"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Sender</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="sender"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '        </tbody>\n' +
    '    </table>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="cancel-button">cancel</button>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="commit-button">commit</button>\n' +
    '</form>'
);

utils.configure.templates.editTrigger = (
    '<form dojoType="dijit.form.Form" method="post" id="edit-node" class="edit-node">\n' +
    '    <table class="configuration">\n' +
    '        <tbody>\n' +
    '            <tr class="table-header">\n' +
    '                <th>Attribute</th>\n' +
    '                <th class="control">Value</th>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Trigger name</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="name"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Poll period</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="poll_period"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <th>Hysteresis</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="hysteresis"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="dark">\n' +
    '                <th>Trigger Message</th>\n' +
    '                <td class="control">\n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" name="message" \n' +
    '                        value="input is less than ${constant}"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '            <tr class="light">\n' +
    '                <td colspan="2">\n' +
    '                    Alarm when node\n ' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" id="input-node" name="input"/>\n' +
    '                    <button type="button" dojoType="dijit.form.Button">\n' +
    '                        <script type="dojo/method" event="onClick" args="evt">\n' +
    '                            console.log("onClick()", this, evt);\n' +
    '                            utils.select.nodes.open("input-node");\n' +
    '                        </script>\n' +
    '                        select\n' +
    '                    </button> \n' +
    '                    is \n' +
    '                    <select name="comparison" size="5" \n' +
    '                        dojoType="dijit.form.FilteringSelect">\n' +
    '                       <option></option>\n' +
    '                       <option name="less_than" value="less_than">&lt;</option>\n' +
    '                       <option name="greater_than" value="greater_than">&gt;</option>\n' +
    '                    </select> \n' +
    '                    than constant \n' +
    '                    <input dojoType="dijit.form.TextBox" \n' +
    '                        type="text" id="constant" name="constant"/>\n' +
    '                </td>\n' +
    '            </tr>\n' +
    '        </tbody>\n' +
    '    </table>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="cancel-button">cancel</button>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="commit-button">commit</button>\n' +
    '</form>'
);

utils.configure.templates.editTargets = (
    '<form dojoType="dijit.form.Form" method="post" id="edit-targets" class="edit-node">\n' +
    '    <table class="configuration">\n' +
    '        <tbody>\n' +
    '            <tr class="table-header">\n' +
    '                <th>Targets</th>\n' +
    '                <th class="control"></th>\n' +
    '            </tr>\n' +
    '        </tbody>\n' +
    '    </table>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="cancel-button">cancel</button>\n' +
    '    <button dojoType="dijit.form.Button" type="button" id="commit-button">commit</button>\n' +
    '</form>'
);

utils.configure.templates.nodeRows = [
    ('<tr class="light">\n' +
     '    <th class="node-name"></th>\n' +
     '    <td class="node-action edit-node">\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editNode(evt);\n' +
     '            </script>\n' +
     '            edit\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).deleteNode(evt);\n' +
     '            </script>\n' +
     '             - \n' +
     '        </button>\n' +
     '    </td>\n' +
     '</tr>'),
    ('<tr class="dark">\n' +
     '    <th class="node-name"></th>\n' +
     '    <td class="node-action edit-node">\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editNode(evt);\n' +
     '            </script>\n' +
     '            edit\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).deleteNode(evt);\n' +
     '            </script>\n' +
     '             - \n' +
     '        </button>\n' +
     '    </td>\n' +
     '</tr>')
 ];

utils.configure.templates.triggerRows = [
    ('<tr class="light">\n' +
    '    <th class="trigger-name"></th>\n' +
    '    <td class="trigger-action edit-trigger">\n' +
    '        <button type="button" dojoType="dijit.form.Button">\n' +
    '            <script type="dojo/method" event="onClick" args="evt">\n' +
    '                console.log("onClick()", this, evt);\n' +
    '                dojo.byId("triggers-table").manager.editNode(evt);\n' +
    '            </script>\n' +
    '            edit\n' +
    '        </button>&nbsp;\n' +
    '        <button type="button" dojoType="dijit.form.Button">\n' +
    '            <script type="dojo/method" event="onClick" args="evt">\n' +
    '                console.log("onClick()", this, evt);\n' +
    '                dojo.byId("triggers-table").manager.editTargets(evt);\n' +
    '            </script>\n' +
    '            targets\n' +
    '        </button>&nbsp;\n' +
    '        <button type="button" dojoType="dijit.form.Button">\n' +
    '            <script type="dojo/method" event="onClick" args="evt">\n' +
    '                console.log("onClick()", this, evt);\n' +
    '                dojo.byId("triggers-table").manager.deleteNode(evt);\n' +
    '            </script>\n' +
    '             - \n' +
    '        </button>\n' +
    '    </td>\n' +
    '</tr>'),
    ('<tr class="dark">\n' +
        '    <th class="trigger-name"></th>\n' +
        '    <td class="trigger-action edit-trigger">\n' +
        '        <button type="button" dojoType="dijit.form.Button">\n' +
        '            <script type="dojo/method" event="onClick" args="evt">\n' +
        '                console.log("onClick()", this, evt);\n' +
        '                dojo.byId("triggers-table").manager.editNode(evt);\n' +
        '            </script>\n' +
        '            edit\n' +
        '        </button>&nbsp;\n' +
        '        <button type="button" dojoType="dijit.form.Button">\n' +
        '            <script type="dojo/method" event="onClick" args="evt">\n' +
        '                console.log("onClick()", this, evt);\n' +
        '                dojo.byId("triggers-table").manager.editTargets(evt);\n' +
        '            </script>\n' +
        '            targets\n' +
        '        </button>&nbsp;\n' +
        '        <button type="button" dojoType="dijit.form.Button">\n' +
        '            <script type="dojo/method" event="onClick" args="evt">\n' +
        '                console.log("onClick()", this, evt);\n' +
        '                dojo.byId("triggers-table").manager.deleteNode(evt);\n' +
        '            </script>\n' +
        '             - \n' +
        '        </button>\n' +
        '    </td>\n' +
        '</tr>'
)];



utils.configure.templates.exportRowTemplates = [
    ('<tr class="light">\n' +
     '    <th class="node-name"></th>\n' +
     '    <td class="node-action edit-node">\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editNode(evt);\n' +
     '            </script>\n' +
     '            edit\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editSources(evt);\n' +
     '            </script>\n' +
     '            sources\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editTransporter(evt);\n' +
     '            </script>\n' +
     '            transporter\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).deleteNode(evt);\n' +
     '            </script>\n' +
     '             - \n' +
     '        </button>\n' +
     '    </td>\n' +
     '</tr>'),
    ('<tr class="dark">\n' +
     '    <th class="node-name"></th>\n' +
     '    <td class="node-action edit-node">\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editNode(evt);\n' +
     '            </script>\n' +
     '            edit\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editSources(evt);\n' +
     '            </script>\n' +
     '            sources\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).editTransporter(evt);\n' +
     '            </script>\n' +
     '            transporter\n' +
     '        </button>&nbsp;\n' +
     '        <button type="button" dojoType="dijit.form.Button">\n' +
     '            <script type="dojo/method" event="onClick" args="evt">\n' +
     '                console.log("onClick()", this, evt);\n' +
     '                utils.configure.node.getManager(evt).deleteNode(evt);\n' +
     '            </script>\n' +
     '             - \n' +
     '        </button>\n' +
     '    </td>\n' +
     '</tr>')
 ];

utils.configure.templates.cloudRowTemplates = [
      ('<tr class="light">\n' +
       '    <th class="node-name"></th>\n' +
       '    <td class="node-action edit-node">\n' +
       '        <button type="button" dojoType="dijit.form.Button">\n' +
       '            <script type="dojo/method" event="onClick" args="evt">\n' +
       '                console.log("onClick()", this, evt);\n' +
       '                utils.configure.node.getManager(evt).deleteNode(evt);\n' +
       '            </script>\n' +
       '             - \n' +
       '        </button>\n' +
       '    </td>\n' +
       '</tr>'),
      ('<tr class="dark">\n' +
       '    <th class="node-name"></th>\n' +
       '    <td class="node-action edit-node">\n' +
       '        <button type="button" dojoType="dijit.form.Button">\n' +
       '            <script type="dojo/method" event="onClick" args="evt">\n' +
       '                console.log("onClick()", this, evt);\n' +
       '                utils.configure.node.getManager(evt).deleteNode(evt);\n' +
       '            </script>\n' +
       '             - \n' +
       '        </button>\n' +
       '    </td>\n' +
       '</tr>')
   ];

"""
Copyright (C) 2007 2009 2010 2011 Cisco Systems

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
"""
"""
    Security manager forms are accessed via a "manage" parameter.
    The "manage" parameter may be passed via query string or 
    POST data.  The value of "manage" needs to be the name of 
    one of the managers under the Security Manager.  Such as 
    "Roles", "Users", or "Policies".
    
    The Simple Manager Form provides base adaptation that is 
    easily extended by subclasses to provide manager specific 
    child node table lists, edit, remove, and create buttons.
    
    Handling of these forms on the client is asynchronous and 
    tailored by applying custom attributes to the form and field 
    elements.  
    
    The target ID attribute may be attached to a form in order to 
    specify which element from the currently displayed page should 
    be replaced with the corresponding element in the returned page.
    
    The target Type attribute may be used to specify that the form 
    submitted should be replaced by itself from the response, using 
    the "self" value; or to specify that the response be displayed 
    in a pop-up dialog box, using the "dialog" value; or that the 
    widget containing the submitted form have its content replaced 
    with returned page.
    
    Note that if the submitted form is already displayed inside of 
    a dialog box, then the target Type "self" will prevent the dialog 
    box from closing.  All other targeting specifications are applied 
    relative to the form that opened the dialog box.
"""
import cgi
import itertools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.lib.configure import as_boolean
from mpx.lib.node import as_node
from mpx.service.security.interfaces import ISimpleManager
from mpx.service.security.interfaces import ISecurityManager
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.htmlgen import *
from mpx.lib import msglog

class HTMLSimpleManagerForm(object):
    implements(IWebContent)
    adapts(ISimpleManager)
    def __init__(self, manager):
        self.manager = manager
        self.path = None
        self.base_doc = HTMLgen.SimpleDocument()
        self.security_manager = as_node("/services/Security Manager")
    def get_request_path(self):
        return self.path
    def get_page_heading(self):
        return self.manager.name
    def get_page_title(self):
        return self.manager.name
    def get_column_names(self):
        return ['Name']
    def get_row_values(self, child):
        values = []
        for header in self.get_column_names():
            values.append(getattr(child, header.lower()))
        return values
    def get_row_actions(self, child = None):
        actions = []
        if not hasattr(child, 'is_removable') or child.is_removable():
            actions.append('remove')
        if not hasattr(child, 'is_configurable') or child.is_configurable():
            actions.append('edit')
        return actions
    def get_action_behaviour(self, action):
        if action == 'remove':
            return "return confirm('Delete child and its configuration?');"
        return ''
    def get_allowed_additions(self):
        return ['Child']
    def add_child_form(self, content):
        return
    def render(self, path=None):
        attrs = KeyWordAssist()
        secured_manager = self.security_manager.as_secured_node(self.manager)
        permitted = False
        try:
            permitted = secured_manager.is_manage_users_capable()
        except: 
            pass
        if path is not None:
            self.path = path
        request_path = self.get_request_path()
        if request_path is None:
            raise Exception('Adapter does not know request path.')
        tableid = "%s-config-table" % self.manager.name.lower()
        encoded = cgi.escape(self.manager.name)
        manager = HTMLgen.Input(name='manager', type='hidden', value=encoded)
        
        content = HTMLgen.Div(**attrs('class','section'))
        table = HTMLgen.TableLite(id=tableid)
        setattr(table, "class", "configuration-table configureNodesTable")
        headrow = HTMLgen.TR(**attrs('class','table-header'))
        for header in self.get_column_names() + ['Action']:
            headcell = HTMLgen.TH(header, scope="col", id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")
            headrow.append(headcell)
        table.append(headrow) 
        classes = itertools.cycle(["light", "dark"])
        children = []
            
        if permitted:
            children = self.manager.children_nodes()
        elif self.manager.name == 'Users':
            children.append(self.manager.user_from_current_thread())
        else:
            return("<span style='color:red;'>You are not Authorized to view this page</span>")
        _children = []
        _default = []
        for child in children:
            if hasattr(child, 'is_removable') and child.is_removable():
                _default.append(child)
            else:
                _children.append(child)
        _default = sorted(_default, key=lambda child: child.name.lower())
        _children = sorted(_children, key=lambda child: child.name.lower())
        _children.extend(_default)
        children = _children
        
        for child in children:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            encoded = cgi.escape(child.name)
            node = HTMLgen.Input(name='node', type='hidden', value=encoded)
            cells = self.get_row_values(child)
            # First value is assumed to be row header.
            row.append(HTMLgen.TH(cells[0]))
            # Any other values are added as regular cells.
            for value in cells[1:]:
                row.append(HTMLgen.TD(value))
            actioncell = HTMLgen.TD(**attrs('class', "control"))
            actions = self.get_row_actions(child)
            for action in actions:
                if action in ("remove", "add") and not permitted:
                    continue
                actionform = HTMLgen.Form(request_path)
                formId = action + "_" + cgi.escape(child.name)
                #form name will be set as title of the dialog
                if action == "permissions":
                    actionform.name = "Permissions"
                elif action == "roles":
                    actionform.name = "Assign Roles"
                else:                    
                    actionform.name = action.title() + " %s" % self.manager.name                
                actionform.append(manager)
                actionform.append(node)
                encoded = cgi.escape(action)
                if action in ("add", "remove"):
                    actioninput = HTMLgen.Input(
                        name='actionName', type='hidden', value=encoded)
                    actionform.append(actioninput)
                if action in ("add", "edit"):
                    section = HTMLgen.Input(
                        name='section', type='hidden', value="main")
                    actionform.append(section)
                    actionform = adorn(actionform, targetType="dialog")
                elif action != "remove":
                    section = HTMLgen.Input(
                        name='section', type='hidden', value=encoded)                    
                    actionform.append(section)
                    actionform = adorn(actionform, targetType="dialog")
                else:
                    actionform = adorn(actionform, targetID=tableid, id=formId)
                if action != 'remove':
                    actionform.submit.value = encoded
                else:
                    session_manager = as_node('/services/session_manager')
                    actionform.submit.value = ' - '
                    if (session_manager.is_user_active(cgi.escape(child.name)) == True):
                        actionform.submit.onClick = ("return(confirmDialog('"
                                                 + formId +"', "
                                                 + "'Active user! Are you sure you want to delete <b>" 
                                                 + cgi.escape(child.name) + "</b> and "
                                                 + "its configurations?', false));")
                    else:
                        actionform.submit.onClick = ("return(confirmDialog('"
                                                 + formId +"', "
                                                 + "'Are you sure you want to delete <b>" 
                                                 + cgi.escape(child.name) + "</b> and "
                                                 + "its configurations?', false));")
                actioncell.append(actionform)
                if action != actions[-1]:
                    actioncell.append(' ')
            row.append(actioncell)
            table.append(row)
        content.append(table)
        if permitted:
            self.add_child_form(content)
        return str(content)

register_adapter(HTMLSimpleManagerForm)

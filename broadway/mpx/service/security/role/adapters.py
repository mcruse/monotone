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
    POST data.
    
    The Role Manager's edit form allows users to create, edit, and 
    remove Role nodes.  Role nodes are only configured with a name.
    The Role Manager's form displays a list of existing Role nodes, 
    along with buttons for creating new Role nodes.  The existing 
    Role instances are listed with edit and remove actions available.
    
    Creating a new Role node is similar to editing an existing node 
    instance.  This is because the process of creating new Role nodes 
    first creates a new Role node, providing a default name as a place 
    holder.  The configuration editor for that Role node is then 
    launched automatically, assuming users will desire to provide a 
    name other than the default.  
"""
import cgi
import copy
import string
import urllib
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.backports import Dictionary
from mpx.www.w3c.xhtml.interfaces import IWebContent
from interfaces import IRoleManager
from interfaces import IRole
from mpx.service.security.adapters import HTMLSimpleManagerForm
from mpx.lib.htmlgen import *

addform = """
<form action="/securityconfig" method="POST" id="main" onSubmit="return false">

<input type="hidden" value="Roles" name="manager">
<input type="hidden" value="add" name="actionName">
<table class="nodeEditTable nodeEditContent" style="margin-bottom:10px;">
    <tr>
        <th>Name</th>
        <td>
            <input dojoType="dijit.form.TextBox" type="text" value="" name="configure.name">
        </td>
    </tr>
</table>
<input type="submit" value="commit" name="SubmitButton" style="display: none;">
</form>
"""
addform = urllib.quote(addform)

class HTMLRoleManagerForm(HTMLSimpleManagerForm):
    adapts(IRoleManager)
    def add_child_form(self,content):
        popup = HTMLgen.Form("#")
        popup.submit.value = "+"
        popup.submit.name = "Add Role"
        popup.submit.onClick = "return popup_form(this, '%s', true)" % addform
        content.append(popup)
    def get_allowed_additions(self):
        return ['Role']

register_adapter(HTMLRoleManagerForm, [IRoleManager])

class HTMLRoleForm(object):
    implements(IWebContent)
    adapts(IRole)

    def __init__(self, role):
        self.role = role
        self.base_doc = HTMLgen.SimpleDocument(title='Role Editor')

    def render(self, request_path):
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        encoded = cgi.escape(self.role.parent.name)
        manager = HTMLgen.Input(name='manager', type='hidden', value=encoded)
        encoded = cgi.escape(self.role.name)
        node = HTMLgen.Input(name='node', type='hidden', value=encoded)
        config_form = HTMLgen.Form(request_path)
        config_form.append(manager)
        config_form.append(node)
        config_form.submit.value = 'commit'
        hidden = HTMLgen.Input(
            name="actionName",type='hidden',value="configure")
        config_form.append(hidden)
        config_section = HTMLgen.Div(**attrs('class','section'))
        config_table = HTMLgen.TableLite(**attrs('class', 'configuration'))
        headrow = HTMLgen.TR(**attrs('class', 'table-header'))
        for header in ['Attribute', 'Value']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Value":
                setattr(headcell, "class", "control")            
            headrow.append(headcell)
        config_table.append(headrow)

        configrows = []
        rowclasses = ['light', 'dark']
        config = Dictionary(self.role.configuration())

        namerow = HTMLgen.TR(**attrs('class', rowclasses[len(configrows) % 2]))
        namerow.append(HTMLgen.TH('Role Name'))
        namefield = HTMLgen.Input(value = config.pop('name'), name = 'configure.name')
        namefield.onFocus="this.readOnly=true;this.style.color='grey'"
        namerow.append(HTMLgen.TD(namefield, **attrs('class', 'control')))
        configrows.append(namerow)

        config_table.append(*configrows)
        config_form.append(config_table)
        config_section.append(adorn(config_form, id="main"))
        document.append(config_section)
        return str(document)

register_adapter(HTMLRoleForm)


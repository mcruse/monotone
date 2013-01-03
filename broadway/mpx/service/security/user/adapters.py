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
import cgi
import copy
import string
import urllib
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.backports import Dictionary
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.service.security.adapters import HTMLSimpleManagerForm
from interfaces import IUser
from interfaces import IUserManager
from mpx.lib.htmlgen import *

addform = """
<form action="/securityconfig" method="post" id="main">
    <input type="hidden" value="Users" name="manager"/>
    <input type="hidden" value="add" name="actionName"/>
        
    <table class="nodeEditTable nodeEditContent" style="margin-bottom:10px;">
    <tbody>
        <tr>
            <th>Username</th>
            <td>
                <input dojoType="dijit.form.TextBox" type="text" value="" name="configure.name"/>
            </td>
        </tr>
        <tr>
            <th>Password</th>
            <td>
                <input dojoType="dijit.form.TextBox" type="password" value="" name="configure.password"/>
            </td>
        </tr>
        <tr>
            <th>Confirm Password</th>
            <td>
                <input dojoType="dijit.form.TextBox" type="password" value="" name="configure.password"/>
            </td>
        </tr>
        <tr>
            <th>Homepage</th>
            <td>
                <input dojoType="dijit.form.TextBox" type="text" id="homepage" value="/" name="configure.homepage" />
                <input type="button" onclick="utils.select.files.open('homepage');" value="..." name="homepage" />
            </td>
        </tr>
        <tr>
            <th>System Administrator</th>
            <td>
                <input dojoType="dijit.form.CheckBox" type="checkbox" name="configure.roles" value="System Administrator"/>
            </td>
        </tr>
    </tbody>
    </table>
    <input type="submit" value="commit" name="SubmitButton" style="display: none;"/>
</form>
"""
addform = urllib.quote(addform)

class HTMLUserManagerForm(HTMLSimpleManagerForm):
    adapts(IUserManager)
    def render(self, *args):
        content = super(HTMLUserManagerForm, self).render(*args)
        popup = HTMLgen.Form("#")
        popup.submit.value = " + "
        popup.submit.name = "Add User"
        popup.submit.onClick = "return popup_form(this, '%s', true)" % addform
        return "\n".join([content, str(popup)])
    def get_row_actions(self, child):
        actions = []
        if not hasattr(child, 'is_configurable') or child.is_configurable():
            actions.append('edit')
        actions.append("roles")
        if not hasattr(child, 'is_removable') or child.is_removable():
            actions.append('remove')
        return actions
    def get_allowed_additions(self):
        """Special handling of User addition appended to form by render."""
        return []

register_adapter(HTMLUserManagerForm, [IUserManager])

class IdentifiedInput(HTMLgen.Input):
    def __init__(self, *args, **kw):
        self.id = kw.get('id', '')
        if kw.has_key('id'):
            del(kw['id'])
        HTMLgen.Input.__init__(self, *args, **kw)

    def __str__(self):
        output = HTMLgen.Input.__str__(self)
        fragments = output.split(' ')
        if self.id:
            fragments.insert(1, 'ID="%s"' % self.id)
        return string.join(fragments, ' ')

class IdentifiedForm(HTMLgen.Form):
    def __init__(self, *args, **kw):
        self.id = kw.get('id', '')
        if kw.has_key('id'):
            del(kw['id'])
        HTMLgen.Form.__init__(self, *args, **kw)

    def __str__(self):
        output = HTMLgen.Form.__str__(self)
        fragments = output.split(' ')
        if self.id:
            fragments.insert(1, 'ID="%s"' % self.id)
        return string.join(fragments, ' ')

class ClassifiedForm(IdentifiedForm):
    def __init__(self, *args, **kw):
        self.className = kw.get('class', '')
        if kw.has_key('class'):
            del(kw['class'])
        IdentifiedForm.__init__(self, *args, **kw)

    def __str__(self):
        output = IdentifiedForm.__str__(self)
        fragments = output.split(' ')
        if self.className:
            if len(fragments) > 2:
                fragments.insert(2, 'class="%s"' % self.className)
            else: fragments.insert(1, 'class="%s"' % self.className)
        return string.join(fragments, ' ')

class AutoIdentified(object):
    def __init__(self, etype, prefix = None):
        self.etype = etype
        if prefix is None:
            prefix = etype.__name__
        self.prefix = prefix + '%s'
        self.current_id = 0
    def __call__(self, *args, **kw):
        if not kw.has_key('id'):
            idnumber = self.current_id
            self.current_id += 1
            kw['id'] = self.prefix % idnumber
        return self.etype(*args, **kw)

class HTMLUserForm(object):
    implements(IWebContent)
    adapts(IUser)

    def __init__(self, user):
        self.user = user
        self.base_doc = HTMLgen.SimpleDocument(title='User Editor')
    def render(self, request_path):
        from mpx.service.trendmanager.trendutil import DojoInput, CustomInput
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        page_heading = HTMLgen.Heading(
            2, 'Edit %s' % self.user.name, id="editorlabel")
        document.append(page_heading)
        container = HTMLgen.Div(id="forms")
        
        encoded = cgi.escape(self.user.parent.name)
        manager = HTMLgen.Input(name='manager', type='hidden', value=encoded)
        encoded = cgi.escape(self.user.name)
        node = HTMLgen.Input(name='node', type='hidden', value=encoded)
        config_form = HTMLgen.Form(request_path)
        config_form.append(manager)
        config_form.append(node)
        config_form.submit.value = 'commit'
        hidden = HTMLgen.Input(
            name="actionName",type='hidden',value="configure")
        config_form.append(hidden)
        config_table = HTMLgen.TableLite(
            **{'class': 'nodeEditTable nodeEditContent', 'style': 'margin-bottom:10px;'})
        
        configrows = []
        config = Dictionary(self.user.configuration())

        namerow = HTMLgen.TR()
        namerow.append(HTMLgen.TH('Username'))
        namefield = DojoInput(**{'value': config.pop('name'), 
                                 'name': 'configure.name', 
                                 'disabled': True})
        #if namefield.value in ["mpxadmin" , "Anonymous"]:
        #always disabling change of username: username is a key field 
        #namefield.onFocus="this.readOnly=true;this.style.color='grey'"
        namerow.append(HTMLgen.TD(namefield))
        configrows.append(namerow)
        
        oldpasswordrow = HTMLgen.TR()
        oldpasswordrow.append(HTMLgen.TH('Old Password'))
        oldpasswordfield = DojoInput(**{'type': 'password',
                                        'name': 'configure.old_password'})
        oldpasswordrow.append(HTMLgen.TD(oldpasswordfield, **attrs('class', 'control')))
        configrows.append(oldpasswordrow)
        
        passwordrow = HTMLgen.TR()
        passwordrow.append(HTMLgen.TH('New Password'))
        password = config.pop('password')
        passwordfield = DojoInput(**{'type': 'password',
                                     'name': 'configure.password'})
        passwordrow.append(HTMLgen.TD(passwordfield, **attrs('class', 'control')))
        configrows.append(passwordrow)
        confirmrow = HTMLgen.TR()
        confirmrow.append(HTMLgen.TH('Confirm Password'))
        confirmfield = DojoInput(**{'type': 'password',
                                    'name': 'configure.password'})
        confirmrow.append(HTMLgen.TD(confirmfield, **attrs('class', 'control')))
        configrows.append(confirmrow)
        homepagerow = HTMLgen.TR()
        homepagerow.append(HTMLgen.TH('User Homepage'))
        homepagecell = HTMLgen.TD(**attrs('class', 'control'))
        homepagefield = DojoInput(**{'value': config.pop('homepage'),
                                     'name': 'configure.homepage',
                                     'id': 'homepage'})
        homepagecell.append(homepagefield)
        browsebutton = HTMLgen.Input(type='button', value='...', name = 'homepage')
        browsebutton.onClick = "utils.select.files.open('%s');" % homepagefield.id
        homepagecell.append(browsebutton)
        homepagerow.append(homepagecell)
        configrows.append(homepagerow)

        config_table.append(*configrows)
        config_form.append(config_table)
        container.append(adorn(config_form, id="main"))

        ###
        # Roles part of page.
        roles_table = HTMLgen.TableLite(**{'class': 'nodeEditTable nodeEditContent',
                                           'style': 'margin-bottom: 10px; width: 250px;'})
        
        roleform = HTMLgen.Form(request_path)
        roleform.name = "Assign Roles"
        roleform.append(manager)
        roleform.append(node)
        roleform.submit.value = 'commit'
        action = HTMLgen.Input(name="actionName",type='hidden',value="invoke")
        method = HTMLgen.Input(
            name="methodName",type="hidden",value='set_roles')
        roleform.append(action)
        roleform.append(method)

        rolerows = []
        roles = self.user.parent.parent.role_manager.get_role_names()
        adminrole = self.user.parent.parent.role_manager.administrator.name
        roles = sorted(roles, key=lambda role: role.lower())
        assignedroles = self.user.get_roles()
        if adminrole in assignedroles:
            roles = [adminrole]
            # duplicating the 'params' variable, as the dijit CheckBox
            # toggling cannot be identified by the HTML form. 
            roleform.append(HTMLgen.Input(name="params", type="hidden", value=adminrole))
        else:
            roles.remove(adminrole)
        
        for role in roles:
            rolerow = HTMLgen.TR()
            rolerow.append(HTMLgen.TH(role))
            encoded_role = cgi.escape(role)
            field = DojoInput(
                dojoType='dijit.form.CheckBox', type="checkbox", checked=(role in assignedroles),
                name='params', value = encoded_role, readOnly = (role == adminrole))
            rolecell = HTMLgen.TD(**attrs('style', 'width:25px;'))
            rolecell.append(field)
            rolerow.append(rolecell)
            rolerows.append(rolerow)
        roles_table.append(*rolerows)
        roleform.append(roles_table)
        container.append(adorn(roleform, id="roles"))
        document.append(container)
        return str(document)

register_adapter(HTMLUserForm)


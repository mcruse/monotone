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
import itertools
import urllib
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.backports import Dictionary
from mpx.lib.configure import as_boolean
from mpx.www.w3c.xhtml.interfaces import IWebContent
from interfaces import IPolicyManager
from interfaces import IPolicy
from mpx.service.security.adapters import HTMLSimpleManagerForm
from mpx.lib.htmlgen import *
from mpx.lib import msglog
from mpx.service.trendmanager.trendutil import DojoInput

addform = """
<form action="/securityconfig" method="POST" id="main">
<input type="hidden" value="Policies" name="manager">
<input type="hidden" value="add" name="actionName">
<table class="nodeEditTable nodeEditContent" style="margin-bottom:10px;">
    <tbody>
        <tr>
            <th>Name</th>
            <td class="control">
                <input dojoType="dijit.form.TextBox" type="text" value="" name="configure.name">
            </td>
        </tr>
        <!--<tr class="dark">
        <th>Acquires Existing Assertions</th>
        <td class="control">
            <select size="1" name="configure.acquires">
                <option value="True">Yes</option>
                <option value="False">No</option>
            </select>
        </td>
        </tr>-->
        <tr>
        <th>Policy Context</th>
        <td>
            <input dojoType="dijit.form.TextBox" type="text" value="" name="configure.context" id="context">
            <input type="button" onclick="utils.select.nodes.open('context');" value="Select" name="context">
        </td>
        </tr>
    </tbody>
</table>
<input type="submit" value="commit" name="SubmitButton" style="display: none;">
</form>
"""
addform = urllib.quote(addform)

class HTMLPolicyManagerForm(HTMLSimpleManagerForm):
    adapts(IPolicyManager)
    def add_child_form(self,content):
        popup = HTMLgen.Form("#")
        popup.submit.value = "+"
        popup.submit.name = "Add Policy"
        popup.submit.onClick = "return popup_form(this, '%s', true)" % addform
        content.append(popup)
        
    def get_row_actions(self, child):
        actions = []
        if child.is_configurable():
            actions.append('edit')
            actions.append('permissions')
        if child.is_removable():
            actions.append('remove')
        return actions
    
    def get_allowed_additions(self):
        return ['Policy']

register_adapter(HTMLPolicyManagerForm, [IPolicyManager])

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

class StandardizedOption(object):
    def __init__(self, text, name = None, value = None, selected = False):
        self.text = text
        self.name = name
        self.value = value
        self.selected = selected
    def select(self):
        self.selected = True
    def deselect(self):
        self.selected = False
    def __str__(self):
        element = '<option'
        if self.name is not None:
            element += ' name="%s"' % self.name
        if self.value is not None:
            element += ' value="%s"' % self.value
        element += '>%s</option>' % self.text
        return element

class StandardizedSelect(HTMLgen.Select):
    def __init__(self, options, *args, **kw):
        self.options = options
        HTMLgen.Select.__init__(self, ('',), *args, **kw)
    def __str__(self):
        open, close = HTMLgen.Select.__str__(self).split('<OPTION>\n')
        options = map(str, self.options)
        return open + string.join(options, '\n') + close

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

class HTMLPolicyForm(object):
    implements(IWebContent)
    adapts(IPolicy)
    def update_control(self,field,attr):
        if self.policy.get_readOnly(attr):
            field = adorn(field,('disabled','true'))
        return field
    
    def __init__(self, policy):
        self.policy = policy
        self.base_doc = HTMLgen.SimpleDocument(title='Policy Editor')
    def render(self, request_path):
        attrs = KeyWordAssist()
        
        document = self.base_doc.copy()
        page_heading = HTMLgen.Heading(
            2, 'Edit %s' % self.policy.name, id="editorlabel")
        document.append(page_heading)
        encoded = cgi.escape(self.policy.parent.name)
        manager = HTMLgen.Input(name='manager', type='hidden', value=encoded)
        encoded = cgi.escape(self.policy.name)
        node = HTMLgen.Input(name='node', type='hidden', value=encoded)
        config_form = HTMLgen.Form(request_path)
        config_form.append(manager)
        config_form.append(node)
        config_form.submit.value = 'commit'
        hidden = HTMLgen.Input(
            name="actionName",type='hidden',value="configure")
        config_form.append(hidden)
        
        config_section = HTMLgen.Div(**attrs('class','section'))
        config_table = HTMLgen.TableLite(
            **{'class': 'nodeEditTable nodeEditContent', 'style': 'margin-bottom:10px;'})
        config_header = HTMLgen.TR(**attrs('class', 'table-header'))
        config_table.append(config_header)

        configrows = []
        config = Dictionary(self.policy.configuration())

        namerow = HTMLgen.TR()
        namerow.append(HTMLgen.TH('Name'))
        namefield = DojoInput(**{'value': config.pop('name'), 'name': 'configure.name',
                                 'disabled': True})
        #namefield.onFocus="this.readOnly=true;this.style.color='grey'"
        namefield = self.update_control(namefield,'name')       

        namerow.append(HTMLgen.TD(namefield))
        configrows.append(namerow)

#        acquiresrow = HTMLgen.TR(**attrs('class', rowclasses[len(configrows) % 2]))
#        acquiresrow.append(HTMLgen.TH('Acquires Existing Assertions'))
#        acquires = config.pop('acquires')
#        yesoption = StandardizedOption('Yes', None, 'True')
#        nooption = StandardizedOption('No', None, 'False')
#        if as_boolean(acquires):
#            yesoption.select()
#        else:
#            nooption.select()
#        options = [yesoption, nooption]
#        acquiresfield = StandardizedSelect(options, name='configure.acquires')
#        acquiresrow.append(HTMLgen.TD(acquiresfield, **attrs('class', 'control')))
#        configrows.append(acquiresrow)

        contextrow = HTMLgen.TR()
        contextrow.append(HTMLgen.TH('Policy Context'))
        contextcell = HTMLgen.TD()
        contextfield = DojoInput(**{'value': config.pop('context', ''), 
                                    'name': 'configure.context', 
                                    'id': 'context'})
        contextcell.append(contextfield)
        browsebutton = HTMLgen.Input(type='button', value='Select', name = 'context')
        browsebutton.onClick = "utils.select.nodes.open('%s');" % contextfield.id
        contextcell.append(browsebutton)
        contextrow.append(contextcell)
        configrows.append(contextrow)
        config_table.append(*configrows)
        config_form.append(config_table)
        config_section.append(adorn(config_form, id="main"))
        document.append(config_section)

        ###
        # Permissions part of page.
        section = HTMLgen.Div(id='permissions', **attrs('class','section'))
        # Names of available permissions.
        fields = []
        permissions = self.policy.parent.get_permissions()
        for permission in permissions:
            field = HTMLgen.Input(type='checkbox', checked=False, 
                                  name='params', value=permission)
            fields.append(field)
        forms = []
        roles = self.policy.parent.parent.role_manager.get_role_names()
        roles.sort()
        rolemap = config.pop('rolemap')
        action = HTMLgen.Input(name="actionName",type='hidden',value='invoke')
        method = HTMLgen.Input(
            name="methodName", type='hidden',value='set_permissions')
        classes = itertools.cycle(['light', 'dark'])
        for role in roles:
            encoded = cgi.escape(role)
            form = HTMLgen.Form(request_path)
            ptable = HTMLgen.TableLite(**{'class':'configuration-table', 'style': 'margin:10px;'})
            title = HTMLgen.Input(type="hidden", name="title", value=encoded)
            form.append(title)
            form.append(manager)
            form.append(node)
            form.append(action)
            form.append(method)
            # Make first parameter passed to set_permissions the current role.
            #   Being the first input with name 'params', this will always be first value.
            rolefield = HTMLgen.Input(
                name="params", type='hidden', value=encoded)
            form.append(rolefield)
            # Copy list of all available permissions 
            # fields so original not modified.
            pfields = copy.deepcopy(fields)
            # If any permissions are granted, 
            # pre-select them in permissions inputs.
            pgranted = rolemap.get(role, [])
            for permission in pgranted:
                pfields[permissions.index(permission)].checked = 1
            # Add all availble permission fields.
            for permission,field in zip(permissions, pfields):
                prow = HTMLgen.TR(**attrs('class', classes.next()))
                prow.append(HTMLgen.TH(permission))
                prow.append(HTMLgen.TD(field, **attrs('class', 'control')))
                ptable.append(prow)
            form.append(ptable)
            form.submit.value = 'commit'
            section.append(form)
        document.append(section)
        return str(document)

register_adapter(HTMLPolicyForm)


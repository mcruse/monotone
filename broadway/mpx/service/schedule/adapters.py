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
import itertools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.backports import Dictionary
from mpx.www.w3c.xhtml.interfaces import IWebContent
from interfaces import ISchedule
from interfaces import IScheduleHolder
from interfaces import IScheduleHolderParent
from mpx.service.trendmanager import trendutil
from mpx.lib.htmlgen import *

class Action(object):
    def __init__(self, label, value = None, behaviour = None, enabled = True):
        self.label = label
        if value is None:
            value = self.label
        self.value = value
        if behaviour is None:
            behaviour = ''
        self.behaviour = behaviour
        self.enabled = enabled

class KeyWordAssist(dict):
    def __call__(self, *args):
        pairs = []
        for i in range(0, len(args), 2):
            pairs.append((args[i],args[i+1]))
        # Modification to enable in python 2.2
        pairs = dict(pairs)
        self.update(pairs)
        return self.copy()

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

def navigation(url, action, context="", **kw):
    form = HTMLgen.Form(url, name=action)
    if context:
        context = cgi.escape(context)
        input = HTMLgen.Input(name="node", value=context, type='hidden')
        form.append(input)
    form.submit.value = action
    keywords = dict(kw)
    keywords.setdefault("class", "navigation " + action)
    return adorn(form, **keywords)

class HTMLScheduleHolderParentForm(object):
    implements(IWebContent)
    adapts(IScheduleHolderParent)
    
    def __init__(self, parent):
        self.parent = parent
        self.path = None
    def get_request_path(self):
        return self.path
    def get_page_heading(self):
        return self.parent.name
    def get_page_title(self):
        return self.parent.name
    def get_column_names(self):
        return ['Name']
    def get_row_values(self, child):
        values = []
        for header in self.get_column_names():
            values.append(getattr(child, header.lower()))
        return values
    def get_row_actions(self, child = None):
        source = getattr(child, 'source', None)
        dynamic = not not (source == 'ScheduleConfigurator')
        removemessage = 'Delete Holder and its schedules?'
        removemessage += '  Note that, if there are widgets or services referring to this Holder or any schedule within it, deleting it may effect their operation.'
        onremove = "return confirm('%s');" % removemessage
        remove = Action('-', 'remove', onremove, dynamic)
        schedules = Action('schedules', 'schedules')
        return [remove, schedules]
    def get_allowed_additions(self):
        return ['Schedule Holder']
    def render(self, path = None):
        attrs = KeyWordAssist()
        if path is not None:
            self.path = path
        request_path = self.get_request_path()
        if request_path is None:
            raise Exception('Adapter does not know request path.')
        document = HTMLgen.Div(**attrs("class", "content"))
        encoded_parent = cgi.escape(self.parent.url)
        context = HTMLgen.Input(
            name='node', value=encoded_parent, type='hidden')
        children_section = HTMLgen.Div(**attrs('class', 'section'))
        children_table = HTMLgen.TableLite(
            id="holder-parent", **attrs('class', 'configuration-table'))
        children_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in self.get_column_names() + ['Action']:
            headcell = HTMLgen.TH(
                header, scope="col", abbr=header, id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")            
            children_header.append(headcell)
        children_table.append(children_header)
        classes = itertools.cycle(['light', 'dark'])
        children = self.parent.children_nodes()
        children = filter(IScheduleHolder.providedBy, children)
        for child in children:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            cells = self.get_row_values(child)
            # First value is assumed to be row header.
            row.append(HTMLgen.TH(cells[0]))
            # Any other values are added as regular cells.
            for value in cells[1:]:
                row.append(HTMLgen.TD(value))
            actioncell = HTMLgen.TD(**attrs('class', "control"))
            encodednode = cgi.escape(child.url)
            nodeinput = HTMLgen.Input(
                name="node", value=encodednode, type="hidden")
            actions = self.get_row_actions(child)
            for action in actions:
                actionname = cgi.escape(action.value)
                actionform = trendutil.CustomForm(request_path)
                actionform.append(nodeinput)
                actioninput = HTMLgen.Input(
                    name="actionName", value=actionname, type='hidden')
                actionform.append(actioninput)
                actionform.submit.value = action.label
                if action.behaviour:
                    actionform.submit.onClick = action.behaviour
                if not action.enabled:
                    actionform.submit.disabled = True
                if action.value == "remove":
                    actionform = adorn(actionform, 
                                       targetID="mainContent", 
                                       targetType="refresh")
                else:
                    actionform = adorn(actionform, 
                                       targetHandling="content",  
                                       targetID="schedule-configuration")
                actioncell.append(actionform)
                if action != actions[-1]:
                    actioncell.append(' ')
            row.append(actioncell)
            children_table.append(row)
        children_section.append(children_table)
        table = HTMLgen.TableLite(**attrs('class', 'configuration-table'))
        headrow = HTMLgen.TR(**attrs('class','table-header'))
        for header in ['Property', 'Value']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Value":
                setattr(headcell, "class", "control")            
            headrow.append(headcell)
        table.append(headrow)
        actioninput = HTMLgen.Input(
            name="actionName", value="add", type="hidden")
        for childtype in self.get_allowed_additions():
            add_form = HTMLgen.Form(request_path)
            add_form.append(context)
            add_form.append(actioninput)
            addtable = copy.deepcopy(table)
            addrow = HTMLgen.TR(**attrs("class", "light"))
            addrow.append(HTMLgen.TH("Name"))
            addname = IdentifiedInput(id='childname', name='configure.name')
            addcell = HTMLgen.TD(**attrs("class", "control"))
            addcell.append(addname)
            addrow.append(addcell)
            addtable.append(addrow)
            add_form.append(addtable)
            add_form.submit.value = "continue"      
            add_form = adorn(add_form, 
                             targetHandling="content",  
                             targetID="schedule-configuration")      
            addform = urllib.quote(str(add_form))
            popup = HTMLgen.Form(request_path)
            popup.submit.value = "+"
            onclick = "return popup_form(this, '%s', true)"
            popup.submit.onClick = onclick % addform
            children_section.append(adorn(popup, ("class", "add")))
        children_section.append(
            navigation(request_path, "reload", self.parent.url))
        document.append(children_section)
        return str(document)

register_adapter(HTMLScheduleHolderParentForm)

class HTMLScheduleHolderForm(object):
    implements(IWebContent)
    adapts(IScheduleHolder)

    def __init__(self, holder):
        self.path = None
        self.holder = holder
    def get_request_path(self):
        return self.path
    def get_page_heading(self):
        return self.holder.name
    def get_page_title(self):
        return self.holder.name
    def get_column_names(self):
        return ['Name']    
    def _generate_edit_link(self, child):
        baselink = '/omega/webscheduler/webscheduler.psp?'
        query = {'editmode': 'FULL'}
        query['scheduleholder'] = urllib.quote_plus(self.holder.url)
        query['scheduleprefix'] = 'RZSched_'
        name = child.name[len(query['scheduleprefix']):]
        query['schedulename'] = urllib.quote_plus(name)
        params = []
        for key, value in query.items():
            params.append('%s=%s' % (key, value))
        return baselink + string.join(params, '&')
    def _generate_targets_editor(self, child):
        form = HTMLgen.Form("/driverconfig")
        form.name = ("%s Outputs" % child.name)
        query = {'add': 'ValueDriver', 
                 'edit': urllib.quote_plus(child.name),
                 'configure.input': urllib.quote_plus(child.url)}
        for key, value in query.items():
            form.append(HTMLgen.Input(name=key, value=value, type="hidden"))
        form.submit.value = "outputs"
        return adorn(form, ("class", "dialog extract"))
    def _generate_targets_script(self, child):
        href = self._generate_targets_link(child)
        return "window.open('%s', 'ValueDriver'); return false;" % href
    
    def _generate_edit_script(self, child):
        href = self._generate_edit_link(child)
        return "window.open('%s', 'ScheduleEditor'); return false;" % href

    def get_row_values(self, child):
        values = []
        for header in self.get_column_names():
            values.append(getattr(child, header.lower()))
        return values
    def get_row_actions(self, child = None):
        source = getattr(child, 'source', None)
        dynamic = not not (source == 'ScheduleConfigurator')
        removemessage = 'Delete Schedule and its configuration?'
        removemessage += '  Note that, if there are widgets or services referring to this schedule, deleting it may effect their operation.'
        onremove = "return confirm('%s');" % removemessage
        remove = Action('-', 'remove', onremove, dynamic)
        rename = Action('rename', 'rename', None, dynamic)
        targets = self._generate_targets_editor(child)
        onedit = self._generate_edit_script(child)
        edit = Action('edit', '', onedit, child.name.startswith('RZSched_'))
        return [remove, rename, targets, edit]
    def get_allowed_additions(self):
        return ['Schedule']
    def render(self, path = None):
        attrs = KeyWordAssist()
        if path is not None:
            self.path = path
        request_path = self.get_request_path()
        if request_path is None:
            raise Exception('Adapter does not know request path.')
        document = HTMLgen.Div(**attrs("class", "content"))
        encoded_holder = cgi.escape(self.holder.url)
        context = HTMLgen.Input(
            name='node', value=encoded_holder, type='hidden')
        children_section = HTMLgen.Div(**attrs('class','section'))
        children_table = HTMLgen.TableLite(
            id="schedule-holder", **attrs('class', 'configuration-table'))
        children_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in self.get_column_names() + ['Action']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")
            children_header.append(headcell)
        children_table.append(children_header)

        classes = itertools.cycle(['light', 'dark'])
        children = self.holder.children_nodes()
        children = filter(ISchedule.providedBy, children)
        for child in children:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            cells = self.get_row_values(child)
            # First value is assumed to be row header.
            # remove the 'RZSched_' prefix when displaying
            cellname = cells[0].split("RZSched_")            
            if(cells[0] != "RZSched"):
                row.append(HTMLgen.TH(cellname[1]))
            else:
                row.append(HTMLgen.TH(cells[0]))
            # Any other values are added as regular cells.
            for value in cells[1:]:
                row.append(HTMLgen.TD(value))

            actioncell = HTMLgen.TD(**attrs("class", "control"))
            encodednode = cgi.escape(child.url)
            nodeinput = HTMLgen.Input(
                name="node", value=encodednode, type="hidden")
            actions = self.get_row_actions(child)
            for action in actions:
                if isinstance(action, Action):
                    actionform = trendutil.CustomForm(request_path)
                    actionform.append(nodeinput)
                    actioninput = HTMLgen.Input(
                        name="actionName", value=action.value, type='hidden')
                    actionform.append(actioninput)
                    actionform.submit.value = action.label
                    if action.behaviour:
                        actionform.submit.onClick = action.behaviour
                    if not action.enabled:
                        actionform.submit.disabled = True
                else:
                    actionform = action
                actioncell.append(actionform)
                if action != actions[-1]:
                    actioncell.append(' ')
            row.append(actioncell)
            children_table.append(row)
        children_section.append(children_table)
        table = HTMLgen.TableLite(**attrs('class', 'configuration-table'))
        headrow = HTMLgen.TR(**attrs('class','table-header'))
        for header in ['Property', 'Value']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Value":
                setattr(headcell, "class", "control")            
            headrow.append(headcell)
        table.append(headrow)
        for childtype in self.get_allowed_additions():            
            add_form = HTMLgen.Form(request_path)
            add_form.append(context)
            addinput = HTMLgen.Input(
                name='actionName', value="add", type='hidden')
            add_form.append(addinput)
            addtable = copy.deepcopy(table)
            addrow = HTMLgen.TR(**attrs("class", "light"))
            addrow.append(HTMLgen.TH("Name"))
            addname = IdentifiedInput(id='childname', name='configure.name')
            addcell = HTMLgen.TD(**attrs("class", "control"))
            addcell.append(addname)
            addrow.append(addcell)
            addtable.append(addrow)
            add_form.append(addtable)
            add_form.submit.value = "continue"            
            addform = urllib.quote(str(add_form))
            popup = HTMLgen.Form(request_path)
            popup.submit.value = "+"
            popup.submit.onClick = "return popup_form(this, '%s')" % addform
            children_section.append(adorn(popup, ("class", "add")))
        children_section.append(
            navigation(request_path, "reload", self.holder.url))
        children_section.append(
            navigation(request_path, "back", self.holder.parent.url))
        document.append(children_section)
        return str(document)

register_adapter(HTMLScheduleHolderForm)

class HTMLScheduleForm(object):
    implements(IWebContent)
    adapts(ISchedule)

    def __init__(self, schedule):
        self.schedule = schedule

    def render(self, request_path):
        attrs = KeyWordAssist()
        document = HTMLgen.Div(**attrs("class", "content"))
        encoded_schedule = urllib.quote_plus(self.schedule.url)        
        config_form = HTMLgen.Form(request_path)
        nodeinput = HTMLgen.Input(
            name='node', value=encoded_schedule, type='hidden')
        actioninput = HTMLgen.Input(
            name="actionName", value="configure", type="hidden")
        config_form.append(nodeinput)
        config_form.append(actioninput)
        config_form.submit.value = 'save'
        config_form.submit.onClick = ('return utils.schedule.'
                                      'validate_configuration(this.form);')
        config_section = HTMLgen.Div(**attrs('class','section'))
        config_table = HTMLgen.TableLite(**attrs('class', 'configuration-table'))
        config_header = HTMLgen.TR(**attrs('class', 'table-header'))
        for header in ['Attribute', 'Value']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")
            
            config_header.append(headcell)
        config_table.append(config_header)
        configrows = []
        classes = itertools.cycle(['light', 'dark'])
        config = Dictionary(self.schedule.configuration())
        namerow = HTMLgen.TR(**attrs('class', classes.next()))
        namerow.append(HTMLgen.TH('Schedule Name'))
        sched_name = config.pop('name').split("RZSched_")
        namefield = HTMLgen.Input(value=sched_name[1],
                                  name='configure.name')
        namerow.append(HTMLgen.TD(namefield, 
                                  **attrs('class', 'configuration')))
        configrows.append(namerow)
        config_table.append(*configrows)
        config_form.append(config_table)
        config_section.append(config_form)
        config_section.append(
            navigation(request_path, "reload", self.schedule.url))        
        config_section.append(
            navigation(request_path, "back", self.schedule.parent.url))        
        document.append(config_section)
        return str(document)

register_adapter(HTMLScheduleForm)



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
import string
import itertools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.service.alarms2.trigger.interfaces import ITriggerManager
from mpx.service.alarms2.trigger.interfaces import ITrigger
from mpx.service.alarms2.trigger.triggers import ComparisonTrigger
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.htmlgen import *

class IdInput(HTMLgen.Input):
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

nodeselectscript = """
var objWin = null;
function open_node_selector(id){
    if (arguments.length == 0) {
        var id = this.getAttribute('name');
    }
    var w = '600';
    var h = '600';
    var features = "height=1,width=1,resizeable,scrollbars";
    var url = '';
    if (!objWin || objWin.closed) {
        url = "/webapi/nodeSelector.html?textid=" + id;
    }
    objWin = window.open(url,"nodeSelector",features);
    if (url.length == 0) {
        objWin.set_target(window, id);
    }
        
    var height = window.screen.availHeight;
    var width = window.screen.availWidth;
    var left_point = parseInt(width/2) - parseInt(w/2);
    var top_point =  parseInt(height/2) - parseInt(h/2);
    objWin.moveTo(left_point,top_point);
    objWin.resizeTo(w,h);
    objWin.focus();
}
"""

class HTMLTriggerManager(object):
    implements(IWebContent)
    adapts(ITriggerManager)

    def __init__(self, manager):
        self.manager = manager
        self.base_doc = HTMLgen.SimpleDocument(title='Trigger Manager')

    def render(self):
        attrs = KeyWordAssist()
        request_path = '/triggerconfig'
        document = self.base_doc.copy()
        trigger_section = HTMLgen.Div(**attrs('class','section'))
        trigger_table = HTMLgen.TableLite(
            id="trigger-config", **attrs('class', 'configuration-table'))
        trigger_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in ['Name', 'Description', 'Action']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            trigger_header.append(headcell)
            if header == "Action":
                setattr(headcell, "class", "control")
        trigger_table.append(trigger_header)

        triggers = self.manager.get_triggers()
        classes = itertools.cycle(["light", "dark"])
        for trigger in triggers:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            row.append(HTMLgen.TH(trigger.name))
            row.append(HTMLgen.TD(trigger.description))
            actioncell = HTMLgen.TD(**attrs('class', 'control'))
            encoded = cgi.escape(trigger.name)
            actions = ['edit', 'remove']
            for action in actions:
                actionform = HTMLgen.Form(request_path)
                actioninput = HTMLgen.Input(name=action, 
                                            value=encoded, type='hidden')
                actionform.append(actioninput)
                if action == "remove":
                    actionform = adorn(actionform, targetID="trigger-config")
                else:
                    section = HTMLgen.Input(
                        name='section', type='hidden', value="main")
                    actionform.append(section)
                    actionform = adorn(actionform, targetType="dialog")
                actionform.submit.value = action
                if action == 'remove':
                    actionform.submit.onClick = ("return confirm('Delete "
                                                 "trigger and its "
                                                 "configuration?');")
                actioncell.append(actionform)
                if action != actions[-1]: 
                    actioncell.append(' ')
            row.append(actioncell)
            trigger_table.append(row)
        trigger_section.append(trigger_table)
        add_form = HTMLgen.Form(request_path)
        addinput = HTMLgen.Input(name='add', value='true', type='hidden')
        add_form.append(addinput)
        section = HTMLgen.Input(
            name='section', type='hidden', value="main")
        add_form.append(section)
        add_form = adorn(add_form, targetType="dialog")
        add_form.submit.value = 'add'
        trigger_section.append(add_form)
        document.append(trigger_section)
        return str(document)

register_adapter(HTMLTriggerManager)


class HTMLTrigger(object):
    implements(IWebContent)
    adapts(ITrigger)

    def __init__(self, trigger):
        self.trigger = trigger
        self.base_doc = HTMLgen.SimpleDocument(
            title='Trigger', stylesheet='/omega/eventmanager/styles.css')

    def render(self):
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        page_heading = HTMLgen.Heading(
            2, 'Editing "%s"' % self.trigger.name, id="editorlabel")
        browsescript = HTMLgen.Script(code = nodeselectscript)
        page_heading.append(browsescript)
        document.append(page_heading)
        encoded_name = cgi.escape(self.trigger.name)
        encoded_url = cgi.escape(self.trigger.url)

        editorinput = HTMLgen.Input(name="edit", type='hidden', value=encoded_name)
        request_path = '/triggerconfig'

        ###
        # Form Navigation
        navigation = HTMLgen.Div(**attrs('class', 'confignavigation'))
        reloadform = HTMLgen.Form(request_path)
        reloadform.append(editorinput)
        reloadform.submit.value = 'reload editor'
        backform = HTMLgen.Form(request_path)
        backform.submit.value = 'back to main'
        navigation.append(reloadform)
        navigation.append(backform)
        document.append(navigation)

        ###
        # Targets part of page.
        targets_section = HTMLgen.Div(id = 'TargetsSection',
                                      **attrs('class','section'))
        targets_table = HTMLgen.TableLite(**attrs('class', 'defaultstyle'))
        targets_caption = HTMLgen.Caption('Add / Remove Trigger Targets')
        targets_table.append(targets_caption)
        targets_header = HTMLgen.TR(**attrs('class','table1_headers'))
        for header in ['Name', '']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header)
            targets_header.append(headcell)
        targets_table.append(targets_header)

        targets = self.trigger.get_targets()
        count = 0
        rowclasses = ['light', 'dark']
        for target in targets:
            count += 1
            row = HTMLgen.TR(**attrs('class', rowclasses[count % 2]))
            row.append(HTMLgen.TH(target.name))
            encoded_target = cgi.escape(target.url)

            remove_target_form = HTMLgen.Form(request_path)
            action = HTMLgen.Input(
                name="actionName", type='hidden', value='remove_target')
            action_target = HTMLgen.Input(name="target", type='hidden', value=encoded_name)
            targeturl = HTMLgen.Input(name="params", type='hidden', value=encoded_target)
            remove_target_form.append(editorinput)
            remove_target_form.append(action)
            remove_target_form.append(action_target)
            remove_target_form.append(targeturl)
            remove_target_form.submit.value = 'remove'
            row.append(HTMLgen.TD(remove_target_form))

            targets_table.append(row)
        targets_section.append(targets_table)

        manager = self.trigger.nodespace.as_node('/services/Alarm Manager')
        nodes = manager.get_alarms()
        alarms = []
        for node in nodes:
            if node in targets: continue
            alarms.append((node.name, cgi.escape(node.url)))
        if alarms:
            alarms.sort()
            select = HTMLgen.Select(alarms, name='params')
            action = HTMLgen.Input(
                name="actionName", type='hidden', value='add_target')
            action_target = HTMLgen.Input(name="target", type='hidden', value=encoded_name)
            add_form = HTMLgen.Form(request_path)
            add_form.append(editorinput)
            add_form.append(action)
            add_form.append(action_target)
            add_form.append(select)
            add_form.submit.value = 'Add Target'
            targets_section.append(add_form)
        document.append(targets_section)
        ### End Sources ###

        ##
        # Configuration part of page.
        config_section = HTMLgen.Div(id = 'ConfigurationSection',
                                     **attrs('class','section'))
        config_form = HTMLgen.Form(request_path)
        config_form.submit.value = 'Commit'
        config_form.reset = HTMLgen.Input(type='reset', name='resetButton', value='Clear changes')
        config_form.reset.onClick = "return confirm('Clear all form modifications without reconfiguring device?');"
        hidden = HTMLgen.Input(name="configure", type='hidden', value=encoded_name)
        config_form.append(hidden)

        name = self.trigger.name
        config = self.trigger.configuration()
        config_table = HTMLgen.TableLite(**attrs('class', 'defaultstyle'))
        config_caption = HTMLgen.Caption('View / Modify "%s" configuration' % name)
        config_table.append(config_caption)
        config_header = HTMLgen.TR(**attrs('class', 'table1_headers'))
        for header in ['Attribute', 'Value']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            config_header.append(headcell)
        config_table.append(config_header)

        hidden = {}
        configurable = {}
        appendconfig = None
        if isinstance(self.trigger, ComparisonTrigger):
            fields = ['name', 'message', 'hysteresis', 'poll_period', 'alarm_delay']
            for aname, avalue in config.items():
                if aname in fields:
                    configurable[aname] = avalue
                else:
                    hidden[aname] = avalue
            appendconfig = HTMLgen.TH(colspan = 2)
            appendconfig.append(HTMLgen.Text('Alarm when node '))
            input = IdInput(value=config.get('input',''), name='configure.input', id = 'input_node')
            appendconfig.append(input)
            browsebutton = HTMLgen.Input(type='button', value='Select Node', name = 'input_node')
            browsebutton.onClick = "open_node_selector('%s');" % input.id
            appendconfig.append(browsebutton)

            if hidden.has_key('input'): del(hidden['input'])
            appendconfig.append(HTMLgen.Text(' is '))
            comparison = config.get('comparison', '')
            select = ['', '>', '<']
            if comparison in ('greater_than','>', 'input > constant'):
                select = ['>', '<', '']
            elif comparison in ('less_than', '<', 'input < constant'):
                select = ['<', '>', '']
            appendconfig.append(HTMLgen.Select(select, name='configure.comparison'))
            if hidden.has_key('comparison'): del(hidden['comparison'])
            appendconfig.append(HTMLgen.Text(' than constant '))
            appendconfig.append(HTMLgen.Input(value=config.get('constant', ''), name='configure.constant'))
            if hidden.has_key('constant'): del(hidden['constant'])
            # Below are removed because trigger builds from other information.
            if hidden.has_key('statement'): del(hidden['statement'])
            if hidden.has_key('critical_input'): del(hidden['critical_input'])
            if hidden.has_key('variables'): del(hidden['variables'])
        else: configurable.update(config)

        for aname,avalue in hidden.items():
            field = HTMLgen.Input(value=avalue, type='hidden', name='configure.%s' % aname)
            config_form.append(field)

        count = 0
        rowclasses = ['light', 'dark']
        for aname,avalue in configurable.items():
            count += 1
            row = HTMLgen.TR(**attrs('class', rowclasses[count % 2]))
            headercell = HTMLgen.TH(aname)
            configfield = HTMLgen.Input(value=avalue, name='configure.%s' % aname)
            datacell = HTMLgen.TD(configfield, **attrs('class', 'configuration'))
            row.append(headercell)
            row.append(datacell)
            config_table.append(row)
        if appendconfig is not None:
            count += 1
            row = HTMLgen.TR(**attrs('class', rowclasses[count % 2]))
            row.append(appendconfig)
            config_table.append(row)
        config_form.append(config_table)
        config_section.append(config_form)
        document.append(config_section)
        ### End Configuration ###
        return str(document)

register_adapter(HTMLTrigger)

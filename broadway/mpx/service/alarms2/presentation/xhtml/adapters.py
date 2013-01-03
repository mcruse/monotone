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
# Refactor 2/11/2007
import urllib
import itertools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.service.alarms2.interfaces import IAlarmManager
from mpx.service.alarms2.interfaces import IAlarm
from mpx.service.alarms2.interfaces import IAlarmEvent
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.htmlgen import *
import cgi

class HTMLAlarmManager(object):
    implements(IWebContent)
    adapts(IAlarmManager)
    def __init__(self, manager):
        self.manager = manager
        self.base_doc = HTMLgen.SimpleDocument(title='Alarm Editor')
    def render(self):
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        request_path = '/alarmconfig'
        alarm_section = HTMLgen.Div(**attrs('class','section'))
        alarm_table = HTMLgen.TableLite(id="alarm-config-table")
        setattr(alarm_table, "class", "configuration-table")
        alarm_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in ['Name','Overview','Priority','Description','Action']:
            headcell = HTMLgen.TH(
                header, scope="col", abbr=header, id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")
            alarm_header.append(headcell)
        alarm_table.append(alarm_header)
        alarms = self.manager.children_nodes()
        count = 0
        rowclasses = ['light', 'dark']
        statenames = ['raised', 'cleared', 'accepted', 'closed', 'total']
        for alarm in alarms:
            count += 1
            encoded_name = urllib.quote_plus(alarm.name)
            row = HTMLgen.TR(id=encoded_name,
                             **attrs('class', rowclasses[count % 2]))
            row.append(HTMLgen.TH(alarm.name))
            overviewcell = HTMLgen.TD()
            events = alarm.get_events()
            states = {'total': len(events), 'raised': 0,
                      'cleared': 0, 'accepted': 0, 'closed': 0}
            for event in events:
                states[event.state.lower()] += 1
            for state in statenames:
                overviewcell.append('%s: %s' % (state, states[state]))
                if state != statenames[-1]: overviewcell.append(' ')
            row.append(overviewcell)
            row.append(HTMLgen.TD(alarm.priority))
            row.append(HTMLgen.TD(alarm.description))
            actioncell = HTMLgen.TD(**attrs('class', "control"))
            actions = ['edit', 'remove', 'trigger', 'clear']
            for action in actions:
                actionform = HTMLgen.Form(request_path)
                formId = action + "_" + cgi.escape(alarm.name)
                actionform.name = action.title() + " Alarm"
                actioninput = HTMLgen.Input(name=action,
                                            type='hidden',
                                            value=encoded_name)
                actionform.append(actioninput)
                actionform.submit.value = action
                if action == 'remove':
                    actionform.submit.value = ' - '
                    actionform = adorn(actionform,
                                       targetID="alarm-config-table", id=formId)
                    actionform.submit.onClick = ("return(confirmDialog('"
                                                 + formId +"', "
                                                 + "'Are you sure you want to delete <b>"
                                                 + cgi.escape(alarm.name) + "</b> and "
                                                 + "its configurations?', false));")
                elif action == "edit":
                    actionform = adorn(actionform, targetType="dialog")
                else:
                    actionform = adorn(actionform, targetID=encoded_name)
                actioncell.append(actionform)
                if action != actions[-1]:
                    actioncell.append(' ')
            row.append(actioncell)
            alarm_table.append(row)
        alarm_section.append(alarm_table)
        add_form = HTMLgen.Form(request_path)
        addinput = HTMLgen.Input(name='add', type='hidden', value='true')
        #CSCte94335 - to add the title to add alarm dialog
        add_form.name = "Add Alarm"
        add_form.append(addinput)
        add_form.submit.value = ' + '
        add_form = adorn(add_form, targetType="dialog")
        alarm_section.append(add_form)
        document.append(alarm_section)
        return str(document)


class HTMLAlarm(object):
    implements(IWebContent)
    adapts(IAlarm)
    def __init__(self, alarm):
        self.alarm = alarm
        self.base_doc = HTMLgen.SimpleDocument(title='Alarm Editor')
    def render(self):
        attrs = KeyWordAssist()
        request_path = '/alarmconfig'
        encoded = urllib.quote_plus(self.alarm.name)
        form = HTMLgen.Form('/alarmconfig')
        # Hidden input telling handler to configure node on submit.
        configure = HTMLgen.Input(name="configure",
                                  type="hidden", value=encoded)
        form.append(configure)
        table = HTMLgen.TableLite(**attrs('class', 'configuration'))
        header = HTMLgen.TR(**attrs('class', 'table-header'))
        for column in ['Attribute', 'Value']:
            cell = HTMLgen.TH(column, scope="col", abbr=column)
            header.append(cell)
        table.append(header)
        abnormal = {}
        hidden = ["parent", "source", "enabled"]
        ordered = ["priority", "name",  "debug", "max_raised",
                   "max_cleared", "max_accepted", "description"]
        configuration = self.alarm.configuration()
        attributes = set(configuration)
        names = [name for name in ordered if name in attributes]
        names.extend(attributes - set(names))
        poptions = [("P%d" % i,"P%d" % i)  for i in range(1, 11)]
        pfield = HTMLgen.Select(poptions, name='priority')
        priority = configuration.get('priority', 'P1')
        if priority in poptions:
            pfield.selected.append(priority)
        abnormal['priority'] = pfield
        description = configuration.get("description", "")
        dfield = HTMLgen.Textarea(description, name="description")
        abnormal["description"] = dfield
        name = configuration.get("name", "")
        # CSCte94385 - max length of name field is set to 100
        nfield = HTMLgen.Input(name="name", value=name, maxlength=100)
        abnormal["name"] = nfield
        classes = itertools.cycle(["light", "dark"])
        for aname in names:
            avalue = configuration[aname]
            qname = cgi.escape(aname)
            qvalue = cgi.escape(avalue)
            if aname in hidden:
                field = HTMLgen.Input(value=qvalue, name=qname, type='hidden')
                form.append(field)
            else:
                if abnormal.has_key(aname):
                    field = abnormal.get(aname)
                else:
                    field = HTMLgen.Input(name=qname, value=qvalue)
                row = HTMLgen.TR(**attrs('class', classes.next()))
                row.append(
                    HTMLgen.TH(qname, **attrs("class", "attribute-name")))
                row.append(
                    HTMLgen.TD(field, **attrs("class", "attribute-value")))
                table.append(row)
        form.append(table)
        form.submit.value = form.submit.name = "save"
        cancel = HTMLgen.Input(type="reset", value="cancel", name="cancel")
        form.append(cancel)
        # CSCte94385 (fix disabled for now) - validate invalid chars
        dialogId = "edit"
        #strScript = ("function " + dialogId + "_validate() { if(document.getElementById('" + dialogId + "').name.value.match('[^a-zA-Z0-9_]')) { " +
        #                 "alert('Error: Name should have only alphanumeric and _ charaters.');" +
        #                 "return false;}" +
        #                 "return true;}")
        #script = HTMLgen.Script(language="JavaScript", code=strScript)
        #form.append(script)
        form = adorn(form, id=dialogId)
        form = adorn(form, onsubmit = "return false") #This will disable form submission when enter key is pressed (CSCtg05439)
        return str(form)


register_adapter(HTMLAlarmManager)
register_adapter(HTMLAlarm)

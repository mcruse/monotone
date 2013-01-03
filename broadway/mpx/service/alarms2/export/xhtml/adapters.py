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
import itertools
from HTMLgen import HTMLgen
from HTMLgen import Formtools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.lib.configure import as_boolean
from mpx.service.alarms2.export.interfaces import IExporterContainer
from mpx.service.alarms2.export.interfaces import IAlarmExporter
from mpx.service.alarms2.export.interfaces import IAlarmFormatter
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.htmlgen import *

class HTMLExporterContainer(object):
    implements(IWebContent)
    adapts(IExporterContainer)

    def __init__(self, container):
        self.container = container
        self.base_doc = HTMLgen.SimpleDocument(title='Alarm Exporters')

    def render(self):
        attrs = KeyWordAssist()
        request_path = '/exportconfig'
        document = self.base_doc.copy()

        exporter_section = HTMLgen.Div(**attrs('class','section'))
        exporter_table = HTMLgen.TableLite(
            id="export-config", **attrs('class', 'configuration-table'))
        exporter_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in ['Name', 'Description', 'Action']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")
            exporter_header.append(headcell)
        exporter_table.append(exporter_header)

        exporters = self.container.get_exporters()
        classes = itertools.cycle(['light', 'dark'])
        for exporter in exporters:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            row.append(HTMLgen.TH(exporter.name))
            row.append(HTMLgen.TD(exporter.description))
            actioncell = HTMLgen.TD(**attrs('class', 'control'))
            exportname = cgi.escape(exporter.name)
            actions = ['edit', 'triggers', 'events', 'remove']
            for action in actions:
                actionform = HTMLgen.Form(request_path)
                actioninput = HTMLgen.Input(
                    name=action, value=exportname, type='hidden')
                actionform.append(actioninput)
                if action == "remove":
                    actionform.submit.onClick = ("return confirm('Delete"
                                                 " exporter and its "
                                                 "configuration?');")
                    actionform = adorn(actionform, targetID="export-config")
                else:
                    if action == "edit":
                        section = "main"
                    else:
                        section = action
                    sectioninput = HTMLgen.Input(
                        name='section', type='hidden', value=section)
                    actionform.append(sectioninput)
                    actionform = adorn(actionform, targetType="dialog")
                actionform.submit.value = action
                if exporter.name != 'Alarm Logger':
                    actioncell.append(actionform)
                    if action != actions[-1]:
                        actioncell.append(' ')
            row.append(actioncell)
            exporter_table.append(row)
        exporter_section.append(exporter_table)
        add_form = HTMLgen.Form(request_path)
        addinput = HTMLgen.Input(name='add', value='true', type='hidden')
        add_form.append(addinput)
        section = HTMLgen.Input(
            name='section', type='hidden', value="main")
        add_form.append(section)
        add_form = adorn(add_form, targetType="dialog")
        add_form.submit.value = 'add'
        exporter_section.append(add_form)
        document.append(exporter_section)
        return str(document)

register_adapter(HTMLExporterContainer)


class HTMLAlarmExporter(object):
    implements(IWebContent)
    adapts(IAlarmExporter)

    def __init__(self, exporter):
        self.exporter = exporter
        self.base_doc = HTMLgen.SimpleDocument(title='Alarm Exporter')

    def render(self):
        """
            Configuration should be broken into three main topics.
            Edit, associated with an 'edit' button on the manager 
            page, exposes name and other standard node configuration 
            options.
            
            Export, associated with an 'export' button on the manager 
            page, exposes two panels.  One panel is identified with a 
            title of "transport", and configures the transporter; the 
            other is identified with a title of "format", and configures 
            the formatter.
            
            Trigger, associated with a "triggers" button on the manager 
            page, allows the user to select available event generators 
            and configure specific events for each using check boxes.
        """
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        request_path = '/exportconfig'
        exportname = cgi.escape(self.exporter.name)
        editorinput = HTMLgen.Input(
            name='edit', type='hidden', value=exportname)
        targetinput = HTMLgen.Input(
            name="target", type='hidden', value=exportname)
        classes = itertools.cycle(['light', 'dark'])

        ###
        # Sources part of page.
        section = HTMLgen.Div(id="triggers",**attrs('class','section'))
        triggernames = ['raised', 'accepted', 'cleared', 'closed']
        actioninput = HTMLgen.Input(
            name="actionName", type="hidden", value="add_source")
        sources = self.exporter.get_sources()
        for source in sources:
            form = HTMLgen.Form(request_path)
            sourcename = cgi.escape(source.name)
            sourcepath = cgi.escape(source.as_node_url())            
            table = HTMLgen.TableLite(**attrs('class','configuration-table'))
            title = HTMLgen.Input(name="title",type="hidden",value=sourcename)
            form.append(editorinput)
            form.append(actioninput)
            form.append(targetinput)
            form.append(title)
            sourceinput = HTMLgen.Input(
                name="params", type='hidden', value=sourcepath)
            form.append(sourceinput)
            selected = self.exporter.get_event_names(source)
            if 'all' in selected: 
                selected = triggernames[:]
            items = []
            for name in triggernames:
                triggername = cgi.escape(name)
                row = HTMLgen.TR(**attrs('class', classes.next()))
                row.append(HTMLgen.TH(triggername))                
                field = HTMLgen.Input(type='checkbox', 
                                      checked=(name in selected), 
                                      name='params', value=triggername)
                row.append(HTMLgen.TD(field, **attrs('class', 'control')))
                table.append(row)
            form.submit.value = 'commit'
            form.append(table)
            section.append(form)

            ## Not integrated yet.
            remove_source_form = HTMLgen.Form(request_path)
            actioninput = HTMLgen.Input(
                name="actionName", type='hidden', value='remove_source')
            remove_source_form.append(editorinput)
            remove_source_form.append(actioninput)
            remove_source_form.append(sourceinput)
            remove_source_form.append(targetinput)
            remove_source_form.submit.value = 'remove'
        document.append(section)

        manager = self.exporter.nodespace.as_node('/services/Alarm Manager')
        nodes = [manager] + manager.get_alarms()
        triggers = []
        for node in nodes:
            if node in sources: 
                continue
            triggers.append((node.name, cgi.escape(node.url)))
        if triggers:
            triggers.sort()
            select = HTMLgen.Select(triggers, name='params')
            add_form = HTMLgen.Form(request_path)
            add_form.append(editorinput)
            add_form.append(actioninput)
            add_form.append(targetinput)
            add_form.append(select)
            add_form.submit.value = 'add'
#            sources_section.append(add_form)
#        document.append(sources_section)
        ### End Sources ###

        ##
        # Configuration part of page.
        config_section = HTMLgen.Div(id="main", **attrs('class','section'))
        configure = HTMLgen.Input(
            name="configure", type='hidden', value=exportname)
        exportconfig = self.exporter.configuration()
        if exportconfig.has_key('formatter'):
            formatconfig = exportconfig['formatter']
            del(exportconfig['formatter'])
        else: 
            formatconfig = {}
        if exportconfig.has_key('transporter'):
            transportconfig = exportconfig['transporter']
            del(exportconfig['transporter'])
        else: 
            transportconfig = {}
        hidden = ['parent', 'connection', 'debug', 'enabled']
        boolean = ['gm_time', 'authenticate', 'as_attachment']
        password = ['password']
        for name,config in [('Exporter', exportconfig), 
                            ('Formatter', formatconfig), 
                            ('Transporter', transportconfig)]:
            form = HTMLgen.Form(request_path)
            title = HTMLgen.Input(type="hidden", name="title", value=name)
            form.append(title)
            form.append(editorinput)
            table = HTMLgen.TableLite(**attrs('class','configuration-table'))

            config_header = HTMLgen.TR(**attrs('class', 'table-header'))
            for header in ['Attribute', 'Value']:
                headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                      id="%sheader" % header)
                if header == "Value":
                    setattr(headcell, "class", "control")                
                config_header.append(headcell)
            table.append(config_header)

            classes = itertools.cycle(['light', 'dark'])
            for aname,avalue in config.items():
                fieldname = '%s.%s' % (name,aname)
                if aname in boolean:
                    if as_boolean(avalue):
                        options = ['true', 'false']
                    else: 
                        options = ['false', 'true']
                    field = HTMLgen.Select(options, name=fieldname)
                else: 
                    field = HTMLgen.Input(value=avalue, name=fieldname)
                if aname in hidden:
                    field.type = 'hidden'
                    form.append(field)
                    continue
                elif aname in password:
                    field.type = 'password'
                row = HTMLgen.TR(**attrs('class', classes.next()))
                headercell = HTMLgen.TH(aname)
                datacell = HTMLgen.TD(field,**attrs('class', 'control'))
                row.append(headercell)
                row.append(datacell)
                table.append(row)
            form.append(table)
            config_section.append(form)
        document.append(config_section)
        return str(document)

register_adapter(HTMLAlarmExporter)


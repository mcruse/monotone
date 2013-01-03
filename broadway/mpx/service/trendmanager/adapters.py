"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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
import htmltrend
import htmlconfirm

import urllib
import cgi
from HTMLgen import HTMLgen

from mpx.componentry import adapts
from mpx.componentry import implements
from mpx.componentry import register_adapter

from mpx.www.w3c.xhtml.interfaces import IWebContent

from mpx.lib import msglog
from mpx.lib.htmlgen import *

from interfaces import ITrendManager
from interfaces import ITrendPointConfiguration
from interfaces import ITrendPreferenceConfiguration

from trendutil import CustomButton
from trendutil import CustomForm
from trendutil import CustomInput
from trendutil import DojoInput
from trendutil import CustomLabel
from trendutil import domish
from trendutil import nodeselectscript

updatenamescript = """
function update_point_name(src_id,dst_id) {
    src = document.getElementById(src_id);
    dst = document.getElementById(dst_id);
    point_name = dst.value.replace(/^\s+/, '').replace(/\s+$/, '');
    node_url = src.value;
    if (point_name == '') {
        node_components = node_url.split('/');
        basename = '';
        for (var i=node_components.length-1; i >= 0; i++) {
            basename = node_components[i];
            if (basename != '') {
                break;
            }
        }
        dst.value = basename;
    }
    return;
}
"""

addform = """
<form action="/trendmanager" method="post">
    <input type="hidden" value="true" name="newtrend"/>
    <table class="nodeEditTable nodeEditContent" style="margin-bottom:10px;">
    <tbody>
        <tr>
            <th>Name</th>
            <td>
            <input dojoType="dijit.form.TextBox" type="text" name="trendname" maxlength="50" value="%s"/>
            </td>
        </tr>
    </tbody>
    </table>
    <input type="submit" value="commit" name="SubmitButton" 
            style="display: none;"/>
</form>
"""

class HTMLTrendManager(object):
    implements(IWebContent)
    adapts(ITrendManager)
    def __init__(self, manager):
        self.manager = manager
        return
    def __render_trend_row(self, request_path, display_name, trend_map, count):
        trend = trend_map[display_name]
        if trend is None:
            return None
        rowclasses = ['light', 'dark']
        row = HTMLgen.TR(**{'class':rowclasses[count % 2]})
        span = HTMLgen.Span(display_name, **{'style': 'white-space: pre;'})
        row.append(HTMLgen.TH(span))
        try:
            if not trend.get_points():
                domish(row).setAttribute('class', 'nopoints')
            actioncell = HTMLgen.TD(**{"nowrap":True})
            last_action = actioncell
            encoded_name = urllib.quote_plus(trend.name)
            # @note Using display text as URL is a bad idea...
            # @note More of a combo box approach would be better.
            # @note I don't think all the forms and hidden inputs are needed.
            #       either use a single form and the input name, or use
            #       multiple forms with encoded request paths...  Or?
            actions = ['view trend',
                       'configure points',
                       'trend preferences',
                       ' - ']    
            for action in actions:
                form_id = action.lstrip().rstrip() + cgi.escape(trend.name)
                if action == 'view trend':
                    actionform = CustomForm(request_path)
                    actionname = 'reload'
                elif action == 'trend preferences':
                    actionform = CustomForm(request_path, targetType='ignore')
                    if (trend.klass == 'log') and (len(trend.get_points()) > 9):
                            actionform.submit.onClick = (
                                "(alert('This trend is configured via /services/logger and has more than 9 points. Viewing/configuring points for this trend is currently not supported.'));return false;"
                                )
                    else:
                        actionform.submit.id = ("%sbutton")%encoded_name
                        actionform.submit.onClick = ("getTrendPreferences('%s', '%s');"%(encoded_name, actionform.submit.id))
                elif action == ' - ':
                    actionform = CustomForm(request_path, targetID='trend-config-table', id=form_id)
                    actionname = action.replace(' ', '').lower()
                else:
                    actionform = CustomForm(request_path, targetType='dialog')
                    actionname = action.replace(' ', '').lower()
                actionform.name = action.title()    
                actioninput = CustomInput(
                    name=actionname,
                    value=encoded_name,
                    type='hidden')
                if trend.klass == 'log':
                    if action in ['configure points', '-']:
                        actionform.submit.disabled = True
                        actioninput.disabled = True
                else:
                    if action == ' - ':
                        actionform.name = 'Remove Trend'
                        actionform.submit.onClick = (
                            "return (confirmDialog('"+ form_id +"', 'Delete trend <b>%s</b> and its"
                            " configuration?', false));" % trend.name
                            )
                        actionform.klass = 'manual'
                if action == 'view trend':
                    if (trend.klass == 'log') and (len(trend.get_points()) > 9):
                            actionform.submit.onClick = (
                                "(alert('This trend is configured via /services/logger and has more than 9 points. Viewing/configuring points for this trend is currently not supported.'));return false;"
                                )
                    else:
                        actionform.klass = 'manual'
                        preferences = trend.get_preferences()
                        window_width = preferences['width']
                        window_height = preferences['height']
                        window_title = preferences['title']
                        #actionform.cgi=None
                        actionform.submit.onClick = (
                            "openWindow('%s?viewtrend=%s','%s'); return false;"
                            % (request_path,
                               encoded_name,
                               trend.name.replace(' ', '_').replace('.', '_'))
                            )                       
                        if not trend.get_points():
                            # No point in viewing graph with no points.
                            actionform.submit.disabled = True
                        #actioninput.disabled=True
                actionform.append(actioninput)
                actionform.submit.value = action
                externally_managed = getattr(trend,'externally_managed',False)
                if externally_managed and action != 'view trend':
                        actionform.submit.disabled = True
                actioncell.append(actionform)
            # Add row
            row.append(actioncell)
        except Exception, e:
            cell = HTMLgen.TD("Invalid configuration: Please validate the configuration using ConfigTool.")
            rowid='row%s'%count
            dots="[+]"
            js = "var element = document.getElementById('%s'); if(element.innerHTML == '%s'){element.innerHTML='[-]<BR>%s'}else{element.innerHTML='%s'}" % (rowid,dots, str(e).replace('\"', '').replace("\'", ""),dots);
            invalid_label=CustomLabel(id=rowid,onclick=js,style='color:red;text-decoration:underline;cursor: pointer')
            invalid_label.append(dots)
            cell.append(invalid_label)
            row.append(cell)
            msglog.exception()
            msg = ("Failed create row for: %s" % 
                   display_name)
            msglog.log('trendmanager', msglog.types.ERR, msg)
        return row
    def render(self):
        request_path = '/trendmanager'
        trend_section = HTMLgen.Div(**{'class':'section'})
        trend_table = HTMLgen.TableLite(**{'class':'configuration-table configureNodesTable',
                                            'id':'trend-config-table'})
        trend_section.append(trend_table)
        trend_table_tr_th = HTMLgen.TR(**{'class':'table-header'})
        trend_table.append(trend_table_tr_th)
        th_name = HTMLgen.TH('Trend', id='Nameheader')
        trend_table_tr_th.append(th_name)
        th_action = HTMLgen.TH('Action', id='Actionheader')
        trend_table_tr_th.append(th_action)
        trends = self.manager.get_trends()
        trend_map = {}
        for trend in trends:
            trend_name = None
            try:
                trend_name = trend.name
                display_name = trend.get_preferences()['title']
                if not display_name:
                    display_name = trend.name
                if display_name != trend.name:
                    display_name = "%s (%s)" % (display_name, trend.name)
                trend_map[display_name] = trend
            except:
                msg = ("Failed to get preferences for: %s, can't list." %
                       trend_name)
                msglog.log('trendmanager', msglog.types.ERR, msg)
                msglog.exception(prefix='Handled')
        display_names = trend_map.keys()
        display_names.sort(lambda a,b: cmp(a.lower(),b.lower()))
        count = 0
        for display_name in display_names:
            try:
                count += 1
                row = self.__render_trend_row(request_path,
                                              display_name, trend_map, count)
                trend_table.append(row)
            except:
                msglog.exception()
                msg = ("Failed create row for: %s" %
                       display_name)
                msglog.log('trendmanager', msglog.types.ERR, msg)    
        # Add + to the last actioncell (maybe the actionheader if no trends)
        actionform = CustomForm(request_path)        
        actionform.submit.value = ' + '
        actionform.submit.name = 'Add Trend'
        trend_name = self.manager.generate_trend_name()        
        add_form = (addform) % (trend_name)
        add_form = urllib.quote(add_form)
        actionform.submit.onClick = "return popup_form(this, '%s', true); return false;" % add_form
        trend_section.append(actionform)
        return str(trend_section)
register_adapter(HTMLTrendManager)

class HTMLTrendPointConfiguration(object):
    implements(IWebContent)
    adapts(ITrendPointConfiguration)
    def __init__(self, tpf):
        self.tpf = tpf
        self.trend = tpf.trend
        self.encoded_name = urllib.quote_plus(self.trend.name)
        self.globalsettingscontainer = None
        self.trend_configuration = None
        return
    def add_global_settings(self):
        if 'period' not in self.trend_configuration.keys():
            # This is coming from /services/logger node - no point
            # configuration from UI
            return
        container = self.globalsettingscontainer
        table = HTMLgen.TableLite(**{"class":"nodeEditTable nodeEditContent", "style": "width:100%;border-spacing:5px;"})
        table.append(HTMLgen.TR(HTMLgen.TH("Global Settings", **{"style": "font-weight:800;"}), **{"style": "background:#D9E3E9;height:20px;text-indent:5px;"}))
        period_value = self.trend_configuration['period']
        frameset = HTMLgen.Frameset(
            HTMLgen.Span(CustomLabel("Period:", **{"for":"period"}),
                         DojoInput(**{"id":"period",
                                        "name":"period",
                                        "value":period_value,
                                        "dojoType":"dijit.form.NumberTextBox",
                                        "invalidMessage":"Invalid duration, period value should be a positive integer...",
                                        "constraints":"{min:1,places:0}"}),
                         CustomLabel("seconds", **{"for":"period"}),
                         **{"style":"white-space: nowrap"}),
            )
        table.append(HTMLgen.TR(HTMLgen.TD(frameset)))
        container.append(table)
        return
    def render(self):
        # @todo Restructure like preferences, point_form -> form...
        self.trend_configuration = self.trend.configuration()
        document = HTMLgen.SimpleDocument(
            title='trendMANAGER',
            stylesheet='/omega/trendmanager/styles.css',
            script=[HTMLgen.Script(code=nodeselectscript),
                    HTMLgen.Script(code=updatenamescript),]
            )
        # Hack-around to set the class on the BODY for HTMLGen
        document.append(
            HTMLgen.Script(code="""
              document.body.className = 'manager';
              """)
            )
        page_heading = HTMLgen.Heading(2, "Trend Point Configuration",
                                       id="editorlabel")
        document.append(page_heading)
        section = HTMLgen.Div(**{'class':'section'})
        point_form = CustomForm('/trendmanager')

        self.globalsettingscontainer = HTMLgen.Div(
            **{'id':'globalsettingscontainer'}
            )
        point_form.append(self.globalsettingscontainer)
        self.add_global_settings()
        point_section = HTMLgen.Div(**{'class':'section'})
        point_table = HTMLgen.TableLite(**{'class':'nodeEditTable'})
        point_header = HTMLgen.TR(**{'class':'trend_table_headers'})
        for header in ['Point Name', 'Node Path']:
            header_id = "%sheader" % header.replace(' ','').lower()
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id=header_id)
            point_header.append(headcell)
        point_table.append(point_header)
        rowclasses = ['light', 'dark']
        cd_points = self.trend_configuration['points']
        for point_position in xrange(1,10):
            point_row = HTMLgen.TR(**{'class':rowclasses[point_position % 2]})
            point_name_value = ""
            point_node_value = ""
            if len(cd_points) >= point_position:
                point_cfg = cd_points[point_position-1]
                point_name_value = point_cfg['name']
                point_node_value = point_cfg['node']
            point_name_id = "point%d" % point_position
            name_input = DojoInput(**{
                'value':point_name_value,
                'name':point_name_id,
                'id':point_name_id,
                })
            name_column = HTMLgen.TD(**{"nowrap":True})
            name_column.append(name_input)
            point_row.append(name_column)
            point_node_id = "node%d" % point_position
            node_input = DojoInput(**{
                'value':point_node_value,
                'name':point_node_id,
                'id':point_node_id,
                })
            # @fixme Cool idea, need to swap order of node and name and
            #        adding +/- capability would be extremely helpful in
            #        user experience.
            #node_input.onChange = "update_point_name('%s','%s');" % (
            #    point_node_id,
            #    point_name_id
            #    )
            node_column = HTMLgen.TD(**{"class":"configuration",
                                        "nowrap":True})
            node_column.append(node_input)
            browse_node_id = "browse%d" % point_position
            node_browse = CustomInput(**{
                'type':'button',
                'name':browse_node_id,
                'value':'...',
                })
            node_browse.onClick = "open_node_selector('%s');" % point_node_id
            button_column = HTMLgen.TD(**{"nowrap":True})
            button_column.append(node_browse)
            point_row.append(node_column)
            point_row.append(button_column)
            point_table.append(point_row)
        point_table.append(
            CustomInput(type='hidden', name='commitpoints', value='Commit')
            )
        point_form.append(point_table)
        point_form.submit = HTMLgen.Span(**{"class":"savespan"})
        point_form.submit.append(
            CustomInput(type='hidden', name='trend', value=self.encoded_name)
            )
        point_form.submit.append(
            CustomInput(type='submit', name='commitpoints', value='Commit')
            )
        point_form.submit.append(
            CustomInput(type='submit', name='cancelpoints', value='Cancel')
            )
        point_form.submit.append(
            CustomInput(type='submit', name='reloadpoints', value='Reload')
            )        
        section.append(point_form)
        document.append(section)
        return str(document)
register_adapter(HTMLTrendPointConfiguration)

class ColorSpan(HTMLgen.Span):
    def open_color_selector(self):
        return ("javascript:open_color_selector('%s', '%s');" %
                (self.input_id,self.button_id))
    def change_button_color(self):
        return ("javascript:change_button_color('%s', '%s');" %
                (self.input_id,self.button_id))
    def color_attr(self, value):
        try:
            return "#%06X" % int(value)
        except:
            return value
    def __init__(self, *contents, **kw):
        span_kw = kw.copy()
        self.input_id = span_kw["input.id"]
        del span_kw["input.id"]
        self.button_id = "%sbutton" % self.input_id
        input_kw = {"id":self.input_id,
                    "name":self.input_id,
                    "onChange":self.change_button_color(),
                    "class":"color",
                    }
        if span_kw.has_key("input.value"):
            input_kw["value"] = self.color_attr(span_kw["input.value"])
            del span_kw["input.value"]
        button_kw = {"type":"button",
                     "id":self.button_id,
                     "name":self.button_id,
                     "class":"color",
                     "onclick":self.open_color_selector()}
        if input_kw.has_key("value"):
            button_kw["style"] = "background-color: %s" % input_kw["value"]
        self.input = CustomInput(**input_kw)
        self.button = CustomButton(**button_kw)
        new_contents = [self.input, self.button]
        new_contents.extend(contents)
        HTMLgen.Span.__init__(self, *new_contents, **span_kw)
        return

class RangeSpan(HTMLgen.Span):
    def __init__(self, *contents, **kw):
        span_kw = kw.copy()
        self.from_id = span_kw["from.id"]
        del span_kw["from.id"]
        self.to_id = span_kw["to.id"]
        del span_kw["to.id"]
        self.from_value = span_kw["from.value"]
        del span_kw["from.value"]
        self.to_value = span_kw["to.value"]
        del span_kw["to.value"]
        from_kw = {"id":self.from_id,
                   "name":self.from_id,
                   "value":self.from_value}
        to_kw = {"id":self.to_id,
                 "name":self.to_id,
                 "value":self.to_value}
        self.from_input = CustomInput(**from_kw)
        self.to_input = CustomInput(**to_kw)
        new_contents = [CustomLabel("From:"),self.from_input,
                        CustomLabel("To:"),self.to_input]
        new_contents.extend(contents)
        HTMLgen.Span.__init__(self, *new_contents, **span_kw)
        return

class HTMLTrendPreferenceConfiguration(object):
    implements(IWebContent)
    adapts(ITrendPreferenceConfiguration)
    def __init__(self, tpf):
        self.tpf = tpf
        self.trend = tpf.trend
        self.encoded_name = urllib.quote_plus(self.trend.name)
        self.document = None
        self.generalpreferencescontainer = None
        self.pointpreferencescontainer = None
        self.axespreferencescontainer = None
        self.trend_configuration = None
        return
    def add_general_preferences(self):
        container = self.generalpreferencescontainer
        table = HTMLgen.TableLite(**{"width":"100%"})
        table.append(HTMLgen.TR(HTMLgen.TH("General Preferences")))
        preferences = self.trend_configuration['preferences']
        display_name_value = preferences['title']
        width_value = preferences['width']
        height_value = preferences['height']
        backgroundcolor_value = preferences['background']['color']
        textcolor_value = preferences['text']['color']
        textsize_value = preferences['text']['fontsize']
        textfont_value = preferences['text']['fontname']
        timespanvalue_value = preferences['timespan']['value']
        timespanunit_value = preferences['timespan']['unit']
        timereference_value = preferences['time-reference']
        frameset = HTMLgen.Frameset(
            HTMLgen.Span(CustomLabel("Display Name:", **{"for":"displayname"}),
                         CustomInput(**{"id":"displayname",
                                        "name":"displayname",
                                        "value":display_name_value}),
                         **{"style":"white-space: nowrap"}),
            HTMLgen.Span(CustomLabel("Width:", **{"for":"width"}),
                         CustomInput(**{"id":"width",
                                        "name":"width",
                                        "class":"i4d",
                                        "value":width_value}),
                         CustomLabel("Height:", **{"for":"height"}),
                         CustomInput(**{"id":"height",
                                        "name":"height",
                                        "class":"i4d",
                                        "value":height_value}),
                         **{"style":"white-space: nowrap"}),
            HTMLgen.Span(CustomLabel("Background Color:",
                                     **{"for":"backgroundcolor"}),
                         ColorSpan(**{"input.id":"backgroundcolor",
                                      "input.value":backgroundcolor_value}),
                         **{"style":"white-space: nowrap"}),
            HTMLgen.Span(CustomLabel("Text Color:",
                                     **{"for":"textcolor"}),
                         ColorSpan(**{"input.id":"textcolor",
                                      "input.value":textcolor_value}),
                         CustomLabel("Text Size:", **{"for":"textsize"}),
                         CustomInput(**{"id":"textsize",
                                        "name":"textsize",
                                        "class":"i2d",
                                        "value":textsize_value}),
                         CustomLabel("Font:", **{"for":"textfont"}),
                         CustomInput(**{"id":"textfont",
                                        "name":"textfont",
                                        "value":textfont_value}),
                         **{"style":"white-space: nowrap"}),
            HTMLgen.Span(CustomLabel("Initial Timespan:",
                                     **{"for":"timespanvalue"}),
                         CustomInput(**{"id":"timespanvalue",
                                        "name":"timespanvalue",
                                        "class":"i4d",
                                        "value":timespanvalue_value}),
                         HTMLgen.Select((("samples","samples"),
                                         ("hours","hours"),("minutes","minutes"),("seconds","seconds")),
                                        **{"name":"timespanunit",
                                           "size":1,
                                           "selected":(timespanunit_value,)}),
                         **{"style":"white-space: nowrap"}),
            HTMLgen.Span(CustomLabel("Time Reference:",
                                     **{"for":"timereference"}),
                         HTMLgen.Select((("Mediator","Mediator"),
                                         ("UTC","UTC"),("Browser","Browser")),
                                        **{"name":"timereference",
                                           "size":1,
                                           "selected":(timereference_value,)}),
                         **{"style":"white-space: nowrap"}),
            )
        table.append(HTMLgen.TR(HTMLgen.TD(frameset)))
        table.append(
            CustomInput(type='hidden', name='commitpreferences', value='Commit')
            )
        container.append(table)
        return
    def create_point_row(self, point_info):
        point_position = point_info['position']
        point_name = point_info['name']
        point_node = point_info['node']
        point_color = point_info['color']
        point_axis = point_info['y-axis']
        tag = HTMLgen.TR(
            HTMLgen.TD(point_position),
            HTMLgen.TD(point_name),
            HTMLgen.TD(ColorSpan(**{"input.id":
                                    "colorpoint%d" % point_position,
                                    "input.value": point_color})),
            HTMLgen.TD(HTMLgen.Select((("1","1"),("2","2",)),
                                      **{"name":
                                         "axispoint%d" % point_position,
                                         "size":1,
                                         "selected":(str(point_axis),)})),
            **{"class":['dark','light'][point_position&1]}
            )
        if not point_name or not point_node:
            tag = HTMLgen.Comment(tag)
        return tag
    def add_point_preferences(self):
        container = self.pointpreferencescontainer
        # I use a table for the header 'cause I don't know better...
        section = HTMLgen.TableLite(**{"width":"100%"})
        section.append(HTMLgen.TR(HTMLgen.TH("Point Preferences")))
        container.append(section)
        # And now the actual configuration data.
        table = HTMLgen.TableLite(**{"style":"white-space: nowrap; width: 1%",
                                     "class":"defaultstyle"})
        table.append(HTMLgen.TR(
            HTMLgen.TH("#"),
            HTMLgen.TH("Name"),
            HTMLgen.TH("Color"),
            HTMLgen.TH("Axis"),
            ))
        points_configuration = self.trend.get_points()
        points_preferences = self.trend_configuration['preferences']['points']
        for i in xrange(0,len(points_configuration)):
            point_info = {
                "position":i+1,
                "name":points_configuration[i]['name'],
                "node":points_configuration[i]['node'],
                "color":points_preferences[i]['color'],
                "y-axis":points_preferences[i]['y-axis'],
                }
            table.append(self.create_point_row(point_info))
        section.append(HTMLgen.TD(table))
        return
    def create_axis_row(self, axis_info, **options):
        axis_id = axis_info['id']
        axis_enable = axis_info['enable']
        axis_type = axis_info['type']
        axis_from = axis_info['from']
        axis_to = axis_info['to']
        enabled_options = options.get('enabled_options',
                                      (("disabled","0"),("enabled","1"),))
        type_options = ("numeric","binary")
        tag = HTMLgen.TR(
            HTMLgen.TD(axis_id),
            HTMLgen.TD(HTMLgen.Select(enabled_options,
                                      **{"name":
                                         "enableaxis%s" % axis_id,
                                         "size":1,
                                         "selected":(str(axis_enable),)})),
            HTMLgen.TD(RangeSpan(**{"from.id":"fromaxis%s" % axis_id,
                                    "to.id":"toaxis%s" % axis_id,
                                    "from.value": axis_from,
                                    "to.value": axis_to,
                                    "style":"white-space: nowrap"})),
            HTMLgen.TD(HTMLgen.Select(type_options,
                                      **{"name":
                                         "typeaxis%s" % axis_id,
                                         "size":1,
                                         "selected":(axis_type,)})),
            **{"class":['dark','light'][int(axis_id)&1]}
            )
        return tag
    def add_axes_preferences(self):
        container = self.axespreferencescontainer
        # I use a table for the header 'cause I don't know better...
        section = HTMLgen.TableLite(**{"width":"100%"})
        section.append(HTMLgen.TR(HTMLgen.TH("Axis Preferences")))
        container.append(section)
        # And now the actual configuration data.
        table = HTMLgen.TableLite(**{"style":"white-space: nowrap; width: 1%",
                                     "class":"defaultstyle"})
        table.append(HTMLgen.TR(
            HTMLgen.TH("Axis"),
            HTMLgen.TH("Status"),
            HTMLgen.TH("Range"),
            HTMLgen.TH("Type"),
            ))
        axis_preferences = self.trend_configuration['preferences']['y-axes']
        for i in xrange(0,len(axis_preferences)):
            axis_info = axis_preferences[i].copy()
            axis_info['id'] = str(i+1)
            row_options = {}
            if i == 0:
                # Left axis always enabled due to bug in ChartTool.
                axis_info['enable'] = "1"
                row_options['enabled_options'] = (("enabled","1"),)
            table.append(self.create_axis_row(axis_info, **row_options))
        section.append(HTMLgen.TD(table))
        return
    def create_document_structure(self):
        self.document = HTMLgen.SimpleDocument(
            title='trendMANAGER',
            stylesheet='/omega/trendmanager/styles.css',
            script=[HTMLgen.Script(src="/webapi/js/ColorPicker2.js"),
                    HTMLgen.Script(code="""
                    window.ColorPicker_targetButton = null;
                    function pickColor(color) {
                        ColorPicker_targetInput.value = color;
                        ColorPicker_targetButton.style.backgroundColor = color;
                        return;
                    }
                    var cp = new ColorPicker('window');
                    function open_color_selector(input_id, button_id) {
                        var input = document.getElementById(input_id);
                        var button = document.getElementById(button_id);
                        window.ColorPicker_targetButton = button;
                        cp.select(input, input_id);
                        return;
                    }
                    function change_button_color(input_id, button_id) {
                        var input = document.getElementById(input_id);
                        var button = document.getElementById(button_id);
                        var color = input.value;
                        button.style.backgroundColor = color;
                        return;
                    }
                    """)
                    ]
            )
        # Hack-around to set the class on the BODY for HTMLGen
        self.document.append(
            HTMLgen.Script(code="""
              document.body.className = 'manager';
              """)
            )
        page_heading = HTMLgen.Heading(2, "Trend Preferences",
                                       id="editorlabel")
        self.document.append(page_heading)
        section = HTMLgen.Div(**{'class':'section'})
        form = CustomForm('/trendmanager')
        #
        # Also, create methods in request handler to extract the values
        # to make changing the form easier.
        #
        self.generalpreferencescontainer = HTMLgen.Div(
            **{'id':'generalpreferencescontainer'}
            )
        form.append(self.generalpreferencescontainer)
        self.pointpreferencescontainer = HTMLgen.Div(
            **{'id':'pointpreferencescontainer'}
            )
        form.append(self.pointpreferencescontainer)
        self.axespreferencescontainer = HTMLgen.Div(
            **{'id':'axespreferencescontainer'}
            )
        form.append(self.axespreferencescontainer)
        form.submit = HTMLgen.Span(**{"class":"savespan"})
        form.submit.append(
            CustomInput(type='hidden', name='trend', value=self.encoded_name)
            )
        form.submit.append(
            CustomInput(type='submit', name='commitpreferences',
                        value='Commit')
            )
        form.submit.append(
            CustomInput(type='submit', name='cancelpreferences',
                        value='Cancel')
            )
        form.submit.append(
            CustomInput(type='submit', name='reloadpreferences',
                        value='Reload')
            )
        section.append(form)
        self.document.append(section)
        return
    def render(self):
        self.trend_configuration = self.trend.configuration()
        self.create_document_structure()
        self.add_general_preferences()
        self.add_point_preferences()
        self.add_axes_preferences()
        return str(self.document)
register_adapter(HTMLTrendPreferenceConfiguration)

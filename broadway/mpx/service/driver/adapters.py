"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
import string
import urllib
import itertools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry.backports import Dictionary
from mpx.www.w3c.xhtml.interfaces import IWebContent
from interfaces import IPeriodicDriverManager
from interfaces import IPeriodicDriver
from mpx.lib.htmlgen import *

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
        if self.selected:
            element += ' selected="selected"'
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

nodeselectscript = """
var objWin = null;
function open_node_selector(id){
     if (arguments.length == 0) {
         var id = this.getAttribute('name');
     }
     var w = '600';
     var h = '600';
     var features = "height=1,width=1,resizeable,scrollbars";
     objWin = window.open("/webapi/nodeSelector.html?textid=" + id, "nodeSelector", features);
     var height = window.screen.availHeight;
     var width = window.screen.availWidth;
     var left_point = parseInt(width/2) - parseInt(w/2);
     var top_point =  parseInt(height/2) - parseInt(h/2);
     objWin.moveTo(left_point,top_point);
     objWin.resizeTo(w,h);
     objWin.focus();
}
"""

class HTMLPeriodicDriverManagerForm(object):
    implements(IWebContent)
    adapts(IPeriodicDriverManager)
    
    def __init__(self, parent):
        self.parent = parent
        self.path = None
        self.base_doc = HTMLgen.SimpleDocument(
            title = self.get_page_title(),
            stylesheet='/omega/includes/css/valuedriverpage.css')

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
        actions = ['remove', 'edit']
        return actions

    def get_action_behaviour(self, action):
        if action == 'remove':
            return "return confirm('Delete periodic driver and its configuration?');"
        return ''

    def get_allowed_additions(self):
        return ['Value Driver']

    def render(self, path = None):
        attrs = KeyWordAssist()
        if path is not None:
            self.path = path
        request_path = self.get_request_path()
        if request_path is None:
            raise Exception('Adapter does not know request path.')
        document = self.base_doc.copy()
        page_heading = HTMLgen.Heading(2, self.get_page_heading(), id="editorlabel")
        document.append(page_heading)
        encoded_parent = urllib.quote_plus(self.parent.url)
        context = HTMLgen.Input(name='manage', value=encoded_parent, type='hidden')

        navigation = HTMLgen.Div(**attrs('class', 'confignavigation'))
        reloadform = HTMLgen.Form(request_path)
        reloadform.append(context)
        reloadform.submit.value = 'reload'
        #backform = HTMLgen.Form()
        #backform.submit.value = 'back'
        #backform.submit.onClick = "top.location = '/omega/webscheduler/index.html'; return false;"
        navigation.append(reloadform)
        #navigation.append(backform)
        document.append(navigation)

        children_section = HTMLgen.Div(**attrs('class','section'))
        children_table = HTMLgen.TableLite(
            **attrs('class', 'configuration-table'))
        children_header = HTMLgen.TR(**attrs('class','table-header'))
        for header in self.get_column_names() + ['Action']:
            headcell = HTMLgen.TH(header, scope="col", abbr=header,
                                  id="%sheader" % header)
            if header == "Action":
                setattr(headcell, "class", "control")            
            children_header.append(headcell)
        children_table.append(children_header)

        classes = itertools.cycle(['light', 'dark'])
        children = self.parent.children_nodes()
        children = filter(IPeriodicDriver.providedBy, children)
        for child in children:
            row = HTMLgen.TR(**attrs('class', classes.next()))
            cells = self.get_row_values(child)
            # First value is assumed to be row header.
            row.append(HTMLgen.TH(cells[0]))
            # Any other values are added as regular cells.
            for value in cells[1:]:
                row.append(HTMLgen.TD(value))

            actioncell = HTMLgen.TD(**attrs("class", "control"))
            encoded_name = urllib.quote_plus(child.name)
            actions = self.get_row_actions(child)
            for action in actions:
                actionform = HTMLgen.Form(request_path)
                actionform.append(context)
                actioninput = HTMLgen.Input(name=action, value=encoded_name, type='hidden')
                actionform.append(actioninput)
                actionform.submit.value = action
                behaviour = self.get_action_behaviour(action)
                if behaviour:
                    actionform.submit.onClick = behaviour
                actioncell.append(actionform)
                if action != actions[-1]:
                    actioncell.append(' ')
            row.append(actioncell)
            children_table.append(row)
        children_section.append(children_table)
        for childtype in self.get_allowed_additions():
            add_form = HTMLgen.Form(request_path)
            add_form.append(context)
            addinput = HTMLgen.Input(name = 'add',
                                     value = childtype,
                                     type = 'hidden')
            add_form.append(addinput)
            add_form.submit.value = 'Add ' + childtype
            children_section.append(add_form)
        document.append(children_section)
        return str(document)

register_adapter(HTMLPeriodicDriverManagerForm)

closescript = """
function handle_close() {
  if (window.opener) {
    window.close();
    return false;
  } else {
    return true;
  }
}
"""

class HTMLPeriodicDriverForm(object):
    implements(IWebContent)
    adapts(IPeriodicDriver)

    def __init__(self, driver):
        self.driver = driver
        scripts = []
        scripts.append(HTMLgen.Script(code = nodeselectscript))
        scripts.append('\n')
        scripts.append(HTMLgen.Script(code = closescript))
        scripts.append('\n')
        self.base_doc = HTMLgen.SimpleDocument(
            title='PeriodicDriver Editor', 
            stylesheet='/omega/includes/css/valuedriverpage.css', script=scripts)

    def render(self, request_path):
        attrs = KeyWordAssist()
        document = HTMLgen.Div(**attrs("class", "content"))        
        encoded_driver = urllib.quote_plus(self.driver.name)
        encoded_manager = urllib.quote_plus(self.driver.parent.url)
        context = HTMLgen.Input(name='manage', value=encoded_manager, type='hidden')
        editorinput = HTMLgen.Input(name='edit', type='hidden', value=encoded_driver)
        navigation = HTMLgen.Div(**attrs('class', 'confignavigation'))
        closeform = HTMLgen.Form(request_path)
        closeform.append(context)
        closeform.submit.value = 'close'
        closeform.submit.onClick = "return handle_close();"
        navigation.append(closeform)
        #document.append(navigation)

        config_form = HTMLgen.Form(request_path)
        config_form.append(context)
        config_form.submit.value = 'Save'
        hidden = HTMLgen.Input(name="configure", type='hidden', value=encoded_driver)
        config_form.append(hidden)
        config_section = HTMLgen.Div(**attrs('class','section'))
        config_table = HTMLgen.TableLite(
            **attrs('class', 'configuration-table'))
        config_header = HTMLgen.TR(**attrs('class', 'table-header'))
        for header in ['Attribute', 'Value']:
            headcell = HTMLgen.TH(
                header, scope="col", abbr=header, id="%sheader" % header)
            config_header.append(headcell)
        config_table.append(config_header)
        configrows = []
        classes = itertools.cycle(["light", "dark"])
        config = Dictionary(self.driver.configuration())

        namerow = HTMLgen.TR(**attrs('class', classes.next()))
        namerow.append(HTMLgen.TH('Value Driver Name'))
        namefield = HTMLgen.Input(
            value=config.pop('name'), name='configure.name')
        namerow.append(
            HTMLgen.TD(namefield, **attrs('class', 'configuration')))
        configrows.append(namerow)
        
        periodrow = HTMLgen.TR(**attrs('class', classes.next()))
        periodrow.append(HTMLgen.TH('Poll Period'))
        periodfield = HTMLgen.Input(
            value=config.pop('period'), name='configure.period')
        periodrow.append(
            HTMLgen.TD(periodfield, **attrs('class', 'configuration')))
        configrows.append(periodrow)
        
        inputrow = HTMLgen.TR(**attrs('class', classes.next()))
        inputrow.append(HTMLgen.TH('Input Node'))
        inputfield = IdentifiedInput(
            value=config.pop('input'), id='inputnode', name='configure.input')
        inputcell = HTMLgen.TD()
        inputcell.append(inputfield)
        browsebutton = HTMLgen.Input(type='button', value='Select', name = 'context')
        browsebutton.onClick = "utils.select.nodes.open('%s');" % inputfield.id
        inputcell.append(browsebutton)
        inputrow.append(inputcell)
        configrows.append(inputrow)
        
        nonoutputrows = len(configrows)
        outputs = config.pop('outputs')
        for output in outputs:
            outputrow = HTMLgen.TR(**attrs('class', classes.next()))
            outputrow.append(HTMLgen.TH('Output Node'))
            outputfield = IdentifiedInput(
                value=output, name='configure.outputs', 
                id='Output%s' % (len(configrows) - nonoutputrows))
            outputcell = HTMLgen.TD()
            outputcell.append(outputfield)
            browsebutton = HTMLgen.Input(
                type='button', value='Select', name='context')
            browsebutton.onClick = (
                "utils.select.nodes.open('%s');" % outputfield.id)
            outputcell.append(browsebutton)
            outputrow.append(outputcell)
            configrows.append(outputrow)
        
        conversionrow = HTMLgen.TR(**attrs('class', classes.next()))
        conversionrow.append(HTMLgen.TH('Input Conversion'))
        conversions = [('None', 'none'), ('Integer', 'int'), 
                       ('Float', 'float'), ('String', 'str')]
        options = []
        conversion = config.pop('conversion')
        for name, value in conversions:
            selected = not not (conversion == value)
            option = StandardizedOption(name, None, value, selected)
            options.append(option)
        conversionfield = StandardizedSelect(options, 
                                             name='configure.conversion')
        conversionrow.append(
            HTMLgen.TD(conversionfield, **attrs('class', 'configuration')))
        configrows.append(conversionrow)
        
        config_table.append(*configrows)
        config_form.append(config_table)
        config_section.append(config_form)
        document.append(config_section)
        return str(document)

register_adapter(HTMLPeriodicDriverForm)


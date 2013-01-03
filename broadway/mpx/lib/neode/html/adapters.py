"""
Copyright (C) 2010 2011 Cisco Systems

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
from HTMLgen import HTMLgen
from HTMLgen import Formtools
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.www.w3c.dom.interfaces import IDomNode
from mpx.www.w3c.dom.interfaces import IDomDocument
from mpx.www.w3c.dom.interfaces import IDomElement
from mpx.www.w3c.dom.interfaces import IDomNodeList
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.neode.html import read

class KeyWordAssist(dict):
    def __call__(self, *args):
        pairs = []
        for i in range(0, len(args), 2):
            pairs.append((args[i],args[i+1]))
        # Modification to enable in python 2.2
        pairs = dict(pairs)
        self.update(pairs)
        return self.copy()

class HTMLDomDocument(object):
    implements(IWebContent)
    adapts(IDomDocument)

    def __init__(self, domnode):
        self.domnode = domnode
        self.base_doc = HTMLgen.SimpleDocument(
            title='DomNode Browser', style=read('node_style.css'))

    def render(self):
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        parent = self.domnode.parentNode
        title = 'Browse DOM Node: <em>%s</em>'
        title_tuple = (self.domnode.nodeName,)
        if parent is not None:
            title = title + ', Located at: <em>%s</em>'
            title_tuple = title_tuple + (parent.nodeID,)
        title = title % title_tuple
        header = HTMLgen.Heading(
            1, title, html_escape="OFF", **attrs('class','title'))
        document.append(header)

        config_section = HTMLgen.Div(**attrs('class','config_section'))
        config_section_header = HTMLgen.Heading(
            2, 'Configuration',**attrs('class','section'))
        config_section.append(config_section_header)

        config_table = HTMLgen.TableLite(**attrs('class','config_table'))
        config_caption = HTMLgen.Caption('Node configuration table')
        config_table.append(config_caption)
        configuration = self.domnode.attributes
        header_row = HTMLgen.TR(**attrs('class','config_header'))
        header_row.append(HTMLgen.TH('Name'), HTMLgen.TH('Value'))
        rows = [header_row]
        for name,attr in configuration.items():
            row = HTMLgen.TR()
            row.append(HTMLgen.TD(name))
            row.append(HTMLgen.TD(attr.value))
            rows.append(row)
        config_table.append(*rows)
        config_section.append(config_table)

        child_section = HTMLgen.Div(**attrs('class','child_section'))
        child_section_header = HTMLgen.Heading(
            2, 'Child Nodes',**attrs('class','section'))
        child_section.append(child_section_header)

        child_table = HTMLgen.TableLite(**attrs('class','child_table'))
        child_caption = HTMLgen.Caption("Child node listing")
        child_table.append(child_caption)
        header_row = HTMLgen.TR(**attrs('class','child_header'))
        header_row.append(
            HTMLgen.TH('Name'), HTMLgen.TH('URL'), HTMLgen.TH('Value'))
        rows = [header_row]
        children = self.domnode.childNodes
        for child in children:
            row = HTMLgen.TR()
            row.append(HTMLgen.TD(child.nodeName))
            row.append(HTMLgen.TD(child.nodeID))
            value = child.nodeValue
            if value is None: value = 'N/A'
            row.append(HTMLgen.TD(value))
            rows.append(row)
        child_table.append(*rows)
        child_section.append(child_table)

        document.append(config_section)
        document.append(child_section)
        return str(document)

register_adapter(HTMLDomDocument)

class HTMLDomNodeConfiguration(object):
    implements(IWebContent)
    adapts(IDomNode)

    def __init__(self, domnode):
        self.domnode = domnode
        self.base_doc = HTMLgen.SimpleDocument(
            title='DomNode Browser', style=read('node_style.css'))

    def render(self):
        attrs = KeyWordAssist()
        document = self.base_doc.copy()
        parent = self.domnode.parentNode
        title = 'Edit DOM Node: <em>%s</em>'
        title_tuple = (self.domnode.nodeName,)
        if parent is not None:
            title = title + ', Located at: <em>%s</em>'
            title_tuple = title_tuple + (parent.nodeID,)
        title = title % title_tuple
        header = HTMLgen.Heading(
            1, title, html_escape="OFF", **attrs('class','title'))
        document.append(header)

        config_section = HTMLgen.Div(**attrs('class','config_section'))
        config_section_header = HTMLgen.Heading(
            2, 'Configuration',**attrs('class','section'))
        config_section.append(config_section_header)

        configuration = self.domnode.attributes
        config_form = HTMLgen.Form()
        config_table = []
        for aname, avalue in configuration.items():
            avalue = avalue.value
            config_table.append((aname, HTMLgen.Input(name=aname, value=avalue, size="150")))
        config_form.append(Formtools.InputTable(config_table))
        config_section.append(config_form)

        child_section = HTMLgen.Div(**attrs('class','child_section'))
        child_section_header = HTMLgen.Heading(
            2, 'Child Nodes',**attrs('class','section'))
        child_section.append(child_section_header)

        child_table = HTMLgen.TableLite(**attrs('class','child_table'))
        child_caption = HTMLgen.Caption("Child node listing")
        child_table.append(child_caption)
        header_row = HTMLgen.TR(**attrs('class','child_header'))
        header_row.append(
            HTMLgen.TH('Name'), HTMLgen.TH('URL'), HTMLgen.TH('Value'))
        rows = [header_row]
        children = self.domnode.childNodes
        for child in children:
            row = HTMLgen.TR()
            row.append(HTMLgen.TD(child.nodeName))
            row.append(HTMLgen.TD(child.nodeID))
            value = child.nodeValue
            if value is None: value = 'N/A'
            row.append(HTMLgen.TD(value))
            rows.append(row)
        child_table.append(*rows)
        child_section.append(child_table)

        document.append(config_section)
        document.append(child_section)
        return str(document)

register_adapter(HTMLDomNodeConfiguration)


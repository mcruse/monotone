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
from mpx.componentry import implements
from mpx.componentry.presentation.template import TemplateProcessor
from interfaces import IDocumentElement
from interfaces import IContainerElement
from interfaces import ISimpleElement
from interfaces import IWebContent


class SimpleElement(object):
    implements(ISimpleElement)
    
    def __init__(self, tag_name, attributes = {}):
        self.tag_name = tag_name
        self.attributes = attributes
        self.content = ''
    def set_content(self,content):
        self.content = content
    def set_attribute(self, name, value):
        self.attributes[name] = value
    def get_attribute(self, name):
        return self.attributes[name]
    def get_attributes(self):
        return self.attributes.copy()
    def get_attribute_names(self):
        return self.attributes.keys()
    def get_content(self):
        return self.content
    def render_open(self):
        attrs = ''
        for key,value in self.attributes.items():
            attrs += ' %s="%s"' % (key,value)
        return '<%s %s>' % (self.tag_name, attrs)
    def render_content(self):
        return self.get_content()
    def render_close(self):
        return '</%s>' % self.tag_name
    def render(self):
        output = self.render_open() 
        output += self.render_content() 
        output += self.render_close()
        return output

class AttributeDictionary(dict):
    """
        Dictionary type object that can be configured 
        with key/value pairs of attributes associated with 
        an element.
        
        Object provides render(), which returns single string, 
        suitable for instertion within an opening tag, representing 
        all attributes within dictionary.
        
        Also provides psuedo-key 'attributes' which returns 
        same results as render.  This is to enable usage of 
        this object within template, where the template may 
        specify "$attributes" or "${attributes} inside opening 
        tag.
        
        WARNING: Conflict will occur if associated attributes 
        have actual attribute value named 'attributes.'  If this 
        is the case, this dictionary will need to be extended to 
        provide a workaround.
    """ 
    implements(IWebContent)
    
    def __init__(self, *args, **kw):
        super(AttributeDictionary, self).__init__(*args, **kw)
    
    def render(self):
        output = ''
        for name,value in self.items():
            output += '%s="%s" ' % (name, value)
        if output: output = output[0:-1]
        return output
    
    def __getitem__(self, item):
        if item == 'attributes':
            return self.render()
        return super(AttributeDictionary, self).__getitem__(item)
    
    def __setitem__(self, item, *args):
        if item == 'attributes':
            raise KeyError('CONFLICT: key "attributes" is unusable keyword.')
        return super(AttributeDictionary, self).__setitem__(item, *args)
    
    def get(self, item, *args):
        if item == 'attributes':
            return self.render()
        return super(AttributeDictionary, self).get(item, *args)
    
    def setdefault(self, item, *args):
        if item == 'attributes':
            return self.render()
        return super(AttributeDictionary, self).setdefault(item, *args)

class BoundTemplateElement(TemplateProcessor):
    implements(IWebContent)
    
    def __init__(self, mapping, format_data):
        self.mapping = mapping
        super(BoundTemplateElement, self).__init__(format_data)
    def substitute(self, **kw):
        return super(
            BoundTemplateProcessor, self).substitute(self.mapping, **kw)
    def safe_substitute(self, mapping, **kw):
        return super(
            BoundTemplateProcessor, self).safe_substitute(self.mapping, **kw)
    def render(self):
        return self.substitute()

class ContainerElement(SimpleElement):
    implements(IContainerElement)
    
    def __init__(self, tag_name, attributes={}, children=[]):
        self.elements = children
        SimpleElement.__init__(self,tag_name,attributes)
    def add_element(self,element):
        self.elements.append(element)
    def render_content(self):
        output = ''
        for element in self.elements:
            output += element.render()
        return output + SimpleElement.render_content(self)

class DocumentElement(ContainerElement):
    implements(IDocumentElement)
    
    def render(self):
        return ContainerElement.render(self)

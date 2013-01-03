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
import string

from HTMLgen import HTMLgen

from mpx.componentry import Interface
from mpx.componentry import adapts
from mpx.componentry import class_implements
from mpx.componentry import implements
from mpx.componentry import register_adapter

##
# Cheesy reuse, but I don't really want to perpetuate the copy-and-paste re-use
# that most of our web-stuff suffers from...
from mpx.service.alarms2.trigger.xhtml.adapters import nodeselectscript
from mpx.service.alarms2.trigger.xhtml.adapters import IdInput

class CustomInput(IdInput):
    def __init__(self, **kw):
        self.disabled = False
        self.klass = kw.get('class','')
        if self.klass:
            kw = kw.copy()
            del kw['class']
        IdInput.__init__(self,**kw)
        return
    def __str__(self):
        result = IdInput.__str__(self)
        if (self.disabled):
            result = result.replace('>',' disabled>')
        if (self.klass):
            result = result.replace('>',' class="%s">' % self.klass)
        return result

# Class for all dojo specific customizations ...
# A separate class is required (instead of making the changes directly in
# CustomInput() class because that changes the look-n-feel/style of other 
# GUI tabs which may not be required.
class DojoInput(CustomInput):
    def __init__(self, **kw):
        self.dojoType = kw.get('dojoType', 'dijit.form.TextBox')
        self.invalidMessage = kw.get('invalidMessage','')
        self.constraints = kw.get('constraints','')
        self.regExp = kw.get('regExp','')
        self.id = kw.get('id', '')
        self.checked = kw.get('checked', False)
        self.readOnly = kw.get('readOnly', False)
        CustomInput.__init__(self,**kw)
        return
    def __str__(self):
        result = CustomInput.__str__(self)
        if (self.dojoType):
            result = result.replace('>',' dojoType="%s">' % self.dojoType)
        if (self.constraints):
            result = result.replace('>',' constraints="%s">' % self.constraints)
        if (self.invalidMessage):
            result = result.replace('>',' invalidMessage="%s">' % self.invalidMessage)
        if (self.regExp):
            result = result.replace('>',' regExp="%s">' % self.regExp)
        if (self.id):
            result = result.replace('>',' id="%s">' % self.id)
        if (self.checked):
            result = result.replace('>',' checked>')
        if (self.readOnly):
            result = result.replace('>',' readOnly="true">')
        return result

class CustomForm:
    """Define a user filled form. Uses POST method.
   
    *cgi* is the URL to the CGI processing program.  Input objects
    (any others as well) are appended to this container widget.
    
    Keywords
    
        name -- name of the form
        submit -- The Input object to be used as the submit button.
                  If none specified a Submit button will automatically
                  be appended to the form. Do not manually append your
                  submit button. HTMLgen will append it for you.
        reset  -- Input object to be used as a reset button.
        target -- set a TARGET attribute
        enctype -- specify an Encoding type.
        onSubmit -- script, which is executed, when the form is submitted
    """
    def __init__(self, cgi = None, **kw):
        self.contents = []
        self.cgi = cgi
        self.submit = CustomInput(type='submit',
                                  name='SubmitButton', value='Send')
        self.reset = None
        self.target = None
        self.enctype = None
        self.name = None
        self.id = None
        self.targetType = None
        self.targetID = None
        self.onSubmit = ''
        self.klass = kw.get('class','')
        if self.klass:
            kw = kw.copy()
            del kw['class']
        HTMLgen.overlay_values(self, kw)

    def append(self, *items):
        """Append any number of items to the form container.
        """
        for item in items:
            self.contents.append(item)

    def __str__(self):
        s = ['\n<FORM METHOD="POST"']
        if self.cgi: s.append(' ACTION="%s"' % self.cgi)
        if self.enctype: s.append(' ENCTYPE="%s"' % self.enctype)
        if self.target: s.append(' TARGET="%s"' % self.target)
        if self.name: s.append(' NAME="%s"' % self.name)
        if self.id: s.append(' ID="%s"' % self.id)
        if self.onSubmit: s.append(' onSubmit="%s"' % self.onSubmit)
        if self.targetType: s.append(' targetType="%s"' % self.targetType)
        if self.targetID: s.append(' targetID="%s"' % self.targetID)
        if self.klass: s.append( 'class="%s"' % self.klass)
        s.append('>\n')
        for item in self.contents:
            s.append(str(item))
        s.append(str(self.submit))
        if self.reset: s.append(str(self.reset))
        s.append('\n</FORM>\n')
        return string.join(s, '')

class CustomLabel(HTMLgen.AbstractTag):
    """Specify a label within a document (frameset).
    """
    tagname = 'LABEL'
    attrs = ('for', 'class','id', 'style', 'lang', 'title', 'accesskey',
             'onfocus', 'onblur', 'onclick', 'ondblclick', 'onmousedown',
             'onmouseup', 'onmouseover', 'onmousemove', 'onmouseout',
             'onkeypress', 'onkeydown', 'onkeyup')
    attr_template , attr_dict = HTMLgen._make_attr_inits(attrs)

class CustomButton(HTMLgen.AbstractTag):
    """Specify a button within a document.
    """
    tagname = 'BUTTON'
    attrs = ('name', 'value', 'type', 'class','id', 'style', 'lang', 'title',
             'accesskey', 'disabled', 'tabindex', 'onfocus', 'onblur',
             'onclick', 'ondblclick', 'onmousedown', 'onmouseup',
             'onmouseover', 'onmousemove', 'onmouseout', 'onkeypress',
             'onkeydown', 'onkeyup')
    attr_template , attr_dict = HTMLgen._make_attr_inits(attrs)

class MockDOMish(object):
    def __init__(self, tag):
        print "Warning:  Adapting class %r with MockDOMish!" % (
           tag.__class__.__name__
            )
        self.tag = tag
        return
    def getTagById(self, id):
        return None

class IDOMish(Interface):
    pass

def domish(tag):
    try:
        return IDOMish(tag)
    except:
        return MockDOMish(tag)

class ILeafNode(Interface):
    pass

class_implements(IdInput, ILeafNode)

class IContentContainter(Interface):
    pass

class_implements(HTMLgen.AbstractTag, IContentContainter)
class_implements(HTMLgen.BasicDocument, IContentContainter)
class_implements(HTMLgen.Container, IContentContainter)
class_implements(HTMLgen.Form, IContentContainter)
class_implements(CustomForm, IContentContainter)

class IDataContainer(Interface):
    pass

class_implements(HTMLgen.List, IDataContainer)

class LeafNodeDOM(object):
    implements(IDOMish)
    adapts(ILeafNode)
    def __init__(self, tag):
        self.tag = tag
        return
    def getAttribute(self, name):
        if hasattr(self.tag,name):
            return getattr(self.tag,name)
        elif hasattr(self.tag,'attr_dict'):
            if self.tag.attr_dict.has_key(name):
                ugh = self.tag.attr_dict[name].split('"')
                if len(ugh) == 3:
                    return ugh[1]
        return None
    def setAttribute(self, name, value):
        if hasattr(self.tag,name):
            return setattr(self.tag,name,value)
        elif hasattr(self.tag,'attr_dict'):
            self.tag.attr_dict[name] = ' %s="%s"' % (name, value)
        return None
    def getTagById(self, id):
        my_id = self.getAttribute('id')
        if my_id == id:
            return self.tag
        return None

register_adapter(LeafNodeDOM)

class ContentContainterDOM(LeafNodeDOM):
    implements(IDOMish)
    adapts(IContentContainter)
    def getTagById(self, id):
        result = super(ContentContainterDOM,self).getTagById(id)
        if result is None:
            for tag in self.tag.contents:
                result = domish(tag).getTagById(id)
                if result is not None:
                    return result
        return result

register_adapter(ContentContainterDOM)

class DataContainterDOM(LeafNodeDOM):
    implements(IDOMish)
    adapts(IDataContainer)
    def getTagById(self, id):
        result = super(DataContainterDOM,self).getTagById(id)
        if result is None:
            for tag in self.tag.data:
                result = domish(tag).getTagById(id)
                if result is not None:
                    return result
        return result

register_adapter(DataContainterDOM)

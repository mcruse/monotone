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

class Tag:
    def __init__(self,type):
        self.attributes = {}
        self.innerHTML = ''
        self.type = type    
    def appendinnerHTML(self,text):
        self.innerHTML += '%s' % text
    def _get_attributes(self):
        attrs = ''
        for k,v in self.attributes.items():
            attrs += '%s="%s" ' %(k,v)
        return attrs
    def get(self,indent='',after_start=''):
        html = '%s<%s %s>%s%s</%s>\n' % (indent,self.type,
                                         self._get_attributes(),
                                         after_start,
                                         self.innerHTML,self.type)        
        return html
    def appendChild(self,tag):
        self.innerHTML += tag.get()
    def __setitem__(self,k,v):
        self.attributes[k] = v
    def __getitem__(self,k):
        return self.attributes[k]
    def has_key(self,k):
        return self.attributes.has_key(k)
    
class _Row(Tag):
    def __init__(self):
        Tag.__init__(self,'tr')
        self._cells = []
    def insertCell(self,index=-1):
        if index == -1:
            index = len(self._cells)
        td = Td()
        self._cells.insert(index,td)
        
    def cells(self,index=-1):
        if index == -1:
            index = len(self._cells)-1
        return self._cells[index]
    def complete(self):
         for td in self._cells:
            self.appendChild(td)
class Table(Tag):
    def __init__(self,type='table'):
        Tag.__init__(self,type) 
        self._rows = []      
    def insertRow(self,index=-1):
        tr = _Row()
        if index == -1:
            index = len(self._rows)
        self._rows.insert(index, tr)
    def rows(self,index=-1):
        if index == -1:
            index = len(self._rows) -1
        return self._rows[index]
    def getRows(self):
        return self._rows
    def get(self):
        for row in self._rows:
            row.complete()
            self.appendChild(row)
        html = '<%s %s>\n%s</%s>\n' % (self.type,
                                     self._get_attributes()
                                     ,self.innerHTML,self.type)      
        return html
class Link(Tag):
    def __init__(self,type='link'):
        Tag.__init__(self,type)
        self.attributes['REL'] = 'stylesheet'
        self.attributes['type'] = 'text/css'
        
class Head(Tag):
    def __init__(self,type='head'):
        Tag.__init__(self,type)
class Title(Tag):
    def __init__(self,type='title'):
        Tag.__init__(self,type)
class Body(Tag):
    def __init__(self,type='body'):
        Tag.__init__(self,type)        
class Div(Tag):
    def __init__(self,type='div'):
        Tag.__init__(self,type) 
class Span(Tag):
    def __init__(self,type='span'):
        Tag.__init__(self,type) 
class Tr(Tag):
    def __init__(self,type='tr'):
        Tag.__init__(self,type)     
    def get(self):
        return Tag.get(self,'','\n')
class Td(Tag):
    def __init__(self,type='td'):
        Tag.__init__(self,type) 
    def get(self):
        return Tag.get(self,'\t')
class Img(Tag):
    def __init__(self,type='img'):
        Tag.__init__(self,type) 
class A(Tag):
    def __init__(self,type='a'):
        Tag.__init__(self,type) 
class StyleAttr:
    def __init__(self):
        self.styles = {}
    def __setitem__(self,k,v):
        self.styles[k] = v
    def __getitem__(self,k):
        return self.styles[k]
    def has_key(self,k):
        return self.styles.has_key(k)
    def get(self):
        t = ''
        for k,v in self.styles.items():
            t += '%s:%s;' % (k,v)
        return t    
if __name__ == '__main__':
    tbl = Table()
    tbl.insertRow()
    tbl.rows(0).insertCell()
    tbl.rows(0)['style'] = 'color:red'
    tbl.insertRow()
    tbl.rows(1)['height'] = '500px'
    tbl.rows(1).insertCell()
    tbl.rows(1).cells(0).innerHTML = 'test'
    print tbl.get()
    
    '''t = Tag('span')
    t['style'] = 'color:red'
    t['height'] = '100px'
    t.add_text('Test')
    t2 = Tag('div')
    t2['width'] = '100px'
    t2.appendChild(t)
    print t2.get()'''
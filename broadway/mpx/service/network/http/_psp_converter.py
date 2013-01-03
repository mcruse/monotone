"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
import re
import string
def log(msg):
    print msg
class PSPConverter:
    def __init__(self,fp,standalone=1,indent_level='    '):
        self.fp = fp
        self.py = ''
        self.standalone = standalone
        self.indent_default = indent_level
        self.RE_CODE_START = re.compile('.*<%{1}\s*$')
        self.RE_SET_CODE_SECTION = re.compile('.*<%%>\s*$')
        self.RE_SET_CODE_TOKENS = re.compile('<%%>')
        self.RE_END_CODE = re.compile('.*%>$')
        self.RE_STRING = re.compile('\S')
    def _create_indent(self,index):
        start = 0
        indent = self.indent_default
        while start < index:
            indent += ' '
            start +=1
        return indent  
    def _look_for_tags(self,l):
        tags = re.findall('(<%=.*?>)',l)          
        return tags
    def _clean_line(s3elf,l):
        l = string.rstrip(l)
        m =re.search('\S',l)
        if m:
            s = m.start()
            l = '%s%s' % (l[:s].replace('\t','    '),l[s:])            
        return l
    def _replace_tags(self,l,tags):  
        nl = ''
        if tags:
           for tag in tags:
               l = l.replace(tag,'" + str(' + string.strip(tag[3:-2]) + ') + "')   
        nl += '"%s\\n"' % l 
        return nl
    def _replace_quotes(self,l):
        rt = ''
        if l[-1:] == '\n':
            rt = l[:-1].replace('"','\\"') 
        else:
            rt = l[:].replace('"','\\"') 
        return rt
    def convert(self):
        self.fp.seek(0)
        in_code_section = 0
        html_under_code = 0
        indent = self.indent_default
        if self.standalone ==1:
            self.py = 'def run(psp,request,response):\n'
        previous_line = None
        for l in self.fp.readlines():  
            test = 0
            if in_code_section:                   
                l = self._clean_line(l)                
                l += '\n'
                end_m = self.RE_END_CODE.match(l)                
                if end_m:
                    indent = self._create_indent(end_m.span()[1] -2)                    
                    in_code_section = 0
                else:
                    self.py += '%s%s' % (self.indent_default,l)
            elif self.RE_CODE_START.match(l):                
                html_under_code = 0
                indent = self.indent_default
                in_code_section =1 
            elif self.RE_SET_CODE_SECTION.match(l):
                m = self.RE_SET_CODE_TOKENS.search(l)
                indent = self._create_indent(m.start())             
                html_under_code =1 
            else: 
                line = self._replace_quotes(l) 
                if previous_line:                   
                    if self.RE_END_CODE.match(previous_line):                        
                        html_under_code = 1                       
                if html_under_code:
                    m = self.RE_STRING.search(line)
                    if m: 
                        # if we are the first line lets get the indent
                        if html_under_code == 1 :                            
                            indent = self._create_indent(m.start())                            
                            html_under_code += 1 
                        # use the first line indent for the rest of the HTML lines
                        else:
                            html_under_code +=1
                    else:
                        html_under_code = 0              
                else:
                    # use the the html as the indent                    
                    m  = self.RE_STRING.search(line)
                    if m and previous_line != '\n' and html_under_code:
                        indent = self._create_indent(m.start())
                    else:
                        indent = self.indent_default    
                tags = self._look_for_tags(line)
                l = self._replace_tags(line,tags)
                self.py += '%spsp.write(%s)\n' % (indent,l)                
            previous_line = l
    def get(self):        
        return self.py
    
if __name__ == '__main__':
    import sys
    fn = ''
    if len(sys.argv) > 1:
        fn = sys.argv[1]
    print 'Opening File:\n    %s\n' % fn
    f = open(fn,'r')
    psp = PSPConverter(f)
    psp.convert()
    of = open('test.py','w')
    of.write(psp.get())
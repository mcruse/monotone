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
import re
import sys
import string

class Function:
    def __init__(self,name):
        self.name = name
        self.params = []
        self.notes = []
        self.template_file = "function_template.html"
        self.rturn = "null"
        self.desc = ""
        self.patterns = {}
        self.patterns['\$\$FUNCTION\$\$'] = self.get_name
        self.patterns['\$\$DESC\$\$'] = self.get_desc
        self.patterns['\$\$PARAMS\$\$'] = self.get_params_rows
        self.patterns['\$\$PARAMS_LIST\$\$'] = self.get_params_list
        self.patterns['\$\$NOTES\$\$'] = self.get_notes
        self.patterns['\$\$RETURN\$\$'] = self.get_return
    def add_param(self,name,desc,example=None):
        param ={}
        param['name'] = name
        param['desc'] = desc
        param['example'] = example
        self.params.append(param)
    def set_return(self,rturn):
        self.rturn = rturn
    def add_note(self,note):
        self.notes.append(note)
    def set_desc(self,desc):
        self.desc = desc
    def get_params_list(self):
        _html = '<span class="param">%s</span>,'
        html = ""
        for p in self.params:
            html += _html % p['name']
        return html[:-1]
    def get_notes(self):
        html =""
        if len(self.notes) > 0: 
            for n in self.notes:
                html += '<tr><td class="label" width="30">NOTE</td>\n'            
                html += '<td class="note">%s</td>\n' % n
                html += '</tr>'                
        return html
    def get_params_rows(self):
        html = ""
        _parm =  '<tr><td width="30" class="param">%s</td>\n'
        _parm_desc1 = '<td width="91%" class="param_def">'
        _parm_desc2 = '%s</td>\n</tr>\n'
        _example = '<tr><td width="30" class="label">Example</td><td class="inner_color"width="91%">'
        _example2 = '<span class="example">Example:%s</span></td>\n</tr>\n'
        for p  in self.params:
            html += _parm % p['name'] 
            html += _parm_desc1
            html += _parm_desc2 % p['desc']
            if p['example'] is not None:
                html += _example
                html += _example2 % p['example']
        return html
    def get_return(self):
        html = ""
        html += '<tr><td class="label" width="30">Return</td>\n'
        html += '<td class="return">%s</td></tr>' % self.rturn
        return html
    def get_name(self):
        return self.name
    def get_desc(self):
        return self.desc
    def generate_doc(self):
        f =  open(self.template_file)
        lines = ""
        for l in f.xreadlines():
            lines += l
        for k,v in self.patterns.items():
            lines = re.sub(k,apply(v),lines)
        return lines   

class Method(Function):
    def __init__(self,name):
        Function.__init__(self,name)        
        self.template_file = "method_template.html"
        self.patterns['\$\$METHOD\$\$'] = self.get_name
        self.patterns['\$\$DESC\$\$'] = self.get_desc
        self.patterns['\$\$PARAMS\$\$'] = self.get_params_rows
        self.patterns['\$\$PARAMS_LIST\$\$'] = self.get_params_list
        self.patterns['\$\$NOTES\$\$'] = self.get_notes
        self.patterns['\$\$RETURN\$\$'] = self.get_return

class FunctionDoc:
    def __init__(self,lines,index):
        self.generator_name = "Function"
        self.types = {"param":self._get_param,"return":self._get_return}
        self.types['note'] = self._get_note
        self.index = index
        self.lines = lines        
    def generate(self,outfile): 
        _eval = '%s("%s")' % (self.generator_name,self._get_name())
        self.generator = eval(_eval)
        self.generator.set_desc(self._get_desc())
        l = self.lines[self.index]
        while l[0:2] == "//":
            matched = 0 
            for k,v in self.types.items():
                if re.match("^// @%s" % k,l):
                    matched = 1
                    apply(v) 
                    if self.index <= len(self.lines)-1 :
                        l = self.lines[self.index]
                    else:
                        l = "  "
                        matched =1
                    break
            if matched == 0:
                self.index += 1
        line_break = "**********************************"    
        outfile.write('START' +  line_break)
        outfile.write('\n')        
        outfile.write(self.generator.generate_doc())
        outfile.write('END' + line_break) 
        outfile.write('\n')  
        return self.index
    def _get_note(self):
        l = self.lines[self.index]
        self.index += 1
        n_array = l.split(" ")
        n = string.strip(string.join(n_array[2:]))
        self.generator.add_note(n)
    def _get_return(self):
        l = self.lines[self.index]
        self.index += 1
        r_array = l.split(" ")
        r = string.strip(string.join(r_array[2:]))
        self.generator.set_return(r)        
    def _get_param(self):
        l = self.lines[self.index]
        self.index += 1
        p = "^// @param"
        e = "^// @example"
        while re.match(p,l):
            param = l.split(" ")
            p = string.strip(param[2])
            example = None
            desc = string.join(param[3:]) 
            l = self.lines[self.index]            
            if re.match(e,l):           
                example = self._get_example()
            self.generator.add_param(p,desc,example)            
        return
    def _get_example(self):
        example_array = self.lines[self.index].split(" ")
        self.index += 1
        example = string.join(example_array[2:])        
        return string.strip(example)    
    def _get_name(self):
        name = self.lines[self.index].split(' ')[2]
        self.index += 1             
        return string.strip(name)
    def _get_desc(self):
        l = self.lines[self.index][len("// "):]
        desc = l
        self.index += 1
        return string.strip(desc)
    
class MethodDoc(FunctionDoc):
    def __init__(self,lines,index):
        FunctionDoc.__init__(self,lines,index)
        self.generator_name = "Method"
            
        
class Documentation:
    def __init__(self,lines,starting_index):
        self.lines = lines
        self.index = starting_index + 1
        self.types = {"MethodDoc":"@method"}
        self.types['FunctionDoc'] = '@function'
       
    def generate(self,outfile):
        for k,v in self.types.items():
            p = "^// %s" % v
            if re.match(p,self.lines[self.index]):            
                obj = eval(k +"(self.lines,self.index)")
                self.index = obj.generate(outfile)
        return self.index

def msglog(msg):
    debug = 1
    if debug:
        print msg
        
if __name__ == "__main__":
    filename = "js/sdk.js"
    outfile_name = "doc_output.html"
    outfile = None
    f = None
    try:
        try:
            msglog('Opening FILE:"%s" as output file' % outfile_name)
            outfile = open(outfile_name,"w")
            f = open(filename,"r")
            lines = f.readlines()
            index = 0
            while index <= len(lines)-1:
                l = lines[index]
                if l[0:4] == "//@@":
                    d = Documentation(lines,index)
                    index = d.generate(outfile)                
                else:
                    index += 1                
           
        except IOError,e:
            print "ERROR:%s" % e
    finally:
        if f != None:
            f.close()
        if outfile != None:
            outfile.close()

"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import time
from mpx.lib import msglog
from types import *
from mpx.lib.sgml_formatter import SGMLFormatter
import string
import re
##
# Formatter for entrmsglog entries.
#
class HTMLFormatter(SGMLFormatter):
    def __init__(self, entries):
        self.children = entries
        SGMLFormatter.__init__(self)
        self.row_1_width = '30'
        self.row_2_width = '10%'
        self.row_3_width = '10%'
        self.row_4_width = '65%'
        
    ##
    # Output html representation of msglog.
    #
    # @return html
    def output(self, type = 'all',application = 'all', sort_order='descending',records='25'):
        self._header()
        self._table_values(type,application,sort_order,records)
        children = self._flatten_children()
        self.open_tag('tr')
        self.open_tag('td',width=1,Class='header_row')
        self.add_text('Seq')
        self.close_tag('td')
        self.open_tag('td',width=self.row_1_width,Class='header_row')
        self.add_text('Timestamp')
        self.close_tag('td')
        self.open_tag('td',width=self.row_2_width,Class='header_row')
        self.add_text('Application')
        self.close_tag('td')
        self.open_tag('td',width=self.row_3_width,Class='header_row')
        self.add_text('Type')
        self.close_tag('td')
        self.open_tag('td',width=self.row_4_width,Class='header_row')
        self.add_text('Message')
        self.close_tag('td')
        self.close_tag('tr')         
        even_row = 0
        
        for child in children:
            if type == 'all' and application == 'all':
                self._wrap_child(child,even_row)
                if even_row:
                    even_row = 0
                else:
                    even_row = 1                        
            elif  type =='all' and application != 'all':
                if re.match(application, child.application):
                    self._wrap_child(child,even_row)
                    if even_row:
                        even_row = 0
                    else:
                        even_row = 1
            elif application == 'all' and type != 'all':
                if child.type == type:
                    self._wrap_child(child,even_row)
                    if even_row:
                        even_row = 0
                    else:
                        even_row = 1
            elif application != 'all' and type != 'all':
                if child.type == type and re.match(application,child.application):
                    self._wrap_child(child,even_row)
                    if even_row:
                        even_row = 0
                    else:
                        even_row = 1                  
        self._footer()
        return SGMLFormatter.output(self)

    def _table_values(self,type,application,sort_order,records):
        self.open_tag('input',type='hidden',id='type',value=type)
        self.close_tag('input')
        
        self.open_tag('input',type='hidden',id='application',value=application)
        self.close_tag('input')

        self.open_tag('input',type='hidden',id='sort_order',value=sort_order)
        self.close_tag('input')

        self.open_tag('input',type='hidden',id='records',value=records)  
        self.close_tag('input')
        
        
    def _flatten_children(self):
        flat = self.children[:]
        for parent in flat:
            index = flat.index(parent) + 1
            for child in parent.get_children():
                flat.insert(index, child)
                index += 1
        return flat

    def create_css_link(self):
        self.open_tag('link',rel='stylesheet', href='/stylesheets/main.css',type='text/css')
        self.close_tag('link')
        
        self.open_tag('link',rel='stylesheet', href='includes/msglog.css',type='text/css')
        self.close_tag('link')
    
    def create_no_cache_headers(self):
        pass
        #can not figure out how to add the keyword http-equiv
        #self.open_tag('meta',content='text/html; charset-iso-8859-1')
        #self.close_tag('meta')
        #self.open_tag('meta',http-equiv='Content-Type',content='text/html; charset-iso-8859-1')
        #self.close_tag('meta')
        #self.open_tag('meta',http-equiv='Cache-Control',content='no-store')
        #self.close_tag('meta')
        #self.open_tag('meta',http-equiv='Pragma',content='no-cache')
        #self.close_tag('meta')
        #self.open_tag('meta',http-equiv='expires',content='0')
        #self.close_tag('meta')

    def _header(self):
        self.open_tag('html')
        self.open_tag('head')
        self.create_css_link()
        self.create_no_cache_headers()
        self.close_tag('head')
        self.open_tag('body',Class="back_ground")
        self.open_tag('table',width='100%',border='0', id="msg_table",cellpadding="4",
                      cellspacing="0")
        self.open_tag('tbody')

    def _footer(self):
        self.close_tag('tbody')
        self.close_tag('table')
        self.single_tag('br')
        self.close_tag('body')
        self.close_tag('html')

   
    def _wrap_child(self, child,even_row):
        cls_type = ''
        row_class = ''
        if even_row:
            row_class = 'even_row'
        else:
            row_class = 'odd_row'
        if child.type == ERR:
            cls_type = 'error_text'
        elif child.type == EXC:
            cls_type = 'exception_text'
        elif child.type == TB:
            cls_type = 'traceback_text'
        elif child.type == INFO:
            cls_type = 'information_text'
        elif child.type == FATAL:
            cls_type = 'fatal_text'
        elif child.type == WARN:
            cls_type = 'warning_text'
        elif child.type == DB:
            cls_type = 'debug_text'
        else:
            cls_type = 'normal_text'    
        
        self.open_tag('tr')
        self.open_tag('td',width=10,Class=row_class)
        self.open_tag('span',Class=cls_type,seq='%s' % child.seqnum)
        self.add_text('%s' % child.seqnum)
        self.close_tag('span')
        self.close_tag('td')
        self.open_tag('td',width=self.row_1_width,Class=row_class,nowrap='true')        
        timestamp = time.strftime('%H:%M:%S %m/%d/%y',
                                  time.localtime(child.timestamp))
        ts = '%.10f' % child.timestamp
        self.open_tag('span',Class=cls_type,raw_timestamp=ts)
        self.add_text(timestamp)
        self.close_tag('span')
        self.close_tag('td')
        self.open_tag('td', width=self.row_3_width,Class=row_class)
        self.open_tag('span',Class=cls_type)
        self.add_text(str(child.application))
        self.close_tag('span')
        self.close_tag('td')
        self.open_tag('td', width=self.row_3_width,Class=row_class)
        self.open_tag('span',Class=cls_type)
        self.add_text(child.type)
        self.close_tag('span')
        self.close_tag('td')        
        self.open_tag('td', width=self.row_4_width,Class=row_class)        
        self.open_tag('span',Class=cls_type)
        self.add_text(string.lstrip(string.replace(str(child.message),'\n','<br>'))) 
        self.close_tag('span')
        self.close_tag('td')        
        self.close_tag('tr')
        
        

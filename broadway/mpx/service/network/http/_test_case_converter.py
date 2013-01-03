"""
Copyright (C) 2003 2004 2006 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
from StringIO import StringIO
from mpx_test import DefaultTestFixture, main
from _psp_converter import PSPConverter
class TestCase(DefaultTestFixture):
    def test_look_for_tags_1(self):
        l = 'Logs: <select id="<%=log%>" name="log" onchange="get_log()">'
        converter = PSPConverter(None)
        t = converter._look_for_tags(l)
      
        if t[0] != '<%=log%>':
            msg = 'Not converted right\n'
            msg += 'Line:%s\n' % l
            msg += 'After:%s' % t
            self.fail(msg)
    def test_single_replace_tags(self):
        l = '<td width="50%"><%=node.get()%></td>'
        converter = PSPConverter(None)
        tags = converter._look_for_tags(l)
        nl = converter._replace_quotes(l)
        shouldbe = '"<td width=\"50%\">" + str(node.get()) + "</td>\\n"'
        nl = converter._replace_tags(l,tags)
        if nl != shouldbe:
            msg = 'Did not replace tags right\n'
            msg += 'Original line:%s\n' % l
            msg += 'new Line:%s\n' % nl
            msg += 'should be:%s\n' % shouldbe
            self.fail(msg)
    def test_multi_replace_tags(self):
        l = '<td width="50%"><%=node.get()%><%=time.get%></td>'
        converter = PSPConverter(None)
        tags = converter._look_for_tags(l)
        nl = converter._replace_quotes(l)
        shouldbe = '"<td width="50%">" + str(node.get()) + "" + str(time.get) + "</td>\\n"'
        nl = converter._replace_tags(l,tags)
        if nl != shouldbe:
            msg = 'Did not replace tags right\n'
            msg += 'Original line:%s\n' % l
            msg += 'new Line:%s\n' % nl
            msg += 'should be:%s\n' % shouldbe
            self.fail(msg)
    def test_multi_1_replace_tags(self):
        l = '<td width="50%"><%=node.get()%>Test<%=time.get%></td>'
        converter = PSPConverter(None)
        tags = converter._look_for_tags(l)
        nl = converter._replace_quotes(l)
        shouldbe = '"<td width="50%">" + str(node.get()) + "Test" + str(time.get) + "</td>\\n"'
        nl = converter._replace_tags(l,tags)
        if nl != shouldbe:
            msg = 'Did not replace tags right\n'
            msg += 'Original line:%s\n' % l
            msg += 'new Line:%s\n' % nl
            msg += 'should be:%s\n' % shouldbe
            self.fail(msg)

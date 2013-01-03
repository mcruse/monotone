"""
Copyright (C) 2001 2002 2003 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

from mpx.lib.sgml_formatter import SGMLFormatter

_html = (
    '<html>\n <title>title text\n </title>'
    '\n <body>body text<br>\n  ' + \
    '<img y="image_y" src="image_source" x="image_x"/>\n </body>\n</html>'
    )

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.formatter = SGMLFormatter()
        return
    def test_complete_output(self):
        self.formatter.open_tag('html')
        self.formatter.open_tag('title')
        self.formatter.add_text('title text')
        self.formatter.close_tag()
        self.formatter.open_tag('body')
        self.formatter.add_text('body text')
        self.formatter.single_tag('br')
        self.formatter.open_close_tag('img', src='image_source', x='image_x', y='image_y')
        self.formatter.close_tag('body')
        output = self.formatter.output_complete()
        self.failUnless(output == _html,
                        'output = %r\n\nhtml = %r' % (output, _html))
    def test_partial_output(self):
        self.formatter.open_tag('html')
        self.formatter.open_tag('title')
        self.formatter.add_text('title text')
        self.formatter.close_tag()
        output = self.formatter.output()
        self.failUnless(output == _html[0:35], 'output = %r\n\nhtml = %r' % (output, _html[0:35]))
        self.formatter.open_tag('body')
        output = self.formatter.output()
        self.failUnless(output == _html[35:43], 'output = %r\n\nhtml = %r' % (output, _html[35:43]))
        self.formatter.add_text('body text')
        self.formatter.single_tag('br')
        self.formatter.open_close_tag('img', src='image_source', x='image_x', y='image_y')
        self.formatter.close_tag('body')
        self.formatter.close_tag()
        output = self.formatter.output()
        self.failUnless(output == _html[43:], 'output = %r\n\nhtml = %r' % (output, _html[43:]))

if __name__ == '__main__':
    main()

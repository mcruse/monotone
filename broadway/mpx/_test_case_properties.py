"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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

import os
from StringIO import StringIO

from mpx import Properties

file_text = """\
attribute1=attribute_value
attribute2=testtest=testtest
# This is a comment
#This is a comment
attribute3=value3
this is an error that should not kill system
attribute4="""

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        f = StringIO() # A file-like object.
        f.write(file_text)
        f.seek(0) # Rewind the file.
        self.file_object = f
        return
    def test_empty_value(self):
        p = Properties(self.file_object)
        v = p.attribute4
        assert v == '', "Empty attribute should be ''"
        return
    def test_environment_override(self):
        os.environ['BROADWAY_attribute1'] = 'override property'
        v = Properties(self.file_object).attribute1
        assert v == 'override property', 'Environment var override failed'
        return
    def test_get_property(self):
        v = Properties(self.file_object).attribute3
        assert v == 'value3', 'Error getting property'
        return
    def test_set_property(self):
        props = Properties(self.file_object)
        props.set('Attribute', 'Value')
        v = props.get('Attribute')
        assert v == 'Value', 'Attribute not created'
        return
    def test_set_property_2(self):
        props = Properties(self.file_object)
        props.set('NewAttribute', 'Value')
        v = props.NewAttribute
        assert v == 'Value', 'Attribute not created'
        return
    def test_default_properites(self):
        props = Properties(self.file_object)
        v = props.get('ROOT')
        assert v != None, 'ROOT is undefined'
        return
    def test_default_properites_2(self):
        props = Properties(self.file_object)
        v = props.ROOT
        assert v != None, 'ROOT is undefined'
        return
    def test_str(self):
        v = str(Properties(self.file_object))
        assert v != None, 'Error while dumping properites'
        return
    def test_repr(self):
        v = repr(Properties(self.file_object))
        assert v != None, 'Error while dumping properites'
        return

if __name__ == '__main__':
    main(TestCase)

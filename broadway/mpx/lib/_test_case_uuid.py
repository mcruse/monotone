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
from mpx_test import DefaultTestFixture, main

from string import split
from uuid import UUID

class TestCase(DefaultTestFixture):
    def test_new(self):
        u = UUID()
        return
    def test_str(self):
        u = UUID()
        text = str(u)
        # An ISO 11578 UUID is exactly 36 characters long.
        if len(text) != 36:
            raise ("A valid ISO 11578 UUID is exactly 36 characters long"
                   ", not %d characters." % (len(text),))
        # Ensure that there are exactly 5 '-' separated components.
        # 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
        components=split(text,'-')
        if len(components) != 5:
            raise ("A valid ISO 11578 UUID has 5 components, not %d." %
                   (len(components),))
        # Check the size of each component.
        valid_lengths = (8,4,4,4,12)
        for i in range(0,5):
            if len(components[i]) != valid_lengths[i]:
                raise (
                    "The %s element is %d characters long, but should be %d" %
                    (("1st","2nd","3rd","4th","5th","6th")[i],
                     len(components[i]),
                     valid_lengths[i]))
        # Check that each component of the UUID represents a valid hexidecimal
        # value.
        components=map(lambda x: long(x,16), components)
        return
    def test_long(self):
        u = UUID()
        long(u)
        return
    def test_cmp(self):
        u1 = UUID()
        u2 = UUID()
        if u1 == u2:
            raise ("Two newly instantiated UUID's where equal.  This is bad,"
                   " very bad.\n"
                   "  The UUID created were '%s' and '%s'." % (u1,u2))
        if u1 < u2:
            if long(u1) >= long(u2):
                raise "Native and long compare disagree."
        if u1 > u2:
            if long(u1) <= long(u2):
                raise "Native and long compare disagree."
        if u1 < u2:
            if str(u1) >= str(u2):
                raise "Native and string compare disagree."
        if u1 > u2:
            if str(u1) <= str(u2):
                raise "Native and string compare disagree."
        return
    def test_load(self):
        u1 = UUID()
        u2 = UUID(str(u1))
        if u1 != u2:
            raise "Load of %s resulted in masmatch of %s." % (u1, u2)
        return
    def test_hash(self):
        u1 = UUID()
        u2 = UUID()
        if u1 == u2:
            raise ("Two newly instantiated UUID's where equal.  This is bad,"
                   " very bad.\n"
                   "  The UUID created were '%s' and '%s'." % (u1,u2))
        dictionary = {}
        dictionary[u1] = "u1"
        dictionary[str(u2)] = "u2"
        if not dictionary.has_key(u1):
            raise "Failed dictionary.has_key(u1)."
        if not dictionary.has_key(u2):
            raise "Failed dictionary.has_key(u2)."
        if not dictionary.has_key(str(u1)):
            raise "Failed dictionary.has_key(str(u1))."
        if not dictionary.has_key(str(u2)):
            raise "Failed dictionary.has_key(str(u2))."
        if not dictionary[u1] == 'u1':
            raise "Failed dictionary[u1] == 'u1'."
        if not dictionary[u2] == 'u2':
            raise "Failed dictionary[u2] == 'u2'."
        if not dictionary[str(u1)] == 'u1':
            raise "Failed dictionary[str(u1)] == 'u1'."
        if not dictionary[str(u2)] == 'u2':
            raise "Failed dictionary[str(u2)] == 'u2'."

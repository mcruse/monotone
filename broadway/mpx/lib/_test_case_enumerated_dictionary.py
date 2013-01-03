"""
Copyright (C) 2002 2005 2010 2011 Cisco Systems

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
##
# Test cases to exercise the BACnet modules.
#
# @note The ethernet specific tests are only run if the process is the root user.
# @fixme Report exceptions correctly from C.  (Raise MpxException objects).
# @fixme Phase out this test.  Replace it with APDU tests that include sending
#        and receiving a packet on "lo" and validataing they are the same.

from mpx_test import DefaultTestFixture, main

from mpx.lib import EnumeratedValue, EnumeratedDictionary

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
    def test_1(self):
        try:
            ed = EnumeratedDictionary()
        except:
            raise 'Failed to create empty dictionary'
        try:
            one = EnumeratedValue(1, 'one')
            two = EnumeratedValue(2, 'two')
            ed[1] = one
            ed['two'] = two
        except:
            raise 'Basic assignment failed'
        try:
            ed[3] = one
        except:
            pass
        else:
            raise 'Failed to detect mismatch between int key and value'
        try:
            ed['three'] = one
        except:
            pass
        else:
            raise 'Failed to detect mismatch between str key and value'
        try:
            s = str(ed)
        except:
            raise 'Failed to produce str from self'
        #exp_str = "{1: EnumeratedValue(1,'one'), 2: EnumeratedValue(2,'two')}"
        exp_str = "{1: {'__base__': 'EnumeratedValue', 'num': 1, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'one'}, 2: {'__base__': 'EnumeratedValue', 'num': 2, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'two'}}"
        if s != exp_str:
            raise 'str conversion failed (%s vs %s)' % (s, exp_str)
        try:
            r = repr(ed)
        except:
            raise 'Failed to produce repr string'
        #exp_repr = "EnumeratedDictionary({1: EnumeratedValue(1,'one'), 2: EnumeratedValue(2,'two')})"
        exp_repr = "EnumeratedDictionary({1: {'__base__': 'EnumeratedValue', 'num': 1, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'one'}, 2: {'__base__': 'EnumeratedValue', 'num': 2, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'two'}})"
        if r != exp_repr:
            raise 'repr string comparison failed (%s vs %s)' % (r, exp_repr)
        if ed[1] != one:
            raise 'Failed to get correct item for int key'
        if ed['two'] != two:
            raise 'Failed to get correct item for str key'
        try:
            ed['three']
        except:
            pass
        else:
            raise 'Failed to raise key exception on bad key'
        if ed.items() != [(1, EnumeratedValue(1,'one')), (2, EnumeratedValue(2,'two'))]:
            raise 'Failed to produce items'
        try:
            ed[3]='three'
            ed['four']=4
        except:
            raise 'Failed set for simple int and str items'
        if ed[3] != EnumeratedValue(3,'three'):
            raise 'Implicit creation of EnumeratedValue failed'
        if ed['three'] != EnumeratedValue(3,'three'):
            raise 'str dict did not get implicit assignment'
        ed2 = EnumeratedDictionary(ed)
        try:
            if ed == ed2:
                pass
            else:
                raise 'Equality test failed'
        except:
            raise 'Equality test crashed'
        ed2 = EnumeratedDictionary(ed)
        try:
            ed3 = EnumeratedDictionary(ed2)
        except:
            raise 'Failed to instanciate from another EnumeratedDictionary'
        if ed != ed3:
            raise 'Non-equality test failed'
        try:
            del ed2[1]
        except:
            raise 'del failed'
        if ed2.get(1) != None:
            raise 'Failed to del an item'
        if ed2.get('one') != None:
            raise 'Failed to del an item from str_dict'
        try:
            del ed2['two']
        except:
            raise 'del failed'
        if ed2.get(2) != None:
            raise 'Failed to del an item'
        if ed2.get('two') != None:
            raise 'Failed to del an item from str_dict'
        s = str(ed)
        #exp_str = "{1: EnumeratedValue(1,'one'), 2: EnumeratedValue(2,'two'), 3: EnumeratedValue(3,'three'), 4: EnumeratedValue(4,'four')}"
        exp_str = "{1: {'__base__': 'EnumeratedValue', 'num': 1, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'one'}, 2: {'__base__': 'EnumeratedValue', 'num': 2, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'two'}, 3: {'__base__': 'EnumeratedValue', 'num': 3, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'three'}, 4: {'__base__': 'EnumeratedValue', 'num': 4, '__class__': 'mpx.lib.EnumeratedValue', 'str': 'four'}}"
        if s != exp_str:
            raise 'Failed to survive all the stuff I tried to do to it.... (%s vs %s)' % (s, exp_str)
 
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

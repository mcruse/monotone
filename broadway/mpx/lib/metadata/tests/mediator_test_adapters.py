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
# Refactor 2/11/2007
from mpx.componentry import implements
from mpx.componentry import Interface
from mpx.lib.metadata.interfaces import IMetaDataProvider
from mpx.lib.metadata.adapters import MetaDataProvider

class C(object):
    implements(Interface)
    def __init__(self, name='test', value='test value',
                 nstest='Namespace conflict test'):
        self.name = name
        self.value = value
        self.__predicate = nstest

objects = []
for i in range(0, 100):
    objects.append(C('Test %s' % i, 'Value %s' % i, 'Conflict Test %s' % i))

first = objects[0]
meta1 = IMetaDataProvider(first)

assert meta1.context is first, "Incorrect context"
items = meta1.get_items()
meta_dict = meta1.get_meta_dictionary()
predicates = meta1.get_predicates()
triples = meta1.get_triples()
values = meta1.get_values()
assert type(items) is list, 'Incorrect datatype'
assert type(meta_dict) is dict, 'Incorrect datatype'
assert type(predicates) is list, 'Incorrect datatype'
assert type(triples) is list, 'Incorrect datatype'
assert type(values) is list, 'Incorrect datatype'

assert not (items or meta_dict or predicates or triples or values), 'Non-empty'

meta1.add_meta('name', 'shane')
items = meta1.get_items()
meta_dict = meta1.get_meta_dictionary()
predicates = meta1.get_predicates()
triples = meta1.get_triples()
values = meta1.get_values()

assert (items == [('name', 'shane')] and
        meta_dict['name'] == 'shane' and
        predicates == ['name'] and
        triples == [(meta1.context, 'name', 'shane')] and
        values == ['shane']), 'Incorrect meta-data'

meta1.add_meta('shane', 'name')
items = meta1.get_items()
meta_dict = meta1.get_meta_dictionary()
predicates = meta1.get_predicates()
triples = meta1.get_triples()
values = meta1.get_values()

assert len(items)==2 and items[0]==(items[1][1],items[1][0]), 'Bad data'
assert meta_dict['name']=='shane' and meta_dict['shane']=='name', 'Bad data'
assert 'name' in predicates and 'shane' in predicates, 'Bad data'
assert (len(triples) == 2 and
        (meta1.context,'name','shane') in triples and
        (meta1.context,'shane','name') in triples), 'Bad data'
assert 'name' in values and 'shane' in values, 'Bad data'

meta2 = IMetaDataProvider(first)
assert items == meta2.get_items(), 'Mismatched data'
assert items is not meta2.get_items(), 'Should not be same object'
assert meta_dict == meta2.get_meta_dictionary(), 'Mismatched data'
assert predicates == meta2.get_predicates(), 'Mismatched data'
assert triples == meta2.get_triples(), 'Mismatched data'
assert values == meta2.get_values(), 'Mismatched data'

del(meta1)
del(meta2)

meta2 = IMetaDataProvider(first)
assert items == meta2.get_items(), 'Mismatched data'
assert items is not meta2.get_items(), 'Should not be same object'
assert meta_dict == meta2.get_meta_dictionary(), 'Mismatched data'
assert predicates == meta2.get_predicates(), 'Mismatched data'
assert triples == meta2.get_triples(), 'Mismatched data'
assert values == meta2.get_values(), 'Mismatched data'

meta3 = IMetaDataProvider(first)
assert meta2 is not meta3, 'Should not be same object'
meta3.add_meta('Test', 'test')
assert meta2.get_meta('Test') == 'test', 'Changes not reflected.'

try: meta3['no such predicate']
except KeyError: pass
else: assert True, 'Should have raised exception'

try: predicate = meta3.get_meta('no such predicate', 'predicate')
except KeyError: assert True, 'Should have returned default'
else: assert predicate == 'predicate', 'Wrong default returned'

try: meta3['no such predicate']
except KeyError: pass
else: assert True, 'Still should have raised exception'

try: predicate = meta3.setdefault_meta('no such predicate', 'predicate')
except KeyError: assert True, 'Should have returned default'
else: assert predicate == 'predicate', 'Wrong default returned'

try: predicate = meta3['no such predicate']
except KeyError: assert True, 'Should have returned setdefault'
else: assert predicate == 'predicate', 'Incorrect value'

assert MetaDataProvider.get_subject_meta(first, 'absent') is None, (
    'Static method should have returned None')

assert MetaDataProvider.get_subject_meta(first, 'name') == 'shane', (
    'Should have found meta data')

state = MetaDataProvider.get_subject_meta_state(first)
assert (state.has_key('__meta') and
        state['__meta'] == first.__dict__['__meta']), (
            'Should have returned dict.')





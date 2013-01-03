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
from mpx.componentry.tests import verify_class
from mpx.componentry.interfaces import IOrderedCollection
from mpx.componentry.interfaces import INamedCollection
from mpx.componentry.interfaces import IFieldStorage
from mpx.componentry.interfaces import IFieldStorageCollection

from mpx.componentry.bases import OrderedCollection
from mpx.componentry.bases import FieldStorage
from mpx.componentry.bases import FieldStorageCollection

# Interface verification: Disabled because verify_class no work on Mediator
#verify_class(IOrderedCollection, OrderedCollection)
#verify_class(IFieldStorage, FieldStorage)
#verify_class(IFieldStorageCollection, FieldStorageCollection)


# OrderedCollection tests
class T1(object):
    name = 'T1: test1'
    def __init__(self,value1,value2):
        self.value1 = value1
        self.value2 = value2
    def show(self):
        showing = '%s(%s, %s): %s, %s' % (
            self.__class__.__name__, self.value1,
            self.value2, self.value1, self.value2)
        print showing
        return showing
    def value(self,which='1'):
        if which == '1': return self.value1
        if which == '2': return self.value2
        raise AttributeError(which)

objects = []
for i in range(0,100):
    objects.append(T1(i,str(i)))

oc = OrderedCollection(objects)

values1 = []
values2 = []
names = []
shows = []
for i in range(0,100):
    values1.append(i)
    values2.append(str(i))
    names.append(T1.name)
    shows.append(objects[i].show())

assert oc.invoke('value') == values1, "invoke('value') returned wrong data"
assert oc.invoke('value','2') == values2, "invoke('value', '2') returned wrong data"
assert oc.getattr('name') == names, "getattr('name') returned wrong data"
assert oc.getattr('value1') == values1, "getattr('value1') returned wrong data"
assert oc.getattr('value2') == values2, "getattr('value2') returned wrong data"
assert oc.invoke('show') == shows, "invoke('shows') returned wrong data"

# FieldStorage tests
class Fields(FieldStorage):
    fields = ['f1','f2','f3','f4','f5','f6','f7','f8','f9','f10']
    def __init__(self,values = [1,2,3,4,5,6,7,8,9,10], append_name = None, append_value = None):
        self.values = values[:]
        if append_name is not None:
            self.fields = self.fields[:] + [append_name]
            self.values.append(append_value)
        super(Fields, self).__init__()
    def _populate(self,dictionary):
        keys = dictionary.keys()
        for key in keys:
            if key not in self.fields:
                raise Exception('Something wrong with dict',dictionary)
        for field in self.fields:
            if field not in keys:
                raise Exception('Something wrong with dict', dictionary)
        for i in range(0,len(self.fields)):
            dictionary[self.fields[i]] = self.values[i]
        return
    def get_field_value(self,name):
        return self.values[self.fields.index(name)]

f1 = Fields()
f1.get_field_names()
f1.get_field_dictionary()
f1.get_field_value('f3')
f1.get_field_names()
f1.get_field_values(['f2','f3','f4','f5','f6'])

assert f1.fields is Fields.fields, 'Using different fields for no reason'
assert f1.get_field_names() == tuple(Fields.fields), 'Wrong fields'
assert f1.get_field_dictionary() == dict(zip(f1.fields,f1.values)), 'f1 has wrong dict'
assert f1.get_field_value('f3') == 3, 'f1 returned wrong value for f3'
assert f1.get_field_values(['f2','f3','f4','f6']) == [2,3,4,6], 'f1 returned wrong field values'

f2 = Fields([1,2,3,4,5,6,7,8,9,10],'f11')
assert f2.fields is not Fields.fields, 'Not using different fields but should be'
assert f2.get_field_names() == ('f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11'), 'Wrong fields'
assert f2.get_field_dictionary() == dict(zip(f2.fields,f2.values)), 'f2 has wrong dict'
assert f2.get_field_value('f3') == 3, 'f2 returned wrong value for f3'
assert f2.get_field_value('f11') is None, 'f2 returned wrong value for f11'
assert f2.get_field_values(['f2','f3','f4','f6','f11']) == [2,3,4,6,None], 'f2 returned wrong field values'

# Test FieldStorageCollection
objects = []
for i in range(0,100):
    objects.append(Fields([i * x for x in [1,2,3,4,5,6,7,8,9,10]],'multiplier',i))

collection = FieldStorageCollection(objects)
assert collection.get_field_names() == objects[0].get_field_names(), (
    'Collection field names do not match first field object')

assert collection.return_type() is OrderedCollection, (
    'Collection return_type() not base class.')

objects = []
for i in range(0,100):
    objects.append(Fields([x for x in [1,2,3,4,5,6,7,8,9,10]],'multiplier',i))

collection = FieldStorageCollection(objects)

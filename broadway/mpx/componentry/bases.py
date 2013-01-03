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
"""
    Module defines base implementation of many useful components.

    Base implementations serve three purposes:
        - they provide example implementations to serve
            as guides to others implementing similar objects;
        - they provide convenient base classes for objects
            providing specialized variations of these components;
        - they attempt to reduce implementation effort by defining
            fully functional implementations wherever possible, and by
            providing partial implementations that call on helper
            functions to provide specific details wherever possible.

    The following classes are defined:
        - OrderedCollection, a fully functional collection object
            which implements IOrderedCollection interface.
        - FieldStorage, which defines most functionality required
            by implementors of IFieldStorage.
        - FieldStorageCollection, a fully functional collection
            object implementing IFieldCollection.
"""
from mpx.componentry import implements, adapts
from mpx.componentry.interfaces import IOrderedCollection
from mpx.componentry.interfaces import IFieldStorage
from mpx.componentry.interfaces import IFieldStorageCollection
from _helpers import DelayedFactory as _DelayedFactory
from backports import Dictionary

##
# NOTE: 'OrderedCollection' may also be accessed using
#   'OC' shorcut.
class OrderedCollection(list):
    """
        See interfaces.OrderedCollection.

        NOTE: Shortcut 'OC' to this object is
        provided for convenience.
    """
    implements(IOrderedCollection)

    def from_list(list_obj):
        if not isinstance(list_obj, list) and not isinstance(list_obj, tuple):
            raise TypeError('Must be list or tuple instance.')
        return OrderedCollection(list_obj)
    from_list = staticmethod(from_list)
    from_tuple = from_list

    def from_callable(obj, *args, **kw):
        if not callable(obj):
            raise TypeError("Object 'obj' must be callable.")
        result = obj(*args, **kw)
        return OrderedCollection.from_list(result)
    from_callable = staticmethod(from_callable)

    def from_invoke(obj, attr, *args, **kw):
        return OrderedCollection.from_callable(getattr(obj, attr), *args, **kw)
    from_invoke = staticmethod(from_invoke)

    def getattr(self, name, default=AttributeError):
        error = default(name)
        return self.return_type()([getattr(obj,name,error) for obj in self])

    def invoke(self,name,*args,**keywords):
        methods = self.getattr(
            name, _DelayedFactory(AttributeError,1,2))
        return self.return_type()([method(*args, **keywords) for method in methods])

    def return_type(self):
        """
            Makes default type of returned collections
            type(self).  This means returned collections
            will be instances of self.__class__, which is
            an instance of current subclass.

            To make collections of different type be returned,
            overrride this method and return class object
            of desired return type.
        """
        return type(self)

"""
    Shortcut 'OC' provided for 'OrderedCollection'
"""
OC = OrderedCollection

class FieldStorage(object):
    """
        A partially complete implementation of an IFieldStorage class.

        Complete implementations of:
            - 'get_field_names', and
            - 'get_field_values'
        are provided.

        Partial implementation of:
            - 'get_field_dictionary'
        is provided.

        The partial implemenation of 'get_field_dicionary' calls
        upon undefined helper function '_populate', passing
        dictionary in which values must be inserted for the
        defined keys only.

        Subclasses must define:
            - '_populate', which takes dictionary with keys
                of field names and must replace values with
                value of appropriate fields.
            - 'get_field_value', which takes a name of a
                field and returns its value.

        With the above two defitions, subclasses will be
        complete implementations of IFiedStorage classes.
    """
    implements(IFieldStorage)

    fields = []
    field_dict = Dictionary()

    def __init__(self):
        self.field_dict = Dictionary.fromkeys(self.fields)

    def get_field_names(self):
        return tuple(self.fields)

    def get_field_dictionary(self):
        dictionary = self.field_dict.copy()
        self._populate(dictionary)
        return dictionary

    def get_field_value(self, name):
        raise Exception('_populate(dict) not implemented')

    def set_field_value(self, name, value):
        raise Exception('set_field_value(name, value) not implemented')

    def get_field_values(self, names):
        values = []
        for name in names:
            values.append(self.get_field_value(name))
        return values

    def _populate(self,dict):
        """
            Helper function hook for subclasses.  Implementation
            must replace None values with actual field
            values for each named field, where names
            are already provided as keys within dictionary.
        """
        raise Exception('_populate(dict) not implemented')

    # Functions allowing these objects to be treated
    #   as dictionary helmits.
    def keys(self):
        return self.get_field_names()

    def values(self):
        return self.get_field_values(self.get_field_names())

    def items(self):
        return self.get_field_dictionary().items()

    def get(self,name,default=None):
        return self.get_field_dictionary().get(name,default)

    def __getitem__(self,name):
        return self.get_field_value(name)

    def __setitem__(self,name):
        self.set_field_value(name)

class FieldStorageCollection(OrderedCollection):
    implements(IFieldStorageCollection)

    def __init__(self,objects,*args,**keywords):
        self.fields = None
        for obj in objects:
            assert IFieldStorage.providedBy(obj), (
                'Object %s does not implement IFieldStorage.' % obj)
            names = obj.get_field_names()
            if self.fields is not None:
                assert names == self.fields, (
                    'Object %s does not have the same fields.' % obj)
            else: self.fields = names
        super(FieldStorageCollection, self).__init__(objects, *args, **keywords)

    def invoke(self, name, *args, **keywords):
        if name == 'get_field_names':
            results = self.fields[:]
        else:
            invoke = super(FieldStorageCollection, self).invoke
            if name == 'get_field_dictionary':
                # values = list of lists of values, where each
                #   list is all items from one object. [[1,2,3],[1,2,3],...]
                values = invoke('get_field_values', self.fields)
                # values = list of tuples of values, where each
                #   tuple is a particular filed from each object.
                #   [(1,1,...), (2,2,...), (3,3,...), ...]
                values = zip(*values)
                # values = list of tuples, where each
                #   tuple is a label and a tuple of values
                #   with corresponding values.
                #   [('l1',(1,1,...), ('l2',(2,2,...)), ...]
                values = zip(self.fields, values)
                results = Dictionary(values)
            else: results = invoke(name, *args, **keywords)
        return results

    def get_field_names(self):
        return self.invoke('get_field_names')

    def get_field_dictionary(self):
        return self.invoke('get_field_dictionary')

    def get_field_values(self,names):
        return self.invoke('get_field_values',names)

    def return_type(self):
        # If returned collections were instances of
        #   this.__class__, rather than of OrderedCollection,
        #   all attributes would have to provide
        #   IFieldStorage as well.
        return OrderedCollection




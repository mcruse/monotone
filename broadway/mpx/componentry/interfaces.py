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
from mpx.componentry import Interface, Attribute

class IPickles(Interface):
    """
        Marker-interface so objects wishing to be propogated
        may define an adapter that pickles them.

        By a default adapter will be defined that accepts
        any Interface and simply pickles, as its only
        property, the object being adapted.  More specific
        adapters may be defined and will be used instead.

        It is important to note that the act of pickling and
        unpickling via an IPickles adapter should itself be a
        passive action.  In particular, if the object(s) being
        maninpulated are events, or other objects representing
        actions that may, in and of themselves, take some action
        as a result of being unpickled.  Instead, an IPickles adapter
        should delay the active aspects of its job until the __call__
        method is called; this allows better control over the
        sytems' behaviour when receiving, for example, remote events.
    """
    def __init__(context):
        """
            As with all adapters, it is initialized by passing a
            reference to the object being adapted.
        """
    def __call__():
        """
            Returns the instance being adapted.
        """

class IOrderedCollection(Interface):
    """
        Represent collection of objects, allowing
        operations to be invoke on all objects in
        collection.

        Object is instanciated with list of objects
        for collection.
    """
    def from_callable(obj, *args, **keywords):
        """
            * StaticMethod *
            Invoke callable object 'obj', passing *args
            and **kw as arguments; instanciate OrderedCollection
            with list result and return.

            NOTE:
                - 'obj' must be a callable object, and
                - 'obj(*args, **kw)' must return list instance.
        """
    def from_invoke(obj, attr, *args, **keywords):
        """
            * StaticMethod *
            Get attribute 'attr' from object 'obj' and
            invoke, passing *args and **kw as arguments;
            instanciate OrderedCollection with list result and return.

            NOTE:
                - 'getattr(obj, name)' must return a callable object, and
                - 'getattr(obj, name)(*args, **kw)' must return list instance.
        """
    def from_list(list_obj):
        """
            * StaticMethod *
            Return OrderedCollection instance of
            list 'list_obj'
        """
    def from_tuple(tuple_obj):
        """
            * StaticMethod *
            Return OrderedCollection instance of
            tuple 'tuple_obj'
        """
    def invoke(method, *args, **keywords):
        """
            Call method 'method' on all objects in collection
            and return an ordered list of results.

            returns IOrderedList of results.
        """
    def getattr(name, default=AttributeError):
        """
            Return IOrderedCollection instance containing
            all attributues named 'name.'  Use instance of
            'default' to fill locations of objects not implementing
            attribute 'name.'  By default this will be an AttributeError
            object instanciated with name 'name.'
        """

class INamedCollection(Interface):
    """
        Represent collection of objects, allowing
        operations to be invoke on all objects in
        collection.

        Object is instanciated with list of objects
        for collection.
    """

class IFieldStorage(Interface):
    """
        Object that can easily be displayed or
        represented as a list of name-value pairs.

        Object provides functions to simplify determining
        appropriate fields, retrieving values by field name,
        etc.
    """
    def get_field_names():
        """
            Get list of field-names that should be
            displayed about this object in order represent
            object as list of name-value pairs.

            returns list of fild names
        """
    def get_field_dictionary():
        """
            Get a dictionary of name-value pairs where names
            are same as names returned by get_field_names, and
            values are the corresponding values of those fields.
        """
    def get_field_value(name):
        """
            Return value of field named 'name'
        """
    def get_field_values(names):
        """
            Return ordered list of values
            corresponding to fields named in 'names'
        """
class IFieldStorageCollection(IOrderedCollection):
    """
        Collection of LIKE IFieldStorage objects.

        This interface is designed to make it simple
        to represent collections of similar FieldStorage
        objects using tables, lists of lists, etc.
    """
    def get_field_names():
        """
            See IFieldStorage.get_field_names()
        """
    def get_field_dictionary():
        """
            See IFieldStorage.get_field_dictionary()

            Values of ordered lists of values, rather
            that simply a value.
        """
    def get_field_values(name):
        """
            See IFieldStorage.get_field_values(names)

            Rather that returning one list of values,
            this method returns an ordered list of lists of values.
        """

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
from mpx.componentry import Interface
from mpx.componentry import Attribute

class IMetaDataProvider(Interface):
    def get_subject_meta(subject, predicate, default = None):
        """
            NOTE: Static
            Static method for quick lookup of meta data using
            the subject object as a parameter, rather than creating
            and working with an adapter for the subject.
        """

    def get_subject_meta_state(subject):
        """
            NOTE: Static
            Static method for getting dicationary that may be
            merged with an object's __dict__ dictionary to recreate
            meta-state for object.  This function should be called
            by __getstate__ method of any object using __getstate__
            for pickling in order to assure associated meta-data
            is preserved.

            Consider automatically adding wrapper to context
            if context defines __getstate__.  This wrapper function
            could then call the context's __getstate__ when executed,
            and add to the returned state the additional information
            associated with meta-data, before returning the value.
        """

    def __getitem__(predicate):
        """
            Return value associated with self by predicate 'predicate'.

            Raise KeyError if no meta-data defined by
            predicate 'predicate' exists.
        """
    def get_meta(predicate, default = None):
        """
            Return value associated with self by predicate 'predicate'.

            Return 'default' if no such predicate exists.
        """
    def __setitem__(predicate, value):
        """
            Attach new meta-data related to self by
            predicate 'predicate' and having value 'value.'

            Overwrite previous value if predicate already exists.
        """
    def add_meta(predicate, value):
        """
            Attach new meta-data related to self by
            predicate 'predicate' and having value 'value.'

            Raise TypeError if meta-data already defined.
        """
    def update_meta(predicate, value):
        """
            Update meta-data with predicate and value,
            ovewriting any existing value.
        """
    def setdefault_meta(predicate, default):
        """
            If predicate 'predicate' does not exist, add
            it with value 'default'.

            Return item associated with predicate 'predicate,'
            regardless of whether or not 'default' was used.
        """
    def get_predicates():
        """
            Return list of predicates associated
            with this object.
        """
    def get_values():
        """
            Return list of values associated with
            this object by ANY predicate.
        """
    def get_items():
        """
            Return list of two-tuples made up of
            predicate, value pairs.
        """
    def get_triples():
        """
            Return list of three-tuples made up of
            subject, predicate, value sets; where 'subject'
            is always a reference to this object.
        """
    def get_meta_dictionary():
        """
            Return dicationary with keys of
            this object's predicates, and values
            of the corresponding values.
        """

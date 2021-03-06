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
    This package pulls together 3rd party classes,
    methods, and services required to implement component
    architecture.  Namely:
        - the 'Interface' super class, used to define all
            interfaces;
        - the 'Attribute' class, used to define attributes
            on interfaces.  Not completely necessary, but may
            provide nice meta-data and validation hooks for later
            purposes
        - the 'implements' function, used by classes to
            declare they implement a given interface;
        - the 'directly_provides' function, used by on
            objects to declare the provision of an interface
            post intantiation.  Most often used for marker
            interfaces only; where a 'marker' interface is an
            interface that has no content other than a doc-string.
        - the 'adapts' function, used by Adapter classes
            to declare they adapt the specified interface.
        - the 'register_adapter' function, which should be
            called for each defined Adapter class definition.
        - the 'get_adapter' function, which can be used to
            retrieve an initialized adapter according to needs.
        - the 'query_adapter' function, which is the same
            as 'get_adapter,' but returns None if not found.
        - the 'get_multi_adapter' function, 'get_adapter'
            for adapters that adapt multiple components.
        - the 'query_multi_adapter' function, 'query_adapter'
            for adapters that adapt multiple components.
        - the 'register_utilty' function, which allows
            simple registration of arbitrary components
            by Interface and name.
        - the 'get_utility' function, which allows
            retrieval of registered utilities by
            Interface and name.
        - the 'query_utility' function, which
            performs 'get_utility' but returns
            None if utilty not found.
        - and the 'ComponentLookupError' exception.



    Interfaces:
    All interfaces must subclass, directly or indirectly, the
    'Interface' class.  Interfaces should have names starting with
    capital letter 'I', to distinguish them from classes.

    Interface bodies define required functions of interface, including all
    parameters except 'self.'  Interface functions do not have
    any body, aside from doc string describing function.  For example:

        class ISomeInterface(Interface):
            def required_function(param1, param2):
                '''
                    Classes implementing 'ISomeInterface'
                    must define function 'required_function'
                    that will take (self, param1, param2) arguments.
                '''

    Define Interface methods that will be static or class methods in
    actual implementation in generally the same way it is done for
    normal methods.  Namely:

        If method 'smethod' will be implemented as a static
        function, and the static function takes 'arg1', 'arg2', and
        'arg3', define the interface function as this:

            def smethod(arg1, arg2, arg3)...

        This is exactly the same way one would define the smethod
        function if were not a staticmethod as well.

        If smethod were instead to be a class method, which receives
        a class reference in place of 'self' for its first argument
        when invoked, the definition still would be exactly the same.

        Interface checking is done at runtime and therefore operates
        under whatever binding effects Python has imposed.

        In summary, then:
            - regular method definitions must leave out
                argument 'self' in the interface definition,
            - classmethod method definitions must likewise
                leave out the class reference passed in as the
                first parameter when classmethods are invoked, and finally
            - staticmethods are declared with the exact number of arguments
                they will recieve when invoked at runtime, in spite of not
                inherently recieving an additional parameter when invoked.


    Implementing Interfaces:
    All classes implementing an interface must declare
    their implementation within the class definition.  For example:

        class ClassImplementingISomeInterface:
            implemnts(ISomeInterface)

            def required_function(self, param1, param2):
                ''' Regular function definition '''


    Adapters:
    Adapters are objects that implement an interface for an
    object implementing a different interface.  Adapters
    allow polymorphism without requiring unecessary
    and/or contrived multiple-inheretence.

    Adapters may subclass the provided 'Adapter' class,
    but doing so is not necessary.  Adapters must
    declare the interfaces they implement, as do any
    classes that implement interfaces.  In addition,
    Adapters must declare which Interface(s) they adapt.
    For example:

        class SomeAdapter(object):
            implements(ISomeInterface)
            adapts(ISomeOtherInterface)

            def __init__(self, context):
                '''
                    context is the traditional
                    name for the prameter/attribute
                    referencing the object being adapted.
                '''
                self.context = context

            def required(self, param1, param2):
                '''
                    Whatever must be done to operate on
                    adapted object according to ISomeInterface's
                    interface definition.
                '''

    Registering Adapters:
    To realize the power of this design, the component registry
    is required.  The component registry keeps track of interface
    implementations and adaptations, and allows runtime lookup
    of objects according to desired source object and desired
    interface.  Configure the component registry as follows:

        register_adapter(SomeAdapter)


    Runtime Adapter usage:
    Now the following operations can be performed:

        - ISomeInterface.implementedBy(SomeClass) returns boolean indication
            whether or not the specified class implements ISomeInterface.

        - ISomeInterface.providedBy(SomeClass()) returns boolean indication
            whether or not specified object implements ISomeInterface.

        - ISomeInterface(SomeClass()) returns provided instance if instance
            already provides ISomeInterface, otherwise returns instance of
            appropriate Adapter, configured with provided instance and
            providing the desired Interface.  TypeError exception raised
            if no appropriate adapter is found.
            - get_adapter(SomeClass(), ISomeInterface) performs same operation
                as Interface shortcut above.  However, ComponentLookupError
                is raised if no approrpriate adapter is found; rather than
                TypeError raised on Interface-based lookup.
            - query_adapter(SomeClass(), ISomeInterface) also performs the
                same operation, however None is returned if no appropriate
                adapter is found.  This is similar to dict.get.

    Additional Notes:
        - Interface inheritance follows similar rules as normal inheritance.

        - A class, ClassB, which impelements interface IB and subclasses class
            ClassA, which implements interface IA, has the following results:
                - ClassB 'implements' IB, and all IB base-interfaces.
                - ClassB 'implements' IA, and all IA base-interfaces.
                - Instances of ClassB are objects of 'type' ClassB.
                - Instances of ClassB are objects of 'type' ClassA.
                - Instances of ClassB 'provide' interface IB, and all IB base-interfaces.
                - Instances of ClassB 'provide' interface IA, and all IA base-interfaces.

        - Interface objects provide the following methods:
                - Interface.providedBy(object), returns boolean indication
                    of whether 'object' provides interface 'Interface.'
                - Interface.implementedBy(class), returns boolean indication
                    of whether or not class object 'class' implements
                    interface 'Interface.'

        - Interface(instance) is same as get_adapter(instance, Interface).

        - register_adapter takes: factory, adapts=None, provides=None, name=''
            - 'factory' is reference to Adapter class, e.g. SomeAdapter
            - 'adapts' is list of Interfaces Adapter adapts.
                - When 'adapts' is none, interfaces attached to factory
                    by factory definition when calling adapts(Interface) are used.
                - When 'adapts' is a list of Interfaces, adapter is called a
                    multi-adapter.  Multi-adapters must cannot be retreived using
                    'get_adapter' and 'query_adapter,' now 'get_multi_adapter' and
                    'query_multi_adapter' must be used.
            - 'provides' refers to the Interface implemented by the adapter.
                - If the Adapter implements more than one interface, this value
                    must be provided explicitly and may only be one of the
                    implemented interfaces.
            - 'name' allows a registration to be named, making it possible
                for the retreival to specify an Adapter by name.

        - register_adapter(SomeAdapter) is same as
            register_adapter(SomeAdapter, [ISomeOtherInterface], ISomeInterface) as long as
            SomeAdapter only implements ISomeInterface.  Middle param of None is also same.
            - If SomeAdapter implements more than one interface, short form of
                register_adapter(SomeAdapter) will fail.  Must call
                register_adapter(SomeAdapter, None, ISomeInterface), where
                ISomeInterface is one of the Interfaces implemented by SomeAdapter.

        - get_adapter takes: object, interface=Interface, name=u''
            - 'object' refers to instance that will be adapted.
            - 'interface' refers to Interface class that must be
                provided by the adapted object.
            - 'name' allows retreival of adapter by name if corresponding
                registration also used name.
            - returns instantiated Adapter object meeting requirements.
            - raises ComponentLookupError if not found.

        - query_adapter: see get_adapter
            - returns None instead of raising exception if not found.

        - query_multi_adapter and get_multi_adapter: see corresponding
            non-multi functions.
            - 'object' parameter is now list of objects that will be adapted.


    Utility functions:
    Functions 'register_utility,' 'get_utility,' and 'query_utility' have been
    convenience.  These functions operate as follows:

        - register_utility takes: component, provides=None, name=u''
            - 'component' is an object providing interface(s).
            - 'provides' is an optional argument for specifying
                the Interface to associate the registration with.
                - if 'component' provides more than one interface,
                    this argument must specify an Interface for
                    the registration.
            - 'name' is optional string argument providing a name
                for the registered utility.
                - if 'name' is not provided, it defaults to emtpty string.
                - if 'name' is provided, the lookups of utility must
                    specify exact name.

        - query_utility takes: interface, name=''
            - 'interface' refers to Interface utility was
                registered with.
            - 'name' may specify string name corresponding
                to name provided at registration.
            - returns utility registered with matching
                parameters, or None if no such utility exists.

        - get_utilty: see query_utility
            - raises ComponentLookupError if when 'get_utility'
                would return None.

    AdapterChain function:
    Method that creates "adapter chains" which, unfortunately,
    zope does not inherently do.  The usage is that you first
    create all your adapter classes normally.  Then, for any
    two non-direct adaptations you want to register, you call:

    NewClass = AdapterChain(superclass, Interface1, ...)
        - 'superclass' is the class you want to end up with.
            This is the class that implements the interface
            you want to work with.
        - 'Interface1, ...' is a list of interfaces starting
            with the interface implemented by the class you
            will be adapting, and ending with the interface
            implemented by the class you want to work with.

    Consider the following structure:
        class IA(Interface):
            '''Interface A'''

        class IB(Interface):
            '''Interface B'''

        class IC(Interface):
            '''Interface C'''

        class ID(Interface):
            '''Interface D'''

        class A(object):
            implements(IA)

        class B(object):
            implements(IB)
            adapts(IA)

        class C(object):
            implements(IC)
            adapts(IB)

        class D(object):
            implements(ID)
            adapts(IC)

    Given this structure, we should now have an adapter chain allowing
    the automatic adaption of any object A-D to any other object A-D, given
    the second object comes later in the sequence than the first.  For example:
        # given
        >>> a = A()
        # we should be able to say
        >>> d = ID(a)

    Although there is no direct adaptation from A to D, the system should
    have returned the following composite structure:

        ID(a) should return D( C( B(a) ) ), chaining adapters like so.

    Unfortunately this does not happen.  To mimic this behaviour, we
    have provided the helper function AdapterChain.  Used on this example:

        >>> DChain = AdapterChain(D, IA, IB, IC, ID)
        # Now one can do the following
        >>> a = A()
        >>> d = ID(a)
        # And get the expected result.
"""

from zope.interface import Interface, Attribute, implements
from zope.interface import directlyProvides as directly_provides

# adapts takes one or more listed interfaces,
#   called when defining adapter.
from zope.component import adapts
# register_adapter must be called for adapters to be registered for lookup
from zope.component import provideAdapter as register_adapter

# query_adapter takes object to be adapted and interface to be provided
#   raises exception if adapter is not located.
from zope.component import queryAdapter as query_adapter
# get_adapter is exactly like query_adapter, but returns None
#   if no adapter is found; optional third parameter may be provided as return.
#   NOTE: shortcut for 'get_adapter' functionality is to call interface(object).
from zope.component import getAdapter as get_adapter
from zope.component.interfaces import ComponentLookupError

# get_multi_adapter must be used when adapter adapts more than one interface.
#   Arguments are tuple of objects to be adapted, and interface to be provided.
from zope.component import queryMultiAdapter as query_multi_adapter
from zope.component import getMultiAdapter as get_multi_adapter

# Utility registration and retrieval classes.
from zope.component import provideUtility as register_utility
from zope.component import queryUtility as query_utility
from zope.component import getUtility as get_utility


# Adapter chaining helper-function.
#   May choose to make chaining automatic
#   at some point, for now chained adaptations
#   will remain explicit.
# *args is list of interfaces starting
#   with interface implemented by object being adapted.
def AdapterChain(superclass,*args):
    class Chain(superclass):
        interfaces = args
        implements(args[-1])
        adapts(args[0])

        def __new__(klass,context,*args,**keywords):
            chain = klass.interfaces[1:]
            for interface in chain:
                print interface.__name__ + '(%s())' % context.__class__.__name__
                context = interface(context)
            return context

    register_adapter(Chain, [args[0]], args[-1])
    return Chain



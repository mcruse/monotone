======================
Python Tips and Tricks
======================

:Authors: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: To provide information on using Python well, especially
           for developers of, or using, the Broadway framework.

.. contents::
   :depth: 2

------------------
The Need For Speed
------------------

While the Mediator platform is incredibly powerful relative to
comparable systems, it still isn't a 2 Ghz desktop workstation.
This section introduces some techniques to help the Mediator
avoid the dreded "Ghz envy" so it can lead a happy, productive
life.

Tune for the Common Code Path
=============================

<tbd>

-----------------------
Unexpected Side Effects
-----------------------

This section points out some unexpected side effects from seemingly
correct Python statements.

Default Arguments
=================

Default arguments are an extremely useful feature of most modern
programming languages, including Python.  There are situations
where the results may not be what one expected.

Empty Lists and Dictionaries
----------------------------

Using an empty list or dictionary as the default value of an
argument to a function (or method) has a surprising side effect:
**The same instance is reused every time the function
is invoked without the provided argument.**  In
other words, if the function or method modifies the
default object, then the next time the function is invoked
using the default argument, it will still contain those
modifications.  For example, take the following function
definition::

        import time
        def unexpected_reuse(victim_of_circumstance = []):
            # ... meaningful logic here ...
            whatever = time.time()
            victim_of_circumstance.append(whatever)
            return victim_of_circumstance

Every time that ``unexpected_reuse`` is invoked without any arguments,
it will default to the list instantiated in the function definition.
Since the function definition is only evaluated once, the list is
only instantiated once.  Therefore, the same list is being used
and modified.  This results in the following behavior::

        >>> unexpected_reuse()
        [1062353840.239259]
        >>> unexpected_reuse()
        [1062353840.239259, 1062353843.139215]
        >>> unexpected_reuse()
        [1062353840.239259, 1062353843.139215, 1062353843.72803]

Which is not what someone invoking the function would intuitively
expect.  Unless the the intention is to reuse the same list, the
correct implementation is::

        import time
        def no_unexpected_reuse(not_a_victim_of_circumstance = None):
            if not_a_victim_of_circumstance is None:
               not_a_victim_of_circumstance = []
            # ... meaningful logic here ...
            whatever = time.time()
            not_a_victim_of_circumstance.append(whatever)
            return not_a_victim_of_circumstance

Which results in the correct behavior below::

      >>> no_unexpected_reuse()
      [1062354950.181302]
      >>> no_unexpected_reuse()
      [1062354950.611606]
      >>> no_unexpected_reuse()
      [1062354951.249488]

Finding likely problems
+++++++++++++++++++++++

From the shell in the root source directory::

     grep -n -E '[[:space:]]*[a-zA-Z_]+[a-zA-Z0-9_]*[[:space:]]*=\
     [[:space:]]*[\[{][[:space:]]*[]}][[:space:]]*[,)]' \
     $(find . -name "*.py")

From inside (x)emacs, in a file in the root source directory
(``BROADWAY`` is a good choice):

     1. Get to the default grep prompt: <Alt-X>grep<return>
     2. Add the following to the grep -n prompt::

            -E '[[:space:]]*[a-zA-Z_]+[a-zA-Z0-9_]*[[:space:]]*=\
            [[:space:]]*[\[{][[:space:]]*[]}][[:space:]]*[,)]' \
            $(find . -name "*.py") 2>

Circular References due to Late Method Binding
==============================================

A cool trick is for an instance to override a method based on
an initialization, or even run-time decision.  A silly example
is something like::

    class A:
        def __init__(self, arg):
            if arg == 1:
                self.late_bound = self._late_1
            elif arg == 2:
                self.late_bound = self._late_2
            else:
                self.late_bound = self._late_other
            return
        def late_bound(self):
            assert 1, "Invalid internal state."
        def _late_1(self):
            return 1
        def _late_2(self):
            return 2
        def _late_other(self):
            return "other"

Results in objects that behave as follows::

    >>> a1 = A(1)
    >>> a2 = A(2)
    >>> ao = A(3)
    >>> a1.late_bound()
    1
    >>> a2.late_bound()
    2
    >>> ao.late_bound()
    'other'
    >>>

This is extremely powerful because it allows already instanciated
objects to modify their behavior in a way that is extremely power
and efficient (once a decision is made, no more conditional logic
is executed, etc).

The Problem
-----------

This creates a non-obvious, circular reference, of the instance
with it itself [#MET_INST]_ .

.. note::  For more information on the creation of the circular reference,
           see `Proving There is a Circular Reference`_ below.

.. [#MET_INST] Actually, it's a circular reference with the
               bound method instantiated when the method's
               attribute is dereferenced and it's reference
               to the instance.  But that is another topic
               entirely.

The Solution
------------

The solution is to create an object that acts like a bound method instance,
but that uses a *weak* reference to the actual instance.  This can be done
manually, but there is an ``mpx.lib.WeakInstanceMethod`` class to simplify to
dirty work.  By using a weak reference to the actual instance, Python does
not consider the ``WeakInstanceMethod`` instance a *referrer* to the
actual instance.  This means that when all other references to the actual
instance are deleted it will instantly be deleted and not require garbage
collection.  Class ``B`` is a reimplementation of class ``A`` using
``WeakInstanceMethod``, which is shown below::

    from mpx.lib import WeakInstanceMethod

    class B:
        def __init__(self, arg):
            if arg == 1:
                self.late_bound = WeakInstanceMethod(self, B._late_1)
            elif arg == 2:
                self.late_bound = WeakInstanceMethod(self, B._late_2)
            else:
                self.late_bound = WeakInstanceMethod(self, B._late_other)
            return
        def late_bound(self):
            assert 1, "Invalid internal state."
        def _late_1(self):
            return 1
        def _late_2(self):
            return 2
        def _late_other(self):
            return "other"

Notice that the class method is passed to ``WeakInstanceMethod``.  If an
instance method is used, it will not work.

This implementation behaves exactly the same to the typical user of the
instance::

    >>> b1 = B(1)
    >>> b2 = B(2)
    >>> bo = B(99)
    >>> b1.late_bound()
    1
    >>> b2.late_bound()
    2
    >>> bo.late_bound()
    'other'

But now there is no circular reference, so instances of ``B`` are deleted
immediately after the last reference to them is deleted.  This means that
fewer object collect awaiting garbage collection, which means that the
garbage collector runs less often which means that our applications are
more efficient.

.. note::  For more information on the proving that the circular reference
           has been removed, see `Proving There is not a Circular Reference`_
           below.

Shortcomings
++++++++++++

There are a couple of shortcomings to this solution.

1. It does not work with the ``__setitem__`` and *possibly* other
   implicit functions.

2. There may be a rare case where a user of you object **expects** the
   method reference to keep the object from being destroyed.  This is
   extremely rare, and against our programming policies.

I will cover these topics elsewhere, later.  I'll write that policy too...

Proving There is a Circular Reference
-------------------------------------

Assuming class ``A`` and instances ``a1``, ``a2``, and ``ao`` as defined
as above, then this section will duplicate the circular reference issue.

1. Disable the garbage collector::

        >>> import gc
        >>> gc.disable()
        >>>

   This ensures that we control when the garbage collector runs so
   nothing unexpected happens behind our backs.

2. Import the Broadway ``instances_of`` debugging function::

        >>> from mpx.lib.debug import instances_of
        >>> 

   This function will find all [#GC_OBJS]_ instances of objects derived from
   a class.

3. Delete the only references to ``a1``, ``a2`` and ``ao`` and then check
   if the instances are still in memory::

        >>> del a1
        >>> del a2
        >>> del ao
        >>> print len(instances_of(A))
        3
        >>> 

   Told you so.

4. Now run the garbage collector and recheck for instances of ``A`` in
   memory::

        >>> gc.collect()
        63
        >>> print len(instances_of(A))
        0
        >>> 

   After garbage collection [#GC_63]_ , no more instances of ``A`` exists.
   Since no other references where removed, and after garbage collection
   removed the 3 instance disappeared, we can be relatively sure that
   the instances had circular references.

.. [#GC_OBJS] OK, really just all *garbage collectible* instances,
              which is the same thing, for all intents and purposes.

.. [#GC_63] The example shows 63 objects collected.  We would have expected
            3, except that importing ``mpx.lib`` can start a lot of things
            in motion.  Your mileage may vary.

Proving There is not a Circular Reference
-----------------------------------------

Assuming class ``B`` and instances ``b1``, ``b2``, and ``bo`` as defined
as above, then this section will prove that there is not a circular reference
in the implementation of ``B`` .

1. Disable the garbage collector::

        >>> import gc
        >>> gc.disable()
        >>>

   This ensures that we control when the garbage collector runs so
   nothing unexpected happens behind our backs.

2. Import the Broadway ``instances_of`` debugging function::

        >>> from mpx.lib.debug import instances_of
        >>> 

   This function will find all [#GC_OBJS]_ instances of objects derived from
   a class.

3. Delete the only references to ``b1``, ``b2`` and ``bo`` and then check
   if the instances are still in memory::

        >>> del b1
        >>> del b2
        >>> del bo
        >>> print len(instances_of(B))
        0
        >>> 

   Told you so, again.

----
Tips
----

Complex String Formatting, Simplified
=====================================

Printf-like format specifications
---------------------------------

<todo: write>

Printf-like format specifications, TNG
--------------------------------------

<todo: write>

--------------
Change History
--------------

========== ==================================================================
2003/09/18 Added `Complex String Formatting, Simplified`_.
========== ==================================================================

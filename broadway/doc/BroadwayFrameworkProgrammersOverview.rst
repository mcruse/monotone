=========================================
Broadway Framework: Programmer's Overview
=========================================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: This document is intended to provide a terse, technical, overview
           of components and API available in the Broadway Framework.

.. contents::
   :depth: 2

-------
Purpose
-------

This document is intended to provide a terse, technical, overview
of components and API available in the Broadway Framework.  It
is meant to introduce Envenergy's Programmers to the Broadway
Framework and provide links to documents with more in depth
information.

----------
Disclaimer
----------

The only way I know to approach "catching up" on documentation is
to do it piecemeal, documenting new capabilities and concepts, while
slowly back filling older, supporting information as I touch on
it.  Every attempt that I have ever seen by myself,
or anyone else, to generate complete documentation in a big bang,
while behind the curve, has failed miserably. Therefore, I intend
to provide some useful, incomplete information with the hope that
it will continue to evolve into something better.

All suggestions and requests are appreciated.  Specifically, if there
is a part of the Framework that is particularly confusing, please
let me know and I'll try to address the general information in this
document and the details in a Programmer's Guide for that component.

------------
Introduction
------------

<todo: write>

-------
Modules
-------

This section provides (well, it will provide) a module-by-module overview of
Broadway.  Technically, most of the components in this list are actually
packages, but I like to stick to the term modules since the term package
is already overused.

mpx
===

This module is the linchpin of Broadway.  All intrinsic capabilities of the
Framework and all optional extensions are installed in this module, or one
of the it's sub-modules. 

mpx.lib
=======

This module contains all of the standard, non-node related, functionality
of the Framework.

factory(callable_path)
----------------------

<todo: write>

deprecated(message, stacklevel=3)
---------------------------------

<todo: write>

Reloadable Singletons
---------------------

<todo: write>

_`ReloadableSingletonFactory`
    <todo: write>

    ReloadableSingletonFactory(klass, \*args, \*\*keywords)
        <todo: write>

_`ReloadableSingletonInterface`
    Defines the methods required by the ReloadableSingletonFactory_.

    _`ReloadableSingletonInterface._unload`\ ()
        <todo: write>

_`ReloadableList`
    <todo: write>

_`ReloadableDict`
    <todo: write>

WeakInstanceMethod
------------------

<todo: write>

ImmutableMixin
--------------

<todo: write>

ImmutableWrapper
----------------

<todo: write>

mpx.lib.exceptions
==================

This module is intended to define all the common exceptions of Broadway
and the components.

.. note: For histerical raisons (as Mike would say), there has been a
         tendancy to define *all* exceptions in this module.  There
         is no need for this.  When a package introduces a new exception,
         it should be defined in said package.

MpxException
------------

The base class from which all Broadway exceptions should be derived.

DecoratedException
------------------

A class used to describe exceptions in a consistent manner, providing a flexible
representation of the traceback, the name, and nickname of the exception as
well as being the logical point to add methods that convert the exception to
human readable strings as well as the underlying dictionary representation
used by RNA.

**This is not an exception, do not derive new exceptions from this class.**

current_exception()
-------------------

Return a  `DecoratedException`_ instance that describes the *current*
exception.  The *current* exception means the exception currently being
handled inside of the except block of a try/except clause
of the current thread.

mpx.lib.namespace
=================

**This module has been removed.**  This module was an attempt to seperate
the lowest level of the namespace management from the `mpx.lib.node`_
module.  It was overkill and it's functionality has bee merged into
`mpx.lib.node`_\ .  *There were very few references*
*to this module and I've removed all of them and*
*replaced them with appropriate references in*
*mpx.lib.node.  Please fix, or let me know, if*
*you encounter any problems.*

mpx.lib.node
============

This module contains the classes and functions used to derive and interact
with nodes, but it does not contain any actual nodes. [#RootLie]_

.. [#RootLie] Ok, it contains the implementation of the root ('/') node,
              but that's a minor detail.


as_deferred_node(value, relative_to=None)
-----------------------------------------

<todo: write>

as_internal_node(value, relative_to=None)
------------------------------------------

<todo: write>

as_node(value, relative_to=None)
---------------------------------

<todo: write>

as_node_url(value)
------------------

<todo: write>

current_state(node)
-------------------

<todo: write>

is_configured(node)
-------------------

<todo: write>

is_enabled(node)
----------------

<todo: write>

is_node(node)
-------------

<todo: write>

is_node_url(node)
-----------------

<todo: write>

is_running(node)
----------------

<todo: write>

ConfigurableNode
----------------

<todo: write>

ConfigurableNode
    <todo: write>

_`ConfigurableNode.configure`\ (configuration_dictionary)
    <todo: write>

_`ConfigurableNode.configuration`\ ()
    <todo: write>

_`ConfigurableNode.start`\ ()
    <todo: write>

_`ConfigurableNode.stop`\ ()
    <todo: write>

_`ConfigurableNode.prune`\ (force=0)
    <todo: write>

_`ConfigurableNode.as_node`\ (path=None)
    <todo: write>

_`ConfigurableNode.as_internal_node`\ (path=None)
    <todo: write>

_`ConfigurableNode.as_node_url`\ ()
    <todo: write>

_`ConfigurableNode.is_enabled`\ ()
    <todo: write>

_`ConfigurableNode.is_running`\ ()
    <todo: write>

_`ConfigurableNode.is_configured`\ ()
    <todo: write>

_`ConfigurableNode.current_state`\ ()
    <todo: write>

_`ConfigurableNode._public_interface`\ ()
    <todo: write>

_`ConfigurableNode._create_instance_lock`\ ()
    <todo: write>

_`ConfigurableNode._acquire_node`\ ()
    <todo: write>

_`ConfigurableNode._release_node`\ ()
    <todo: write>

CompositeNode
-------------

Class that extends ConfigurableNode_, adding support for children
nodes.

_`CompositeNode.children_nodes`\ (\*\*options)
    <todo: write>

_`CompositeNode.children_names`\ (\*\*options)
    <todo: write>

_`CompositeNode.get_child`\ (name, \*\*options)
    <todo: write>

_`CompositeNode.has_child`\ (name, \*\*options)
    <todo: write>

_`CompositeNode.new_child`\ (name, factory)
    <todo: write>

_`CompositeNode.start`\ ()
    <todo: write>

_`CompositeNode.stop`\ ()
    <todo: write>

_`CompositeNode.prune`\ (force=0)
    <todo: write>

ServiceNode
-----------

<todo: write>

SubServiceNode
--------------

<todo: write>

ROOT
----

<todo: write>

mpx.lib.url
===========

<todo: write>

mpx.lib.thread_pool
===================

This module implements generic thread pools and also provides four thread pools
for common use: ``EMERGENCY``, ``HIGH``, ``NORMAL``, and ``LOW``.

ThreadPool
----------

Class used to instanciate a *private* thread pool.

ThreadPool(maxthreads)
    Instanciate a new "private" thread pool of up to ``maxthreads`` threads.

_`ThreadPool.size`\ ()
    Returns the number of threads in the pool.

_`ThreadPool.resize`\ (maxthreads)
    Change the pool to contain ``maxthreads`` threads.

_`ThreadPool.queue`\ (action, \*args, \*\*keywords)
    Queue the callable ``action`` on the thread pool and return a
    `PendingResult`_ object.  The first avaiable thread in the pool will
    invoke ``action(*args, **keywords)`` and update the returned
    `PendingResult`_\ .

_`ThreadPool.queue_on`\ (queue, key, action, \*args, \*\*keywords)
    Queue the callable ``action`` on the thread pool and return a
    `PendingResult`_ object.  The first avaiable thread in the pool will
    invoke ``action(*args, **keywords)``,  update the returned
    `PendingResult`_ and then add the `PendingResult`_ to the
    specified ``queue``.

    The ``key`` is an arbitraty object that the consumer of the target
    ``queue`` can use to identify the ``action``.

PendingResult
-------------

Class that instantiates an object used to poll, wait for and retrieve the
result of a queued action.

PendingResult()
    **Do not instantiate directly, instances are returned by the**
    **ThreadPool.queue() and ThreadPool.queue_on() methods.**

_`PendingResult.result`\ (timeout=None)
    Wait up to ``timeout`` seconds for the result of the previously queued
    action.

_`PendingResult.key`\ ()
    Return the ``key`` used to identify the previously queued action.
    This is only meaningful if the action had been queued via the
    `ThreadPool.queue_on`_\ () method.

_`EMERGENCY`
   Singleton to a thread pool intended for queued actions that must be executed
   soon, regardless of system load.  **This should be used extremely**
   **judiciously.**

_`HIGH`
   Singleton to a thread pool intended for actions that need to execute as
   soon as possible, without disrupting the system as a whole.
   **Actions queued on this pool should execute quickly to keep this pool**
   **available for other actions requesting the expedited priority.**

_`NORMAL`
   Singleton to a thread pool intended for the vast majority of the
   queued actions in the system.

_`LOW`
   Singleton to a thread pool intended for "background" tasks that may
   take a long time to complete but aren't in a hurry.

mpx.\ *pkg*
===========

Comming soon as part of the 'finer granularity', independant component
packaging refactor.  This will happen in phases, migrating packages
from their current ``mpx.lib.``\ *pkg*, ``mpx.service.``\ *pkg*
and ``mpx.ion.``\ *pkg* to their new ``mpx.``\ *pkg* centric locations.

When creating a new Framework component, please follow the following
paradigm [#PkgGuess]_ :

  ``mpx.``\ *pkg*
    This is the *root* [#CompositeOK]_ of the of the new component.  Please
    create an install script in the *pkg* and, if one exists, the packages
    properties module.  To create the install script, please use the
    ``pgenerate_install`` script.  If ``pgenerate_install``\ 's ``--help``
    is insufficient, please come see me.  The name of the package should be
    ``mpx.``\ *pkg*,  all the ``Makefile``\ s from this point on should set
    ``PRELEASE`` to ``mpx.``\ *pkg*, etc.

  ``mpx.``\ *pkg*\ ``.lib``
    This module should include all of the package's non-node related
    code.  The structure of this module and any underlying modules
    is up to the developer, but none of the code in these modules
    should refer to nodes as such.

  ``mpx.``\ *pkg*\ ``.node``
    This module should include all of the package's node specific
    code.  Ideally this is a collection of nodes that use
    assemble the entities in ``mpx.``\ *pkg*\ .lib such that external
    clients can express logical configurations, interrogate running
    collections of nodes and interact with them via RNA over XMLRPC.
    As above, the structure of this module and any underlying modules
    is up to the developer.

.. [#PkgGuess] This is the direction I am going, but details may change.
               Input, as always, is welcome.

.. [#CompositeOK] For complex related packages, the model
                  ``mpx.``\ *composite*\ .\ *pkg* is encouraged.
                  Something like mpx.bacnet.core, mpx.bacnet.mstp,
                  mpx.bacnet.ip, mpx.bacnet.ethernet, where
                  mpx.bacnet.core is requierd by all the other
                  packages would allow us to individually
                  install, upgrade, provide/sell each supported
                  media.  This is just an example, relax Fred.
                  Then mpx.bacnet.virtual could be split out
                  as well.

For example, if you are adding a new protocol called ``foobar``, then
you should create a new Broadway packaged named ``mpx.foobar``, in the
``.../mpx/foobar`` directory.  If it's a super simple Broadway package,
it would at least require the following files::

   Makefile.in
   mpx.foobar.install.py
   __init__.py
   _test_case_foobar.py

If there is supporting, non-node related code that is externally reusable
as well as node related code, then the minimal list would also include::

   lib.py
   node.py

Of course, ``lib`` and ``node`` can be implemented as Python packages,
there can be many more test suites and all sorts of implementation
specific, supporting modules.

mpx.dallas
==========

<todo: write>

mpx.avr
=======

<todo: write>

mpx_test
========

This module implements Broadway's extensions to Python's unittest
module.  **When writing a test suite, this module must be imported**
**before any other mpx or opt module.**

_`DefaultTestFixture`
    This is the base class from which all Broadway test cases should
    be derived.  It provides some special hooks into Broadway that
    allow for the complete creation and destruction of the environment
    in which tests run.

    The ``setUp`` method creates a new Broadway environment and the
    ``tearDown`` method destroys it.  If a sub-class overrides either of these
    methods, it must invoke the base class' equivalent.  Otherwise the results
    for all subsequent tests will be tainted.

_`DefaultTestFixture.assert_comparison()`
    Helper method that evaluates an expression and raises an ``AssertionError``
    exception with a useful text message if the expression does not evaluate
    true.

_`DefaultTestFixture.assert_hasattr()`
    Helper method that evaluates an expression and raises an ``AssertionError``
    exception with a useful text message if the ``object`` does not have the
    named ``attribute``.

_`DefaultTestFixture.should_raise_assertion()`
    Executes an expression and raises an ``AssertionError`` if the expresion
    does not.

_`DefaultTestFixture.del_node_tree()`
    This method ``stop()``\ 's and ``prune()``\ 's the entire node tree,
    ensuring that all future node references are to new nodes.

    If your tests rely on the node tree, then it is a good idea to call
    this in the derived class's ``tearDown()`` method.

_`DefaultTestFixture.new_node_tree()`
    This method creates a new node tree.  It does not start the node tree
    so subbsiquent code can add additional nodes as well as modify the
    configuration of existing nodes.

    If your tests rely on the node tree, then it is a good idea to call
    this method in the derived class's ``setUp()`` method.

_`DefaultTestFixture.tmpnam()`
    This method returns the full path name usable in creating a temporary
    file.  The following are gauaranteed:

    1.  The file does not exist.
    2.  The same file name will not be returned twice during the same
        invokation of entire test suite (aka the ``run_test_modules``
        command).
    3.  If the file is created, it will be deleted by the
        ``DefaultTestCase.tearDown()`` method at the end of the current
        unittest.

    .. note: The ``tmpnam()`` function does not create the file,
             that is the caller's responsibility.

_`DefaultTestFixture.RepeatingString`
    This class defines a string-like object that can represent a huge string
    (of repeated data) without consuming a lot of memory.

    .. note:  Python's underlying os.write() function uses the low-level
              buffers contanined in the string, which only contain the basic
              repeating pattern.  This can be a disadvantage in that os.write()
              will only write the repeating pattern once, but this side effect
              can be used to test high level write functions that need to test
              handling os.write() preforming partial writes.

_`thread`
    Instance of an object that has references to all of the unmodified
    attributes of the Python ``thread`` module.  This allows test cases
    tho access Python's ``thread`` module even though the *tested*
    code must conform to ``properties.STRICT_COMPLIANCE``.

opt
===

This module is a peer of ``mpx`` and it is where applications and third
party components that rely on, or extend, the Framework are installed.
Specifically, each vendor or client has, or can install, a sub-module named
after the vendor/client.  The actual application or component is installed in a
sub-module named after the application itself.  Examples::

         opt.trane.tsws
         opt.trane.vista
         opt.cinemark.pilot

It may seem that a more apt name for opt is app, but it important
to remember that the components installed in ``opt`` can also be services,
protocols, personalities, libraries or any other supporting component.

Rational
--------

The ``opt`` module is a peer of the ``mpx`` module to clearly separate
the application and third party files from the Framework itself.  The
``opt``\ .\ *vendor/customer-name*\ .\
*application/component-name* pattern allows multi-ple components
to be installed by multiple parties, without collision.

Broadway Packages
=================

Package Install Module
----------------------

<todo: write>

Package Properties Module
-------------------------

<todo: write>

-------------------
About this Document
-------------------

This source for this document, `BroadwayFrameworkProgrammersOverview.rst`_
is written using the ReStructuredText markup language which is part of
Python's docutils package.  Modifications to this document must conform to
the `reStructuredText Markup Specification`_.  If this is your first exposure
to reStructuredText, please read `A ReStructuredText Primer`_ and the
`Quick reStructuredText`_ user reference first.

.. _`BroadwayFrameworkProgrammersOverview.rst`:
    BroadwayFrameworkProgrammersOverview.rst
.. _`reStructuredText Markup Specification`:
   http://docutils.sourceforge.net/spec/rst/reStructuredText.txt
.. _`A ReStructuredText Primer`:
   http://docutils.sourceforge.net/docs/rst/quickstart.html
.. _`Quick reStructuredText`:
   http://docutils.sourceforge.net/docs/rst/quickref.html

--------------
Change History
--------------

========== ==================================================================
2003/09/18 Created in an attempt to desseminate information about recent
           changes and additions to Broadway.
           Specifically:  New Node capabilies and refactoring in
           `mpx.lib.node`_, general purpose thread pools in
           `mpx.lib.thread_pool`_, new DefaultTestFixture capabilies in
           `mpx_test`_, the dimise of `mpx.lib.namespace`_,
           reloadable singletons as well as weak method references in
           `mpx.lib`_, `mpx.lib.url`_ parser improvements and a warning of the
           impending `mpx.pkg`_ pattern.
2003/09/28 Added `mpx.dallas`_ and `mpx.avr`_ stubs.
2003/10/20 Added `DefaultTestFixture.assert_comparison()`_,
           `DefaultTestFixture.assert_hasattr()`_, and
           `DefaultTestFixture.should_raise_assertion()`_, and
           `DefaultTestFixture.RepeatingString`_.
========== ==================================================================

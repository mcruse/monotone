===============================
Node Browser Programmer's Guide
===============================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: This paper provides information about programmatic uses of the the
           Node Browser.

.. contents::
   :depth: 1

---------------
Simple Browsing
---------------

<info here>

-------------------------------------
The ``action`` Query String Parameter
-------------------------------------

<info here>

Setting a Node's Value
----------------------

<write up ``?action=get_override``>

<write up ``?action=set_override``>

---------------------------------------------------
Enabling and Disabling a Node's ``debug`` Attribute
---------------------------------------------------

<write up ``?action=debug_on`` and ``?action=debug_off``>

------------------------------------
Invoking Arbitrary Methods on a Node
------------------------------------

**New in 1.3.2 and 1.4.0.dev.1.**

The Node Browser now supports invoking arbitrary methods on any node
in the system\ [#InvokeRational]_.  This is accomplished by adding an
``?action=invoke&method=``\ *method-name*
query string to the node's URL, where *method-name* should be
replaced with the actual name of the method to invoke.  By default,
the response is returned as a ``Content-Type`` of ``text/plain``
since that is usually correct.  The ``?action=invoke`` query string
also accepts an additional ``Content-Type=``\ *content-type*
argument to force a specific ``Content-Type`` in the response.  This
is especially useful if the returned data is displayable by the
browser (like a JPEG), if it provides a hint as to the application
the browser should launch, or to force the browser to query the
user for the action.

.. [#InvokeRational] This capability was added to simplify
                     supporting a MehtaTech requirement,
                     but should be useful in many applications.

Data Marshalling
----------------

This interface is intended to be much simpler than RNA over XMLRPC
and therefore does not provide any data marshaling beyond simple
string representations.  XML has been considered, but is
inappropriate for the intended consumers of this capability.

Streaming/Chunking Data
-----------------------

If the object returned by the method has a ``read`` method, than
the ``read`` method will be used to stream the response to the
client (unless chunking is disabled, and then the result will
be read into memory and returned in a single response).  This
allows for returning much more data than would fit in memory.

Limitations
-----------

At this time, passing parameters and keywords to the method is
not supported but is easily added if we need to do so.  My current
thoughts are to add support for optional ``arg``\ *n*\ ``=``\ *value*
and ``kw_``\ *name*\ ``=``\ *value* elements to the query string.

--------------------
Interactive Examples
--------------------

``?action=invoke``
------------------

Start an interactive session.

Example::

    [mevans@fearfactory native]$ ./penvironment.d/etc/rc.mfw -i
    WARNING: init process not signalled.
    XMLHandler started
    >>>

Now, paste the text following at the interactive prompt::

    from mpx.lib.node import CompositeNode
    class X(CompositeNode):
        def cpuinfo(self):
            return open('/proc/cpuinfo')
        def meminfo(self):
            return open('/proc/meminfo')
        def ioports(self):
            return open('/proc/ioports')
        def iomem(self):
            return open('/proc/iomem')
        def __call__(self):
            return "Thanks for calling!"
    
    x = X()
    x.configure({'name':'too cool','parent':'/services'})

Now, log in to the `Node Browser`_, browse to `too cool`_ and invoke any of the
methods on `too cool`_ that do not require any arguments by appending
``?action=invoke&method=``\ *method name* to the URL.  Examples:

`?action=invoke&method=cpuinfo`_
    Invokes the ``cpuinfo`` method on the ``/services/too%20cool`` node.

`?action=invoke&method=meminfo`_
    Invokes the ``meminfo`` method on the ``/services/too%20cool`` node.

`?action=invoke&method=iomem`_
    Invokes the ``iomem`` method on the ``/services/too%20cool`` node.

`?action=invoke&method=ioports`_
    Invokes the ``ioports`` method on the ``/services/too%20cool`` node.

`?action=invoke&method=configuration`_
    Invokes the ``configuration`` method on the ``/services/too%20cool`` node.

`?action=invoke`_
    Invokes the ``/services/too%20cool`` node itself.

.. _`?action=invoke&method=cpuinfo`:
   http://localhost:8080/nodebrowser/services/too%20cool?action=invoke&method=cpuinfo
.. _`?action=invoke&method=meminfo`:
   http://localhost:8080/nodebrowser/services/too%20cool?action=invoke&method=meminfo
.. _`?action=invoke&method=ioports`:
   http://localhost:8080/nodebrowser/services/too%20cool?action=invoke&method=ioports
.. _`?action=invoke&method=iomem`:
   http://localhost:8080/nodebrowser/services/too%20cool?action=invoke&method=iomem
.. _`?action=invoke&method=configuration`:
   http://localhost:8080/nodebrowser/services/too%20cool?action=invoke&method=configuration
.. _`?action=invoke`:
   http://localhost:8080/nodebrowser/services/too%20cool?action=invoke
.. _`Node Browser`: http://localhost:8080/nodebrowser
.. _`too cool`: http://localhost:8080/nodebrowser/services/too%20cool

-------------------
About this Document
-------------------

This source for this document, `BrowserGuide.rst`_, is
written using the ReStructuredText markup language which is
part of Python's docutils package.  Modifications to this
document must conform to the
`reStructuredText Markup Specification`_.
If this is your first exposure to reStructuredText, please
read `A ReStructuredText Primer`_ and the `Quick
reStructuredText`_ user reference first.

.. _`BrowserGuide.rst`: BrowserGuide.rst
.. _`reStructuredText Markup Specification`:
   http://docutils.sourceforge.net/spec/rst/reStructuredText.txt
.. _`A ReStructuredText Primer`:
   http://docutils.sourceforge.net/docs/rst/quickstart.html
.. _`Quick reStructuredText`:
   http://docutils.sourceforge.net/docs/rst/quickref.html

-----------
CVS History
-----------

The CVS log of changes to this file.

$Log: BrowserGuide.rst,v $
Revision 1.1  2003/08/13 23:23:01  mevans
Support invoking arbitrary methods on Nodes via the Node Browser.


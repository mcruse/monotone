====================
Engineering Glossary
====================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: Glossary of terms used in the engineering group.

.. contents::
   :depth: 0

-------
Purpose
-------

To provide concise definitions of the terms we use.

--------
Glossary
--------

.. New Term Template
   -------------8<-----------------
   _`Term`
     Indented definition block.
   ------------->8-----------------

_`Configuration Attribute`
  See `Node Configuration Attribute`_

_`Node`
  1. The fundamental building block of dynamically loadable, textually
     configurable, object.
  2. An object that conforms to the `Node Interface`_

_`Node Configuration Attribute`
  An Node attribute that is set by the ``configuration()`` method.

_`Node Interface`
  Specifies the minimum sub-set of Common Node Methods and Common Node
  Attributes required for an entity to be considered a Node_.

_`Node Namespace`
  A hierarchical mapping of Node_\ s which is represented in conformance
  to the URI ``<path>``.

_`Node Tree`
  An acyclic directed graph of Node_\ s addressable in the `Node Namespace`_,
  via a `Node URL`_.

_`Node URL`
  A ``String``-like encoding of a Node's location the a `Node Tree`_.
  
  A Python reference to a Node object, or a ``String``-like encoding of a
  `Node URL`_.

_`NodeDef`
  Meta-data about a specific use of a Node_.  It defines the factory required
  to instantiate it, it's potential, immediate, relationships it the
  `Node Tree`_, and its `Configuration Attribute`_\ s

  It can be extended to in include other arbitrary, application specific
  meta-data via `Meta-Data Attribute`_\ s.

_`NodeDef Configuration Attribute`
  The definition of a `Node Configuration Attribute`_ in a NodeDef_.

-------------------
About this Document
-------------------

This source for this document, `Glossary.rst`_ is
written using the ReStructuredText markup language which is
part of Python's docutils package.  Modifications to this
document must conform to the
`reStructuredText Markup Specification`_.
If this is your first exposure to reStructuredText, please
read `A ReStructuredText Primer`_ and the
`Quick reStructuredText`_ user reference first.

.. _`Glossary.rst`: Glossary.rst
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

$Log: Glossary.rst,v $
Revision 1.1  2003/07/24 05:00:48  mevans
Continued to lay the ground work for documentation in the source tree.

Revision 1.2  2003/07/15 04:03:15  mevans
Interim checkup of functional system to avoid future conflicts and to backup this source base.

Revision 1.1  2003/07/11 01:21:28  mevans
Paranoia update of the NodeDef Guidelines.


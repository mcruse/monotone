=======================================
Subscription Manager Programmer's Guide
=======================================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: Documents the using the Subscription Manager.

.. contents::

-------
Purpose
-------

There are several areas of functionality that while
technically possible using standard Mediator Framework
components, the current solutions are complex and do not
scale well. The Subscription Manager is designed to address
several of these issues in a consistent, extensible, manner
while maintaining the simplicity and elegance of the
underlying components.  The specific areas that are
addresses by the Subscription Manager are: Driving one node
with the value of another; Linking node's for the purpose
proxying; Batching the retrieval of large numbers of node's
values efficient; Notifying consumers of values of changes
to those values; Providing a non-blocking mechanism for
remote consumers to read values. The purpose of the
Subscription Manager is to provide the support required to
provide the underlying functionality required to address
all these issues in a scalable, extensible manner.

--------
Overview
--------

The functionality of the Subscription Manager is implemented as a
ServiceNode via the mpx.service.SubscriptionManager class. Components
that require the Subscription Manager will 
locate the Subscription Manager via a well known NodeURL,
"/services/Subscription Manager". The implementation is not a
singleton and there are no limitations against extending the
mpx.service.SubsrciptionManager node via inheritance, nor using other
instances of the SubscriptionManager for specialized purposes. The
"/services/Subscription Manager" node will is an implicitly inherent
node of the MPX Application and typical end users can not delete or
rename the inherent Subscription Manager, nor can they add new
instances of the Subscription Manager to an MPX Application
configuration.

Clients of the Subscription Manager interact with it via it's public
methods. The fundimental concept behind the Subscription Manager is
that a Subscription is a collection of node references from which the
client wants real-time values. A client has two options for the
delivery of values, by registering for SubscriptionChangeOfValue
events or by polling for changed values. The reason for the two
delivery mechanisms is to suit different types of consumers. Each node
reference in a subscription is associated with a client specific
node identifier (NID_). This NID_ acts as the unique key that identifies
a node in a subscription. There are several reasons for using the NID_:

 - It allows a client to use an optimized reference to a node
   value. Examples of optimized references are keys to dictionaries,
   indexes to lists, tags used in HTML, etc.
 - It allows a client to specify the same node several times in a
   subscription. This may seem inefficient at first, but the
   Subscription Manager already has all of the logic to handle
   multiple consumers of the same node efficiently.  Why should the
   client have to invent a similar scheme?  This makes writing
   clients much easy.

Using the NID_, the client can dynamically manage a subscription,
adding new node references, removing existing ones and replacing an
existing NID_\'s node reference.

--------
Glossary
--------

Glossary of terms used in this programmer's guide.

.. The glossary terms are created as a reStructuredText Definition List
   where the term is an Inline Internal Link.  I.e.:

     _`term`
       definition ...

_`client`
  In the context of the subscription service, the client is the software entity
  that is using the Subscription Manager.  It is not relevant whether that
  entity resides in the same Mediator Framework Environment or not.

_`client specific node identifier`
  The pedantic phrase for a `Node ID`_.

_`NID`
  See `Node ID`_.

_`Node ID`
  An object, provided by the client of the Subscription Manager,
  used to uniquely identify a `Node Reference`_ in a Subscription_.
  Both the Subscription Manager and the client_ use the `Node ID`_ for this
  purpose.

  NOTES:

    1. A `Node ID`_ must be an instance of a Hashable class.
    2. A `Node ID`_ must be unique in a Subscription_, but may be reused in
       multiple `Subscription`_\ s.

_`Node Reference`

  A Python reference to a Node object, or a `Node URL`_.

_`Node Tree`
  An acyclic directed graph of Node_\ s addressable in the `Node Namespace`_,
  via a `Node URL`_.

_`Node URL`
  A ``String``-like encoding of a Node's location the a `Node Tree`_.
  
_`Subscription`
  A list of `Node Reference`_\ s of which the client_ interested.

_`Subscription ID`
  A conceptually opaque object, produced by the Subscription Manager, to
  uniquely identify a Subscription_. Both the Subscription Manager and the
  client_ use the `Node ID`_ for this purpose.

-------------------
About this Document
-------------------

This source for this document, `ProgrammersGuide.rst`_ is written using
the ReStructuredText markup language 
which is part of Python's docutils package.  Modifications to this
document must conform to the 'reStructuredText Markup Specification'_.
If this is your first exposure to reStructuredText, please read
`A ReStructuredText Primer`_ and the `Quick reStructuredText`_
user reference first.

.. _`ProgrammersGuide.rst`: ProgrammersGuide.rst
.. _reStructuredText Markup Specification:
   http://docutils.sourceforge.net/spec/rst/reStructuredText.txt
.. _A ReStructuredText Primer:
   http://docutils.sourceforge.net/docs/rst/quickstart.html
.. _Quick reStructuredText:
   http://docutils.sourceforge.net/docs/rst/quickref.html



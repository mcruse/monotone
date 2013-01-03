===============================
User Manager Programmer's Guide
===============================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: Programmers documentation about the Mediator Framework's
           UserManager intended to suppliment this Python package's
           automatically generated API documentation.

.. Note::

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

.. contents::


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
"/services/Subscription Manager" node will is an implicitly inherant
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
delivery mechanisms is to suit deferant types of consumers. Each node
reference in a subscription is associated with a client specific
node identifier (NID_). This NID_ acts as the unique key that identifies
a node in a subscription. There are several reasons for using the NID_:

 - It allows a client to use an optimized reference to a node
   value. Examples of optimzed references are keys to dictionaries,
   indexes to lists, tags used in HTML, etc.
 - It allows a client to specify the same node several times in a
   subscription. This may seem inefficient at first, but the
   Subscription Manager already has all of the logic to handle
   multiple consumers of the same node efficiently.  Why should the
   client have to invent a similiar scheme?  This makes writing
   clients much easy.

Using the NID_, the client can dynamically manage a subscription,
adding new node references, removing existing ones and replacing an
existing NID_\'s node reference.

--------
Glossary
--------

Glossary of terms used in this programmer's guide.

.. _`client specific node identifier`:

client specific node identifier
   An object, specified by the client of the Subscription Manager,
   used to identify a specific node reference in a subscription.

.. _NID:

NID
   See `client specific node identifier`_.

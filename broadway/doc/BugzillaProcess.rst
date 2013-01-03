==================================================
Use of Bugzilla in Envenergy's Development Process
==================================================

:Authors: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: To provide information on using Envenergy's Bugzilla Server
           as an integral part of our development process.

.. contents::
   :depth: 2

-------
Purpose
-------

This document is meant to provide information on using Envenergy's Bugzilla
Server as an integral part of our development process.  Specifically,
the intent of this document is to capture the practices and suggestions
that improve the efficiency of Software Development at Envenergy.  Hopefully
this will be a "living document" that evolves based on input from the
development team.

The information provided herein supplements `Bugzilla's help pages`_ as well
as Bugzilla's extensive `on-line documentation`_\ , it does not
replace it.  All Envenergy engineer's are expected to be familiar with
`Chapter 3. Using Bugzilla`_ of the `on-line documentation`_ as well as
the `Bug Writing Guidelines`_ \.

.. _`Bugzilla's help pages`:
   http://bugzilla.envenergy.com/bugzilla/bug_status.html

.. _`on-line documentation`:
   http://www.bugzilla.org/documentation.html

.. _`Chapter 3. Using Bugzilla`:
   http://www.bugzilla.org/docs216/html/using.html

.. _`Bug Writing Guidelines`:
   http://landfill.bugzilla.org/bugzilla-tip/bugwritinghelp.html

----------
Guidelines
----------

These guidelines outline the official practices of Engineering, regarding it's
use of Bugzilla.

Responsibility
--------------

At every point in a bug's life, it has an owner_\ .  As a general rule
an owner_ should accept_, resolve_, or reassign_ a bug within 1 business
day of being assigned.  This does not mean that the bug must be ``FIXED`` in
that time-frame.  The owner_ can reassign_ a bug for many reasons,
for example:

  Owner needs information
    The owner can reassign the bug to someone requesting more information.
    When the information is provided, the bug is reassigned back to the
    individual that requested the information.

  Wrong owner
    The owner believes that someone else is **significantly** better suited
    to fix the bug.  It's important that we can efficiently "hand off" bugs
    to the correct party.  On the other hand, it is bad for everyone
    for the engineering team to become over compartmentalize.  We are
    a small team and as such everyone must be willing to support the entire
    code-base.

  Insufficient Time
    If the bug is scheduled_ in a time frame that the owner_ can not
    meet due to other commitments, then the owner_ should reassign_ the
    bug to the project leader or Carl.

Prioritization
--------------

For the most part, the owner_ has a fair bit of latitude in deciding exactly
when to resolve a bug.  This is to allow for logical decisions in managing
one's workload, especially since several bugs may relate
to a common area of code.  Of course, once a bug is scheduled_ \ , then it
must not be "bumped" by unscheduled_ bugs without
`damn good reason`_\ .

-----------
Suggestions
-----------

Some suggestions on using Bugzilla in ways that efficiently support
our Development Process.  These suggestions do not effect the actual
policies, they're just meant to help individuals follow the policies
with less hassle.

Queries
-------

Creating custom, named, queries and adding to the footer of your Bugzilla
user greatly simplifies managing your bugs.

To define these queries, go to Bugzilla `Query Page`_, set up the query as
specified under the *Query Definition* sub-header and then press the
``Search`` button near the bottom of the page.  If the following query
definitions, if a search criteria is not mentioned,
then it is blank (for text entry fields) or has nothing selected
(for list boxes).

.. _`Query Page`:
   http://bugzilla.envenergy.com/bugzilla/query.cgi

My Assigned Bugs
++++++++++++++++

This query only lists bugs that I have accept_\ ed.  This should be the list
of bugs that you are working on for an upcoming product release.

Use
  I use this query to check for new bugs a couple times a day.

Query Definition
  **Status**
        ``ASSIGNED``

  **Email and Numbering**
        Any of
            [**x**] bug owner

            ``is``

            *user-name*\ ``@envenergy.com``

  (*****)  Remember this query, and name it: ``My Assigned Bugs``
           [**x**] and put it in my page footer

  Sort results by: ``Importance``

My New Bugs
+++++++++++

This query only lists bugs where I am the owner_ that have a status of
``NEW`` or ``REOPENED``.  These are bugs that I have not yet accept_\ ed
reassign_\ ed or resolve_\ d and that I am expected to do so in 24 hours.

Use
  I was this query to manage my list of bugs that should be addressed in an
  upcoming release.

Query Definition
  **Status**::

        NEW
        REOPENED

  **Email and Numbering**
        Any of
            [**x**] bug owner

            ``is``

            *user-name*\ ``@envenergy.com``

  (*****)  Remember this query, and name it: ``My Assigned Bugs``
           [**x**] and put it in my page footer

  Sort results by: ``Importance``

---------
Proposals
---------

Numbered ideas to improve our Bugzilla processes.  Please never reuse
a proposal number (i.e. **don't** re-sequence or otherwise "clean-up"
numbers in such a manner to confuse things).  Proposal ``0`` is a
place holder.

Active
------

  An area to list proposals that are (should be) under active consideration.

  1. A significant percentage of our "bugs" are actually new features and
     enhancements.  Should we call "bugs" something else like "Software
     Work Orders", "Issues", or does it matter. (mevans)

  2. It would be helpful to "officially" use project the milestone feature
     of Bugzilla for scheduling.  I think that the project lead/manager
     should be responsible for creating the milestones in Bugzilla.
     (mevans)

  3. I think a policy about using priorities could be helpful.  As an engineer,
     I like to use P1 to indicate the bugs that I'm working on and P2 as
     bugs that are next, etc...  They are not necessarily "scheduled" since
     so many are more infrastructure, etc.  I think that formalizing some
     sort of simple scheme would help any review process by making the
     intended sequencing visible to all parties.  Adding some sort of policy
     whereby management can isolate a bug and coupling that with proposal
     2 (using milestones) I think could help streamline our processes.
     (mevans)

Rejected
--------

  An area to list proposals that have been considered and rejected.  This
  area is intended to reduce dead horse flogging.

  0. No proposals have been rejected.

--------
Glossary
--------

_`accept`
        The action of accepting responsibility for a bug.  This is done
        by selecting the ``Accept bug (change status to ASSIGNED)`` 
        radio button and pressing the ``Commit``  button on a bug's
        show_bug page.  Typically, the owner_ should accept the
        bug\ [#OAB]_.

.. [#OAB] Acceptance of a bug can be forced on another user, but
          I believe that is not a good practice.

_`damn good reason`
       Like I'd help you think of one...

_`owner`
        The current assignee of a bug, whether or not that person has
        accept_\ ed the bug.

_`powers that be`
         The project lead, Carl, Mike, Chris...  Pretty much everybody but
         you.

_`reassign`
        The act of changing the ownership of a bug.

_`resolve`
        To document the (presumably) final status of a bug.

_`scheduled`
        Formally decreed by the `powers that be`_ to be resolved by a specific
        date.

_`unscheduled`
        Not scheduled_\ , duh.

-------------------
About this Document
-------------------

This source for this document, `BugzillaProcess.rst`_ is
written using the ReStructuredText markup language which is
part of Python's docutils package.  Modifications to this
document must conform to the
`reStructuredText Markup Specification`_.
If this is your first exposure to reStructuredText, please
read `A ReStructuredText Primer`_ and the `Quick
reStructuredText`_ user reference first.

.. _`BugzillaProcess.rst`: BugzillaProcess.rst
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

$Log: BugzillaProcess.rst,v $
Revision 1.2  2003/11/14 21:57:35  mevans
Changed to support the my latest understanding of our current process and added a section for proposals.

Revision 1.1  2003/08/19 20:51:22  mevans
Started living document for our processes using Bugzilla.

..  LocalWords:  Envenergy Envenergy's Bugzilla Bugzilla's OAB
..  LocalWords:  BugzillaProcess rst reStructuredText
..  LocalWords:  docutils mevans CVS

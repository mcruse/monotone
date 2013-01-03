===============================================================================
Security Issues
===============================================================================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: High level overview of current security issues intended to
           help prioritize and focus our efforts to address those
           concerns.

.. include:: document.hldb

.. contents::
   :depth: 2

-----------------------------------
Assorted Perceived Security Issues
-----------------------------------

This section touches on the assorted security issues and some possible
solutions.  The complexity of providing a consistent, extensible, solution
requires a more complete discussion, some of which is provided in
the `Related Topics`_ and `How Long is a Piece of String?`_ sections.

Application Runs as root User
-----------------------------

There has been some concern about the Mediator Application running as the root
user.  This is difficult to discuss in the "high-level" that this document
targets and there is a great deal of cross pollination between this issue and
user management.

Suggested Solution
==================

There are sections of the code that need to run as superuser for assorted
reasons\ [#]_\ .  I suggest that the Framework/Application start as root and
then changes to another user (perhaps mpxadmin, but actually a new user like
"mpxsystem" would even be better from an auditing standpoint).  By starting as
root, the application can switch back to root in protected sections where that
is required and can also switch to other users to run in the context of a
logged in user, taking advantage of Linux's file permissions, etc\ [#]_\ .

.. [#] Assorted reasons that some Framework/Application code needs to run as
       root:

   a) Some system calls and resources require root permissions
      (e.g. the low-level Ethernet access for BACnet and Mehta Tech, privileged
      ports like HTTP/HTTPS).
   b) Changing the effective user id of a thread.
   c) I'm sure there are more reasons.


.. [#] The Web Server already takes advantage of switching the effective user
       id and leveraging Linux's file permissions for GETing and SETing.

The goal of the user model in the Framework was to use actual OS users
as the basis for Framework/Application users.  Some of these concerns are
already being addressed 

Configuration Tool Exchanges Passwords in Plain Text
----------------------------------------------------

The current implementation of the Configuration Tool transmits user names and
passwords in plain text.  There are three interactions where this occurs: 1)
When the user logs in, 2) when modifying any "Nodes" that contain
username/password fields, and 3) when issuing commands the the command
service [#]_\ .

.. [#] The command service is used by the configuration tool to Setup the
       Mediator's Network Configuration, Restart the Framework and to reboot
       the Mediator.

Suggested Solution
===================

Switching the configuration tool to communicate the Mediator via HTTPS should
be a "quick fix" for the user log in and modifying the application
(broadway.xml) configuration.  The Framework already supports XML-RPC over
HTTPS, we just need to ensure that it is enabled "out of the box."

Communication to the command service occurs in a proprietary, plain text,
protocol that will be discussed below.

The Configuration Service Exchanges Passwords in Plain Text.
------------------------------------------------------------

Communication to the command service occurs in a proprietary, plain text,
"protocol" that includes broadcasting (via Multicast) usernames and passwords
in plain text.  At some point an effort occurred to munge the username and
password using a predictable (i.e. easily cracked) algorithm.
I don't know if that effort was ever completed and put to use.

Suggested Solution
===================

I think that using a combination of refinements to the current Multicast and/or
adding a "secure channel" via XML-RPC over HTTPS could be a achieved using an
IP address created by following the IETF draft titled
`Dynamic Configuration of Link-Local IPv4 Addresses`_\ .  This requires more
investigation and there may be better approaches...

.. _`Dynamic Configuration of Link-Local IPv4 Addresses`:
   http://files.zeroconf.org/draft-ietf-zeroconf-ipv4-linklocal.txt

Mpxadmin Password Exposed in JavaScript
---------------------------------------

Currently, some of our applications hard code the "mpxadmin" user in some of
the JavaScript used to interact with the Mediator via XML-RPC.  The reason for
JavaScript containing the mpxadmin username and password in clear text
ultimately comes down to inconsistent use of the (incomplete)
User Manager in various components of the Framework and Applications
(specifically Costco, methinks).

Since any user can select "read source" on a page containing the JavaScript,
this is a *major* security flaw.

Suggested Solution
===================

Adopt a policy that we don't hard-code usernames and passwords in JavaScript.
``:-)``

Of course to make it practical to enforce this policy, we need to complete and
document our `Basic User Model`_ as well as completing RFC2617 support in
`RNA over XML-RPC`_\ .

--------------
Related Topics
--------------

Basic User Model
----------------

The Framework User object is conceptually an extension of the OS user.  The
primary reason for this is that it allows simple leveraging of OS capabilities\
[#]_\ .  The current implementation is solid, but limited to the bare minimum
to meet each project's requirements.  The fundamental model is extremely
flexible and allows the Framework and Applications to associate meta-data with
users to help solve application specific requirements.  There are several tasks
we need to prioritize "shore up" our Basic User Model.  These include (in no
particular order):

  1. Complete User Management API.  We support adding users, deleting users,
     changing their password and adding, deleting and modifying the user's
     meta-data.  But there are several attributes of users that we have not
     exposed the management of through a simple API.
  2. Implement some sort of User Management GUI.  This could be done in the
     Configuration Tool, but I think we should seriously consider starting to
     use a Browser based interface for much of the basic system configuration.
  3. Determine if we want any "out of the box" users (e.g. "mpxadmin",
     "mpxoperator", "mpxuser").  We don't currently have an "out of the box"
     application.

.. [#] File and resource permissions, use of quotas on a per user bases,
       and integration with external applications.

RFC2617
-------

RFC2617\ [#]_ provides a simple authentication model for HTTP and HTTPS.  The
Framework's Web Server now supports RFC2617 "basic authentication" [#]_ and I
believe that this provides an appropriate, common, access point for all of our
primary "entry points" into the system (HTTP/HTML, XML-RPC, RNA over XML-RPC
and eventually SOAP).

.. [#] `HTTP Authentication: Basic and Digest Access Authentication`_
.. [#] Digest authentication is presumably "mostly implemented" but was
       deemed unnecessary for the Costco project and therefore left dangling.

.. _`HTTP Authentication: Basic and Digest Access Authentication`:
   http://www.faqs.org/rfcs/rfc2617.html

RNA over XML-RPC
----------------

As mentioned previously, our Web Server now supports RFC2617 base user
authentication in a fairly extensible manner.  We need to extend our XML-RPC
handler to use this capability and then we must decide on one of two
approaches:

1.  Extend RNA to enforce user based access control.
2.  Add inherent support in the Framework for determining the "user context"
    in which the current code is running.

The first approach touches less code but requires that each "entry point"
into the system manage user access and probably will require maintaining fairly
complex rules.  The second approach is more flexible from a "code anything
you need" standpoint, provides a more consistent approach, but ultimately will
require more code.  I like the flexibility of the second approach, but I'd like
to ponder it more...

SSL Certificates
----------------

Since the Mediator uses the openssl/openssh libraries, we could integrate the
use of SSL Certificates for authentication purposes over HTTPS and IPSec.  This
could have advantages, especially in managing large numbers of Mediators.  I
don't have a specific suggestion at this time, but I believe that it merits
some serious research (I think Bret and Mike have quite a head start in this
area).

SOAP
----

Moving forward, we need to ensure that our implementations will not interfere
with cleanly integrating SOAP into our projects and Framework.  All research
that I've done indicates that using RFC2617 authentication is a
standard practice for SOAP in general as well as for and Microsoft .NET servers
in particular.  Furthermore, SSL is a standard mechanism for encrypting SOAP
messages.  Therefore, I believe that the suggestions put forth support
providing a standards compliant SOAP interface.

------------------------------
How Long is a Piece of String?
------------------------------

Security in itself can be a topic for endless thought, discussion, debate, hand
wringing.  On top of that, it either touches on, or reminds us of millions of
other issues.  I tried to keep this document concise and I think that it's
important that we approach these issues in a phased approach.  Just because a
phase does not cure cancer and solve world hunger is no reason to dismiss it.

Below are some related and not so related issues that I didn't want to lose.

Policies
--------

We should have some general policies about the security of the Mediator.  In
general, the system should be fairly "locked down" out of the box.  Where user
action is required to "lock down" the Mediator, we should provide clear
documentation to help our customers protect themselves from nar-do-wells.

Resource Management
-------------------

We need to look into better tracking of resource consumption that can lead to
system failures.  Basically RAM and Flash.  How mush is used, by whom and what
to do when we are running out.

Copyrights
----------

While far from our largest concern, it would behoove us to have a standard
copyright in all of our source files, possible in the binary as well.  We need
at least to types of copyrights: one for files that the user shouldn't modify,
and probably should not have gotten a hold of, and another for templates,
example files, source code that is readable in published pages, etc.  As part
of the SDKs we may even want a third "less restrictive/more open source"
license.

Ultimately, our build process should become the "Copyright Nazi", ensuring that
we are following what ever rules we make up.

===============================================================================
Security Bug List
===============================================================================

:Author: Mark M. Evans
:Contact: mevans@envenergy.com
:Revision: $Revision: 20101 $
:Date: $Date: 2011-03-06 08:02:15 -0800 (Sun, 06 Mar 2011) $
:Copyright: 2003 Envenergy, Inc. Proprietary Information
:Abstract: Attempt to break up the Security Issues into Bugzilla
           entries that can be prioritized and scheduled.

.. include:: document.hldb

.. contents::
   :depth: 2

-----------------------------------
Bug 1: Run Framework as "mpxsystem"
-----------------------------------

Requirements
------------

1. broadway.core install script to nondestructively add a "mpxsystem" user
2. mpx.system.run() switches process to "mpxsystem" user.
3. Add a function to mpx.lib.user to return the "current" User object,
   switch to another user, saving the current user on a "stack" and another
   function to restore the previous user from the stack.
4. Find all code sections that must run as root (e.g. access to the low level 

Notes
-----

1. The init process must start the Framework/Application as root, but the
   Framework should switch to the "mpxsystem" user as the default running user
   and switch back to root when root access is required.

2. When the unit tests are run as a regular user, user switching will not
   work.  This should be addressed gracefully.

3. Code that switches to "superuser" should be contained in a try/finally
   block that insures that the thread will return to the normal mpxsystem
   user.

.. _`Bug 2`:

-----------------------------------------------------
Bug 2: Framework should enable HTTPS "out of the box"
-----------------------------------------------------

Some versions of the Framework enable HTTPS "out of the box", some don't.  The
default behavior of the Framework should enable both HTTP and HTTPS.  This
should be a baseline requirement that we verify.

Requirements
------------

1. The default configuration for HTTPS includes enough information to support
   self generated certificates.
2. All the default services of HTTP should also be enabled:
   a. node browser
   b. message log viewer
   c. XML-RPC
   d. RNA over XML-RPC

Notes
-----

1.  Communicating via HTTPS will result in "self signed" certificate messages
    which we need to document, and which is the topic of other investigations.

---------------------------------------------------------------------
Bug 3:  Configuration Tool should default to using XML-RPC over HTTPS
---------------------------------------------------------------------

The Configuration Tool should support XLM-RPC (and therefore RNA over XML-RPC)
via HTTPS to improve the secure transmission of user names and passwords.

Requirements
------------

1. Added support of XLM-RPC and RNA over XML-RPC via HTTPS.
2. Continued support of XLM-RPC and RNA over XML-RPC via HTTPS for both
   backwards compatibility and for configurations and applications that disable
   HTTPS.
3. Ideally, the configuration tool would "know" the correct transport to try
   first (via configuration data, the configuration service or some other
   means.)  If the configuration tool needs to resort to a default, the default
   behavior would be to try HTTPS first and then fall back to HTTP if the HTTPS
   TCP/IP connection is rejected or times out.
4. When attempting to connect over HTTP the user should be informed that they
   are using a clear text connection, and be given the opportunity to abort the
   connection, as well as to continue.
5. The user should be able to disable these warnings on a per target bases as
   well as globally.

Notes
-----

The current implementation of the Configuration Tool transmits user names and
passwords in plain text.  There are three interactions where this occurs:

  1. When the user logs in.
  2. When modifying any "Nodes" that contain username/password fields.
  3. When issuing commands the the command service [#]_\ .

.. [#] The command service is used by the configuration tool to Setup the
       Mediator's Network Configuration, Restart the Framework and to reboot
       the Mediator.

This bug addresses the first two interactions.

Depends On
----------

`Bug 2`_

-------------------------------------------------------------------
Bug 4:  The Configuration Service Exchanges Passwords in Plain Text
-------------------------------------------------------------------

Communication to the command service occurs in a proprietary, plain text,
"protocol" that includes broadcasting (via Multicast) usernames and passwords
in plain text.  At some point an effort occurred to munge the username and
password using a predictable (i.e. easily cracked) algorithm.
I don't know if that effort was ever completed and put to use.

Requirements
------------

1. During authentication, passwords must exchanged in a secure manner.
2. Commands that include usernames and passwords must be encrypted.
3. The Configuration Tool should continue to support the current protocol for
   backwards compatibility for a TBD period of time.

Notes
-----

1. This is important to fix, but requires more consideration and work than
   `Bug 3:  Configuration Tool should default to using XML-RPC over HTTPS`_
   and I'd like a lot of input from Mike Cruse.
2. This will require changes to both the Configuration Tool and the
   Configuration Service which runs on the Mediator.
3. A combination of refinements to the current Multicast and/or
   adding a "secure channel" via XML-RPC over HTTPS could be a achieved using
   an IP address created by following the IETF draft titled 
   `Dynamic Configuration of Link-Local IPv4 Addresses`_\ .  This requires more
   investigation and there may be better approaches.

.. _`Dynamic Configuration of Link-Local IPv4 Addresses`:
   http://files.zeroconf.org/draft-ietf-zeroconf-ipv4-linklocal.txt

----------------------------------------------
Bug 5: Mpxadmin Password Exposed in JavaScript
----------------------------------------------

Requirements
------------

1. Remove all hard-coded user names and passwords from all pages served by the
   Mediator.

Depends On
----------

`Bug 9`_

.. _`Bug 6`:

---------------------------------------
Bug 6: Complete User Management Objects
---------------------------------------

Requirements
------------

1. A User object that presents all the attributes of a user and that
   allows for modifying the attributes of a user.
2. A Group object that presents all the attributes of a group and that
   allows for modifying the attributes of a group.
3. A mechanism that returns User objects by name or id.
4. A mechanism that returns Group objects by name or id.
5. A factory to create new users.
6. A factory to create new groups.

The framework needs a User and Group object that represent attributes of
users and allow for 

Notes
-----

1. Much of this functionality is complete, but it is easier to list
   the complete requirements.

---------------------------------------
Bug 7: Complete User Management Service
---------------------------------------

Extend the /services/user_management Node to provide a methods
that use the User and Group objects internally, but expose an
API that requires only simple objects supported by XML-RPC (floats, integers,
strings, tuples, and dictionaries).

Notes
-----

1. Much of this functionality is complete, but it is easier to list
   the complete requirements.
2. This is required for external management of users, from an enterprise
   server for instance.

Depends On
----------

`Bug 6`_

------------------------------------------------
Bug 8: Implement a Standard User Management Page
------------------------------------------------

Create (an) extensible PSP page(s) that provides for basic user
management.  It should serve as the foundation from which applications could
provide application specific user management pages.

Depends On
----------

`Bug 6`_

.. _`Bug 9`:

----------------------------------------------------
Bug 9: Use RFC2617 Authentication in XML-RPC Handler
----------------------------------------------------

Requirements
------------

1. Implement this functionality on a new URL to allow reverse compatibility
   during the transition.
2. Enable using Web Server's RFC2617 Authentication.
3. Pass the User Object provided in the request on to the sub handler.

---------------------------------------------
Bug 10: Define the Standard Users and Groups
---------------------------------------------

Notes
-----

Determine if we want any "out of the box" users and groups (e.g. "mpxadmin",
"mpxoperator", "mpxuser").  We don't currently have an "out of the box"
application.

---------------------------------------------------
Bug 11: Clarify Security Goals for RNA over XML-RPC
---------------------------------------------------

Notes
-----

We must decide on one of two approaches:

1.  Extend RNA to enforce user based access control.
2.  Add inherent support in the Framework for determining the "user context"
    in which the current code is running.

The first approach touches less code but requires that each "entry point"
into the system manage user access and probably will require maintaining fairly
complex rules.  The second approach is more flexible from a "code anything
you need" standpoint, provides a more consistent approach, but ultimately will
require more code.  I like the flexibility of the second approach, but I'd like
to ponder it more...

---------------------------------------------------
Bug 12: Clarify Issues and Uses of SSL Certificates
---------------------------------------------------

TBD

-----------------------------------------------------
Bug 13: Establish Security Policies and Documentation
-----------------------------------------------------

Notes
-----

We should have some general policies about the security of the Mediator.  In
general, the system should be fairly "locked down" out of the box.  Where user
action is required to "lock down" the Mediator, we should provide clear
documentation to help our customers protect themselves from nar-do-wells.

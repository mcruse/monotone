"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from mpx.componentry import Interface
from mpx.componentry import Attribute
from mpx.componentry.security.interfaces import IUser as _IUserObject
from mpx.service.security.interfaces import ISimpleManager
from mpx.lib.eventdispatch.interfaces import IEvent

class IUser(_IUserObject):
    """
        Slightly ugly way of extending the componentry.security
        Interface definition of IUser without requiring name-changes
        throughout.  Should be straightened-up eventually.
    """

    def is_removable():
        """
            Return boolean indicator as to whether node may be pruned.
        """

    def is_configurable():
        """
            Return boolean indicator as to whether node may be (re)configured.
        """

class IUserEvent(IEvent):
    user = Attribute(
        """
            Reference to User node which raised the Event.
        """)

    description = Attribute(
        """
            Short description of event.  For example, 'role change',
            'password change', 'name change', 'user configured'.
        """)

class IUserManager(ISimpleManager):
    """
        Manages collection of User objects and provides
        shortcut functions for convenience.  Primarily
        serves as marker interface.
    """

    anonymous = Attribute(
        """
            Read-only reference to special user "Anonymous", which is
            User object associated with unidentified users.
        """)

    sysadmin = Attribute(
        """
            Read-only reference to special user "System Administrator";
            this user will be given all permissions dynamically during
            permission queries.
        """)

    def get_users():
        """
            Return list of user objects.
        """

    def get_user(name):
        """
            Return user node with name 'name'.
        """

    def get_user_names():
        """
            Return list of user names.
        """

    def has_user(username):
        """
            Returns True if user with username 'username'
            exists, False otherwise.
        """

    def user_from_object(userobject):
        """
            Function to bridge existing User Manager and User objects
            as defined in mpx.lib.user.User with the Users defined here.
        """

    def user_from_current_thread():
        """
            Grab the mpx.lib.user.User from the current running thread,
            which only works for web-based requests, and convert to
            User Node and return.
        """

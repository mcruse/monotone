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
from mpx.service.security.interfaces import ISimpleManager
from mpx.componentry import Interface
from mpx.componentry import Attribute

class IRoleManager(ISimpleManager):
    """
        Manages collection of Role objects and provides
        shortcut functions for convenience.  Primarily
        serves as marker interface.
    """

    unknown = Attribute(
        """
            Read-only reference to special role "Unknown", which is role
            meant to be assigned to unauthenticated users.
        """)

    authenticated = Attribute(
        """
            Read-only referent to special role "Authenticated", which role
            meant to be assigned to all identified and authenticated users.
        """)

    administrator = Attribute(
        """
            Read-only reference to special role "System Administrator", this
            reference may be used by policies to determine whether all
            permissions should be granted to a role.
        """)

    def get_roles():
        """
            Return list of role objects.
        """

    def get_role(name):
        """
            Return role node with name 'name'.
        """

    def get_role_names():
        """
            Return list of role names.
        """

    def has_role(rolename):
        """
            Returns True if role named 'rolename' exists;
            False otherwise.
        """

class IRole(Interface):
    """
        Marker interface for incredibly simple Role
        Nodes, whose name is the role name and which
        have a description allowing user to create a
        descriptive explanation of the role's meaning.
    """

    def is_removable():
        """
            Return boolean indicator as to whether node may be pruned.
        """

    def is_configurable():
        """
            Return boolean indicator as to whether node may be (re)configured.
        """

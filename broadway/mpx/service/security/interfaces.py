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
from mpx.lib.neode.interfaces import ICompositeNode

class ISecurityService(Interface):
    """
        Interface defining those security-related attributes that
        may be retreived from any of the security services.
    """

    security_manager = Attribute(
        """
            Read-only reference to Security Manager, the primary manager
            under which all other security services/managers are located.
        """)

    user_manager = Attribute(
        """
            Read-only reference to User Manager service, this is typically
            the "Users" child of the security manager.
        """)

    role_manager = Attribute(
        """
            Read-only reference to Roel Manager service, this is typically
            the "Roles" child of the security manager.
        """)

    policy_manager = Attribute(
        """
            Read-only reference to Policy Manager service, this is typically
            the "Policies" child of the security manager.
        """)

class ISecurityManager(ISecurityService):
    """
        This interface does not extend the SimpleManager as it
        owns inherent children 'roles', 'users', and 'policies',
        which may not be deleted.
    """

    def as_secured_node(self, node_url, user = None, as_node_func = None):
        """
            Returned ISecured version of node with URL 'node_url'.
            If 'user' is not None, apply specified user for security;
            otherwise attempt to get user from active thread.

            By default Security Manager will use its own Nodespace's as_node,
            but this may be overriden by passing in a different as_node_func.
        """


class ISimpleManager(ISecurityService):
    """
        Marker interface for nodes which manage collections of
        child objects.  The purpose of the Marker is to enable
        the use of a general configuration adapter which creates
        a form, XHTML for now, that allows the user to
        add, edit, and remove children nodes.

        Extends the ICompositeNode interface to ensure that any
        object implementing this interface also implements
        the ICompositeNode, typically through extending
        CompositeNode itself.  The concept of a 'manager' is
        tightly bound to the concept of a node with children
        nodes.

        NOTE: Although this Interface is defined here, it should
        eventually be moved to a more generic location to reflect
        its role as a generic management interface.
    """

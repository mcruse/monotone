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

class IPolicyManager(ISimpleManager):
    """
        Manages collection of policy objects and provides
        functions simplifying the lookup of important information
        but requiring data from groups of policies.
    """

    default = Attribute(
        """
            Read-only reference to special policy "Default", which is policy
            that "always" exists and establishes base mappings.
        """)

    def get_permissions():
        """
            Return list of available permissions as listed in
            permissions repository module.

            NOTE: This is a static method, so can be called by
            class or instance reference with same results.
        """

    def get_policy(name):
        """
            Return policy node with name 'name'.
        """

    def has_policy(name):
        """
            Test whether policy named 'name' exists.  Return
            True if it does, false otherwise.
        """

    def get_policies():
        """
            Return list of policy nodes.
        """

    def get_context_policies(context, ascending = True):
        """
            Return a list of policices that are in effect,
            or active, and the location of context.  Context may be
            a URL or a node reference.

            Optional parameter 'ascending' allows the caller
            to specify the sort order of the policy list.

            If ascending is True or not provided, policies will be
            ordered from least to greatest degree of specificity.
        """

class IPolicy(Interface):
    context = Attribute(
        """
            Node URL at where Policy is applicable.  This policy
            will be applied to all nodes at URL 'context' and below,
            unless overridden by another policy in a lower context.
        """
    )

    acquires = Attribute(
        """
            Boolean flag indicating whether this policy inherits all
            policy assertions already in place at this location, or
            if it replaces all existing assertions altogether.
        """
    )

    rolemap = Attribute(
        """
            Dictionary mapping roles to permissions.  Key
            is name of role, value is list of permissions granted
            to role.
        """
    )

    def is_running():
        """
            Returns boolean indication of whether node has
            been successfully started and not stopped since.
        """

    def is_removable():
        """
            Return boolean indicator as to whether node may be pruned.
        """

    def is_configurable():
        """
            Return boolean indicator as to whether node may be (re)configured.
        """

    def get_permissions(role):
        """
            Return list of permissions that have been granted to role
            'role' by this Policy.
        """

    def set_permissions(role, *permissions):
        """
            Allows permissions for single role to be set at a time,
            same functionality is available through configuration dictionary.
        """

    def rank_match(context):
        """
            Return 0 if Policy's context does not match 'context',
            otherwise return integer value indicating the number of
            nodes in context so match can be compared to that of other
            policies.

            Method may raise mpx.lib.exceptions.ENotRunning if the
            policy has not been started, has been stopped, or an
            exception occurred during start.
        """

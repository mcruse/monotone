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

class ISecurityContext(Interface):
    """
        Interface implemented by an object which may act as a
        security conetxt, meaning security policies may be
        associated with the instance itself.
    """
    url = Attribute("""
        String instance indicating the context with
        which a policy may be associated.""")

class IUser(Interface):
    """
        Marker interface for incredibly simple User
        Nodes, whose name is the user name and which
        have a description allowing user to create a
        descriptive explanation of the user's meaning.
    """

    def get_roles():
        """
            Returns list of roles currently assigned to user.
        """

    def set_roles(*roles):
        """
            Replaces all currently assigned roles with 'roles'.
        """

class ISecure(Interface):
    """
        Marker Interface used for secured adaptation
        of arbitrary Interface implementing objects.
    """

    def set_caching(flag):
        """
            Enable/disable caching of Authorizations operations.

            Flag == True: Enable caching.  Can improve performance
            considerably in situations where repetitive requests are
            made agains the adapter for particular attributes.

            Flag == False: Disable.  May provide minimal improvement
            of default performance iff usage has little to know repitition
            of lookups.

            The default behaviour uses caching.
        """

    def is_adaptable():
        """
            Returns True if the user/context/policies associated with this
            security adapter allow access to those attributes used by the
            adaptation framework.  Failures occurring in the adaptation
            code--even Authorization failures--are very effectively squashed
            and expressed only as ComponentLookupErrors.  It is therefore
            wise to test the adaptability of a secured object before attempting
            to apply another adapter to it.
        """

    def test_adaptability():
        """
            Actually gets each of the attributes needed by the adaptation
            framework.  This function actually raises an Authorization
            exception if adaptation of this object will fail outright.
        """

class ISecurityInformation(Interface):
    def from_default():
        """
            Factory method for producing duplicates of the standard
            default security configuration.  Used to ease the work
            associated with creating and configuring SecurityInformation
            instances--most configuration already done in default.

            NOTE: This method is a classmethod!
        """

    def make_private(name):
        """
            Make attribute named 'name' both unsettable and ungettable.
        """

    def make_public(name):
        """
            Make attribute named 'name' both settable and gettable.
        """

    def protect(name, getpermission, setpermission = None, delpermission = None):
        """
            Protect getting attribute named 'name' with permission
            'getpermission.'

            If optinal 'setpermission' is provided, the set permission
            will also be assigned.
        """

    def allow_get(name):
        """
        """

    def allow_set(name):
        """
        """

    def allow_del(name):
        """
        """

    def disallow_get(name):
        """
        """

    def disallow_set(name):
        """
        """

    def disallow_del(name):
        """
        """

    def protect_get(name, permission):
        """
        """

    def protect_set(name, permission):
        """
        """

    def protect_del(name, permission):
        """
        """

    def getting_permission(name):
        """
            Get permission associated with getting attr named 'name.'

            Returns None if no permission has been set.
        """

    def setting_permission(name):
        """
            Get permission associated with setting attr named 'name.'

            Returns None if no permission has been set.
        """

    def deleting_permission(name):
        """
            Get permission associated with deleting attr named 'name.'

            Returns None if no permission has been set.
        """

    def copy():
        """
            Convenience function for duplicating SecurityInformation
            instances.  Used by 'from_default' to create copies of
            default security information; should be useful in other
            circumstances as well.
        """

class IPermissionChecker(Interface):
    """
        Provide 'getter' type functions for querying
        object about assigned security information.
    """

    def set_default_security(fallback = None):
        """
            Provide a default SecurityInformation instance
            to be used for objects which have no other security
            information provided.
        """

    def getting_permission(attribute):
        """
            If a permission has been associated with getting
            attribute 'attribute' return it; otherwise return
            None.
        """

    def setting_permission(attribute):
        """
            If a permission has been associated with setting
            attribute 'attribute' return it; otherwise return
            None.
        """

    def deleting_permission(attribute):
        """
            If a permission has been associated with deleting
            attribute 'attribute' return it; otherwise return
            None.
        """

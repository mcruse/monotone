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
from threading import Lock
from mpx.componentry import implements
from interfaces import ISecurityInformation
from zope.interface import advice as _zadvice

def secured_by(*securityinfos):
    """
        Declare that object(s) 'securityinfos' provide
        security information for klass being defind during call.
    """
    for securityinfo in securityinfos:
        if not ISecurityInformation.providedBy(securityinfo):
            raise TypeError('Security objects must provide ISecurityInfo.')

    ##
    # Closure formed by inner-function allows delayed assignement
    #   of security information.
    def setup_security_info(klass):
        if not vars(klass).has_key('__secured_by__'):
            klass.__secured_by__ = []
        map(klass.__secured_by__.append, securityinfos)
        return klass
    return _zadvice.addClassAdvisor(setup_security_info)

def get_security_info(context, default = None):
    securityinfos = getattr(context, '__secured_by__', [default])
    if len(securityinfos) > 1:
        exception = Exception('Object has multiple security infos.  Use "get_securityinfos".')
        raise exception
    return securityinfos[0]

def get_security_infos(context, default = []):
    securityinfos = getattr(context, '__secured_by__', default)
    return securityinfos[:]

class SecurityInformation(object):
    implements(ISecurityInformation)
    _default_lock = Lock()
    _default_security = None

    def from_default(klass):
        klass._default_lock.acquire()
        try:
            if klass._default_security is None:
                default = SecurityInformation('View', 'Configure', 'Private')
                default.protect_get('get', 'View')
                default.protect_get('set', 'Override')
                default.protect_get('configure', 'Configure')
                default.protect_get('prune', 'Configure')
                default.protect_get('add_child', 'Configure')
                default.protect_set('name', 'Configure')
                default.protect_set('parent', 'Configure')
                default.protect_set('url', 'Configure')
                klass._default_security = default
            security_info = klass._default_security.copy()
        finally:
            klass._default_lock.release()
        return security_info
    from_default = classmethod(from_default)

    def __init__(self, defaultget = None, defaultset = None, defaultdel = None):
        self.getting_permissions = {}
        self.setting_permissions = {}
        self.deleting_permissions = {}
        self.defaultget = defaultget
        self.defaultset = defaultset
        self.defaultdel = defaultdel

    def make_private(self, name):
        self.getting_permissions[name] = "Private"
        self.setting_permissions[name] = "Private"
        self.deleting_permissions[name] = "Private"

    def make_public(self, name):
        self.getting_permissions[name] = "Public"
        self.setting_permissions[name] = "Public"
        self.deleting_permissions[name] = "Public"

    def protect(self, name, getpermission, setpermission = None, delpermission = None):
        self.getting_permissions[name] = getpermission
        self.setting_permissions[name] = setpermission
        self.deleting_permissions[name] = delpermission

    def allow_get(self, name):
        self.getting_permissions[name] = "Public"

    def allow_set(self, name):
        self.setting_permissions[name] = "Public"

    def allow_del(self, name):
        self.deleting_permissions[name] = "Public"

    def disallow_get(self, name):
        self.getting_permissions[name] = "Private"

    def disallow_set(self, name):
        self.setting_permissions[name] = "Private"

    def disallow_del(self, name):
        self.deleting_permissions[name] = "Private"

    def protect_get(self, name, permission):
        self.getting_permissions[name] = permission

    def protect_set(self, name, permission):
        self.setting_permissions[name] = permission

    def protect_del(self, name, permission):
        self.deleting_permissions[name] = permission

    def getting_permission(self, name):
        return self.getting_permissions.get(name, self.defaultget)

    def setting_permission(self, name):
        return self.setting_permissions.get(name, self.defaultset)

    def deleting_permission(self, name):
        return self.deleting_permissions.get(name, self.defaultdel)

    def copy(self):
        security_info = type(self)(self.defaultget, self.defaultset, self.defaultdel)
        security_info.getting_permissions = self.getting_permissions.copy()
        security_info.setting_permissions = self.setting_permissions.copy()
        security_info.deleting_permissions = self.deleting_permissions.copy()
        return security_info

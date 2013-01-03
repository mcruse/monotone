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
import types
import time
import inspect
from inspect import getmro
from inspect import isclass
from inspect import ismethod
from inspect import isfunction
from functools import wraps
from functools import update_wrapper
from mpx.lib import msglog
from mpx.componentry import Interface
from mpx.componentry import implements
from mpx.componentry import adapts
from mpx.componentry import register_adapter
from mpx.componentry import implemented_by
from mpx.componentry import provided_by
from mpx.componentry import directly_provides
from interfaces import IPermissionChecker
from interfaces import ISecure
from interfaces import IUser
from interfaces import ISecurityContext
from declarations import SecurityInformation
from declarations import get_security_info
from mpx.lib.exceptions import Unauthorized
from mpx.lib.exceptions import Forbidden

class Timer(object):
    class Call(object):
        def __init__(self):
            self.count = 0
            self.tlapse = 0
        def touch(self, tlapse):
            self.count += 1
            self.tlapse += tlapse
        def average(self):
            return self.tlapse / self.count
    def __init__(self, *args):
        self.calls = {}
    def __call__(self, name, tlapse):
        self.calls.setdefault(name, Timer.Call()).touch(tlapse)
    def summarize(self):
        for name, timer in self.calls.items():
            SecuredAdapter.debug_out('Method "%s" called %s time, average %s seconds per call.' % (name, timer.count, timer.average()))

timer = Timer()

def secured_method(bastion, method):
    """
        Invokes method within context of Security Bastion.
        
        Note, this option has serious impact on performance and 
        should generally be skipped as it's generally excessive.
    """
    @wraps(method)
    def invoke(*args, **kw):
        return method.im_func(bastion, *args, **kw)
    return invoke

def secured_function(bastion, function):
    secure = type(bastion).get_instattr(bastion, "__secure")
    @wraps(function)
    def invoke(*args, **kw):
        return secure(function(*args, **kw))
    return invoke

def secured_callable(bastion, callable_object):
    secure = type(bastion).get_instattr(bastion, "__secure")
    def call(*args, **kw):
        return secure(callable_object(*args, **kw))
    if ismethod(callable_object) or isfunction(callable_object):
        update_wrapper(call, callable_object)
    return call

class SecuredAdapter(object):
    implements(ISecure)
    adapts(None, IUser)
    debug = False
    SETTERS = set(["__setattr__", "setattr"])
    DELETERS = set(["__delattr__", "delattr"])
    GETTERS = set(["__getattr__","__getattribute__","getattr","get_method"])
    def should_mangle(name):
        return name.startswith('__') and not name.endswith('__')
    should_mangle = staticmethod(should_mangle)

    def debug_out(klass, message):
        if klass.debug:
            print message
    debug_out = classmethod(debug_out)

    def is_mangled(klass, name):
        return name.startswith('_%s__' % klass.__name__)
    is_mangled = classmethod(is_mangled)

    def post_mangling(klass, name):
        if klass.should_mangle(name):
            name = '_%s%s' % (klass.__name__, name)
        return name
    post_mangling = classmethod(post_mangling)

    def get_classattr(klass, name):
        name = klass.post_mangling(name)
        return type.__getattribute__(klass, name)
    get_classattr = classmethod(get_classattr)

    def del_classattr(klass, name):
        name = klass.post_mangling(name)
        return type.__delattr__(klass, name)
    del_classattr = classmethod(del_classattr)

    def set_classattr(klass, name, value):
        name = klass.post_mangling(name)
        return type.__setattr__(klass, name, value)
    set_classattr = classmethod(set_classattr)

    def get_instattr(klass, instance, name):
        name = klass.post_mangling(name)
        return object.__getattribute__(instance, name)
    get_instattr = classmethod(get_instattr)

    def del_instattr(klass, instance, name):
        name = klass.post_mangling(name)
        return object.__delattr__(instance, name)
    del_instattr = classmethod(del_instattr)

    def set_instattr(klass, instance, name, value):
        name = klass.post_mangling(name)
        return object.__setattr__(instance, name, value)
    set_instattr = classmethod(set_instattr)

    def __init__(self, context, user):
        set_instattr = SecuredAdapter.set_instattr
        get_instattr = SecuredAdapter.get_instattr
        set_instattr(self, '__user', user)
        set_instattr(self, '__context', context)
        set_instattr(self, '__checker', IPermissionChecker(context))
        set_instattr(self, '__attr_cache', {})
        set_instattr(self, '__caching', True)
        set_instattr(self, '__initialized', True)
        checker = get_instattr(self, '__checker')
        checker.set_default_security(PermissionChecker.simplesecurity)
        if ISecure.providedBy(context):
            raise TypeError('Context already provides ISecure.')
        SecuredAdapter.debug_out('SecuredAdapter instantiated: %s' % context)
    
    def __getattribute__(self, name):
        if name == 'set_caching':
            return SecuredAdapter.get_instattr(self, '__set_caching')
        if name == 'is_adaptable':
            return SecuredAdapter.get_instattr(self, '__is_adaptable')
        if name == 'test_adaptability':
            return SecuredAdapter.get_instattr(self, '__test_adaptability')
        if name in SecuredAdapter.GETTERS:
            return SecuredAdapter.get_instattr(self, "__getattribute__")
        if name in SecuredAdapter.SETTERS:
            return SecuredAdapter.get_instattr(self, "__setattr__")
        if name in SecuredAdapter.DELETERS:
            return SecuredAdapter.get_instattr(self, "__delattr__")
        caching = SecuredAdapter.get_instattr(self, '__caching')
        if caching:
            getfunction = SecuredAdapter.get_instattr(self, '__caching_getattribute')
        else:
            getfunction = SecuredAdapter.get_instattr(self, '__getattribute')
        return getfunction(name)

    def __set_caching(self, flag = True):
        SecuredAdapter.set_instattr(self, '__caching', flag)

    def __is_adaptable(self):
        try:
            SecuredAdapter.get_instattr(self, '__test_adaptability')()
        except: 
            return False
        return True

    def __test_adaptability(self):
        attributes = ['__providedBy__', '__provides__', '__class__', '__conform__']
        while attributes:
            try:
                while attributes:
                    getattr(self, attributes.pop(0))
            except AttributeError:
                continue
        return

    def __caching_getattribute(self, name):
        get_instattr = SecuredAdapter.get_instattr
        initialized = get_instattr(self, '__initialized')
        if not initialized or SecuredAdapter.is_mangled(name):
            return get_instattr(self, name)
        attr_cache = get_instattr(self, '__attr_cache')
        context = get_instattr(self, '__context')
        SecuredAdapter.debug_out('%s.%s' % (context, name))
        cached = attr_cache.has_key(name)
        try: attribute = getattr(context, name)
        except AttributeError:
            if cached:
                del(attr_cache[name])
            raise
        if cached:
            SecuredAdapter.debug_out('cached %s' % name)
            secured = get_instattr(self, '__secure')(attribute)
        else:
            checker = get_instattr(self, '__checker')
            authorize = get_instattr(self, '__authorize')
            authorize(checker.getting_permission, name)
            secured = get_instattr(self, '__secure')(attribute)
            attr_cache[name] = True
        return secured

    def __getattribute(self, name):
        get_instattr = SecuredAdapter.get_instattr
        initialized = get_instattr(self, '__initialized')
        if not initialized or SecuredAdapter.is_mangled(name):
            return get_instattr(self, name)
        context = get_instattr(self, '__context')
        SecuredAdapter.debug_out('%s.%s' % (context, name))
        attribute = getattr(context, name)
        checker = get_instattr(self, '__checker')
        authorize = get_instattr(self, '__authorize')
        authorize(checker.getting_permission, name)
        secured = get_instattr(self, '__secure')(attribute)
        return secured

    def __setattr__(self, name, value):
        get_instattr = SecuredAdapter.get_instattr
        set_instattr = SecuredAdapter.set_instattr
        initialized = get_instattr(self, '__initialized')
        if not initialized or SecuredAdapter.is_mangled(name):
            return set_instattr(self, name, value)
        checker = get_instattr(self, '__checker')
        authorize = get_instattr(self, '__authorize')
        authorize(checker.setting_permission, name)
        context = get_instattr(self, '__context')
        result = setattr(context, name, value)
        return result

    def __delattr__(self, name):
        get_instattr = SecuredAdapter.get_instattr
        del_instattr = SecuredAdapter.del_instattr
        initialized = get_instattr(self, '__initialized')
        if not initialized or SecuredAdapter.is_mangled(name):
            return del_instattr(self, name)
        context = get_instattr(self, '__context')
        attribute = getattr(context, name)
        checker = get_instattr(self, '__checker')
        authorize = get_instattr(self, '__authorize')
        authorize(checker.deleting_permission, name)
        return delattr(context, name)

    def __secure(self, response, context = None, user = None):
        if isinstance(response, (int, float, str, file)):
            SecuredAdapter.debug_out(
                '__secure(%s) => %s directly (simple type).' % (response, response))
            return response

        get_instattr = SecuredAdapter.get_instattr
        if user is None:
            user = get_instattr(self, '__user')
        if context is None:
            context = get_instattr(self, '__context')
        securefunc = get_instattr(self, '__secure')

        if isinstance(response, (list, tuple)):
            return [securefunc(item, context, user) for item in response]
        if isinstance(response, dict):
            tuplist = [(securefunc(key, context, user),
                        securefunc(value, context, user))
                        for key, value in response.items()]
            return dict(tuplist)
        ##
        # Using inspect insmethod to catch non-object callables.
        # For speed, this is done before ISecurityContext testing
        # based on the assumption that ismethod is a much faster 
        # call *and* that most often, at this point, callables 
        # will be methods.
        if ISecurityContext.providedBy(response):
            return SecuredAdapter(response, user)
        if isclass(response):
            return response
        if callable(response):
            return secured_callable(self, response)
        SecuredAdapter.debug_out(
            '__secure(%s) => %s directly.  Unknown type.' % (response, response))
        return response

    def __authorize(self, permission_func, attrname):
        permission = permission_func(attrname)
        if permission in (None, "Private"):
            error = 'Forbidden action.  Permission: %s.'
            raise Forbidden(error % permission)
        elif permission == "Public":
            return True
        get_instattr = SecuredAdapter.get_instattr
        user = get_instattr(self, '__user')
        context = get_instattr(self, '__context')
        policies = user.parent.parent.policy_manager.get_context_policies(context)
        if not policies:
            error = 'Forbbiden action.  No policy at context: %s.'
            raise Forbidden(error % context)
        roles = user.get_roles()
        if not roles:
            error = 'User "%s" has no roles.'
            raise Unauthorized(error % user.name)
        permissions = []
        for policy in policies:
            rolepermissions = map(policy.get_permissions, roles)
            map(permissions.extend, rolepermissions)
        valid_permissions = get_instattr(self, '_permissions_valid')
        if not valid_permissions(permission, permissions):
            if not isinstance(context, str):
                try: context = context.url
                except: pass
            error = '"%s" does not have required permission "%s." at context "%s".'
            raise Unauthorized(error % (user.name, permission, context))
        return True
    
    def _permissions_valid(self, required, available):
        if required == 'Manage Users': 
            return (required in available)
                
        permissions = {'Configure': 2, 'Override': 1, 'View': 0}
        max_permission_available = -1
        required_permission = permissions[required]
        if 'Configure' in available:
            max_permission_available = permissions['Configure']
        elif 'Override' in available:
            max_permission_available = permissions['Override']
        elif 'View' in available:
            max_permission_available = permissions['View']
        elif required in available:
            return True
            
        if required_permission <= max_permission_available:
            return True
        else: return False
            

class PermissionChecker(object):
    implements(IPermissionChecker)
    adapts(None)
    simplesecurity = SecurityInformation.from_default()

    def __init__(self, context):
        self.context = context
        self.fallback_informer = None
        self._setup_informers()

    def set_default_security(self, fallback = None):
        self.fallback_informer = fallback

    def _setup_informers(self):
        informers = []
        ##
        # Uses object type's MRO to compile all security assertions
        #   about object's attributes, including those attributes and
        #   assertions originating in the class's hierarchy.  The most
        #   recent assertion about an attribute is the assertion which
        #   is applied, allowing subclasses to "override" assertions of
        #   their super classes.  Checking starts with object itself so
        #   object-specific security can override that inherited from its
        #   class.
        #
        #   NOTE: Although the object takes precedence, the class's
        #   security declaration is still used; this may or may not be as
        #   expected.
        ##
        for object in (self.context,) + getmro(type(self.context)):
            securityinfo = get_security_info(object, None)
            if securityinfo is not None:
                if len(informers) == 0:
                    informers.append(securityinfo)
                elif informers[-1] is not securityinfo:
                    # Prevent duplicate entries caused by inheritence.
                    informers.append(securityinfo)
        self._informers = informers

    def getting_permission(self, attribute):
        informers = self._informers[:]
        if not informers and self.fallback_informer is not None:
            informers.append(self.fallback_informer)
        for informer in informers:
            permission = informer.getting_permission(attribute)
            if permission:
                return permission
        return None

    def setting_permission(self, attribute):
        informers = self._informers[:]
        if not informers and self.fallback_informer is not None:
            informers.append(self.fallback_informer)
        for informer in informers:
            permission = informer.setting_permission(attribute)
            if permission:
                return permission
        return None

    def deleting_permission(self, attribute):
        informers = self._informers[:]
        if not informers and self.fallback_informer is not None:
            informers.append(self.fallback_informer)
        for informer in informers:
            permission = informer.deleting_permission(attribute)
            if permission:
                return permission
        return None

register_adapter(SecuredAdapter)
register_adapter(PermissionChecker)

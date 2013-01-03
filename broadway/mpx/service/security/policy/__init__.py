"""
Copyright (C) 2007 2009 2010 2011 Cisco Systems

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
import re
import urllib
from threading import RLock
from threading import Event
from mpx.lib import security
from mpx.lib import msglog
from mpx.lib.exceptions import EConfigurationIncomplete, EInvalidValue
from mpx.lib.exceptions import EConfigurationInvalid
from mpx.lib.exceptions import ENotRunning
from mpx.lib.neode.node import ConfigurableNode
from mpx.service.security import SecurityService
from mpx.lib.configure import as_boolean
from mpx.componentry import implements
from mpx.componentry.security.interfaces import ISecurityContext
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from interfaces import IPolicyManager
from interfaces import IPolicy
import adapters
from mpx.lib.node._node import as_node

class PolicyManager(SecurityService):
    implements(IPolicyManager)
    security = SecurityInformation.from_default()
    secured_by(security)

    security.protect('add_child', 'Manage Users')
    security.protect('remove_child', 'Manage Users')
    security.protect('rename_child', 'Manage Users')

    def __init__(self, *args):
        self.__default = None
        self.__started = False
        super(PolicyManager, self).__init__(*args)

    def __get_default(self):
        if not self.__started:
            self.start()
        return self.__default
    default = property(__get_default)

    def get_permissions():
        return security.permissions[:]
    get_permissions = staticmethod(get_permissions)

    def get_policies(self):
        if not self.__started:
            self.start()
        return self.children_nodes()

    def get_policy(self, name):
        if not self.__started:
            self.start()
        return self.get_child(name)

    def has_policy(self, name):
        if not self.__started:
            self.start()
        return self.has_child(name)
    
    # to be used only by UI to determine  if the
    # logged in user should be allowed to view
    # all the nodes or not based on the permissions.
    security.protect('is_manage_users_capable', 'Manage Users')
    def is_manage_users_capable(self):
        return True    

    def get_context_policies(self, context, ascending = True):
        if not self.__started:
            self.start()
        if not isinstance(context, str):
            context = ISecurityContext(context).url
        active = []
        children = self.children_nodes()
        ranked = []
        for child in children:
            try:
                ranked.append((child.rank_match(context), child))
            except ENotRunning:
                # Only log once for consecutive failures.
                if (child.__ENotRunning_logged % 1000) == 0:
                    msglog.log('broadway', msglog.types.WARN,
                               'Policy "%s" not running.' % child.name)
                child.__ENotRunning_logged += 1
            else:
                child.__ENotRunning_logged = 0
        ranked.sort()
        ranked.reverse()
        for rank, child in ranked:
            if rank:
                active.insert(0, child)
            else:
                break
            if not child.acquires:
                break
        if not ascending:
            active.reverse()
        return active

    def start(self):
        if not self.__started:
            self.__started = True
            default = self.__create_default('Default', '/', ['name', 'context'])
            if self.role_manager.authenticated is not None:
                default.set_permissions(self.role_manager.authenticated, 'View')
            if self.role_manager.manager is not None:
                default.set_permissions(self.role_manager.manager, ['View', 'Configure', 'Override'])
            # Callback reference to static 'get_permissions' method means
            #   queries for assigned permissions of this role will return
            #   all defined permissions available.
            if self.role_manager.administrator is not None:
                default.set_permissions(self.role_manager.administrator, self.get_permissions)
            self.__default = default
            http = self.__create_default(
                'HTTP Files', 
                '/services/network/http_server/http_file_handler',
                ['name']
                )
            https = self.__create_default(
                'HTTPS Files', 
                '/services/network/https_server/https_file_handler',
                ['name']
                )
            super(PolicyManager, self).start()

    def add_child(self, child):
        result = super(PolicyManager, self).add_child(child)
        child.__ENotRunning_logged = 0
        return result

    def __create_default(self, policyname, context, readonly =()):
        if self.has_child(policyname):
            policy = self.get_child(policyname)
        else:
            policy = self.nodespace.create_node(Policy)
            msglog.log(
                'broadway', 
                msglog.types.INFO,
                'Policy Manager creating default policy "%s".' % policyname
                )
        config = {'parent': self, 'name': policyname, 'context': context, 'is_default': True}
        policy.configure(config)
        policy.readonly = list(readonly)
        return policy

##
# Masks usage of callback for generating list of permissions
#   dynamically.  The value can be a list of permissions, as
#   usual, or it may be a callable which will be invoked and
#   its returned value returned as the value when a key associated
#   with a callable value is accessed.
class _RoleMap(dict):
    def __getitem__(self, role):
        permissions = self.get(role, None)
        if permissions is None:
            raise KeyError(role)
        return permissions
    def get(self, role, default = []):
        permissions = super(_RoleMap, self).get(role, default)
        if callable(permissions):
            permissions = permissions()
        elif permissions:
            permissions = permissions[:]
        return permissions
    def callable_items(self):
        return [(role, permission) for role, permission
                in self.items() if callable(permission)]
    def callable_subset(self):
        return _RoleMap(self.callable_items())
    def callable_keys(self):
        return self.callable_subset().keys()
    def callable_values(self):
        return self.callable_subset().values()
    def copy(self):
        # This copy method written to replace callable values with
        #   their return values, so configuration dictionaries
        #   comeback with fully populated permissions.
        current = _RoleMap(self)
        roles = current.keys()
        permissions = map(current.get, roles)
        return _RoleMap(zip(roles, permissions))

class Policy(ConfigurableNode):
    implements(IPolicy)
    security = SecurityInformation.from_default()
    secured_by(security)
    security.protect('context', 'Manage Users')
    security.protect('acquires', 'Manage Users')
    security.protect('rolemap', 'Manage Users')
    security.make_private('readonly')
    def __init__(self, *args):
        self.readonly = []
        self.__lock = RLock()
        self.__active = Event()
        self.acquires = True
        self.context = ""
        self.filter = ""
        self.is_default = False
        self.uses_expression = False
        self.configured_expression = False
        self.rolemap = _RoleMap()
        super(Policy, self).__init__(*args)
        
    def get_readOnly(self,attr):
        return attr in self.readonly
            
    security.protect('configure', 'Manage Users')
    def configure(self, config):
        """
            Configure node with from configuration dictionary.
            
            The policy may be configured to use regular expressions 
            instead of simple node-URL contexts in two different ways.
            
            The configuration dictionary may include a True/False 
            value "uses_expression", in which case the context 
            regular expression is taken verbatim from the "context" 
            parameter, and an optional filter expression from the 
            "filter" parameter.
            
            Or the expression(s) may be encoded directly into the 
            "context" value using the following format:
            
            REGEX: '<context regex>', FILTER: '<filter regex>'
            
            Note that the ", FILTER: [...]" part is completely 
            optional and will default to no filter. 
        """
        for attrname in self.readonly:
            current = getattr(self, attrname, None)
            incoming = config.get(attrname)
            if None not in (current, incoming) and (current != incoming):
                message = 'Attribute "%s" is readonly for Policy "%s".  '
                message += 'Overriding new value %s with current value %s.'
                message = message % (attrname, self.name, incoming, current)
                msglog.log('broadway', msglog.types.WARN, message)
                config[attrname] = current
        self.acquires = as_boolean(config.get('acquires', self.acquires))
        if not self.is_default:
            self.is_default = as_boolean(config.get('is_default', False))
        self.configure_context(config)
        super(Policy, self).configure(config)
        # Getting set of mappings whose value is a callback function.
        #   The assumption is being made here that such mappings are
        #   those considered 'read-only.'
        self.__lock.acquire()
        try:
            inherent = self.rolemap.callable_subset()
            self.rolemap = _RoleMap(config.get('rolemap', self.rolemap))
            self.rolemap.update(inherent)
        finally: 
            self.__lock.release()
        self.__verify_setup()
        
    def configure_context(self, config):
        context = config.get('context', self.context)
        if not context:
            raise TypeError("Policy must have non-empty context")
        if config.has_key("uses_expression"):
            self.uses_expression = as_boolean(config["uses_expression"])
        else:
            self.uses_expression = False
        if self.uses_expression:
            self.context = context
            if config.has_key("filter"):
                self.filter = config["filter"]
            self.configured_expression = True
        else:
            self.configured_expression = False
            if isinstance(context, str) and context.startswith("REGEX:"):
                self.uses_expression = True
                # Regular expression encoded into context 
                # as "REGEX: '<expr>', FILTER: '<expr>'.
                REGEX,FILTER = "REGEX","FILTER"
                expressions = eval("{%s}" % context)
                self.context = expressions.get(REGEX, "")
                self.filter = expressions.get(FILTER, "")
            elif context != self.context:
                if not isinstance(context, str):
                    if ISecurityContext.providedBy(context):
                        context = context.url
                    else:
                        raise TypeError("Context must be string or object"
                                        " providing ISecurityContext.")
                self.filter = ""
                self.context = context
        return self.context,self.filter
    def context_configuration(self, config):
        if self.configured_expression:
            config["context"] = self.context
            config["filter"] = self.filter
            config["uses_expression"] = "1"
        elif self.uses_expression:
            context = "REGEX: %r, FILTER: %r" % (self.context, self.filter)
            config["context"] = context
        else:
            config["context"] = self.context
        return config
    def configuration(self):
        config = super(Policy, self).configuration()
        config['acquires'] = str(self.acquires)
        config['is_default'] = as_boolean(self.is_default)
        self.context_configuration(config)
        self.__lock.acquire()
        try:
            config['rolemap'] = self.rolemap.copy()
        finally: 
            self.__lock.release()
        return config
    def start(self):
        if not self.context:
            raise TypeError("Policy must have non-empty context")
        self.__lock.acquire()
        try:
            self.__verify_setup()
            self.__active.set()
        finally: 
            self.__lock.release()
        super(Policy, self).start()
    def stop(self):
        if not self.parent.default is self:
            self.__active.clear()
        else:
            message = 'Policy "%s" is system default and has ' % self.name
            message += 'not been deactivated, although it has been stopped.'
            msglog.log('broadway', msglog.types.WARN, message)
        super(Policy, self).stop()
    def is_running(self):
        return self.__active.isSet()
    def is_removable(self):
        return not len(self.readonly)
    def is_configurable(self):
        return not self.is_default   
    security.protect('prune', 'Manage Users')
    def prune(self):
        if not self.is_removable():
            error = '%s "%s" is not removable.'
            raise TypeError(error % (type(self).__name__, self.name))
        return super(Policy, self).prune()
    def __verify_setup(self):
        try:
            node = as_node(self.context)
        except:
            raise EInvalidValue("Invalid Context",  "%s" % self.context)
        policies = list(self.parent.get_policies())
        policies.remove(self)
        for policy in policies:
            if policy.uses_expression != self.uses_expression:
                continue
            if policy.context != self.context:
                continue
            # Policy contexts are same.
            message = ("Conflicting policy configurations detected."
                       "Policies %s and %s have same context: '%s'.")
            msglog.log("broadway", msglog.types.WARN, 
                       message % (self, policy, self.context))
            if policy.is_running():
                message = "Running policy '%s' already has context: %s"
                raise TypeError(message % (policy.name, self.context))
            else:
                message = ("%s ignoring context conflict: "
                           "conflicting policy is not running.")
                msglog.log("broadway", msglog.types.WARN, message % self)
        permissions = self.parent.get_permissions()
        rolemap = self.rolemap.copy()
        for role, granted in rolemap.items():
            if not self.parent.parent.role_manager.has_role(role):
                message = 'Policy "%s" ' % self.url
                message += 'removing role "%s".  ' % role
                message += 'It does not exist.'
                msglog.log('broadway', msglog.types.WARN, message)
                del(self.rolemap[role])
            elif isinstance(granted, (list, tuple)):
                for permission in granted:
                    if permission not in permissions:
                        message = 'Policy "%s" ' % self.url
                        message += 'removing permission "%s" ' % permission
                        message += 'from role "%s".  ' % role
                        message += 'Permission does not exist.'
                        msglog.log('broadway', msglog.types.WARN, message)
                        self.rolemap[role].remove(permission)
        return
    def get_permissions(self, role):
        if not isinstance(role, str):
            role = role.name
        return self.rolemap.get(role)
    security.protect('set_permissions', 'Manage Users')
    def set_permissions(self, role, *permissions):
        ##
        # Permissions parameter can be one of three things:
        #   - A single list or tuple object, whose items will
        #       replace the permissions tuple.
        #   - A variable number of permission strings.
        #   - A single callable object which will be called
        #       and whose return value will be returned anytime
        #       the permissions for this role are queried.
        if not isinstance(role, str):
            role = role.name
        if len(permissions) == 1:
            if type(permissions[0]) in (list, tuple):
                permissions = permissions[0][:]
            elif callable(permissions[0]):
                permissions = permissions[0]
        if not self.parent.parent.role_manager.has_role(role):
            raise ValueError('Role "%s" does not exist.' % role)
        if isinstance(permissions, (list, tuple)):
            defined = self.parent.get_permissions()
            for permission in permissions:
                if permission not in defined:
                    raise ValueError('Permission "%s" not defined.' % permission)
        self.__lock.acquire()
        try:
            inherent = self.rolemap.callable_subset()
            self.rolemap[role] = permissions
            self.rolemap.update(inherent)
        finally: self.__lock.release()
        if inherent.has_key(role):
            message = 'Permissions for role "%s" in policy "%s" '
            message += 'cannot be changed.  An attempt has been ignored.'
            message = message % (role, self.name)
            msglog.log('broadway', msglog.types.WARN, message)
        return
    def rank_match(self, context):
        if not self.is_running():
            raise ENotRunning('Not started.  This may mean start failed.')
        if not isinstance(context, str):
            context = ISecurityContext(context).url
        if self.uses_expression:
            rank = self.rank_expression(context)
        else:
            rank = self.rank_overlap(context)
        return rank
    def rank_expression(self, context):
        context = urllib.unquote(context)
        match = re.match(self.context, context)
        if not match:
            count = 0
        elif self.filter and re.match(self.filter, context):
            count = 0
        else:
            matching = match.group()
            count = matching.count("/")
            if len(matching) > 1:
                count = count + 1
        return count
    def rank_overlap(self, context):
        context = urllib.unquote(context)
        if not context.startswith(self.context):
            count = 0
        else:
            count = self.context.count('/')
            if len(self.context) > 1:
                count = count + 1
        return count

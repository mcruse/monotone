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
from mpx.lib import msglog
from mpx.lib.neode.node import ConfigurableNode
from mpx.componentry import implements
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.service.security import SecurityService
from interfaces import IRoleManager
from interfaces import IRole
import adapters

class RoleManager(SecurityService):
    implements(IRoleManager)
    security = SecurityInformation.from_default()
    secured_by(security)
    security.protect('add_child', 'Manage Users')
    security.protect('remove_child', 'Manage Users')
    security.protect('rename_child', 'Manage Users')

    def __init__(self, *args):
        self.__unknown = None
        self.__authenticated = None
        self.__administrator = None
        self.__started = False
        super(RoleManager, self).__init__(*args)

    def __get_unknown(self):
        return self.__unknown
    unknown = property(__get_unknown)

    def __get_authenticated(self):
        return self.__authenticated
    authenticated = property(__get_authenticated)

    def __get_administrator(self):
        return self.__administrator
    administrator = property(__get_administrator)
    
    def __get_manager(self):
        return self.__manager
    manager = property(__get_manager)

    def get_roles(self):
        if not self.__started:
            self.start()
        children = self.children_nodes()
        return children

    def get_role(self, name):
        if not self.__started:
            self.start()
        child = self.get_child(name)
        return child

    def get_role_names(self):
        if not self.__started:
            self.start()
        names = self.children_names()
        return names

    def has_role(self, rolename):
        if not self.__started:
            self.start()
        return self.has_child(rolename)
    
    # to be used only by UI to determine  if the
    # logged in user should be allowed to view
    # all the nodes or not based on the permissions.
    security.protect('is_manage_users_capable', 'Manage Users')
    def is_manage_users_capable(self):
        return True

    def start(self):
        if not self.__started:
            self.__started = True
            self.__unknown = self.__create_default('Unknown')
            self.__authenticated = self.__create_default('Operator')
            self.__manager = self.__create_default('Manager')
            self.__administrator = self.__create_default('System Administrator')
            super(RoleManager, self).start()

    def __create_default(self, rolename, readonly = ['name']):
        if self.has_role(rolename):
            role = self.get_role(rolename)
        else:
            role = self.nodespace.create_node(Role)
            msglog.log('broadway', msglog.types.INFO,
                       'Role Manager created default role: "%s"' % rolename)
        config = {'parent': self, 'name': rolename}
        role.configure(config)
        role.readonly = readonly
        return role

class Role(ConfigurableNode):
    implements(IRole)
    security = SecurityInformation.from_default()
    secured_by(security)
    security.protect_set('name', 'Manage Users')
    security.make_private('readonly')

    def __init__(self, *args):
        self.readonly = []
        super(Role, self).__init__(*args)

    security.protect('configure', 'Manage Users')
    def configure(self, config):
        for attrname in self.readonly:
            current = getattr(self, attrname, None)
            incoming = config.get(attrname)
            if None not in (current, incoming) and (current != incoming):
                message = 'Attribute "%s" is readonly for Role "%s".  '
                message += 'Overriding new value %s with current value %s.'
                message = message % (attrname, self.name, incoming, current)
                msglog.log('broadway', msglog.types.WARN, message)
                config[attrname] = current
        self.description = config.get('description', '')
        return super(Role, self).configure(config)

    def configuration(self):
        config = super(Role, self).configuration()
        config['description'] = self.description
        return config

    def is_removable(self):
        return not len(self.readonly)

    def is_configurable(self):
        #roles are not configurable
        return False
    
    security.protect('prune', 'Manage Users')
    def prune(self):
        affected=['roles']
        if not self.is_removable():
            error = '%s "%s" is not removable.'
            raise TypeError(error % (type(self).__name__, self.name))
        for user in self.parent.parent.user_manager.get_users():
            if self.name in user.roles:
                temp =user.roles
                temp.remove(self.name)
                user.set_roles(temp)
                if 'users' not in affected:
                    affected.append('users')
        
        for policy in self.parent.parent.policy_manager.get_policies():
            if self.name in policy.rolemap:
                policy.rolemap.pop(self.name)
                if 'policies' not in affected:
                    affected.append('policies')
                

        #if role is associated, then more than one pdo must be changed, thus we send a list of items that are changed
        #else we just return as before
        if len(affected)>1:
            super(Role, self).prune()
            return affected
        else:
            return super(Role, self).prune()
            
         

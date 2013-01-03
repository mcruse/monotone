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
from mpx.componentry import implements
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.node import as_internal_node
from mpx.lib.configure import as_boolean
from mpx.componentry import query_multi_adapter
from mpx.componentry.security import ISecure
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.neode.node import CompositeNode
from interfaces import ISecurityManager
from moab.user import manager as _manager

class SecurityManager(CompositeNode):
    implements(ISecurityManager)
    def __init__(self,*args,**kw):
        super(SecurityManager, self).__init__(*args, **kw)
    def as_secured_node(self, node_url, user=None, as_node_func=None, **kw):
        dereference = kw.get("dereference_aliases", False)
        if user is None:
            user = self.user_manager.user_from_current_thread()
        elif isinstance(user, str):
            user = self.user_manager.get_user(user)
        if as_node_func:
            node = as_node_func(node_url)
        elif (not dereference and 
              isinstance(node_url, str) and 
              node_url.startswith("/aliases")):
            try:
                node = as_internal_node(node_url)
            except ENoSuchName:
                node = self.nodespace.as_node(node_url)
        else:
            node = self.nodespace.as_node(node_url)
        configurable = IConfigurableNode(node)
        return query_multi_adapter((configurable, user), ISecure)

    def configure(self, config):
        self.setattr('pw_not_username', as_boolean(config.get('pw_not_username', _manager.password_config.getboolean('Prohibited', 'username_as_password'))))
        self.setattr('pw_min_len_root', int(config.get('pw_min_len_root', _manager.password_config.getint('Length', 'minadmin'))))
        self.setattr('pw_no_repeat', as_boolean(config.get('pw_no_repeat', _manager.password_config.getboolean('Complexity', 'no_repeats'))))
        self.setattr('pw_complexity', as_boolean(config.get('pw_complexity', _manager.password_config.getboolean('Complexity', 'character_sets'))))
        self.setattr('pw_min_len', int(config.get('pw_min_len', _manager.password_config.getint('Length', 'min'))))
        self.setattr('pw_max_len', int(config.get('pw_max_len', _manager.password_config.getint('Length', 'max'))))
        self.setattr('pw_not_cisco', as_boolean(config.get('pw_not_cisco', _manager.password_config.getboolean('Prohibited', 'cisco'))))
        self.setattr('pw_not_mpxadmin', as_boolean(config.get('pw_not_mpxadmin', _manager.password_config.getboolean('Prohibited', 'mpxadmin'))))
        super(SecurityManager, self).configure(config)

        if not self.has_child('Roles'):
            from mpx.service.security.role import RoleManager
            manager = self.nodespace.create_node(RoleManager)
            manager.configure({'name': 'Roles',
                               'parent': self,
                               'debug': self.debug})
            self.message('Created Role Manager.')
        if not self.has_child('Users'):
            from mpx.service.security.user import UserManager
            manager = self.nodespace.create_node(UserManager)
            manager.configure({'name': 'Users',
                               'parent': self,
                               'debug': self.debug})
            self.message('Created User Manager.')
        if not self.has_child('Policies'):
            from mpx.service.security.policy import PolicyManager
            manager = self.nodespace.create_node(PolicyManager)
            manager.configure({'name': 'Policies',
                               'parent': self,
                               'debug': self.debug})
            self.message('Created Policy Manager.')
        return

    def configuration(self):
        config = super(SecurityManager, self).configuration()
        config['pw_not_username'] = str(self.getattr('pw_not_username'))
        config['pw_min_len_root'] = str(self.getattr('pw_min_len_root'))
        config['pw_no_repeat'] = str(self.getattr('pw_no_repeat'))
        config['pw_complexity'] = str(self.getattr('pw_complexity'))
        config['pw_min_len'] = str(self.getattr('pw_min_len'))
        config['pw_max_len'] = str(self.getattr('pw_max_len'))
        config['pw_not_cisco'] = str(self.getattr('pw_not_cisco'))
        config['pw_not_mpxadmin'] = str(self.getattr('pw_not_mpxadmin'))
        return config
    def start(self):
        self.message('Security Manager starting.')

        _manager.password_config.set('Length', 'min', str(self.getattr('pw_min_len')))
        _manager.password_config.set('Length', 'max', str(self.getattr('pw_max_len')))
        _manager.password_config.set('Length', 'minadmin', str(self.getattr('pw_min_len_root')))
        _manager.password_config.set('Complexity', 'character_sets', str(self.getattr('pw_complexity')))
        _manager.password_config.set('Complexity', 'no_repeats', str(self.getattr('pw_no_repeat')))
        _manager.password_config.set('Prohibited', 'cisco', str(self.getattr('pw_not_cisco')))
        _manager.password_config.set('Prohibited', 'mpxadmin', str(self.getattr('pw_not_mpxadmin')))
        _manager.password_config.set('Prohibited', 'username_as_password', str(self.getattr('pw_not_username')))
        super(SecurityManager, self).start()
        self.message('Security Manager startup complete.')
    def __get_user_manager(self):
        return self.get_child('Users')
    def __get_role_manager(self):
        return self.get_child('Roles')
    def __get_policy_manager(self):
        return self.get_child('Policies')
    user_manager = property(__get_user_manager)
    role_manager = property(__get_role_manager)
    policy_manager = property(__get_policy_manager)

    def message(self, message, mtype = msglog.types.INFO):
        if (mtype != msglog.types.DB) or self.debug:
            msglog.log('broadway', mtype, message)
        return

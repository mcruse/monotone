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
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.exceptions import EDeleteActiveUser
from mpx.lib.exceptions import EUnreachableCode
from mpx.lib.node._node import as_node
from mpx.lib.node import as_internal_node
from moab.user.manager import PasswdFile
from moab.user.manager import GroupFile
from moab.user.manager import ShadowFile
from moab.user.manager import PasswdEntry
from moab.user.manager import GroupEntry
from moab.user.manager import ShadowEntry
from mpx.lib import msglog
from mpx.lib import threading
from mpx.lib.user import _User as OGUserObject
from mpx.lib.neode.node import ConfigurableNode
from mpx.service.security import SecurityService
from mpx.componentry import implements
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.lib.eventdispatch.dispatcher import Dispatcher
from mpx.lib.eventdispatch import Event
from interfaces import IUserManager
from interfaces import IUserEvent
from interfaces import IUser
import adapters
import re
import os
class UserEvent(Event):
    implements(IUserEvent)
    description = 'Generic User Event'
    def __init__(self, user, origin = None, guid = None):
        self.user = user
        super(UserEvent, self).__init__(user, origin, guid)

class UserPasswordModified(UserEvent):
    description = 'User password changed.'
    def __init__(self, user, password, previous = None, *args):
        self.password = password
        self.previous = previous
        super(UserPasswordModified, self).__init__(user, *args)

class UserRolesModified(UserEvent):
    description = 'User roles changed.'
    def __init__(self, user, roles, previous = None, *args):
        self.roles = roles
        self.previous = previous
        super(UserRolesModified, self).__init__(user, *args)

class UserManager(SecurityService):
    implements(IUserManager)
    security = SecurityInformation.from_default()
    secured_by(security)

    def __init__(self, *args):
        # This is required for use of older system, remove later...
        self.__system_lock = threading.Lock()
        self.__renaming_user = None
        self.__running = threading.Event()
        self.__sysadmin = None
        self.__anonymous = None
        super(UserManager, self).__init__(*args)

    def __get_sysadmin(self):
        return self.__sysadmin
    sysadmin = property(__get_sysadmin)

    def __get_anonymous(self):
        return self.__anonymous
    anonymous = property(__get_anonymous)

    def get_users(self):
        children = self.children_nodes()
        return children

    def get_user(self, name):
        child = self.get_child(name)
        return child

    def get_user_names(self):
        names = self.children_names()
        return names

    def has_user(self, username):
        return self.has_child(username)
    
    # to be used only by UI to determine  if the
    # logged in user should be allowed to view
    # all the nodes or not based on the permissions.
    security.protect('is_manage_users_capable', 'Manage Users')
    def is_manage_users_capable(self):
        return True    

    def user_from_object(self, userobject):
        if isinstance(userobject, User):
            username = userobject.name
        elif isinstance(userobject, OGUserObject):
            username = userobject.name()
            if username == 'NoneUser':
                username = 'Anonymous'
        elif userobject is None:
            username = 'Anonymous'
        else:
            error = 'User object can be type: User, OGUserObject, or None.  '
            error += 'Not %s.' % type(userobject)
            raise TypeError(error)
        try:
            return self.get_user(username)
        except ENoSuchName, e:
            # TODO:  Determine if this is the right place.
            #        Put in to handle Linux system user names that do not
            #        have security manager counterparts (nobody,mail,et al).
            from mpx.service.user_manager import EAuthenticationFailed
            raise EAuthenticationFailed()
        raise EUnreachableCode()

    def user_from_current_thread(self):
        current_thread = threading.currentThread()
        active_request = getattr(current_thread, 'active_request', None)
        if active_request is None:
            raise TypeError('Current thread must be HTTP(S) request.')
        userobject = active_request.user_object()
        return self.user_from_object(userobject)

    def start(self):
        super(UserManager, self).start()
        # @TODO The "create_default" line violates EDCS-562669 and needs to be refactored
        self.__sysadmin = self.__create_default('mpxadmin', '')
        self.__sysadmin.set_roles(self.role_manager.administrator)
        self.__anonymous = self.__create_default('Anonymous', '')
        self.__anonymous.set_roles(self.role_manager.unknown)
        self.__system_lock.acquire()
        try:
            users = self.get_users()
            for user in users:
                self.__synchronize_system(user, validate=True)
            self.__running.set()
        finally:
            self.__system_lock.release()

    def stop(self):
        self.__system_lock.acquire()
        self.__running.clear()
        self.__system_lock.release()
        super(UserManager, self).stop()

    security.protect('add_child', 'Manage Users')
    def add_child(self, user):
        result = super(UserManager, self).add_child(user)
        if not self.__renaming_user is user:
            if not hasattr(user, '__subid'):
                user.__subid = user.dispatcher.register_for_type(
                    self._handle_event, UserEvent)
            try:
                self.synchronize_system_files(user)
            except:
                message = 'Adding user "%s" to system failed.  See traceback.'
                msglog.log('broadway', msglog.types.ERR, message % user.name)
                msglog.exception(prefix = 'Handled')
        return result

    security.protect('remove_child', 'Manage Users')
    def remove_child(self, user, name = None):
        username = name
        if username is None:
            username = user.name
        if not self.__renaming_user is user:
            if hasattr(user, '__subid'):
                user.dispatcher.unregister(user.__subid)
                user.__subid = None
            try:
                self.synchronize_system_files(None, username)
            except KeyError:
                message = 'Removing user "%s" from the system failed.  '
                message += 'No such system user was found.  Traceback follows.'
                msglog.log('broadway', msglog.types.ERR, message % username)
                msglog.exception(prefix = 'Handled')
        return super(UserManager, self).remove_child(user, name)

    security.protect('rename_child', 'Manage Users')
    def rename_child(self, usernode, oldname):
        if not self.__running.isSet():
            message = 'Cannot rename user because User Manager is not running.'
            raise TypeError(message)
        self.__renaming_user = usernode
        try:
            result = super(UserManager, self).rename_child(usernode, oldname)
            self.synchronize_system_files(usernode, oldname)
        finally:
            self.__renaming_user = None
        return result

    def synchronize_system_files(self, usernode, currentname = None):
        self.__system_lock.acquire()
        try:
            if self.__running.isSet():
                self.__synchronize_system(usernode, currentname)
        finally:
            self.__system_lock.release()
        return

    def _handle_event(self, event):
        user = event.user
        self.synchronize_system_files(user)

    ##
    # Usernode is reference to user node object the system should be
    #   synchronized to.  If 'currentname' is provided and not None,
    #   then the user entry is retreived by 'currentname' rather than
    #   usernode.name; this allows renaming operations to take place.
    #   Method return boolean indication whether unsaved system changes exist.
    def __synchronize_system(self, usernode, currentname = None,
                             validate = True):
        system_users = PasswdFile()
        system_shadow = ShadowFile()
        system_groups = GroupFile()
        userchange = False
        shadowchange = False
        groupchange = False
        group_is_private = False
        system_users.load()
        system_shadow.load()
        system_groups.load()
        flag = 0
        #flag will be used to check if system admin is 
        #being demoted. bug CSCth82465
        #if system admin is being demoted, 
        #it's entry will be removed and added again

        if usernode and usernode.name in system_users:
                userentry = system_users[usernode.name]

#user is a system administrator, but not mpxadmin, 
#and it's current role is not mpxadmin
#i.e. a system administrator other than mpxadmin is being demoted
                if userentry.user_type() == 'mpxadmin' \
                        and usernode.name != 'mpxadmin' \
                        and self.role_manager.administrator.name not in usernode.roles:
                    flag = 1
                    
        if usernode is None or flag:
            # If no usernode is provided, the user with name 'currentname' is
            #   being removed.
            if flag:
                currentname = usernode.name
            if currentname is None:
                raise ValueError('Name must be provided when removing user.')
            userentry = system_users[currentname]

            # Loop through all groups to which user belongs, removing user.
            groups = userentry.groups(system_groups)
            for groupentry in groups:
                users = groupentry.user_list()
                # User is not in user list of private group, so only
                #   groups in to which user *also* belongs are modified.
                if currentname in users:
                    users.remove(currentname)
                    groupentry.user_list(users)
                    groupchange = True
                    message = 'removed user "%s" from group "%s".'
                    self.output_message(
                        message % (currentname, groupentry.group()))

            # If a private group was associated with the user--a group
            #   whose name is the same as the user name and whose member
            #   list contains no entries--find and remove it to keep clean.
            if currentname in system_groups:
                groupentry = system_groups[currentname]
                if len(groupentry.user_list()) == 0:
                    # Private group for user entry, remove it.
                    del(system_groups[currentname])
                    groupchange = True
                    self.output_message(
                        'removed private group "%s".' % currentname)
                    
            # Finally, delete user itself.
            del(system_users[userentry.user()])
            userchange = True

            # delete user details from /etc/shadow
            del(system_shadow[userentry.user()])
            shadowchange = True
            self.output_message('removed user "%s" from system.' % currentname)
            
            #delete user from the cache
            as_node('/services/User Manager').remove_user(currentname)
            
        if usernode:
            username = usernode.name
            # Name may be being changed.  Node reference always has correct
            #   name, where 'currentname' is the previous name if the name
            #   is in fact being changed.  Rename child operations take
            #   advantage of this.
            if currentname is None:
                currentname = username
            if currentname in system_users:
                # User already exists, must be being updated.
                fd=open("/etc/group","r")
                userentry = system_users[currentname]
                userid = userentry.uid()
                groupid = userentry.gid()
                flag = 1
                for line in fd.readlines():
                    if re.search(str(groupid),line,re.IGNORECASE) != None:
                        flag = 0
                        break
                if flag:
                    cmd = "addgroup -g "
                    cmd += str(groupid)
                    cmd += " "
                    cmd += currentname 
                    os.system(cmd)
                    flag = 0
                groupentry = system_groups[groupid]
                shadowentry = system_shadow[currentname]
            else:
                # User is completely new and user and private group
                #   must be created.
                userid = system_users.new_uid()
                while userid in system_groups:
                    userid = system_users.new_uid(userid)
                else:
                    groupid = userid
                userentry = PasswdEntry()
                groupentry = GroupEntry()
                shadowentry = ShadowEntry()
                message = 'creating user "%s" and group "%s".'
                self.output_message(message % (username, username))

            # A private group has the same name as the associated
            #   user account.
            group_is_private = False
            if groupentry.group() == userentry.user():
                group_is_private = True

            # If username has changed: change entry and flag.
            if userentry.user() != username:
                groups = []
                if userentry.user() is not None:
                    # New users cause exception when doing
                    #   group lookup before name is set.
                    groups = userentry.groups(system_groups)
                currentname = userentry.user()
                userentry.user(username, validate)
                userchange = True
                shadowentry.user(username, validate)
                shadowchange = True
                message = 'changed user name from "%s" to "%s".'
                self.output_message(message % (currentname, username))
                # Modify groups to which user belongs to reflect updated name.
                for group in groups:
                    users = group.user_list()
                    if currentname in users and username not in users:
                        users[users.index(currentname)] = username
                        group.user_list(users)
                        groupchange = True
                        message = 'changed user "%s" in group "%s" to "%s".'
                        self.output_message(
                            message % (currentname, group.group(), username))

            # If group is only for this user and group name isn't username,
            #   change and flag.
            if group_is_private and groupentry.group() != username:
                currentgroup = groupentry.group()
                groupentry.group(username)
                groupchange = True
                message = 'changed group name from "%s" to "%s".'
                self.output_message(message % (currentgroup, username))

            # Change user-entry's password if doesn't match user node's.
            password = usernode.password
            if len(password) and not shadowentry.password_matches_crypt(password):
                shadowentry.user(username, validate)
                shadowentry.passwd(password, validate)
                userentry.passwd('x', False)
                shadowentry.lstchg()
                shadowchange = True
                userchange = True
                self.output_message(
                    'changed password for user "%s".' % username)

            # Set user-entry UID to calulated UID (used for new entries).
            if not userentry.uid() == userid:
                currentuid = userentry.uid()
                userentry.uid(userid)
                userchange = True
                message = 'changed UID for user "%s" from %s to %s.'
                self.output_message(message % (username, currentuid, userid))

            # Set user-entry GID to calculated GID (used for new entries).
            if userentry.gid() != groupid:
                currentgid = userentry.gid()
                userentry.gid(groupid)
                userchange = True
                message = 'changed GID for user "%s" from %s to %s.'
                self.output_message(message % (username, currentgid, groupid))
            
            if not userentry.gecos():
                currentgecos = userentry.gecos()
                userentry.gecos('ROLE=user')
                userchange = True
                message = 'changed gecos for user "%s" from %s to %s.'
                self.output_message(message % (username, currentgecos, 'ROLE=user'))

            # Set group-entry GID to calculated GID (should match whether private or not).
            if groupentry.gid() != groupid:
                currentgid = groupentry.gid()
                groupentry.gid(groupid)
                groupchange = True
                message = 'changed GID for group "%s" from %s to %s.'
                self.output_message(
                    message % (groupentry.group(), currentgid, groupid))

            if userchange:
                # Passwd file changed, set user into user dicationary
                #   in case user was newly created, and save back file.
                system_users[userentry.user()] = userentry
                system_users.save()
                userchange = False
                as_node('/services/User Manager').remove_user(usernode.name)

            if shadowchange:
                # /etc/shadow file changed, set user into user dicationary
                #   in case user was newly created, and save back file.
                system_shadow[shadowentry.user()] = shadowentry
                system_shadow.save()
                shadowchange = False

            if groupchange:
                # Group file changed, set user into groups dicationary
                #   in case group was newly created, and save back file.
                system_groups[groupentry.group()] = groupentry
                system_groups.save()
                groupchange = False

            roles = usernode.roles[:]
            if self.role_manager.administrator.name in roles:
                if userentry.user_type() != 'mpxadmin':
                    userchange = True
                    shadowchange = True
                    groupchange = True
                    userentry.user_type('mpxadmin', system_users, system_groups)
                    self.output_message('made user "%s" into "mpxadmin" type.' % username)
                    if username in system_groups:
                        group = system_groups[username]
                        if userentry.gid() != group.gid():
                            users = group.user_list()
                            if len(users) == 0:
                                del(system_groups[username])
                                groupchange = True
                                message = 'removed group "%s".  ' % username
                                message += 'Group no longer referenced.'
                            else:
                                message = 'not removing group "%s".  ' % username
                                message += 'Still has users %s.' % (users,)
                            self.output_message(message)
            elif userentry.user_type() == 'mpxadmin':
                message = 'System Administrator cannot be demoted.  '
                message += 'User "%s" must be removed in order to demote.'
                raise TypeError(message % username)

        if userchange:
            system_users.save()
            userchange = False
            username = usernode.name if usernode else currentname
            as_node('/services/User Manager').remove_user(username)

        if shadowchange:
            system_shadow.save()
            shadowchange = False
        if groupchange:
            system_groups.save()
            userchange = False
        return (userchange or groupchange or shadowchange)

    def __create_default(self, username, password, roles = [], readonly = ['name']):
        if self.has_user(username):
            user = self.get_user(username)
            password = user.password
        else:
            user = self.nodespace.create_node(User)
            self.output_message('created default user "%s".' % username)
        config = {'parent': self, 'name': username,
                  'password': password, 'roles': roles}
        user.configure(config)
        user.readonly = readonly
        return user

    def output_message(self, message, mtype = msglog.types.INFO):
        if mtype != msglog.types.DB or self.debug:
            msglog.log('broadway', mtype, 'User Manager: %s' % message)
        return

class User(ConfigurableNode):
    implements(IUser)
    security = SecurityInformation.from_default()
    secured_by(security)
    #security.protect('roles', 'Manage Users')
    security.make_private('readonly')
    def __init__(self, *args):
        self.dispatcher = Dispatcher()
        self._lock = threading.Lock()
        self.roles = []
        self.readonly = []
        self.homepage = '/'
        self.__password = ''
        self.description = ''
        super(User, self).__init__(*args)

    #security.protect('password', 'Manage Users')
    def __get_password(self):
        return self.__password
    def __set_password(self, password):
        previous = self.password
        self.__password = password
        if previous != self.password and self.parent is not None:
            event = UserPasswordModified(self, password, previous)
            self.dispatcher.dispatch(event)
        return
    password = property(__get_password, __set_password)

    security.protect('configure', 'View')
    def configure(self, config):
        for attrname in self.readonly:
            current = getattr(self, attrname, None)
            incoming = config.get(attrname)
            if None not in (current, incoming) and (current != incoming):
                message = 'Attribute "%s" is readonly for User "%s".  '
                message += 'Overriding new value %s with current value %s.'
                message = message % (attrname, self.name, incoming, current)
                msglog.log('broadway', msglog.types.WARN, message)
                config[attrname] = current
        self.description = config.get('description', self.description)
        self.homepage = config.get('homepage', self.homepage)
        # Ignoring password if all astericks.
        password = config.get('password', "")
        if config.has_key('old_password') and config.get('old_password') == '':
            raise Exception("Invalid Old Password")
        old_password = config.get('old_password', None)
        if password and (password != len(password) * '*'):
            system_users = PasswdFile()
            system_users.load()
            if old_password and config.get('name', '') in system_users:
                system_shadow = ShadowFile()
                system_shadow.load()
                shadowentry = system_shadow[config.get('name')]
                if not shadowentry.password_matches_crypt(old_password):
                    raise Exception("Invalid Old Password")
            self.__set_password(password)
            self.password = password
        super(User, self).configure(config)
        if config.has_key('roles'):
            self.set_roles(list(config.get('roles', self.roles)))

    def configuration(self):
        config = super(User, self).configuration()
        config['description'] = self.description
        config['homepage'] = self.homepage
        config['password'] = "********"
        config['roles'] = self.get_roles()
        return config

    def start(self):
        super(User, self).start()
        self._synchronize()

    def is_removable(self):
        return not len(self.readonly)

    def is_configurable(self):
        return True

    security.protect('prune', 'Manage Users')
    def prune(self):
        if not self.is_removable():
            error = '%s "%s" is not removable.'
            raise TypeError(error % (type(self).__name__, self.name))
        return super(User, self).prune()

    def _synchronize(self):
        self._lock.acquire()
        try:
            roles = self.roles[:]
            for role in roles:
                if not self.parent.role_manager.has_role(role):
                    message = 'User "%s" ' % self.url
                    message += 'removing role "%s".  ' % role
                    message += 'It does not exist.'
                    msglog.log('broadway', msglog.types.WARN, message)
                    self.roles.remove(role)
        finally: self._lock.release()

    security.protect('get_roles', 'View')
    def get_roles(self):
        return self.roles[:]

    security.protect('set_roles', 'Manage Users')
    def set_roles(self, *roles):
        # Allow roles to be list or tuple, or many params.
        if len(roles) == 1 and isinstance(roles[0], (list, tuple)):
            roles = roles[0][:]
        for role in roles:
            if not self.parent.parent.role_manager.has_role(role):
                raise ValueError('Role "%s" does not exist.' % role)
        rolenames = []
        for role in roles:
            if isinstance(role, str):
                rolenames.append(role)
            else: rolenames.append(role.name)

        if self.parent.anonymous is not self:
            authenticated = self.parent.role_manager.authenticated.name
            
        if self.parent.sysadmin is self:
            adminrole = self.parent.role_manager.administrator.name
            if adminrole not in rolenames:
                message = 'User "%s" is system admin.  Appending role "%s".'
                msglog.log('broadway', msglog.types.WARN,
                           message % (self.name, adminrole))
                rolenames.append(adminrole)
        elif self.parent.anonymous is self:
            unknownrole = self.parent.role_manager.unknown.name
            if unknownrole not in rolenames:
                message = 'User "%s" is anonymous.  Appending role "%s".'
                msglog.log('broadway', msglog.types.WARN,
                           message % (self.name, unknownrole))
                rolenames.append(unknownrole)
        self._lock.acquire()
        try:
            previous = self.roles
            if len(rolenames) == 0:
                unknownrole = self.parent.role_manager.unknown.name
                rolenames.append(unknownrole)
            self.roles = rolenames
        finally: self._lock.release()
        if self.roles != previous:
            event = UserRolesModified(self, self.roles, previous)
            self.dispatcher.dispatch(event)
        return


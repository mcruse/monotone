"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
import os as _os
import getpass as _getpass
import string as _string

from clu import CommandLineUtility, EArgument, EOption, EInput
from mpx.lib.exceptions import ENameInUse, ENotImplemented
from mpx.lib.log import log_names as _log_names
from mpx.lib.log import log as _log
from mpx.lib.log import trimming_log as _trimming_log

from clu import EArgument, EOption, EInput, SubCommand
from moab.user import manager as _manager

class UserMixin:
    def __init__(self):
        return
    def current_user(self):
        user = _getpass.getuser()
        if user == 'root':
            # @note Lots-o-super users, use the group id to differenciate...
            # @fixme There has got to be a better way. (like a mpxsudo).
            gid = _os.getgid()
            groups = _manager.GroupFile()
            groups.load()
            if gid in groups:
                return groups[gid].group()
            raise EArgument("Could not determine the specific super-user.")
        return user

class PasswdMixin(UserMixin):
    def __init__(self):
        UserMixin.__init__(self)
        self._password = None
        self.register_option('--password',
                             self._password_handler,
                             "Specify the user's login password.  If this"
                             " option is not specified, then the user is"
                             " prompted for the password.",
                             ['-p'])
        return
    def _password_handler(self, *args):
        self._password = self.pop_next()
        if self._password is None:
            raise EArgument('--password requires an argument.')
        return
    def password(self, user):
        if self._password is not None:
            return self._password
        p1 = _getpass.getpass("Enter a new password for %r: " % user)
        p2 = _getpass.getpass("Retype the new password: ")
        if not p1:
            raise EInput("Empty passwords are not allowed.")
        if p1 != p2:
            raise EInput("Entries did not match.")
        return p1

class User_List(SubCommand):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        self._valid_types = ('mpxadmin', 'mpxconfig', 'mpxuser',
                             'pppuser', 'webdev', 'none')
        self._types = list(self._valid_types)
        self._types.remove('none')
        self._long_output = 0
        self._one = 0
        self.register_option('--all',
                             self._all_handler, """\
List all users.  By default, only users whose type is not 'none' are listed.\
""",
                             ['-a'])
        self.register_option('--type',
                             self._type_handler, """\
List only users of a specific user type.\
""",
                             ['-t'])
        self.register_option('--long',
                             self._long_handler, """\
List information about the user, as well as the user name.\
""",
                             ['-l'])
        self.register_option('-1',
                             self._one_handler, """\
List names in a single column.  Useful for piping through grep, etc.""",[])
        return
    def _all_handler(self, *args):
        if 'none' not in self._types:
            self._types = list(self._valid_types)
        return
    def _one_handler(self, *args):
        self._one = 1
        return
    def _type_handler(self, *args):
        user_type = self.pop_next()
        if user_type is None:
            raise EArgument('%r requires an argument.' % args[0])
        if user_type not in self._valid_types:
            raise EArgument(
                "The argument to %r must be one of %r" % (args[0],
                                                          self._valid_types)
                )
        self._types = [user_type,]
        return
    def _long_handler(self, *args):
        self._long_output = 1
        return
    def __call__(self, *args):
        argv = self.arguments()
        if len(argv) != 0:
            raise EArgument(
                "mpxadmin list: No arguments are supported.\n"
                "               'mpxadmin user list --help' for more "
                "               information.")
        passwd_db = _manager.PasswdFile()
        passwd_db.load()
        group_db = _manager.GroupFile()
        group_db.load()
        users = []
        for user in passwd_db:
            if user.user_type() in self._types:
                users.append(user)
        def _cmp_by_name(u1, u2):
            return cmp(u1.user(),u2.user())
        users.sort(_cmp_by_name)
        if self._long_output:
            for user in users:
                self.put_stdout_msg(
                    ("%(user)s: %(uid)s %(gid)s %(type)s\n") %
                    {'user':user.user(),
                     'uid': "uid=%d," % user.uid(),
                     'gid': "gid=%d," % user.gid(),
                     'type':"type=%s" % user.user_type()}
                    )
                groups = user.groups(group_db)
                text = ""
                if groups:
                    g = groups.pop(0)
                    text = g.group()
                for g in groups:
                    text = "%s,%s" % (text,g.group())
                self.put_stdout_msg(
                    ("%(tab)-4s %(groups)s\n") %
                    {'tab':"",
                     'groups': "groups=%s" % text}
                    )
                self.put_stdout_msg(
                    ("%(tab)-4s %(dir)s\n") %
                    {'tab':"",
                     'dir': "directory=%s" % user.directory()}
                    )
                self.put_stdout_msg(
                    ("%(tab)-4s %(shell)s\n") %
                    {'tab':"",
                     'shell': "shell=%s" % user.shell()}
                    )
                self.put_stdout_msg("\n")
        else:
            if self._one:
                for user in users:
                    self.put_stdout_msg("%s\n", user.user())
            else:
                columns = 4
                rows = (len(users) + columns - 1) / columns
                for row in range(0,rows):
                    line = ""
                    for column in range(0,columns):
                        index = (row*columns) + column
                        if index >= len(users):
                            break
                        line += "%-18s" % users[index].user()
                    self.put_stdout_msg("%s\n", line)
        return
##
# Provides a command line interface to adding an "MPX" enabled user to
# the system.
#
# Modeled after the Linux useradd command, eventually should implement
# all the options.
class User_Add(SubCommand, PasswdMixin):
    ##
    # "mpxadmin user add" command handler.
    def __call__(self, *args):
        argv = self.arguments()
        if len(argv) != 2:
            raise EArgument(
                "mpxadmin rename: Must be called with two arguments.\n"
                "                 mpxadmin [user-type] new-user-name\n"
                "                 'mpxadmin user add --help' for more "
                "                 information.")
        user_type = argv[0]
        user_name = argv[1]
        passwd = _manager.PasswdFile()
        passwd.load()
        group = _manager.GroupFile()
        group.load()
        new_user = _manager.PasswdEntry()
        new_user.user(user_name)
        new_user.user_type(user_type, passwd, group)
        new_user.passwd(self.password(user_name))
        group.save()
        passwd.save()
        return
    def _uid_handler(self, *args):
        raise ENotImplemented("--uid not implemented")
    def _group_handler(self, *args):
        raise ENotImplemented("--group not implemented")
    def _groups_handler(self, *args):
        raise ENotImplemented("--groups not implemented")
    def _shell_handler(self, *args):
        raise ENotImplemented("--shell not implemented")
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        PasswdMixin.__init__(self)
        self._user_type = 'none'
        self.register_option('--uid',
                             self._uid_handler, """\
uid  Explicitly force the user id.

By default the user id is calculated.""",
                             ['-u'])
        self.register_option('--group',
                             self._group_handler, """\
group  Explicitly force the user's primary login group by name or number.

The group name must exist. A group number must refer to an already existing
group.

By default the primary group is a new group, named the same as the user.""",
                             ['-g'])
        self.register_option('--groups',
                             self._groups_handler, """\
group,[...]  A list of supplementary groups which the user is also a member
             of.

             By default, the list of suplimentary groups is managed by the
             type.

             Each group is separated from the next by a comma, with no
             intervening whitespace.  The groups are subject to the same
             restrictions as the group given with the --group option.  The
             default is for the user to belong only to the initial group.""",
                             ['-G'])
        self.register_option('--shell',
                             self._shell_handler, """\
  Specify the user's login shell.

  By default the shell is determined by the user's type.  Some types can not
  use this option to override the user's shell (pppuser)""",
                             ['-s'])
        return
    def __str__(self):
        return (
            "user-type new-user-name  Create a new user named 'new-user-name'"
            " of 'user-type'."
            )

class User_Rename(SubCommand, UserMixin):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        UserMixin.__init__(self)
        return
    def __str__(self):
        return (
            "[old-user-name] new-user-name  Change user name from"
            " old-user-name to new-user-name.  If old-user-name"
            " is not specified, assume it is the current user."
            )
    ##
    # "mpxadmin user remname" command handler.
    def __call__(self, *args):
        argv = self.arguments()
        if len(argv) not in (1,2):
            raise EArgument(
                "mpxadmin rename: Must be called with one or two arguments.\n"
                "                 mpxadmin [old-user-name] new-user-name\n"
                "                 'mpxadmin user rename --help' for more "
                "                 information.")
        elif len(argv) == 1:
            old_user_name = argv[0]
            new_user_name = self.current_user()
        elif len(argv) == 2:
            old_user_name = argv[0]
            new_user_name = argv[1]
        else:
            raise EInternalError("Exectuted unreachable code.")
        raise ENotImplemented("Renaming user %r to %r not implemented." %
                              (old_user_name, new_user_name))
        return

class User_Passwd(SubCommand, PasswdMixin):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        PasswdMixin.__init__(self)
        return
    def __str__(self):
        return "[user]  Change a mediator user's password."
    ##
    # "mpxadmin passwd" command handler.
    def __call__(self, *args):
        argv = self.arguments()
        if not len(argv):
            user = self.current_user()
        elif len(argv) == 1:
            user = argv[0]
        else:
            raise EArgument, (
                "mpxadmin passwd: Must be called with at most one argument.\n"
                "                 'mpxadmin passwd --help' for more "
                "                 information.")
        passwd = _manager.PasswdFile()
        passwd.load()
        if not user in passwd:
            raise EArgument(
                "mpxadmin passwd: %r is not a valid Mediator user." % user)
        entry = passwd[user]
        entry.passwd(self.password(user))
        passwd[user] = entry
        passwd.save()
        print "Password changed."
        return

class User_Delete(SubCommand, UserMixin):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        UserMixin.__init__(self)
        return
    def __str__(self):
        return (
            "user user-name  User to delete."
            )
    ##
    # "mpxadmin user delete" command handler.
    def __call__(self, *args):
        argv = self.arguments()
        if len(argv) != 1:
            raise EArgument(
                "mpxadmin delete: Must be called with one argument.\n"
                "                 mpxadmin delete user-name\n"
                "                 'mpxadmin user delete --help' for more "
                "                 information.")
        elif len(argv) == 1:
            user = argv[0]
        else:
            raise EInternalError("Executed unreachable code.")
        passwd = _manager.PasswdFile()
        passwd.load()
        if not user in passwd:
            raise EArgument(
                "mpxadmin delete: %r is not a valid Mediator user." % user)
        del passwd[user]
        passwd.save()
        return

class User(SubCommand):
    def __init__(self, *args):
        SubCommand.__init__(self, *args)
        # Register "mpxadmin user rename" command.
        User_Rename(self, "rename", ("rn","mv"))
        # Register "mpxadmin user passwd" command.
        User_Passwd(self, "passwd")
        # Register "mpxadmin user add"
        User_Add(self, "add")
        # Register "mpxadmin user list"
        User_List(self, "list", ("ls",))
        # Register "mpxadmin user delete" command.
        User_Delete(self, "delete", ("del",))
        return
    def __str__(self):
        return "  Sub-command to manage MPX users."
    ##
    # "mpxadmin user" command handler.
    def __call__(self, *args):
        argv = self.arguments()
        raise EArgument(
            "mpxadmin user:  Requires a sub-command.\n"
            "                'mpxadmin user --help' for more "
            "                information.")
        return

class MPX_Admin(CommandLineUtility):
    HELP = """
mpxadmin:  Command-line utility to help manage a Mediator.
"""
    OVERVIEW = """
"""
    def __init__(self, argv=None):
        CommandLineUtility.__init__(self, self.HELP, argv)
        # register the "mpxadmin passwd" command handler.
        # NOTE:  This is here for reverse compatibility.
        User_Passwd(self, "passwd")
        # register the "mpxadmin user" command handler.
        User(self,"user")
        # register the "mpxadmin log" command handler.
        # NOTE:  The "mpxadmin log" command is simply a place holder for more
        #        specific sub-commands.
        log = self.register_command("log", self.log,
                                    "Manage log files.",
                                    [])
        # register the "mpxadmin log info" command handler.
        log.register_command("info", self.log_info,
                             "Output general information about a log",
                             [])
        # register the "mpxadmin log list" command handler.
        list = log.register_command("list", self.log_list,
                                    "List existing logs",
                                    ["ls"])
        # register the "mpxadmin log list --all" option.
        list.register_option('--all', self.log_list_all,
                             "List all logs, including potentially corrupt"
                             " logs.",
                             ['-a'])
        self._log_list_all = 0 # By default, do not list potentially corrupt
                               # logs.
        self._force_remove = 0
        force = 'Force backfill operation, even if log is msglog or invalid.'
        count = 'Number of rows to backfill into log.'
        period = 'Timespan between consecutive rows of backfill.'
        offset = 'Hours away from 12:00 to synchronized timestamp to.'
        self._backfill_options = {'--force':{'aliases':['-f'],
                                             'value':0,'help':force},
                                  '--count':{'aliases':['-c'],
                                             'value':1,'help':count},
                                  '--period':{'aliases':['-p'],
                                              'value':1,'help':period},
                                  '--offset':{'aliases':['-o'],
                                              'value':0,'help':offset}
                                  }
        return
    ##
    # "mpxadmin log" command handler.
    # NOTE: This is really just a place holder.
    def log(self, command):
        argv = self.arguments()
        if not len(argv):
            raise EArgument, (
                "mpxadmin log: Requires a sub-command.\n"
                "              'mpxadmin log --help' for more information.")
        raise EArgument, (
            ("mpxadmin log: %r is not a valid a sub-command.\n"
             "              'mpxadmin log --help' for more information.") %
            argv[0])
    def log_remove(self,command):
        name = self._get_log_name()
        if (not self._force_delete 
            and name == 'msglog'):
            raise EArgument('Must force delete to remove msglog.')
        log = self._get_log_instance(name)
        log.destroy()
    def force_log_remove(self,option):
        self._force_remove = 1
    def log_truncate(self,command):
        name = self._get_log_name()
        log = self._get_log_instance(name)
        log.trim_ge('_seq',0)
    def log_backfill(self,command):
        name = self._get_log_name()
        log = self._get_log_instance(name)
        log.trim_ge('_seq',0)
    def backfill_option(self,option):
        if '=' not in option:
            raise EArgument('Option %s malformed')
        option,value = _string.split(option,'=')
        try:
            entry = self._backfill_options[option]
        except KeyError:
            for entry in self._backfill_options.values():
                if option in entry['aliases']:
                    break
            raise EArgument('Argument %s not recognized' % option)
                    
        
    def _get_log_name(self,required=1,only_arg=1):
        argv = self.arguments()
        if len(argv):
            if only_arg and len(argv) > 1:
                raise EArgument('Must be called with at most one password.')
            return argv[-1]
        if required:
            raise EArgument('Requires log name parameter.')
        return None
    def _get_log_instance(self,name):
        try:
            log = _log(name)
        except ENameInUse:
            log = _trimming_log(name)
        return log
    ##
    # "mpxadmin log info" command handler.
    def log_info(self, command):
        argv = self.arguments()
        raise NotImplementedError("log_info%r" % (tuple(argv),))
    ##
    # "mpxadmin log list" command handler.
    def log_list(self, command):
        argv = self.arguments()
        if len(argv):
            text = "argument"
            argument = argv[0]
            if len(argv) != 1:
                text += "s"
                argument = tuple(argv)
            raise EArgument(
                "mpxadmin log: Invalid %s, %r." % (text, argument))
        rejects = []
        list = _log_names(rejects)
        for name in list:
            self.put_stdout_msg("%s\n", name)
        if self._log_list_all:
            # Also list potentially corrupt logs.
            for name in rejects:
                self.put_stdout_msg("%s\n", name)
        return
    ##
    # "mpxadmin log list --all" option handler.
    def log_list_all(self, option):
        # Set the flag indicating to list (potentially) corrupt logs as well as
        # valid ones.
        self._log_list_all = 1
        return
    def run_command(self, command):
        self.put_stdout_msg(self.HELP)
        self.put_stdout_msg(self.OVERVIEW)
        self.put_stdout_msg("\n")
        self.put_stdout_msg("sub-commands:\n\n")
        keys = self.commands().keys()
        keys.sort()
        for key in keys:
            info = self.commands()[key].help_description()
            self.put_stdout_msg("  %s", info['name'])
            for alias in info['aliases']:
                self.put_stdout_msg(", %s", alias)
            self.put_stdout_msg(":\n")
            self.put_stdout_msg("    %s", info['text'])
            self.put_stdout_msg("\n")
        return 0

if __name__ == '__main__':
    main = MPX_Admin()
    main()

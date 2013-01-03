"""
Copyright (C) 2002 2003 2004 2009 2010 2011 Cisco Systems

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
# passwd and group abstraction.
# Better yet:  users and roles (ACLs another day).

import types as _types
import os as _os
import errno as _errno
import re as _re
import string as _string
import stat as _stat
import ConfigParser as configparser
from crypt import crypt as _crypt
import time as _time

# @fixme The following try/except block is to work around issues of
#        using this file in isolation (without relying on /usr/lib/broadway
#        on a mediator).
try:
    # For the "integrated" environment.
    from mpx import properties
    from mpx.lib.exceptions import EConfigurationIncomplete
    from mpx.lib.exceptions import EInvalidValue
    from mpx.lib.exceptions import ENameInUse
    from mpx.lib.configure import REQUIRED
except:
    # Fallback for the "restricted" /usr/lib/moab/config_service environment.
    class EConfigurationIncomplete(Exception):
        pass
    class EInvalidValue(Exception):
        pass
    class ENameInUse(Exception):
        pass
    REQUIRED="REQUIRED"
    class _Properties:
        def __init__(self):
            self.BIN_DIR = '/bin'
            self.SBIN_DIR = '/sbin'
            self.ETC_DIR = '/etc'
            self.HOME_ROOT = '/home'
            return
    properties = _Properties()

PASSWD_FILE = _os.path.join(properties.ETC_DIR, 'passwd')
SHADOW_FILE = _os.path.join(properties.ETC_DIR, 'shadow')
GROUP_FILE = _os.path.join(properties.ETC_DIR, 'group')

password_config = configparser.RawConfigParser()	#Will store password configuration. config_password will be set by Security Manager when it starts

#default password configurations starts
password_config.add_section('Length')
password_config.set('Length', 'min', '8')
password_config.set('Length', 'max', '80')
password_config.set('Length', 'minadmin', '12')
password_config.add_section('Complexity')
password_config.set('Complexity', 'character_sets', 'true')
password_config.set('Complexity', 'no_repeats', 'true')
password_config.add_section('Prohibited')
password_config.set('Prohibited', 'mpxadmin', 'true')
password_config.set('Prohibited', 'username_as_password', 'true')
#default password configuration settings ends

def get_default_username_config():
    config = configparser.RawConfigParser()
    # establish defaults
    config.add_section('Length')
    config.set('Length', 'min', '8')
    config.set('Length', 'max', '80')
    return config

disallowed_characters = r"""[^!"#$%&'()*+,\-./:;<=>?@[\]^_`{|}~\\a-zA-Z0-9]"""
special_characters = r"""[!"#$%&'()*+,\-./:;<=>?@[\]^_`{|}~\\ ]"""
numeric = r"[0-9]"
uppercase = r"[A-Z]"
lowercase = r"[a-z]"

def valid_username(username):
    """
        Invoked whenever a new username is added via the Security 
        Management web applications.
        
        Return None to indicate username is valid.  
        Return string with error message if failed 

        The following are the rules for username validation:
        1. length > 8 and length < 80
        2. chars not allowed: [!"#$%&'()*+,\-./:;<=>?@[\]^_`{|}~\\ ]
    """
    # load rules for username
    config = get_default_username_config()

    # extract individual rules for validating username
    un_min_len = config.getint('Length', 'min')
    un_max_len = config.getint('Length', 'max')

    error_message = None
    if len(username) < un_min_len:
        error_message = 'Username too short.' 
    elif len(username) > un_max_len:
        error_message = 'Username too long.' 
    elif _re.search(special_characters, username):
        m = _re.search(special_characters, username)
        c = username[m.start():m.end()]
        error_message = 'Unsupported character(s): %s detected.' % (repr(c),) 
    else:
        # passes all tests ..so return None
        return None

    error_message += '\n\r\n\rUsername must meet the following rules:\n\r'\
            '\n\rMust be at least %d characters in length.\r\n' \
            'Must not exceed %d characters in length.\r\n' \
            'May only contain UPPERcase, lowercase letters and numbers\n\r'
    error_message = error_message % (un_min_len, un_max_len)
    return error_message

def valid_password(password, username, admin=True, request=None):
    """
        Invoked whenever a new password is set via the Security 
        Management web applications.
        
        Return None to indicate password is valid.  
        Return string with error message if failed        
        Rules for password validation are defined in EDCS-562669
    """
    # test the username / password combo against the rules
    def is_username():
        if username is None:
            return False
        if password.lower() == username.lower():
            # password equal to username not allowed
            return True
        if password.lower() == username.lower()[::-1]:
            # password equal to username reversed not allowed
            return True
        return False
    def is_mpxadmin():
        if password.lower() == 'mpxadmin':
            return True
        return False
    def not_complex():
        complexity = 0
        if _re.search(uppercase, password):
            complexity += 1
        if _re.search(lowercase, password):
            complexity += 1
        if _re.search(numeric, password):
            complexity += 1
        if _re.search(special_characters, password):
            complexity += 1
        return complexity < 3
    def has_repeats():
        repeats = 0
        old_char = None
        for char in password: 
            if char == old_char:
                repeats += 1
                if repeats > 2:
                    return True
            else:
                repeats = 0
            old_char = char
        return False

    #password_config will be set by Security Manager, when it starts

    # extract individual rules for testing of password
    pw_min_len = password_config.getint('Length', 'min')
    if admin: # SEC-MIN-LENG for administrator accounts, different min len
        pw_min_len = password_config.getint('Length', 'minadmin')
    pw_max_len = password_config.getint('Length', 'max')
    pw_complexity = password_config.getboolean('Complexity', 'character_sets')
    pw_no_repeat = password_config.getboolean('Complexity', 'no_repeats')
    pw_not_username = password_config.getboolean('Prohibited', 'username_as_password')
    pw_not_mpxadmin = password_config.getboolean('Prohibited', 'mpxadmin')

    error_message = None
    if len(password) < pw_min_len:
        # SEC-MIN-LENG error
        error_message = 'Password too short.' 
    elif len(password) > pw_max_len:
        # SEC-MAX-LENG error
        error_message = 'Password too long.' 
    elif _re.search(disallowed_characters, password):
        # SEC-SUP-CHAR, SEC-CHR-CHCK error.
        m = _re.search(disallowed_characters, password)
        c = password[m.start():m.end()]
        error_message = 'Unsupported character(s): %s detected.' % (repr(c),) 
    elif pw_not_mpxadmin and is_mpxadmin():
        error_message = 'Username or Password is mpxadmin'
    elif pw_not_username and is_username():
        error_message = 'Password is username'
    elif pw_no_repeat and has_repeats():
        error_message = 'Character repeated more than 3 times'
    elif pw_complexity and not_complex():
        error_message = 'Password too simple.'
    else:
        # passes all tests
        return None

    error_message += '\n\r\n\rPasswords must meet the following rules: \n\r'\
            '\n\rMust be at least %d characters in length. \r\n' \
            'Must not exceed %d characters in length. \r\n' \
            'May only contain UPPERcase and lowercase letters, numbers & ' \
            '\n\rpunctuation characters. \n\r'
    if pw_not_username:
        error_message += 'Must not equal username or reversed username. \n\r'
    if pw_not_mpxadmin:
        error_message += 'Username or password must not equal mpxadmin. \n\r'
    if pw_no_repeat:
        error_message += 'Must not repeat any characters more than three '\
            'times in a row. \n\r'
    if pw_complexity:
        error_message += 'Must contain characters from at least three of '\
            'the four character groups: \n\rUPPERcase & lowercase letters, '\
            'numbers and punctuation characters. \n\r'
    error_message = error_message % (pw_min_len, pw_max_len)
    #msglog.log('broadway', msglog.types.INFO, error_message)
    return error_message

##
# UNIX specific /etc/passwd file entry.
class PasswdEntry:
    SEQUENCE = ('user', 'crypt', 'uid', 'gid',
                'gecos', 'directory', 'shell')
    DEFAULTS = {SEQUENCE[0]:REQUIRED,
                SEQUENCE[1]:'*',
                SEQUENCE[2]:REQUIRED,
                SEQUENCE[3]:REQUIRED,
                SEQUENCE[4]:'',
                SEQUENCE[5]:REQUIRED,
                SEQUENCE[6]:'/sbin/nologin'}
    def __init__(self,line=None):
        assert (
            line is None) or (type(line) in _types.StringTypes), (
            "Optional line must be None or a string."
            )
        self._reset()
        if line:
            self.from_line(line)
        return
    def __nonzero__(self):
        return len(self._entry) != 0
    def __str__(self):
        result = "%s:%s:%s:%s:%s:%s:%s" % (self._entry[self.SEQUENCE[0]],
                                           self._entry[self.SEQUENCE[1]],
                                           self._entry[self.SEQUENCE[2]],
                                           self._entry[self.SEQUENCE[3]],
                                           self._entry[self.SEQUENCE[4]],
                                           self._entry[self.SEQUENCE[5]],
                                           self._entry[self.SEQUENCE[6]])
        return result
    def __repr__(self):
        return '%s.%s(%r)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              str(self))
        return result
    def __hash__(self):
        return hash(self.user())
    def _reset(self):
        self._entry = {}
        self._entry.update(self.DEFAULTS)
        return
    def from_line(self, line):
        self._reset()
        line = line.strip()
        if not len(line) or line[0] == '#':
            return None
        columns = line.split(':')
        if len(columns) != len(self.SEQUENCE):
            raise EInvalidValue('columns', columns)
        for i in range(0,len(self.SEQUENCE)):
            attribute = self.SEQUENCE[i]
            default = self.DEFAULTS[attribute]
            value = columns[i]
            if not value and default == REQUIRED:
                raise EConfigurationIncomplete("User Manager", attribute)
            self._entry[attribute] = value
        return self
    def user(self, user=None, validate=True):
        assert (type(user) in _types.StringTypes) or (user is None), (
            "Optional user must be None one of the string types %r." %
            _types.StringTypes
            )
        if user is not None:
            if validate:
                msg = valid_username(user)
                if msg:
                    raise EInvalidValue("User Manager", msg)
            self._entry[self.SEQUENCE[0]] = user
        result = self._entry[self.SEQUENCE[0]]
        if result == REQUIRED:
            return None
        return result
    def passwd(self, passwd=None, validate=True):
        assert (type(passwd) in _types.StringTypes) or (passwd is None), (
            "Optional passwd must be None one of the string types %r." %
            _types.StringTypes
            )
        if passwd is not None:
            import identity as _identity # Deferred load of module to avoid
                                         # endless loop...
            # determine which minimum length to test
            admin = False
            if self.user_type() == 'mpxadmin':
                admin = True
            # throw exception if password is not good
            if validate:
                msg = valid_password(passwd, self.user(), admin)
                if msg:
                    raise EInvalidValue("Password Manager", msg)
            self.crypt(passwd)
            # If the user is IGMP/CSIK enabled, update the CSIK.
            if self.__get_gecos_entry("CSIK") is not None:
                self.__set_gecos_entry("CSIK",
                                       _identity.csiked_password(passwd))
            return
        return '********'
    def crypt(self, crypt=None):
        assert (type(crypt) in _types.StringTypes) or (crypt is None), (
            "Optional crypt must be None one of the string types %r." %
            _types.StringTypes
            )
        if crypt is not None:
            self._entry[self.SEQUENCE[1]] = crypt
        result = self._entry[self.SEQUENCE[1]]
        if result == REQUIRED:
            return None
        return result
    def password_matches_crypt(self, password):
        crypt_password = self.crypt()
        return _crypt(password, crypt_password[:2]) == crypt_password
    def uid(self, uid=None):
        assert (type(uid) is _types.IntType) or (uid is None), (
            "Optional uid must be None or an integer, not %r." % type(uid)
            )
        if uid is not None:
            self._entry[self.SEQUENCE[2]] = uid
        result = self._entry[self.SEQUENCE[2]]
        if result == REQUIRED:
            return None
        return int(result)
    def gid(self, gid=None):
        assert (type(gid) is _types.IntType) or (gid is None), (
            "Optional gid must be None or an integer, not %r." % type(gid)
            )
        if gid is not None:
            self._entry[self.SEQUENCE[3]] = gid
        result = self._entry[self.SEQUENCE[3]]
        if result == REQUIRED:
            return None
        return int(result)
    def gecos(self, gecos=None):
        assert (type(gecos) in _types.StringTypes) or (gecos is None), (
            "Optional gecos must be None one of the string types %r." %
            _types.StringTypes
            )
        if gecos is not None:
            self._entry[self.SEQUENCE[4]] = gecos
        result = self._entry[self.SEQUENCE[4]]
        if result == REQUIRED:
            return None
        return result
    def directory(self, directory=None):
        assert (
            type(directory) in _types.StringTypes) or (directory is None), (
            "Optional directory must be None one of the string types %r." %
            _types.StringTypes
            )
        if directory is not None:
            self._entry[self.SEQUENCE[5]] = directory
        result = self._entry[self.SEQUENCE[5]]
        if result == REQUIRED:
            return None
        return result
    def shell(self, shell=None):
        assert (type(shell) in _types.StringTypes) or (shell is None), (
            "Optional shell must be None one of the string types %r." %
            _types.StringTypes
            )
        if shell is not None:
            self._entry[self.SEQUENCE[6]] = shell
        result = self._entry[self.SEQUENCE[6]]
        if result == REQUIRED:
            return None
        return result
    #
    # Extensions to move to the Abstract User and maintain in it's
    # PDO.
    #
    def user_type(self, user_type=None, passwd_db=None, group_db=None):
        previous_type = self.__get_user_type()
        if previous_type == 'none':
            _hack_map = {
                'admin':'mpxconfig',
                'mpxadmin':'mpxadmin',
                'webdev':'webdev',
                'pppuser':'pppuser',
                }
            if _hack_map.has_key(self.user()):
                previous_type = _hack_map[self.user()]
        if user_type is not None:
            self.__set_user_type(user_type, passwd_db, group_db)
        return previous_type
    ##
    # @return The list of GroupEntry's which this user is a member of.
    #         The first entry is the primary group.
    def groups(self, group_db):
        results = [group_db[self.gid()]]
        for g in group_db:
            if self.user() in g.user_list():
                if g not in results:
                    results.append(g)
        return results
    ##
    # Update the file objects (not saved though).
    def __use_ids(self, passwd_db, group_db, uid, gid):
        if gid in group_db:
            # The primary group exists, use it.
            ge = group_db[gid]
            gid = ge.gid()
        else:
            # Create the primary group for the user, with the same name and id.
            ge = GroupEntry()
            ge.group(self.user())
            ge.gid(gid)
            group_db[ge.group()] = ge
        # Ensure that the user is a member of its primary group.
        if self.user() not in ge.user_list():
            ge.user_list(ge.user_list() + [self.user(),])
        # Use the user's uid and primary gid.
        self.uid(uid)
        self.gid(gid)
        passwd_db[self.user()] = self
        # Ensure that the user is in a group of it's type.
        user_type = self.user_type()
        if user_type != 'none':
            if user_type not in group_db:
                ge = GroupEntry()
                ge.group(user_type)
                id = passwd_db.new_uid()
                while id in passwd_db or id in group_db:
                    id = passwd_db.new_uid(id)
                ge.gid(id)
                group_db[ge.group()] = ge
            else:
                ge = group_db[user_type]
            if self.user() not in ge.user_list():
                ge.user_list(ge.user_list() + [self.user(),])
        return
    def __new_ids(self, passwd_db, group_db):
        if self.user() in passwd_db:
            raise ENameInUse("User Manager",
                             "%r already exists as a user." % self.user())
        if self.user() in group_db:
            raise ENameInUse("User Manger",
                             "%r already exists as a group." % self.user())
        id = passwd_db.new_uid()
        while id in passwd_db or id in group_db:
            id = passwd_db.new_uid(id)
        self.__use_ids(passwd_db, group_db, id, id)
        return
    def __mpxadmin_ids(self, passwd_db, group_db):
         user_type = self.user_type() # 'mpxadmin'
         if user_type in group_db:
             gid = group_db[user_type].gid()
         else:
             ge = GroupEntry()
             ge.group(user_type)
             gid = passwd_db.new_uid()
             while gid in passwd_db or gid in group_db:
                 gid = passwd_db.new_uid(gid)
             ge.gid(gid)
             group_db[ge.group()] = ge
         uid = int(properties.MPX_UID) # 0, aka root (permissions hack).
         self.__use_ids(passwd_db, group_db, uid, gid)
         return
    def __get_gecos_entry(self, name):
        items = self.gecos().split(",")
        for item in items:
            elements = item.split('=',1)
            if len(elements) == 2:
                if elements[0] == name:
                    return elements[1]
        return None
    def __set_gecos_entry(self, name, value):
        previous_value = None
        old_items = self.gecos().split(",")
        new_items = []
        for item in old_items:
            elements = item.split('=',1)
            if len(elements) == 2:
                if elements[0] == name:
                    previous_value = elements[1]
                    item = "%s=%s" % (name,value)
            if item:
                new_items.append(item)
        if previous_value is None:
            # Add the name/value.
            item = "%s=%s" % (name,value)
            new_items.append(item)
        if new_items:
            self.gecos(_string.join(new_items,","))
        return previous_value
    def __set_user_type(self, user_type, passwd_db, group_db):
        assert group_db is not None, (
            'group_db argument is required to set the user-type.'
            )
        assert passwd_db is not None, (
            'passwd_db argument is required to set the user-type.'
            )
        assert self.user() is not None, (
            "user-name must be set before setting the user-type"
            )
        _valid_types = ('none','pppuser','mpxadmin','mpxuser','webdev')
        assert user_type in _valid_types, (
            "user_type must be one of %r." % (_valid_types,)
            )
        if self.__get_user_type() != 'none':
            raise EInvalidValue('Can not change an existing users type.')
        self.__user_type_map[user_type](self, passwd_db, group_db)
        return
    def __get_user_type(self):
        user_type = self.__get_gecos_entry("TYPE")
        if user_type is None:
            return 'none'
        return user_type
    def __none_user_type(self, passwd_db, group_db):
        self.shell('/bin/sh')
        self.directory(_os.path.join(properties.HOME_ROOT, self.user()))
        self.__new_ids(passwd_db, group_db)
        return
    def __pppuser_user_type(self, passwd_db, group_db):
        self.__set_gecos_entry("TYPE","pppuser")
        self.shell('%s file %s >/dev/console 2>&1' %
                   (_os.path.join(properties.SBIN_DIR, 'pppd'),
                   _os.path.join(properties.ETC_DIR, 'ppp', 'dial-in-options'))
                   )
        self.directory(_os.path.join(properties.TARGET_ROOT, 'root'))
        self.__new_ids(passwd_db, group_db)
        return
    def __mpxadmin_user_type(self, passwd_db, group_db):
        self.__set_gecos_entry("TYPE","mpxadmin")
        self.__set_gecos_entry("ROLE","administrator") # @deprecated
        self.__set_gecos_entry("CSIK","*")
        self.shell('/bin/sh')
        self.directory(_os.path.join(properties.HOME_ROOT, 'mpxadmin'))
        self.__mpxadmin_ids(passwd_db, group_db)
        return
    def __mpxuser_user_type(self, passwd_db, group_db):
        self.__set_gecos_entry("TYPE","mpxuser")
        self.__set_gecos_entry("ROLE","user") # @deprecated
        self.shell('/bin/echo "User does not have shell access."')
        self.directory(_os.path.join(properties.TARGET_ROOT, 'root'))
        self.__new_ids(passwd_db, group_db)
        return
    def __mpxconfig_user_type(self, passwd_db, group_db):
        self.__set_gecos_entry("TYPE","mpxconfig")
        self.directory(_os.path.join(properties.TARGET_ROOT, 'root'))
        self.shell('%s --path=/usr/lib/mpx/python --simple' %
                   _os.path.join(properties.BIN_DIR, 'mpxconfig'))
        self.__new_ids(passwd_db, group_db)
        return
    def __webdev_type(self, passwd_db, group_db):
        self.__set_gecos_entry("TYPE","webdev")
        self.directory(properties.WWW_ROOT)
        self.shell(_os.path.join(properties.SBIN_DIR, 'ftponly'))
        self.__new_ids(passwd_db, group_db)
        return
    __user_type_map = {
        'none':__none_user_type,
        'mpxadmin':__mpxadmin_user_type,
        'mpxconfig':__mpxconfig_user_type,
        'mpxuser':__mpxuser_user_type,
        'pppuser':__pppuser_user_type,
        'webdev':__webdev_type,
        }

##
# UNIX specific /etc/shadow file entry.
class ShadowEntry:
    SEQUENCE = ('user', 'passwd', 'lstchg', 'min', 
                'max', 'warn', 'inact', 'expire', 
                'flag')
    DEFAULTS = {SEQUENCE[0]:REQUIRED,
                SEQUENCE[1]:REQUIRED,
                SEQUENCE[2]:REQUIRED,
                SEQUENCE[3]:'0',
                SEQUENCE[4]:'99999',
                SEQUENCE[5]:'7',
                SEQUENCE[6]:'',
                SEQUENCE[7]:'',
                SEQUENCE[8]:''}
    def __init__(self,line=None):
        assert (line is None) or (type(line) in _types.StringTypes),\
               ("Optional line must be None or a string.")
        self._reset()
        if line:
            self.from_line(line)
        return
    def __str__(self):
        result = "%s:%s:%s:%s:%s:%s:%s:%s:%s" %\
                 (self._entry[self.SEQUENCE[0]],
                  self._entry[self.SEQUENCE[1]],
                  self._entry[self.SEQUENCE[2]],
                  self._entry[self.SEQUENCE[3]],
                  self._entry[self.SEQUENCE[4]],
                  self._entry[self.SEQUENCE[5]],
                  self._entry[self.SEQUENCE[6]],
                  self._entry[self.SEQUENCE[7]],
                  self._entry[self.SEQUENCE[8]])
        return result
    def _reset(self):
        self._entry = {}
        self._entry.update(self.DEFAULTS)
        return
    def from_line(self, line):
        self._reset()
        line = line.strip()
        if not len(line) or line[0] == '#':
            return None
        columns = line.split(':')
        if len(columns) != len(self.SEQUENCE):
            raise EInvalidValue('columns', columns)
        for i in range(0,len(self.SEQUENCE)):
            attribute = self.SEQUENCE[i]
            default = self.DEFAULTS[attribute]
            value = columns[i]
            if not value and default == REQUIRED:
                raise EConfigurationIncomplete("User Manager", attribute)
            self._entry[attribute] = value
        return self
    def user(self, user=None, validate=True):
        assert (type(user) in _types.StringTypes) or (user is None), (
            "Optional user must be None one of the string types %r." %
            _types.StringTypes
            )
        if user is not None:
            if validate:
                msg = valid_username(user)
                if msg:
                    raise EInvalidValue("User Manager", msg)
            self._entry[self.SEQUENCE[0]] = user
        result = self._entry[self.SEQUENCE[0]]
        if result == REQUIRED:
            return None
        return result
    def passwd(self, passwd=None, validate=True):
        assert (type(passwd) in _types.StringTypes) or (passwd is None), (
            "Optional passwd must be None one of the string types %r." %
            _types.StringTypes
            )
        if passwd is not None:
            import identity as _identity 
            # determine which minimum length to test
            admin = False
            if self.user_type() == 'mpxadmin':
                admin = True
            # throw exception if password is not good
            if validate:
                msg = valid_password(passwd, self.user(), admin)
                if msg:
                    raise EInvalidValue("Password Manager", msg)
            self.crypt(_identity.crypted_password(self.user(), passwd))
            return
        return '********'
    def crypt(self, crypt=None):
        assert (type(crypt) in _types.StringTypes) or (crypt is None), (
            "Optional crypt must be None one of the string types %r." %
            _types.StringTypes
            )
        if crypt is not None:
            self._entry[self.SEQUENCE[1]] = crypt
        result = self._entry[self.SEQUENCE[1]]
        if result == REQUIRED:
            return None
        return result
    def user_type(self):
        if self.user() is None:
            return None
        system_users = PasswdFile()
        system_users.load()
        if self.user() not in system_users:
            return None
        user = system_users[self.user()]
        type = user.user_type()
        if type != 'none':
            return type
        else:
            return None
    def lstchg(self):
        self._entry[self.SEQUENCE[2]] = int(_time.time()/(60*60*24))
        result = self._entry[self.SEQUENCE[2]]
        if result == REQUIRED:
            return None
        return result
    def password_matches_crypt(self, password):
        crypt_password = self.crypt()
        if crypt_password is None:
            return False
        # try MD5
        fields = crypt_password.split('$')
        if len(fields) > 3:
            salt = fields[2]
            crypted = _crypt(password, '$1$'+salt+'$')
            if crypt_password == crypted:
                return True
        # try crypt (for legacy users)
        crypted = _crypt(password, crypt_password[:2])
        if crypt_password == crypted:
            return True
        return False

class SaveCountMixin(object):
    def SaveCountMixin(klass):
        klass.__total_saves = 0
        klass.__file_saves = {}
        return
    SaveCountMixin = classmethod(SaveCountMixin)
    def total_saves(klass):
        return klass.__total_saves
    total_save = classmethod(total_saves)
    def file_saves(klass, filename):
        filename = _os.path.realpath(filename)
        if klass.__file_saves.has_key(filename):
            return klass.__file_saves[filename]
        return 0
    file_saves = classmethod(file_saves)
    def _saved_file(klass, filename):
        filename = _os.path.realpath(filename)
        if not klass.__file_saves.has_key(filename):
            klass.__file_saves[filename] = 0
        klass.__file_saves[filename] += 1
        return
    _saved_file = classmethod(_saved_file)

##
# UNIX specific /etc/passwd file abstraction.
class PasswdFile(SaveCountMixin):
    class _Iterator:
        def __init__(self, entries):            
            self._entries = []
            self._entries.extend(entries)
        def __iter__(self):
            return self
        def next(self):
            if not len(self._entries):
                raise StopIteration
            return self._entries.pop(0)
    def __init__(self, file=PASSWD_FILE):
        self._file = file
        self._entries = []
        return
    def __len__(self):
        return len._entries
    def __iter__(self):
        return self._Iterator(self._entries)
    def __getitem__(self, user):
        if type(user) is _types.IntType:
            for e in self._entries:
                if e.uid() == user:
                    return e
        elif type(user) in _types.StringTypes:
            for e in self._entries:
                if e.user() == user:
                    return e
        else:
            assert 0, ("type(user key) must be an integer " +
                       "or one of string types %r.") % (_types.StringTypes,)
        raise KeyError, repr(user)
    ##
    # @fixme Support indexing by the integer uid as well.
    def __setitem__(self, user, entry):
        assert type(user) in _types.StringTypes, (
            "type(user name key) must be one of %r" % (_types.StringTypes,)
            )
        assert (entry is None) or (entry.__class__ is PasswdEntry), (
            "rvalue must be an instance of PasswdEntry or None."
            )
        for i in range(0,len(self._entries)):
            e = self._entries[i]
            if e.user() == user:
                # Updating an existing entry.
                if entry is None:
                    # None indicates to delete the existing entry
                    self._entries.pop(i)
                elif e.user() != entry.user():
                    # Renaming from <code>user</code> to
                    # <code>entry.user()</code>.
                    if entry.user() in self._entries:
                        # Special case, renaming a user to another exiting
                        # user.  The entry has total precedence.
                        j = self._entries.index(entry.user())
                        self._entries[j] = entry # Replace existing target name
                        self._entries.pop(i)     # Delete the entry with the
                                                 # old name.
                else:
                    # Updating (replacing) the user's information.
                    self._entries[i] = entry
                return
        assert entry.user() == user, (
            "When adding a new user, entry.user() must equal user."
            )
        self._entries.append(entry)
    def __delitem__(self, user):
        if type(user) is _types.IntType:
            for e in self._entries:
                if e.uid() == user:
                    self._entries.remove(e)
                    return
        elif type(user) in _types.StringTypes:
            for e in self._entries:
                if e.user() == user:
                    self._entries.remove(e)
                    return
        else:
            assert 0, ("type(user key) must be an integer " +
                       "or one of string types %r.") % (_types.StringTypes,)
        raise KeyError, repr(user)
    def __contains__(self, user):
        if type(user) is _types.IntType:
            for e in self._entries:
                if e.uid() == user:
                    return 1
        elif type(user) in _types.StringTypes:
            for e in self._entries:
                if e.user() == user:
                    return 1
        else:
            assert 0, ("type(user key) must be an integer " +
                       "or one of string types %r.") % (_types.StringTypes,)
        return 0
    def load(self, file=None):
        self._entries = []
        if file is None:
            file = self._file
        else:
            self._file = file
        try:
            fd = open(file, 'r')
        except IOError, e:
            if e.errno != _errno.ENOENT:
                raise
            fd = open('/dev/null', 'r')
        try:
            while 1:
                line = fd.readline()
                if line:
                    entry = PasswdEntry(line)
                    if entry:
                        self._entries.append(entry)
                else:
                    break
        finally:
            fd.close()
    def save(self, file=None):
        if file is None:
            file = self._file
        else:
            self._file = file
        fd = open(file, 'w+')
        try:
            for e in self._entries:
                fd.write(str(e))
                fd.write('\n')
        finally:
            self._saved_file(file)
            fd.close()
        return
    ##
    # @returns The first integer above <code>after</code> that is not in use
    #          as a UID or as a GID in the currently loaded passwd file.
    def new_uid(self, after=499):
        prev_uid = after
        next_uid = after+1
        while next_uid != prev_uid:
            prev_uid = next_uid
            for entry in self:
                if entry.uid() == next_uid or entry.gid() == next_uid:
                    next_uid += 1
                    break
                continue
            continue
        return next_uid
    def default_home(self, user):
        assert type(user) in _types.StringTypes, (
            "type(user name key) must be one of %r" % _types.StringTypes
            )
        return _os.path.join(properties.HOME_ROOT, user)
    def last_modified(self,file=None):
        if file is None:
            file = self._file
        else:
            self._file = file
        return _os.stat(file)[_stat.ST_MTIME]
    def exists(self,file=None):
        if file is None:
            file = self._file
        return _os.path.isfile(file)
    
PasswdFile.SaveCountMixin()

##
# UNIX specific /etc/shadow file abstraction.
class ShadowFile(SaveCountMixin):
    class _Iterator:
        def __init__(self, entries):            
            self._entries = []
            self._entries.extend(entries)
        def __iter__(self):
            return self
        def next(self):
            if not len(self._entries):
                raise StopIteration
            return self._entries.pop(0)
    def __init__(self, file=SHADOW_FILE):
        self._file = file
        self._entries = []
        return
    def __len__(self):
        return len._entries
    def __iter__(self):
        return self._Iterator(self._entries)
    def __getitem__(self, user):
        if type(user) in _types.StringTypes:
            for e in self._entries:
                if e.user() == user:
                    return e
        else:
            assert 0, ("type (user key) must be a string type")
        raise KeyError, repr(user)
    def __setitem__(self, user, entry):
        assert type(user) in _types.StringTypes, (
            "type(user name key) must be one of %r" % (_types.StringTypes,)
            )
        assert (entry is None) or (entry.__class__ is ShadowEntry), (
            "rvalue must be an instance of ShadowEntry or None."
            )
        for i in range(0,len(self._entries)):
            e = self._entries[i]
            if e.user() == user:
                # Updating an existing entry.
                if entry is None:
                    # None indicates to delete the existing entry
                    self._entries.pop(i)
                elif e.user() != entry.user():
                    # Renaming from <code>user</code> to
                    # <code>entry.user()</code>.
                    if entry.user() in self._entries:
                        # Special case, renaming a user to another exiting
                        # user.  The entry has total precedence.
                        j = self._entries.index(entry.user())
                        self._entries[j] = entry # Replace existing target name
                        self._entries.pop(i)     # Delete the entry with the
                                                 # old name.
                else:
                    # Updating (replacing) the user's information.
                    self._entries[i] = entry
                return
        assert entry.user() == user, (
            "When adding a new user, entry.user() must equal user."
            )
        self._entries.append(entry)
    def __delitem__(self, user):
        if type(user) in _types.StringTypes:
            for e in self._entries:
                if e.user() == user:
                    self._entries.remove(e)
                    return
        else:
            assert 0, ("type (user key) must be a string type")
        raise KeyError, repr(user)
    def __contains__(self, user):
        if type(user) in _types.StringTypes:
            for e in self._entries:
                if e.user() == user:
                    return 1
        else:
            assert 0, ("type (user key) must be a string type")
        return 0
    def load(self, file=None):
        self._entries = []
        if file is None:
            file = self._file
        else:
            self._file = file
        try:
            fd = open(file, 'r')
        except IOError, e:
            if e.errno != _errno.ENOENT:
                raise
            fd = open('/dev/null', 'r')
        try:
            while 1:
                line = fd.readline()
                if line:
                    entry = ShadowEntry(line)
                    if entry:
                        self._entries.append(entry)
                else:
                    break
        finally:
            fd.close()
    def save(self, file=None):
        if file is None:
            file = self._file
        else:
            self._file = file
        fd = open(file, 'w+')
        try:
            for e in self._entries:
                fd.write(str(e))
                fd.write('\n')
        finally:
            self._saved_file(file)
            fd.close()
        return
    def default_home(self, user):
        assert type(user) in _types.StringTypes, (
            "type(user name key) must be one of %r" % _types.StringTypes
            )
        return _os.path.join(properties.HOME_ROOT, user)
    def last_modified(self,file=None):
        if file is None:
            file = self._file
        else:
            self._file = file
        return _os.stat(file)[_stat.ST_MTIME]
    def exists(self,file=None):
        if file is None:
            file = self._file
        return _os.path.isfile(file)
    
ShadowFile.SaveCountMixin()

##
# UNIX specific /etc/group file entry.
class GroupEntry:
    SEQUENCE = ('group', 'crypt', 'gid', 'user_list')
    DEFAULTS = {SEQUENCE[0]:REQUIRED,
                SEQUENCE[1]:'*',
                SEQUENCE[2]:REQUIRED,
                SEQUENCE[3]:()}
    def __init__(self,line=None):
        self._reset()
        if line:
            self.from_line(line)
        return
    def __nonzero__(self):
        return len(self._entry) != 0
    def __str__(self):
        result = "%s:%s:%s:" % (self._entry[self.SEQUENCE[0]],
                                self._entry[self.SEQUENCE[1]],
                                self._entry[self.SEQUENCE[2]])
        for user in self.user_list():
            result = "%s%s," % (result, user)
        if result[-1] == ',':
            result = result[:-1]
        return result
    def __repr__(self):
        return '%s.%s(%r)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              str(self))
        return result
    def __hash__(self):
        return hash(self.group())
    def _reset(self):
        self._entry = {}
        self._entry.update(self.DEFAULTS)
        return
    def group(self, group=None):
        assert (type(group) in _types.StringTypes) or (group is None), (
            "Optional group must be None one of the string types %r." %
            _types.StringTypes
            )
        if group is not None:
            self._entry[self.SEQUENCE[0]] = group
        result = self._entry[self.SEQUENCE[0]]
        if result == REQUIRED:
            return None
        return result
    def crypt(self, crypt=None):
        assert (type(crypt) in _types.StringTypes) or (crypt is None), (
            "Optional crypt must be None one of the string types %r." %
            _types.StringTypes
            )
        if crypt is not None:
            self._entry[self.SEQUENCE[1]] = crypt
        result = self._entry[self.SEQUENCE[1]]
        if result == REQUIRED:
            return None
        return result
    def password_matches_crypt(self, password):
        crypt_password = self.crypt()
        return _crypt(password, crypt_password[:2]) == crypt_password
    def gid(self, gid=None):
        assert (type(gid) is _types.IntType) or (gid is None), (
            "Optional gid must be None or an integer, not %r." % type(gid)
            )
        if gid is not None:
            self._entry[self.SEQUENCE[2]] = gid
        result = self._entry[self.SEQUENCE[2]]
        if result == REQUIRED:
            return None
        return int(result)
    def _coerce_user_list(self, user_list):
        list_types = (_types.ListType,_types.TupleType,)
        if type(user_list) in list_types:
            result = list(user_list)
        elif type(user_list) in _types.StringTypes:
            user_list = user_list.split(',')
            for user in user_list:
                if not user:
                    user_list.remove(user)
            result = user_list
        elif user_list is None:
            result = self._coerce_user_list(self._entry[self.SEQUENCE[3]])
        else:
            assert 0, (
                "Optional user_list must be None, a string, a list or a tuple."
                )
        return result
    def user_list(self, user_list=None):
        result = self._coerce_user_list(user_list)
        if user_list is not None:
            self._entry[self.SEQUENCE[3]] = result
        return result
    def from_line(self, line):
        self._reset()
        line = line.strip()
        if not len(line) or line[0] == '#':
            return None
        columns = line.split(':')
        if len(columns) != len(self.SEQUENCE):
            raise EInvalidValue('columns', columns)
        for i in range(0,len(self.SEQUENCE)):
            attribute = self.SEQUENCE[i]
            default = self.DEFAULTS[attribute]
            value = columns[i]
            if not value and columns[i] == REQUIRED:
                raise EConfigurationIncomplete("User Manager", attribute)
            self._entry[attribute] = value
        return self

##
# UNIX specific /etc/group file abstraction.
class GroupFile(SaveCountMixin):
    class _Iterator:
        def __init__(self, entries):            
            self._entries = []
            self._entries.extend(entries)
        def __iter__(self):
            return self
        def next(self):
            if not len(self._entries):
                raise StopIteration
            return self._entries.pop(0)
    def __init__(self, file=GROUP_FILE):
        self._file = file
        self._entries = []
        return
    def __len__(self):
        return len._entries
    def __iter__(self):
        return self._Iterator(self._entries)
    def __getitem__(self, group):
        if type(group) is _types.IntType:
            for e in self._entries:
                if e.gid() == group:
                    return e
        elif type(group) in _types.StringTypes:
            for e in self._entries:
                if e.group() == group:
                    return e
        else:
            assert 0, ("type(group key) must be an integer " +
                       "or one of string types %r.") % _types.StringTypes
        raise KeyError, repr(group)
    ##
    # @fixme Support indexing by the integer gid as well.
    def __setitem__(self, group, entry):
        assert type(group) in _types.StringTypes, (
            "type(group name key) must be one of %r" % _types.StringTypes
            )
        assert (entry is None) or (entry.__class__ is GroupEntry), (
            "rvalue must be an instance of PasswdEntry or None."
            )
        for i in range(0,len(self._entries)):
            e = self._entries[i]
            if e.group() == group:
                # Updating an existing entry.
                if entry is None:
                    # None indicates to delete the existing entry
                    self._entries.pop(i)
                elif e.group() != entry.group():
                    # Renaming from <code>group</code> to
                    # <code>entry.group()</code>.
                    if entry.group() in self._entries:
                        # Special case, renaming a group to another exiting
                        # group.  The entry has total precedence.
                        j = self._entries.index(entry.group())
                        self._entries[j] = entry # Replace existing target name
                        self._entries.pop(i)     # Delete the entry with the
                                                 # old name.
                else:
                    # Updating (replacing) the group's information.
                    self._entries[i] = entry
                return
        assert entry.group() == group, (
            "When adding a new group, entry.group() must equal group."
            )
        self._entries.append(entry)
    def __delitem__(self, group):
        if type(group) is _types.IntType:
            for e in self._entries:
                if e.gid() == group:
                    self._entries.remove(e)
                    return
        elif type(group) in _types.StringTypes:
            for e in self._entries:
                if e.group() == group:
                    self._entries.remove(e)
                    return
        else:
            assert 0, ("type(group key) must be an integer " +
                       "or one of string types %r.") % _types.StringTypes
        raise KeyError, repr(group)
    def __contains__(self, group):
        if type(group) is _types.IntType:
            for e in self._entries:
                if e.gid() == group:
                    return 1
        elif type(group) in _types.StringTypes:
            for e in self._entries:
                if e.group() == group:
                    return 1
        else:
            assert 0, ("type(group key) must be an integer " +
                       "or one of string types %r.") % (_types.StringTypes,)
        return 0
    def load(self, file=None):
        self._entries = []
        if file is None:
            file = self._file
        else:
            self._file = file
        try:
            fd = open(file, 'r')
        except IOError, e:
            if e.errno != _errno.ENOENT:
                raise
            fd = open('/dev/null', 'r')
        try:
            while 1:
                line = fd.readline()
                if line:
                    entry = GroupEntry(line)
                    if entry:
                        self._entries.append(entry)
                else:
                    break
        finally:
            fd.close()
    def save(self, file=None):
        if file is None:
            file = self._file
        else:
            self._file = file
        fd = open(file, 'w+')
        try:
            for e in self._entries:
                fd.write(str(e))
                fd.write('\n')
        finally:
            self._saved_file(file)
            fd.close()

GroupFile.SaveCountMixin()

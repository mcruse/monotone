"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from crypt import crypt
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.uuid import UUID
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import EConfiguration
from moab.user.manager import PasswdFile
from moab.user.manager import PasswdEntry
from moab.user.manager import GroupFile
from moab.user.manager import GroupEntry
from moab.user.manager import PASSWD_FILE,GROUP_FILE
from moab.user.identity import crypted_password
from moab.user.manager import ShadowFile
from moab.user.manager import ShadowEntry
from moab.user.manager import SHADOW_FILE

class NewUser(PersistentDataObject):
    #USERS = _UserDictionary()
    def __init__(self,name,password_file=PASSWD_FILE,group_file=GROUP_FILE,
                 shadow_file = SHADOW_FILE):
        self.__lock = Lock()
        self.__password_file = password_file
        self.__group_file = group_file
        self.__shadow_file = shadow_file
        self.meta = {}
        self.USERS.load()
        if not self.USERS.has_key(self.name()):
            msglog.log('broadway',msglog.types.INFO,
                       ('No profile for user %s found, creating'
                        ' new profile' % name))
            self.USERS[self.name()] = str(UUID())
        PersistentDataObject.__init__(self,self.USERS[self.name()])
        PersistentDataObject.load(self)
    def save(self):
        self.__lock.acquire()
        try:
            passwd_db = PasswdFile(self.__password_file)
            passwd_db.load()
            passwd_db[self.name()] = self.password_entry()
            passwd_db.save()

            # save /etc/shadow content
            shadow_db = ShadowFile(self.__shadow_file)
            shadow_db.load()
            shadow_db[self.name()] = self.shadow_entry()
            shadow_db.save()
        finally:
            self.__lock.release()
        self.load(self.name())
    def name(self):
        return self.__user.user()
    def group(self):
        return self.__groups[0].group()
    def groups(self):
        group_db = GroupFile(self.__group_file)
        group_db.load()
        return self.__user.groups(group_db)
    def group_ids(self):
        ids = []
        for group in self.groups():
            ids.append(group.gid())
        return ids
    def type(self):
        return self.__user.user_type()
    def set_type(self,type):
        raise ENotImplemented(self.set_type)
    def password(self):
        raise ENotImplemented(self.password)
    def set_password(self,password):
        self.__shadow.crypt(crypted_password(self.__name,password))
    def crypt(self):
        return self.__shadow.crypt()
    def set_crypt(self,crypt):
        self.__shadow.crypt(crypt)
    def uid(self):
        return self.__user.uid()
    def set_uid(self,uid):
        self.__user.uid(uid)
    def gid(self):
        return self.__groups[0].gid()
    def set_gid(self,gid):
        self.__user.gid(gid)
    def gids(self):
        gids = []
        for group in self.__groups:
            gids.append(group.gid())
        return gids
    def set_gids(self,gids):
        raise ENotImplemented(self.set_gids)
    def gecos(self):
        return self.__user.gecos()
    def set_gecos(self,gecos):
        self.__user.gecos(gecos)
    def directory(self):
        return self.__user.directory()
    def set_directory(self,directory):
        self.__user.directory(directory)
    def shell(self):
        return self.__user.shell()
    def set_shell(self,shell):
        self.__user.shell(shell)
    def is_dirty(self):
        return not self.__loaded
    def set_meta_value(self,name,value):
        self.meta[name] = value
        PersistentDataObject.save(self)
    def get_meta_value(self,name,default=None):
        if self.meta.has_key(name):
            return self.meta[name]
        return default
    def get_meta(self):
        return self.meta.copy()
    def __getitem__(self,name):
        return self.get_meta_value(name)
    def __setitem__(self,name,value):
        return self.set_meta_value(name,value)
    def password_entry(self):
        return self.__user
    def shadow_entry(self):
        return self.__shadow
    def group_entry(self):
        return self.__groups[0]
    def group_entries(self):
        return self.__groups

class User(PersistentDataObject):
    #USERS = _UserDictionary()
    def __init__(self,name,password_file=PASSWD_FILE,group_file=GROUP_FILE,
                 shadow_file = SHADOW_FILE):
        self.__lock = Lock()
        self.__password_file = password_file
        self.__shadow_file = shadow_file
        self.__group_file = group_file
        self.__loaded = 0
        self.load(name)
        self.meta = {}
        self.USERS.load()
        if not self.USERS.has_key(self.name()):
            msglog.log('broadway',msglog.types.INFO,
                       ('No profile for user %s found, creating'
                        ' new profile' % name))
            self.USERS[self.name()] = str(UUID())
        PersistentDataObject.__init__(self,self.USERS[self.name()])
        PersistentDataObject.load(self)
    def loaded(self):
        self.__lock.acquire()
        try:
            return self.__loaded
        finally:
            self.__lock.release()
    def load(self,name):
        self.__lock.acquire()
        try:
            passwd_db = PasswdFile(self.__password_file)
            passwd_db.load()
            if name in passwd_db:
                self.__user = passwd_db[name]
            else:
                raise EInvalidValue('name',name,'No such user.')
            shadow_db = ShadowFile(self.__shadow_file)
            shadow_db.load()
            if name in shadow_db:
                self.__shadow = shadow_db[name]
            else:
                raise EInvalidValue('name',name,'No such user.')
            self.__groups = []
            groups_db = GroupFile(self.__group_file)
            groups_db.load()
            for group_name in self.__user.groups(groups_db):
                self.__groups.append(groups_db[group_name])
            if not self.__groups:
                raise EInvalidValue('name',name,'User belongs to no groups.')
            self.__loaded = 1
        finally:
            self.__lock.release()
    def save(self):
        self.__lock.acquire()
        try:
            passwd_db = PasswdFile(self.__password_file)
            passwd_db.load()
            passwd_db[self.name()] = self.password_entry()
            passwd_db.save()

            # save /etc/shadow content
            shadow_db = ShadowFile(self.__shadow_file)
            shadow_db.load()
            shadow_db[self.name()] = self.shadow_entry()
            shadow_db.save()
        finally:
            self.__lock.release()
        self.load(self.name())
    def name(self):
        return self.__user.user()
    def group(self):
        return self.__groups[0].group()
    def groups(self):
        group_db = GroupFile(self.__group_file)
        group_db.load()
        return self.__user.groups(group_db)
    def group_ids(self):
        ids = []
        for group in self.groups():
            ids.append(group.gid())
        return ids
    def type(self):
        return self.__user.user_type()
    def set_type(self,type):
        raise ENotImplemented(self.set_type)
    def password(self):
        raise ENotImplemented(self.password)
    def set_password(self,password):
        self.__shadow.crypt(crypted_password(self.__name,password))
    def crypt(self):
        return self.__shadow.crypt()
    def set_crypt(self,crypt):
        self.__shadow.crypt(crypt)
    def uid(self):
        return self.__user.uid()
    def set_uid(self,uid):
        self.__user.uid(uid)
    def gid(self):
        return self.__groups[0].gid()
    def set_gid(self,gid):
        self.__user.gid(gid)
    def gids(self):
        gids = []
        for group in self.__groups:
            gids.append(group.gid())
        return gids
    def set_gids(self,gids):
        raise ENotImplemented(self.set_gids)
    def gecos(self):
        return self.__user.gecos()
    def set_gecos(self,gecos):
        self.__user.gecos(gecos)
    def directory(self):
        return self.__user.directory()
    def set_directory(self,directory):
        self.__user.directory(directory)
    def shell(self):
        return self.__user.shell()
    def set_shell(self,shell):
        self.__user.shell(shell)
    def is_dirty(self):
        return not self.__loaded
    def set_meta_value(self,name,value):
        self.meta[name] = value
        PersistentDataObject.save(self)
    def get_meta_value(self,name,default=None):
        if self.meta.has_key(name):
            return self.meta[name]
        return default
    def get_meta(self):
        return self.meta.copy()
    def __getitem__(self,name):
        return self.get_meta_value(name)
    def __setitem__(self,name,value):
        return self.set_meta_value(name,value)
    def password_entry(self):
        return self.__user
    def shadow_entry(self):
        return self.__shadow
    def group_entry(self):
        return self.__groups[0]
    def group_entries(self):
        return self.__groups

    

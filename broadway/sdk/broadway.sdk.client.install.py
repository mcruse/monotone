"""
Copyright (C) 2003 2004 2006 2008 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
#-*-Python-*- Hint to [X]Emacs on colorization, etc...
import sys

from moab.user.manager import PasswdFile, PasswdEntry, GroupFile, GroupEntry
from moab.user.identity import crypted_password as _crypted_password

from tools.lib import os

from mpx.install import *
from mpx.install.filesystem import makedirs, chown
from mpx import properties

class InstallSelf(InstallPackage):
    def __init__(self):
        InstallPackage.__init__(self, 'broadway.sdk.client',
                                'Broadway: Client SDK',
                                ['broadway.core'])
        self.UID = int(properties.MPX_UID)
        self.GID = int(properties.MPX_GID)
        self.keywords = {}
        self.keywords.update(CommandKeywords.DEFAULTS)
        self.keywords["verbosity"] = (self.options.verbose + 1)
        self.keywords["debug"] = self.options.debug
        self.keywords["test"] = self.options.test
        return
    def _fatal_keywords(self):
        keywords = {}
        keywords.update(self.keywords)
        keywords[CommandKeywords.FATAL_KEY] = 1
        return keywords
    def _install_webapi_dir(self,root):
        webapi_path = os.path.join(root,'webapi')
        # Ensure that webapi is empty (by deleting it).
        os.system("rm -rf %s" % (webapi_path,), **self._fatal_keywords())
        # Ensure that the root directory exists.
        makedirs(root)
        # Copy over the latest webapi with all files as hard links
        # to avoid wasting space
        # - not that this makes the assumption that nothing in the
        # webapi directory is modified by the user - because if it
        # is this code will break the design goal of having the
        # install process restore every thing to a known state
        os.system("cp -r --link client %s" % (webapi_path,),**self.keywords)
        return

    def _update_webdev_user(self):
        passwd = PasswdFile()
        passwd.load()
        group = GroupFile()
        group.load()
        if "webdev" not in passwd:
            if "webdev" not in group:
                next_id = passwd.new_uid()
                while next_id in group:
                    next_id = passwd.new_uid(next_id)
                webdev = GroupEntry()
                webdev.group("webdev")
                webdev.crypt("*")
                webdev.gid(next_id)
                webdev.user_list((webdev.group(),))
                group[webdev.group()] = webdev
                group.save()
            gid = group["webdev"].gid()
            uid = passwd.new_uid(gid-1)
            while uid in passwd:
                uid = passwd.new_uid(uid)
            webdev = PasswdEntry()
            webdev.user(user="webdev", validate=False)
            webdev.crypt(_crypted_password("webdev", "webdev"))
            webdev.uid(uid)
            webdev.gid(gid)
            webdev.gecos("AKA=webdev")
            webdev.directory(properties.WWW_ROOT)
            webdev.shell(os.path.join(properties.ETC_DIR,"ftponly"))
            passwd[webdev.user()] = webdev
            passwd.save()
        return
    def _update_webdev_home(self):
        self.cwd.pushd(properties.WWW_ROOT)
        chown(".", "webdev", "webdev", recurse=1, ignore_errors=1, followslinks=0)
        os.system("chmod -R ug+Xrw . *", **self.keywords)
        self.cwd.popd()
        return
    def _update_webdev_files(self):
        bin_dir = os.path.join(properties.WWW_ROOT,'bin')
        etc_dir = os.path.join(properties.WWW_ROOT,'etc')
        for dir in (bin_dir, etc_dir):
            makedirs(dir)
        self.cwd.pushd(bin_dir)
        for file in ('gzip','ls','tar'):
            source = os.path.join('/bin',file)
            target = os.path.join(bin_dir,file)
            os.system("rm -f %s && ln -s %s %s" % (target,source,target),
                      **self._fatal_keywords())
        self.cwd.popd()
        self.cwd.pushd(etc_dir)
        
        self.cwd.popd()
        return
    def _update_webdev(self):
        self._update_webdev_user()
        self._update_webdev_home()
        self._update_webdev_files()
        return
    def install(self):
        self._update_webdev()
        return 0

def MAIN(args=sys.argv, stdout=sys.stdout, stderr=sys.stderr):
    save_argv=sys.argv
    save_stdout=sys.stdout
    save_stderr=sys.stderr
    sys.argv=args
    sys.stdout=stdout
    sys.stderr=stderr
    try:
        # MAIN()
        ip = InstallSelf()
        return ip.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

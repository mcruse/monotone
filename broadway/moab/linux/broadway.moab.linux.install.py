"""
Copyright (C) 2003 2004 2005 2006 2007 2009 2010 2011 Cisco Systems

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

import sys, signal

from tools.lib import os, CommandKeywords

from mpx.install import *
from mpx.install.filesystem import makedirs, chown

from mpx import properties

from moab.user.manager import PasswdFile, PasswdEntry, GroupFile, GroupEntry
from moab.user.identity import crypted_password as _crypted_password
from moab.user.identity import csiked_password as _csiked_password

from moab.linux.templates import motd
from moab.linux.lib.servicemgr import InittabManager, InittabGroup

# @fixme mpxconfig uses tools.lib, which should probably be cloned somewhere.
ROOT = properties.ROOT
# @fixme MPX_PYTHON_LIB + MOAB + SITE-PACKAGES == 'headache'
MPX_PYTHON_LIB = os.path.realpath(properties.MPX_PYTHON_LIB)

VAR_RUN=os.path.realpath(properties.get('VAR_RUN','/var/run'))
# VAR_RUN_BROADWAY is not really a property.  It is always relative to VAR_RUN.
VAR_RUN_BROADWAY=os.path.join(VAR_RUN,'broadway')

TARGET_ROOT = properties.TARGET_ROOT
HOME_ROOT = properties.HOME_ROOT
SBIN_DIR = properties.SBIN_DIR
LIB_DIR = properties.LIB_DIR
BIN_DIR = properties.BIN_DIR
ETC_DIR = properties.ETC_DIR
ETCDHCPC_DIR = os.path.join(properties.ETC_DIR, 'dhcpc')

MPX_UID = properties.MPX_UID
MPX_GID = properties.MPX_GID

MPXCONFIG_SCRIPT = os.path.join(BIN_DIR, 'mpxconfig')
MPXCONFIG_PYC = os.path.join(MPX_PYTHON_LIB, 'mpxconfig.pyc')
MPXUPGRADE_SCRIPT = os.path.join(BIN_DIR, 'mpxupgrade')
MPXUPGRADE_PYC = os.path.join(MPX_PYTHON_LIB, 'mpxupgrade.pyc')
IPCHECK_SCRIPT = os.path.join(BIN_DIR, 'ipcheck')
IPCHECK_PYC = os.path.join(MPX_PYTHON_LIB, 'ipcheck.pyc')

LIB_MODULES = ('simplemenu', 'zoneinfo', 'servicemgr', 'devicemgr')
BIN_MODULES = ('mpxconfig', 'mpxupgrade', 'ipcheck')

RC_MFW_SCRIPT = os.path.join(ETC_DIR, 'rc.mfw')
RC_MFW_PYC =os.path.join(ETC_DIR, 'rc.mfw.pyc')

def _update_superuser(username,
                      directory='/root',
                      shell='/sbin/nologin',
                      crypt=None,
                      uid=None,
                      gid=None):
    if crypt is None:
        crypt=''
    if uid is None:
        uid = 0
    users = PasswdFile()
    users.load()
    groups = GroupFile()
    groups.load()
    if username not in groups:
        group = GroupEntry()
        group.group(username)
        group.crypt("*")
        if gid is None:
            gid = users.new_uid()
            while gid in groups:
                gid = users.new_uid(gid)
        group.gid(gid)
        group.user_list((username,))
        groups[username] = group
        groups.save()
    gid = groups[username].gid()
    if username in users:
        user = users[username]
    else:
        user = PasswdEntry()
        user.crypt(crypt)
    user.gid(gid)
    user.uid(uid)
    user.user(username)
    user.shell(shell)
    user.directory(directory)
    if crypt:
        user.crypt(crypt)
    users[username] = user
    users.save()
    user = users[username]
    if user.gid() != gid:
        user.gid(gid)
        users[user.user()] = user
        users.save()
    return

class LinuxInstallPackage(InstallPackage):
    def __init__(self):
        InstallPackage.__init__(self,
                                 'broadway.moab.linux',
                                 'Broadway: MOE Abstraction Layer for Linux',
                                 [])
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
    def get_conflicts(self):
        return self.conflict_list
    def _force_target_directory(self, directory):
        makedirs(directory)
        chown(directory, "root", "mpxadmin", ignore_errors=1)
        keywords = {}
        keywords.update(self.keywords)
        keywords[CommandKeywords.FATAL_KEY] = 0
        os.system("chmod 0770 %s" % (directory,), **keywords)
        return
    def _update_mpxadmin_user(self):
        #
        # Ensure the mpxadmin group exists.
        # 
        passwd = PasswdFile()
        passwd.load()
        group = GroupFile()
        group.load()

        self.options.normal_message("Checking for mpxadmin group.")
        if "mpxadmin" not in group:
            self.options.normal_message("No mpxadmin group, adding.")
            mpxadmin = GroupEntry()
            mpxadmin.group("mpxadmin")
            mpxadmin.crypt("*")
            mpxadmin.gid(int(MPX_GID))
            mpxadmin.user_list((mpxadmin.group(),))
            group[mpxadmin.group()] = mpxadmin
            group.save()
            self.options.normal_message("Added mpxadmin group(%d) in %s.",
                                        mpxadmin.gid(), group._file)
        else:
            self.options.normal_message("mpxadmin group already exists.")
        if int(MPX_GID):
            # Installing as regular user, presumably in penvironment.d, add
            # the required "root" group.
            self.options.normal_message("Checking for root group.")
            if "root" not in group:
                self.options.normal_message("No root group, adding.")
                root = GroupEntry()
                root.group("root")
                root.crypt("*")
                root.gid(int(MPX_GID))
                root.user_list((root.group(),))
                group[root.group()] = root
                group.save()
                self.options.normal_message("Added root group(%d) in %s.",
                                            root.gid(), group._file)
            else:
                self.options.normal_message("root group already exists.")
        #
        # Ensure the mpxadmin user exists.
        #
        self.options.normal_message("Checking for mpxadmin user.")
        #if "mpxadmin" not in passwd:
        # if there is no mpxadmin type user, create a default
        if len(filter(lambda pw: pw.user_type() == 'mpxadmin', passwd)) == 0:
            self.options.normal_message(
                "No mpxadmin user, checking for mpxadmin group.")
            gid = group["mpxadmin"].gid()
            # @fixme This is not pretty, but it will work for now.
            #        A new UID would be uid = passwd.new_uid(gid-1)
            uid = int(MPX_UID) # Hijacking root for superuser privelidges...
            mpxadmin = PasswdEntry()
            mpxadmin.user("mpxadmin")
            mpxadmin.directory(passwd.default_home(mpxadmin.user()))
            mpxadmin.crypt(_crypted_password("mpxadmin", "mpxadmin"))
            mpxadmin.uid(uid)
            mpxadmin.gid(gid)
            # @fixme Formalize the Mediator concept of meta-data associated
            #        with users.  Also consider moving the meta-data out of
            #        /etc/passwd and into a PDO...
            # META-DATA:
            #   AKA:  Allows us to track renames of key users (pppuser,
            #         mpxadmin, webdev, ...)
            #   CSIK:  Configuration Service Initial Key (used to calculate
            #          "classic" Configuration Service Security Keys.
            mpxadmin.gecos("AKA=mpxadmin,CSIK=%s,ROLE=administrator" % (
                _csiked_password("mpxadmin"),))
            mpxadmin.shell("/bin/bash")
            passwd[mpxadmin.user()] = mpxadmin
            passwd.save()
            self.options.normal_message("Added mpxadmin user(%d.%d) in %s.",
                                        mpxadmin.uid(), mpxadmin.gid(),
                                        passwd._file)
            # Create and update the mpxadmin user.
            self._force_target_directory(mpxadmin.directory())
            self.cwd.pushd(mpxadmin.directory())
            passwd = PasswdFile()
            passwd.load()
            group = GroupFile()
            group.load()
            os.system("chmod -R ug+Xrw .", **self._fatal_keywords())
            chown(".", "mpxadmin", "mpxadmin", recurse=1, ignore_errors=1)
            self.cwd.popd()
        else:
            self.options.normal_message(
                "mpxadmin user already exists.")
        #
        # Ensure mpxadmin is a member of the root group.
        # 
        group = GroupFile()
        group.load()
        root = group["root"]
        user_list = root.user_list()
        if "mpxadmin" not in user_list:
            self.options.normal_message(
                "Adding mpxadmin user to the root group.")
            user_list.append("mpxadmin")
            root.user_list(user_list)
            group["root"] = root
            group.save()
        return
    ###
    # Create the profile for the framework.
    #
    def _create_profile(self):
        self.options.normal_message("Creating profile for framework")
        if self.options.test:
            return
        profile_dir_name = os.path.join(ETC_DIR,'profile.d')
        profile_file_name = os.path.join(profile_dir_name,'broadway.sh')
        # Create the profile.
        makedirs(profile_dir_name)
        try:
            profile_file = open(profile_file_name, 'w')
        except:
            self.options.error_message("FAILED TO OPEN %s" %
                                       profile_file_name)
            return
        # Add the tools directory to the search path.
        profile = """#!%s\n\nPATH="$PATH:%s"\nexport PATH""" % (
            profile_file_name, os.path.join(ROOT, 'tools')
            )
        profile_file.write(profile)
        profile_file.close()
        os.chmod(profile_file_name, 0755)

    ###
    # Update the Message-of-the-Day file with version and serial numbers.
    #
    def _update_motd(self):
        # Gather the bits and pieces of information we need to insert into
        # the message-of-the-day file.
        if properties.get_boolean('UPDATE_MOTD', 'false'):     
            self.options.normal_message("Updating message-of-the-day file")
            if self.options.test:
                return
            # Get the format string from the template
            text = motd.as_string()
            # Create a new message-of-the-day file.
            motd_file_name = os.path.join(ETC_DIR,'motd')
            motd_file = open(motd_file_name, 'w')
            try:
                motd_file.write(text)   
            finally:
                motd_file.close()
    def _update_mpx_python_lib(self):
        # Ensure the target directory exists.
        makedirs(MPX_PYTHON_LIB)
        keywords = {}
        keywords.update(self.keywords)
        keywords[CommandKeywords.FATAL_KEY] = 1
        #
        #
        # Install mpxconfig, mpxupgrade and associated libraries.
        # @fixme Consolodate /usr/lib/mpx/python, site-packages and the
        #        minimal moab...
        self.cwd.pushd('lib')
        for module in LIB_MODULES:
            os.system('rm -f %s/%s.py*' % (MPX_PYTHON_LIB, module), **keywords)
            file = InstallFile(self.options, module+".pyc") # !read_only (copy)
            file.relocate(MPX_PYTHON_LIB)
            file.chmod(0664)
            continue
        self.cwd.popd()
        self.cwd.pushd('bin')
        for module in BIN_MODULES:
            os.system('rm -f %s/%s.py*' % (MPX_PYTHON_LIB, module), **keywords)
            file = InstallFile(self.options, module+".pyc")
            file.relocate(MPX_PYTHON_LIB)
            file.chmod(0664)
            continue
        self.cwd.popd()
        return
    def _update_var(self):
        # Ensure that there is a proftpd in var
        PROFTPD_DIR =os.path.realpath(os.path.join(TARGET_ROOT,
                                                   'var','proftpd'))
        makedirs(PROFTPD_DIR)
        # Ensure that there is a lock in var
        VAR_LOCK = os.path.realpath(os.path.join(TARGET_ROOT,
                                    'var','lock'))
        makedirs(VAR_LOCK,0755)
        return
    def _update_devtools(self):
        DEVLIB_DIR = os.path.join(TARGET_ROOT,
                                  "opt/envenergy/devtools/2.0/x86")
        makedirs(DEVLIB_DIR)
        # Ensure executables will work with the current devtools.
        # @fixme Place holder.
        SLINK = os.path.join(DEVLIB_DIR,'lib')
        if os.path.ismount(SLINK):
            assert 0, ("Existing %s can not be a mount point." % SLINK)
        if os.path.islink(SLINK) or os.path.isfile(SLINK):
            self.options.normal_message("Removing old %s", SLINK)
            os.unlink(SLINK)
        elif os.path.isdir(SLINK):
            # assert 0, ("Existing %s can not be a directory." % SLINK)
            self.options.normal_message(
                "Skipping linking of existing %s directory.",
                SLINK)
            return
        assert not os.path.exists(SLINK), "Failed to remove %s." % SLINK
        self.options.normal_message("Creating %s link to %s.", SLINK,
                                    os.path.join(TARGET_ROOT,'lib'))
        os.symlink(os.path.join(TARGET_ROOT,'lib'), SLINK)
        return
    def _update_sbin(self):
        # Ensure the target directory exists.
        real_sbin_dir = os.path.join(TARGET_ROOT, 'sbin')
        makedirs(real_sbin_dir)
        self.cwd.pushd('bin')
        keywords = {}
        keywords.update(self.keywords)
        keywords[CommandKeywords.FATAL_KEY] = 1
        for executable in ['hotplug']:
            # Copy the executable to the real sbin directory.
            os.system('rm -f %s/%s' % (real_sbin_dir, executable), **keywords)
            file = InstallFile(self.options, executable) #!read_only
            file.relocate(real_sbin_dir)
            file.chmod(0775)
        self.cwd.popd()  
        return
    def _update_bin(self):
        # Ensure the target directory exists.
        makedirs(BIN_DIR)
        self.cwd.pushd('bin')
        blinky_bill = 'blinky_bill'
        wdt = 'wdt'
        bin_list = ('watchdog',)
        keywords = {}
        keywords.update(self.keywords)
        keywords[CommandKeywords.FATAL_KEY] = 1
        if os.path.exists(os.path.join(TARGET_ROOT,
                                       'proc/mediator/sig')):
            # Only copy blinky_bill and wdt if /proc/mediator/pattern exists.
            bin_list += (blinky_bill, wdt)
        else:
            os.system('rm -f %s' % os.path.join(BIN_DIR,
                                                os.path.basename(blinky_bill)),
                      **keywords)
            os.system('rm -f %s' % os.path.join(BIN_DIR, os.path.basename(wdt)),
                      **keywords)
        for executable_source in bin_list:
            executable_target = os.path.join(
                BIN_DIR,
                os.path.basename(executable_source)
                )
            # Copy the executable to the BIN_DIR.
            os.system('rm -f %s' % executable_target, **keywords)
            file = InstallFile(self.options, executable_source) #!read_only
            file.relocate(BIN_DIR)
            file.chmod(0775)
        # Force a specific environment.
        keywords = {}
        keywords['ENV'] = properties.as_environment()
        # @fixme mpxconfig uses tools.lib, which should probably be cloned
        #        somewhere.
        keywords['ENV']['PYTHONPATH'] = '%s:%s' % (MPX_PYTHON_LIB, ROOT)
        create_pyscript(MPXCONFIG_SCRIPT, MPXCONFIG_PYC, **keywords)
        create_pyscript(MPXUPGRADE_SCRIPT, MPXUPGRADE_PYC, **keywords)
        create_pyscript(IPCHECK_SCRIPT, IPCHECK_PYC, **keywords)
        # @fixme This could be much cleaner.
        # Delete versions of old executables in incorrect places.
        correct_dir = os.path.realpath(BIN_DIR)
        for old_dir in (os.path.join(TARGET_ROOT,'bin'),
                        os.path.join(TARGET_ROOT,'sbin'),
                        os.path.join(TARGET_ROOT,'usr/bin'),
                        os.path.join(TARGET_ROOT,'usr/sbin')):
            old_dir = os.path.realpath(old_dir)
            if old_dir == correct_dir:
                # If old_dir == correct_dir, then old_dir 'taint so
                # old...
                continue
            for basename in ('watchdog','blinky_bill','mpxconfig','mpxupgrade',
                             'ipcheck'):
                old_file = os.path.join(old_dir,basename)
                if os.path.exists(old_file):
                    keywords = {}
                    keywords.update(self.keywords)
                    keywords[CommandKeywords.FATAL_KEY] = 1
                    os.system('rm -f %s' % old_file, **keywords)
        self.cwd.popd()
        return
    def _validate_var_run(self):
        makedirs(VAR_RUN,0755)
        makedirs(VAR_RUN_BROADWAY,0775)
        chown(VAR_RUN_BROADWAY, "root", "mpxadmin", recurse=1, ignore_errors=1)
        return
    def _update_rc_mfw(self):
        #
        # Upgrade /etc/rc.mfw
        file = InstallFile(self.options, 'rc.mfw.pyc', 0)
        file.relocate(ETC_DIR)
        file.chmod(0664)
        create_pyscript(RC_MFW_SCRIPT, RC_MFW_PYC,
                        # Support interactive mode.
                        ('RESPAWN=--respawn\n'
                         'test "$1" = "-i" &&'
                         ' PYTHON_VIA_ENV="${PYTHON_VIA_ENV} -i"\n'
                         'test "$1" = "-i" && RESPAWN=""'
                         ),
                        **{'EXEC':
                           'exec ' +
                           os.path.join(BIN_DIR,'watchdog') +
                           ' ${RESPAWN}',
                           }
                        )
        return
    def _update_dhcpcd_exe(self):
        #
        # Upgrade /etc/dhcpc/dhcpcd.exe
        makedirs(ETCDHCPC_DIR, 0755)
        self.cwd.pushd('bin')
        file = InstallFile(self.options, 'dhcpcd.exe')
        file.relocate(ETCDHCPC_DIR)
        file.chmod(0770)
        self.cwd.popd()
        return
    def _update_inittab(self):
        # @todo Support xinit.d enabling/disabling as well.
        wdt = os.path.join(BIN_DIR, 'wdt')
        wdt_key = 'HW_WATCHDOG'
        blinky_bill = os.path.join(BIN_DIR, 'blinky_bill')
        blinky_key = 'MPX_STATUS_LED'
        proftpd = '/usr/sbin/proftpd'
        proftpd_key = 'MPX_FTPD'
        service_map = {wdt_key:
                       {'delete_all':
                        '^([^:]*):([^:]*):([^:]*):(.*\\bwdt\\b.*)',
                        'add':('wdt:2345:once:%s' % wdt)},
                       blinky_key:
                       {'delete_all':
                        '^([^:]*):([^:]*):([^:]*):(.*\\bblinky_bill\\b.*)',
                        'add':('led:2345:respawn:%s' % blinky_bill)},
                       proftpd_key:
                       {'delete_all':
                        '^([^:]*):([^:]*):([^:]*):(.*\\b\\Sproftpd\\b.*)',
                        'add':('%s%sftpd:2345:respawn:%s -n'
                               % (InittabGroup.ENTRY_DISABLED_TAG,
                                  InittabGroup.TAG_SEP,
                                  proftpd))},
                       'MPX_APP':
                       {'delete_all':
                         ('^([^:]*):([^:]*):([^:]*):(.*\\b%s\\b.*)'
                          % os.path.basename(RC_MFW_SCRIPT)),
                        'add':('mfw:345:respawn:%s >/dev/null' %
                               RC_MFW_SCRIPT)},
                       }
        for f, k in ((wdt, wdt_key),
                     (blinky_bill, blinky_key),
                     (proftpd, proftpd_key)):
            if not os.path.exists(f):
                service_map[k].pop('add', None)
        inittab = InittabManager()
        for gname in service_map.keys():
            inittab.remgroup(gname)
            inittab.delete_matching_lines(service_map[gname]['delete_all'])
            if service_map[gname].has_key('add'):
                inittab.addgroup(InittabGroup(gname, service_map[gname]['add']))
        inittab.commit()
        return
    def _notify_led(self):
        # @fixme Make sure this fails fast...
        # Set the status indicator to INSTALLING.
        from moab.linux.lib.statusled import StatusLED
        led = StatusLED()
        if led.waitForStart():
            led.setInstalling()
        return
    
    def _update_pppd_support(self):
        pppdir = os.path.join( properties.ETC_DIR, 'ppp' )
        makedirs( pppdir )
        
        self.cwd.pushd( 'bin' )
        file = InstallFile( self.options, 'ip-up.local' )
        file.relocate( pppdir )
        file.chmod( 0770 )
        file = InstallFile( self.options, 'ip-down.local' )
        file.relocate( pppdir )
        file.chmod( 0770 )
        self.cwd.popd()
        
        self.cwd.pushd( 'lib' )
        file = InstallFile( self.options, 'routing.pyc', 1 )
        file.relocate( pppdir )
        self.cwd.popd()
    
    def install(self):
        self._update_devtools()
        makedirs(ETC_DIR)
        self._update_mpxadmin_user()
        makedirs(SBIN_DIR)
        makedirs(LIB_DIR)
        self._update_var()
        self._update_mpx_python_lib()
        self._update_bin()
        self._update_sbin()
        self._validate_var_run()
        self._update_rc_mfw()
        # In case this if the first time blinky_bill was installed, and now that
        # inittab has been updated, re-notify the led.
        self._notify_led()
        self._update_dhcpcd_exe()
        self._update_motd()
        self._create_profile()
        self._update_pppd_support()
        self._update_inittab()
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
        ip = LinuxInstallPackage()
        return ip.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

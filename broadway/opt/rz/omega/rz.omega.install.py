"""
Copyright (C) 2008 2009 2010 2011 Cisco Systems

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
import os
import sys
import popen2

from mpx.install import *
from mpx import properties
import time as t

HARDWARE_MODEL = properties.HARDWARE_MODEL
CONFIGURATION_FILE = properties.CONFIGURATION_FILE
LIB_DIR = properties.LIB_DIR
ETC_DIR = properties.ETC_DIR
HARDWARE_LIST = ["NBM-2500","NBM-4800","NBM-5000","NBM-2400", "GURU"]

UID = int(properties.MPX_UID)
GID = int(properties.MPX_GID)

def _copy_upgradeable_file(source_file, dest, options):
    file = InstallFile(options,source_file,0)
    if os.path.isdir(dest):
        dest = os.path.normpath(os.path.join(dest,
                                             os.path.basename(source_file)))
    if os.path.isfile(dest):
        if options.upgrade and not isfile_upgradeable(dest):
            options.normal_message("Skipping upgrade of %s which has been"
                                   " modified.", dest)
            return
        os.remove(dest)
    file.relocate(dest)
    file.chmod(0664)
    return

class InstallSelf(InstallPackage):
    def __init__(self):
        InstallPackage.__init__(self, 'rz.omega',
                                'Richards-Zeta: Omega',
                                ['broadway','rz.opt',
                                 'envenergy.nodedefs.all'])
        return
    def _install_web_content(self,www_dir):
        self.cwd.pushd('html')	# Change to the HTML "source" directory.
        try:
            makedirs(www_dir)
            for d in ('images', 'omega', 'sounds',):
                # @fixme images directory collides with base images directory.
                src = os.path.abspath(d)
                # @note Using DST relative to the local directory did not
                #       work as expected in os.symlink(SRC, DST).  The
                #       relative DST was treated relative to SRC, not the
                #       CWD.
                dst = os.path.join(www_dir, d)
                #
                # Remove any existing link, file or directory:
                #
                if os.path.islink(dst):
                    # os.path.exists() of a link to a non-existant path
                    # returns False.
                    os.unlink(dst)
                elif os.path.isfile(dst):
                    os.unlink(dst)
                elif os.path.isdir(dst):
                    shutil.rmtree(dst)
                #
                # Create a LINK to the standard files:
                # @note DST is interpreted at runtime, NOT when the link is
                #       created.  This means that CWD is applied when the name
                #       is looked up.
                os.symlink(src, dst)
	    if HARDWARE_MODEL not in HARDWARE_LIST:
	        self._install_nbmnavigator_content()
        finally:
            self.cwd.popd()
        return

    def _install_nbmnavigator_content(self):
        cat_home = os.getenv('CATALINA_HOME')
        if cat_home:
            dst = cat_home + "/webapps/GlobalNavigation.war"
            src = os.path.abspath('omega') + "/nbmnavigator/GlobalNavigation.war"
            if os.path.islink(dst):
                # os.path.exists() of a link to a non-existant path
                # returns False.
                os.unlink(dst)
            elif os.path.isfile(dst):
                os.unlink(dst)
            elif os.path.isdir(dst):
                shutil.rmtree(dst)
            os.symlink(src, dst)
            self._populate_managerdb()
        else:
            msg = 'CATALINA_HOME not set, unable to install GlobalNavigation.war'
            self.options.error_message(msg)
 
    def _populate_managerdb(self):
        try:
            prop_file_path = "/var/mpx/config/sw/META-INF/db.properties"
            mgrdb_dump_path = os.path.abspath("omega") + "/nbmnavigator/manager_db.sql";
            ptr = open(prop_file_path,'r')
            line = ptr.readline()
            while(line):
                if(line.find("db.agg.main.username") != -1):
                    username = line.split("=")[1].split("\n")[0]
                elif(line.find("db.agg.main.password") != -1):
                    password = line.split("=")[1].split("\n")[0]
            	line = ptr.readline()
            cmd = "mysql -u "+ username + " -p"+ password +" < " + mgrdb_dump_path
            child = popen2.Popen3(cmd, 0) # Ignore stderr
            stdout = child.fromchild
            line = stdout.readline()
            # Drain stdout (to avoid a hang).
            while line:
                line = stdout.readline()
        except IOError:
            msg = "db.properties file not found for manager_db"
            self.options.error_message(msg)
	    
    def _shadow_entry(self, shwfile, un):
        if not os.path.exists(shwfile):
            return False
        shwH = open(shwfile, 'r')
        shwF = shwH.readlines()
        shwH.close()
        for sentry in shwF:
            s = sentry.split(':') 
            if s[0] == un:
                return sentry
        return False
       
    def _chk_valid_shadow(self):
        '''
        shwfile  - new shadow file
        pwdfile  - new passwd file
        bshwfile - backup - old shadow file 
        bpwdfile - backup - old passwd file
        backup   - boolean flag to indicate whether 
                   backup is required or not (backup is 
                   taken if an inconsistency between shadow 
                   and passwd file is found)
        '''
        shwfile = ETC_DIR + '/shadow'
        pwdfile = ETC_DIR + '/passwd'
        bpwdfile = ETC_DIR + '/.passwd.bak'
        bshwfile = ETC_DIR + '/.shadow.bak'
        lstchg = str(int(t.time()/(60*60*24)))
        backup = False
        pf = sf = ""
        if not os.path.exists(shwfile) or \
           not os.path.exists(pwdfile):
            return
        pwdH = open(pwdfile, 'r')
        pwdF = pwdH.readlines()
        pwdH.close()
        for pentry in pwdF:
            p = pentry.split(':')
            s = self._shadow_entry(shwfile, p[0])
            if s is False:
                backup = True
                pf += p[0] + ':' + 'x'  + ':' + p[2] + ':' + \
                      p[3] + ':' + p[4] + ':' + p[5] + ':' + p[6]
                if p[1] is None or p[1] is '':
                    p[1] = '*'
                sf += p[0] + ':' + p[1] + ':' + lstchg + ':0:99999:7:::\n'
            else:
                pf += pentry
                sf += s
        if backup:
            os.system('rm -rf ' + bpwdfile)
            os.system('rm -rf ' + bshwfile)
            os.system('mv -f ' + pwdfile + ' ' + bpwdfile)
            os.system('mv -f ' + shwfile + ' ' + bshwfile)
            try:
                pwdH = open(pwdfile, 'w')
                shwH = open(shwfile, 'w')
                pwdH.write(pf)
                shwH.write(sf)
                pwdH.close()
                shwH.close()
                message = ("Inconsistency found in %s and %s\n") % (pwdfile, shwfile)
                message += ("backup %s to %s\n") % (pwdfile, bpwdfile)
                message += ("backup %s to %s\n") % (shwfile, bshwfile)
                message += ("new %s and %s files created\n") % (pwdfile, shwfile)
                self.options.normal_message(message)
            except:
                os.system('mv -f ' + bpwdfile + ' ' + pwdfile)
                os.system('mv -f ' + bshwfile + ' ' + shwfile)
                raise

    def _migrate_to_shadow(self):
        '''
                                old-style               new-style

            /etc/passwd     stores (encrypted)      stores 'x' in the
                            password                password field and
                                                    creates a new shadow
                                                    entry for the user

            /etc/shadow     NA                      stores the (encrypted)
                                                    password

            this function migrates the old-style /etc/passwd to
            the new-style /etc/passwd and creates a /etc/shadow
            file with shadow entries for all the users in the
            /etc/passwd file

            after the migration /etc/.passwd.bak will contain
            the original (old-style) /etc/passwd content
        '''
        shwfile = ETC_DIR + '/shadow'
        pwdfile = ETC_DIR + '/passwd'
        bpwdfile = ETC_DIR + '/.passwd.bak'
        if os.path.exists(shwfile):
            self._chk_valid_shadow()
            return
        pwdH = open(pwdfile, 'r')
        pwdF = pwdH.readlines()
        pwdH.close()
        os.system('rm -rf ' + bpwdfile)
        lstchg = str(int(t.time()/(60*60*24)))
        os.system('mv -f ' + pwdfile + ' ' + bpwdfile)
        try:
            pwdH = open(pwdfile, 'w')
            shwH = open(shwfile, 'w')
            for line in pwdF:
                a = line.split(':')
                p = a[0] + ':' + 'x'  + ':' + a[2] + ':' +\
                    a[3] + ':' + a[4] + ':' + a[5] + ':' + a[6]
                if a[1] is None or a[1] is '':
                    a[1] = '*'
                s = a[0] + ':' + a[1] + ':' + lstchg +\
                    ':0:99999:7:::\n'
                pwdH.write(p)
                shwH.write(s)
            pwdH.close()
            shwH.close()
            message = ("%s migrated to %s") % (pwdfile, shwfile)
            self.options.normal_message(message)
        except:
            os.system('mv -f ' + bpwdfile + ' ' + pwdfile)
            raise

    def _set_file_perm(self, file, perm):
        os.system('chmod ' + perm + ' ' + file)

    def _update_file_permission(self):
        pf = ETC_DIR + '/passwd'
        sf = ETC_DIR + '/shadow'
        gf = ETC_DIR + '/group'
        self._set_file_perm(pf, "644")
        self._set_file_perm(sf, "400")
        self._set_file_perm(gf, "644")
 
    def get_conflicts(self):
        # HACK because the fallback thinks there is a conflict between 
        # envenergy.* APPLICATIONS and dumc.* APPLICATIONS.
        return []
    def install(self):
        xml_file = "%s.xml" % HARDWARE_MODEL
        xml_file = os.path.realpath(os.path.join('config', xml_file))
        if not os.path.exists(xml_file):
            xml_file = os.path.realpath(os.path.join('config', 'Unknown.xml'))
        file = InstallFile(self.options, xml_file, 0)
        file.relocate(CONFIGURATION_FILE)
        file.chown(UID, GID)
        file.chmod(0774)
        #install files into the non-secure site
        self._install_web_content(properties.HTTP_ROOT)
        #install files to the secure site
        self._install_web_content(properties.HTTPS_ROOT)
        # energywise graph depends on soflink to /var/mpx/log
        cmd = ''.join(
            ('ln -fs ', properties.VAR_LOG, ' ',
             os.path.join(properties.HTTPS_ROOT,
                          'omega/nrgyzMgr/energy/energy_log'))
            )
        os.system(cmd)
        self._migrate_to_shadow()
        self._update_file_permission()
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

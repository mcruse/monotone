"""
Copyright (C) 2003 2004 2005 2006 2007 2008 2009 2010 2011 Cisco Systems

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
import os
import sys
import shutil

from mpx.install import *
from mpx.install.filesystem import makedirs
from mpx import properties

# Calculate the attributes of the software and the hardware.
MOE_VERSION = properties.MOE_VERSION
# if this is a release show just the release version which is just a number
# because a release is most likely to go to a customer, otherwise it is probably
# internal and we want to the rest of it
if properties.RELEASE_TYPE  == 'release':
    RELEASE = properties.RELEASE_VERSION
else:
    RELEASE = properties.RELEASE

SERIAL_NUMBER = properties.SERIAL_NUMBER
HARDWARE_CLASS = properties.HARDWARE_CLASS

# Calculate the source directories for this script.
ROOT = os.path.realpath(properties.ROOT)
TOOLS = os.path.join(ROOT, 'tools')
CFG = os.path.join(ROOT, 'cfg')
HTML = os.path.join(ROOT, 'html')
HTTPS = os.path.join(ROOT, 'mpx/service/network/https')

# Calculate the target directories.
MPX_UID = int(properties.MPX_UID)
MPX_GID = int(properties.MPX_GID)
BIN_DIR = properties.BIN_DIR

CONFIGURATION_FILE = properties.CONFIGURATION_FILE
CONFIGURATION_DIR = os.path.split(CONFIGURATION_FILE)[0]

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

class CoreInstallPackage(InstallPackage): 
    def __init__(self):
        InstallPackage.__init__(self,
                                'broadway.core',
                                'Broadway: Mediator Framework Core Package',
                                ['broadway.moab'])
        return
    def get_conflicts(self):
        return self.conflict_list
    ##
    # Update the template file.  Assumes files are in current working
    # directory.
    def _update_template(self, filename, moe_version, release, serial_number,extra_info=''):
        file = None
        try:
            self.options.normal_message("Generating the Mediator's" +
                                        " %s" % filename)
            if self.options.test:
               return

            # Get the template file contents.
            try:
                template_file_name = '%s.template' % filename
                template_file = open(template_file_name, 'r')
            except IOError, e:
                self.options.fatal_message("Unable to open %s",
                                           template_file_name)
                sys.exit(e.errno)
                return
            
            template = template_file.read()
            template_file.close()
            # Create the new files
            try:
                file = open(filename, 'w')
            except IOError, e:
                self.options.fatal_message("Unable to open %s",
                                       file_name)
                sys.exit(e.errno)
                return
            # the "" is for extra links that maybe used by other application
            # look at eval install as an example
            try:                            
                file.write(template % (moe_version, release, serial_number,extra_info))                

            except Exception,e:
                self.options.fatal_message("Unable to update %s",
                                           template_file_name)
                raise
                return
        finally:
            if file:
                file.close()
        
    def _update_html_templates(self, moe_version, release, serial_number):
        self.cwd.pushd(HTML)	# Change the the HTML "source" directory.
        try:
            self._update_template('login.html',
                                  moe_version, release, serial_number)
        finally:
            self.cwd.popd()
            pass
        return
    def _install_web_content_in_root(self,www_dir):
        self.cwd.pushd(HTML)	# Change to the HTML "source" directory.
        try:
            makedirs(www_dir)
            for f in ('energywise.html', 'events.html', 'index.html', 
                      'login.html', 'redirect.html', 'restore.html',
                      'schedules.html', 'security.html', 'system.html', 
                      'trends.html', 'troubleshoot.html', 'upgrade.html', 'fileUpload.html'):
                _copy_upgradeable_file(f, www_dir, self.options)

            for d in ('eventmanager', 'graphtool', 'mpx', 'msglog', 
                      'public', 'reference', 'stylesheets', 'templates',
                      'webapi', 'dojoroot'):
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
                
            # create sym links to cues libraries
            src = 'cues-0.2.1' 
            dst = 'cues'
            dst = os.path.join(www_dir, dst)
            src = os.path.join('/opt/cisco', src)
            if os.path.islink(dst) or os.path.isfile(dst):
                os.unlink(dst)
            elif os.path.isdir(dst):
                shutil.rmtree(dst)
            os.symlink(src, dst)
        finally:
            self.cwd.popd()
            pass
        return
    def _create_default_configuration(self):
        self.cwd.pushd(CFG)
        file = InstallFile(self.options, '.')
        file.chown_tree(MPX_UID, MPX_GID)
        self.options.normal_message(("Generating the default configuration " +
                                     "file for %s hardware.") %
                                    (HARDWARE_CLASS,))
        default_file = "%s.xml" % HARDWARE_CLASS
        if not os.path.isfile(default_file):
            self.options.error_message(("Unable to locate a hardware " +
                                        "specific configuration template.\n" +
                                        "No such file:  %s") %
                                       (default_file,))
            default_file = "%s.xml" % properties.UNKNOWN
        if not os.path.isfile(default_file):
            self.options.fatal_message(("Unable to locate a any useable " +
                                        "configuration template.\n" +
                                        "No such file:  %s") %
                                       (default_file,))
            # @fixme Check the error code.
            sys.exit(1)
            return
        # OK, we have a default XML configuration for the HARDWARE_CLASS.
        file = InstallFile(self.options, default_file, 0)
        file.relocate(CONFIGURATION_FILE)
        replace_property_references(CONFIGURATION_FILE)
        file.chmod(0664)
        self.cwd.popd()
        return
    def _install_or_upgrade(self):
        #
        # Tools
        #
        self.cwd.pushd(TOOLS)
        superexec = InstallFile(self.options, 'superexec', 0) # Force copy!
        superexec.relocate(BIN_DIR)
        superexec.chmod(0774)
        # Link /usr/bin/python-mpx to/usr/lib/broadway/tools/python-mpx
        # A link works better for surviving upgrades.
        python_mpx = InstallFile(self.options, 'python-mpx', 1)
        python_mpx.duplicate(BIN_DIR)
        self.cwd.popd() 
        #
        # HTTP
        #
        self._update_html_templates(MOE_VERSION, RELEASE, SERIAL_NUMBER)
        #install files into the non-secure site
        self._install_web_content_in_root(properties.HTTP_ROOT)
        #install files to the secure site
        self._install_web_content_in_root(properties.HTTPS_ROOT)
        #
        # MPX/SERVICE/NETWORK/HTTPS
        #
        self.cwd.pushd(HTTPS)
        self.options.normal_message("Installing private key for secure HTTP")

        file = InstallFile(self.options, 'private.key', 1)
        file.relocate(CONFIGURATION_DIR)
        file.chmod(0660)

        self.cwd.popd()
        return
    def install(self):
        self._create_default_configuration()
        self._install_or_upgrade()
        return 0
    def upgrade(self):
        self._install_or_upgrade()
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
        ip = CoreInstallPackage()
        return ip.execute()
    finally:
        sys.argv=save_argv
        sys.stdout=save_stdout
        sys.stderr=save_stderr

if __name__ == '__main__':
    MAIN()

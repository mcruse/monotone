"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import commands
import getopt
import glob
import gzip
import os
import string
import sys
import time
import urllib

COMMAND = 'mpxupgrade'

# The directory where broadway lives
BROADWAY_DIR = '/usr/lib'

# The full path to broadway
BROADWAY_HOME = '%s/broadway' % BROADWAY_DIR
MAGIC_MOE = 'netinstall.tgz'

class MPXUpgrade:
    def __init__(self, message_server_in = None):
        self.message_server = message_server_in
        self._stage = 'Mediator Upgrade'
        return
    ##
    # Do the upgrade. 
    # If MOE is specified the it will be installed first.  This is done
    # by downloading the MAGIC_MOE and calling it's /install.1 script passing
    # passing any required arguments.  It is also passed the -post_install
    # argument which is a call back to this script to install the framework.
    # 
    def upgrade(self, source, packages, magic_moe, moe, upgrade_flag):
        STAGE = 'Upgrading Mediator'
        self.stage(STAGE)
        try:
            if moe:
                if not magic_moe:            
                    magic_moe = string.join(moe.split('/')[0:-1], '/')
                    magic_moe = magic_moe + "/" + MAGIC_MOE
                self.upgrade_moe(magic_moe, moe, source)
                sys.exit(0)  ## exit here.
            else:
                self.upgrade_framework(source, packages, upgrade_flag)
        except Exception, e:
            self.stage(STAGE)
            self.send_message(100,
                              'There was an error during upgrade -> %s' % e)
        return
    def upgrade_moe(self, magic_moe, moe, source):        
        STAGE = 'Upgrading the Mediator Operating Environment (OS)'
        self.stage(STAGE)
        try:
            self.send_message(10,
                              'Preparing for Mediator upgrade MOE [%s]' % moe)
            ## Open up socket for reading tar from source
            self.send_message(20, 'Initiating download of %r ...' % MAGIC_MOE)
            fd = self._get_upgrade_file(magic_moe)
            # Prepare the Meditator for update ...
            # ... Shutdown the framework.
            self.send_message(25, 'Shutting down the the current application.')
            os.system('/sbin/init 2')
            # ... Delete the current framework to "make room."
            self.send_message(30, 'Deleting any previous application')
            self._prepare_upgrade()
            # Extract contents of tar to root
            self.send_message(35, 'Downloading and extracting %r' % source)
            self._extract_tar(fd, '/') 
            upgrade = ''
            if upgrade_flag:
                upgrade = '--upgrade'
            post_command = ('%s --source %s --message_server %s %s' %
                            (COMMAND, source, self.message_server, upgrade))
            command = ("/install.wget.1 %s %s '%s'" %
                       (moe, self.message_server, post_command))
            self.send_message(90, 'Running command: ' + command)
            os.system(command)
        except Exception, e:
            raise Exception('Could not upgrade moe: %s' % e)
        return
    def upgrade_framework(self, source, packages, upgrade_flag):
        STAGE = 'Upgrading the Distribution'
        self.stage(STAGE)
        try:
            self.send_message(10,
                              'Initiating the distribution download [%s] ...' %
                              source)
            upgrade_file = self._get_upgrade_file(source)
            self.send_message(20, 'Removing the previous distribution.')
            self._prepare_upgrade()
            self.send_message(30,
                              'Downloading and extracting the distribution ...'
                              )
            self._extract_tar(upgrade_file, BROADWAY_DIR)
            self.send_message( 70,'Installing the distribution.')
            self._run_install_script(upgrade_flag)
            self.send_message(90, 'Executing post install ....')
            self._post_upgrade()
            ## This will shutdown the message server ...
            self.stage('Finalize')
            self.send_message(100, 'Framework upgrade complete!')
        except Exception ,e:
            raise Exception('Exception occurred while upgrading: %s' % e)
        return
    def _run_install_script(self, upgrade_flag):
        try:
            os.chdir(BROADWAY_HOME)
            command = './install'
            if upgrade_flag:
                command = command + ' -u'
            self.send_message( 75,'Running framework install script (%s)' %
                               command)
            output = os.popen(command,'r')
            ## So we can log
            lines = output.readlines()
            for l in lines:
                self.send_message(75, '> %s' % l)
            status = output.close()
            self.send_message(90, 'Install completed with status: %s' %
                              status)
        except Exception, e:
            raise Exception('Error while running install script: %s' % e)
        return
    ##
    # Read from the input stream and output to tar in a child process to
    # extract the files.
    def _extract_tar(self, upgrade_file, directory):
        BUFFSIZE = 4 * 1024
        pipe = os.popen('tar -C %s -pxzf -' % directory, 'w')
        while 1:
            data = upgrade_file.read(BUFFSIZE)
            if len(data) == 0:
                break
            pipe.write(data)
        pipe.close()
        return
    ##
    # Open up server and return the upgrade file
    # as a file object    
    def _get_upgrade_file(self, file_to_get):
        url = '%s' % (file_to_get)
        fd = urllib.urlopen(url)
        return fd
    ##
    # Do whatever is needed to bring framework back up
    def _post_upgrade(self):
        self.send_message(90, 'Going to init level 3 (starting framework)')
        os.system('init 3')
        return
    def _prepare_upgrade(self):
        self.send_message(10,'Going to init level 2')
        status = os.system('init 2')
        if status != 0:
            self.send_message(10,'Error during init: code == %d' % status)
        self.send_message(15,'Removing %s' % BROADWAY_HOME)       
        status = os.system('rm -rf %s' % BROADWAY_HOME)
        if status != 0:
            self.send_message(15,'Could not remove broadway directory: %s' %
                              BROADWAY_DIR)
        status = os.system('rm -f /var/mpx/log/msg*')
        return
    def stage(self, stage=None):
        if stage is not None:
            self._stage = stage
        return self._stage

    ## Send message to message server if specified, but always
    #  output to stdout
    #
    def send_message(self, completed, msg):
        if self.message_server:
            urllib.urlopen('%s?stage=%s&complete=%d&message=%s' %
                           (message_server, self.stage(),
                            completed, msg)).read()
        print "%s(%3d): %s" % (self.stage(), completed, msg)
        return
def display_help():
    print """
Usage: %s [options]

  Connect to a remote server, download and install new software on this
  Mediator.

  Options:
    -d or --distribution   The URL to the upgrade distribution.
    -g or --message_server The URL to the message server.
    -h or --help           Displays this help message and exits.
    -m or --moe            URL to the MOE to install.
    -M or --magic_moe      The URL of the MAGIC_MOE. [Aka %r]
    -p or --packages       Comma seperated list of packages to install from
                           the distribution (the default is all packages).
    -u or --upgrade        Upgrade this Mediator (the default is a fresh
                           install).

    -s or --source         Backwards compatible option for -d|--distribution.

  BUGS:
    @fixme Get rid of all the hard-coded paths!
    @fixme Improve recoverability from early failures (return to init level 5,
           etc...)
    @fixme Support standard Broadway command line options (debug, test,
           verbosity).
    @fixme Depricate -s|--source
""" % (COMMAND, MAGIC_MOE)
    return

if __name__ == '__main__':
    optlist, args = getopt.getopt(sys.argv[1:],
                                  'hM:m:d:p:g:us:',
                                  ['help',
                                   'magic_moe=',
                                   'moe=',
                                   'packages=',
                                   'message_server=',
                                   'upgrade',
                                   'distribution=',
                                   # Source is depricated.
                                   'source='])

    magic_moe = None
    moe = None
    packages = None
    message_server = None
    source = None
    upgrade_flag = 0

    #collect the options
    for o,a in optlist:
        if  o in ('-h','--help'):
            display_help()
            sys.exit(0)
        elif o in ('-M','--magic_moe'):
            magic_moe = a
        elif o in ('-m', '--moe'):
            moe = a
        elif o in ('-p', '--packages'):
            packages = a    
        elif o in ('-g', '--message_server'):
            message_server = a        
        elif o in ('-d', '--distribution', '-s', '--source'):
            source = a
        elif o in ('-u', '--upgrade'):
            upgrade_flag = -1

    if source == None:
        print 'Please specify the --source argument'
        display_help()
        sys.exit(1)

    u = MPXUpgrade(message_server)
    u.upgrade(source, packages, magic_moe, moe, upgrade_flag)

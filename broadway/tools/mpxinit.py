"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
# force user to create new mpxadmin account, named anything but cisco or
# mpxadmin.  
# become new user
# delete old mpxadmin
# update passwd file to allow other accounts to run
# update inittab to make init level 3 default on reboot
# run mpxconfig

# to prepare a mediator for shipping
# update inittab to make init level 1 default on reboot
# update passwd file to prevent any account other than mpxadmin from logging in
#  have mpxadmin shell run firstrun command
# update /etc/group file
# set up default mpxadmin/mpxadmin account
# remove

print '\nPlease wait while system is inspected...\n\r\n'

import sys
sys.path.append('/usr/lib/broadway')
import os as _os
import getpass as _getpass
from moab.user.manager import *

INITTAB_FILE = _os.path.join(properties.ETC_DIR, 'inittab')

INITIAL_SIGNON_MESSAGE="""

Welcome to the Initial Configuration of the Network Building Mediator.

Cisco security policy requires that no default username or password
credentials exist before this device may become operational.  The
operator will need to create a username and password for the initial
administration account before this device may be commissioned.  

The username cannot be either "mpxadmin" or "cisco".

The default password rules are:

Must be at least 12 characters in length for administrators.
Must not exceed 80 characters in length.
May only contain letters, numbers & punctuation characters.
Must not equal the username or the username reversed.
Must not equal any variation of "cisco" or "mpxadmin".
Must not repeat any characters more than three times in a row.
Must contain characters from at least three of the four character groups:
   UPPERcase & lowercase letters, numbers and punctuation characters

If the administration credentials are lost, refer to the user guide
for instructions on how to reset the device to this initial condition.

"""

# instructions to recover initial state:
# Reboot device.  
# When "Press `ESC' to enter the menu... " prompt appears, press ESC
# Press "e"
# Press down arrow to highlight "kernel" line
# Press "e", again
# Add " single" to end of line
# Press Enter
# Press "b"
# Device should start up in single user mode without needing a password
# Type "mpxinitialize"

PASSWORD_PROMPT="Please enter a username for the administrator account: "

def MpxInit():
    # welcome the user
    print INITIAL_SIGNON_MESSAGE
    yn = raw_input("Ready to proceed? (y/n) ")
    if yn != 'y':
        #print 'User not ready to proceed'
        raise EConfigurationIncomplete('Operator not ready to configure')
    print
    user = raw_input("Please enter new Administrator user name: ")
    print
    #test the username for suitability
    p1 = _getpass.getpass("Enter a new password for %r: " % user)
    p2 = _getpass.getpass("Retype the new password: ")
    if not p1:
        raise EConfigurationIncomplete("Empty passwords are not allowed.")
    if p1 != p2:
        raise EConfigurationIncomplete("Entries did not match.")
    # perform complexity test on password
    error = valid_password(p1, user, True) 
    if error is not None:
        raise EConfigurationIncomplete(error)
    # check if user already exists, if so proceed if in mpxadmin group
    passwd = PasswdFile()
    passwd.load()
    group = GroupFile()
    group.load()
    #get or create the mpxadmin passwd entry
    pw = PasswdEntry()
    pw.user(user)
    pw.uid(0)
    pw.gid(0)
    print 'set password'
    pw.passwd(p1) #give it the new password, 
    print 'set shell'
    pw.shell("/bin/sh")
    print 'remove mpxadmin user'
    pw.user_type('mpxadmin', passwd, group) #make sure it's in mpxadmin group
    print 'save group'
    group.save()
    print 'save password'
    passwd.save() #make sure new user saved before deleting mpxadmin user
    try:
        del passwd['mpxadmin']
    except:
        print 'mpxadmin delete exception'
    passwd.save() #save after deleting mpxadmin
    # change default inittab to run at level 3
    filename = properties.ETC_DIR + '/inittab'
    file = open(filename, 'r+')
    lines = file.readlines()
    new_lines = []
    for line in lines:
        if line.find('id:1:initdefault:') == -1:
            new_lines.append(line)
        else:
            new_lines.append('id:3:initdefault:\n')
    file.seek(0)
    file.writelines(new_lines)
    file.truncate()
    file.close()
    #launch mpxconfig
    _os.spawnlp(_os.P_WAIT, 'mpxconfig', 'mpxconfig')
    return 0

def MpxShipIt(force=False):
    # welcome the user
    if not force:
        print 'This command will set up initial mpxadmin account'
        yn = raw_input("Ready to proceed? (y/n) ")
        if yn != 'y':
            print 'User not ready to proceed'
            sys.exit( 0 )
    # for mpxadmin account to have mpxadmin password and login shell to mpxinit
    passwd = PasswdFile()
    passwd.load()
    group = GroupFile()
    group.load()
    try:
        # @TODO: remove print stuff before final build
        # leave root in as temporary back door until 
        # this username business is tested
        print "del passwd['root']"
    except:
        pass
    if 'mpxadmin' not in passwd:
        pw = PasswdEntry()
        pw.user('mpxadmin')
        pw.user_type('mpxadmin', passwd, group)
        pw.uid(0)
        pw.gid(0)
    else:
        pw = passwd['mpxadmin']
    pw.passwd('mpxadmin', False) # don't validate
    pw.shell("/usr/lib/broadway/tools/mpxinit")
    group.save()
    passwd.save() 
    # change default inittab to run at level 1
    filename = properties.ETC_DIR + '/inittab'
    file = open(filename, 'r+')
    lines = file.readlines()
    new_lines = []
    for line in lines:
        if line.find(':initdefault:') == -1:
            new_lines.append(line)
        else:
            new_lines.append('id:1:initdefault:\n')
    file.seek(0)
    file.writelines(new_lines)
    file.truncate()
    file.close()
    return 0

if __name__ == '__main__':
    import sys
    if '--restore-default' in sys.argv:
        #prepare mediator for shipment
        MpxShipIt('--force' in sys.argv)
    else:
        for i in range(10): #give them 10 attempts
            try:
                #first log in.  Create new mpxadmin level user
                MpxInit()
                _os.system( "reboot -f" )
            except Exception, e:
                print
                print str(e)
                raw_input("Press Enter to try again: ")


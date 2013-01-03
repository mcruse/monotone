"""
Copyright (C) 2010 2011 Cisco Systems

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
#
# update_srna_network.py: Initiates the cascade of events that is SRNA update.
# ASSUMES:
#	*Machine on which this script runs MUST be NBM-Mgr. Run as:
#        python-mpx -m tools.srna.update_srna_network -p<password> -f<addr_list>
#       -has Python installed to run this script as __main__.
#		-has openssl installed.
#		-is registered properly with a public key in the 
#			/home/mpxadmin/.ssh/authorized_keys file, so that the SRNA admin
#			need not enter username or password.
#	*GENSSLPEMS file is located in same dir as this script.
# TODO: Make provisions for username/password combinations for scp transfers
#		OTHER than mpxadmin/mpxadmin!!! Actual username could still be mpxadmin,
#		but password could be the passphrase given as the 2nd cmd line arg.
#
# 	*Read in list of IP addresses of NBMs directly accessible to machine on which
#		this script runs, for which keys are to be updated.
#	*Regen CA on local machine, at ./demoCA/, with given passphrase.
#	*scp CA from ./demoCA/ to target NBMs.
#	*scp script gen_ssl_pems.py to target NBMs.
#	*scp desired openssl.cnf file from this script's dir to /usr/ssl/ on NBM.
#	*Order NBMs to use gen_ssl_pems.py to regen SSL keys, with given passphrase.
#	*Order NBMs to use either authentication-only or full-encryption.
#	*Reboot NBMs.
#

import stat
import os, os.path
import shutil
from subprocess import Popen, call, PIPE, STDOUT
import sys
import string
import time
from mpx import properties as prop
join=os.path.join

# Init local vars:
SUBJ="/C=US/ST=California/L=PaloAlto/CN=CertificateAuthority/OU=OpenSourceETG/O=NBM_SRNA"
SRNATMP_DATA = 'srnatmp'
SRNATMP_DATA_DIR = join(prop.TEMP_DIR, SRNATMP_DATA)
CATOP = 'demoCA'
CAKEY = 'cakey.pem'
CAREQ = 'careq.pem'
CACERT = 'cacert.pem'
GENSSLPEMS = 'GenSrnaPems.pyc' # Python script that runs on target NBMs to generate new PEMs
SRNA_UPDATE_TGZ = 'srna_update.tgz'

# Parse cmdline args:
password = ''
addr_list = ''
for arg in sys.argv:
    # Get the private key passphrase from command line:
    if arg[:2] == '-p':
        password = arg[2:]
        print 'update_srna_network: Private Key Passphrase= %s' % password
        if len(password) < 5:
            print 'update_srna_network: Failed. Called without private '\
                    'passphrase (-p)!'
            exit(-1)
    elif arg[:2] == '-f':
        addr_list = arg[2:]
        print 'update_srna_network: Target NBM IP Address List File = %s'\
                % addr_list
        if not os.path.exists(addr_list):
            print 'update_srna_network: Failed. Bad Target NBM IP Address List'\
                    'File: %s (-f). Remember to use full absolute path.' \
                    % addr_list
            exit(-2)

print 'update_srna_network: Regenerating CA...'
print 'update_srna_network: Creating top-level dir to be tarred: %s' \
        % SRNATMP_DATA_DIR
if os.path.exists(SRNATMP_DATA_DIR):
    shutil.rmtree(SRNATMP_DATA_DIR) # waste 'em all if dir already exists
os.mkdir(SRNATMP_DATA_DIR) # create dir
os.chdir(SRNATMP_DATA_DIR)
print "update_srna_network: Re-creating CA dir tree..."
os.mkdir(CATOP) # create dir
os.mkdir(join(CATOP, 'certs')) # create dir
os.mkdir(join(CATOP, 'crl')) # create dir
os.mkdir(join(CATOP, 'newcerts')) # create dir
os.mkdir(join(CATOP, 'private')) # create dir
serial = join(CATOP, 'serial')
os.mknod(serial, 0666)
serial_file = open(serial, 'w')
serial_file.write('00')
serial_file.close()
os.mknod(join(CATOP, 'index.txt'), 0666)
print 'update_srna_network: Creating new CA key...'
key_file = join(CATOP, 'private', CAKEY)
req_file = join(CATOP, CAREQ)
proc_req = Popen(['openssl',
                  'req',
                  '-subj', SUBJ,
                  '-new',
                  '-keyout', key_file,
                  '-passin', 'pass:%s' % password,
                  '-passout', 'pass:%s' % password,
                  '-days', '9125', # 25 years
                  '-out', req_file],
                  stderr=PIPE)
output = proc_req.communicate()
if proc_req.returncode != 0:
    print 'update_srna_network: Call to "openssl req" failed: %d.\nstderr:\n%s'\
            '. Abort SRNA update.' % (proc_req.returncode, output[1]) 
    exit(-3)

from tools.srna.update_srna_local import get_time
start_time = get_time()
if not start_time:
    exit(-4)

print 'update_srna_network: Creating new CA cert, using CA key...'
print 'update_srna_network: cwd = %s' % os.getcwd()
proc_ca = Popen(['openssl',
                 'ca',
                 '-out', join(CATOP, CACERT),
                 '-config', '%s/srna_openssl.cnf' % prop.SRNA_TOOLS,
                 '-batch',
                 '-passin', 'pass:%s' % password,
                 '-keyfile', key_file,
                 '-selfsign', '-extensions', 'v3_ca',
                 '-startdate', start_time, # yesterday
                 '-days', '9125', # 25 years
                 '-infiles', req_file],
                 stderr=PIPE)
output = proc_ca.communicate()
if proc_ca.returncode != 0:
    print 'update_srna_network: Call to "openssl ca" failed: %d.\nstderr:\n%s'\
            '. Abort SRNA update.' % (proc_ca.returncode, output[1]) 
    exit(-5)

print 'update_srna_network: Creating new DH cert, using CA key...'
proc_dh = Popen(['openssl', 'dhparam', '-out', 'srna_dh1024.pem', '-2', '1024'],
                stderr=PIPE)
output = proc_dh.communicate()
if proc_dh.returncode != 0:
    print 'update_srna_network: Call to "openssl dhparam" failed: %d.'\
            '\nstderr:\n%s. Abort SRNA update.' % (proc_dh.returncode, output[1]) 
    exit(-5)

# For each target NBM address in the given file:
#	*Move existing CA dir tree, if any.
#	*Send CA dir tree just created above.
#	*Send gen_ssl_pems.py.
#	*Run gen_ssl_pems.py with appropriate cmd line args.
#	*Reboot target NBM.
#
ADMINUSER = 'mpxadmin'
# Place password into file for tarring:
password_path = 'password'
password_file = open(password_path, 'w')
password_file.write(password)
password_file.close()
os.chmod(password_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
print 'update_srna_network: Tar all files for scp to target NBMs...'
os.chdir(prop.TEMP_DIR)
proc_tar = Popen(['tar',
                  'czvf',
                  SRNA_UPDATE_TGZ,
                  SRNATMP_DATA],
                  stderr=PIPE)
output = proc_tar.communicate()
if proc_tar.returncode != 0:
    print 'update_srna_network: Call to "tar" failed: %d.\nstderr:\n%s.'\
            'Abort SRNA update.' % (proc_tar.returncode, output[1]) 
    exit(-6)

IP_ADDR_FILE = 'ip_addrs'
nonupdate_file = open('nonupdated.txt', 'w')
try:
    addr_list_file = open(addr_list, 'r')
    for ip_addr in addr_list_file:
        ip_addr = string.strip(ip_addr,string.whitespace)
        SSHTGT = ADMINUSER + '@' + ip_addr
        try:
            print 'Getting SSH_CONNECTION info from %s' % ip_addr
            proc_ssh_conn_info = Popen(['ssh', SSHTGT, 'echo $SSH_CONNECTION'],
                                       stdout=PIPE, stderr=PIPE)
            output = proc_ssh_conn_info.communicate()
            if proc_ssh_conn_info.returncode != 0:
                raise Exception('update_srna_network: Unable to run '\
                                '"echo $SSH_CONNECTION" on NBM'\
                                ' at %s.\nstderr:\n%s' % (ip_addr, output[1]))
            # Parse output from remote echo cmd to get (maybe) internal IP on 
            # NBM. Have to acct for occasional '::ffff:192.168.1.100' (or 
            # similar) showing up in the SSH_CONNECTION report:
            parsed = string.split((string.split(output[0], ' ')[2]),':')
            internal_ip = parsed[len(parsed)-1]
            print 'update_srna_network: External addr = %s. '\
                    ' Internal addr = %s.' % (ip_addr, internal_ip)
            print 'update_srna_network: Creating file containing addresses.'
            addr_file = open(IP_ADDR_FILE, 'w')
            addr_file.write(ip_addr + ',' + internal_ip)
            addr_file.close()
            print 'update_srna_network: scping SRNA_UPDATE_TGZ and ip_addr'\
                    ' file to NBM at %s' % ip_addr
            proc_scp = Popen(['scp', SRNA_UPDATE_TGZ, IP_ADDR_FILE,
                              SSHTGT + ':'], stderr=PIPE)
            output = proc_scp.communicate()
            if proc_scp.returncode != 0:
                raise Exception('update_srna_network: Unable to scp TGZ to NBM'\
                                ' at %s.\nstderr:\n%s' % (ip_addr, output[1]))
            print 'update_srna_network: Restarting framework on NBM at %s' \
                    % ip_addr
            proc_ssh_dnr = Popen(['ssh', SSHTGT, "dnr &"], stderr=PIPE)
            output = proc_ssh_dnr.communicate()
            if proc_ssh_dnr.returncode != 0:
                raise Exception('update_srna_network: Unable to run dnr on NBM'\
                                ' at %s.\nstderr:\n%s' % (ip_addr, output[1]))
        except Exception, e:
            print e
            print 'update_srna_network: Continuing to next IP address in file '\
                    '"%s".' % addr_list
            nonupdate_file.write(ip_addr + '\n')
            continue
except Exception, e:
    print e

# Wrap it up:
addr_list_file.close()
nonupdate_file.close()
print 'update_srna_network: All done for now. Target NBMs should reboot soon. '\
    'List of nonupdated NBM IP addresses:'
nonupdate_file = open('nonupdated.txt', 'r')
for ip_addr in nonupdate_file:
    print ip_addr
nonupdate_file.close()
# Remove scratch-space stuff (in /tmp/):
os.chdir(prop.TEMP_DIR)
if os.path.exists(SRNATMP_DATA):
    shutil.rmtree(SRNATMP_DATA) # waste 'em all if dir still exists
if os.path.exists(IP_ADDR_FILE):
    os.remove(IP_ADDR_FILE) # waste 'em all if dir still exists
# If this script is running on an NBM-Mgr, assume that this NBM-Mgr is intended
# to be a permanent part of the network. Ensure that a copy of SRNA_UPDATE_TGZ
# is located in ADMIN_HOME, and restart framework (just like any other target):
if os.path.exists(join(prop.FRAMEWORK_TYPE_DIR, 'nbmmgr')):
    shutil.move(SRNA_UPDATE_TGZ, prop.ADMIN_HOME) # "cleans up" TGZ from /tmp/
    os.chdir(prop.ADMIN_HOME)
    proc_local_dnr = Popen((join(prop.SRNA_TOOLS,'dnr'),'&'))
    output = proc_local_dnr.communicate()
    if proc_local_dnr.returncode != 0:
        raise Exception('update_srna_network: Unable to run dnr on local '\
                        'NBM-Mgr at %s.\nstderr:\n%s' % (ip_addr, output[1]))
else: # host is _not_ an NBM-Mgr, so finish cleanup without MFW restart:
    os.remove(SRNA_UPDATE_TGZ) # waste 'em all if dir still exists



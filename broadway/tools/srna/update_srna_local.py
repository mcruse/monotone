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
# UpdateSrnaTop.py: Runs automatically (from inside /etc/rc.mfw.pyc, created
# from moab/linux/rc.mfw.py) if and when an SRNA_UPDATE_TGZ file is detected.
#
# Use Python, rather than bash, scripting to allow easier access to 
# mpx.properties.

import os
import sys
import os.path
import socket
from fcntl import ioctl
from struct import pack, unpack
import errno
import shutil
import stat
import time
import string
from subprocess import Popen, PIPE, STDOUT
from mpx import properties as prop
from mpx.lib import msglog

join = os.path.join

try:
    IOCTL = None
    try:
        import IOCTL
        SIOCGIFADDR = IOCTL.SIOCGIFADDR
        SIOCGIFHWADDR = IOCTL.SIOCGIFHWADDR
    except:
        import IN
        if hasattr(IN,'SIOCGIFADDR') and hasattr(IN,'SIOCGIFHWADDR'):
            SIOCGIFADDR = IN.SIOCGIFADDR
            SIOCGIFHWADDR = IN.SIOCGIFHWADDR
        else:
            SIOCGIFADDR = 35093
            SIOCGIFHWADDR = 35111
        del IN
finally:
    del IOCTL

def ip_mac_address(interface):
    strIpAddr = '0.0.0.0'
    if interface == 'all':
        return (strIpAddr, None) 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ifreq = pack('16s16s', interface, '')
    try:
        ifreqIp = ioctl(s.fileno(), SIOCGIFADDR, ifreq)
        addr = unpack('20x4B8x', ifreqIp)
        strIpAddr = '%d.%d.%d.%d' % addr 
        ifreqMac = ioctl(s.fileno(), SIOCGIFHWADDR, ifreq)
        mac = unpack('18x6B8x', ifreqMac)
        strMac = '%2.2x:%2.2x:%2.2x:%2.2x:%2.2x:%2.2x' % mac
    except:
        s.close()
        return (None, None)
    s.close()
    return (strIpAddr, strMac)

# Specify map of names of files to be created:
KEY, REQ, CERT = range(0,3)
g_mapFiles = \
{\
    KEY:'srna_key.pem',
    REQ:'srna_req.pem',
    CERT:'srna_cert.pem'
}

# Generate new PEMs without user input.
# Configure strings for use as args in 'openssl' calls:
strSubjBase = '/C=US/ST=Alaska/L=FortCollins/CN='
lstArgsReq = ['openssl',
              'req',
              '-passin', 'pos_req_passin',
              '-passout', 'pos_req_passout',
              '-subj', 'pos_req_subj',
              '-new',
              '-keyout', 'pos_req_keyout',
              '-out', 'pos_req_out',
              '-days', '9125', # 25 years
              '-config', join(prop.SRNA_TOOLS, 'srna_openssl.cnf')]
lstArgsSign = ['openssl',
               'ca',
               '-passin', 'pos_ca_passin',
               '-key', 'pos_ca_keypass',
               '-policy', 'policy_anything',
               '-out', 'pos_ca_out',
               '-batch',
               '-config', join(prop.SRNA_TOOLS, 'srna_openssl.cnf'),
               '-startdate', 'pos_ca_start_time', # yesterday
               '-days', '9125', # 25 years
               '-infiles', 'pos_ca_infiles']
lstArgsStrip = ['openssl',
                'rsa',
                '-passin', 'pos_rsa_passin',
                '-in', 'pos_rsa_in',
                '-out', 'pos_rsa_out']
# Index lists to ease repeated substitutions later :
pos_req_passin = lstArgsReq.index('pos_req_passin')
pos_req_passout = lstArgsReq.index('pos_req_passout')
pos_req_subj = lstArgsReq.index('pos_req_subj')
pos_req_keyout = lstArgsReq.index('pos_req_keyout')
pos_req_out = lstArgsReq.index('pos_req_out')
pos_ca_passin = lstArgsSign.index('pos_ca_passin')
pos_ca_keypass = lstArgsSign.index('pos_ca_keypass')
pos_ca_out = lstArgsSign.index('pos_ca_out')
pos_ca_start_time = lstArgsSign.index('pos_ca_start_time')
pos_ca_infiles = lstArgsSign.index('pos_ca_infiles')
pos_rsa_passin = lstArgsStrip.index('pos_rsa_passin')
pos_rsa_in = lstArgsStrip.index('pos_rsa_in')
pos_rsa_out = lstArgsStrip.index('pos_rsa_out')

def update_srna():
    try:
        # If dnr is not found in /usr/bin/, copy it to there:
        # TODO: Move this task from here into an installation script, but 
        # which one? What build changes are required?...
        dnr_src_path = join(prop.SRNA_TOOLS, 'dnr')
        if not os.path.exists(dnr_src_path):
            msglog.log('update_srna()', msglog.types.ERR,
                       'Could not find %s. Aborting SRNA update.' % dnr_src_path)
            return
        dnr_dst_path = join(prop.BIN_DIR, 'dnr')
        shutil.copy2(dnr_src_path, dnr_dst_path) # always copy, to avoid de-synch
        # If SRNA_UPDATE_TGZ does not exist, then nothing to do this time:
        if not os.path.exists(prop.SRNA_UPDATE_TGZ):
            return
        msglog.log('update_srna()', msglog.types.INFO,
                   'Found file "%s". Updating SRNA CA, certs, and keys.'\
                   % prop.SRNA_UPDATE_TGZ)
        if not untar():
            return
        contact_addr, internal_addr = get_addrs()
        password = validate_materials()
        if not password:
            return
        # Insert password into proper places in openssl call lists:
        pass_arg = 'pass:' + password
        lstArgsReq[pos_req_passin] = pass_arg
        lstArgsReq[pos_req_passout] = pass_arg
        lstArgsSign[pos_ca_passin] = pass_arg
        lstArgsSign[pos_ca_keypass] = password
        lstArgsStrip[pos_rsa_passin] = pass_arg
        # Get and validate current time (important for certificate start dates
        # and durations):
        cur_time = get_time() # rtns value in string fmt
        if not cur_time:
            return
        # Insert start time in proper places:
        lstArgsSign[pos_ca_start_time] = cur_time
        # Prep shared CA's "database" files (which track generated certs):
        init_CA_text_db()
        # Create a local cert and private key for each interface supported by
        # this NBM's hardware platform:
        gen_interface_pems('eth%s', contact_addr, internal_addr)
        # TODO: add other calls to gen_interface_pems() here for "tun", "vibr", 
        # etc.???)
        # Delete old SRNA security materials tree, and rename temp tree to be
        # new permanent tree:
        if os.path.exists(prop.SRNA_DATA):
            shutil.rmtree(prop.SRNA_DATA, True)
        os.rename(prop.SRNATMP_DATA, prop.SRNA_DATA)
    except Exception, e:
        print str(e)
        msglog.exception(prefix='Unhandled')
        msglog.log('update_srna()', msglog.types.ERR,
                   'Abort SRNA update.')
    return

def untar():
    # Rmv any temp files left over from last update:
    if os.path.exists(prop.SRNATMP_DATA):
        shutil.rmtree(prop.SRNATMP_DATA, True) # waste 'em, ignoring errors
    # Get thee to the desired working directory:
    os.chdir(prop.DATA_DIR)
    proc_untar = Popen(('tar', 'xzvf', prop.SRNA_UPDATE_TGZ),\
                   stdout=PIPE, stderr=PIPE)
    output = proc_untar.communicate()
    if proc_untar.returncode != 0:
        msglog.log('update_srna()', msglog.types.ERR,
                   'Could not untar file "%s". Abort SRNA update.\n'\
                   'stdout:\n%s\nstderr:\n%s'\
                   % (prop.SRNA_UPDATE_TGZ, output[0], output[1]))
        return False
    os.remove(prop.SRNA_UPDATE_TGZ) # rmv unneeded TGZ file:
    return True

def get_addrs():
    contact_addr = None 
    internal_addr = None 
    if os.path.exists(prop.SRNA_IP_ADDR_FILE):
        ip_addr_file = open(prop.SRNA_IP_ADDR_FILE, 'r')
        addrs = ip_addr_file.read(1024)
        ip_addr_file.close()
        os.remove(prop.SRNA_IP_ADDR_FILE)
        addr_pr = string.split(addrs, ',')
        if len(addr_pr) != 2:
            msglog.log('get_addrs()', msglog.types.WARN,
                       'Invalid list of addresses: %s. Using default '\
                       'interface IP addresses to generate certs/keys.')
        else:
            for i in range(0,2):
                len_addr = len(addr_pr[i])
                if len_addr < 7 or len_addr > 15:
                    msglog.log('get_addrs()', msglog.types.WARN,
                               'Invalid address: %s. Using default'\
                               'interface IP addresses to generate '\
                               'certs/keys.')
                    break
            else:
                contact_addr = addr_pr[0]
                internal_addr = addr_pr[1]
                msglog.log('get_addrs()', msglog.types.INFO,
                           'Contact: %s. Internal %s.' \
                           % (contact_addr, internal_addr))
    return (contact_addr, internal_addr)

def validate_materials():
    if not os.path.exists(prop.SRNATMP_DATA):
        msglog.log('update_srna()', msglog.types.ERR,
                   'File "%s" did not contain directory "%s". '\
                   'Abort SRNA update.'\
                   % (prop.SRNA_UPDATE_TGZ, prop.SRNATMP_DATA))
        return False
    os.chdir(prop.SRNATMP_DATA) # new cwd, freshly untarred cwd
    PASSWORD_PATH = join(prop.SRNATMP_DATA, 'password')
    if not os.path.exists(PASSWORD_PATH):
        msglog.log('update_srna()', msglog.types.ERR,
                   'File "%s" did not contain file "%s". '\
                   'Abort SRNA update.'\
                   % (prop.SRNA_UPDATE_TGZ, PASSWORD_PATH))
        return False
    # Double check password params:
    MIN_PASSWORD_LEN = 5
    MAX_PASSWORD_LEN = 512
    try:
        statPassFile = os.stat(PASSWORD_PATH)
        if statPassFile.st_size < MIN_PASSWORD_LEN:
            msglog.log('update_srna()', msglog.types.ERR,
                       'Password file is too small: less than %d bytes.'\
                       'Abort SRNA update.' % MIN_PASSWORD_LEN)
            return False
        if statPassFile.st_size > MAX_PASSWORD_LEN:
            msglog.log('update_srna()', msglog.types.ERR,
                       'Password file is too large: more than %d bytes.'\
                       'Abort SRNA update.' % MAX_PASSWORD_LEN)
            return False
        filePassword = open(PASSWORD_PATH, 'r')
        password = filePassword.read(MAX_PASSWORD_LEN)
        filePassword.close()
        password = string.strip(password, string.whitespace)
        os.remove(PASSWORD_PATH)
    except:
        msglog.exception(prefix='Unhandled')
        msglog.log('update_srna()', msglog.types.ERR,
                   'Abort SRNA update.')
        return False
    return password

# Get current date and time, and do a quick validation:
def get_time():
    tm = time.gmtime(time.time()-86400) # get time 24 hrs ago, to bypass small start time diffs
    if tm.tm_year < 2010:
        msglog.log('update_srna', msglog.types.ERR,
                   'Bad local time on NBM: Set to proper local time'\
                   ' and try again. Abort current SRNA update.')
        return False
    return time.strftime('%y%m%d%H%M%SZ', tm)

# Init the index.txt and serial files for the local copy of the CA (shared
# secret):
def init_CA_text_db():
    os.chdir(prop.SRNATMP_DATA)
    text_db_path = join(prop.SRNATMP_DATA, 'demoCA', 'index.txt') 
    if os.path.exists(text_db_path):
        os.remove(text_db_path)
    os.mknod(text_db_path, 0777) # WR for everyone
    serial_path = join(prop.SRNATMP_DATA, 'demoCA', 'serial')
    if os.path.exists(serial_path):
        os.remove(serial_path)
    os.mknod(serial_path, 0777) # WR for everyone
    fileSerial = open(serial_path, 'w')
    fileSerial.write('00') # restart serial numbering
    fileSerial.close()
    return

def gen_interface_pems(if_mask, contact, internal):
    # Gonna need local IP address(es) for key gen. (Must generate one complete 
    # set of PEMs for each interface, due to "commonName" requirements for 
    # OpenSSL.):
    for i in range(0, 10): # scan up to 10 Ethernet interfaces on this HW platform
        os.chdir(prop.SRNATMP_DATA)
        interface = if_mask % str(i)
        ip_addr, mac = ip_mac_address(interface)
        if not mac:
            break # reached the last of the (hopefully sequential) interfaces
        interface_path = join(prop.SRNATMP_DATA, interface)
        if not os.path.exists(interface_path):
            os.mkdir(interface_path)
        # Generate certificate request and local private key:
        msglog.log('gen_interface_pems()',msglog.types.INFO, 'contact = %s, internal = %s, ip_addr = %s' % (contact, internal, ip_addr))
        if contact != internal and ip_addr == internal:
            ip_addr = contact
        subj = strSubjBase + ip_addr + '/OU=' + mac
        key_path = join(interface_path, g_mapFiles[KEY])
        lstArgsReq[pos_req_subj] = subj
        lstArgsReq[pos_req_keyout] = key_path
        req_path = join(interface_path, g_mapFiles[REQ])
        lstArgsReq[pos_req_out] = req_path
        proc_req = Popen(lstArgsReq, stderr=PIPE)
        output = proc_req.communicate()
        if proc_req.returncode != 0:
            msglog.log('update_srna', msglog.types.ERR,
                       'Call to "openssl req" failed: %d.'\
                       '\nstderr:\n%s\nAbort update for'\
                       ' interface %s.' % (proc_req.returncode, output[1],
                                           interface))
            continue
        # Sign certificate request:
        lstArgsSign[pos_ca_out] = join(interface_path, g_mapFiles[CERT])
        lstArgsSign[pos_ca_infiles] = req_path
        proc_ca = Popen(lstArgsSign, stderr=PIPE)
        output = proc_ca.communicate()
        if proc_ca.returncode != 0:
            msglog.log('update_srna', msglog.types.ERR,
                       'Call to "openssl ca" failed: %d.'\
                       '\nstderr:\n%s\nAbort update for'\
                       ' interface %s.' % (proc_ca.returncode, output[1],
                                           interface))
            continue
        # Strip password from new private key, to allow batch-mode SRNA comms:
        key_path_enc = key_path + '.enc'
        shutil.copy2(key_path, key_path_enc) # save encrypted file
        lstArgsStrip[pos_rsa_in] = key_path_enc 
        lstArgsStrip[pos_rsa_out] = key_path
        proc_rsa = Popen(lstArgsStrip, stderr=PIPE)
        output = proc_rsa.communicate()
        if proc_rsa.returncode != 0:
            msglog.log('update_srna', msglog.types.ERR,
                       'Call to "openssl rsa" failed: %d.'\
                       '\nstderr:\n%s\nAbort update for'\
                       ' interface %s.' % (proc_rsa.returncode, output[1],
                                           interface))
            continue
        continue

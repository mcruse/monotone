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
# _test_case_tools_srna.py: Should run before mpx/lib/_test_case_rna.py or 
# mpx/service/network/_test_case_rna.py, to ensure that those tests have
# certificates, keys, and a Certificate Authority available when they run.
#
# ASSUME:
#    (1) Test computer has user "mpxadmin", with any password as long as the 
#        account is configured to allow passwordless ssh/scp access to 
#        mpxadmin@localhost. If passwordless access is NOT configured, then the
#        sshd daemon will ask for the password at one or more points in the
#        execution of the test(s).
#    (2) This TestCase runs only on a test computer, NOT inside an NBM 
#        framework, working in a directory that is NOT /home/mpxadmin/.

import time
import os
from os.path import join, exists
import shutil
import subprocess
from subprocess import Popen, call, PIPE, STDOUT
from threading import Thread

from mpx_test import DefaultTestFixture, main
from mpx import properties as prop


# Define convenience function. Returns name of calling code object (eg function,
# module, etc.):
import sys
def f_name():
    return sys._getframe(1).f_code.co_name # a little too Python ver-specific... 

print 'prop.SRNA_UPDATE_TGZ: %s' % prop.SRNA_UPDATE_TGZ

PRESERVE_DIR = join(prop.TEMP_DIR, 'test_srna')
LOCAL_TGT_FILES = [prop.SRNA_DATA, prop.SRNA_CACERT, prop.SRNA_CAKEY,
                   prop.SRNA_DH1024, prop.SRNA_CERT_eth0, prop.SRNA_KEY_eth0]

ADMINUSER = 'mpxadmin'
ADMIN_HOME = join('/home', ADMINUSER)
ADMINUSER_LOGIN = '%s@localhost' % ADMINUSER

UPDATE_SRNA_NETWORK = 'update_srna_network'
UPDATE_SRNA_NETWORK_PATH = join(prop.SRNA_TOOLS, UPDATE_SRNA_NETWORK + '.pyc')

UPDATE_SRNA_LOCAL = 'update_srna_local'
UPDATE_SRNA_LOCAL_PATH = join(prop.SRNA_TOOLS, UPDATE_SRNA_LOCAL + '.pyc')

SRNA_OPENSSL_CNF = 'srna_openssl.cnf'
SRNA_OPENSSL_CNF_PATH = join(prop.SRNA_TOOLS, SRNA_OPENSSL_CNF)

SRNA_UPDATE_TGZ = 'srna_update.tgz'
SRNA_UPDATE_TGZ_SRC_PATH = join(prop.TEMP_DIR, SRNA_UPDATE_TGZ)
# Have to use separate target path since update_srna_network is unaware of
# actual path to ADMIN_HOME on target NBM. So, has to be static at
# /home/mpxadmin:
SRNA_UPDATE_TGZ_TGT_PATH = join(ADMIN_HOME, SRNA_UPDATE_TGZ)

IP_ADDRS = 'ip_addrs'
IP_ADDRS_PATH = join(prop.TEMP_DIR, IP_ADDRS)

ADDR_LIST = 'addr_list'
ADDR_LIST_PATH = join(prop.TEMP_DIR, ADDR_LIST)

PASSWORD = 'qwerty'

class TestCase(DefaultTestFixture):
    def __init__(self, x):
        DefaultTestFixture.__init__(self, x)
        self.name = self.__class__.__name__
        self.start_dir = os.getcwd()
        # Create dir for preserving data and results between tests:
        if exists(PRESERVE_DIR):
            shutil.rmtree(PRESERVE_DIR, True)
        os.makedirs(PRESERVE_DIR, 0777)
        print 'prop.SRNA_TOOLS: %s' % prop.SRNA_TOOLS
        print 'UPDATE_SRNA_NETWORK_PATH: %s' % UPDATE_SRNA_NETWORK_PATH
        print 'UPDATE_SRNA_LOCAL_PATH: %s' % UPDATE_SRNA_LOCAL_PATH
        print 'SRNA_OPENSSL_CNF_PATH: %s' % SRNA_OPENSSL_CNF_PATH
        print 'SRNA_UPDATE_TGZ_SRC_PATH: %s' % SRNA_UPDATE_TGZ_SRC_PATH
        print 'IP_ADDRS_PATH: %s' % IP_ADDRS_PATH
        print 'ADDR_LIST_PATH: %s' % ADDR_LIST_PATH
        return
    def __del__(self):
        # Remove preservation dir:
        shutil.rmtree(PRESERVE_DIR, True)
#        DefaultTestFixture.__del__(self)
        return
    def setUp(self):
        pfx = '%s.%s: ' % (self.name, f_name())
        DefaultTestFixture.setUp(self)
        # Delete any existing SRNA secure materials trees from 
        # "target NBM":
        print 'prop.SRNATMP_DATA: %s' % prop.SRNATMP_DATA
        if exists(prop.SRNATMP_DATA):
            shutil.rmtree(prop.SRNATMP_DATA, True) # ignore errors
        if exists(prop.SRNA_UPDATE_TGZ):
            os.remove(prop.SRNA_UPDATE_TGZ, True) # ignore errors
        # Delete any existing SRNA secure materials trees from 
        # "admin NBM-Mgr":
        if exists(SRNA_UPDATE_TGZ_SRC_PATH):
            os.remove(SRNA_UPDATE_TGZ_SRC_PATH)
        if exists(IP_ADDRS_PATH):
            os.remove(IP_ADDRS_PATH)
        # Verify that the update_srna_network.pyc tool file is in proper place:
        if not exists(UPDATE_SRNA_NETWORK_PATH):
            self.fail('%sExpected file "%s" to exist; deeply disappointed.' \
                      % (pfx,UPDATE_SRNA_NETWORK_PATH))
            return
        # Verify that the srna_openssl.cnf file is in proper place:
        if not exists(SRNA_OPENSSL_CNF_PATH):
            self.fail('%sExpected file "%s" to exist; deeply disappointed.' \
                      % (pfx, SRNA_OPENSSL_CNF_PATH))
            return
        # Verify that the update_srna_local.pyc tool file is in proper place:
        if not exists(UPDATE_SRNA_LOCAL_PATH):
            self.fail('%sExpected file "%s" to exist; deeply disappointed.' \
                      % (pfx, UPDATE_SRNA_LOCAL_PATH))
            return
        # Verify that ADMINUSER user and home directory for simulated target NBM
        # ALREADY exist (presumably running on an NBM-Mgr...):
        test_ADMINUSER_exist = Popen(('id', ADMINUSER), stdout=PIPE,stderr=PIPE)
        result = test_ADMINUSER_exist.communicate()
        if test_ADMINUSER_exist.returncode != 0:
            self.fail('%sExpected user "%s" to exist; deeply disappointed: %s' \
                      % (pfx, ADMINUSER, result[1]))
            return
        if not os.path.exists(ADMIN_HOME):
            self.fail('%sExpected dir "%s" to exist; deeply disappointed.' \
                      % (pfx, ADMIN_HOME))
            return
        # Create a test IP address list file:
        addr_list_file = open(ADDR_LIST_PATH, 'w')
        addr_list_file.write('127.0.0.1\n127.0.0.1\n')
        addr_list_file.close()
        print 'prop.SRNA_UPDATE_TGZ: %s' % prop.SRNA_UPDATE_TGZ
        return
    def tearDown(self):
        pfx = '%s.%s: ' % (self.name, f_name())
        try:
            # Delete TGZ file, add_list, 
            # Rmv user "mpxadmin"
            #
            pass
        finally:
            DefaultTestFixture.tearDown(self)
            return
    def test_01_gen_shared_CA(self):
        pfx = '%s.%s: ' % (self.name, f_name())
        print 'Starting %s...' % f_name()
        try:
            # Run update_srna_network.pyc to generate CA, TGZ file, etc:
            proc_gen_CA = Popen(('python-mpx', UPDATE_SRNA_NETWORK_PATH,
                                '-p%s' % PASSWORD,
                                '-f%s' % ADDR_LIST_PATH),
                                stderr=PIPE)
            output = proc_gen_CA.communicate()
            if proc_gen_CA.returncode != 0:
                self.fail('%s: Failed: %s' % (pfx, output[1]))
                return
            # Check created items:
            if not exists(SRNA_UPDATE_TGZ_TGT_PATH):
                self.fail('%s: Failed to create %s' \
                          % (f_name(), SRNA_UPDATE_TGZ_TGT_PATH))
                return
            print '%s: OK' % f_name()
            # Preserve TGZ file for other tests:
            print 'SRNA_UPDATE_TGZ_TGT_PATH: %s' % SRNA_UPDATE_TGZ_TGT_PATH
            shutil.copy2(SRNA_UPDATE_TGZ_TGT_PATH, PRESERVE_DIR)
        except Exception, e:
            print str(e)
        finally:
            print 'End %s' % f_name()
            return
    def test_02_gen_local_certs_keys(self):
        pfx = '%s.%s: ' % (self.name, f_name())
        print 'Starting %s...' % f_name()
        # If temporary admin user home does not exist, create it:
        if not exists(prop.ADMIN_HOME):
            os.makedirs(prop.ADMIN_HOME, 0777)
        # Put TGZ file in proper place:
        shutil.copy2(join(PRESERVE_DIR, SRNA_UPDATE_TGZ), 
                     prop.SRNA_UPDATE_TGZ)
        try:
            from tools.srna.update_srna_local import update_srna
            update_srna()
            # Check created items:
            msg = '%s: Failed to create %s'
            for tgt in LOCAL_TGT_FILES:
                if not os.path.exists(tgt):
                    self.fail(msg % (f_name(), tgt))
                    return
            # Save created items for use in mpx.lib._test_case_rna and
            # mpx.service.network._test_case_rna:
            shutil.copytree(prop.SRNA_DATA, join(PRESERVE_DIR, 'srna'))
            print '%s: OK' % pfx
        except Exception, e:
            print str(e)
        finally:
            print 'End %s' % f_name()
            return
#
# Support stand-alone execution:
#
if __name__ == '__main__':
    TestCase.VERBOSE = 1
    main()


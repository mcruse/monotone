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
#=----------------------------------------------------------------------------
# modem.py
#
# Modem tester.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import os
import sys
import select
import time

from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from test_methods import TestMethods
from cmdexec import execute_command
from msg import *

class ModemTester(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'Modem', config, hw_info, logger)

        self._detect_done = 0
        self._modem_present = 0

        ####
        # This is a countdown variable, we only want to execute the modem
        # tests a certain number of times.
        self._test_iterations = config.modem_test_iterations()

        model = self._hw_info.model()
        if model in ('1200', '2400'):
            self._modemdev = '/dev/ttyS1'
        elif model in ('1500', '2500'):
            self._modemdev = '/dev/ttySe'
        else: # <-- Prevent execution on anything else (TSWS, S1, ...).
            self._detect_done = 1
            self._modem_present = 0
            self._modemdev = None

        return

    def _wait_for_ok(self, modem_in_fd):
        have_msg = 0

        # Wait for three seconds...
        while 1:
            result = select.select([modem_in_fd], [], [], 3)
            if not result[0]:
                break

            response = os.read(modem_in_fd, 100)
            if 'OK' in response.split():
                have_msg = 1
                break

        return have_msg

    def _write_out(self, modem_out_fd, command):
        os.write(modem_out_fd, '%s\r' % command)
        return

    def _detect_modem(self):
        # This only needs to happen once.
        if self._detect_done:
            return self._modem_present

        modem_out_fd = os.open(self._modemdev, os.O_WRONLY | os.O_NONBLOCK)
        modem_in_fd = os.open(self._modemdev, os.O_RDONLY | os.O_NONBLOCK)

        msg_testing('Looking for a modem at %s...' % self._modemdev)

        self._write_out(modem_out_fd, 'ATZ')
        result = self._wait_for_ok(modem_in_fd)
        if not result:
            message('no modem detected, skipping tests.')
            self._modem_present = 0
        else:
            message('detected.')
            self._modem_present = 1

        os.close(modem_out_fd)
        os.close(modem_in_fd)

        self._detect_done = 1
        return self._modem_present

    ###
    # Wrapper so our screen messages look ok.  What an uglee kludge...
    def _runtest(self):
        message('Executing modem tests:')

        if not os.access('/tmp/test.fil', os.F_OK):
            os.system('dd if=/dev/zero of=/tmp/test.file bs=64k count=1 1>/dev/null 2>/dev/null')

        msg_testing('  Starting PPP...')
        os.system('/etc/ppp/ppp-on')

        ####
        # We don't get any feedback from pppd or chat regarding success or
        # failure of bringing up a PPP interface (ppp0 in our case).  So, wait
        # for 45 seconds and see if ppp0 exists.
        time.sleep(45)
        result, spewage = execute_command('ifconfig ppp0')
        if not result:
            msg_fail()
            self._nerrors += 1
            self._logger.log('ERROR: ppp did not start: %s\n' % spewage)
            return 0
        message('done.')

        msg_testing('  Sending file...',)
        result, spewage = execute_command('scp /tmp/test.file root@192.168.2.254:/tmp/.')
        # MAGIC NUMBER ALERT!!!....................................^^^^^^^^^^^^^
        if not result:
            msg_fail()
            self._nerrors += 1
            self._logger.log('ERROR: scp to host failed: %s\n' % spewage)
            return 0
        message('done.')

        msg_testing('  Retrieving file...')
        result, spewage = execute_command('scp root@192.168.2.254:/tmp/test.file .')
        # MAGIC NUMBER ALERT!!!.....................^^^^^^^^^^^^^
        os.unlink('./test.file')
        if not result:
            msg_fail()
            self._nerrors += 1
            self._logger.log('ERROR: scp from host failed: %s\n' % spewage)
            return 0
        message('done.')

        msg_testing('  Deleting file on remote system...')
        result, spewage = execute_command('ssh root@192.168.2.254 rm -f /tmp/test.file')
        # MAGIC NUMBER ALERT!!!.....................^^^^^^^^^^^^^
        if not result:
            msg_fail()
            self._nerrors += 1
            self._logger.log('ERROR: ssh on host failed: %s\n' % spewage)
            return 0
        message('done.')

        msg_testing('  Stopping PPP...')
        os.system('/etc/ppp/ppp-off 1>/dev/null 2>/dev/null')
        message('done.')

        return 1

    def print_results(self):
        if self._modem_present:
            self._logger.msg("  %s: %d errors, %d warnings.\n" %
                (self._testname, self._nerrors, self._nwarnings))
        else:
            self._logger.msg("  No modem detected, tests SKIPPED.\n")

    def runtest(self, burnin = 0):
        if not burnin:
            return

        if self._test_iterations == 0:
            return

        result = self._detect_modem()
        if not result:
            return

        result = self._runtest()
        self._test_iterations -= 1

        msg_testing('Modem tests............................................................')
        if result:
            msg_pass()
        else:
            msg_fail()


#=- EOF ----------------------------------------------------------------------

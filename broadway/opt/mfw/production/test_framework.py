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
#=----------------------------------------------------------------------------
# test_framework.py
#
# Provide a framework base class for burnin and production tests.  Much of
# the testing framework is implemented here, but other testers can easily
# be put together.  See "BurninTester" for an example.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import os
import re
import socket
import sys

from avr_lib import *
from cmdexec import execute_command
from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from msg import *
from versioner import hwtest_version

from bootlog import BootlogTester
from counters_relays import CountersAndRelaysTester
from dallas import DallasTester
from ethernet import NetworkTester
from i2c import I2CTester
from memory import MemoryTester
from modem import ModemTester
from serial import SerialTester
from usb import USBTester
from mpx import properties


all_tests = ['dallas', 'bootlog', 'relayscounters', 'i2c', 
             'ethernet', 'ram','serial', 'usb', 'ramstress']

class TesterFramework(object):
    def __init__(self, burnin, enable_eth_tests, enable_modem_test=0, **kw):
        self._burnin = burnin
        self._preflight_done = 0

        # DO NOT CHANGE THE ORDER OF THESE THREE ITEMS!  Thank you!
        self._config = TestConfig(burnin, '/etc/hw_test.conf')
        self._hw_info = HardwareInfo()
        self._logger = TestLogger(burnin, self._hw_info.serialno())

        self._bootlog_tester = None
        self._car_tester = None
        self._dallas_tester = None
        self._eth_tester = None
        self._i2c_tester = None
        self._mem_tester = None
        self._stressmemtester = None
        self._modem_tester = None
        self._serial_tester = None
        self._usb_tester = None
        self._enabled_tests = 0

        model = self._hw_info.model()
        if kw.get('bootlog', True):
            self._bootlog_tester = BootlogTester(
                self._config, self._hw_info, self._logger
                )
            self._enabled_tests += 1
        if kw.get('ram', True):
            self._mem_tester = MemoryTester(
                self._config, self._hw_info, self._logger
                )
            self._enabled_tests += 1
        # do not perform stress test unless called for explicitly.
        if kw.get('ramstress', False):
            self._stressmemtester = MemoryTester(
                self._config, self._hw_info, self._logger, True
                )
            self._enabled_tests += 1
        if enable_eth_tests and kw.get('ethernet', True):
            self._eth_tester = NetworkTester(
                self._config, self._hw_info, self._logger
            )
            self._enabled_tests += 1
        if not model in ('TSWS', 'PC', 'Unknown', ''):
            self._avr_copro = avr()
            if kw.get('serial', True):
                self._serial_tester = SerialTester(
                    self._config, self._hw_info, self._logger
                )
                self._enabled_tests += 1
        if model in ('1200', '2400', '1500', '2500'):
            if kw.get('relayscounters', True):
                self._car_tester = CountersAndRelaysTester(
                    self._config, self._hw_info, self._logger, self._avr_copro
                    )
                self._enabled_tests += 1
            if kw.get('dallas', True):
                self._dallas_tester = DallasTester(
                    self._config, self._hw_info, self._logger, self._avr_copro
                    )
                self._enabled_tests += 1
        if model in ('1500', '2500') and kw.get('i2c', True):
            self._i2c_tester = I2CTester(
                self._config, self._hw_info, self._logger
                )
            self._enabled_tests += 1
        if self._hw_info.model() in ('2400', '2500') and kw.get('usb', True):
            self._usb_tester = USBTester(self._config, self._hw_info, self._logger)
            self._enabled_tests += 1
        return

    ###
    # Do a single pass test over all tests except the boot log.
    #
    # XXX: iteration is unused for now, just a placeholder.
    def _core_test(self, iteration):
        if not self._preflight_done:
            raise Exception("Pre-test checkout has not been done, aborting.\n")

        if self._car_tester:
            self._car_tester.runtest(self._burnin)

        if self._dallas_tester:
            self._dallas_tester.runtest(self._burnin)

        if self._eth_tester:
            self._eth_tester.runtest(1) # burnin set to 1 to avoid netperf tests

        if self._i2c_tester:
            self._i2c_tester.runtest(self._burnin)

        if self._mem_tester:
            self._mem_tester.runtest(self._burnin)
            
        if self._stressmemtester:
            self._stressmemtester.runtest(self._burnin)

        if self._modem_tester:
            self._modem_tester.runtest(self._burnin)

        if self._serial_tester:
            self._serial_tester.runtest(self._burnin)

        if self._usb_tester:
            self._usb_tester.runtest(self._burnin)

        return


    ###
    # Make sure that we have a valid serial number, and:
    #   - If in burn-in mode we don't have one, do not test.
    #   - If in production mode, get this info using a barcode scanner
    #     and program the serial number and mac address(es).
    def preflight_check(self):
        if self._preflight_done:
            return 1

        serialRE = re.compile("\d{2}-\d{5}", re.IGNORECASE)

        result = serialRE.search(self._hw_info.serialno())
        if result:
            self._preflight_done = 1
            return 1

        message('This unit needs a serial number and MAC address(es).')
        if self._burnin:
            message('Burn-in tests cannot be done on brand-new units.')
            return 0

        msg_testing('One moment while a connection is made to the HW test server...')
        m_address = self._config.def_macaddr()
        self._hw_info.set_mac_addr(0, m_address)
        os.system('ifconfig eth0 down')
        #os.system('rmmod natsemi; sleep 1; insmod -q natsemi')
        if_mac_addr = '%s:%s:%s:%s:%s:%s' % \
            (m_address[0:2], m_address[2:4], m_address[4:6], m_address[6:8], 
             m_address[8:10], m_address[10:])

        os.system('ifconfig eth0 hw ether %s' % if_mac_addr)
        os.system('ifconfig eth0 %s up' % self._config.def_ipaddr())

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self._config.hwtest_server(), self._config.hwtest_port()))
        except:
            msg_fail()
            return 0

        message('done.\nYou may now scan the barcode on this unit.')

        # Send a hello message and then go into a wait.
        s.send('GreetZ_1138')
        data = s.recv(64)
        s.close()

        serial, mac0, mac1 = data.split(":")

        # Any of the following set_xxx calls will raise an exception on failure.
        msg_testing('Programming the serial number and MAC address(es) for this unit...')
        self._hw_info.set_serialno(serial)
        self._hw_info.set_mac_addr(0, mac0)
        if not mac1 == "":
            self._hw_info.set_mac_addr(1, mac1)
        message('done.')

        msg_testing('Restarting networking...')
        self._hw_info.restart_networking()
        self._hw_info.reload_values()
        message('done.')

        self._preflight_done = 1
        return 1

    def print_prerun_summary(self):
        if self._enabled_tests <= 1:
            return
        self._logger.msg('Mediator hardware test program revision %s.\n', hwtest_version())
        self._logger.msg('Copyright (C) 2009 Cisco Systems, Inc.  All rights reserved.\n\n')
        self._logger.msg('Test executed on %s\n' % os.popen('date').readline())
        self._logger.msg('Model number: %s\n' % self._hw_info.model())
        self._logger.msg('Framework version: %s\n' % properties.COMPOUND_VERSION)
        self._logger.msg('MOE version: %s\n' % properties.MOE_VERSION)
        self._logger.msg('Serial number: %s\n' % self._hw_info.serialno())
        self._logger.msg('eth0 MAC address: %s\n' % self._hw_info.mac_addr(0))
        if self._hw_info.model() in ('TSWS', '2400', '2500'):
           self._logger.msg('eth1 MAC address: %s\n' % self._hw_info.mac_addr(1))

        ###
        # Having a list of loaded modules will be extremely helpful in the
        # event a test should fail (because the module might not have loaded).
        self._logger.msg('Loaded kernel modules:\n')
        result, spewage = execute_command('/sbin/lsmod')
        if not result:
           raise Exception('Cannot get module info, aborting test.')

        for line in spewage:
            self._logger.msg(line)

        self._logger.msg('\n')
        return

    def tests_in_error(self):
        errs = 0
        if self._bootlog_tester:
            errs += self._bootlog_tester.nissues()

        if self._car_tester:
            errs += self._car_tester.nissues()

        if self._dallas_tester:
            errs += self._dallas_tester.nissues()

        if self._eth_tester:
            errs += self._eth_tester.nissues()

        if self._i2c_tester:
            errs += self._i2c_tester.nissues()

        if self._mem_tester:
            errs += self._mem_tester.nissues()

        if self._modem_tester:
            errs += self._modem_tester.nissues()
            
        if self._serial_tester:
            errs += self._serial_tester.nissues()

        if self._usb_tester:
            errs += self._usb_tester.nissues()
        return errs
    
    def report_results(self):
        if self._enabled_tests > 1:
            self._logger.msg('Test summary for unit %s:\n' % self._hw_info.serialno())

        # NOTE NOTE NOTE NOTE NOTE NOTE =---------------------------------
        #
        # Please report results in the order that the tests are done.
        # Like muscle memory, folks can develop visual memory as well.
        #
        # NOTE NOTE NOTE NOTE NOTE NOTE =---------------------------------

        if self._bootlog_tester:
            self._bootlog_tester.print_results()

        if self._car_tester:
            self._car_tester.print_results()

        if self._dallas_tester:
            self._dallas_tester.print_results()

        if self._eth_tester:
            self._eth_tester.print_results()

        if self._i2c_tester:
            self._i2c_tester.print_results()

        if self._mem_tester:
            self._mem_tester.print_results()

        if self._modem_tester:
            self._modem_tester.print_results()

        if self._serial_tester:
            self._serial_tester.print_results()

        if self._usb_tester:
            self._usb_tester.print_results()
            
        if self._enabled_tests > 1:
            self._logger.msg("=----- END OF REPORT ------------------------------=\n\n")

    ###
    # Examine the boot log and run all core tests once.
    def runtests(self):
        if not self._preflight_done:
            raise Exception("Pre-test checkout has not been done, aborting.\n")

        if self._bootlog_tester:
            self._bootlog_tester.runtest(self._burnin)

        self._core_test(1)
        return

#=- EOF ----------------------------------------------------------------------

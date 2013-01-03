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
# ethernet.py
#
# Network interface tester.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import sys

from config import TestConfig
from cmdexec import execute_command
from logger import TestLogger
from test_methods import TestMethods
from msg import *

class _EthernetPort(TestMethods):
    def __init__(self, config, hw_info, logger, eth_port,
                  netperf_server, netperf_server_port,
                  ping_host, ping_count):
        TestMethods.__init__(self, 'Ethernet', config, hw_info, logger)

        self._eth_port = eth_port
        self._netperf_server = netperf_server
        self._netperf_server_port = netperf_server_port
        self._ping_host = ping_host
        self._ping_count = ping_count

    def print_results(self):
        self._logger.msg("  Network interface eth%d: %d errors.\n" %
            (self._eth_port, self._nerrors))

    def _run_netperf(self, cable_len = 0):
        msg_testing('\nConnect a %dM cable to eth%d and press enter...' % (cable_len, self._eth_port))
        sys.stdin.readline()

        msg_testing('Testing eth%d with a %dM cable (about five minutes)....................' % (self._eth_port, cable_len))

        result, spewage = execute_command('/usr/bin/mediator_test %s %s' %
                                           (self._netperf_server, self._netperf_server_port))
        if result:
            msg_pass()
        else:
            self._nerrors += 1

            self._logger.log('ERROR: %dM cable on eth%d test failed:' % (cable_len, self._eth_port))
            for line in spewage:
                self._logger.log(line)

            msg_fail()

    def _run_ping(self):
        msg_testing('  Ping testing eth%d....................................................' % self._eth_port)

        result, spewage = execute_command('ping -I eth%d -c %d %s' %
                                           (self._eth_port, self._ping_count, self._ping_host))
        if result:
            msg_pass()
        else:
            self._nerrors += 1

            ###
            # NOTE: We can't log 'spewage' here because there are extra
            # percent symbols embedded in PING's response which throws off
            # the logger's string handling.
            self._logger.log('ERROR: Ping test on eth%d failed\n' % self._eth_port)

            msg_fail()

    def runtest(self, burnin = 0):
        if burnin:
            self._run_ping()
        else:
            self._run_netperf(3)
            self._run_netperf(100)

class NetworkTester(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'NetworkTester', config, hw_info, logger)

        # So we only show the netperf performance notice once during testing.
        self._netperf_notice = 0

        self._eth0 = None
        self._eth1 = None

        self._eth0 = _EthernetPort(config, hw_info, logger, 0,
                                    self._config.netperf_eth0(),
                                    self._config.netperf_eth0_port(),
                                    self._config.ping_host_eth0(),
                                    self._config.ping_count_eth0())

        if self._hw_info.model() in ('TSWS', '2400', '2500'):
            self._eth1 = _EthernetPort(config, hw_info, logger, 1,
                                        self._config.netperf_eth1(),
                                        self._config.netperf_eth1_port() ,
                                        self._config.ping_host_eth1(),
                                        self._config.ping_count_eth1())

    def print_results(self):
        if self._eth0:
            self._eth0.print_results()

        if self._eth1:
            self._eth1.print_results()

    def runtest(self, burnin = 0):
        # We're not using netperf for the burnin testing.
        if burnin:
            self._netperf_notice = 1

        if not self._netperf_notice:
            print '\nBeginning network test.  We will be using netperf for these tests.  Netperf\'s'
            print 'results are dependent on network as well as how loaded the system that'
            print 'netserver is running on.  Benchmark results may vary on subsequent runs.'

            self._netperf_notice = 1
        else:
            message('Testing ethernet ports:')

        if self._eth0:
            self._eth0.runtest(burnin)
            self._nerrors += self._eth0.nerrors()

        if self._eth1:
            self._eth1.runtest(burnin)
            self._nerrors += self._eth1.nerrors()

        message('Network tests complete.')

#=- EOF ----------------------------------------------------------------------

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
# serial.py
#
# Serial port tester.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import os
import select
import sys
from termios import *

from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from test_methods import TestMethods
from msg import *

class _RS232Tester(TestMethods):
    def __init__(self, config, hw_info, logger, ttydev1, ttydev2):
        TestMethods.__init__(self, 'RS232', config, hw_info, logger)

        self._ttydev1 = ttydev1
        self._ttydev2 = ttydev2
        return

    def _test_ports(self, sender, receiver):
        sender.write('Greetings from your fellow RS232 port\n')

        # Wait for 5 seconds...
        result = select.select([receiver], [], [], 5.0)
        if not result[0]:
            return 1

        response = receiver.readline().strip()
        if response == 'Greetings from your fellow RS232 port':
            return 0

        # TIMEOUT...
        return 1

    def _openport(self, ttydev):
        s_port = open(ttydev, 'r+')
        try:
            p_attr = tcgetattr(s_port.fileno())
        except:
            raise Exception('I/O error on port %s' % ttydev)

        p_attr[0] = IGNPAR
        p_attr[1] = 0
        p_attr[2] = CS8 | CREAD | HUPCL | CLOCAL
        p_attr[3] = 0
        p_attr[4] = B9600  # XXX: This is a little slow...
        p_attr[5] = B9600  # XXX: This is a little slow...
        tcsetattr(s_port.fileno(), TCSANOW, p_attr)

        return s_port

    def print_results(self):
        self._logger.msg("  Serial ports %s and %s: %d errors\n" %
            (self._ttydev1, self._ttydev2, self._nerrors))
        return

    def runtest(self, burnin = 0):
        msg_testing('Testing serial ports %s and %s.........................' % (self._ttydev1, self._ttydev2))

        port1 = self._openport(self._ttydev1)
        port2 = self._openport(self._ttydev2)

        n_errs = 0
        n_errs += self._test_ports(port1, port2)
        n_errs += self._test_ports(port2, port1)
        self._nerrors += n_errs

        port1.close()
        port2.close()

        if n_errs:
            self._logger.log('ERROR: Serial port tests failed (%d errors)\n' % self._nerrors)
            msg_fail()
        else:
            msg_pass()

        return

class _RS485Tester(TestMethods):
    def __init__(self, config, hw_info, logger, ttydev1, ttydev2):
        TestMethods.__init__(self, 'RS485', config, hw_info, logger)

        self._ttydev1 = ttydev1
        self._ttydev2 = ttydev2

    def _test_ports(self, sender, receiver):
        sender.write('Greetings from your fellow RS485 port\n')

        # Wait for 2 seconds...
        result = select.select([receiver], [], [], 2.0)
        if not result[0]:
            return 1

        response = receiver.readline().strip()
        if response == 'Greetings from your fellow RS485 port':
            return 0

        # TIMEOUT...
        return 1

    def _openport(self, ttydev):
        s_port = open(ttydev, 'r+')
        try:
            p_attr = tcgetattr(s_port.fileno())
        except:
            raise Exception('I/O error on port %s' % ttydev)

        p_attr[0] = IGNPAR
        p_attr[1] = 0
        p_attr[2] = CS8 | CREAD | HUPCL | CLOCAL
        p_attr[3] = 0
        p_attr[4] = B9600  # XXX: This is a little slow...
        p_attr[5] = B9600  # XXX: This is a little slow...
        tcsetattr(s_port.fileno(), TCSANOW, p_attr)

        return s_port

    def print_results(self):
        self._logger.msg("  Serial ports %s and %s: %d errors\n" %
            (self._ttydev1, self._ttydev2, self._nerrors))

    def runtest(self, burnin = 0):
        msg_testing('Testing serial ports %s and %s.........................' % (self._ttydev1, self._ttydev2))

        port1 = self._openport(self._ttydev1)
        port2 = self._openport(self._ttydev2)

        n_errs = 0
        n_errs += self._test_ports(port1, port2)
        n_errs += self._test_ports(port2, port1)
        self._nerrors += n_errs

        port1.close()
        port2.close()

        if n_errs:
            self._logger.log('ERROR: Serial port tests failed (%d errors)\n' % self._nerrors)
            msg_fail()
        else:
            msg_pass()


class SerialTester(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'Serial ports', config, hw_info, logger)

        self._rs232test = None
        self._rs485test_a = None
        self._rs485test_b = None

        model = self._hw_info.model()

        if model in ('1500', '2500'):
            self._rs232test = _RS232Tester(config, hw_info, logger,
                                            '/dev/ttyS8', '/dev/ttyS9')

        if model in ('1200', '2400'):
            ###
            # Don't get confused by this.  On ZF's we have either the RS232
            # ports *OR* the extra RS485 ports, but not both.  It seems that
            # we mostly use the RS485 (have a peek in /etc/rc.mpx), so we
            # test those...   *STM*
            os.system('/bin/rs485init >/dev/null')
            self._rs485test_a = _RS485Tester(config, hw_info, logger,
                                              '/dev/ttyS4', '/dev/ttyS5')
        else:
            self._rs485test_a = _RS485Tester(config, hw_info, logger,
                                              '/dev/ttySa', '/dev/ttySb')

        if model in ('2400', '2500'):
            if model in ('2400',):
                self._rs485test_b = _RS485Tester(config, hw_info, logger,
                                                  '/dev/ttyS6', '/dev/ttyS7')
            else:
                self._rs485test_b = _RS485Tester(config, hw_info, logger,
                                                  '/dev/ttySc', '/dev/ttySd')
        return

    def print_results(self):
        if self._rs232test:
            self._rs232test.print_results()

        if self._rs485test_a:
            self._rs485test_a.print_results()

        if self._rs485test_b:
            self._rs485test_b.print_results()

    def runtest(self, burnin = 0):
        if self._rs232test:
            self._rs232test.runtest()
            self._nerrors += self._rs232test.nerrors()

        if self._rs485test_a:
            self._rs485test_a.runtest()
            self._nerrors += self._rs485test_a.nerrors()

        if self._rs485test_b:
            self._rs485test_b.runtest()
            self._nerrors += self._rs485test_b.nerrors()

#=- EOF ----------------------------------------------------------------------

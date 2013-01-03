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
# dallas.py
#
# Dallas bus temperature sensors tester.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import sys

from avr_lib import *
from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from test_methods import TestMethods
from msg import *

class DallasTester(TestMethods):
    def __init__(self, config, hw_info, logger, avr):
        TestMethods.__init__(self, 'Dallas temp sensors', config, hw_info, logger)

        self._num_dallas_busses = 2
        if hw_info.model() in ('2400', '2500'):
            self._num_dallas_busses = 4

        self._avr = avr
        return

    def runtest(self, burnin = 0):
        msg_testing('Testing Dallas temperature sensors.....................................')

        failed = 0
        for bus in range(1, (self._num_dallas_busses + 1)):
            a = self._avr.dallas_readrom(bus)
            address = self._avr.tohex(a)
            if address == 'ffffffffffffffff':
                self._logger.log('ERROR: Bus %d, bad address.\n' % bus)
                failed = 1
                self._nerrors += 1

        if failed:
            self._logger.log('Temp sensors, found %d errors and %d warnings.\n' %
                (self._nerrors, self._nwarnings))
            msg_fail()
        else:
            msg_pass()

        return

#=- EOF ----------------------------------------------------------------------

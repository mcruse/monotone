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
# usb.py
#
# USB tester.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import sys
import os

from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from test_methods import TestMethods
from msg import *

class USBTester(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'USB', config, hw_info, logger)

    def runtest(self, burnin = 0):
        msg_testing('  Looking for the thumb drive...')

        #
        # The automounter will take care of mounting the thumb drive for us,
        # all wee need to do is look for the 'test.breadcrumb' and verify
        # it's contents.
        #
        sda_ok = os.path.exists('/mnt/sda1/test.breadcrumb')
        sdb_ok = os.path.exists('/mnt/sdb1/test.breadcrumb')
        if sda_ok and sdb_ok:
            msg_pass()
        else:
            if sdb_ok or sdb_ok:
                self._nerrors += 1
            else:
                self._nerrors += 2
            msg_fail()

#=- EOF ----------------------------------------------------------------------

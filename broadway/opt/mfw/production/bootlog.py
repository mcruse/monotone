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
# bootlog.py
#
# System boot log examiner, looks for errors and warnings generated during
# the Mediator boot-up.
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

import re
import os
import sys

from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger
from test_methods import TestMethods
from msg import *

class BootlogWarning:
    WARNING = re.compile("^.*(warning\s*.*?)", re.IGNORECASE)

class BootlogError:
    ERROR = re.compile("^.*(error\s*.*?)", re.IGNORECASE)

###
# We always see these non-fatal errors from the IDE driver:
#    hda: task_no_data_intr: status=0x51 { DriveReady SeekComplete Error }
#    hda: task_no_data_intr: error=0x04 { DriveStatusError }
# This RE allows us to ignore them.
class BootlogIsHDA:
    ISHDA = re.compile("^hda.*", re.IGNORECASE)

class BootlogTester(TestMethods):
    def __init__(self, config, hw_info, logger):
        TestMethods.__init__(self, 'Boot log', config, hw_info, logger)
        return

    def _parse_line(self, line, lineno = None):
        result = BootlogError.ERROR.search(line)
        if result:
            result = BootlogIsHDA.ISHDA.match(line)
            if not result:
                self._logger.log('ERROR in boot log: %s' % line)
                self._nerrors += 1

        result = BootlogWarning.WARNING.search(line)
        if result:
            if line.find('maximal mount count reached') >= 0:
                return
            self._logger.log('WARNING in boot log: %s' % line)
            self._nwarnings += 1
        return

    def runtest(self, burnin = 0):
        filename = self._config.bootlog()
        if not os.path.exists(filename):
            raise Exception('Error, missing the dmesg log file [%s]' % filename)

        msg_testing('Examining system boot log for errors and warnings......................')

        try:
            f = open(filename, "r+")
            for line in f.xreadlines():
                self._parse_line(line)
        finally:
            f.close()

            if (self._nerrors == 0 and self._nwarnings == 0):
                msg_pass()
            else:
                self._logger.log('Boot log, found %d errors and %d warnings.\n' % (self._nerrors, self._nwarnings))
                msg_fail()

        return

#=- EOF ----------------------------------------------------------------------

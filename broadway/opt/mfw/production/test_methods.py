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
# test_methods.py
#
# Provide a base class for all tester classes.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

from config import TestConfig
from hwinfo import HardwareInfo
from logger import TestLogger

class TestMethods(object):
    def __init__(self, testname, config, hw_info, logger):
        self._testname = testname
        self._nerrors = 0
        self._nwarnings = 0
        self._config = config
        self._hw_info = hw_info
        self._logger = logger

    def __repr__(self):
        return self._testname

    def nerrors(self):
        return self._nerrors

    def nwarnings(self):
        return self._nwarnings
    
    def nissues(self):
        return self.nerrors() + self.nwarnings()
    
    def print_results(self):
        self._logger.msg("  %s: %d errors, %d warnings.\n" %
            (self._testname, self._nerrors, self._nwarnings))

    def runtest(self, burnin = 0):
        raise Exception('%s\' runtest method not implemented.\n' % self._testname)

#=- EOF ----------------------------------------------------------------------

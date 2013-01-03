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
# burnin_test.py
#
# Provide a framework for burnin tests.
#
#
# Written by S.T. Mansfield (scott.mansfield@encorp.com)
# $Revision: 20101 $
#=----------------------------------------------------------------------------

from test_framework import TesterFramework

class BurninTester(TesterFramework):
    def __init__(self, enable_eth_tests = 1, enable_modem_test = 0, **kw):
        burnin = 1
        TesterFramework.__init__(
            self, burnin, enable_eth_tests, enable_modem_test, **kw
            )

    def runtests(self):
        iterations = 1

        if not self._preflight_done:
            raise Exception("Pre-test checkout has not been done, aborting.\n")

        ####
        # During burn-in testing we only need to look at the boot
        # log once, thankyouverymuch...
        if self._bootlog_tester:
            self._bootlog_tester.runtest(self._burnin)

        for iter in range(self._config._burnin_iterations):
            try:
                print 'Executing burn-in test iteration %d of %d' % (iterations, self._config._burnin_iterations)
                self._core_test(iterations)
                iterations += 1

            except KeyboardInterrupt:
                self._logger.msg("\n\nBurnin tests halted at %d iterations.\n" % iterations)
                return
        return

#=- EOF ----------------------------------------------------------------------

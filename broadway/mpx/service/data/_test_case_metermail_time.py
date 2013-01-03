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
##
#

##
# @fixme Python 2.2 hack.  Force a timezone we know about.  In Python 2.4
#        tzset should allow for testing of different TZ configurations in the
#        same process.
#
import os
os.environ['TZ'] = 'PST8PDT'

##
# @note Until rewritten to use tzset (see above), time must be imported after
#       the timezone is set.
import time

from mpx_test import DefaultTestFixture, main

from metermail_time import DSTRange
from metermail_time import dst_range
from metermail_time import DST_BIAS
from metermail_time import W3CDateTime

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        return
    def tearDown(self):
        DefaultTestFixture.tearDown(self)
        return
    def test_DST_BIAS(self):
        self.assert_comparison('DST_BIAS.bias_text()', '==', "'480'")
        self.assert_comparison('DST_BIAS.dst_bias_text()', '==', "'-60'")
        return
    def test_dst_range(self):
        y1 = 2005
        y2 = 2006
        r1 = dst_range(y1)
        r2 = dst_range(y2)
        # Make sure the correct DST start and end ISO 8601 strings are reported
        # the 2005:
        self.assert_comparison('r1.dst_start_text()', '==',
                               "'2005-04-03T10:00:00Z'")
        self.assert_comparison('r1.dst_end_text()', '==',
                               "'2005-10-30T09:00:00Z'")
        # Make sure the correct DST start and end ISO 8601 strings are reported
        # the 2006:
        self.assert_comparison('r2.dst_start_text()', '==',
                               "'2006-04-02T10:00:00Z'")
        self.assert_comparison('r2.dst_end_text()', '==',
                               "'2006-10-29T09:00:00Z'")
        # Make sure the ID and value comparisons are valid:
        self.assert_comparison('r1', 'is not', 'DSTRange(y1)')
        self.assert_comparison('r1', '==', 'DSTRange(y1)')
        self.assert_comparison('r1', '!=', 'r2')
        # Ensure that DSTRanges were cached:
        self.assert_comparison('dst_range(y1)', 'is', 'r1')
        self.assert_comparison('dst_range(y2)', 'is', 'r2')
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
# Test cases to exercise exception memory use.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib import msglog

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.msglog_object = msglog.log_object()
        return
    def test_1(self):
        try:
            1/0
        except:
            msglog.exception()
        for entry in self.msglog_object:
            if entry['message'].startswith('ZeroDivisionError:'):
                # OK, we logged a divide by zero error!
                return
        self.fail(
            "Did not find a logged ZeroDivisionError"
            )
        raise "Unreachable!"
    def test_2(self):
        try:
            raise 'string exception'
        except:
            msglog.exception()
        for entry in self.msglog_object:
            if entry['message'].startswith('string exception'):
                # OK, we logged a divide by zero error!
                return
        self.fail(
            "Did not find a logged 'string exception'"
            )
        raise "Unreachable!"

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

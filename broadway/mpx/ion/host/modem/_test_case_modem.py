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
# Test cases to exercise the Modem-related objects.
##

from mpx_test import DefaultTestFixture, main

from mpx.ion.host.modem import Modem, InternalModem

class TestCase(DefaultTestFixture):
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
        return
    def tearDown(self):
        DefaultTestFixture.tearDown(self)
        return

    # test_a: Does some basic checking on getChatScript to make sure that
    #         it is stripping out unwanted characters in the dialing string,
    #         but leaving in those that we do want.
    def test_a(self):
        p = Modem(None)

        p.configure({})

        nums = [['(509) 778-1537', '5097781537'],
                ['(509)+778-1537', '5097781537']]

        for x,y in nums:
            p.getChatScript('Howdy', x)

            if p.edited_phone != y:
                raise "Didn't get expected phone number from %s.  Got %s." % (x, p.edited_phone)

    def test_b(self):
        p = InternalModem()
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

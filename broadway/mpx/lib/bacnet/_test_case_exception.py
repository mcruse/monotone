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
from npdu import NPDU
from _exceptions import BACnetError

##
# Test cases to exercise the data encoders and decoders.
#

from mpx_test import DefaultTestFixture, main

class TestCase(DefaultTestFixture):
    def test_write_property_multiple_error(self):
        npdu_msg = ('\x01\x00P\xee\x10\x0e\x91\x02\x91*\x0f'
                    '\x1e\x0c \xc0\x00\t\x19{)\x01\x1f')
        npdu = NPDU()
        npdu.fromstring(npdu_msg)
        exc_msg = str(BACnetError(npdu))
        self.assert_comparison(
            "exc_msg.find('(writePropertyMultiple)')", ">", "-1"
            )
        return
    def test_no_npdu(self):
        exc_msg = str(BACnetError(None))
        return

if __name__ == '__main__':
    main()

"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
# Test cases to exercise the npdu.NPDU() psuedo class.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib.bacnet.npdu import NPDU
from mpx.lib.exceptions import EOverflow

_strange_complex_ack='\x01\x040\x01\x00\x01\x0e'

# This is a (possibly) valid response that used to crash NDPU().fromstring().
# @note This is an example BACnet-ComplexACK-PDU sent from a Trane BCU.
#       I'm not convinced that it is compliant with ASHRAE 135-1995
#       20.1.5.4 and 20.1.5.5.  Specifically segmented-message == 0
#       but sequence-number and proposed-window-size are specified.
#       I've modified our codec to assume that sequence-number and
#       proposed-window-size are present if segmented-message or
#       N-DATAUNIT.data-expecting-reply.  I don't know if this will
#       work with all BACnet devices...
_large_fromstring=\
'\x01\x040\x01\x00\x01\x0e\x0c&\xc0\x00C\x1e*,KN\t\x01\x1e\x1c\x00\x00\x00' + \
'\x00)\x00\x1f.D?\x80\x00\x00/O\x1f\x0c&\xc0\x00C\x1e*,sNDC\x90\x00\x00O' + \
'\x1f\x0c&\xc0\x00C\x1e*(?N\t\x02\x1e\x0c\x02\x00\x00\x02\x1c\x00@\x00\x19)U' + \
'\x1f.DBp\x00\x00/O\x1f\x0c&\xc0\x00C\x1e*(=N\t\x02\x1e\x0c\x02\x00\x00\x02' + \
'\x1c\x00@\x00\x17)U\x1f.DB\x8c\x00\x00/O\x1f\x0c&\xc0\x00C\x1e*+\xdcNDB' + \
'\x8c\xcc\xcdO\x1f\x0c&\xc0\x00C\x1e*,qNDC\x9c\x00\x00O\x1f\x0c&\xc0\x00C' + \
'\x1e*,oNDD\xe7\x00\x00O\x1f\x0c&\xc0\x00C\x1e*+\xccN\x10O\x1f\x0c&\xc0\x00C' + \
'\x1e*(HN\t\x01\x1e\x0c\x02\x00\x00\x02\x1c\x01\x00\x00\x15)U\x1f.\x10/O\x1f' + \
'\x0c&\xc0\x00C\x1e)UN\x91\x02O\x1f\x0c&\xc0\x00C\x1e*(pN\x10O\x1f\x0c&' + \
'\xc0\x00C\x1e*)\x02N\x11O\x1f\x0c&\xc0\x00C\x1e*(>N\t\x02\x1e\x0c\x02\x00' + \
'\x00\x02\x1c\x00@\x00\x16)U\x1f.DB\x94\x00\x00/O\x1f\x0c&\xc0\x00C\x1e' + \
'*(GN\t\x01\x1e\x1c\x00\x00\x00\x00)\x00\x1f.\x10/O\x1f\x0c&\xc0\x00C\x1e*+' + \
'\xebND\x00\x00\x00\x00O\x1f\x0c&\xc0\x00C\x1e*\'\x15N\x11O\x1f\x0c&\xc0' + \
'\x00C\x1e*(\x89N\x91\x05O\x1f\x0c&\xc0\x00C\x1e*(}N\x10O\x1f\x0c&\xc0' + \
'\x00C\x1e*+\xdbNDB\xaa\x00\x00O\x1f\x0c&\xc0\x00C\x1e*(<N\x0c\x02\x00' + \
'\x00\x02\x1c&@\x00\x03O\x1f\x0c&\xc0\x00C\x1e)MNu\x11\x00VAV 2-04 FinanceO' + \
'\x1f\x0c&\xc0\x00C\x1e*\'\x10N!\x01O\x1f\x0c&\xc0\x00C\x1e*\'\x11N!`O\x1f' + \
'\x0c&\xc0\x00C\x1e*('

# This is just a big message, it is not valid beyond the initial header.
_really_large_fromstring= _large_fromstring + ('*' * 1574)

class TestCase(DefaultTestFixture):
    def test_empty(self):
        NPDU()
    def test_tostring(self):
        s = '\x01\x20\xff\xff\x00\x45\x10\x08\x09\x01\x19\x01'
        n = NPDU()
        n.version = 1
        n.dspec = 1
        n.dnet = 0xffff
        n.dlen = 0
        n.hop_count = ord('\105')
        n.pdu_type = 1
        n.choice = 8
        n.data = '\x09\x01\x19\x01'
        if s != n.tostring():
            raise 'Incorrect byte string generated for WHO_HAS device 1.'
    def test_fromstring(self):
        s = '\x01\x20\xff\xff\x00\x45\x10\x08\x09\x01\x19\x01'
        n = NPDU().fromstring(s)
        if s != n.tostring():
            raise 'Mismatch between fromstring() and tostring().'
    ##
    # This string used to crash.
    def test_large_fromstring(self):
        n = NPDU().fromstring(_large_fromstring)
        s = n.tostring()
        if s != _large_fromstring:
            raise 'Mismatch between fromstring() and tostring()' + \
                  ' in a large string.'
    ##
    # Just fits...
    def test_really_large_fromstring(self):
        n = NPDU().fromstring(_really_large_fromstring)
        s = n.tostring()
        if s != _really_large_fromstring:
            raise 'Mismatch between fromstring() and tostring()' + \
                  ' in a really large string.'
    ##
    # One, waffer thin byte too many.
    def test_too_large_fromstring(self):
        try:
            n = NPDU().fromstring(_really_large_fromstring + '*')
        except EOverflow:
            pass
        else:
            raise 'fromstring() failed to detect too much data.'

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

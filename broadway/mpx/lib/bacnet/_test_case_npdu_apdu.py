"""
Copyright (C) 2001 2003 2010 2011 Cisco Systems

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
# Test cases to exercise the npdu.APDU() class.
#

from mpx_test import DefaultTestFixture, main

from mpx.lib.bacnet.npdu import NPDU
from mpx.lib.bacnet.apdu import *

class TestCase(DefaultTestFixture):
    derived_attrs = {'choice':(1,0),
                     'dadr':('\xff\xff','\xcc'),
                     # 'data':('abcd','1234'),
                     'data_expecting_reply':(1,0), 'dlen':(2,1),
                     'dnet':(0xffff,1), 'dspec':(1,0), 'fromstring':(),
                     'hop_count':(2,255), 'invalid_apdu':(1,0),
                     'invoke_id':(2,127), 'max_apdu_length_accepted':(1,0),
                     'more_follows':(1,0), 'msg_type':(1,0),
                     'negative_ack':(1,0), 'network_msg':(1,0),
                     'pdu_type':(7,0),
                     'priority':(3,1),
                     'reason':(1,0), 'sadr':('\x00\x00','\xdd'),
                     'segmented_message':(1,0),
                     'segmented_response_accepted':(1,0),
                     'sequence_number':(1,0), 'server':(1,0), 'slen':(2,1),
                     'snet':(2,3), 'sspec':(1,0), 'tostring':(),
                     'vendor_id':(1,2), 'version':(1,100), 'window_size':(1,0)}
    def _compare_mapped_get_and_set_on(self, a, n):
        for attr, values in self.derived_attrs.items():
            if getattr(n,attr) != getattr(a,attr):
                self.fail("Failed initial psuedo inheritance:  "
                          "APDU.%s != NPDU.%s." % (attr, attr))
            for value in values:
                prev = getattr(a,attr)
                setattr(a, attr, value)
                if getattr(n,attr) != getattr(a,attr):
                    raise "Failed modified psuedo inheritance:  " + \
                          " APDU.%s != NPDU.%s." % (attr, attr)
                setattr(a, attr, prev)
                setattr(n, attr, value)
                if getattr(n,attr) != getattr(a,attr):
                    raise "Failed modified 'reverse' psuedo inheritance:  " + \
                          " APDU.%s != NPDU.%s." % (attr, attr)        
    def test_instanciate(self):
        APDU()
        BACnetConfirmedServiceRequestAPDU()
        BACnetUnconfirmedServiceRequestAPDU()
        BACnetSimpleACK_APDU()
        BACnetComplexACK_APDU()
        BACnetSegmentACK_APDU()
        BACnetErrorAPDU()
        BACnetRejectAPDU()
        BACnetAbortAPDU()
    def test_instanciate_with_npdu(self):
        n = NPDU()
        APDU(n)
        BACnetConfirmedServiceRequestAPDU(n)
        BACnetUnconfirmedServiceRequestAPDU(n)
        BACnetSimpleACK_APDU(n)
        BACnetComplexACK_APDU(n)
        BACnetSegmentACK_APDU(n)
        BACnetErrorAPDU(n)
        BACnetRejectAPDU(n)
        BACnetAbortAPDU(n)
    def test_psuedo_inheritance(self):
        n = NPDU()
        a = APDU(n)
        self._compare_mapped_get_and_set_on(a,n)
    def test_broken_psuedo_inheritance(self):
        n = NPDU()
        a = APDU(n)
         # Break the pass through of the choice attribute.
        a.__dict__['choice'] = 1
        try:
            self._compare_mapped_get_and_set_on(a,n)
        except:
            return
        raise 'Test failed to detect broken inheritance.'

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

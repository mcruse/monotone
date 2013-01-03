"""
Copyright (C) 2002 2006 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx

from array import array
from mpx.lib.debug import string_fromdump
from mpx.lib.bacnet import npdu
from mpx.lib.bacnet import apdu

# Semi-valid CONFIRMED_REQUEST_PDU.
def example_confirmed_request_npdu():
    req = apdu.APDU()
    req.version = 1
    req.network_msg = 0
    req.priority = 0
    req.data_expecting_reply = 1
    req.sspec = 1
    req.dspec = 0
    req.snet = 2222
    req.slen = 6
    req.sadr = '123456'
    req.hop_count = 255
    req.vendor_id = 95
    req.segmented_response_accepted = 1
    req.more_follows = 0
    req.segmented_message = 0
    req.pdu_type = 0x00
    req.invoke_id = 101
    req.choice = 12
    req.data = array('c',"\x0c\x02\x01\x73\x18\x19\x61")
    return req.as_npdu()

def example_confirmed_response_pdu(req):
    rsp = apdu.APDU()
    rsp.version = req.version
    rsp.network_msg = req.network_msg
    rsp.priority = req.priority
    rsp.data_expecting_reply = req.data_expecting_reply
    rsp.dspec = req.sspec
    if req.sspec:
        rsp.dspec = 1
        rsp.dnet = req.snet
        rsp.dlen = req.slen
        rsp.dadr = req.sadr
        rsp.hop_count = 0xff
    else:
        rsp.dspec = 0
        rsp.hop_count = 0x00
    rsp.sspec = 0
    if rsp.pdu_type == 0x00: # BACnet-Confirmed-Service-Request-PDU
        rsp.pdu_type = 0x03  # BACnet-ComplexACK-PDU (segmented-message=0)
    rsp.more_follows = 0
    rsp.segmented_message = 0
    rsp.invoke_id = req.invoke_id
    rsp.choice = req.choice
    return rsp.as_npdu()

req = example_confirmed_request_npdu()
rsp = example_confirmed_response_pdu(req)

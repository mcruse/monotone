"""
Copyright (C) 2002 2010 2011 Cisco Systems

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

import time
import types
import threading
from struct import *

from mpx.lib import msglog
from mpx.lib.bacnet import npdu, network
from mpx.lib.bacnet.apdu import BACNET_CONFIRMED_SERVICE_REQUEST_PDU, \
                                BACNET_ERROR_PDU, BACNET_REJECT_PDU, \
                                BACNET_ABORT_PDU, APDU

def recv_response(request_id):
    r = network.recv_response(request_id, 10.0)
    if r.pdu_type == BACNET_ERROR_PDU:
        failure = 'error'
    elif r.pdu_type == BACNET_REJECT_PDU:
        failure = 'reject'
    elif r.pdu_type == BACNET_ABORT_PDU:
        failure = 'abort'
    else:
        failure = None
    if failure:
        raise 'BACnet error', (r, failure)
    if not r: raise 'BACnet error', (r, 'timeout')
    return r

def read_property(device, prop):
    global threadlock1
    results = []
    threadlock1.acquire()
    try:
        object = prop[0]
        instance = prop[1]
        property = prop[2]
        arrayidx = None
        if len(prop) > 3 :
            arrayidx = prop[3]
        rp = npdu.NPDU()
        rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
        rp.choice = 12
        if arrayidx :
            raise 'Not supported'
        else :
            rp.data = rp.data + pack('>BIBB', 0x0c, object << 22 | instance,
                                     0x19, property)
        request_id = network.send_request(device, rp)
        r = network.recv_response(request_id)
        return r
    finally:
        threadlock1.release()

threadlock1=threading.RLock()

def write_property(device, object, instance, property, arrayidx, priority,
                   value, btype):
    rp = npdu.NPDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 15
    # @fixme  redo this whole routine to take advantage of incoming btype
    # @fixme  this is a huge hack for object 130.
    # @fixme  Better would be to set the type (real, int, enum) according to
    #         property
    if property > 127 :
        rp.data = pack('>BIBH', 0x0c, object << 22 | instance, 0x1A, property)
    else:
        # This was what was here
        rp.data = pack('>BIBB', 0x0c, object << 22 | instance, 0x19, property)
    if btype == 4:
        value = float(value)
    else :
        value = int(value)
    if property == 85:
        if btype == 0:
            rp.data = rp.data + pack('>BBBBB', 0x3e, 0x00, 0x3f, 0x49, priority)
        elif btype == 4:
            rp.data = rp.data + pack('>BBfBBB', 0x3e, 0x44, value, 0x3f, 0x49,
                                     priority)
        elif btype == 9:
            if value < 256:
                rp.data = rp.data + pack('>BBBBBB', 0x3e, 0x91, value, 0x3f,
                                         0x49, priority)
            else:
                rp.data = rp.data + pack('>BBIBBB', 0x3e, 0x94, value, 0x3f,
                                         0x49, priority)
    elif object == 130:
        rp.data = rp.data + pack('>BBBBBIBBBBBfBB', 0x3e, 0x09, 0x01, 0x1e
                                 ,0x1c, 0, 0x29, 0x00,0x1f,
                                 0x2e, 0x44, value, 0x2f, 0x3f)
    else:
        if btype == 4:
            rp.data = rp.data + pack('>BBfBBB', 0x3e, 0x44, value, 0x3f, 0x49,
                                     priority)
        else:
            rp.data = rp.data + pack('>BBIBBB', 0x3e, 0x94, value, 0x3f, 0x49,
                                     priority)
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)
    return r

"""
Copyright (C) 2002 2003 2004 2005 2007 2008 2010 2011 Cisco Systems

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
# Provides the basic networking capabilities for BACnet.
#
# @todo ClientTSM timeout's and retries.
# @todo DeviceTSM.
# @todo Ensure it's thread safe.
# @todo Use semaphores on the queue, instead of polling it.
# @todo Move public I/Fs up to mpx.lib.bacnet and rename _network

import copy, struct
from time import time as now
from mpx.lib import utils
from mpx.lib import pause, msglog
from mpx.lib.threading import Lock, Condition, ImmortalThread
from mpx.lib.exceptions import EInvalidValue, EAlreadyOpen, ETimeout
from mpx.lib.exceptions import ENotImplemented, EIOError, EDeviceNotFound
from mpx.lib.bacnet import tag, data, npdu
import mpx.lib.scheduler
from mpx.lib.scheduler import scheduler

from npdu import Addr
from npdu import recv as _recv
from npdu import send as _send
from npdu import I_AM_ROUTER
from npdu import NPDU
from npdu import add_route

import network as _network

import traceback

from mpx.lib.bacnet.constants import * 

import apdu
import sequence
import array

from apdu import BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU, \
                 BACNET_CONFIRMED_SERVICE_REQUEST_PDU, BACNET_SIMPLE_ACK_PDU, \
                 BACNET_COMPLEX_ACK_PDU, BACNET_ERROR_PDU, BACNET_REJECT_PDU, \
                 BACNET_ABORT_PDU, BACNET_SEGMENT_ACK_PDU, \
                 I_AM_CHOICE, WHO_IS_CHOICE, \
                 ABORT_REASON_INVALID_APDU_IN_THIS_STATE, \
                 APDU, is_APDU, UNCONFIRMED_COV_NOTIFICATION_CHOICE
import tag

DECODE_MAX_APDU_LENGTH = (50,128,206,480,1024,1476)

##
# The lock used for module wide data.
# @todo See if we want more granular locking.  I doubt it.
_module_lock = Lock()
_tsm_q = {}

debug = 0
npdu.debug = 0

##
# This class implements the Transaction State Machine for the Responding
# BACnet User (server).  [ASHRAE 135-1995 sub-clause 5.4.5]
##
class _ServerTSM:
    IDLE = 'idle'				# ASHRAE 135-1995 5.4.5.1
    SEGMENTED_REQUEST = 'segmented request'	# ASHRAE 135-1995 5.4.5.2
    AWAIT_RESPONSE = 'await response'	        # ASHRAE 135-1995 5.4.5.3
    SEGMENTED_RESPONSE = 'segmented response'	# ASHRAE 135-1995 5.4.5.4
    COMPLETE = 'complete'			# IDLE with a result.
    def __init__(self, device, interface, network, source, apdu):
        global _module_lock
        global _tsm_q
        self._cv = Lock()
        self.timestamp = now()
        #self.network = network
        self.device = device
        self.address = device.address
        self.request = apdu
        self.network = network
        self.source = source
        self.exception = None
        self.state = self.IDLE
        # maximum npdu length is from three sources, the interface, the device
        # and the request.  NPDU header is 21 bytes max
        # max_apdu_len is the number of bytes, max_apdu_length_accepted is an encoded value
        mtu = min(interface.mtu - _network._MAX_APDU_OVERHEAD, device.max_apdu_len)
        #read max apdu size from request and make sure we pick the leastest
        # length is encoded according to bacnet 20.1.2.5 
        # this issue also shows up in lib.c bacnet_send_message
        if apdu.max_apdu_length_accepted < len(DECODE_MAX_APDU_LENGTH):
            mtu = min(mtu, DECODE_MAX_APDU_LENGTH[apdu.max_apdu_length_accepted])
        self.send_segment_size = mtu
        # use either interface or device timeout/retry values
        self.T_seg = interface.T_seg
        if device.T_seg is not None:
            self.T_seg = device.T_seg
        self.T_wait_for_seg = interface.T_wait_for_seg
        if device.T_wait_for_seg is not None:
            self.T_wait_for_seg = device.T_wait_for_seg
        self.T_out = interface.T_out
        if device.T_out is not None:
            self.T_out = device.T_out
        self.N_retry = interface.N_retry
        if device.N_retry is not None:
            self.N_retry = device.N_retry

        self.retry_count = 0 
        self.segment_retry_count = 0
        self.sent_all_segments = 0
        self.last_sequence_number = 0 
        self.initial_sequence_number = 0
        self.actual_window_size = None
        self.proposed_window_size =  None
        self.segment_timer = None
        self.response = None
        self.invoke_id = apdu.invoke_id

        return
    
    def process_state(self, msg):
        try:
            self._cv.acquire()
            if self.state == self.IDLE:
                self._idle_state(msg)
            elif self.state == self.SEGMENTED_REQUEST:
                self._segmented_request_state(msg)
            elif self.state == self.SEGMENTED_RESPONSE:
                self._segmented_response_state(msg)
            elif self.state == self.COMPLETE:
                self._completed_state(msg)
            else:
                raise EIOError('Illegal TSM state')
        finally:
            self._cv.release()
            
    def _idle_state(self, msg):
        if not msg:
            self._stop_segment_timer()
            return  #no timers while idle
        # @fixme Validate APDU...
        if msg.pdu_type == BACNET_CONFIRMED_SERVICE_REQUEST_PDU:
            if msg.segmented_message == 1:
                if msg.sequence_number == 0:
                    self.request = APDU(msg)
                    self.actual_window_size = msg.window_size
                    self._send_segment_ack(msg)
                    self.segment_retry_count = 0
                    self._start_segment_timer()
                    self.last_sequence_number = 0
                    self.initial_sequence_number = 0
                    self.state = self.SEGMENTED_REQUEST
                    return
                else: #bad sequence number
                    self._UnexpectedPDU_Received(msg)
                    return
            else: #unsegmented, get response now
                self._send_response(confirmed_service_indication(self.network, self.device, msg))
                return
        elif msg.pdu_type == BACNET_ABORT_PDU:
            self._complete()
            return
        elif msg.pdu_type == BACNET_SEGMENT_ACK_PDU and msg.server == 0:
            self._UnexpectedPDU_Received(msg)
        else:
            print 'unexpected packet ignored in bacnet server idle state'
            pass #silence
    def _segmented_request_state(self, msg):
        if msg:
            if msg.pdu_type == BACNET_CONFIRMED_SERVICE_REQUEST_PDU:
                if msg.segmented_message == 1:
                    if msg.sequence_number == int((self.last_sequence_number + 1) & 0xff):
                        if msg.more_follows == 1: #still more coming in
                            self.request.data.fromstring(msg.data) #append data to buffer
                            self.last_sequence_number = int((self.last_sequence_number + 1) & 0xff)
                            if msg.sequence_number == int((self.initial_sequence_number + self.actual_window_size) & 0xff):
                                self.initial_sequence_number = self.last_sequence_number
                                self._send_segment_ack(msg)
                            self.segment_retry_count = 0
                            self._start_segment_timer()
                            return
                        else: #final segment has been received
                            self.request.data.fromstring(msg.data) #append data to buffer
                            self.last_sequence_number = int((self.last_sequence_number + 1) & 0xff)
                            self._stop_segment_timer()
                            self._send_segment_ack(msg)
                            self.initial_sequence_number = self.last_sequence_number
                            self._send_response(confirmed_service_indication(self.network, self.device, self.request))
                            return
                    else: #segment received out of order
                        self._send_segment_nack(msg.invoke_id, self.last_sequence_number)
                        self.segment_retry_count = 0
                        self._start_segment_timer()
                        self.initial_sequence_number = self.last_sequence_number
                        return
            elif msg.pdu_type == BACNET_ABORT_PDU:
                self._complete()
                return
            _UnexpectedPDU_Received(msg)  
        else: #since clock tick
            t = self.segment_timer
            if t:
                if t.executing() or t.expired():
                    if self.segment_retry_count < 3:
                        #lock?
                        self.segment_retry_count += 1
                        self._start_segment_timer()
                    else:
                        self._complete(None)
    def _segmented_response_state(self, msg):
        if debug:
            print 'Server TSM _segmented_response_state'
        if msg:
            if msg.pdu_type == BACNET_SEGMENT_ACK_PDU:
                if not self._InWindow(msg): #duplicate ack
                    if debug: print 'ServerTSM: segmented_response_state: duplicate ack'
                    self._start_segment_timer()
                    return #do nothing self._DuplicateACK_Received(msg)
                else:
                    if self.sent_all_segments: #final ack received
                        if debug: print '_ServerTSM: final ack received'
                        self._stop_segment_timer()
                        self._complete(msg)
                        return
                    else:
                        self._start_segment_timer()
                        self.segment_retry_count = 0
                        return self._NewACK_Received(msg)
            elif msg.pdu_type == BACNET_ABORT_PDU:
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_SIMPLE_ACK_PDU) and \
                 (self.sent_all_segments == 1)):
                self._complete(msg)
            elif msg.pdu_type == BACNET_CONFIRMED_SERVICE_REQUEST_PDU: #duplicate
                if msg.segmented_message == 1:
                    self._send_segment_nack(self.request.invoke_id, self.last_sequence_number)
            else:  #anything else is unexpected
                self._UnexpectedPDU_Received(msg)
        else: #since tick
            t = self.segment_timer
            if t:
                if t.executing() or t.expired():
                    if self.segment_retry_count <= self.N_retry:
                        #lock?
                        self.segment_retry_count += 1
                        self._start_segment_timer()
                        self._FillWindow()
                    else:
                        self._complete(None)
        pass
    def _NewACK_Received(self, msg):
        if debug: print '_ServerTSM._NewACK_Received'
        self.initial_sequence_number = (msg.sequence_number + 1) % 0x100
        self.actual_window_size = msg.window_size
        self._FillWindow()
    ##
    # @return True if the BACnet-SegmentACK's sequence-number is in the
    #         current transmission window.  Otherwise, false.
    def _InWindow(self, msg):
        window_index = (msg.sequence_number - self.initial_sequence_number) \
                       % 0x100
        return window_index < self.actual_window_size
    def _FillWindow(self):
        if debug: print 'ServerTSM: enter _FillWindow', self.initial_sequence_number, self.actual_window_size
        for ix in range(self.initial_sequence_number,
                        self.initial_sequence_number+self.actual_window_size):
            last_seg = len(self.response.data) <= (self.send_segment_size*(ix+1))
            # Send the next segment.
            segment = APDU()
            segment.version = 1
            segment.data_expecting_reply = 1
            segment.pdu_type = BACNET_COMPLEX_ACK_PDU
            segment.segmented_message = 1
            segment.more_follows = not last_seg
            segment.invoke_id = self.request.invoke_id
            segment.sequence_number = (ix % 256)
            segment.window_size = self.proposed_window_size
            segment.choice = self.request.choice
            segment.data = self.response.data[self.send_segment_size*ix:
                                             self.send_segment_size*(ix+1)]
            if debug: print 'ServerTSM: _FillWindow: ', len(segment.data), last_seg, ix
            segment = segment.as_npdu()
            self._send(segment)
            if last_seg:
                self.sent_all_segments = 1
                return
    def _send_response(self, apdu):
        self.response = apdu
        if debug: print 'ServerTSM:_send_response: ', str(len(apdu.data))
        if is_APDU(apdu):
            if len(apdu.data) <= self.send_segment_size:
                self.send_UnsegmentedComplexOrSimpleAck(apdu.as_npdu())
            else:
                self.send_SegmentedComplexAck(apdu)
        else:
            if len(apdu.data) <= self.send_segment_size:
                self.send_UnsegmentedComplexOrSimpleAck(apdu)
            else:
                self.send_SegmentedComplexAck(apdu)
        return
    def _send(self, response):
        if not _is_master_server(self.device, self.network):
            response.sspec = 1
            response.slen = 6 #what should we chose?
            response.sadr = utils.bytes_as_string_of_hex_values(self.device.instance_number, response.slen)
            response.snet = self.device.network #correct local copy?
        if (hasattr(self.request, 'sspec')) and (self.request.sspec == 1): #message came through router, send it back
            response.dspec = 1
            response.dlen = self.request.slen
            response.dadr = self.request.sadr
            response.dnet = self.request.snet
        _send(self.network, self.source, response)
                    
    def _send_segment_ack(self, msg):
        if debug: print '_ServerTSM._send_segment_ack'
        # Acknowledge the final segment
        ack = NPDU()
        ack.version = 1
        ack.data_expecting_reply = 0
        ack.pdu_type = BACNET_SEGMENT_ACK_PDU
        ack.negative_ack = 0
        ack.server = 1
        ack.window_size = self.actual_window_size
        ack.invoke_id = msg.invoke_id
        ack.sequence_number = msg.sequence_number
        self._send(ack)
    def _send_segment_nack(self, invoke_id, sequence_number):
        if debug: print '_ServerTSM._send_segment_nack'
        # Acknowledge the final segment
        ack = NPDU()
        ack.version = 1
        ack.data_expecting_reply = 0
        ack.pdu_type = BACNET_SEGMENT_ACK_PDU
        ack.negative_ack = 1
        ack.server = 1
        ack.window_size = self.actual_window_size
        ack.invoke_id = invoke_id
        ack.sequence_number = sequence_number
        self._send(ack)
    ##
    # BACnet event handler for send_UnsegmentedComplexAck.
    def send_UnsegmentedComplexOrSimpleAck(self, msg):
        if debug: print '_ServerTSM.send_ConfirmedUnsegmented'
        #if self.state != self.IDLE:
            ## @fixme exceptions...
            #raise EIOError('Transaction State Machine in use')
        msg.data_expecting_reply = 0
        msg.server = 1
        self._send(msg)
        self._complete(msg)
    ##
    # BACnet event handler for send_SegmentedComplexAck.
    def send_SegmentedComplexAck(self, msg):
        if debug: print '_ServerTSM.send_SegmentedComplexAck', len(msg.data)
        #if self.state != self.IDLE:
            ## @fixme exceptions...
            #raise EIOError('Transaction State Machine in use')
        self.segment_retry_count = 0
        self.initial_sequence_number = 0
        self.proposed_window_size = 10
        self.actual_window_size = 1
        self._start_segment_timer()
        self.sent_all_segments = 0
        # Send the first segment.
        segment = APDU()
        segment.version = 1
        segment.data_expecting_reply = 1
        segment.server = 1
        segment.pdu_type = BACNET_COMPLEX_ACK_PDU
        segment.segmented_message = 1
        segment.more_follows = 1
        segment.segmented_response_accepted = 1
        segment.invoke_id = msg.invoke_id
        segment.sequence_number = 0
        segment.window_size = self.proposed_window_size
        segment.choice = msg.choice
        segment.data = msg.data[0:self.send_segment_size]
        segment = segment.as_npdu()
        self.state = self.SEGMENTED_RESPONSE
        self._send(segment)
    def _completed_state(self, msg):
        pass
#todo have all TSM exit through this state to clean up timers
    def _complete(self, msg):
        if debug: print 'SM _complete'
        self._stop_segment_timer()
        self.response = msg
        if not msg:
            self.exception = ETimeout
        self.state = self.COMPLETE
    def complete(self):
        return self.state == self.COMPLETE
    def _UnexpectedPDU_Received(self, msg):
        if debug: print '_ServerTSM._UnexpectedPDU_Received'
        # Send an ABORT.
        self._stop_segment_timer()
        abort = npdu.NPDU()
        abort.version = 1
        abort.data_expecting_reply = 0
        abort.pdu_type = BACNET_ABORT_PDU
        abort.server = 1
        abort.invoke_id = msg.invoke_id
        abort.reason = ABORT_REASON_INVALID_APDU_IN_THIS_STATE
        self._send(abort)
        # Give up.
        self.exception = EIOError('Unexpected PDU.') # @fixme
        self._complete(None)
        return
    def _start_segment_timer(self, timeout=None):
        self._stop_segment_timer()
        if timeout is None:
            timeout = self.T_seg
        self.segment_timer = scheduler.seconds_from_now_do(timeout, self._segment_timeout)
    def _stop_segment_timer(self):
        if self.segment_timer:
            self.segment_timer.cancel()
            self.segment_timer = None
    def _segment_timeout(self):
        if debug: print '_ServerTSM: timeout'
        self.process_state(None)

_device_str = """\
_network._DeviceInfo:
  id:                %s
  object_type:       %s
  max_apdu_len:      %s
  can_recv_segments: %s
  can_send_segments: %s
  vendor_id:         %s
  network:           %s
  address:           %s
  readPropertyFallback: %s
  mac_network:       %s
  mac_address:       %s"""

_rpm_fallback = ["Unknown", "ReadPropertyMultiple",
                 "ReadPropertyMutliple-Singular", "ReadProperty"]
class _DeviceInfo:
    def __init__(self, carrier_mtu=1468):
        self.instance_number = 0
        self.object_type = 8
        #20.1.2.5 max-APDU-length-accepted.  here we use actual length value
        self.max_apdu_len = carrier_mtu - _network._MAX_APDU_OVERHEAD
        self.can_recv_segments = 1
        self.can_send_segments = 1
        self.vendor_id = 95
        self.network = 0
        self.address = Addr()
        self.readPropertyFallback = 0  #0=Unknown, 1=RPM, 2=RPMsingular, 3=RP
        self.mac_network = 0
        self.mac_address = Addr()
        self.node = None
        #if None, use interface's values.  These are set during server node start
        self.T_seg = None 
        self.T_wait_for_seg = None
        self.T_out = None
        self.N_retry = None
    def segmentation_supported(self):
        answer = 0
        if not self.can_recv_segments:
            answer = 1
        if not self.can_send_segments:
            answer |= 2
        return answer
    def object_identifier(self):
        if debug: print 'return boid'
        return data.BACnetObjectIdentifier(self.object_type, self.instance_number)
    def __str__(self):
        global _device_str
        result = _device_str % (self.instance_number, self.object_type,
                                self.max_apdu_len,
                                self.can_recv_segments, self.can_send_segments,
                                self.vendor_id, self.network, self.address,
                                _rpm_fallback[self.readPropertyFallback],
                                self.mac_network, self.mac_address)
        return result

the_devices = {} #go plural
# called by BIN.ServerDevice during start to create a DeviceTable entry
# and to verify that only one device may directly use an Interface.  
# Virtual Devices are not associated with an Interface, they exist behind
# a logical router
def create_server_device(node, network, carrier_mtu=1476):
    #print 'create server device: ', node.as_node_url(), network, carrier_mtu
    the_device = _DeviceInfo(carrier_mtu)
    the_device.instance_number = node.instance
    the_device.node = node
    the_device.network = network
    the_device.mac_network = network
    interface = node.get_interface()
    if interface is None:
        # virtual device.  Modify Addr with an address equal to the intance number
        the_device.address.address = utils.bytes_as_string_of_hex_values(the_device.instance_number, 6)
    else:
        # real device.  Use Interface's Addr 
        the_device.address = interface.addr #the_device.address
        #only one real device is allowed for an interface
        if interface.master_device is not None:
            raise EInvalidValue("BACnet server device misconfigured", str(network), '''Only one device with the Interface's network number is allowed.
Existing device: %s
New device: %s''' % (interface.master_device.node.as_node_url(), node.as_node_url(),))
        interface.master_device = the_device
    the_device.mac_address = the_device.address
    # the following two lines need to be generalized for multiple internetworks
    the_devices[the_device.instance_number] = the_device #add to list, key by instance number aka mac address
    _network.add_server_to_device_table(the_device) #copy client since it won't see this
    if debug: print 'the server device has been created: %s' % str(the_device)
    return the_device

def destroy_server_device(device):
    #remove device from the Device Info table and prevent responses to whois
    try:
        del the_devices[device.instance_number]
    except:
        print 'destroy bacnet server device failed'
##
# Send a response to a client request.  This is only intended for server
# responses.  All other NPDUs should be sent with send_request.
def send_response(network, address, msg):
    _send(network, address, msg)

# answer true if device is the master device for the network
def _is_master_server(device, network):
    interface = device.node.get_interface() #interface node or None
    if interface:
        # device with interface objects are master devices
        # is this device the master for THIS network
        return (device.network == network)
    return False
##
# Used by a virtual device to implement a service.
# @todo Determine where registerred network messages are recieved.  Here
#       could work, then devices could register for unsolicited messages.
#       This capability (network messages) is not required right now.
def recv_request(interface, network, source, msg):
    from mpx.lib.bacnet import _bacnet
    global _tsm_q
    if debug:
        print 'BACNET SERVER: received request'
    # look up device based on instance number being used as a MAC address
    tsm_key = None
    response = None
    try:
        the_device = None
        if (not hasattr(msg, 'dspec')) or (msg.dspec == 0):
            the_device = interface.master_device
        else:
            addr_str = msg.dadr
            diff = len(addr_str) - 4
            if diff > 0:
                addr_str = addr_str[-4:]
            elif diff < 0:
                addr_str = ('\x00' * diff) + addr_str
            instance_number = struct.unpack('!L',addr_str)[0]
            if not the_devices.has_key(instance_number): return #be silent for devices we do not know about or have not started
            the_device = the_devices[instance_number]  #could get fancier here to handle errors, like when request directed to client node
        #find tsm for server device/client device/invoke id combo
        if (not hasattr(msg, 'sspec')) or (msg.sspec == 0):
            source_key = str(source)
            if debug: print 'source key', source_key
        else:
            source_key = (str(source), str(msg.sadr), msg.snet)
        tsm_key = (the_device.instance_number, source_key, msg.invoke_id)
        if _tsm_q.has_key(tsm_key):
            tsm = _tsm_q[tsm_key]
        else:
            tsm = _ServerTSM(the_device, interface, network, source, msg) #create a new one in the idle state
            _tsm_q[tsm_key] = tsm
        tsm.process_state(msg) #parse the message based on the current state 
        if tsm.complete():
            del _tsm_q[tsm_key]
    except Exception, e:
        msglog.exception()
        rp = npdu.NPDU()
        rp.pdu_type = BACNET_REJECT_PDU
        rp.version = 1
        rp.invoke_id = msg.invoke_id
        rp.reason = 9 # Unsupported-Service
        #raise ENotImplemented
        if (hasattr(msg, 'sspec')) and (msg.sspec == 1): #message came through router, send it back
            rp.dspec = 1
            rp.dlen = msg.slen
            rp.dadr = msg.sadr
            rp.dnet = msg.snet
        response = rp
        if tsm_key is not None:
            if _tsm_q.has_key(tsm_key):
                del _tsm_q[tsm_key]
        send_response(network, source, response)
            
def confirmed_service_indication(network, the_device, msg):
    import _bacnet
    try:
        if msg.choice == BACNET_READ_PROPERTY:
            response = _bacnet.server_read_property(the_device.node, msg)
        elif msg.choice == BACNET_READ_PROPERTY_MULTIPLE:
            response = _bacnet.server_read_property_multiple(the_device.node, msg)
        elif msg.choice == BACNET_WRITE_PROPERTY:
            response = _bacnet.server_write_property(the_device.node, msg)
        elif msg.choice == BACNET_WRITE_PROPERTY_MULTIPLE:
            response = _bacnet.server_write_property_multiple(the_device.node, msg)
        elif msg.choice == BACNET_CONFIRMED_COV_NOTIFICATION:
            response = server_cov_notification_msg(the_device.node, \
                       msg, confirmed = True)
        else: #reject amything else
            raise ENotImplemented('bacnet server', msg.choice, 'service choice not supported')
        if response and (not _is_master_server(the_device, network)):
            response.sspec = 1
            response.slen = 6 #what should we chose?
            response.sadr = utils.bytes_as_string_of_hex_values(the_device.instance_number, response.slen)
            response.snet = the_device.network #correct local copy?
    except Exception, e:
        msglog.exception()
        rp = npdu.NPDU()
        rp.pdu_type = BACNET_REJECT_PDU
        rp.version = 1
        rp.invoke_id = msg.invoke_id
        rp.reason = 9 # Unsupported-Service
        response = rp
    return response

def recv_abort(network, source, msg):
    if debug:
        print 'BACNET SERVER: received abort'
    pass
##
# Used to fail quickly for non-responsive devices.  Slow responses will still
# eventually get registerred when we receive the I_AM_CHOICE_REQUEST.
_failed_device_timeout = {}

##
# @return The BACnet address of <code>device</code>.  None if the
#         <code>device</code>'s address can not be determined in under
#         2.5 seconds.
# @note This function gets less patient for non-responsive devices.
def device_address(device):
    info = _device_info(device)
    if info:
        return info.address
    return None

##
# @return Perform a Global WHO_IS to populate the _device_table.  
#         Allow 0.1 seconds for anything new to show up.
def i_am(device, network):
    global _module_lock
    if debug: print 'send i am'
    boid = device.object_identifier()
    ss = device.segmentation_supported()
    s = sequence.BACnetIAm(boid, 
          device.max_apdu_len, 
          ss, 
          device.vendor_id)
    if debug: print s.encoding
    # Broadcast a I AM device request.
    wi = NPDU()
    wi.version = 1
    wi.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
    wi.choice = I_AM_CHOICE
    wi.data = tag.encode(s.encoding) 
    wi.dspec = 1
    wi.dlen = 0
    wi.dnet = 0xffff
    
    #ADDED TO SUPPORT VIRTUAL ROUTER or Devices on other networks    
    if not _is_master_server(device, network):
        wi.sspec = 1
        wi.slen = 6 #see above
        wi.snet = device.network
        wi.sadr = utils.bytes_as_string_of_hex_values(device.instance_number, wi.slen)
    
    wi.hop_count = 255
    _send(network, Addr(), wi)
    # no longer need this since when server device is created it is added to device table
    # _network.add_server_to_device_table(device) #copy client since it won't see this
    if debug: print 'sent I am to: %s' % (str(network),)

def server_cov_notification_msg(device, msg, confirmed):
     import _bacnet
     response = _bacnet.cov_notification_msg(device, msg, confirmed)
     return response
    
def who_is_request_received(msg, network):
    if not the_devices: 
        if debug: print 'who is received but we have no device(s)'
        return

    if len(msg.data) == 0: #device limits tags len==0 means global request
        if debug: print 'who are'
        for the_device in the_devices.values():
            i_am(the_device, network)
    else:
        if debug: print 'check if we are who is'
        tags = tag.decode(msg.data).value
        if debug: 
            print tags
        
        if len(tags) == 2:
            if debug:
                print tags[0]
                print tags[1]
            lower_limit = data.decode_unsigned_integer(tags[0].data) #Device Instance Range Low Limit
            upper_limit = data.decode_unsigned_integer(tags[1].data)
            if debug: print 'is it between: %s and %s' % (lower_limit, upper_limit)

# From bacnet plugfest, we were filtering out anyone not on our network from test for
# address limits.  We were responding ok to global whoisall
#            if network == the_device.network:
            for the_device in the_devices.values():
                if the_device.instance_number >= lower_limit:
                    if the_device.instance_number <= upper_limit:
                        if debug: print 'i am the mo-fo'
                        i_am(the_device, network)
    
    

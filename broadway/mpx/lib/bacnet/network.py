"""
Copyright (C) 2001 2002 2003 2005 2006 2007 2009 2010 2011 Cisco Systems

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

#@todo Allow bacnet servers behind NAT firewalls to know their external IP address

import array
import copy
from time import time as now
from moab.linux.lib import uptime
import os

from mpx.lib import pause, msglog
from mpx.lib.threading import Lock, ImmortalThread
from mpx.lib.exceptions import *
from mpx.lib.bacnet import tag, data
import mpx.lib.scheduler
from mpx.lib.scheduler import scheduler
from threading import Condition

##
# @fixme Make the open functions loadable, instead of hard coded.
from npdu import _open_eth, _open_ip, _open_mstp, _open_virtual, Addr

from npdu import recv as _recv
from npdu import send as _send
from npdu import close as _close
from npdu import I_AM_ROUTER
from npdu import NPDU
from npdu import add_route

from _exceptions import * # get the bacnet exceptions

import traceback

import apdu
from apdu import BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU, \
                 BACNET_CONFIRMED_SERVICE_REQUEST_PDU, BACNET_SIMPLE_ACK_PDU, \
                 BACNET_COMPLEX_ACK_PDU, BACNET_ERROR_PDU, BACNET_REJECT_PDU, \
                 BACNET_ABORT_PDU, BACNET_SEGMENT_ACK_PDU, \
                 I_AM_CHOICE, WHO_IS_CHOICE, \
                 UNCONFIRMED_COV_NOTIFICATION_CHOICE, \
                 ABORT_REASON_INVALID_APDU_IN_THIS_STATE, \
                 APDU, is_APDU
import server
import tag

BACNET_RPM_UNKNOWN = 0
BACNET_RPM_OK = 1
BACNET_RPM_SINGLE_OK = 2
BACNET_RPM_NOT_SUPPORTED = 3

from mpx.lib.debug import dump_tostring
debug = 0
debugTSM = 0

ETHERNET = 'Ethernet'
IP       = 'IP'
MSTP     = 'MSTP'
VIRTUAL  = 'Virtual'

def _open_ip_wrapper(name, network, addr, keywords):
    import bvlc
    interface_id = _open_ip(name, network, addr, keywords)
    bvlc.start_bbmd_service()
    return interface_id

_interface_types = {
    ETHERNET:_open_eth,
    IP:_open_ip_wrapper,
    MSTP:_open_mstp,
    VIRTUAL:_open_virtual
    }

_max_address_table = {
    ETHERNET:6,
    IP:6,
    MSTP:1,
    VIRTUAL:6
    }

##
# Calculate the maximum number of octets that APDU and NPDU headers will consume
# of a standard APDU maximum response encoding.  BACnet APDU sizes were
# calculated by ASHRAE assuming that the address of the NPDU would never exceed
# 6 bytes and that the total NPCI would not exceed 24 octets.  If BACnet/IP
# ever supports IPv6, then this assumption will no longer be true.
def _calc_pdu_overhead():
    max_apdu_hdr = 6
    max_len = 6 # BACnet packet sizes already account for 6 octet address.
    for addr_len in _max_address_table.values():
        if addr_len > max_len:
            max_len = addr_len
    overflow = (max_len - addr_len) * 2
    return max_apdu_hdr + overflow

#_MAX_APDU_OVERHEAD = _calc_pdu_overhead()
_MAX_APDU_OVERHEAD = 21 # max NPDU header length that preceeds APDU

##
# The lock used for module wide data.
# @todo See if we want more granular locking.  I doubt it.
_module_lock = Lock()
_network_map = {}
_device_table = {}
_request_q = {}
#_cv = Condition() made individual for each tsm

##
# This class implements the Transaction State Machine for the Requesting
# BACnet User (client).  [ASHRAE 135-1995 sub-clause 5.4.4]
# @todo Have the TSM persist?
# @fixme Support timeout/retry logic.
class _ClientTSM:
    IDLE = 'idle'				# ASHRAE 135-1995 5.4.4.1
    SEGMENTED_REQUEST = 'segmented request'	# ASHRAE 135-1995 5.4.4.2
    AWAIT_CONFIRMATION = 'await confirmation'	# ASHRAE 135-1995 5.4.4.3
    SEGMENTED_CONF = 'segmented confirmation'	# ASHRAE 135-1995 5.4.4.4
    COMPLETE = 'complete'			# IDLE with a result.
    def __init__(self, device, apdu, timeout=3.0, **keywords):
        global _module_lock
        global _tsm_q
        global _request_q
        self.timestamp = now()
        self.device = device
        self.address = device.address
        self.request = apdu
        self.exception = None
        self.callback = None
        if keywords.has_key('callback'):
            self.callback = keywords['callback']
        self.state = self.IDLE
        if not _network_map.has_key(device.mac_network):
            raise EInvalidValue
        interface = _network_map[device.mac_network]
        self.T_seg = timeout * 2.0 / 3.0 #interface.T_seg
        self.T_wait_for_seg = self.T_seg * 4 #interface.T_wait_for_seg
        self.T_out = timeout #interface.T_out
        self.N_retry = interface.N_retry
        #pick the least packet size allowed between the device and the interface
        #this leaves out smaller mtu's from intervening routers
        #but most routers smaller mtu's will likely match the device's mtu
        mtu = min(interface.mtu - _MAX_APDU_OVERHEAD, device.max_apdu_len)
        self.send_segment_size = mtu

        self.retry_count = 0 
        self.segment_retry_count = 0
        self.sent_all_segments = 0
        self.last_sequence_number = 0 
        self.initial_sequence_number = 0
        self.actual_window_size = None
        self.proposed_window_size =  None
        self.segment_timer = None
        self.request_timer = None
        self.sent = False
        self._cv = Condition()
        self.request_id = _next_request_id() #if an exception occurs in here, we want to break now
        try:
            apdu.invoke_id = self.request_id
            _tsm_q[apdu.invoke_id] = self
            if debugTSM:
                print 'TSM init'
            # @fixme Validate APDU...
            if apdu.pdu_type == BACNET_CONFIRMED_SERVICE_REQUEST_PDU:
                if self.callback:
                    if not _request_q.has_key(self.device.instance_number):
                        _request_q[self.device.instance_number] = []
                    _request_q[self.device.instance_number].append(self)
                    if len(_request_q[self.device.instance_number]) > 2:  #only allow two outstanding requests
                        #print "defer sending: ", apdu.invoke_id
                        return
                self._send_pdu_and_start_timers() # if an exception occurs in here, it might be temporary.  Just timeout
        except:
            # we log the exception but allow the normal timeout process to occur
            msglog.log('bacnet',msglog.types.INFO,
               'Unable to transmit request')
            msglog.exception()
    def _send_pdu_and_start_timers(self):
        self.sent = True
        self._start_segment_timer()
        self._start_request_timer()
        self._send_confirmed_service_request_pdu(self.request)
        #print 'sent: ', self.request.invoke_id
    def _send_confirmed_service_request_pdu(self, apdu):
        if is_APDU(apdu):
            if len(apdu.data) <= self.send_segment_size:
                self.send_ConfirmedUnsegmented(apdu.as_npdu())
            else:
                self.send_ConfirmedSegmented(apdu)
        else:
            if len(apdu.data) <= self.send_segment_size:
                self.send_ConfirmedUnsegmented(apdu)
            else:
                self.send_ConfirmedSegmented(apdu)
        return
    def process_state(self, msg):
        if self.state == self.IDLE:
            self._idle_state(msg)
        elif self.state == self.SEGMENTED_REQUEST:
            self._segmented_request_state(msg)
        elif self.state == self.AWAIT_CONFIRMATION:
            self._await_confirmation_state(msg)
        elif self.state == self.SEGMENTED_CONF:
            self._segmented_conf_state(msg)
        elif self.state == self.COMPLETE:
            self._completed_state(msg)
        else:
            raise EIOError('Illegal TSM state')
    def _idle_state(self, msg):
        if not msg:
            return  #no timers while idle
        if ((msg.pdu_type == BACNET_COMPLEX_ACK_PDU) and \
           (msg.segmented_message == 1)) or \
           ((msg.pdu_type == BACNET_SEGMENT_ACK_PDU) and \
           (msg.server == 1)):
            self._send_Abort()
        #anything else, we don't know about.  Do nothing
        if debugTSM:
            print 'TSM _idle_state'
        pass
    def _segmented_request_state(self, msg):
        if debugTSM:
            print 'TSM _segmented_request_state'
        if msg:
            if msg.pdu_type == BACNET_SEGMENT_ACK_PDU:
                if not msg.server:
                    # @fixme Now what?  The specicificaton does not say...
                    return
                if not self._InWindow(msg):
                    self._start_segment_timer()
                    return self._DuplicateACK_Received(msg)
                else:
                    if self.sent_all_segments:
                        self._stop_segment_timer()
                        self._start_request_timer()
                        return self._FinalACK_Received(msg)
                    else:
                        self._start_segment_timer()
                        self.segment_retry_count = 0
                        return self._NewACK_Received(msg)
            elif msg.pdu_type == BACNET_ABORT_PDU:
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_SIMPLE_ACK_PDU) and \
                 (self.sent_all_segments == 1)):
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_COMPLEX_ACK_PDU) and \
                  (self.sent_all_segments == 1) and \
                  (msg.segmented_message == 0)):
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_COMPLEX_ACK_PDU) and \
                  (self.sent_all_segments == 1) and \
                  (msg.segmented_message == 1) and \
                  (msg.sequence_number == 0)):
                self._stop_request_timer()
                self._start_segment_timer()
                self._SegmentedComplexACK_Received(msg)
            elif ((msg.pdu_type == BACNET_ERROR_PDU) and \
                  (self.sent_all_segments == 1)):
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_REJECT_PDU) and \
                  (self.sent_all_segments == 1)):
                self._complete(msg)
            else:  #anything else is unexpected
                self._send_Abort()
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
    def _await_confirmation_state(self, msg):
        #if debugTSM:
            #print 'TSM _await_confirmation_state'
        if msg:
            if (msg.pdu_type == BACNET_SIMPLE_ACK_PDU):
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_COMPLEX_ACK_PDU) and \
                  (msg.segmented_message == 0)):
                self._complete(msg)
            elif ((msg.pdu_type == BACNET_COMPLEX_ACK_PDU) and \
                  (msg.segmented_message == 1) and \
                  (msg.sequence_number == 0)):
                self._stop_request_timer()
                self._SegmentedComplexACK_Received(msg)
            elif (msg.pdu_type == BACNET_ERROR_PDU):
                self._complete(msg)
            elif (msg.pdu_type == BACNET_REJECT_PDU):
                self._complete(msg)
            elif msg.pdu_type == BACNET_ABORT_PDU:
                self._complete(msg)
            elif msg.pdu_type == BACNET_SEGMENT_ACK_PDU:
                self._DuplicateACK_Received(msg)
            else: #anything thing else is bogus
                self._send_Abort()
        else: #since tick
            t = self.request_timer
            if t:
                if t.executing() or t.expired():
                    if debugTSM:
                        print 'request timeout'
                    if self.retry_count < self.N_retry:
                        #lock?
                        self.retry_count += 1
                        self._start_request_timer()
                        self._send_confirmed_service_request_pdu(self.request)
                        pass
                    else:
                        if debugTSM:
                            print 'retry count exceeded'
                        self._complete(None)
        pass
    def _segmented_conf_state(self, msg):
        if debugTSM:
            print 'TSM _segmented_conf_state'
        if msg:
            if ((msg.pdu_type == BACNET_COMPLEX_ACK_PDU) and \
                  (msg.segmented_message == 1)):
                next_seq = (self.last_sequence_number + 1) % 256
                if next_seq != msg.sequence_number:
                    self._start_segment_timer()
                    return self._SegmentReceivedOutOfOrder(msg)
                if not msg.more_follows:
                    return self._LastSegmentOfComplexACK_Received(msg)
                last_seq = (self.initial_sequence_number +
                            self.actual_window_size) % 256
                if next_seq == last_seq:
                    self._start_segment_timer()
                    return self._LastSegmentOfGroupReceived(msg)
                self._start_segment_timer()
                return self._NewSegmentReceived(msg)
            elif (msg.pdu_type == BACNET_REJECT_PDU):
                self._complete(msg)
            elif msg.pdu_type == BACNET_ABORT_PDU:
                self._complete(msg)
            else: #anything thing else is bogus
                self._send_Abort()
        else: #since tick
            t = self.segment_timer
            if t:
                if t.executing() or t.executed():
#            if now() >= (self.segment_timer + self.T_wait_for_seg):
                    self._complete(None)
        pass
    def _completed_state(self, msg):
        pass
#todo have all TSM exit through this state to clean up timers
    def _complete(self, msg):
        self._cv.acquire()
        try:
            if self.state == self.COMPLETE:
                return
            self.state, cb, self.callback = self.COMPLETE, self.callback, None
        finally:
            self._cv.release()
        if debugTSM:
            print 'TSM _complete'
        self._stop_segment_timer()
        self._stop_request_timer()
        self.response = msg
        if not msg:
            self.exception = ETimeout()
        if cb is not None:
            # examine the request queue and remove our entry
            queue = _request_q.get(self.device.instance_number, [])
            if self in queue:
                queue.pop(queue.index(self)) #this index will allways be less than any new elements add, therefor no conflict
                #print "remove from q ", self.request.invoke_id
            # send next unsent request
            for tsm in queue:
                if tsm.sent == False:
                    tsm._send_pdu_and_start_timers()
                    break
            cb.unwind_callbacks(self)  #this is where all the callbacks get run in reverse order
        
    def _start_segment_timer(self, extra=0):
        self._stop_segment_timer()
        self.segment_timer = scheduler.seconds_from_now_do(self.T_seg + extra, self._segment_timeout)
    def _stop_segment_timer(self):
        if self.segment_timer:
            self.segment_timer.cancel()
            self.segment_timer = None
    def _segment_timeout(self):
        try:
            self._cv.acquire()
            self._cv.notifyAll()
        finally:
            self._cv.release()
        if self.callback is not None:
            self.process_state(None)
        pass
    def _start_request_timer(self, extra=0):
        self._stop_request_timer()
        self.request_timer = scheduler.seconds_from_now_do(self.T_out + extra, self._request_timeout)
    def _stop_request_timer(self):
        if self.request_timer:
            self.request_timer.cancel()
            self.request_timer = None
    def _request_timeout(self):
        try:
            self._cv.acquire()
            self._cv.notifyAll()
        finally:
            self._cv.release()
        if self.callback is not None:
            self.process_state(None)
        pass

    def process_pdu(self, source, msg):
        self.timestamp = now()
        if   msg.pdu_type == BACNET_SIMPLE_ACK_PDU:
            return self.process_SimpleACK(msg)
        elif msg.pdu_type == BACNET_COMPLEX_ACK_PDU:
            return self.process_ComplexACK(msg)
        elif msg.pdu_type == BACNET_SEGMENT_ACK_PDU:
            return self.process_SegmentACK(msg)
        elif msg.pdu_type == BACNET_ERROR_PDU:
            return self.process_Error(msg)
        elif msg.pdu_type == BACNET_REJECT_PDU:
            return self.process_Reject(msg)
        elif msg.pdu_type == BACNET_ABORT_PDU:
            return self.process_Abort(msg)
        return
    ##
    # @return True if the BACnet-SegmentACK's sequence-number is in the
    #         current transmission window.  Otherwise, false.
    def _InWindow(self, msg):
        window_index = (msg.sequence_number - self.initial_sequence_number) \
                       % 0x100
        return window_index < self.actual_window_size
    ##
    # Send all packets in the current transmission window:
    # [self.initial_sequence_number, self.initial_sequence_number+
    #                                self.actual_window_size).
    def _FillWindow(self):
        for ix in range(self.initial_sequence_number,
                        self.initial_sequence_number+self.actual_window_size):
            last_seg = len(self.request.data) <= self.send_segment_size*(ix+1)
            # Send the next segment.
            segment = APDU()
            segment.version = 1
            segment.data_expecting_reply = 1
            segment.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
            segment.segmented_message = 1
            segment.more_follows = not last_seg
            segment.segmented_response_accepted = 1
            segment.invoke_id = self.request.invoke_id
            segment.sequence_number = (ix % 256)
            segment.window_size = self.proposed_window_size
            segment.choice = self.request.choice
            segment.data = self.request.data[self.send_segment_size*ix:
                                             self.send_segment_size*(ix+1)]
            segment = segment.as_npdu()
            _send(self.device.network, self.device.address, segment)
            if last_seg:
                self.sent_all_segments = 1
                return
        return
    ##
    # Entry point for all SimpleACK PDUs.  Basically the BACnet handler for the
    # SimpleACK_Received event.
    def process_SimpleACK(self, msg):
        if debug: print '_ClientTSM.process_SimpleACK()'
        if self.state == self.AWAIT_CONFIRMATION:
            self._complete(msg)
            return
        elif state == self.SEGMENTED_REQUEST:
            if self.sent_all_segments:
                self._complete(msg)
                return
            return self._UnexpectedPDU_Received(msg)
        raise EIOError('Unexpected SimpleACK.') # @fixme exceptions...
    ##
    # Entry point for all ComplexACK PDUs.
    def process_ComplexACK(self, msg):
        if debug: print '_ClientTSM.process_ComplexACK'
        if msg.segmented_message:
            return self._process_SegmentedComplexACK(msg)
        else:
            return self._UnsegmentedComplexACK_Received(msg)
    ##
    # Entry point for all Error PDUs.  Basically the BACnet handler for the
    # ErrorPDU_Received event.
    def process_Error(self, msg):
        if debug: print '_ClientTSM.process_Error'
        self._complete(msg)
        return
    ##
    # Entry point for all Reject PDUs.  Basically the BACnet handler for the
    # RejectPDU_Received event.
    def process_Reject(self, msg):
        if debug: print '_ClientTSM.process_Reject'
        self._complete(msg)
        return
    ##
    # Entry point for all Abort PDUs.  Basically the BACnet handler for the
    # AbortPDU_Received event.
    def process_Abort(self, msg):
        if debug: print '_ClientTSM.process_Abort'
        self._complete(msg)
        return
    ##
    # Entry point for all SegmentACK PDUs.  Basically the BACnet handler for
    # the SegmentACK_Received event.
    def process_SegmentACK(self, msg):
        if debug: print '_ClientTSM.process_SegmentACK'
        if self.state == self.AWAIT_CONFIRMATION:
            # Silently ignore.
            return
        elif self.state == self.SEGMENTED_REQUEST:
            if not msg.server:
                # @fixme Now what?  The specicificaton does not say...
                return
            if not self._InWindow(msg):
                return self._DuplicateACK_Received(msg)
            else:
                if self.sent_all_segments:
                    return self._FinalACK_Received(msg)
                else:
                    return self._NewACK_Received(msg)
        return self._UnexpectedPDU_Received(msg)
    ##
    # Handler for all segmented ComplexACK PDUs.  Since there are several
    # events to process for segmented ComplexACK PDUs, this handler
    # examins the current state and the message to determin which event to
    # "generate."
    def _process_SegmentedComplexACK(self, msg):
        if debug: print '_ClientTSM._process_SegmentedComplexACK'
        if self.state == self.AWAIT_CONFIRMATION \
           and msg.sequence_number == 0:
                return self._SegmentedComplexACK_Received(msg)
        elif self.state == self.SEGMENTED_REQUEST \
             and msg.sequence_number == 0 \
             and self.sent_all_segments:
            return self._SegmentedComplexACK_Received(msg)
        elif self.state == self.SEGMENTED_CONF:
            next_seq = (self.last_sequence_number + 1) % 256
            if next_seq != msg.sequence_number:
                return self._SegmentReceivedOutOfOrder(msg)
            if not msg.more_follows:
                return self._LastSegmentOfComplexACK_Received(msg)
            last_seq = (self.initial_sequence_number +
                        self.actual_window_size) % 256
            if next_seq == last_seq:
                return self._LastSegmentOfGroupReceived(msg)
            return self._NewSegmentReceived(msg)
        return self._UnexpectedPDU_Received(msg)
    ##
    # BACnet event handler for SendConfirmedUnsegmented.
    def send_ConfirmedUnsegmented(self, msg):
        if debug: print '_ClientTSM.send_ConfirmedUnsegmented'
        #if self.state != self.IDLE:
            ## @fixme exceptions...
            #raise EIOError('Transaction State Machine in use')
        msg.version = 1
        msg.data_expecting_reply = 1
        # The network layer handles large messages and segmented messages.
        msg.segmented_response_accepted = 1
        self.state = self.AWAIT_CONFIRMATION
        _send(self.device.network, self.device.address, msg)
    ##
    # BACnet event handler for SendConfirmedSegmented.
    def send_ConfirmedSegmented(self, msg):
        if debug: print '_ClientTSM.send_ConfirmedSegmented'
        #if self.state != self.IDLE:
            ## @fixme exceptions...
            #raise EIOError('Transaction State Machine in use')
        self.segment_retry_count = 0
        self._start_segment_timer()
        self.initial_sequence_number = 0
        self.proposed_window_size = 10
        self.actual_window_size = 1
        self.sent_all_segments = 0
        # Send the first segment.
        segment = APDU()
        segment.version = 1
        segment.data_expecting_reply = 1
        segment.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
        segment.segmented_message = 1
        segment.more_follows = 1
        segment.segmented_response_accepted = 1
        segment.invoke_id = msg.invoke_id
        segment.sequence_number = 0
        segment.window_size = self.proposed_window_size
        segment.choice = msg.choice
        segment.data = msg.data[0:self.send_segment_size]
        segment = segment.as_npdu()
        self.state = self.SEGMENTED_REQUEST
        _send(self.device.network, self.device.address, segment)
    ##
    # BACnet event handler for SendUnconfirmed.
    def send_Unconfirmed(self, msg):
        if debug: print '_ClientTSM.send_Unconfirmed'
        raise ENotImplemented
    ##
    # BACnet event handler for SendAbort.
    def send_Abort(self, msg):
        if debug: print '_ClientTSM.send_Abort'
        raise ENotImplemented
    ##
    # BACnet handler for the SegmentedComplexACK_Received event.  This is the
    # event that occurs when receiving the first segment of a segmented
    # ComplexACK_PDU.
    def _SegmentedComplexACK_Received(self, msg):
        if debug: print '_ClientTSM._SegmentedComplexACK_Received'
        self.actual_window_size = msg.window_size
        self.response_segments = [msg]
        self.last_sequence_number = 0
        self.initial_sequence_number = 0
        self._start_segment_timer(self.T_wait_for_seg)  #give this one a little extra time
        self.state = self.SEGMENTED_CONF
        # Acknowledge the initial segment
        ack = NPDU()
        ack.version = 1
        ack.data_expecting_reply = 0
        ack.pdu_type = BACNET_SEGMENT_ACK_PDU
        ack.negative_ack = 0
        ack.server = 0
        ack.window_size = self.actual_window_size
        ack.invoke_id = msg.invoke_id
        ack.sequence_number = 0
        _send(self.device.network, self.device.address, ack)
        return
    ##
    # BACnet handler for the UnsegmentedComplexACK_Received event.  This is
    # the event that occurs when receiving the ComplexACK in a single message.
    def _UnsegmentedComplexACK_Received(self, msg):
        if debug: print '_ClientTSM._UnsegmentedComplexACK_Received'
        if self.state == self.AWAIT_CONFIRMATION:
            self._complete(msg)
            return
        elif state == self.SEGMENTED_REQUEST:
            if self.sent_all_segments:
                self._complete(msg)
            return self._UnexpectedPDU_Received(msg)
        # @fixme exceptions...
        raise EIOError('Unexpected unsegmented ComplexACK.')
    ##
    # BACnet handler for the LastSegmentOfComplexACK_Received event.  This is the
    # event that occurs when we receive the final segment of a segmented
    # ComplexACK (the segment with more-follows == 0).
    def _LastSegmentOfComplexACK_Received(self, msg):
        if debug: print '_ClientTSM._LastSegmentOfComplexACK_Received'
        # Acknowledge the final segment
        ack = NPDU()
        ack.version = 1
        ack.data_expecting_reply = 0
        ack.pdu_type = BACNET_SEGMENT_ACK_PDU
        ack.negative_ack = 0
        ack.server = 0
        ack.window_size = self.actual_window_size
        ack.invoke_id = msg.invoke_id
        ack.sequence_number = msg.sequence_number
        _send(self.device.network, self.device.address, ack)
        # Append the final complex ACK to the list.
        self.response_segments.append(msg)
        # Assemble all of the complex ACKs into a single large APDU.
        # An APDU is used because there is no limit to the amount of
        # data an APDU can contain.
        response = APDU(self.response_segments.pop(0))
        while self.response_segments:
            response.data.fromstring(self.response_segments.pop(0).data)
        response.sequence_number = 0
        response.window_size = 0
        response.segmented_message = 0
        response.more_follows = 0
        # OK, we're done.
        self._complete(response)
        return
    ##
    # BACnet handler for the LastSegmentOfGroupReceived event.  This is
    # the event that occurs when receiveing a segment of a segmented
    # ComplexACK with a sequence-number == (initial_sequence_number+
    # actual_window_size)%256.
    def _LastSegmentOfGroupReceived(self, msg):
        if debug: print '_ClientTSM._LastSegmentOfGroupReceived'
        self.last_sequence_number = msg.sequence_number
        self.initial_sequence_number = self.last_sequence_number # @fixme ?
        # Acknowledge the final segment
        ack = NPDU()
        ack.version = 1
        ack.data_expecting_reply = 0
        ack.pdu_type = BACNET_SEGMENT_ACK_PDU
        ack.negative_ack = 0
        ack.server = 0
        ack.window_size = self.actual_window_size
        ack.invoke_id = msg.invoke_id
        ack.sequence_number = msg.sequence_number
        _send(self.device.network, self.device.address, ack)
        # Append the complex ACK to the list.
        self.response_segments.append(msg)
        return
    ##
    # BACnet handler for the NewSegmentReceived event.  This is the event
    # that occurs when receiving a segment of a segmented ComplexACK that
    # is not the first segment (sequence-number==0), nor the final segment
    # (more-follows==0), nor the last segment in a group.
    def _NewSegmentReceived(self, msg):
        if debug: print '_ClientTSM._NewSegmentReceived'
        self.last_sequence_number = msg.sequence_number
        # Append the complex ACK to the list.
        self.response_segments.append(msg)
        return
    ##
    # BACnet handler for the SegmentReceivedOutOfOrder event.  This is the
    # event that occurs when the TSM receives a segment with a
    # sequence_number != (last_segment_number+1)%256
    def _SegmentReceivedOutOfOrder(self, msg):
        if debug: print '_ClientTSM._SegmentReceivedOutOfOrder'
        # NACK the out of sequence segment.
        nack = NPDU()
        nack.version = 1
        nack.data_expecting_reply = 0
        nack.pdu_type = BACNET_SEGMENT_ACK_PDU
        nack.negative_ack = 1
        nack.server = 0
        nack.window_size = self.actual_window_size
        nack.invoke_id = msg.invoke_id
        nack.sequence_number = self.last_sequence_number
        _send(self.device.network, self.device.address, nack)
        return
    ##
    # BACnet handler for the UnexpectedPDU_Received event.  This is the
    # event that occurs when the TSM receives a PDU it didn't expect.  Duh.
    def _UnexpectedPDU_Received(self, msg):
        if debug: print '_ClientTSM._UnexpectedPDU_Received'
        if self.state == self.IDLE:
            return
        elif self.state == self.SEGMENTED_CONF \
             or self.state == self.SEGMENTED_REQUEST:
            self._send_Abort()
        else:
            # @fixme Do what?
            pass
        return
    def _send_Abort(self):
        # Send an ABORT.
        self._stop_request_timer()
        self._stop_segment_timer()
        abort = npdu.NPDU()
        abort.version = 1
        abort.data_expecting_reply = 0
        abort.pdu_type = BACNET_ABORT_PDU
        abort.server = 0
        abort.invoke_id = msg.invoke_id
        abort.reason = ABORT_REASON_INVALID_APDU_IN_THIS_STATE
        # Give up.
        self.exception = EIOError('Unexpected PDU.') # @fixme
        self._complete(None)

    def _DuplicateACK_Received(self, msg):
        if debug: print '_ClientTSM._DuplicateACK_Received'
        # Ignore it.
        return
    def _FinalACK_Received(self, msg):
        if debug: print '_ClientTSM._FinalACK_Received'
        self.state = self.AWAIT_CONFIRMATION
        return
    def _NewACK_Received(self, msg):
        if debug: print '_ClientTSM._NewACK_Received'
        self.initial_sequence_number = (msg.sequence_number + 1) % 0x100
        self.actual_window_size = msg.window_size
        return self._FillWindow()
    def _NewSegmentReceived_NoSpace(self, msg):
        if debug: print '_ClientTSM._NewSegmentReceived_NoSpace'
        raise ENotImplemented
    def _FinalTimeout(self, msg):
        if debug: print '_ClientTSM._FinalTimeout'
        raise ENotImplemented
    def _Timeout(self, msg):
        if debug: print '_ClientTSM._Timeout'
        raise ENotImplemented
    def _TimeoutSegmented(self, msg):
        if debug: print '_ClientTSM._TimeoutSegmented'
        raise ENotImplemented
    def _TimeoutUnsegmented(self, msg):
        if debug: print '_ClientTSM._TimeoutUnsegmented'
        raise ENotImplemented
    def _UnexpectedSegmentInfoReceived(self, msg):
        if debug: print '_ClientTSM._UnexpectedSegmentInfoReceived'
        raise ENotImplemented

##
# This class implements the Transaction State Machine for the Responding
# BACnet User (server).  [ASHRAE 135-1995 sub-clause 5.4.5]
class DeviceTSM:
    def wait_for_request(self, addr, apdu):
        pass
    def respond(self, response_id):
        pass

##
# An array of outstanding server transacations, indexed by the transaction's
# invoke_id.
# @note index/invoke_id zero are reserved.
_tsm_q = [None] * 0x0100
_request_id = 0L
_tsm_q_request_id_lock = Lock() # ensure tsm id is protected
##
# @return A new valid request id.
# @note Request ID's are unique values used to track request response pairs.
#       The invoke ID is encoded in the request ID as the low eight bits.  In
#       this implementation, invoke_id == 0 is reserved.
# @fixme Should we reserve a range of invoke_id's for unmanaged requests?
# if we find we run out of request_id's (more than 255 outstanding requests)
# we could maintain id's separately for each Device ID
def _next_request_id():
    global _request_id
    _tsm_q_request_id_lock.acquire()
    try:
        i = 0
        while i<256: # search for next _request_id
            _request_id += 1
            _request_id &= 0xff # 8 bit number
            if not _request_id: # id must not be 0
                _request_id = 1
            if _tsm_q[_request_id] is None: # see if busy
                return _request_id # normal exit, id is available
            if debug:
                msglog.log('bacnet', msglog.types.INFO, 'Busy TSM at: %d' % _request_id)
            i += 1
        # trouble.  All TSM's seem to be in use.  Should never happen
        raise EConnectionError('bacnet', msglog.types.ERROR, \
                          'Unable to find empty TSM %d' % _request_id)
    finally:
        _tsm_q_request_id_lock.release()

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
    def __init__(self):
        self.instance_number = 0
        self.object_type = 0
        self.max_apdu_len = 0
        self.can_recv_segments = 0
        self.can_send_segments = 0
        self.vendor_id = 0
        self.network = 0
        self.address = Addr()
        self.readPropertyFallback = 0  #0=Unknown, 1=RPM, 2=RPMsingular, 3=RP
        self.mac_network = 0
        self.mac_address = Addr()
        self.node = None

    def create_client_device(self, node):
        self.node = node

    def __str__(self):
        global _device_str
        result = _device_str % (self.instance_number, self.object_type,
                                self.max_apdu_len,
                                self.can_recv_segments, self.can_send_segments,
                                self.vendor_id, self.network, self.address,
                                _rpm_fallback[self.readPropertyFallback],
                                self.mac_network, self.mac_address)
        return result

_interface_str = """\
network._Interface:
  type:         %s
  name:         %s
  interface_id: %s
  network:      %d
  addr:         %s
  broadcast:    %s
  is_open:      %d"""
class _Interface:
    def __init__(self):
        self.type = None
        self.name = None
        self.interface_id = None
        self.network = None
        self.addr = None
        self.broadcast = None
        self.is_open = 0
        self.T_seg = 2.0  #where do we get these values???
        self.T_wait_for_seg = self.T_seg * 4
        self.T_out = 3.0
        self.N_retry = 3
        self.thread = None
        self.mtu = 501 #minimal mtu for a default (mstp size)
        self.master_device = None #one real device per interface
    def __str__(self):
        global _interface_str
        return _interface_str  % (self.type,self.name,self.interface_id,
                           self.network,self.addr,
                           self.broadcast,self.is_open)
##
# @return A list of supported interface types.
def interface_types():
    ret = []
    for name in _interface_types.keys():
        ret.append(name)
    return ret

##
# Process network NPDUs.
def _process_network_msg(network,msg,source):
    if msg.msg_type == I_AM_ROUTER:
        for i in range(0,len(msg.data),2):
            try:
                if debug: print '_process_network_msg: add_route'
                remote_network = (ord(msg.data[i]) << 8)
                remote_network += ord(msg.data[i+1])
                if remote_network != network:
                    add_route(remote_network, network, source)
            except:
                msglog.exception()

##
# Receive messages on an interface and handle them correctly.
def _receive_on_interface(interface):
    global _module_lock
    network = interface.network
    while interface.is_open:
        source = Addr()
        msg = _recv(network,source) #block in here
        if msg.network_msg:
            _process_network_msg(network,msg,source)
            # Copies to registerred queues?
        else:
            if msg.pdu_type == BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU:
                if msg.choice == I_AM_CHOICE:
                    if debug: print 'i am returned'
                    d = _DeviceInfo()
                    tags = tag.decode(msg.data).value
                    boid = tags[0].value
                    d.instance_number = boid.instance_number
                    if d.instance_number in server.the_devices:
                        # ignore I-AMs from our own server devices
                        # broadcast mes
                        return 
                    d.object_type = boid.object_type
                    d.max_apdu_len = tags[1].value
                    segmentationSupported = tags[2].value
                    d.can_recv_segments = segmentationSupported == 0 or \
                                          segmentationSupported == 2
                    d.can_send_segments = segmentationSupported == 0 or \
                                          segmentationSupported == 1
                    d.vendor_id = tags[3].value
                    d.mac_address = source
                    if msg.slen > 0: #non zero source address
                        d.address = Addr(msg.sadr)
                    else:
                        d.address = source
                    d.mac_network = network
                    if msg.snet > 0:  #non zero source net 
                        d.network = msg.snet
                        try:
                            if d.network in _network_map:
                                raise EInvalidValue("Device_ID",
                                 d.instance_number,
                                 'Attempted to set route to our network in I-AM')
                            add_route(d.network, network, source) 
                        except:
                            msglog.exception()  #before this, we were breaking thread at plugfest
                    else:
                        d.network = network
                    d.readPropertyFallback = 0

                    device_instance_number_conflict = 0  #check for a duplicate device instance number

                    _module_lock.acquire()
                    try:
                        if _device_table.has_key(d.instance_number):
                            old_d = _device_table[d.instance_number]
                            if ((old_d.address.address != d.address.address) or \
                                (old_d.network != d.network)):
                                device_instance_number_conflict = 1
                            #update new device from old device entries
                            d.readPropertyFallback = old_d.readPropertyFallback
    
                        _device_table[d.instance_number] = d
                    finally:
                        _module_lock.release()
                    # Copies to registerred queues?

                    if device_instance_number_conflict:
                        #print "Duplicate devices:"
                        #print old_d
                        #print d
                        msglog.log('broadway', msglog.types.WARN, \
                          'Dulplicate devices: ' + \
                          str(old_d) + ' and: ' + str(d))
                elif msg.choice == WHO_IS_CHOICE:
                    if debug: print 'who is recieved'
                    server.who_is_request_received(msg, network)
                elif msg.choice == UNCONFIRMED_COV_NOTIFICATION_CHOICE:
                    # Support for confirmed COV notifications only
                    # for now.
                    if debug: print 'Unconfirmed COV Notif received'
                else:
                    # queue.append(_NetworkMessage(source,msg))
                    pass # @fixme Process?
                         # Add to a trimmed q?  Copies to a registerred queues?
            elif (msg.pdu_type == BACNET_CONFIRMED_SERVICE_REQUEST_PDU) or \
                ((msg.pdu_type == BACNET_SEGMENT_ACK_PDU) and (msg.server == 0)):
                server.recv_request(interface, network, source, msg)
            elif (msg.pdu_type == BACNET_ABORT_PDU) and (msg.server == 0):
                server.recv_abort(network, source, msg)
            else:
                tsm = None
                try:
                    # @fixme Could crash...
                    tsm = _tsm_q[msg.invoke_id]
                    flag = 0
                    if tsm:
                        tsm._cv.acquire()
                        if msg.sspec:
                            flag = tsm.address.address == msg.sadr
                        else:
                            flag = tsm.address.address == source.address
                    if flag:
                        try:
                            #tsm.process_pdu(source, msg)
                            tsm.process_state(msg)
                        except Exception, e:
                            tsm.response = None
                            tsm.exception = e
                            tsm.state = tsm.COMPLETE
                        except:
                            tsm.response = None
                            tsm.exception = Exception(sys.exc_info()[0])
                            tsm.state = tsm.COMPLETE
                    else:
                        # @todo Handle unrequested messages (DeviceTSM)
                        #       This may require client address based queues.
                        if debug:
                            print "*** Dropped packet!"
                            print "*** TSM == ", tsm
                            print "*** flag ==", flag
                            print "*** msg.sspec", msg.sspec
                            if tsm:
                                print "*** tsm.address.address ==",\
                                      tsm.address.address
                            if msg.sspec:
                                print "*** msg.sadr ==", msg.sadr
                            else:
                                print "*** source.address ==", repr(source.address)
                finally:
                    if debug > 1: print 'NETWORK: _receive_on_interface - notify cv', msg.invoke_id
                    if tsm:
                        tsm._cv.notifyAll()
                        tsm._cv.release()
                    if debug > 1: print 'NETWORK: _receive_on_interface - cv notified', msg.invoke_id
                    #if debug > 1: print 'NETWORK: _receive_on_interface - release lock'
                    #_module_lock.release()
                    #if debug > 1: print 'NETWORK: _receive_on_interface - lock released'

class InterfaceThread(ImmortalThread):
    def __init__(self, interface):
        ImmortalThread.__init__(self,
                                name='BACnet Interface: %s' % interface.name)
        self.interface = interface
    def reincarnate(self):
        msglog.log('broadway',msglog.types.INFO,
                   'B/IP restarting listening on interface:\n' + \
                   str(self.interface))
    def run(self):
        ##
        # Run the interface's receiver.  If it fails, restart it.
        #def _receive_on_interface_wrapper(interface):
        if debug: print 'Start thread on interface'
        while self.interface.is_open:
            _receive_on_interface(self.interface)
        self.should_die()
        msglog.log('broadway',msglog.types.INFO,
               'B/IP stopped listening on interface:\n' + \
               str(self.interface))
        if debug: print 'Interface is no longer open'
        self.interface = None  #break circular reference

##
# Open a BACnet interface and add it to the internal routing tables.
#
# @param interface_type
# @param name
# @param network
# @keyword address
# @keyword broadcast
# @return An 'opaque' interface object.
# @note Do not modify the returned interface object.
def open_interface(interface_type, name, network, mtu=501, **keywords):
    global _module_lock
    _module_lock.acquire()
    try:
        if _network_map.has_key(network):
            raise EAlreadyOpen

        addr = Addr()
        if not _interface_types.has_key(interface_type):
            raise EInvalidValue, ('interface_type', interface_type)
        open_func = _interface_types[interface_type]
        if not keywords.has_key('get_broadcast'):
            keywords = copy.copy(keywords)
            keywords['get_broadcast'] = Addr()
        interface_id = open_func(name, network, addr, keywords)
        interface = _Interface()
        interface.type = interface_type
        interface.name = name
        interface.network = network
        interface.addr = addr
        interface.broadcast = keywords['get_broadcast']
        interface.is_open = 1
        interface.interface_id = interface_id
        interface.mtu = mtu 
        _network_map[network] = interface
        interface.thread = InterfaceThread(interface)
    finally:
        _module_lock.release()
    if interface:
        if interface.thread:
            interface.thread.start()
    return interface
    

##
# Allow the program to close a previously openned interface.
# @param interface The 'opaque' interface object returned by
#        <code>open_interface</code>.
def close_interface(interface):
    global _module_lock
    _module_lock.acquire()
    try:
        network = interface.network
        interface.is_open = 0
        #
        # A bit of a hack to wake up the interface's _receive thread.
        n = NPDU()
        n.version = 1
        n.dspec = 1
        n.dnet = 0xffff
        n.dlen = 0
        n.hop_count = 255
        n.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
        n.choice = 8
        _send(network, interface.addr, n)

        for akey in _device_table.keys():
            del(_device_table[akey])
        result = _close(network)
        if _network_map.has_key(network):
            del _network_map[network]
        pause(.01) # @fixme Why is this needed?  Forces thread switch?
        return result
    finally:
        _module_lock.release()

##
# Send an apdu.APDU.  This is for client requests, unconfirmed requests and
# network messages.
# @param device The BACnet device (an integer) to send the <code>apdu</code>.
# @param apdu The APDU to send.  Note, this can be an npdu.NPDU.
# @return A unique request id, used for receiving responses.  None if the
#         this is not a client BACNET_CONFIRMED_SERVICE_REQUEST_PDU.
# @note The network layer manages the invoke id for confirmed requests from
#       a client.
# @todo Support routing?
# @todo Support network = 0xFFFF.
# @todo Complain if trying to broadcast a confirmed APDU.

def send_request(device, apdu, timeout=3.0, **keywords):
    device_object = _device_info(device)
    if debug: print '_device_info result: ', str(device_object)
    if not device_object:
        if debug: print 'Device not found'
        raise EDeviceNotFound ('EDeviceNotFound with address: ' + str(device)) 
    if not apdu.network_msg and \
       apdu.pdu_type == BACNET_CONFIRMED_SERVICE_REQUEST_PDU:
        return _ClientTSM(device_object, apdu, timeout, **keywords).request_id
    else:
        _send(device_object.network, device_object.address, apdu)
        return None

##
# Send a response to a client request.  This is only intended for server
# responses.  All other NPDUs should be sent with send_request.
def send_response(*args):
    raise ENotImplemented

##
# Used by a virtual device to implement a service.
# @todo Determine where registerred network messages are recieved.  Here
#       could work, then devices could register for unsolicited messages.
#       This capability (network messages) is not required right now.
def recv_request(*args):
    raise ENotImplemented

##
# Receive a message on the specified <code>network</code>.
# @param request_id The network request_id ...
# @param timeout The most time, in seconds, to wait for an APDU.
# @return An APDU received as a response to request_id.
# @fixme Don't poll.
# @note No locking is performed intentionally.  The last action on a TSM
#       is that it is set to the complete state, so once it's complete it
#       becomes static.
def recv_response(request_id, timeout=3.0):
    global _tsm_q
    invoke_id = request_id & 0xff
    tsm = _tsm_q[invoke_id]
    if not tsm:
        raise EInvalidValue('No such request_id') # @fixme...
    tsm.T_seg = timeout * 2.0 / 3.0
    tsm.T_wait_for_seg = tsm.T_seg * 4
    tsm.T_out = timeout
    #we could alter tsm's timeouts here
    n_segments = 0
    if debug > 1: print 'NETWORK (for %d): recv_response - acquire cv', invoke_id
    tsm._cv.acquire()
    if debug > 1: print 'NETWORK (for %d): recv_response - cv acquired', invoke_id
    try:
        t_fail = now() + (timeout * 5)
        while tsm.state != tsm.COMPLETE:
            if debug > 1: print 'NETWORK (for %d): recv_response - start process_state', invoke_id
            tsm.process_state(None)
            if debug > 1: print 'NETWORK (for %d): recv_response - process_state complete', invoke_id
            if tsm.state != tsm.COMPLETE:
                if debug > 1: print 'NETWORK (for %d): recv_response - wait for cv', invoke_id
                timeout = t_fail - now()
                if timeout <= 0:
                    break
                tsm._cv.wait(timeout)
                if debug > 1: print 'NETWORK (for %d): recv_response - cv done waiting', invoke_id
        else:
            if tsm.exception:
                #del(_device_table[tsm.device.instance_number])
                raise tsm.exception
            message = tsm.response
            if debug > 1: print 'NETWORK (for %d): recv_response - return message: ', invoke_id, str(message)
            return message
    finally:
        _tsm_q[invoke_id] = None # release queue entry for another request to use
        if debug > 1: print 'NETWORK (for %d): recv_response - release cv', invoke_id
        tsm._cv.release()
        if debug > 1: print 'NETWORK (for %d): recv_response - cv released', invoke_id
    raise ETimeout('recv_response: Failsafe timeout.')
        

##
# Used to fail quickly for non-responsive devices.  Slow responses will still
# eventually get registerred when we receive the I_AM_CHOICE_REQUEST.
_failed_device_timeout = {}

##
# @return The _DevinceInfo instance that describes <code>device</code>.
#         None if the <code>device</code> is not in the _device_table
#         and it does not respond to a WHO_IS in under 2.5 seconds.
# @note This function gets less patient for non-responsive devices.
# @fixme Broadcast on all networks.
def _device_info(device):
    global _module_lock
    global _failed_device_timeout
    global _device_table
    _module_lock.acquire()
    try:
        if _device_table.has_key(device):
            info = _device_table[device]
            return info
        iterations = 25 # 25 iterations == ~2.5 seconds.
        count = 1
        if _failed_device_timeout.has_key(device):
            count,time_stamp = _failed_device_timeout[device]
            if uptime.secs() < (time_stamp + 2**count):
                return None #has not been long enough to try again. min 2 secs, max 128 secs
            iterations = (24 / (2**count)) + 2 #how long to wait for response
            count += 1
            count = min(count, 7) #missing device is sent who-is every 128 seconds
        _failed_device_timeout[device] = (count, uptime.secs())
    finally:
        _module_lock.release()

    for k in _network_map.keys():        
        # Broadcast a WHO IS device request.
        wi = NPDU()
        wi.version = 1
        wi.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
        wi.choice = WHO_IS_CHOICE
        wi.data = tag.Context(0,data.encode_unsigned_integer(device)).encoding + \
            tag.Context(1,data.encode_unsigned_integer(device)).encoding
        wi.dspec = 1
        wi.dlen = 0
        wi.dnet = 0xffff
        wi.hop_count = 255
        _send(k, Addr(), wi)  #I love garbage collection
        server.who_is_request_received(wi, k) #copy server since it won't hear this
        if debug: 
            print 'send WHOIS to: ', str(k)
        
    # Wait up to iterations/10.0 seconds for a response.
    #print iterations
    for i in xrange(1,iterations): #25, 13, 7, 4, 3, 2 interations, 
        pause(0.1)
        _module_lock.acquire()
        try:
            if _device_table.has_key(device):
                info = _device_table[device]
                if _failed_device_timeout.has_key(device):
                    # This is no longer an unresponsive device.
                    del _failed_device_timeout[device]
                if debug: print 'found the device'
                return info
        finally:
            _module_lock.release()
    if debug: print "whois, isn't"
    return None

def add_server_to_device_table(server):
    if _device_table.has_key(server.instance_number): return
    _device_table[server.instance_number] = server
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

def device_accepts_rpm(device):
    device_object = _device_info(device)
    if debug: print '_device_info result: ', str(device_object)
    if not device_object:
        if debug: print 'Device not found'
        raise EDeviceNotFound ('EDeviceNotFound with address: ' + str(device)) 
    #if not info: return None
    if debug: print 'accepts rpm: ', device, device_object.readPropertyFallback, device_object.can_recv_segments, device_object.can_send_segments
    if device_object.readPropertyFallback == BACNET_RPM_NOT_SUPPORTED: return 0 #proven itself to be a slacker
    if device_object.can_recv_segments and device_object.can_send_segments: return 1 #yea
    return 0
##
# @return Perform a Range bounded WHO_IS to populate the _device_table.  
#         Allow 0.1 seconds for anything new to show up.
def _who_are_devices_in_range(lower, upper):
    global _module_lock
    global _device_table
    starting_count = len(_device_table)
    iterations = 10 # 5 iterations == ~0.5 seconds.
    for k in _network_map.keys():        
        # Broadcast a WHO IS device request.
        wi = NPDU()
        wi.version = 1
        wi.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
        wi.choice = WHO_IS_CHOICE
        # lower and upper values are inclusive of the ID's allowed
        wi.data = tag.Context(0,data.encode_unsigned_integer(lower)).encoding + \
            tag.Context(1,data.encode_unsigned_integer(upper)).encoding
        wi.dspec = 1
        wi.dlen = 0
        wi.dnet = 0xffff
        wi.hop_count = 255
        _send(k, Addr(), wi)  #I love garbage collection
        server.who_is_request_received(wi, k) #copy server since it won't hear this
        if debug: 
            print 'send WHOIS to: ', str(k)
    prior_length = 0
    # Wait up to iterations/10.0 seconds after the last response.
    i = 0
    while i < iterations:
        pause(0.1)
        _module_lock.acquire()
        try:
            if len(_device_table) != prior_length:
                i = 0
                prior_length = len(_device_table)
            else:
                i = i + 1
        finally:
            _module_lock.release()
#    _device_table[2] = _device_table[1]   #put in to test more than one device in the device info table
    return len(_device_table) - starting_count
def _global_who_are_devices():
    global _module_lock
    global _device_table
    starting_count = len(_device_table)
    iterations = 10 # 5 iterations == ~0.5 seconds.
    # Broadcast a WHO IS device request.
    for k in _network_map.keys():        
        wi = NPDU()
        wi.version = 1
        wi.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
        wi.choice = WHO_IS_CHOICE
        wi.dspec = 1
        wi.dlen = 0
        wi.dnet = 0xffff
        wi.hop_count = 255
        _send(k, Addr(), wi)
        if debug: print 'send who_are to: ', str(k)
    prior_length = 0
    # Wait up to iterations/10.0 seconds after the last response.
    i = 0
    while i < iterations:
        pause(0.1)
        _module_lock.acquire()
        try:
            if len(_device_table) != prior_length:
                i = 0
                prior_length = len(_device_table)
            else:
                i = i + 1
        finally:
            _module_lock.release()
#    _device_table[2] = _device_table[1]   #put in to test more than one device in the device info table
    return len(_device_table) - starting_count
MAX_DEVICE_ID = 4194304
def _who_are_devices():
    global _device_table
    if len(_device_table) == 0:
        print 'send global who are'
        _global_who_are_devices() # start with a global who is.
    starting_count = len(_device_table)
    print 'device table starting length: ', starting_count
    # search in the gaps for new device id's we may have missed
    known_devices = _device_table.keys()
    known_devices.sort()
    known_devices.append(MAX_DEVICE_ID)
    lower = 0
    print known_devices
    while len(known_devices):
        upper = known_devices.pop(0)
        if (upper - lower) > 0:
            print ' gap between lower: %d and upper: %d' % (lower, upper - 1)
            # search between the lower and upper addresses for new devices
            if _who_are_devices_in_range(lower, upper - 1): # new devices
                # since new device(s) found, reconstruct list and try again
                known_devices = _device_table.keys()
                known_devices.sort()
                known_devices.append(MAX_DEVICE_ID)
                # trim off id's < lower
                while len(known_devices):
                    x = known_devices.pop(0)
                    if x >= lower:
                        known_devices.insert(0,x)
                        break
                continue # don't change lower and try again
        # if there is no gap or there were no new boards
        lower = upper + 1
    return len(_device_table) - starting_count

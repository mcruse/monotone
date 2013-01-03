"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
"""Module rznet_line_handler.py: Class definitions for RznetThread and support
classes.  RznetThread performs actual I/O ops, and includes a single wait point
for all events associated with all ports assocd with a one or more RZNet RS485
ports.
"""

from termios import *

import array
import exceptions
import fcntl
import math
import os
import select
import string
import struct
import sys
import time
import tty
import types
import weakref
from moab.linux.lib import uptime #use uptime.secs() instead of time.time()

from mpx import properties

from mpx.lib import msglog
from mpx.lib import socket

from mpx.ion.host.eth import Eth
from mpx.ion.host.port import Port
from mpx.ion.rz.InterfaceRouteNode import ComIfRouteNode

from mpx.lib import thread_pool
from mpx.lib import thread_queue
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.debug import dump_tostring
from mpx.lib.exceptions import EAlreadyOpen
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.exceptions import ENotOpen
from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import EUnreachableCode
from mpx.lib.exceptions import MpxException
from mpx.lib.msglog.types import DB
from mpx.lib.msglog.types import ERR
from mpx.lib.msglog.types import INFO
from mpx.lib.msglog.types import WARN
from mpx.lib.node import CompositeNode
from mpx.lib.node import ConfigurableNode
from mpx.lib.rz.containers import MultiListMixin
from mpx.lib.rz.utils import *
from mpx.lib.scheduler import scheduler
from mpx.lib.threading import Thread
from mpx.lib.threading import Semaphore
from mpx.lib.threading import Condition
from mpx.lib.threading import EKillThread
from mpx.lib.threading import Event
from mpx.lib.threading import ImmortalThread
from mpx.lib.threading import Lock
from mpx.lib.threading import currentThread

class ERestart(MpxException):
    pass

class EPollErr(MpxException):
    pass

class _ProfileStub:
    def __init__(self,method):
        self.bound_method = method
        return
    def __call__(self,evt):
        import profile
        import mpx.lib.rz.rzhost_line_handler
        mpx.lib.rz.rzhost_line_handler._ProfileStub_self = self
        mpx.lib.rz.rzhost_line_handler._ProfileStub_evt = evt
        profile.run("""
import mpx.lib.rz.rzhost_line_handler
mpx.lib.rz.rzhost_line_handler._ProfileStub_self.bound_method(
    mpx.lib.rz.rzhost_line_handler._ProfileStub_evt
    )
""")
        return None

REPORT_LIST_NAME = 'REPORT_LIST_NAME'
SUBSCR_LIST_NAME = 'SUBSCR_LIST_NAME'
BOUND_LIST_NAME = 'BOUNDR_LIST_NAME'

from rznet_line_handler import PointData, DevSubscrData, DevBoundData, PktData
from rznet_line_handler import ST_SYN, ST_SOH, ST_HDR, ST_EXT

_tmp_dir = properties.get('TEMP_DIR')

class RzhostThread(ImmortalThread):
    #n_tty_num = 0
    #@fixme: "6" is owned by X25; need to assign new number to rznet...
    #n_rznet_num = 6

    class AML_Engine:
        retry_after = 30.0 # - How long to wait for an AML to be responded to.
                           #   @fixme Brutally slow to account for time for
                           #          150+ AMLs to all get responses.  Batching
                           #          of AMLs and knowing when AMLs acutally
                           #          were sent would be a big help...
        n_retries = 2      # - How many times to retry after initial AML.
        def __init__(self, rznet_thread, point_data):
            self.debug_lvl = rznet_thread.debug_lvl
            self.rznet_thread = rznet_thread
            self.point_data_ref = weakref.ref(point_data)
            self.remaining_retries = self.n_retries
            if point_data._aml_engine is not None:
                # Replace existing AML_Engine
                try:
                    if self.debug_lvl & 8:
                        msglog.log(
                            'mpx:rz', DB,
                            'AML_Engine(): Replacing AML_Engine for %d,%d' %
                            (point_data.dst_addr, point_data.obj_id)
                            )
                    self._aml_engine.retry_event.cancel()
                except:
                    msglog.exception()
            point_data._aml_engine = self
            self.retry_event = scheduler.after(self.retry_after,
                                               self.retry_callback)
            return
        def retry_callback(self):
            thread_pool.NORMAL.queue_noresult(self.retry_handler)
            return
        def retry_handler(self):
            point_data = self.point_data_ref()
            if point_data is None:
                # The point data was destroyed, nothing to see here.
                if self.debug_lvl & 8:
                    msglog.log('mpx:rz', DB,
                               'retry_handler():  PointData dereferenced.')
                return
            rznet_thread = self.rznet_thread
            rznet_thread._internal_lock.acquire()
            try:
                if point_data.value is not None:
                    # If there is a value, the AML succeeded.
                    point_data._aml_engine = None
                    if self.debug_lvl & 8:
                        msglog.log(
                            'mpx:rz', DB,
                            'retry_handler(): Received value for %d,%d' %
                            (point_data.dst_addr, point_data.obj_id)
                            )
                    return
                if self.remaining_retries <= 0:
                    point_data.value = ETimeout()
                    point_data.state = 0
                    if point_data._cov_callback is not None:
                        # Propagate the timeout to the appropriate Node(s):
                        point_data._check_cov()
                    if self.debug_lvl & 8:
                        msglog.log(
                            'mpx:rz', DB,
                            'retry_handler(): Time out on %d,%d' %
                            (point_data.dst_addr, point_data.obj_id)
                            )
                    return
                self.remaining_retries -= 1
                rznet_thread._send_AML(point_data.dst_addr, point_data.obj_id)
                self.retry_event = scheduler.after(self.retry_after,
                                                   self.retry_callback)
                if self.debug_lvl & 8:
                    msglog.log(
                        'mpx:rz', DB,
                        'retry_handler(): Sent LAN_AML for %d,%d' %
                        (point_data.dst_addr, point_data.obj_id)
                        )
            finally:
                rznet_thread._internal_lock.release()
            return

    def __init__(self, rs232_port, slave_port_num,
                 req_addr, application_parent):
        ImmortalThread.__init__(self)

        self._port_rznp = rs232_port
        self._listen_skt_rzhs_port_num = slave_port_num
        #self._port_rzhm = master_port_node # we'll try to open this dev file
        #self._QA = QA
        self._req_addr = req_addr
        self._application_parent = application_parent
        self._mntr_request = 0
        ##
        # The command_q processes commands serially on another thread (from a
        # thread pool), thus allowing the line handler to continue handling
        # incomming messages:
        self._command_q = thread_queue.ThreadQueue(thread_pool.NORMAL, 1)

        self.debug_lvl = application_parent.debug_lvl
        self.debug_print(1, '__init__()')

        ##
        # _reestablish_global_aml_ownership*:
        #
        #   This section is to recover from a "diagnostic" perfectHost
        #   stealing subscriptions to points which we are interested.
        #
        #   *_busy:  Indicates that we are activily reestablishing our monitor
        #            list in the backgoround so don't queue/run another handler
        #            at this time.
        #
        #   *_entry:  The current scheduler entry to "steal back" the
        #             points we were monitoring.  None if no one stole our
        #             subscriptions.
        #
        #   *_aml_timeout:  How long (in seconds) after a monitor "steals"
        #                   subscriptions to wait before "stealing" them back.
        #
        #   *_cml_timeout:  How long (in seconds) after a monitor explicitly
        #                   releases a subscription to wait before "stealing"
        #                   them back.
        #
        self._reestablish_global_aml_ownership_busy = False
        self._reestablish_global_aml_ownership_entry = None
        self._reestablish_global_aml_ownership_aml_timeout = 60.0 * 10.0
        self._reestablish_global_aml_ownership_cml_timeout = 60.0 * 1.0

        #
        # RS485 port's own and next addresses are init'd to invalid
        # values.  However, both are read each time they are needed
        # (eg for pkts to PhWin), since own addr can be changed
        # without notification by user via procfs, and next addr
        # depends on state of network token passing:
        # THE HOST VERSION gets it's "address" from the configuration
        self._rznp_addr = self._application_parent.rznet_addr
        # NO NEXT ADDRESS, SINCE NOT TOKEN PASSING self._rznp_next_addr = 0

        # PhWin client (TCP socket) port variables. (Used by serial
        # connection also, via PPP.):
        self._listen_skt_rzhs = None # listen_skt for PhWin connection
        self._fd_listen_skt_rzhs = -1
        self._data_skt_rzhs = None  # data_skt for PhWin connection
        self._fd_data_skt_rzhs = -1
        self._data_skt_rzhs_rd_buf_len = 4096 # - nice default number,
                                          #   replaced in __set_up()
        # RZNet (RS485 COM) port variables:
        # THERE IS NO NET PEER OR LDISC self._file_rznp = None # - we'll try to open this dev file in
        #self._fd_rznp = -1     #   self.__set_up()...
        # init value is overwritten in __set_up()
        #NO LDISC USED self._rznp_ldisc_num_org = struct.pack('i', self.n_tty_num)

        # RZHostMaster Port (RS232 COM) port variables. (This port
        # is optional!):
        #  in self.start()
        self._file_rzhm = None # - we'll try to open this dev file in
        self._fd_rzhm = -1     #   self.__set_up()...

        #
        # Init response pkt processing dictionary. Key = type; Value = method.  
        # 
        self._rznp_procs = {
            #the first two are normally only seen on the Lan but are routed through to the mediator
            LAN_OBJ_VAL  : self._proc_rznp_rd_bound_val, #routed through for bound variables
            LAN_UPDATE   : self._proc_rznp_ack, #self._proc_rznp_update_request, #routed through to trigger an update from bound variables
            #these are ACK packets to specific commands
            LAN_AML      : self._proc_rznp_aml_ack, #ack to an aml request, start requesting reports
            LAN_CML      : self._proc_rznp_ack, #capture locallay and do not relay to phwin
            LAN_REPORT   : self._proc_rznp_REPORT, #response packet
            LAN_OBJ_OVRD : self._proc_rznp_ack,
            LAN_OBJ_CLOV : self._proc_rznp_ack,
            LAN_TIME     : self._proc_rznp_time_ack,
            #any not listed are passed back to phwin unchanged
            }
        # Init phwin command pkt processing dictionary.
        # Handler listens to phwin commands and acts on the following list.  any others are passed through unchanged.
        # the commands are merged with the state of the line handler and/or passed through to the modem server
        # Key = type; Value = method:
        self._rzhs_procs = {
            LAN_AML : self._proc_rzhs_AML, #merge the phwin aml points in with mpx points and add any new ones (always broadcast)
            LAN_CML : self._proc_rzhs_CML, #pass cml to any point the mpx is not intereseted in (always broadcast)
            LAN_TO_MEM : self._proc_rzhs_to_mem, #examine address to see if we should change 'state' (start/stop/etc) (can be any address)
            LAN_REPORT : self._proc_rzhs_REPORT, #reply with most recent point changes (mpx polls this all the time itself) (always modemserver)
            LAN_OBJ_OVRD : self._proc_rzhs_ovrd,
            LAN_OBJ_CLOV : self._proc_rzhs_clov,
            LAN_TIME     : self._proc_rzhs_null,
            LAN_GOTO     : self._proc_rzhs_goto,
            #LAN_SEND_MEM : self._proc_rzhs_send_mem, #pass through
            #anything not listed should be passed through and any response passed back
            }

        self.def_max_dev_subscrs = 256 #max sub points for entire system

        #incoming packets from phwin. 
        #handlers for various stages of collecting a complete packet
        self._pkt_form_states = { ST_SYN : self._do_SYN,
                                  ST_SOH : self._do_SOH,
                                  ST_HDR : self._do_HDR,
                                  ST_EXT : self._do_EXT }

        #incoming packets from modem server
        self._response_form_states = { ST_SYN : self._rsp_SYN,
                                       ST_SOH : self._rsp_SOH,
                                       ST_HDR : self._rsp_HDR,
                                       ST_EXT : self._rsp_EXT }

        # Init timing vars:
        self._tm0 = 0.0
        self._tm1 = 0.0
        self._tm2 = 0.0
        self._tm3 = 0.0
        self._tm_del1 = 0.0
        self._tm_del2 = 0.0
        self._tm_del3 = 0.0
        self._tm_del1_avg = 0.0
        self._tm_del2_avg = 0.0
        self._tm_del3_avg = 0.0
        self._last_update = 0
        self._max_update_period = 2.0 #if no icoming changes, period between update requests
        self._min_update_period = 0.1 #if full 11-point update responses, period between update requests
        self._aml_defferal = 0
        self._aml_defferal_count = 0

        self._internal_lock = Lock()
        self._internal_lock.acquire() # - disable over-eager accessors until
        self._port_rznp_condition = Condition(Lock()) #used to implement timeout retry logic on rznp com port
        self._port_rznp_timeout = 5.0
        self._port_rznp_state = None
        self._port_rznp_lock = Lock() #control access to the rznp com port for transmitting
        self._cml_queue = []
        self._connected_state = None
        self._application_running = 1 #running by default.  This is set when phwin sends app start / stop commands
        self._inital_update_request = 0

        self._set_value_cache = {}
        self._set_value_fifo = []
        self._set_value_semaphore = Semaphore()
        self._set_value_thread = ImmortalThread()
        self._set_value_thread.run = self._set_value_run
        self._set_value_thread.start()

        self._rcvd_value_cache = {}
        self._rcvd_value_fifo = []
        self._rcvd_value_semaphore = Semaphore()
        self._rcvd_value_thread = ImmortalThread()
        self._rcvd_value_thread.run = self._rcvd_value_run
        self._rcvd_value_thread.start()

        self.__init_set_up = True

        return

    ##
    # @note Should be called with self._internal_lock already acquired.
    def __set_up(self):
        global REPORT_LIST_NAME
        self.debug_print(1, '__set_up()')

        try:
            self._last_response_pkt = None  #the last thing sent to phwin
            # List of LAN_TO_HOST pkts waiting to go out in response to
            # incoming LAN_REPORT pkts from PhWin. Needed since LTH
            # extension length is limited to 11 point values, at 11 bytes
            # each, and since Modem Server may send only one pkt in
            # response to any given pkt recvd from PhWin:
            # IDEA: remove length restriction to LAN_REPORT response (lan to host) or bump it to 4096, 1024, etc
            self._update_response_pkts = []
            # Dict of registered file descriptors to event processor
            # method.  Maintained by start() and methods called from run():
            self._fds = {}

            # Per-Device Caches of subscribed points and their latest
            # values/status:
            self._device_subscrs = {} # K: device LAN Addr,
                # V: DeviceSubscrData instance, containing
                #    self-formed list of PointData instances
            self._bound_devices = {}
            # Set vars for waiting for response in get_val():
            self._read_wait_evt = Event()
            self._read_wait_time = 10.0 # - reader waits this time (sec)
                                        #   before returning error
            self._set_cond_on_read = 0 # - order read thread to notify the
                                       #   condition on read, rather than
                                       #   process pkt.
            # Set vars for waiting for thread looping in run() to exit:
            self._run_exit_evt = Event()
            self._run_exit_time = 10.0 # - stop() waits this time (sec)
                                       #   before continuing with shutdown
            # PhWin packet formation vars:
            self._pkts = [] # list of single-pkt bufs (where phwin incoming packets are collected)
            self._num_pkts = 2
            for i in range(self._num_pkts):
                self._pkts.append(PktData())
            self.debug_print(1, 'pkt0: %s', str(self._pkts[0]))
            self.debug_print(1, 'pkt1: %s', str(self._pkts[1]))
            self._last_pkt_idx = -1 # - idx of last valid unused pkt, if
                                    #   any 
            self._cur_pkt_idx = 0   # - idx of cur incoming pkt
            self._pkt_form_state = 0 #holds SYN, SOH, HDR or EXT state enum

            #now setup the same sort of variables for responses from the system
            self._responses = [] # list of single- responses bufs (where phwin incoming packets are collected)
            self._num_responses = 2
            for i in range(self._num_responses):
                self._responses.append(PktData())
            self.debug_print(1, 'response 0: %s', str(self._responses[0]))
            self.debug_print(1, 'response 1: %s', str(self._responses[1]))
            self._last_response_index = -1 # - idx of last valid unused pkt, if
                                    #   any 
            self._current_response_index = 0   # - idx of cur incoming pkt
            self._response_form_state = 0 #holds SYN, SOH, HDR or EXT state enum

            # Create Schedule and timer IDs and periods:
            self._sched_entry_subscr_scan = None # set by Schedule.after()
            self._timer_ID_subscr_scan = 0
            self._time_subscr_scan = 1000.0
            # Init node tuple to be read from ldisc ioctl upon client  NO MORE LDISC
            # request: 
            self._nodes_list = []  #mpx sends lan status request and stores lan addresses here
            self._ext_nodes = array.array('B') # - pkt extension containing
                                               #   node addrs

            # List of updated points waiting for xmssn to PhWin client at next
            # LAN_REPORT req
            self._REPORT_pts = MultiListMixin(REPORT_LIST_NAME)

            # Add cmd_skts:
            self._near_cmd_skt, self._far_cmd_skt = create_cmd_skts(
                'RznetThread', _tmp_dir
                )
            self._fd_cmd = self._near_cmd_skt.fileno()
            self._fds[self._fd_cmd] = self._proc_evt_cmd # add entry to dict:
            self.debug_print(1, 'cmd_skts opened: fd = %d.', self._fd_cmd)

            # Open dev file for RZNet Port object:
            try:
                self._port_rznp.open()
            except EAlreadyOpen:
                self.debug_print(1, 'RZNet device already open')
                pass
            self._file_rznp = self._port_rznp.file
            self._fd_rznp = self._file_rznp.fileno()
            self.debug_print(1, 'RZNet dev file opened: %s (%d).', 
                             self._port_rznp.dev, self._fd_rznp)
            # make sure that we actually receive a "0"...
            #self._rznp_ldisc_num_org = struct.pack('I', 0xFF)
            # Get/save original ldisc for opened port (for restoration in
            # stop()):
            # self._rznp_ldisc_num_org = fcntl.ioctl(self._fd_rznp, TIOCGETD,
                                                   # self._rznp_ldisc_num_org)
            # need first elem of one-elem tuple
            # org_ldisc_num = struct.unpack('I', self._rznp_ldisc_num_org)[0]
            # self.debug_print(1, 'Saved original RZNet dev file ldisc # %d.',
                             # org_ldisc_num)
            # Set ldisc to "rznet":
            # s = struct.pack('I', self.n_rznet_num)
            # try:
                # fcntl.ioctl(self._fd_rznp, TIOCSETD, s)
            # except IOError, (errno, strerror):
                # msglog.log('broadway', ERR,
                           # 'Failed to set rznet ldisc on port %s:\n'
                           # 'Error %d: %s\n Make sure module n_rznet is loaded!'
                           # % (self._port_rznp.dev, errno, strerror))
                # self._port_rznp.close()
                # raise EKillThread('Failed to set rznet ldisc')
                # return

            self._fds[self._fd_rznp] = self._proc_evt_rznp # add entry to dict:

            # If RznetNode has requested that we set a specific rznet_addr,
            # then do it now:
            #s_own_addr = struct.pack('I', self._req_addr)
            #fcntl.ioctl(self._fd_rznp, RZNET_IOCSADDR, s_own_addr)

            # Get initial own and next addresses from RS485 dev file into self
            # properties. (Next will be same as own, until ldisc joins the
            # RZNet):
            #self._get_addrs()

            #self.debug_print(1, 'New RZNet dev file ldisc = rznet (%d)',
                             #self.n_rznet_num)

            # Always open a listen_socket in case PhWin wants to connect:
            self._listen_skt_rzhs = create_listen_skt(self._listen_skt_rzhs_port_num)
            if self._listen_skt_rzhs == None:
                raise EKillThread('Failed to create PhWin socket')
            self._fd_listen_skt_rzhs = self._listen_skt_rzhs.fileno()
            # add entry to dict:
            self._fds[self._fd_listen_skt_rzhs] = self._proc_evt_lrzhs

            # Set buf_lens to obtain the most bytes from skts without multiple
            # reads:
            self._data_skt_rzhs_rd_buf_len = self._listen_skt_rzhs.getsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF
                )
            self.debug_print(1, 'fd %d has read buf len = %d.',
                             self._fd_listen_skt_rzhs, self._data_skt_rzhs_rd_buf_len)
            self._near_cmd_skt_rd_buf_len = self._near_cmd_skt.getsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF
                )
            self.debug_print(1, 'fd %d has read buf len = %d.',
                             self._fd_cmd, self._near_cmd_skt_rd_buf_len)
            # Start the subscription scan timer. Scans for expired
            # subscriptions once every timer period:
            self._sched_entry_subscr_scan = scheduler.after(
                self._time_subscr_scan, self.timeout_callback,
                (self._timer_ID_subscr_scan,)
                )
            # Open the RZHostMaster port, if any:
            # if (self._port_rzhm != None) and (self._QA == 1):
                # self._port_rzhm.open()
                # self._file_rzhm = self._port_rzhm.file
                # self._fd_rzhm = self._file_rzhm.fileno()
                # self.debug_print(1, 'RZHostMaster dev file opened: %s (%d).',
                                 # self._port_rzhm.dev, self._fd_rzhm)
                ##add entry to
                ##dict: 
            # Order unsubscription of all points subscribed by this
            # line_handler during a previous incarnation:
            self._send_global_CML()

            #be master timekeeper
            self._master_hour = None
            self._application_running = 1 #running by default.  This is set when phwin sends app start / stop commands

            # Create one-and-only poll object:
            self._poll_obj = select.poll()

            # Register for events from rznp and lrzhs:
            for fd in self._fds.keys():
                self._poll_obj.register(fd, select.POLLIN)

        finally:
            # Done with init:
            if self.__init_set_up:
                self.__init_set_up = False
                self._internal_lock.release()

        return

    def notify_nodes(self):
        try:
            def all_descendants(parent, result_list=None):
                if result_list is None:
                    result_list = []
                try:
                    children = parent.children_nodes()
                except:
                    return result_list
                for child in children:
                    result_list.append(child)
                    all_descendants(child, result_list)
                return result_list
            all_rznet_nodes = all_descendants(self._application_parent)
            for n in all_rznet_nodes:
                if hasattr(n, '_line_handler_up'):
                    n._line_handler_up(self)
        except:
            msglog.exception()
        return

    def __tear_down(self):
        self.debug_print(1, '__tear_down()')

        #
        # Force shutdown of command sockets:
        #
        try:    self._near_cmd_skt.shutdown(2)
        except: msglog.exception()
        try:    self._far_cmd_skt.shutdown(2)
        except: msglog.exception()
        # Clear command socket variables:
        self._near_cmd_skt = None
        self._far_cmd_skt = None
        self._fd_cmd = None
        #
        # Stop the scan timer:
        #
        try:
            if self._sched_entry_subscr_scan != None:
                self._sched_entry_subscr_scan.cancel()
        except:
            msglog.exception()
        #
        # Unregister all fd's from the poll() machinery:
        #
        for fd in self._fds.keys():
            try:    self._poll_obj.unregister(fd)
            except: msglog.exception()
        #
        # Close the RZNet port object.
        #
        try:    self._port_rznp.close()
        except: msglog.exception()
        #
        # Empty out the poll vectoring map:
        #
        try:    self._fds.clear()
        except: msglog.exception()
        #
        # Close the RZHostMaster port, if any:
        #
        try:
            if (self._fd_rzhm != -1):
                self._file_rzhm.close()
                self._file_rzhm = None
                self._fd_rzhm = -1
        except:
            msglog.exception()
        #
        # Close client listen_skt (always open from __set_up() till here):
        #
        try:    self._listen_skt_rzhs.close()
        except: msglog.exception()
        self._fd_listen_skt_rzhs = -1
        #
        # Close client data_skt (if open):
        #
        try:
            if self._data_skt_rzhs is not None:
                self._data_skt_rzhs.close();
        except:
            msglog.exception()
        self._data_skt_rzhs = None
        self._fd_data_skt_rzhs = -1
        #
        # Reset original ldisc for port:
        #
        # try:
            # fcntl.ioctl(self._fd_rznp, TIOCSETD, self._rznp_ldisc_num_org)
            # org_ldisc_num = struct.unpack('i', self._rznp_ldisc_num_org)
            # self.debug_print(1, 'Restored original ldisc # %d.',
                             # org_ldisc_num)
        # except:
            # msglog.exception()
        #
        # Close RS485 port:
        #
        try:
            self._file_rznp.close()
        except:
            msglog.exception()
        self._file_rznp = None
        self._fd_rznp = -1

        # Show that ldisc is no longer part of network:
        #self._rznp_next_addr = self._rznp_addr

        if not self.is_immortal():
            self._run_exit_evt.set()
        return

    def stop(self):
        self.debug_print(1, 'stop()')
        # Send a stop cmd to thread (ie run() method), and wait for run() to
        # exit, up to specified max num msec:
        self._send_cmd('stop')
        self._application_running = 0
        if self is not currentThread():
            self._run_exit_evt.wait(self._run_exit_time)
        return
    def prune(self): #owner node is being pruned.  Delete thyself of evil things
        if self._set_value_thread:
            self._set_value_thread.should_die()
            self._set_value_thread = None
            self._set_value_semaphore.release() #kick it in the pants so it will terminate
    def restart(self):
        self.debug_print(1, 'restart()')
        # Send a restart cmd to thread (ie run() method).
        if self is not currentThread():
            self._send_cmd('restart')
        else:
            raise ERestart()
        return

    def run(self):
        self.debug_print(1, ' runs on %s.', currentThread())

        try:
            self.__set_up()
        except:
            msglog.exception()
            raise EKillThread('__set_up() failed.')

        # Find any nodes that already have ChangeOfValueEvent consumers:
        self.notify_nodes()

        try: # main Thread loop:
            while True:
                timeout_msec = -1 # no poll()-based timeouts, use Schedulers
                # Enter the one-and-only wait state used by this RznetThread:
                evt_pairs = self._poll_obj.poll(timeout_msec)
                #self.debug_print(512, 'Event pairs received = %s', evt_pairs)
                #
                # If no event pairs are returned by poll(), then a timeout
                # must have occurred:
                if len(evt_pairs) == 0:
                    self._proc_timeout()
                # Else, process event pairs:
                else:
                    for evt_pair in evt_pairs:
                        # Timestamp:
                        if evt_pair[0] == self._fd_data_skt_rzhs:
                            self._tm2 = time.time()
                        result = self._fds[evt_pair[0]](evt_pair[1])
                hour = time.localtime()[3]
                if hour != self._master_hour:
                    self._master_hour = hour
                    self._send_time()
        finally:
            self.__tear_down()
            # Indicate run() is exiting:
            self.debug_print(1, 'on %s is ending run()...', currentThread())
        return
    def register_rznet_cov(self, lan_address, id_number, _cov_event_callback):
        dst_addr = lan_address
        obj_id = id_number
        cov_callback = _cov_event_callback
        point_data = None
        #print "register_rznet_cov: acquire"
        self._internal_lock.acquire()
        #print "register_rznet_cov: acquired"
        try:
            value = None
            if not self._device_subscrs.has_key(dst_addr):
                self._device_subscrs[dst_addr] = DevSubscrData(
                    self.def_max_dev_subscrs,
                    self.debug_lvl
                    )
            dev_subscr_data = self._device_subscrs[dst_addr]
            result = dev_subscr_data.add_point_subscr(dst_addr, obj_id)
            point_data = dev_subscr_data.get_point(obj_id)
            # Setup the callback hook.  Assumes only one ION ever does
            # get_value for this point.
            point_data._cov_callback = cov_callback
            if type(result) == types.ListType:
                for t in result:
                    self._send_CML(t[0], t[1])
                    if self.debug_lvl & 16:
                        msglog.log(
                            'mpx:rz', DB,
                            'register_rznet_cov(): Sent CML for (%r,%r).' %
                            (t[0], t[1])
                            )
                result = -1
            # if point already subscribed on device:
            if (result == 0):
                pass
            else: # else, point needs to be subscribed on device:
                self._send_AML(dst_addr, obj_id)
                self.AML_Engine(self, point_data)
                if self.debug_lvl & 8:
                    msglog.log('mpx:rz', DB,
                               'register_rznet_cov(): '
                               'Sent LAN_AML for %d,%d' %
                               (dst_addr, obj_id))
            if point_data.value is not None and point_data.state is not None:
                # If the point already has a value, ensure that the consumer
                # gets an initial value:
                cov_callback(point_data)
        finally:
            #print "register_rznet_cov: release"
            self._internal_lock.release()
            #print "register_rznet_cov: released"
        return
    def unregister_rznet_cov(self, lan_address, id_number):
        point_in_use = False
        #print "unregister_rznet_cov: acquire"
        self._internal_lock.acquire()
        #print "unregister_rznet_cov: acquired"
        try:
            dev_subscr_data = self._device_subscrs[lan_address]
            point_data = dev_subscr_data.get_point(id_number)
            if point_data is not None:
                if point_data.phwin_is_using():
                    if self.debug_lvl & 16:
                        msglog.log(
                            'mpx:rz', DB,
                            'unregister_rznet_cov:Skipped CML for (%r,%r), '
                            'in use.' % (lan_address, id_number)
                            )
                else:
                    point_data._cov_callback = None
                    dev_subscr_data.remove_point_subscr(id_number)
                    self._send_CML(lan_address, id_number)
                    if self.debug_lvl & 16:
                        msglog.log(
                            'mpx:rz', DB,
                            'unregister_rznet_cov:Sent CML for (%r,%r).' %
                            (lan_address, id_number)
                            )
        except:
            #print "unregister_rznet_cov: release in except"
            self._internal_lock.release()
            #print "unregister_rznet_cov: released in except"
            msglog.exception()
            return
        else:
            #print "unregister_rznet_cov: release"
            self._internal_lock.release()
            #print "unregister_rznet_cov: released"
        return
    # get_val(): Blocks until either a value is returned OR timeout occurs
    #            (in which case it rtns "None"). Requires a wait loop after
    #            request has been sent, OUTSIDE of lock protection. Read
    #            thread OR timer will have to wake us up. Upon be awoken by
    #            read, need to scan pkt and determine if it is the one for
    #            which we waited. If not, and if time remains, need to
    #            re-enter wait state. Response pkt criteria: same dst_addr,
    #            same obj_id, pkt type is LAN_MTR_VAL:
    def get_value(self, dst_addr, obj_id,
                  force_resubscribe=0, cov_callback=None):
        point_data = None
        #print "get_value: acquire"
        self._internal_lock.acquire()
        #print "get_value: acquired"
        try:
            value = None
            if not self._device_subscrs.has_key(dst_addr):
                self._device_subscrs[dst_addr] = DevSubscrData(
                    self.def_max_dev_subscrs,
                    self.debug_lvl
                    )
            dev_subscr_data = self._device_subscrs[dst_addr]
            result = dev_subscr_data.add_point_subscr(dst_addr, obj_id)
            point_data = dev_subscr_data.get_point(obj_id)
            if cov_callback: # - setup the callback hook if supplied.  assumes
                             #   only one ION ever does get_value for this
                             #   point.
                point_data._cov_callback = cov_callback
            if type(result) == types.ListType:
                for t in result:
                    self._send_CML(t[0], t[1])
                    if self.debug_lvl & 16:
                        msglog.log(
                            'mpx:rz', DB,
                            'get_value:Sent CML for (%d,%d).' % (t[0], t[1])
                            )
                result = -1
            # if point already subscribed on device:
            if (result == 0) and (force_resubscribe == 0):
                value = [point_data.value, point_data.state]
            else: # else, point needs to be subscribed on device:
                ext = form_addr_obj_id_array(dst_addr, obj_id)
                # ldisc adds src_addr and hdr chksum
                pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_AML, 0, ext)
                if self.debug_lvl & 8:
                    msglog.log('mpx:rz', DB,
                               'get_value(): Sent LAN_AML for %d,%d' %
                               (dst_addr, obj_id))
                try:
                    self._send_rznp_packet(pkt)
                except IOError, e:
                    msglog.exception()
                point_data.cond = Condition()
                # acquire INSIDE critsec, to so we don't miss notify() from
                # other thread
                point_data.cond.acquire()
        finally:
            #print "get_value: release"
            self._internal_lock.release()
            #print "get_value: released"
        if (not point_data is None) \
           and (not point_data.cond is None):
            # wait OUTSIDE critsec, to allow notify() from other thread
            point_data.cond.wait(self._read_wait_time)
            point_data.cond.release()
            #print "get_value: acquire2"
            self._internal_lock.acquire()
            #print "get_value: acquired2"
            try:
                if point_data.value is None:
                    # timeout occurred
                    value = None
                else:
                    value = [point_data.value, point_data.state]
                del point_data.cond
                point_data.cond = None
            finally:
                #print "get_value: release2"
                self._internal_lock.release()
                #print "get_value: released2"
        return value
    def _get_if_bound_proxy(self, lan_addr, obj_ref):
        bound_device = self._bound_devices.get(lan_addr)
        if bound_device:
            return bound_device.get_point(obj_ref)
        return None
    def register_bound_proxy(self, ion):
        #print "register_bound_proxy: acquire"
        self._internal_lock.acquire()
        #print "register_bound_proxy: acquired"
        try:
            dst_addr = int(ion.proxy_lan_addr)
            obj_id = int(ion.proxy_obj_ref)
            if not self._bound_devices.has_key(dst_addr):
                self._bound_devices[dst_addr] = DevBoundData(self.debug_lvl)
            dev_bound_data = self._bound_devices[dst_addr]
            result = dev_bound_data.add_point_subscr(dst_addr, obj_id)
            point_data = dev_bound_data.get_point(obj_id)
            point_data._cov_callback = ion._cov_event_callback
            if point_data.value is not None and point_data.state is not None:
                # If the point already has a value, ensure that the consumer
                # gets an initial value:
                point_data._cov_callback(point_data)
        finally:
            #print "register_bound_proxy: release"
            self._internal_lock.release()
            #print "register_bound_proxy: released"

    def unregister_bound_proxy(self, ion):
        #print "unregister_bound_proxy: acquire"
        self._internal_lock.acquire()
        #print "unregister_bound_proxy: acquired"
        try:
            dst_addr = int(ion.proxy_lan_addr)
            obj_id = int(ion.proxy_obj_ref)
            if self._bound_devices.has_key(dst_addr):
                dev_bound_data = self._bound_devices[dst_addr]
                dev_bound_data.remove(obj_id)
        finally:
            #print "unregister_bound_proxy: release"
            self._internal_lock.release()
            #print "unregister_bound_proxy: released"
    def unregister_subscribed_proxy(self, ion):
        #print "unregister_subscribed_proxy: acquire"
        self._internal_lock.acquire()
        #print "unregister_subscribed_proxy: acquired"
        try:
            dst_addr = int(ion.lan_address)
            obj_id = int(ion.id_number)
            if self._device_subscrs.has_key(dst_addr):
                dev_subscr_data = self._device_subscrs[dst_addr]
                dev_subscr_data.remove_point_subscr(obj_id)
        finally:
            #print "unregister_subscribed_proxy: release"
            self._internal_lock.release()
            #print "unregister_subscribed_proxy: released"

    def broadcast_update_request(self):
        #try for up to 30 seconds after opening port for an ACK from the update request
        self._inital_update_request = time.time()
        #thread_pool.NORMAL.queue_noresult(self.broadcast_update_request_callback)

    def broadcast_update_request_callback(self):
        #request all other boards to send latest value to mediator for bound
        # points
        update_request_pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_UPDATE, 0, None)
        if self.debug_lvl & 96:
            msglog.log('mpx:rz',DB,'Send global LAN_UPDATE')
        try:
            # send global LAN_UPDATE pkt to ldisc
            self._send_rznp_packet(update_request_pkt)
        except Exception, e:
            if time.time() > (self._inital_update_request + 60):
                msglog.log('mpx:rz', INFO, 'UPDATE requests have expired')
                if self.debug_lvl & 96: msglog.exception()
                return
            scheduler.after(5, self.broadcast_update_request_callback) #wait 5 seconds and try again until one minute has past

    def _set_override(self, dst_addr, obj_id, value, pkt_type, pkt=None):
        if pkt is None: #pkt may be supplied direct from phwin, otherwise....
            # Value MUST be floating point:
            value = float(value)

            # Convert value from Intel to HiTech floating point:
            ht_buf = float_to_HiTech(value)

            # Form extension for override pkt:
            b_obj_id = form_short(obj_id)
            ext = array.array('B', [b_obj_id[0], b_obj_id[1], ht_buf[0],
                                    ht_buf[1], ht_buf[2], ht_buf[3], 0, 0])

            # Form override pkt:
            pkt = form_host_pkt(dst_addr, pkt_type, 0, ext)

        # Send override pkt:
        try:
            if self._application_running:
                self._send_rznp_packet(pkt)
        except IOError, e:
            msglog.exception()
        # No need to make sure that point is subscribed. If it is not, then
        # caller has not cared enough to want to know the value yet...
        return
    def set_override(self, dst_addr, obj_id, value):
        self._set_override(dst_addr, obj_id, value, LAN_OBJ_OVRD) #for non-bound points
    def _set_value(self, dst_addr, obj_id, value): #for bound point sets
        #use a cache of outgoing values and only send the most recent value.
        #if the throughput lags behind the changes, skip older values.
        #cache is a dictionary keyed by (dst_addr, obj_id) with a value of, well, value.
        #to insure determinism in getting values out, add the key to a seperate FIFO list and pop keys from there
        #to use in pulling values from the cache.
        if self._application_running:
            obj = (dst_addr, obj_id)
            self._set_value_cache[obj] = value
            self._set_value_fifo.append(obj)
            self._set_value_semaphore.release() #trigger the sending of the value
    def _set_value_run(self): #runs on a separate thread.
        self._set_value_semaphore.acquire() #wait for values to transmit
        while len(self._set_value_fifo): #empty list of queued up outgoing values keys
            if not self._application_running:
                self._set_value_fifo = []
                self._set_value_cache.clear()
                return
            obj = self._set_value_fifo.pop(0) #obj = (dst_addr, obj_id)
            #I hope this next line is atomic
            val,self._set_value_cache[obj] = self._set_value_cache.get(obj), None #return value or None.  Once we switch to 2.5, this can be improved
            if val is not None:
                self._set_override(obj[0], obj[1], val, LAN_OBJ_VAL) #for bound points
    def set_value(self, dst_addr, obj_id, value):
        self._set_value(dst_addr, obj_id, value)
        dev_subscr_data = self._bound_devices.get(dst_addr)
        if dev_subscr_data:
            point_data = dev_subscr_data.get_point(obj_id)
            if point_data is None:
                if self.debug_lvl & 64:
                    msglog.log('mpx:rz',DB,
                               'set_value:Point is None for (%d,%d).'
                               % (dst_addr, obj_id))
                return
            point_data.value = value
            point_data.state = 0

    def clr_override(self, dst_addr, obj_id, pkt=None):
        if pkt is None:
        # Form LAN_CLOV (non-extended) pkt:
            pkt = form_host_pkt(dst_addr, LAN_OBJ_CLOV, obj_id)

        # Send LAN_CLOV pkt:
        try:
            self._send_rznp_packet(pkt)
        except IOError, e:
            msglog.exception()

        # No need to make sure that point is subscribed. If it is not, then
        # caller has not cared enough to want to know the value yet...
        return
    def _send_global_CML(self):
        unsub_pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_CML, 0, None)
        try:
            # send global LAN_CML pkt to ldisc
            self.debug_print_host_packet(unsub_pkt)
            self._port_rznp.write(unsub_pkt.tostring())
            self._port_rznp.flush()
        except IOError, e:
            msglog.exception()
            return
        else:
            if self.debug_lvl & 16:
                msglog.log('mpx:rz', DB, 'Sent global LAN_CML')
    def _send_CMLs(self, pnt_lst):
        cml_exts_list = [] # - saves extensions ready to go
        cml_exts_dict = {} # - saves extensions-in-progress
        cml_ext = array.array('B') # - prep an array to hold LAN_CML extension
                                   #   for up to 14 expired points per target
                                   #   node
        for dst_addr,obj_id in pnt_lst:
            if not self._device_subscrs.has_key(dst_addr):
                if self.debug_lvl & 16:
                    msglog.log('mpx:rz',DB,
                               '_send_CMLs: Got req to clear'
                               ' subscr in unknown device %d. Skipping...'
                               % dst_addr)
                continue
            dev_subscr_data = self._device_subscrs[dst_addr]
            point_data = dev_subscr_data.get_point(obj_id)
            if point_data is None:
                if self.debug_lvl & 16:
                    msglog.log('mpx:rz',DB,
                               '_send_CMLs: Got req to clear subscr for '
                               'unsubscribed point (%d,%d). Skipping...'
                               % (dst_addr,obj_id))
                continue
            # If the there are consumers of this value (PhWin is subscribed, a
            # node is registered, ...), then do not send a CML for this point:
            if point_data.is_in_use():
                continue
            # If we've already seen this point's node addr, extend existing
            # array:
            if cml_exts_dict.has_key(dst_addr):
                nNumBytes = len(cml_exts_dict[dst_addr])
                # If existing array has max allowed point refs, then remove
                # array from dict, and start new array:
                if nNumBytes >= (6 * 14):
                    del cml_exts_dict[dst_addr]
                    a = form_addr_obj_id_array(dst_addr, obj_id)
                    cml_exts_dict[dst_addr] = a
                    cml_exts_list.append((dst_addr, a))
                    if self.debug_lvl & 16:
                        msglog.log('mpx:rz',DB,
                                   '_send_CMLs: Added (%d,%d) to new pkt array'
                                   % (dst_addr, obj_id))
                else: # else, enough room in existing array:
                    cml_exts_dict[dst_addr].extend(
                        form_addr_obj_id_array(dst_addr, obj_id)
                        )
                    if self.debug_lvl & 16:
                        msglog.log('mpx:rz',DB,
                                   '_send_CMLs: Added (%d,%d) to extant pkt'
                                   ' array' % (dst_addr, obj_id))
            else: # else, add a new array to dict and to list:
                a = form_addr_obj_id_array(dst_addr, obj_id)
                cml_exts_dict[dst_addr] = a
                cml_exts_list.append((dst_addr, a))
                if self.debug_lvl & 16:
                    msglog.log('mpx:rz',DB,
                               '_send_CMLs: Added (%d,%d) to new pkt array'
                               ', newdevice dict' % (dst_addr, obj_id))
            dev_subscr_data.remove_point_subscr(obj_id)
        # Clear the dict:
        cml_exts_dict.clear()
        # Form and send a LAN_CML pkt for each extension formed above:
        while len(cml_exts_list) > 0:
            t = cml_exts_list.pop(0)
            dst_addr = t[0]
            ext = t[1]
            # ldisc adds src_addr and hdr/ext chksums
            pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_CML, 0, ext)
            try:
                self._send_rznp_packet(pkt)
                if self.debug_lvl & 16:
                    msglog.log('mpx:rz',DB,
                               '_send_CMLs: Sent CML pkt to RZNet, to %d'
                               % dst_addr)
                time.sleep(2.0) # - because it works; else, maybe too fast and
                                #   target RZ Controller can get confused
            except IOError, e:
                msglog.exception()
        return
    def clear_subscr(self, targets=None):
        # prevent other updates while we clear one or more subscrs
        #print "clear_subscr: acquire"
        self._internal_lock.acquire()
        #print "clear_subscr: acquired"
        try:
            if (type(targets) == types.ListType):
                if not (type(targets[0]) == types.TupleType):
                    raise EInvalidValue(
                        'targets',targets,'Should be None, int, '
                        'or list of 2-tuples (dev_id, obj_id).'
                        )
                self._send_CMLs(targets)
            else:
                dst_addr = None
                if targets is None: #clear ALL subscriptions
                    dst_addr = MODEM_SERVER_DEF_ADDR
                    # Clear all local subscr lists:
                    for dev_subscr_data in self._device_subscrs.values():
                        dev_subscr_data.clear_subscrs()
                elif isinstance(targets, int): #clear all subscriptions in one device
                    dst_addr = targets
                    if not self._device_subscrs.has_key(dst_addr):
                        msglog.log('mpx:rz',WARN,
                                   'clear_subscr:Thin client'
                                   ' reqd unsubscr on unknown device %d' %
                                   dst_addr)
                        return
                    dev_subscr_data = self._device_subscrs[dst_addr]
                    # Clear local subscr list for target device:
                    dev_subscr_data.clear_subscrs()
                else:
                    raise EInvalidValue(
                        'targets',targets,'Should be None, int, '
                        'or list of 2-tuples (dev_id, obj_id).'
                        )
                unsub_pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_CML, 0, None)
                try:
                    # send global LAN_CML pkt to ldisc
                    self._send_rznp_packet(unsub_pkt, 0) #don't repeat or wait for response
                except IOError, e:
                    msglog.exception()
                    return
                else:
                    if self.debug_lvl & 16:
                        msglog.log(
                            'mpx:rz',DB, 'clear_subscr: '
                            'Sent global LAN_CML to %d, reqd by thin client.'
                            % dst_addr
                            )
        finally:
            #print "clear_subscr: release"
            self._internal_lock.release()
            #print "clear_subscr: released"
        return

    def _proc_timeout(self):
        pass
    def _rsp_SYN(self, byte):
        #self.debug_print(16384, '_rsp_SYN: _current_response_index = %d', self._current_response_index)
        if byte == SYN:
            pktd = self._responses[self._current_response_index]
            pktd.buf[pktd.idx] = SYN
            pktd.idx = pktd.idx + 1
            pktd.len = 6 #response header lenght # - reset this, in case rpev pkt was
                                    #   extended!
            self._response_form_state = ST_SOH
        return 0

    def _rsp_SOH(self, byte):
        #self.debug_print(16384, '_rsp_SOH: _current_response_index = %d', self._current_response_index)
        pktd = self._responses[self._current_response_index]
        if byte == SOH:
            pktd.buf[pktd.idx] = SOH
            pktd.idx = pktd.idx + 1
            self._response_form_state = ST_HDR
        else:
            pktd.idx = 0
            self._response_form_state = ST_SYN
            self._rsp_SYN(byte) #just in case two 16's came through
        return 0

    def _rsp_HDR(self, byte):
        #self.debug_print(16384, '_rsp_HDR: _current_response_index = %d', self._current_response_index)
        rtn = 0
        pktd = self._responses[self._current_response_index]
        pktd.buf[pktd.idx] = byte
        pktd.idx = pktd.idx + 1
        if pktd.idx >= 6:
            calc = rznet_chksum(pktd.buf[2 : 5])
            if calc != pktd.buf[5]:
                # self.debug_print(
                    # 0,
                    # 'Bad chksum in header of response from modeem server: '
                    # 'Calc = %02x, Read = %02x',
                    # calc, pktd.buf[5]
                    # )
                pktd.idx = 0 # make sure we're at start of pkt buf
                self._response_form_state = ST_SYN
            elif pktd.buf[4] == 0: #check count for extended type
                # pkt is NOT extended, we're done:
                pktd.idx = 0 # prep for next incoming pkt
                self._last_response_index = self._current_response_index
                self._current_response_index = self._current_response_index + 1
                if self._current_response_index >= self._num_pkts:
                    self._current_response_index = 0
                self._response_form_state = ST_SYN
                rtn = 1
            else:
                # pkt must be extended:
                # max of 255 bytes total
                pktd.len = 6 + pktd.buf[4]
                self._response_form_state = ST_EXT
        return rtn

    def _rsp_EXT(self, byte):
        self.debug_print(16384, '_rsp_EXT: _current_response_index = %d', self._current_response_index)
        rtn = 0
        pktd = self._responses[self._current_response_index]
        pktd.buf[pktd.idx] = byte
        pktd.idx = pktd.idx + 1
        if pktd.idx >= pktd.len: #just read in chksum byte
            check_start = RZHS_CHKSUM + 1
            #check for PASS THROUGH of a Net Peer packet and check the checksum
            type = pktd.buf[RZHS_TYPE]
            seq = pktd.buf[RZHS_SEQ]
            if (type) in (LAN_OBJ_VAL | 0x40, LAN_UPDATE): #pass through packet from net peer. note lan_obj_val without the extended flag bypasses this
                #sum = 0x27 + seq + type #compute pre-load for checksum assuming mediator address of 100,000
                calc = rznet_chksum(pktd.buf[check_start : RZHS_2ND_CHKSUM], 0x27) #sum
                if calc != pktd.buf[RZHS_2ND_CHKSUM]:
                    self.debug_print(
                        65535,
                        'Bad chksum in 2nd hdr of pass through from modemserverc: '
                        'Calc = %02x, Read = %02x',
                        calc, pktd.buf[RZHS_2ND_CHKSUM]
                        )
                    pktd.idx = 0 # make sure we're at start of pkt buf
                    self._response_form_state = ST_SYN
                    return 0
                check_start = RZHS_2ND_CHKSUM + 1
            ext_chksum_idx = pktd.len - 1  #?? seems like this is one short
            calc = rznet_chksum(pktd.buf[check_start : ext_chksum_idx])
            if calc != pktd.buf[ext_chksum_idx]:
                self.debug_print(
                    65535,
                    'Bad chksum in ext of response from modemserverc: '
                    'Calc = %02x, Read = %02x',
                    calc, pktd.buf[ext_chksum_idx]
                    )
                pktd.idx = 0 # make sure we're at start of pkt buf
                self._response_form_state = ST_SYN
            else: # pkt is complete:
                pktd.idx = 0 # prep for next incoming pkt
                self._last_response_index = self._current_response_index
                self._current_response_index = self._current_response_index + 1
                if self._current_response_index >= self._num_pkts:
                    self._current_response_index = 0
                self._response_form_state = ST_SYN
                rtn = 1
        return rtn
    # process a response packet coming from the modem server
    def _proc_evt_rznp(self, evt):
        self.debug_print(512, 'Processing RZNet Event:')
        if (evt & select.POLLIN) != 0:
            passthrough = array.array('B')
            while 1: # read every byte available from port:
                #read response packet into buffer 'bytes' - this may or may not be a complete packet
                bytes = array.array('B')
                bytes.fromstring(self._port_rznp.drain())
                if len(bytes) < 1: # if dskt is jabbering:
                    self.debug_print(2048, 'Emptied bytes from modem server:')
                    break;

                # else, we've got data to process:
                if self.debug_lvl & 2048:
                    self.debug_print(2048, 'Processing response bytes from modem server:')
                    print_array_as_hex(bytes)
                # Validate recvd pkt before proceeding...
                ext = None
                for byte in bytes:
                    pkt_rdy = self._response_form_states[self._response_form_state](byte)
                    if pkt_rdy == 0: # pkt is NOT ready
                        if self._data_skt_rzhs is not None:
                            passthrough.append(byte) #this may just go out if no packet is seen
                        continue
                    if self._data_skt_rzhs is not None:
                        passthrough = array.array('B') #valid packet recvd.  nothing to pass through
                    #now process completed packet
                    pktd = self._responses[self._last_response_index]
                    print_array_as_hex(pktd.buf[:pktd.len])
                    # we're processing that pkt now, so show it's done
                    self._last_response_index = -1
                    try:
                        pkt_type = pktd.buf[2] & 0x3F
                        self.debug_print(4096, 'rsp pkt_type = %02x [%s]', pkt_type, str(PacketTypeEnum.get(pkt_type, 'unknown')))
                        proc = self._rznp_procs[pkt_type]
                    except:
                        #packet type not found - just pass bytes along to host
                        if self._data_skt_rzhs is not None:
                            if (self.debug_lvl & 4):
                                print 'passthrough packet:'
                                print_array_as_hex(pktd.buf[:pktd.len])
                            self._dskt_sendall(pktd.tostring())
                            if self.debug_lvl & 4:
                                print 'passthrough packet: sent'
                            continue
                        if (self.debug_lvl & 0x8000) > 0:
                            print 'unrecognized packet:'
                            print_array_as_hex(pktd.buf)
                    else:
                        proc(pktd.buf.tostring())
                #out of bytes - check for pass through for boot rom responses
                if self._data_skt_rzhs is not None:
                    if self._response_form_state == ST_SYN: #not in the middle of a packet
                        if len(passthrough) > 0:
                            #we are not processing a packet, pass raw bytes to phwin, might be in boot rom
                            if self.debug_lvl & 4096:
                                print 'passthrough raw bytes:'
                                print_array_as_hex(passthrough)
                            self._dskt_sendall(passthrough.tostring()) #send raw bytes to phwin
                            passthrough = array.array('B')
            
            if self._data_skt_rzhs is not None:
                if self._response_form_state == ST_SOH: #last byte received was a SYNC
                    if len(passthrough) > 1: #more than just a SYNC byte waiting - likely needs to passthrough
                        #we are not processing a packet, pass raw bytes to phwin, might be in boot rom
                        if self.debug_lvl & 4096:
                            print 'passthrough raw bytes at close:'
                            print_array_as_hex(passthrough)
                        self._dskt_sendall(passthrough.tostring()) #send raw bytes to phwin
            
                        

        elif (evt & select.POLLERR) != 0:
            raise ERestart()
        return None
    def _send_rznp_packet(self, pkt, wait=1):
        self._port_rznp_lock.acquire()
        self._port_rznp_condition.acquire()
        try:
            if hasattr(self._port_rznp, 'is_connected'):
                if not self._port_rznp.is_connected():
                    self.debug_print(65535, 'Tunnel not connected')
                    raise ETimeout()
            for i in range(3):
                if not self._application_running: #when not running, only allow packets related to loading os and app
                    try:
                        if (pkt[RZHM_TYPE] & 0x3F) in (LAN_OBJ_VAL, LAN_OBJ_CLOV, LAN_OBJ_OVRD, LAN_REPORT, LAN_AML, LAN_CML, LAN_TIME):
                            continue #loop three times and throw an ETimeout
                    except:
                        pass #if we can't access RZHM_TYPE, just let it go
                self.debug_print_host_packet(pkt)
                self._port_rznp.write(pkt.tostring())
                self._port_rznp.flush()
                if wait == 0: 
                    return #just send it and forget about it
                self._port_rznp_state = 0
                self._port_rznp_condition.wait(self._port_rznp_timeout)
                if self._port_rznp_state: #response was seen, bug out
                    return
            #print '### timeout ###'
            raise ETimeout()                
        finally:
            self._port_rznp_condition.release()
            self._port_rznp_lock.release()
    def _ack_rznp_packet(self):
        self._port_rznp_condition.acquire()
        #print 'notify all'
        self._port_rznp_condition.notifyAll()
        self._port_rznp_state = 1
        self._port_rznp_condition.release()

    # Leave listen_skt open perennially, to allow disconnect/reconnect cycles
    # when other end of data_skt goes away unceremoniously:
    def _proc_evt_lrzhs(self, evt):  #PhWin connection request event
        if (evt & select.POLLIN) != 0:
            addr = None
            dskt = None
            try:
                dskt, addr = self._listen_skt_rzhs.accept() #accept the connection from phwin
            except socket.error, details:
                # remote client socket disappeared after calling connect()
                msglog.log(
                    'broadway',ERR,'listen_skt could not accept connection '
                    'from remote client socket: %s.' % str(details)
                    )
            else:
                if not self._data_skt_rzhs is None:
                    # ALWAYS stop existing dskt and use new data socket
                    old_host, old_port = self._data_skt_rzhs.getpeername()
                    self._data_skt_rzhs.close() # close previous
                    self._remove_dskt()     # ..
                    msglog.log('broadway', WARN,
                               'Old data socket (%s:%s) closed; '
                               'new data socket (%s:%s) opened.'
                               % (old_host, old_port, addr[0], addr[1]))
                self._data_skt_rzhs = dskt
                self._data_skt_rzhs.setblocking(0)
                self._data_skt_rzhs.setsockopt(socket.IPPROTO_TCP,
                                           socket.TCP_NODELAY, 1)
                # prevent skt from jabbering with empty pkts after closure
                linger = struct.pack("ii", 1, 0)
                self._data_skt_rzhs.setsockopt(socket.SOL_SOCKET,
                                           socket.SO_LINGER, linger)
                # Register to get events from dskt:
                self._fd_data_skt_rzhs = self._data_skt_rzhs.fileno()
                self._poll_obj.register(self._fd_data_skt_rzhs, select.POLLIN)
                self._fds[self._fd_data_skt_rzhs] = self._proc_evt_drzhs  #proceedure to handle messages
                self.debug_print(1024, 'PhWin Data socket created')

                # While dskt exists, stop further poll service to lskt:
                # @FIXME: rmv this line when perennial lskt works
                # self._poll_obj.unregister(self._fd_listen_skt_rzhs)
                # @FIXME: rmv this line when perennial lskt works
                # del self._fds[self._fd_listen_skt_rzhs]
                # @FIXME: rmv this line when perennial lskt works
        elif (evt & select.POLLERR) != 0:
            raise ERestart()
        return None

    def _remove_dskt(self):
        # dskt no longer exists, so unregister it, remove it from fds map, and
        # delete it. Re-reg lskt:
        try: self._poll_obj.unregister(self._fd_data_skt_rzhs)
        except: msglog.exception()
        try: del self._fds[self._fd_data_skt_rzhs]
        except: msglog.exception()
        self._fd_data_skt_rzhs = -1
        self._data_skt_rzhs = None
        self.debug_print(1024, 'PhWin Data socket closed')
        # @FIXME: rmv this line when perennial lskt works
        # self._poll_obj.register(self._fd_listen_skt_rzhs, select.POLLIN)
        # self._fds[self._fd_listen_skt_rzhs] = self._proc_evt_lrzhs

    def _do_SYN(self, byte):
        self.debug_print(16384, '_do_SYN: _cur_pkt_idx = %d', self._cur_pkt_idx)
        if byte == SYN:
            pktd = self._pkts[self._cur_pkt_idx]
            pktd.buf[pktd.idx] = SYN
            pktd.idx = pktd.idx + 1
            pktd.len = RZHM_HDR_LEN # - reset this, in case rpev pkt was
                                    #   extended!
            self._pkt_form_state = ST_SOH
        return 0

    def _do_SOH(self, byte):
        self.debug_print(16384, '_do_SOH: _cur_pkt_idx = %d', self._cur_pkt_idx)
        pktd = self._pkts[self._cur_pkt_idx]
        if byte == SOH:
            pktd.buf[pktd.idx] = SOH
            pktd.idx = pktd.idx + 1
            self._pkt_form_state = ST_HDR
        else:
            pktd.idx = 0
            self._pkt_form_state = ST_SYN
        return 0

    def _do_HDR(self, byte):
        self.debug_print(16384, '_do_HDR: _cur_pkt_idx = %d', self._cur_pkt_idx)
        rtn = 0
        pktd = self._pkts[self._cur_pkt_idx]
        pktd.buf[pktd.idx] = byte
        pktd.idx = pktd.idx + 1
        if pktd.idx >= RZHM_HDR_LEN:
            calc = rznet_chksum(pktd.buf[RZHM_DST_1ST : RZHM_CHKSUM])
            if calc != pktd.buf[RZHM_CHKSUM]:
                self.debug_print(
                    0,
                    'Bad chksum in hdr of pkt from client (PhWin): '
                    'Calc = %02x, Read = %02x',
                    calc, pktd.buf[RZHM_CHKSUM]
                    )
                pktd.idx = 0 # make sure we're at start of pkt buf
                self._pkt_form_state = ST_SYN
            elif (pktd.buf[RZHM_TYPE] & LAN_EXTEND) == 0:
                # pkt is NOT extended, we're done:
                pktd.idx = 0 # prep for next incoming pkt
                self._last_pkt_idx = self._cur_pkt_idx
                self._cur_pkt_idx = self._cur_pkt_idx + 1
                if self._cur_pkt_idx >= self._num_pkts:
                    self._cur_pkt_idx = 0
                self._pkt_form_state = ST_SYN
                rtn = 1
            else:
                # pkt must be extended:
                # max of 255 bytes total
                pktd.len = RZHM_HDR_LEN + pktd.buf[RZHM_DATA_1ST]
                self._pkt_form_state = ST_EXT
        return rtn

    def _do_EXT(self, byte):
        self.debug_print(16384, '_do_EXT: _cur_pkt_idx = %d', self._cur_pkt_idx)
        rtn = 0
        pktd = self._pkts[self._cur_pkt_idx]
        pktd.buf[pktd.idx] = byte
        pktd.idx = pktd.idx + 1
        if pktd.idx >= pktd.len:
            ext_chksum_idx = pktd.len - 1
            calc = rznet_chksum(pktd.buf[(RZHM_CHKSUM + 1) : ext_chksum_idx])
            if calc != pktd.buf[ext_chksum_idx]:
                self.debug_print(
                    0,
                    'Bad chksum in hdr of pkt from client (PhWin): '
                    'Calc = %02x, Read = %02x',
                    calc, pktd.buf[ext_chksum_idx]
                    )
                pktd.idx = 0 # make sure we're at start of pkt buf
                self._pkt_form_state = ST_SYN
            else: # pkt is complete:
                pktd.idx = 0 # prep for next incoming pkt
                self._last_pkt_idx = self._cur_pkt_idx
                self._cur_pkt_idx = self._cur_pkt_idx + 1
                if self._cur_pkt_idx >= self._num_pkts:
                    self._cur_pkt_idx = 0
                self._pkt_form_state = ST_SYN
                rtn = 1
        return rtn

    #Message received from PhWin - examine message and either pass through or handle locally
    def _proc_evt_drzhs(self, evt):
        # Test remote data_skt for closure:
        try:
            host_name, port_num = self._data_skt_rzhs.getpeername()
        except: # remote socket is closed:
            self.debug_print(
                1024+2048,
                'data-skt %d appears to be dead on the other end.',
                self._fd_data_skt_rzhs
                )
            # dskt no longer exists, so unregister it, remove it from fds map,
            # and delete it. Re-reg lskt:
            self._remove_dskt()
            return None

        if (evt & select.POLLIN) != 0:
            #read phwin packet into buffer 'bytes' - this may or may not be a complete packet
            bytes = array.array('B')
            bytes.fromstring(self._data_skt_rzhs.recv(self._data_skt_rzhs_rd_buf_len,
                                                  10))
            if len(bytes) < 1: # if dskt is jabbering:
                self._data_skt_rzhs.close()
                self._remove_dskt()
                return None

            # else, we've got data to process:
            self.debug_print(16384, 'Processing RZHost bytes from dskt:')
            if self.debug_lvl & 16384:
                print_array_as_hex(bytes)

            # Validate recvd pkt before proceeding...
            ext = None
            for byte in bytes:
                pkt_rdy = self._pkt_form_states[self._pkt_form_state](byte)
                if pkt_rdy == 0: # pkt is NOT ready
                    continue
                #now process completed packet
                pktd = self._pkts[self._last_pkt_idx]
                # we're processing that pkt now, so show it's done
                self._last_pkt_idx = -1

                if pktd.len > RZHM_HDR_LEN: # it's ext, so get ext:
                    # let form_host_pkt() add/recalc ext chksum
                    ext = pktd.buf[RZHM_HDR_LEN : (pktd.len - 1)]
                else:
                    # make sure to clear this before we try to use it!
                    ext = None
                # If pkt is not sent to us, reformat pkt for RZNet and
                # pass it on:
                a_dst_addr = pktd.buf[RZHM_DST_1ST : RZHM_DST_LAST + 1]
                # Strip off possible seq num:
                dst_addr = struct.unpack('<I', a_dst_addr)[0]
                #self.debug_print(2, 'phwin rcvd dst_addr = %x.', dst_addr)

                proc = None
                pkt_type = pktd.buf[RZHM_TYPE] & 0x3F
                try:
                    # lookup fn based on pkt type
                    proc = self._rzhs_procs[pkt_type]
                except:
                    self.debug_print(
                        1024,
                        'proc for RZHostMaster pkt type %d, [%s] not found.',
                        pkt_type, str(PacketTypeEnum.get(pkt_type, 'unknown')) 
                        )
                    # we don't have a special handler so
                    # forward pkt AS IS to the modem server:
                    self.debug_print_host_packet_buffer(pktd.buf)
                    self._port_rznp.write(pktd.tostring())
                    self._port_rznp.flush()

                else:
                    thread_pool.NORMAL.queue_noresult(proc,pktd.buf)
        elif (evt & select.POLLERR) != 0:
            raise ERestart()
        return None

    def _proc_evt_cmd(self, evt):
        result = None
        if (evt & select.POLLIN) != 0:
            cmd = self._near_cmd_skt.recv(self._near_cmd_skt_rd_buf_len)
            self.debug_print(1, 'recvd cmd %s', cmd)
            if cmd == 'stop':
                self.set_immortal(0)
                raise EKillThread('stop')
            elif cmd == 'restart':
                raise ERestart()
            elif cmd == 'subscr_scan':
                self._subscr_scan() # scan for expired subscriptions
                # Schedule next scan:
                self._sched_entry_subscr_scan = scheduler.after(
                    self._time_subscr_scan, self.timeout_callback,
                    (self._timer_ID_subscr_scan,)
                    )
            # Add more cmds with elif's. If cmd processing gets large, use a
            # dict-based implementation of a "switch" statement...
        elif (evt & select.POLLERR) != 0:
            raise EPollErr()
        return result

    def _dskt_sendall(self, data, timeout=10):
        if self._data_skt_rzhs is None:
            return
        try:
            self._data_skt_rzhs.sendall(data, timeout)
        except ETimeout:
            msglog.log(
                'broadway',ERR,
                'Timed out trying to send pkt to PhWin: "%s". '
                'Closing port to PhWin.' % data
                )
            # @FIXME: rmv this line when perennial lskt works
            # self._remove_dskt()
        except:
            msglog.exception()
            self._remove_dskt()

    def _proc_rznp_REPORT(self, pkt): #MNTR values are in from the modem server
        global REPORT_LIST_NAME
        self._ack_rznp_packet()
        # Process given pkt:
        # obtain the extension length (unpack yields a one-elem tuple)
        ext_len = ord(pkt[RZHS_LEN])
        # each value is given in 11 bytes; make sure num bytes is reasonable
        assert ((ext_len - 2) % 11) == 0, (
            'Bad number of bytes in value pkt: %d not evenly divisible by '
            '11' % ext_len
            )
        num_vals = (ext_len - 2) / 11
        #also check header count against byte count in first byte of payload
        point_data_cov_list = []
        if num_vals > 0:
            assert (ext_len == ord(pkt[6])), (
                'Mismatch between header length: %d and '
                'monitor report packet length: %d' % (ext_len, ord(pkt[6])))
            if self.debug_lvl & 8:
                print_array_as_hex(array.array('B',pkt[:ext_len+RZHS_HDR_LEN]))
            for i in range(num_vals):
                # calculate index of first byte of object in payload
                base_idx = i * 11 + 7 #7 is header length plus 1 for count byte at beginning of payload
                # unpack yields a one-elem tuple, extract element via [0]
                src_addr = struct.unpack('<I', pkt[base_idx:base_idx + 4])[0]
                obj_id = struct.unpack('<H',pkt[base_idx+4:base_idx+6])[0] #(ord(pkt[base_idx + 5]) << 8) + ord(pkt[base_idx + 4])
                # If we have an entry, convert bytes to float value, and set
                # point value and state from recvd data:
                dev_subscr_data = self._device_subscrs.get(src_addr)
                if dev_subscr_data:
                    point_data = dev_subscr_data.get_point(obj_id)
                    if point_data is None:
                        self._queue_CML(src_addr, obj_id)
                        if self.debug_lvl & 16:
                            msglog.log(
                                'mpx:rz',DB,
                                '_proc_rznp_REPORT:Point is None; Sent CML for'
                                ' (%d,%d).' % (src_addr, obj_id)
                            )
                        continue
                    point_data.value = HiTech_to_float(pkt[base_idx+6:base_idx+10])
                    point_data.state = ord(pkt[base_idx + 10])
                    # FGD eventually may produce an event through a callback
                    # to the rz ion
                    point_data_cov_list.append(point_data)
                    if self.debug_lvl & 8:
                        msglog.log('mpx:rz',DB,
                                   '_proc_rznp_REPORT:Recvd value "%s" '
                                   'and state "%s" for (%d,%d).'
                                   % (point_data.value,
                                      point_data.state, src_addr, obj_id))
                        pass
                # Else, we did not request the value, so unsubscribe the point:
                else:
                    self._queue_CML(src_addr, obj_id)
                    if self.debug_lvl & 16:
                        msglog.log('mpx:rz',DB,
                                   '_proc_rznp_REPORT:Sent CML for (%d,%d).'
                                   % (src_addr, obj_id))
        del pkt
        thread_pool.NORMAL.queue_noresult(self._distribute_subscr_covs,point_data_cov_list)
        return
    def _distribute_subscr_covs(self, point_data_cov_list):
        for point_data in point_data_cov_list:
            point_data._check_cov()
            if point_data.phwin != 0:
                # RZ controllers send LAN_MTR_VAL only on COV
                point_data.phwin_COV = 1
                # If point is not yet in REPORT list, then add it:
                self._internal_lock.acquire()
                try:
                    if not point_data.is_in_list(REPORT_LIST_NAME):
                        # add point to end of list
                        self._REPORT_pts.ml_insert_elem_as_prev(
                            point_data,REPORT_LIST_NAME
                            )
                        if self.debug_lvl & 8:
                            msglog.log(
                                'mpx:rz',DB,
                                '_proc_rznp_REPORT:Put value "%s" for '
                                '(%d,%d) into REPORT Q.'
                                % (point_data.value, point_data.dst_addr, point_data.obj_id)
                                )
                finally:
                    self._internal_lock.release()
            if not point_data.cond is None: # if necy, notify waiters:
                point_data.cond.acquire(self._read_wait_time)
                try:
                    point_data.cond.notify()
                finally:
                    point_data.cond.release()
        #retrigger update request - this forms a natural throttle since we will not request a new update until done with the previous one
        self._internal_lock.acquire()
        try:
            self._mntr_request = 0
            self._request_mntr_update(len(point_data_cov_list))
        finally:
            self._internal_lock.release()
    def _proc_rznp_rd_bound_val(self, pkt): #OBJ_VAL packet in from modem server to mediator
        #16 01 49 00 10 fc   b9 23 00 00   49   08 00   01   03 00   00 00 80 41   03   8e 
        #this response packet includes 8 bytes in the front of the payload that are from the original rznp packet
        if ord(pkt[2]) == 9:
            self._ack_rznp_packet()
            return #don't process ACKs of mpx_set sends
        if not self._application_running:
            return #ignore incoming value packets when app is not running
        if self.debug_lvl & 32:
            print_array_as_hex(array.array('B',pkt[:ord(pkt[4])]))
        # Process given pkt. Do NOT force endianness on src_addr or ext_len,
        # since rznet ldisc already did this (in order to use those values
        # for ldisc internal use):
        src_addr = struct.unpack('<I', pkt[RZNP_SRC_1ST : RZNP_SRC_LAST + 1])[0] #original packet's source address
        # obtain the extension length (unpack yields a one-elem tuple)
        ext_len = struct.unpack('<H', pkt[RZNP_DATA_1ST : RZNP_DATA_LAST + 1])[0] #original packet's length field
        # each value is given in 7 bytes; make sure num bytes is reasonable
        # assert ((ext_len - 1) % 7) == 0, (
            # 'Bad number of bytes in value pkt: '
            # '%d not evenly divisible by 7'
            # % ext_len
            # )
        num_vals = (ext_len - 1) / 7 #trim off chksum and leading 8 bytes from 2nd header
        #@todo check  type code
        #point_data_cov_list = []
        for i in range(num_vals):
             # first data byte is right after middle chksum
            base_idx = i * 7 + 14
            obj_id = struct.unpack('<H',pkt[base_idx:base_idx+2])[0]#(ord(pkt[base_idx + 1]) << 8) + ord(pkt[base_idx])
            # If we have an entry, convert bytes to float value, and set
            # point value and state from recvd data:
            dev_subscr_data = self._bound_devices.get(src_addr)
            if dev_subscr_data:
                point_data = dev_subscr_data.get_point(obj_id)
                if point_data is None:
                    if self.debug_lvl & 32:
                        msglog.log(
                            'mpx:rz',DB,
                            '_proc_rznp_rd_bound_val:Point is None for '
                            '(%d,%d).' % (src_addr, obj_id))
                    continue
                point_data.value = HiTech_to_float(pkt[base_idx+2:base_idx+6])#((ord(pkt[base_idx+2]),
                                                    #ord(pkt[base_idx+3]),
                                                    #ord(pkt[base_idx+4]),
                                                    #ord(pkt[base_idx+5])))
                point_data.state = ord(pkt[base_idx + 6])
                # FGD eventually may produce an event through a callback
                # to the rz ion
                self._rcvd_value_cache[(src_addr,obj_id)] = point_data
                self._rcvd_value_fifo.append((src_addr,obj_id))
                #point_data_cov_list.append(point_data)
                # if self.debug_lvl & 32:
                    # msglog.log('mpx:rz',DB,
                               # '_proc_rznp_OBJ_VAL:Recvd value '
                               # '"%s" and state "%s" for (%d,%d).'
                               # % (point_data.value, point_data.state,
                                  # src_addr, obj_id))
                    # pass
            # Else, we do not have a registration for this point:
            else:
                msglog.log('mpx:rz',INFO,
                           '_proc_rznp_rd_bound_val: device not found (%d,%d).'
                           % (src_addr, obj_id))
        #thread_pool.NORMAL.queue_noresult(self._distribute_covs, point_data_cov_list)
        self._rcvd_value_semaphore.release()
        #t = Thread(target=self._distribute_covs, args=(point_data_cov_list,), name='dist_cov')
        #t.start()
        return
    #collect updates and distribute them on a single thread instead of creating a new thread each time - this is really going on a point by point basis since OS does not aggragate this type of packet
    def _rcvd_value_run(self): #distribute both bound and subscribed covs
        self._rcvd_value_semaphore.acquire()
        while len(self._rcvd_value_fifo):
            obj = self._rcvd_value_fifo.pop(0) #obj = (dst_addr, obj_id)
            #I hope this next line is atomic
            point_data,self._rcvd_value_cache[obj] = self._rcvd_value_cache.get(obj), None #return value or None.  Once we switch to 2.5, this can be improved
            if point_data:
                if self.debug_lvl & 32:
                    msglog.log('mpx:rz',DB,
                               '_proc_rznp_OBJ_VAL:Recvd value '
                               '"%s" and state "%s" for (%d,%d).'
                               % (point_data.value, point_data.state,
                                  obj[0], obj[1]))
                point_data._check_cov()
    # request a subscribed point update from the modem server
    def _request_mntr_update(self, num_vals=0):  #call only with _internal_lock acquired
        #check to see if any points are subscribed
        assert self._internal_lock.locked(), (
            "_request_mntr_update requires self._internal_lock.locked()"
            )
        if not self._mntr_request: #might be forced due to timeout
            for d in self._device_subscrs.values():
                if d.length() > 0:
                    self._mntr_request += 1
                    update_period = self._max_update_period #if no icoming changes, period between update requests
                    if (num_vals > 10): #since there were changed points report in the last update
                        update_period = self._min_update_period
                    scheduler.after(update_period, self._trigger_send_mntr_request)
                    return #if ANY device has monitor values going, we just need one request sent out
    def _trigger_send_mntr_request(self): #run the request on a thread pool instead of the scheduler since it must wait for a lock
        thread_pool.NORMAL.queue_noresult(self._send_mntr_request)
    def _send_mntr_request(self, retry=0):
        #send cml while locked to prevent overlap with aml
        try:
            while self._cml_queue: #queue of points that came in but were not subscribed
                self._internal_lock.acquire() # protect pt data cache
                try:
                    src_addr, obj_id = self._cml_queue.pop()
                    point_data = None
                    #check against current subscription list - only cml if not subscribed
                    dev_subscr_data = self._device_subscrs.get(src_addr)
                    if dev_subscr_data:
                        point_data = dev_subscr_data.get_point(obj_id)
                    if point_data is None:
                        self._send_CML(src_addr, obj_id) #for hung over subscriptions
                finally:
                    self._internal_lock.release()
        except: #if something goes wrong, don't stop monitoring
            msglog.exception()
        #check for report slow down to allow AMLs to quickly get out
        if self._aml_defferal: #recent AML sent.  Wait to do report to allow more amls to go out
            self._aml_defferal = 0
            self._aml_defferal_count += 1
            if self._aml_defferal_count < 7: #deffer a max of three max update periode times
                scheduler.after(self._max_update_period / 2, self._trigger_send_mntr_request) #defer
                return
        self._aml_defferal_count = 0
        pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_REPORT, retry)
        try:
            self._send_rznp_packet(pkt)
        except ETimeout, e:
            msglog.log('mpx:rz',INFO,'mntr request timeout - reschedule in 15 seconds')
            scheduler.after(15, self._trigger_send_mntr_request) #try again in fifteen  seconds
    # another device on the network has requested an update
    def _proc_rznp_update_request(self, pkt):
        thread_pool.NORMAL.queue_noresult(self._trigger_proc_rznp_update_request,pkt)
    def _trigger_proc_rznp_update_request(self, pkt):
        #print "_trigger_proc_rznp_update_request: acquire"
        self._internal_lock.acquire()
        #print "_trigger_proc_rznp_update_request: acquired"
        try:
            if self.debug_lvl & 96:
                print_array_as_hex(array.array('B',pkt))
            # Process given pkt:
            a_src_addr = pkt[RZHS_SRC_1ST : RZHS_SRC_LAST + 1] #should still match between np pkt and host rsp pkt typs
            # unpack yields a one-elem tuple:
            src_addr = struct.unpack('<I', a_src_addr)[0]
            if self._bound_devices.has_key(src_addr):
                dev_subscr_data = self._bound_devices[src_addr]
                for obj_id in dev_subscr_data.obj_ids():
                    point_data = dev_subscr_data.get_point(obj_id)
                    if point_data is None:
                        msglog.log('mpx:rz',INFO,
                                   '_proc_rznp_update_request:Point is None '
                                   'for (%d,%d).'
                                   % (src_addr, obj_id))
                        continue
                    if point_data.value is not None:
                        # send an value packet to the other rz device
                        self._set_value(src_addr, obj_id, point_data.value)
        finally:
            #print "_trigger_proc_rznp_update_request: release"
            self._internal_lock.release()
            #print "_trigger_proc_rznp_update_request: released"
        return
    def _reestablish_aml_ownership(self, point_data):
        assert self._internal_lock.locked(), (
            "_reestablish_aml_ownership requires self._internal_lock.locked()"
            )
        lan_addr = point_data.dst_addr
        obj_id = point_data.obj_id
        self._send_AML(lan_addr, obj_id)
        self.AML_Engine(self, point_data)
        if self.debug_lvl & 8:
            msglog.log('mpx:rz', DB,
                       '_reestablish_aml_ownership(): Sent LAN_AML for %d,%d' %
                       (lan_addr, obj_id))
        return
    def _reestablish_global_aml_ownership(self):
        if self.debug_lvl & 8:
            msglog.log('mpx:rz', DB,
                       '_reestablish_aml_ownership():'
                       ' Scanning for points requiring (re)LAN_AML.')
        #print "_reestablish_global_aml_ownership: acquire"
        self._internal_lock.acquire()
        #print "_reestablish_global_aml_ownership: acquired"
        try:
            if self._reestablish_global_aml_ownership_busy:
                return
            self._reestablish_global_aml_ownership_busy = True
            if self._reestablish_global_aml_ownership_entry is not None:
                self._reestablish_global_aml_ownership_entry.cancel()
            device_addresses = self._device_subscrs.keys()
        finally:
            #print "_reestablish_global_aml_ownership: release"
            self._internal_lock.release()
            #print "_reestablish_global_aml_ownership: released"
        try:
            for lan_addr in device_addresses:
                #print "_reestablish_global_aml_ownership: acquire2"
                self._internal_lock.acquire()
                #print "_reestablish_global_aml_ownership: acquired2"
                try:
                    if self._device_subscrs.has_key(lan_addr):
                        dev_subscr_data = self._device_subscrs[lan_addr]
                        subscribed_ids = dev_subscr_data.get_object_ids()
                finally:
                    #print "_reestablish_global_aml_ownership: release2"
                    self._internal_lock.release()
                    #print "_reestablish_global_aml_ownership: released2"
                for obj_id in subscribed_ids:
                    #print "_reestablish_global_aml_ownership: acquire3"
                    self._internal_lock.acquire()
                    #print "_reestablish_global_aml_ownership: acquired3"
                    try:
                        point_data = dev_subscr_data.get_point(obj_id)
                        if point_data is None:
                            continue
                        self._reestablish_aml_ownership(point_data)
                    finally:
                        #print "_reestablish_global_aml_ownership: release3"
                        self._internal_lock.release()
                        #print "_reestablish_global_aml_ownership: released3"
        finally:
            self._reestablish_global_aml_ownership_busy = False
        return
    def _reestablish_global_aml_ownership_callback(self):
        thread_pool.NORMAL.queue_noresult(
            self._reestablish_global_aml_ownership
            )
        return
    def _send_AML(self, dst_addr, obj_id): #call while locked
        ext = form_addr_obj_id_array(dst_addr, obj_id)
        pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_AML, 0, ext)
        try:
            self._send_rznp_packet(pkt)
        except Exception, e:
            msglog.exception()
        self._aml_defferal = 1 #temporarily slow down reports while adding points
        self._request_mntr_update()
        return None
    def _queue_CML(self, lan_addr, obj_id):
        self._cml_queue.append((lan_addr, obj_id,))
    def _send_CML(self, lan_addr, obj_id):
        cml_ext = form_addr_obj_id_array(lan_addr, obj_id)
        cml_pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_CML, 0, cml_ext)
        try:
            self._send_rznp_packet(cml_pkt)
        except Exception, e:
            msglog.exception()
            return e
        return None
    def _send_time(self): #background process of sending time every hour
        # rz time packet 14 bytes of data
        # second, minute, hour, day, date, month, year, juiliandate (2),
        # rtc_flags, seconds since midnight (4)
        # time tuple
        # tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec,
        # tm_wday, tm_yday, tm_isdst
        tt = time.localtime()
        julian = form_short(tt[7])
        seconds = (tt[3] * 3600) + (tt[4] * 60) + tt[5]
        seconds = form_long(seconds)
        ta = array.array('B', [tt[5], tt[4], tt[3], (tt[6]+1) % 7,
                               tt[2], tt[1], tt[0] % 100,
                               julian[0], julian[1], 4,
                               seconds[0], seconds[1], seconds[2], seconds[3]])
        # ldisc adds src_addr and hdr/ext chksums
        cml_pkt = form_host_pkt(0, LAN_TIME, 1, ta)
        try:
            self._send_rznp_packet(cml_pkt,0)
        except IOError, e:
            msglog.exception()
        return
    def _proc_rzhs_send_time(self, pkt): #PhWIn just tried to set the time.  Ignore.  Mediator controls time
        self._proc_ACK(pkt) #politely ACK the packet  but ignore it.  Mediator sends it's own set time packet every hour
        del pkt # GC NOW
        return 0
    def _proc_rznp_time_ack(self, pkt):
        self.debug_print(1, 'Set Time Ack received.  Squashed')
        #absorb this and do not pass it to phwin
        del pkt
        return 0
    def _proc_ACK(self, pkt):
        if (self._data_skt_rzhs == None):
            # There is no connection to PhWin, then bail out:
            return
        else:
            # Just return an OS-level LAN_TO_HOST ACK:
            #self._internal_lock.acquire()
            #try:
                self.debug_print(4, 'Rtn ACK to host:')
                ext = array.array('B', [0x06])
                slave_pkt = form_slave_pkt(ext, pkt)
                self._dskt_sendall(slave_pkt.tostring(), 10)
            #finally:
                #self._internal_lock.release()
        return
    def _proc_rzhs_to_mem(self, pkt):
        # example packet:
        #     16 01 FF FF FF FF 45 LL 00 CKSUM 20 40 8C 00/01 CKSUM
        # if the packet is addressed to the default modem server (MODEM_SERVER_DEF_ADDR)
        # (NOT broadcast) and the address of the data is: 0x4020 on page 0x8C
        # then: 
        #     if the value is a single byte of 0 then:
        #         prune all nodes below this rznet peer
        #     else if the value is a single byte of 1 then:
        #         read the xpoints.net file and create a new branch of nodes
        #         and start them
        ignore_pkt = False
        pass_to_modem_server = False
        # Low 24 bits of address.
        dest_addr24 =  pkt[RZHM_DST_1ST:RZHM_DST_LAST].tostring() #note only interested in first 3 bytes
        b_my_addr24 = form_long(self._rznp_addr)[0:3]
        if (b_my_addr24[0] == ord(dest_addr24[0]) and
            b_my_addr24[1] == ord(dest_addr24[1]) and
            b_my_addr24[2] == ord(dest_addr24[2])):
            self._proc_ACK(pkt) #sent directly to us at 100,000, so ACK
        elif dest_addr24 == '\xff\xff\xff': #addressed to modem server, do not ignore
            pass_to_modem_server = True
        else:
            pass_to_modem_server = True
            #print '_proc_rzhs_to_mem: ', repr(dest_addr24)
            if dest_addr24 != '\x00\x00\x00': #if broadcast, act on it
                if self.debug_lvl & 2:
                    msglog.log("mpx:rz", DB,
                               "My address: XX %0X %0X %0X\n"
                               "  No LAN_TO_MEM ACK for dest XX %0X %0X %0X" %
                               (b_my_addr24[2], b_my_addr24[1], b_my_addr24[0],
                                pkt[4], pkt[3], pkt[2]))
                ignore_pkt = True
        if self.debug_lvl & 2:
            msglog.log("mpx:rz", DB, "pkt[2:6]: %r" % pkt[2:6])
        if len(pkt) < 14:
            if self.debug_lvl & 2:
                msglog.log("mpx:rz", DB, "len(pkt): %r" % len(pkt))
            ignore_pkt = True
        elif pkt[10:13].tostring() != "\x20\x40\x8c":
            if self.debug_lvl & 2:
                msglog.log("mpx:rz", DB, "pkt[10:13]: %r" % pkt[10:13])
            ignore_pkt = True
        elif pkt[13] not in (0,1):
            if self.debug_lvl & 2:
                msglog.log("mpx:rz", DB, "pkt[13]: %r" % pkt[13])
            ignore_pkt = True
        if ignore_pkt:
            if self.debug_lvl & 2:
                msglog.log("mpx:rz", DB,
                           "_proc_rzhs_to_mem: Ignoring packet:\n%s ..." %
                           dump_tostring(pkt[0:32]))
            if pass_to_modem_server:
                self._send_rznp_packet(RzHostPkt(pkt), 0) #send without waiting for response
                return 0
        #all that is left is the start/stop application command
        action = pkt[13]
        if action == 0:
            self._rzhs_to_mem_stop_application()
        elif action == 1:
            self._rzhs_to_mem_start_application()
        else:
            raise EUnreachableCode()
        if pass_to_modem_server:
            self._send_rznp_packet(RzHostPkt(pkt), 0) #send without waiting for response
        return 0
    def _proc_rzhs_goto(self, pkt): #when goto recevied, we should shut down nodes
        #a goto sent to any board means were are in the process of reloading os and the app should stop
        self._rzhs_to_mem_stop_application() #may not need so much indirection regarding the thread
        self._send_rznp_packet(RzHostPkt(pkt), 0) #send without waiting for response
    def _rzhs_to_mem_stop_application_callback(self):
        if self.debug_lvl & 2:
            msglog.log("mpx:rz", DB,
                       "_rzhs_to_mem_stop_application_callback()")
        try:
            application_parent = self._application_parent
            for application_node in application_parent.children_nodes():
                if self.debug_lvl & 2:
                    msglog.log("mpx:rz", DB,
                               "  pruning: %r" %
                               application_node.as_node_url())
                application_node.prune(True)
        except:
            msglog.exception()
        return
    def _rzhs_to_mem_stop_application(self):
        if self.debug_lvl & 2:
            msglog.log("mpx:rz", DB, "_rzhs_to_mem_stop_application()")
        self._application_running = 0
        self._command_q.queue_noresult(
            self._rzhs_to_mem_stop_application_callback
            )
        return
    def _rzhs_to_mem_start_application_callback(self):
        if self.debug_lvl & 2:
            msglog.log("mpx:rz", DB,
                       "_rzhs_to_mem_start_application_callback()")
        try:
            application_parent = self._application_parent
            if self.debug_lvl & 2:
                msglog.log("mpx:rz", DB, "  discover_children: %r" %
                           application_parent.as_node_url())
            application_parent.discover_children()
            for application_node in application_parent.children_nodes():
                if self.debug_lvl & 2:
                    msglog.log("mpx:rz", DB, "  starting: %r" %
                               application_node.as_node_url())
                application_node.start()
        except:
            msglog.exception()
        return
    def _rzhs_to_mem_start_application(self):
        if self.debug_lvl & 2:
            msglog.log("mpx:rz", DB, "_rzhs_to_mem_start_application()")
        # self._command_q.queue_noresult(
            # self._rzhs_to_mem_start_application_callback
            # )
        #not needed since control service should do this instead
        self._application_running = 1
        return
    def _proc_rzhs_AML(self, pkt):  #PHWIN has requested  AML
        global REPORT_LIST_NAME
        #print "_proc_rzhs_AML: acquire"
        self._internal_lock.acquire() # protect pt data cache
        #print "_proc_rzhs_AML: acquired"
        try:
            if self.debug_lvl & 8:
                msglog.log('mpx:rz',DB,
                           '_proc_rzhs_AML:Processing LAN_AML from RZHost...')
            # 6 bytes/subscr, up to 14 (Fred?) subscrs
            num_pt_subscrs = (pkt[RZHM_DATA_1ST] - 1) / 6
            # Create extensions for RZNet LAN_AML pkts, so that we send
            # fewest pkts:
            aml_exts_list = [] # saves extensions ready to go
            aml_exts_dict = {} # saves extensions-in-progress
            # prep an array to hold LAN_AML extension for up to 14 points
            # per target node
            aml_ext = array.array('B')
            for n in range(num_pt_subscrs):
                # Get pt info from pkt:
                base_idx = RZHM_HDR_LEN + n * 6
                lan_addr = struct.unpack('<I', pkt[base_idx:base_idx + 4])[0]
                obj_id = struct.unpack('<H', pkt[base_idx + 4:base_idx + 6])[0]
                if lan_addr == 100000: continue #ignore any request for phwin monitor of internal points
                if not self._device_subscrs.has_key(lan_addr):
                    self._device_subscrs[lan_addr] = DevSubscrData(
                        self.def_max_dev_subscrs,
                        self.debug_lvl
                        )
                dev_subscr_data = self._device_subscrs[lan_addr]
                result = dev_subscr_data.add_point_subscr(lan_addr, obj_id)
                point_data = dev_subscr_data.get_point(obj_id)
                point_data.set_phwin()
                if type(result) == types.ListType:
                    for t in result:
                        self._send_CML(t[0], t[1])
                        if self.debug_lvl & 24:
                            msglog.log('mpx:rz',DB,
                                       '_proc_rzhs_AML:Sent CML for %d, %d.'
                                       % (t[0], t[1]))
                    result = -1 # added point subscr
                if result == 0: # if point already subscribed on device:
                    self.debug_print(1,
                                     'Already subscribed to (%d, %d).',
                                     lan_addr, obj_id)
                    # make sure that PhWin gets cur value on next LAN_REPORT
                    # request:
                    point_data.phwin_COV = 1
                    # add point to end of list
                    self._REPORT_pts.ml_insert_elem_as_prev(
                        point_data,REPORT_LIST_NAME
                        )
                    if self.debug_lvl & 8:
                        msglog.log('mpx:rz', DB, '_proc_rzhs_AML: '
                                   '%d, %d already exists with value %s' %
                                   (lan_addr, obj_id, point_data.value))
                    continue # we already have val for reqd pt, so continue
                # Current point needs to be subscribed on device. If we've
                # already seen this point's lan_addr, try to extend existing
                # array:
                a = pkt[base_idx : base_idx + 6]
                if aml_exts_dict.has_key(lan_addr):
                    nNumBytes = len(aml_exts_dict[lan_addr])
                    # If existing array has max allowed point refs, then
                    # remove array from dict, and start new array:
                    if nNumBytes >= (6 * 14):
                        del aml_exts_dict[lan_addr]
                        aml_exts_dict[lan_addr] = a
                        aml_exts_list.append((lan_addr, a))
                        if self.debug_lvl & 8:
                            msglog.log('mpx:rz',DB,
                                       '_proc_rzhs_AML: '
                                       'Added %d, %d to new pkt array' %
                                       (lan_addr, obj_id))
                    else:
                        # Enough room in existing array:
                        aml_exts_dict[lan_addr].extend(a)
                        if self.debug_lvl & 8:
                            msglog.log('mpx:rz',DB,
                                       '_proc_rzhs_AML: '
                                       'Added %d, %d to end of extant array' %
                                       (lan_addr, obj_id))
                else:
                    # init new array and add to dict and to list:
                    aml_exts_dict[lan_addr] = a
                    aml_exts_list.append((lan_addr, a))
                    if self.debug_lvl & 8:
                        msglog.log('mpx:rz',DB,
                                   '_proc_rzhs_AML:Added %d, %d to new pkt '
                                   'array, new device dict' %
                                   (lan_addr, obj_id))
            aml_exts_dict.clear() # GC NOW
            # Form and send a LAN_AML pkt for each extension formed above:
            while len(aml_exts_list) > 0:
                t_ext = aml_exts_list.pop(0) # gradually clear list as we go...
                lan_addr = t_ext[0]
                # ldisc adds src_addr and hdr/ext chksums
                rznet_pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_AML, 0,
                                         t_ext[1])
                try:
                    self._aml_defferal = 1
                    self._send_rznp_packet(rznet_pkt)
                    if self.debug_lvl & 8:
                        msglog.log('mpx:rz',DB,
                                   '_proc_rzhs_AML:Sent AML pkt to RZNet,'
                                   ' to %d' % lan_addr)
                    # Because it works; else, target RZ Controller can get
                    # confused:
                except IOError, e:
                    msglog.exception()
            self._request_mntr_update()
        finally:
            #print "_proc_rzhs_AML: release"
            self._internal_lock.release()
            #print "_proc_rzhs_AML: released"
        # Form and send an ACK pkt back to PhWin:
        self._proc_ACK(pkt)
        del pkt # GC NOW
        return 0
    def _proc_rznp_aml_ack(self, pkt): #an ack has been returned for an AML packet
        self.debug_print(8, 'AML Ack received.  Squashed')
        #absorb this and do not pass it to phwin
        self._ack_rznp_packet()
        del pkt
        return 0
    def _proc_rzhs_CML(self, pkt):
        global REPORT_LIST_NAME
        # If pkt was addressed to Default Modem Server, then it's intended for
        # re-"broadcast". However, since other (HTML) clients might still be
        # listening for values from the RZNet, we must walk the
        # known-subscribed nodes and unsubscribe only those that PhWin
        # alone is watching:
        a_dst_addr = pkt[RZHM_DST_1ST : RZHM_DST_LAST + 1]
        # strip off possible seq num:
        dst_addr = struct.unpack('<I', a_dst_addr)[0]
        if dst_addr == MODEM_SERVER_DEF_ADDR:
            # clear all phwin attrs of points, and (perhaps) unsubscribe
            self._subscr_scan(1)
            self._internal_lock.acquire()
            try:
                self._REPORT_pts.ml_clear(REPORT_LIST_NAME)
            finally:
                self._internal_lock.release()
        # @fixme: Else, pkt was intended to make only this "Modem Server"
        #         clear one or more of its own subscriptions. Implement
        #         this code when Mediator can run templates from an RZ App...
        else:
            msglog.log('broadway',ERR,
                       '_proc_rzhs_CML: Mediator does not yet run templates, '
                       'so it cannot clear subscriptions to those templates.')
        # Need to send ACK to PhWin, even though it's not the broadcast
        # ACK that PhWin thinks it should be...:
        self._proc_ACK(pkt)
        del pkt
        return 0

    def _proc_rznp_ack(self, pkt): #an ack has been returned for several commands including the CML packet
        #absorb this and do not pass it to phwin
        self.debug_print(8, 'Local Ack received.   Squashed')
        self._ack_rznp_packet()
        #del pkt
        return 0
    def _proc_rzhs_REPORT(self, pkt):
        global REPORT_LIST_NAME
        self._internal_lock.acquire() # protect pt data cache
        try:
            a_ext_len = pkt[RZHM_DATA_1ST : RZHM_DATA_LAST + 1]
            # obtain the extension length (unpack yields a one-elem tuple)  any
            # length greater than 0 indicates retry request:
            ext_len = struct.unpack('<H', a_ext_len)[0]
            # retry request and we still have last response
            if (ext_len == 0) or (self._last_response_pkt is None):
                # prep an array to hold LAN_TO_HOST extension:
                upd_ext = array.array('B', [0x02])
                for i in range(11):
                    # max of 11 point values in one response pkt
                    cur_pt = self._REPORT_pts.ml_get_next(REPORT_LIST_NAME)
                    if cur_pt is self._REPORT_pts:
                        # Less than 11 points in the REPORT list
                        break
                    cur_pt.ml_remove(REPORT_LIST_NAME)
                    cur_pt.set_phwin() # reset unsubscr timer
                    cur_pt.phwin_COV = 0
                    ht_buf = None
                    try:
                        # from Intel to HiTech float
                        ht_buf = float_to_HiTech(float(cur_pt.value))
                    except:
                        # value of pt has not been read successfully yet (ie
                        # still None or and Exception)
                        msglog.log(
                            "mpx:rz", INFO, "_proc_rzhs_REPORT: Failed to"
                            " report value of (%r, %r) as %r" %
                            (cur_pt.dst_addr, cur_pt.obj_id, cur_pt.value)
                            )
                        msglog.exception()
                        continue
                    # Form/append extension segment:
                    upd_ext.extend(form_addr_obj_id_array(cur_pt.dst_addr,
                                                          cur_pt.obj_id))
                    a_value = array.array('B', [ht_buf[0], ht_buf[1],
                                                ht_buf[2], ht_buf[3],
                                                cur_pt.state & 0xFF])
                    upd_ext.extend(a_value)

                upd_ext[0] = len(upd_ext) + 1 # incl. chksum in count
                rsp_pkt = form_slave_pkt(upd_ext, pkt)
                self._last_response_pkt = rsp_pkt
            else:
                self.debug_print(1, 'rzhs retry for REPORT')
            try:
                self._data_skt_rzhs.sendall(self._last_response_pkt.tostring(), 10)
            except:
                msglog.log('mpx:rz',ERR,'_proc_rzhs_REPORT: Failed to write '
                           'LAN_TO_HOST pkt to data socket.')
                msglog.exception()
            del pkt # decr ref count
        finally:
            self._internal_lock.release()
            return 0
    def _subscr_scan(self, clr_phwin = 0):
        self.debug_print(1, 'Scanning for unrequested points to unsubscribe.')
        # disable all other accessors while we play with the points dict
        #print "_subscr_scan: acquire"
        self._internal_lock.acquire()
        #print "_subscr_scan: acquire"
        try:
            if not self._application_running:
                return #we might be loading OS or app.
            # Walk the points dict, and create one or more extensions for each
            # node that has one or more expired points. Reference up to 14
            # points in each extension:
            cml_exts_list = [] # saves extensions ready to go
            cml_exts_dict = {} # saves extensions-in-progress
            # prep an array to hold LAN_CML extension for up to 14 expired
            # points per target node:
            cml_ext = array.array('B')
            for dev_subscr_data in self._device_subscrs.values():
                # get ALL subscrs, and let code below determine expiration...
                pds = dev_subscr_data.get_subscrs()
                for point_data in pds:
                    if clr_phwin != 0:
                        # implement active unsubscribe from phwin
                        point_data.phwin = 0
                    dst_addr = point_data.dst_addr
                    obj_id = point_data.obj_id
                    # Determine if we do NOT need to unsubscribe:
                    point_in_use = point_data.is_in_use()
                    self.debug_print(
                        1,
                        'Testing to unsubscr point (%d, %d):\n '
                        '  phwin = %r; phwin_COV = %r.\n '
                        '  phwin_end_time = %r; time = %r\n'
                        '  _cov_callback is not None: %r\.'
                        '  is_in_use(): %r',
                        dst_addr, obj_id,
                        point_data.phwin, point_data.phwin_COV,
                        point_data.phwin_end_time, time.time(),
                        point_data._cov_callback,
                        point_in_use
                        )
                    if point_in_use:
                        continue
                    if cml_exts_dict.has_key(dst_addr):
                        # We've already seen this point's node addr, extend
                        # existing array:
                        nNumBytes = len(cml_exts_dict[dst_addr])
                        # If existing array has max allowed point refs, then
                        # remove array from dict, and start new array:
                        if nNumBytes >= (6 * 14):
                            del cml_exts_dict[dst_addr]
                            a = form_addr_obj_id_array(dst_addr, obj_id)
                            cml_exts_dict[dst_addr] = a
                            cml_exts_list.append((dst_addr, a))
                            if self.debug_lvl & 16:
                                msglog.log('mpx:rz',DB,
                                           '_subscr_scan (CML): '
                                           'Added (%d,%d) to new pkt array'
                                           % (dst_addr, obj_id))
                        else:
                            # Enough room in existing array:
                            cml_exts_dict[dst_addr].extend(
                                form_addr_obj_id_array(dst_addr, obj_id)
                                )
                            if self.debug_lvl & 16:
                                msglog.log('mpx:rz',DB,
                                           '_subscr_scan (CML): '
                                           'Added (%d,%d) to extant pkt array'
                                           % (dst_addr, obj_id))
                    else:
                        # Add a new array to dict and to list:
                        a = form_addr_obj_id_array(dst_addr, obj_id)
                        cml_exts_dict[dst_addr] = a
                        cml_exts_list.append((dst_addr, a))
                        if self.debug_lvl & 16:
                            msglog.log('mpx:rz',DB,
                                       '_subscr_scan (CML): '
                                       'Added %d, %d to new pkt array, '
                                       'new device dict'
                                       % (dst_addr, obj_id))
                    dev_subscr_data.remove_point_subscr(obj_id)
                    self.debug_print(
                        1,
                        'Unsubscribing unrequested point (%d, %d)',
                        dst_addr, obj_id
                        )
            # Clear the dict:
            cml_exts_dict.clear()
            # Form and send a LAN_CML pkt for each extension formed above:
            while len(cml_exts_list) > 0:
                t = cml_exts_list.pop(0)
                dst_addr = t[0]
                #dst_addr = BROADCAST_ADDR
                ext = t[1]
                # ldisc adds src_addr and hdr/ext chksums
                pkt = form_host_pkt(MODEM_SERVER_DEF_ADDR, LAN_CML, 0, ext)
                try:
                    self._send_rznp_packet(pkt)
                    if self.debug_lvl & 16:
                        msglog.log('mpx:rz',DB,
                                   '_subscr_scan:Sent CML pkt to RZNet, to %d'
                                   % dst_addr)
                except IOError, e:
                    msglog.exception()
        finally:
            #print "_subscr_scan: release"
            self._internal_lock.release() # re-enable accessors
            #print "_subscr_scan: released"

        return

    def _proc_rzhs_ovrd(self, pkt): #phwin sent an override command
        host_pkt = RzHostPkt(pkt)
        self._send_rznp_packet(host_pkt)
        #self._set_override(None,None,None, None, host_pkt) #send via this method to merge streams of commands together
        self._proc_ACK(pkt)
        del host_pkt
        del pkt
    def _proc_rzhs_clov(self, pkt): #phwin sent a clear override command
        host_pkt = RzHostPkt(pkt)
        self.clr_override(None, None, host_pkt)
        self._proc_ACK(pkt)
        del host_pkt
        del pkt
    def _proc_rzhs_null(self, pkt): #phwin sent an ack
        self._proc_ACK(pkt)
        del pkt
    # Allow other threads to send commands that can interrupt and control this
    # thread SAFELY, via the integral cmd socket pair (near/far):
    def _send_cmd(self, cmd):
        #print "_send_cmd: acquire"
        self._internal_lock.acquire() # disable access to members
        #print "_send_cmd: acquired"
        try:
            self._far_cmd_skt.send(cmd) # cmd will emerge at the _near_cmd_skt
        finally:
            #print "_send_cmd: release"
            self._internal_lock.release() # re-enable access to members
            #print "_send_cmd: released"

    def _get_addrs(self):
        # Get own and next addresses from RS485 dev file:
        # str_addrs = 8 * '\0'
        # str_addrs = fcntl.ioctl(self._fd_rznp, RZNET_IOCGADDRS, str_addrs)
        # self._rznp_addr, self._rznp_next_addr = struct.unpack(2 * 'I',
                                                              # str_addrs)
        # self.debug_print(
            # 1,
            # 'Read addrs from rznet ldisc ioctl. Own = %08x. Next = %08x.',
            # self._rznp_addr, self._rznp_next_addr
            # )
        raise ENotImplemented
    def get_addrs(self): # externally-usable wrapper for _get_addrs()
        #self._get_addrs() # update addrs from ldisc
        return (self._rznp_addr, self._rznp_addr)

    def _get_node_list(self):
        # Get number of nodes found by ldisc on main rznet. Request all nodes,
        # up to 255.
        # Array struct (on return from ioctl call):
        # byte 0 : num node addrs in array
        # byte 1-3 : 0's
        # byte 4 - 1023 : addresses followed by 0's
        str_nodes = 1024 * '\0'
        str_nodes = fcntl.ioctl(self._fd_rznp, RZNET_IOCGNODES, str_nodes)
        raw_nodes_tuple = struct.unpack(256 * 'I', str_nodes)
        num_nodes = raw_nodes_tuple[0]
        del self._nodes_list[:] # GC NOW
        del self._nodes_list
        self._nodes_list = list(raw_nodes_tuple[1 : num_nodes + 1])
        self.debug_print(1,
                         'Read %d node addrs from rznet ldisc ioctl:',
                         num_nodes)
        if self.debug_lvl & 1:
            for node in self._nodes_list:
                if node == 0:
                    break
                print node

        # @FIXME: Can probably save some processing if we use str_nodes
        #         DIRECTLY to form node_ext...
        # Prep pkt extension containing all node addrs EXCEPT our own!:
        del self._ext_nodes[:]
        iThisNode = -1
        for i in range(len(self._nodes_list)):
            node = self._nodes_list[i]
            if node == 0:
                break;
            if node == self._rznp_addr:
                iThisNode = i
                # do NOT include ourselves as explicit list elem;
                # else, we show up 2x in PhWin
                continue
            b_node = form_long(node)
            node_ext = array.array('B', [b_node[0], b_node[1], b_node[2],
                                         b_node[3]])
            self._ext_nodes.extend(node_ext)
        if iThisNode >= 0:
            del self._nodes_list[iThisNode] # rmv our addr from list

    def timeout_callback(self, tmr_ID):
        thread_pool.NORMAL.queue_noresult(self.timeout, tmr_ID)
        return
    def timeout(self, tmr_ID):
        self.debug_print(2, 'timeout(): timer %d', tmr_ID)
        if tmr_ID == self._timer_ID_subscr_scan:
            self._send_cmd('subscr_scan');
        return
    def debug_print(self, msg_lvl, msg, *args):
        if (msg_lvl & self.debug_lvl) > 0:
            if args:
                msg = msg % args
            prn_msg = 'RznetThread: ' + msg
            print prn_msg
        return
    def debug_print_host_packet(self, pktd):
        self.debug_print_host_packet_buffer(pktd._pkt)
    def debug_print_host_packet_buffer(self, buf):
        if (8192 & self.debug_lvl) > 0:
            length = RZHM_HDR_LEN
            if (buf[RZHM_TYPE] & 0x40) > 0: #extended
                length += buf[RZHM_DATA_LAST] * 256 + buf[RZHM_DATA_1ST]
            print 'send to modem server: [%s] >>>> ' % PacketTypeEnum.get(buf[RZHM_TYPE] & 0x3F, 'unknown'),
            print_array_as_hex(buf[:length])

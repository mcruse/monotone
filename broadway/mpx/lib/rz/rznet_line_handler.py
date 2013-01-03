"""
Copyright (C) 2003 2004 2007 2008 2010 2011 Cisco Systems

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
from mpx.lib.threading import Condition
from mpx.lib.threading import Semaphore
from mpx.lib.threading import EKillThread
from mpx.lib.threading import Event
from mpx.lib.threading import ImmortalThread
from mpx.lib.threading import Lock
from mpx.lib.threading import currentThread

CSI = '\x1b[' #ANSI escape
CSIreset = CSI+'0m'

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
        import mpx.lib.rz.rznet_line_handler
        mpx.lib.rz.rznet_line_handler._ProfileStub_self = self
        mpx.lib.rz.rznet_line_handler._ProfileStub_evt = evt
        profile.run("""
import mpx.lib.rz.rznet_line_handler
mpx.lib.rz.rznet_line_handler._ProfileStub_self.bound_method(
    mpx.lib.rz.rznet_line_handler._ProfileStub_evt
    )
""")
        return None

REPORT_LIST_NAME = 'REPORT_LIST_NAME'
SUBSCR_LIST_NAME = 'SUBSCR_LIST_NAME'
BOUND_LIST_NAME = 'BOUNDR_LIST_NAME'

class PointData(MultiListMixin):
    """class PointData: Wraps data for point managed by RznetLineHandler
       instance."""
    def __init__(self, dst_addr, obj_id, debug_lvl=0):
        MultiListMixin.__init__(self)

        self.dst_addr = dst_addr
        self.obj_id = obj_id
        self.debug_lvl = debug_lvl

        self.value = None
        self.state = None
        self.cond = None
        self._cov_callback = None

        self._aml_engine = None

        self.phwin = 0            # 1: exactly one instance of PhWin has
                                  #    subscribed to this pt
        self.phwin_COV = 0        # 1: value has changed; notify PhWin next
                                  #    time it asks
        self.phwin_period = 900.0 # - used to calc assocd end_time
        self.phwin_end_time = 0   # - time at which point is to be
                                  #   unsubscribed, unless requested
        return
    def _check_cov(self):
        if self._cov_callback:
            self._cov_callback(self) # - let the ION decide to produce the
                                     #   event on change
        # @fixme I don't like testing this every time.
        if self._aml_engine is not None:
            if self._aml_engine.retry_event:
                self._aml_engine.retry_event.cancel()
                if self.debug_lvl >= 1:
                    msglog.log(
                        'mpx:rz', DB,
                        'PointData._check_cov(): Cancel AML_Engine for %d,%d' %
                        (self.dst_addr, self.obj_id)
                        )
            self._aml_engine = None
        return
    def set_phwin(self):
        self.phwin = 1
        self.phwin_end_time = self.phwin_period + time.time()
        return
    ##
    # A consistant way to determine if the PointData is "in use" by ANY
    # consumer.
    def is_in_use(self):
        # 1. self._cov_callback indicates that there is a consumer associated
        #    to a node (either an active .get(), or a COV consumer).
        # 2. self.phwin indicates that the PhWin client has requested the
        #    value. self.phwin_end_time is used to try to determin if the
        #    client has gone away.
        return self._cov_callback is not None or (
            self.phwin and self.phwin_end_time > time.time()
            )
    ##
    # A consistant way to determine if the PointData is "in use" by PhWin.
    def phwin_is_using(self):
        return self.phwin and self.phwin_end_time > time.time()

class DevSubscrData:
    def __init__(self, max_dev_subscrs=256, debug_lvl=0):
        self._list_head = MultiListMixin(SUBSCR_LIST_NAME)
        self._map = {} # K: obj_id, V: PointData ref
        self._max_dev_subscrs = max_dev_subscrs
        self.debug_lvl = debug_lvl
        return
    def add_point_subscr(self, dst_addr, obj_id):
        global SUBSCR_LIST_NAME
        result = 0 # subscr exists
        point_data = None
                                           # - If given point is already
        if self._map.has_key(obj_id):      #    subscribed, then move subscr
            point_data = self._map[obj_id] #    to head of list.
        else:                              # - else,add subscr to head of list.
            point_data = PointData(dst_addr, obj_id, self.debug_lvl)
            self._map[obj_id] = point_data
            result = -1 # added subscr
        self._list_head.ml_insert_elem_as_next(point_data,SUBSCR_LIST_NAME)
        # If too many subscrs, remove oldest:
        over = self._list_head.ml_length(SUBSCR_LIST_NAME) - \
               self._max_dev_subscrs
        if over > 0:
            result = []
        for i in range(over):
            last_point_data = self._list_head.ml_get_prev(SUBSCR_LIST_NAME)
            result.append((last_point_data.dst_addr, last_point_data.obj_id,))
            last_point_data.ml_remove(SUBSCR_LIST_NAME)
            del self._map[last_point_data.obj_id]
        return result
    def get_point(self, obj_id):
        result = None
        if self._map.has_key(obj_id):
            result = self._map[obj_id]
        return result
    def remove_point_subscr(self, obj_id):
        global SUBSCR_LIST_NAME
        if self._map.has_key(obj_id):
            point_data = self._map[obj_id]
            point_data.ml_remove(SUBSCR_LIST_NAME)
            point_data._cov_callback = None
            del self._map[obj_id]
        return
    def get_subscrs(self):
        return self._map.values()[:] # @fixme Methinks values() already creates
                                     #        a new list instance.
    def get_object_ids(self):
        return self._map.keys()
    def length(self):
        return len(self._map)
    def clear_subscrs(self):
        obj_ids = self._map.keys()
        for obj_id in obj_ids:
            self.remove_point_subscr(obj_id)
        return

class DevBoundData:
    def __init__(self, debug_lvl=0):
        self._map = {} # K: obj_id, V: PointData ref
        self.debug_lvl = debug_lvl
        return
    def add_point_subscr(self, dst_addr, obj_id):
        result = 0 # subscr exists
        point_data = None
        if self._map.has_key(obj_id):      # - If given point is already
            point_data = self._map[obj_id] #   subscribed, then move subscr to
                                           #   head of list.
        else:                              # - else, add subscr to head of list
            point_data = PointData(dst_addr, obj_id)
            self._map[obj_id] = point_data
            result = -1 # added subscr
        return result
    def get_point(self, obj_id):
        result = None
        if self._map.has_key(obj_id):
            result = self._map[obj_id]
        return result
    def obj_ids(self):
        return self._map.keys()
    def remove(self, obj_id):
        if self._map.has_key(obj_id):
            pnt = self._map[obj_id]
            pnt._cov_callback = None
            del self._map[obj_id]

class PktData:
    def __init__(self, buf_len = 1024):
        self.buf = array.array('B', buf_len * '\0')
        self.idx = 0
        self.len = RZHM_HDR_LEN # changes only if pkt is extended
    def tostring(self):
        return self.buf.tostring()[:self.len]
    def tofile(self, fileno):
        return self.tostring().tofile(fileno)
# Pkt-reception states:
ST_SYN = 0
ST_SOH = 1
ST_HDR = 2
ST_EXT = 3

_tmp_dir = properties.get('TEMP_DIR')

class RznetThread(ImmortalThread):
    n_tty_num = 0
    #@fixme: "6" is owned by X25; need to assign new number to rznet...
    n_rznet_num = 6

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
                    if self.debug_lvl >= 1:
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
                if self.debug_lvl >= 1:
                    msglog.log('mpx:rz', DB,
                               'retry_handler():  PointData dereferenced.')
                return
            rznet_thread = self.rznet_thread
            rznet_thread._internal_lock.acquire()
            try:
                if point_data.value is not None:
                    # If there is a value, the AML succeeded.
                    point_data._aml_engine = None
                    if self.debug_lvl >= 1:
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
                    if self.debug_lvl >= 1:
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
                if self.debug_lvl >= 1:
                    msglog.log(
                        'mpx:rz', DB,
                        'retry_handler(): Sent LAN_AML for %d,%d' %
                        (point_data.dst_addr, point_data.obj_id)
                        )
            finally:
                rznet_thread._internal_lock.release()
            return

    def __init__(self, rs485_port, slave_port_num, master_port_node, QA,
                 req_addr, application_parent):
        ImmortalThread.__init__(self)

        self._port_rznp = rs485_port
        self._lskt_rzhs_port_num = slave_port_num
        self._port_rzhm = master_port_node # we'll try to open this dev file
        self._QA = QA
        self._req_addr = req_addr
        self._application_parent = application_parent

        self.ignore_point_is_none = True
        self.log_interesting_cmls = True

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
        self._rznp_addr = 0
        self._rznp_next_addr = 0

        # PhWin client (TCP socket) port variables. (Used by serial
        # connection also, via PPP.):
        self._lskt_rzhs = None # listen_skt for PhWin connection
        self._fd_lskt_rzhs = -1
        self._dskt_rzhs = None  # data_skt for PhWin connection
        self._fd_dskt_rzhs = -1
        self._dskt_rzhs_rd_buf_len = 4096 # - nice default number,
                                          #   replaced in __set_up()
        # RZNet (RS485 COM) port variables:
        self._file_rznp = None # - we'll try to open this dev file in
        self._fd_rznp = -1     #   self.__set_up()...
        # init value is overwritten in __set_up()
        self._rznp_ldisc_num_org = struct.pack('i', self.n_tty_num)

        # RZHostMaster Port (RS232 COM) port variables. (This port
        # is optional!):
        #  in self.start()
        self._file_rzhm = None # - we'll try to open this dev file in
        self._fd_rzhm = -1     #   self.__set_up()...

        #
        # Init rznp pkt processing dictionary. Key = type; Value =
        # method.  Note that LAN_TOKEN_LIST IS recognized, but is
        # processed completely within the ldisc. All other pkt types
        # should be ignored, since Mediator runs a virtual Modem
        # Server, but does NOT run a virtual Mozaic:
        self._rznp_procs = {
            LAN_MTR_VAL : self._proc_rznp_rd_val,
            LAN_OBJ_VAL : self._proc_rznp_rd_bound_val,
            LAN_SEND_MEM : self._proc_rznp_send_mem,
            LAN_TO_HOST : self._proc_to_host,
            LAN_UPDATE : self._proc_rznp_update_request,
            LAN_CML    : self._proc_rznp_rcvd_cml,
            LAN_AML    : self._proc_rznp_rcvd_aml,
            }
        # Init rzhs pkt processing dictionary.
        # Key = type; Value = method:
        self._rzhs_procs = {
            LAN_ALARMS : self._proc_rzhs_ALARMS,
            LAN_AML : self._proc_rzhs_AML,
            LAN_CML : self._proc_rzhs_CML,
            LAN_REPORT : self._proc_rzhs_REPORT,
            LAN_SEND_MEM : self._proc_rzhs_send_mem,
            LAN_TIME : self._proc_ACK,
            LAN_TOKEN_LIST : self._proc_rzhs_token_list,
            LAN_TO_MEM : self._proc_rzhs_to_mem
            }

        self.def_max_dev_subscrs = 256

        self._pkt_form_states = { ST_SYN : self._do_SYN,
                                  ST_SOH : self._do_SOH,
                                  ST_HDR : self._do_HDR,
                                  ST_EXT : self._do_EXT }

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

        self._internal_lock = Lock()
        self._internal_lock.acquire() # - disable over-eager accessors until

        self._application_running = 1 #running by default.  This is set when phwin sends app start / stop commands

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
            self._last_response_pkt = None
            # List of LAN_TO_HOST pkts waiting to go out in response to
            # incoming LAN_REPORT pkts from PhWin. Needed since LTH
            # extension length is limited to 11 point values, at 11 bytes
            # each, and since Modem Server may send only one pkt in
            # response to any given pkt recvd from PhWin:
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
            # Pkt formation vars:
            self._pkts = [] # list of single-pkt bufs
            self._num_pkts = 2
            for i in range(self._num_pkts):
                self._pkts.append(PktData())
            self.debug_print(1, 'pkt0: %s', str(self._pkts[0]))
            self.debug_print(1, 'pkt1: %s', str(self._pkts[1]))
            self._last_pkt_idx = -1 # - idx of last valid unused pkt, if
                                    #   any 
            self._cur_pkt_idx = 0   # - idx of cur incoming pkt
            self._pkt_form_state = 0
            # Create Schedule and timer IDs and periods:
            self._sched_entry_subscr_scan = None # set by Schedule.after()
            self._timer_ID_subscr_scan = 0
            self._time_subscr_scan = 1000.0
            # Init node tuple to be read from ldisc ioctl upon client
            # request: 
            self._nodes_list = []
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
            self._port_rznp.open()
            self._file_rznp = self._port_rznp.file
            self._fd_rznp = self._file_rznp.fileno()
            self.debug_print(1, 'RZNet dev file opened: %s (%d).', 
                             self._port_rznp.dev, self._fd_rznp)
            # make sure that we actually receive a "0"...
            self._rznp_ldisc_num_org = struct.pack('I', 0xFF)
            # Get/save original ldisc for opened port (for restoration in
            # stop()):
            self._rznp_ldisc_num_org = fcntl.ioctl(self._fd_rznp, TIOCGETD,
                                                   self._rznp_ldisc_num_org)
            # need first elem of one-elem tuple
            org_ldisc_num = struct.unpack('I', self._rznp_ldisc_num_org)[0]
            self.debug_print(1, 'Saved original RZNet dev file ldisc # %d.',
                             org_ldisc_num)
            # Set ldisc to "rznet":
            s = struct.pack('I', self.n_rznet_num)
            try:
                fcntl.ioctl(self._fd_rznp, TIOCSETD, s)
            except IOError, (errno, strerror):
                msglog.log('broadway', ERR,
                           'Failed to set rznet ldisc on port %s:\n'
                           'Error %d: %s\n Make sure module n_rznet is loaded!'
                           % (self._port_rznp.dev, errno, strerror))
                self._port_rznp.close()
                raise EKillThread('Failed to set rznet ldisc')
                return

            self._fds[self._fd_rznp] = self._proc_evt_rznp # add entry to dict:

            # If RznetNode has requested that we set a specific rznet_addr,
            # then do it now:
            s_own_addr = struct.pack('I', self._req_addr)
            fcntl.ioctl(self._fd_rznp, RZNET_IOCSADDR, s_own_addr)

            # Get initial own and next addresses from RS485 dev file into self
            # properties. (Next will be same as own, until ldisc joins the
            # RZNet):
            self._get_addrs()

            self.debug_print(1, 'New RZNet dev file ldisc = rznet (%d)',
                             self.n_rznet_num)
            # Always open a listen_socket in case PhWin wants to connect:
            self._lskt_rzhs = create_listen_skt(self._lskt_rzhs_port_num)
            if self._lskt_rzhs == None:
                raise EKillThread('Failed to create PhWin socket')
            self._fd_lskt_rzhs = self._lskt_rzhs.fileno()
            # add entry to dict:
            self._fds[self._fd_lskt_rzhs] = self._proc_evt_lrzhs

            # Set buf_lens to obtain the most bytes from skts without multiple
            # reads:
            self._dskt_rzhs_rd_buf_len = self._lskt_rzhs.getsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF
                )
            self.debug_print(1, 'fd %d has read buf len = %d.',
                             self._fd_lskt_rzhs, self._dskt_rzhs_rd_buf_len)
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
            if (self._port_rzhm != None) and (self._QA == 1):
                self._port_rzhm.open()
                self._file_rzhm = self._port_rzhm.file
                self._fd_rzhm = self._file_rzhm.fileno()
                self.debug_print(1, 'RZHostMaster dev file opened: %s (%d).',
                                 self._port_rzhm.dev, self._fd_rzhm)
                # add entry to
                self._fds[self._fd_rzhm] = self._proc_evt_rzhm
                # dict: 
            # Order unsubscription of all points subscribed by this
            # line_handler during a previous incarnation:
            unsub_pkt = form_net_pkt(BROADCAST_ADDR, LAN_CML, 0, None,
                                     PKTFL_NO_BCAST_RESP)
            try:
                # send global LAN_CML pkt to ldisc
                unsub_pkt.tofile(self._file_rznp)
            except IOError, e:
                msglog.log('broadway',ERR,
                           'start: Failed to write global LAN_CML '
                           'pkt to port: errno = %d' % e.errno)
                return
            else:
                if self.log_interesting_cmls or self.debug_lvl >= 1:
                    msglog.log('mpx:rz', DB, 'Sent global LAN_CML')

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
        try:    self._lskt_rzhs.close()
        except: msglog.exception()
        self._fd_lskt_rzhs = -1
        #
        # Close client data_skt (if open):
        #
        try:
            if self._dskt_rzhs != None:
                self._dskt_rzhs.close();
        except:
            msglog.exception()
        self._dskt_rzhs = None
        self._fd_dskt_rzhs = -1
        #
        # Reset original ldisc for port:
        #
        try:
            fcntl.ioctl(self._fd_rznp, TIOCSETD, self._rznp_ldisc_num_org)
            org_ldisc_num = struct.unpack('i', self._rznp_ldisc_num_org)
            self.debug_print(1, 'Restored original ldisc # %d.',
                             org_ldisc_num)
        except:
            msglog.exception()
        #
        # Close RS485 port:
        #
        try:    self._file_rznp.close()
        except: msglog.exception()
        self._file_rznp = None
        self._fd_rznp = -1

        # Show that ldisc is no longer part of network:
        self._rznp_next_addr = self._rznp_addr
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

    def prune(self): #owner node is being pruned
        pass
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

        try: # Thread loop:
            timeout_msec = 15000
            while True:
                # Enter the one-and-only wait state used by this RznetThread:
                evt_pairs = self._poll_obj.poll(timeout_msec)
                #self.debug_print(1, 'Event pairs received = %s', evt_pairs)
                #
                # If no event pairs are returned by poll(), then a timeout
                # must have occurred:
                if len(evt_pairs) == 0:
                    self._proc_timeout()
                # Else, process event pairs:
                else:
                    for evt_pair in evt_pairs:
                        # Timestamp:
                        if evt_pair[0] == self._fd_dskt_rzhs:
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
        self._internal_lock.acquire()
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
                    if self.log_interesting_cmls or self.debug_lvl >= 1:
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
                if self.debug_lvl > 0:
                    msglog.log('mpx:rz', DB,
                               'register_rznet_cov(): '
                               'Sent LAN_AML for %d,%d' %
                               (dst_addr, obj_id))
            if point_data.value is not None and point_data.state is not None:
                # If the point already has a value, ensure that the consumer
                # gets an initial value:
                cov_callback(point_data)
        finally:
            self._internal_lock.release()
        return
    def unregister_rznet_cov(self, lan_address, id_number):
        point_in_use = False
        self._internal_lock.acquire()
        try:
            dev_subscr_data = self._device_subscrs[lan_address]
            point_data = dev_subscr_data.get_point(id_number)
            if point_data is not None:
                if point_data.phwin_is_using():
                    if self.debug_lvl >= 1:
                        msglog.log(
                            'mpx:rz', DB,
                            'unregister_rznet_cov:Skipped CML for (%r,%r), '
                            'in use.' % (lan_address, id_number)
                            )
                else:
                    point_data._cov_callback = None
                    dev_subscr_data.remove_point_subscr(id_number)
                    self._send_CML(lan_address, id_number)
                    if self.debug_lvl >= 1:
                        msglog.log(
                            'mpx:rz', DB,
                            'unregister_rznet_cov:Sent CML for (%r,%r).' %
                            (lan_address, id_number)
                            )
        except:
            self._internal_lock.release()
            msglog.exception()
            return
        else:
            self._internal_lock.release()
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
        self._internal_lock.acquire()
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
                    if self.log_interesting_cmls or self.debug_lvl >= 1:
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
                pkt = form_net_pkt(dst_addr, LAN_AML, 0, ext)
                if self.debug_lvl > 0:
                    msglog.log('mpx:rz', DB,
                               'get_value(): Sent LAN_AML for %d,%d' %
                               (dst_addr, obj_id))
                try:
                    pkt.tofile(self._file_rznp) # send LAN_AML pkt to ldisc
                except IOError, e:
                    msglog.log(
                        'mpx:rz',ERR,
                        'get_value: Failed to write LAN_AML pkt for '
                        '%d,%d to port: errno = %d'
                        % (dst_addr, obj_id, e.errno))
                    if e.errno == ENODEV:
                        return 'RZ controller not found.'
                    if e.errno == EXFULL:
                        return 'Xmit Q is full.'
                    if e.errno == EBUSY:
                        return 'Port is passive.'
                    if e.errno == EINVAL:
                        return 'Ldisc rejected pkt.'
                    return 'Error #%d' % e.errno # for unanticipated errors
                point_data.cond = Condition()
                # acquire INSIDE critsec, to so we don't miss notify() from
                # other thread
                point_data.cond.acquire()
        finally:
            self._internal_lock.release()
        if (not point_data is None) \
           and (not point_data.cond is None):
            # wait OUTSIDE critsec, to allow notify() from other thread
            point_data.cond.wait(self._read_wait_time)
            point_data.cond.release()
            self._internal_lock.acquire()
            try:
                if point_data.value is None:
                    # timeout occurred
                    value = None
                else:
                    value = [point_data.value, point_data.state]
                del point_data.cond
                point_data.cond = None
            finally:
                self._internal_lock.release()
        return value
    def register_bound_proxy(self, ion):
        self._internal_lock.acquire()
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
            self._internal_lock.release()
    def unregister_bound_proxy(self, ion):
        self._internal_lock.acquire()
        try:
            dst_addr = int(ion.proxy_lan_addr)
            obj_id = int(ion.proxy_obj_ref)
            if self._bound_devices.has_key(dst_addr):
                dev_bound_data = self._bound_devices[dst_addr]
                dev_bound_data.remove(obj_id)
        finally:
            self._internal_lock.release()
    def unregister_subscribed_proxy(self, ion):
        self._internal_lock.acquire()
        try:
            dst_addr = int(ion.lan_address)
            obj_id = int(ion.id_number)
            if self._device_subscrs.has_key(dst_addr):
                dev_subscr_data = self._device_subscrs[dst_addr]
                dev_subscr_data.remove_point_subscr(obj_id)
        finally:
            self._internal_lock.release()

    def broadcast_update_request(self):
        #request all other boards to send latest value to mediator for bound
        # points
        update_request_pkt = form_net_pkt(BROADCAST_ADDR, LAN_UPDATE, 0, None,
                                          PKTFL_NO_BCAST_RESP)
        try:
            # send global LAN_UPDATE pkt to ldisc
            update_request_pkt.tofile(self._file_rznp)
        except IOError, e:
            msglog.log('broadway',ERR,
                       'start: Failed to write global LAN_UPDATE '
                       'pkt to port: errno = %d' % e.errno)
            return
        else:
            if self.debug_lvl >= 1:
                msglog.log('mpx:rz',DB,'Sent global LAN_UPDATE')
        return

    def _set_override(self, dst_addr, obj_id, value, pkt_type):
        # Value MUST be floating point:
        value = float(value)

        # Convert value from Intel to HiTech floating point:
        ht_buf = float_to_HiTech(value)

        # Form extension for override pkt:
        b_obj_id = form_short(obj_id)
        ext = array.array('B', [b_obj_id[0], b_obj_id[1], ht_buf[0],
                                ht_buf[1], ht_buf[2], ht_buf[3], 0, 0])

        # Form override pkt:
        pkt = form_net_pkt(dst_addr, pkt_type, 0, ext)

        # Send override pkt:
        try:
            if self._application_running:
                pkt.tofile(self._file_rznp) # send LAN_OBJ_OVRD pkt to ldisc
        except IOError, e:
            msglog.log('broadway',ERR,
                       'set_override: Failed to write LAN_OBJ_OVRD pkt to '
                       'port: errno = %d' % e.errno)
        # No need to make sure that point is subscribed. If it is not, then
        # caller has not cared enough to want to know the value yet...
        return
    def set_override(self, dst_addr, obj_id, value):
        self._set_override(dst_addr, obj_id, value, LAN_OBJ_OVRD)
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
        if self._bound_devices.has_key(dst_addr):
            dev_subscr_data = self._bound_devices[dst_addr]
            point_data = dev_subscr_data.get_point(obj_id)
            if point_data is None:
                if self.debug_lvl >= 1:
                    msglog.log('mpx:rz',DB,
                               'set_value:Point is None for (%d,%d).'
                               % (dst_addr, obj_id))
                return
            point_data.value = value
            point_data.state = 0

    def clr_override(self, dst_addr, obj_id):
        # Form LAN_CLOV (non-extended) pkt:
        pkt = form_net_pkt(dst_addr, LAN_OBJ_CLOV, obj_id)

        # Send LAN_CLOV pkt:
        try:
            pkt.tofile(self._file_rznp) # send LAN_OBJ_OVRD pkt to ldisc
        except IOError, e:
            msglog.log('broadway',ERR,'clr_override: Failed to write '
                       'LAN_CLOV pkt to port: errno = %d' % e.errno)

        # No need to make sure that point is subscribed. If it is not, then
        # caller has not cared enough to want to know the value yet...
        return
    def _send_CMLs(self, pnt_lst):
        cml_exts_list = [] # - saves extensions ready to go
        cml_exts_dict = {} # - saves extensions-in-progress
        cml_ext = array.array('B') # - prep an array to hold LAN_CML extension
                                   #   for up to 14 expired points per target
                                   #   node
        for dst_addr,obj_id in pnt_lst:
            if not self._device_subscrs.has_key(dst_addr):
                if self.debug_lvl >= 1:
                    msglog.log('mpx:rz',DB,
                               '_send_CMLs: Got req to clear'
                               ' subscr in unknown device %d. Skipping...'
                               % dst_addr)
                continue
            dev_subscr_data = self._device_subscrs[dst_addr]
            point_data = dev_subscr_data.get_point(obj_id)
            if point_data is None:
                if self.debug_lvl >= 1:
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
                    if self.debug_lvl >= 1:
                        msglog.log('mpx:rz',DB,
                                   '_send_CMLs: Added (%d,%d) to new pkt array'
                                   % (dst_addr, obj_id))
                else: # else, enough room in existing array:
                    cml_exts_dict[dst_addr].extend(
                        form_addr_obj_id_array(dst_addr, obj_id)
                        )
                    if self.debug_lvl >= 1:
                        msglog.log('mpx:rz',DB,
                                   '_send_CMLs: Added (%d,%d) to extant pkt'
                                   ' array' % (dst_addr, obj_id))
            else: # else, add a new array to dict and to list:
                a = form_addr_obj_id_array(dst_addr, obj_id)
                cml_exts_dict[dst_addr] = a
                cml_exts_list.append((dst_addr, a))
                if self.debug_lvl >= 1:
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
            pkt = form_net_pkt(dst_addr, LAN_CML, 0, ext)
            try:
                pkt.tofile(self._file_rznp) # send pkt to ldisc
                if self.debug_lvl >= 1:
                    msglog.log('mpx:rz',DB,
                               '_send_CMLs: Sent CML pkt to RZNet, to %d'
                               % dst_addr)
                time.sleep(2.0) # - because it works; else, maybe too fast and
                                #   target RZ Controller can get confused
            except IOError, e:
                msglog.log('broadway',ERR,'_subscr_scan: Failed to write '
                           'LAN_CML pkt to port: errno = %d' % e.errno)
        return
    def clear_subscr(self, targets=None):
        # prevent other updates while we clear one or more subscrs
        self._internal_lock.acquire()
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
                flags = 0
                if targets is None:
                    dst_addr = BROADCAST_ADDR
                    flags = PKTFL_NO_BCAST_RESP
                    # Clear all local subscr lists:
                    for dev_subscr_data in self._device_subscrs.values():
                        dev_subscr_data.clear_subscrs()
                elif type(targets) == types.IntType:
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
                unsub_pkt = form_net_pkt(dst_addr, LAN_CML, 0, None, flags)
                try:
                    # send global LAN_CML pkt to ldisc
                    unsub_pkt.tofile(self._file_rznp)
                except IOError, e:
                    msglog.log('mpx:rz',ERR,
                               'clear_subscr: Failed to write LAN_CML'
                               ' pkt for %d to port: errno = %d'
                               % (dst_addr, e.errno))
                    return
                else:
                    if self.log_interesting_cmls or self.debug_lvl >= 1:
                        msglog.log(
                            'mpx:rz',DB, 'clear_subscr: '
                            'Sent global LAN_CML to %d, reqd by thin client.'
                            % dst_addr
                            )
        finally:
            self._internal_lock.release()
        return

    def _proc_timeout(self):
        pass

    def _proc_evt_rznp(self, evt):
        #self.debug_print(1, 'Processing RZNet Event:')
        if (evt & select.POLLIN) != 0:
            for i in range(10): # read every pkt available from ldisc: up to a max of 10 packets at a time
                raw_pkt_str = None
                try:
                    # does NOT require end-of-pkt snub in ldisc
                    raw_pkt_str = os.read(self._fd_rznp, 1024)
                except OSError, e:
                    if e.errno == 11: # "Resource temporarily unavailable"
                        break
                if (raw_pkt_str == None) or (raw_pkt_str == ''):
                    break # no more pkts available in ldisc's rxq
                pkt_type = ord(raw_pkt_str[RZNP_TYPE]) & 0x3F
                proc = self._rznp_procs.get(pkt_type)
                if proc is None: #not self._rznp_procs.has_key(pkt_type):
                    if self.debug_lvl >= 1:
                        msglog.log(
                            'mpx:rz',DB,
                            'Unrecognized pkt type %d recvd from RZNet'
                            % pkt_type
                            )
                    # unrecognized type: do not attempt any further processing
                    # of pkt
                    continue
                proc(raw_pkt_str) # - call fn based on pkt type
                # if req'd, notify waiting thread of pkt arrival and processing
                if self._set_cond_on_read:
                    self.debug_print(1, 'Waiting for read event...')
                    while self._read_wait_evt.isSet():
                        # wait until consumer thread has cleared evt in prep
                        # for waiting
                        time.sleep(0.01)
                    self._read_wait_evt.set();
        elif (evt & select.POLLERR) != 0:
            raise ERestart()
        return None

    # Leave listen_skt open perennially, to allow disconnect/reconnect cycles
    # when other end of data_skt goes away unceremoniously:
    def _proc_evt_lrzhs(self, evt):
        if (evt & select.POLLIN) != 0:
            addr = None
            dskt = None
            try:
                dskt, addr = self._lskt_rzhs.accept()
            except socket.error, details:
                # remote client socket disappeared after calling connect()
                msglog.log(
                    'broadway',ERR,'listen_skt could not accept connection '
                    'from remote client socket: %s.' % str(details)
                    )
            else:
                if not self._dskt_rzhs is None:
                    # ALWAYS stop existing dskt and use new dskt
                    old_host, old_port = self._dskt_rzhs.getpeername()
                    self._dskt_rzhs.close() # close previous
                    self._remove_dskt()     # ..
                    msglog.log('broadway', WARN,
                               'Old data socket (%s:%s) closed; '
                               'new data socket (%s:%s) opened.'
                               % (old_host, old_port, addr[0], addr[1]))
                self._dskt_rzhs = dskt
                self._dskt_rzhs.setblocking(0)
                self._dskt_rzhs.setsockopt(socket.IPPROTO_TCP,
                                           socket.TCP_NODELAY, 1)
                # prevent skt from jabbering with empty pkts after closure
                linger = struct.pack("ii", 1, 0)
                self._dskt_rzhs.setsockopt(socket.SOL_SOCKET,
                                           socket.SO_LINGER, linger)
                # Register to get events from dskt:
                self._fd_dskt_rzhs = self._dskt_rzhs.fileno()
                self._poll_obj.register(self._fd_dskt_rzhs, select.POLLIN)
                self._fds[self._fd_dskt_rzhs] = self._proc_evt_drzhs

                # While dskt exists, stop further poll service to lskt:
                # @FIXME: rmv this line when perennial lskt works
                # self._poll_obj.unregister(self._fd_lskt_rzhs)
                # @FIXME: rmv this line when perennial lskt works
                # del self._fds[self._fd_lskt_rzhs]
                # @FIXME: rmv this line when perennial lskt works
        elif (evt & select.POLLERR) != 0:
            raise ERestart()
        return None

    def _remove_dskt(self):
        # dskt no longer exists, so unregister it, remove it from fds map, and
        # delete it. Re-reg lskt:
        try: self._poll_obj.unregister(self._fd_dskt_rzhs)
        except: msglog.exception()
        try: del self._fds[self._fd_dskt_rzhs]
        except: msglog.exception()
        self._fd_dskt_rzhs = -1
        self._dskt_rzhs = None
        # @FIXME: rmv this line when perennial lskt works
        # self._poll_obj.register(self._fd_lskt_rzhs, select.POLLIN)
        # self._fds[self._fd_lskt_rzhs] = self._proc_evt_lrzhs

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

    def _proc_evt_drzhs(self, evt):
        # Test remote data_skt for closure:
        try:
            host_name, port_num = self._dskt_rzhs.getpeername()
        except: # remote socket is closed:
            self.debug_print(
                0,
                'data-skt %d appears to be dead on the other end.',
                self._fd_dskt_rzhs
                )
            # dskt no longer exists, so unregister it, remove it from fds map,
            # and delete it. Re-reg lskt:
            self._remove_dskt()
            return None

        if (evt & select.POLLIN) != 0:
            bytes = array.array('B')
            bytes.fromstring(self._dskt_rzhs.recv(self._dskt_rzhs_rd_buf_len,
                                                  10))
            if len(bytes) < 1: # if dskt is jabbering:
                self._dskt_rzhs.close()
                self._remove_dskt()
                return None

            # else, we've got data to process:
            if self.debug_lvl > 1:
                self.debug_print(1, CSI+'42m Processing RZHost bytes from dskt:')
                print_array_as_hex(bytes)
                print CSIreset

            # Validate recvd pkt before proceeding...
            ext = None
            for byte in bytes:
                pkt_rdy = self._pkt_form_states[self._pkt_form_state](byte)
                if pkt_rdy == 0: # pkt is NOT ready
                    continue
                pktd = self._pkts[self._last_pkt_idx]
                # we're processing that pkt now, so show it's done
                self._last_pkt_idx = -1
                if (self._QA == 1) and (self._file_rzhm != None):
                    # For QA, disable Internal Modem Server functions:
                    self.debug_print(
                        1, 'Forwarding RZHost pkt to External Modem Server:'
                        )
                    if self.debug_lvl > 1:
                        print_array_as_hex(pktd.buf[:pktd.len])
                    # strip off unused portion at end of 1024-byte pkt buffer
                    pktd_buf = pktd.buf[:pktd.len]
                    try:
                        # forward pkt out of host port
                        pktd_buf.tofile(self._file_rzhm)
                    except IOError, e:
                        msglog.log(
                            'broadway',ERR,
                            'Failed to write pkt recvd from eth port:\n'
                            '%s\nto host serial port, due to: %s.'
                            % (pktd.buf,str(e))
                            )
                else: # else, let 'er rip:
                    if pktd.len > RZHM_HDR_LEN: # it's ext, so get ext:
                        # let form_net_pkt() add/recalc ext chksum
                        ext = pktd.buf[RZHM_HDR_LEN : (pktd.len - 1)]
                    else:
                        # make sure to clear this before we try to use it!
                        ext = None
                    # If pkt is not sent to us, reformat pkt for RZNet and
                    # pass it on:
                    a_dst_addr = pktd.buf[RZHM_DST_1ST : RZHM_DST_LAST + 1]
                    # strip off possible seq num
                    dst_addr = struct.unpack('<I', a_dst_addr)[0]
                    self.debug_print(1, 'dst_addr = %x.', dst_addr)

                    # If dst_addr is not Default Modem Server or our specific
                    # RZNet addr:
                    if (dst_addr != MODEM_SERVER_DEF_ADDR) and (
                        dst_addr != self._rznp_addr):
                        # Repkg rzhost_master pkt as rznet_peer pkt:
                        self.debug_print(
                            1, 'Pass-through pkt from host to rznet:'
                            )
                        if self.debug_lvl > 1:
                            print_array_as_hex(pktd.buf[:pktd.len])
                        a_data = pktd.buf[RZHM_DATA_1ST : RZHM_DATA_LAST + 1]
                        data = struct.unpack('<H', a_data)[0] # extract data/len
                        flags = 0 # default: no special pkt handling by ldisc
                        pkt_type = pktd.buf[RZHM_TYPE] & 0x3F
                        self.debug_print(1, 'pkt_type = %02x', pkt_type)

                        if ((pkt_type == LAN_TO_MEM) or
                            (pkt_type == LAN_RESET) or
                            (pkt_type == LAN_TIME) or
                            (pkt_type == LAN_OBJ_OVRD) or
                            (pkt_type == LAN_OBJ_CLOV) or
                            (pkt_type == LAN_CML) or
                            (pkt_type == LAN_AML) or
                            (pkt_type == LAN_ACK_ALARM) or
                            (pkt_type == LAN_ACK_TREND)):
                            self.debug_print(
                                1,
                                'Setting Response Flag for type %02x',
                                pkt_type
                                )
                            # MS must respond for specific LTMS recvr nodes
                            flags = (flags | PKTFL_RESPOND)
                        if dst_addr == 0:
                            self.debug_print(1, 'flag broadcast')
                            flags = PKTFL_NO_BCAST_RESP
                        rznet_pkt = form_net_pkt(dst_addr, pktd.buf[RZHM_TYPE],
                                                 data, ext, flags)
                        # 2nd Timestamp:
                        self._tm0 = time.time()
                        self._tm_del2 = self._tm0 - self._tm2
                        if self._tm_del2_avg == 0:
                            self._tm_del2_avg = self._tm_del2
                        else:
                            self._tm_del2_avg = (self._tm_del2_avg +
                                                 self._tm_del2) / 2
                        self.debug_print(
                            1,
                            CSI+'42mTime from "Recv PhWin Pkt" to "Send Pkt to '
                            'RZNet":\nLast: %0.3f. Avg: %0.3f.'+CSIreset,
                            self._tm_del2, self._tm_del2_avg
                            )
                        # put rznet pkt out on the rznet
                        try: rznet_pkt.tofile(self._file_rznp)
                        except IOError, e:
                            msglog.log('broadway',ERR,
                                       '_proc_evt_drzhs: Failed to '
                                       'write %d pkt to port: errno = %d'
                                       % (pktd.buf[RZHM_TYPE], e.errno))
                    else: # else, pkt is to us:
                        proc = None
                        try:
                            # get fn based on pkt type
                            proc = self._rzhs_procs[pktd.buf[RZHM_TYPE] & 0x3F]
                        except:
                            self.debug_print(
                                0,
                                'proc for RZHostMaster pkt type %d not found.',
                                pktd.buf[RZHM_TYPE] & 0x3F
                                )
                            # If we have an attached rzhost_master port, then
                            # forward pkt AS IS to that port:
                            if (self._fd_rzhm != -1):
                                pktd.buf.tofile(self._file_rzhm)
                        else:
                            proc(pktd.buf) # call fn based on pkt type
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

    def _dskt_sendall(self, data, timeout):
        if self._dskt_rzhs is None:
            return
        try:
            self._dskt_rzhs.sendall(data, timeout)
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

    def _proc_evt_rzhm(self, evt):
        if (evt & select.POLLIN) != 0:
            bytes = array.array('B')
            bytes.fromstring(self._file_rzhm.read())

            self.debug_print(
                1,
                'Processing RZHostSlave bytes from RZHostMaster serial port:'
                )
            if self.debug_lvl > 1:
                print_array_as_hex(bytes)

            # Pass the recvd bytes directly to client (PhWin) at dskt_rzhs,
            # if any:
            self._dskt_sendall(bytes.tostring(), 10)
        elif (evt & select.POLLERR) != 0:
            raise ERestart()
        return None

    def _proc_rznp_rd_val(self, pkt):
        global REPORT_LIST_NAME
        if not self._application_running:
            return #ignore incoming value packets when app is not running
        if self.debug_lvl >= 1:
            print_array_as_hex(array.array('B',pkt))
        # Process given pkt:
         # unpack yields a one-elem tuple, extract element via [0]. Pkt from
         # ldisc; do not specify endianess of src_addr or ext_len:
        src_addr = struct.unpack('<I', pkt[RZNP_SRC_1ST : RZNP_SRC_LAST + 1])[0]
        # obtain the extension length (unpack yields a one-elem tuple)
        ext_len = struct.unpack('<H', pkt[RZNP_DATA_1ST : RZNP_DATA_LAST + 1])[0]
        # each value is given in 7 bytes; make sure num bytes is reasonable
        #assert ((ext_len - 1) % 7) == 0, (
            #'Bad number of bytes in value pkt: %d not evenly divisible by '
            #'7' % ext_len
            #)
        num_vals = (ext_len - 1) / 7
        dev_subscr_data = self._device_subscrs.get(src_addr)
        for i in range(num_vals):
            # first data byte is right after chksum
            base_idx = i * 7 + RZNP_HDR_LEN
            obj_id = struct.unpack('<H',pkt[base_idx:base_idx+2])[0] #(ord(pkt[base_idx + 5]) << 8) + ord(pkt[base_idx + 4])
            # If we have an entry, convert bytes to float value, and set
            # point value and state from recvd data:
            if dev_subscr_data:
                point_data = dev_subscr_data.get_point(obj_id)
                if point_data is None:
                    if not self.ignore_point_is_none:
                        self._send_CML(src_addr, obj_id)
                        if (self.log_interesting_cmls or
                            self.debug_lvl >= 1):
                            msglog.log(
                                'mpx:rz',DB,
                                '_proc_rznp_rd_val:Point is None; Sent CML'
                                ' for (%d,%d).' % (src_addr, obj_id)
                                )
                    continue
                point_data.value = HiTech_to_float(pkt[base_idx+2:base_idx+6])
                point_data.state = ord(pkt[base_idx + 6])
                # FGD eventually may produce an event through a callback
                # to the rz ion
                self._rcvd_value_cache[(src_addr,obj_id)] = point_data
                self._rcvd_value_fifo.append((src_addr,obj_id))
                #point_data._check_cov()
                if self.debug_lvl >= 10:
                    msglog.log('mpx:rz',DB,
                               '_proc_rznp_rd_val:Recvd value "%s" '
                               'and state "%s" for (%d,%d).'
                               % (point_data.value,
                                  point_data.state, src_addr, obj_id))
                    pass
            # Else, we did not request the value, so unsubscribe the point:
            else:
                if not self.ignore_point_is_none:
                    self._send_CML(src_addr, obj_id)
                    if self.log_interesting_cmls or self.debug_lvl >= 1:
                        msglog.log(
                            'mpx:rz',DB,
                            '_proc_rznp_rd_val:Sent CML for (%d,%d).'
                            % (src_addr, obj_id)
                            )
        #finally:
            #self._internal_lock.release()
        self._rcvd_value_semaphore.release()
        return
    def _proc_rznp_rd_bound_val(self, pkt):
        if not self._application_running:
            return #ignore incoming value packets when app is not running
        #self._internal_lock.acquire()
        #try:
        if self.debug_lvl >= 1:
            print 'bound value rcvd: '
            print_array_as_hex(array.array('B',pkt))
        # Process given pkt:
        # unpack yields a one-elem tuple. Pkt from
         # ldisc; do not specify endianess of src_addr or ext_len:
        src_addr = struct.unpack('<I', pkt[RZNP_SRC_1ST : RZNP_SRC_LAST + 1])[0]
        # obtain the extension length (unpack yields a one-elem tuple)
        ext_len = struct.unpack('<H', pkt[RZNP_DATA_1ST : RZNP_DATA_LAST + 1])[0]
        if self.debug_lvl >= 1:
            print 'src_addr = 0x%08x. ext_len = 0x%04x' % (src_addr,ext_len)
        # each value is given in 7 bytes; make sure num bytes is reasonable
        assert ((ext_len - 1) % 7) == 0, (
            'Bad number of bytes in value pkt: '
            '%d not evenly divisible by 7'
            % ext_len
            )
        num_vals = (ext_len - 1) / 7
        dev_subscr_data = self._bound_devices.get(src_addr)
        for i in range(num_vals):
             # first data byte is right after chksum
            base_idx = i * 7 + RZNP_HDR_LEN
            obj_id = struct.unpack('<H',pkt[base_idx:base_idx+2])[0]
            # If we have an entry, convert bytes to float value, and set
            # point value and state from recvd data:
            if dev_subscr_data:
                point_data = dev_subscr_data.get_point(obj_id)
                if point_data is None:
                    if self.debug_lvl >= 1:
                        msglog.log(
                            'mpx:rz',DB,
                            '_proc_rznp_rd_bound_val:Point is None for '
                            '(%d,%d).' % (src_addr, obj_id))
                    continue
                point_data.value = HiTech_to_float(pkt[base_idx+2:base_idx+6])
                point_data.state = ord(pkt[base_idx + 6])
                # FGD eventually may produce an event through a callback
                # to the rz ion
                self._rcvd_value_cache[(src_addr,obj_id)] = point_data
                self._rcvd_value_fifo.append((src_addr,obj_id))
                #point_data._check_cov()
                # if self.debug_lvl >= 10:
                    # msglog.log('mpx:rz',DB,
                               # '_proc_rznp_rd_val:Recvd value '
                               # '"%s" and state "%s" for (%d,%d).'
                               # % (point_data.value, point_data.state,
                                  # src_addr, obj_id))
                    # pass
            # Else, we do not have a registration for this point:
            else:
                msglog.log('mpx:rz',INFO,
                           '_proc_rznp_rd_bound_val: not found (%d,%d).'
                           % (src_addr, obj_id))
        #finally:
            #self._internal_lock.release()
        self._rcvd_value_semaphore.release()
        return
    #collect updates and distribute them on a single thread instead of creating a new thread each time - this is really going on a point by point basis since OS does not aggragate this type of packet
    def _rcvd_value_run(self):
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
                if point_data.phwin != 0:
                    # RZ controllers send LAN_MTR_VAL only on COV
                    point_data.phwin_COV = 1
                    # If point is not yet in REPORT list, then add it:
                    if not point_data.is_in_list(REPORT_LIST_NAME):
                        # add point to end of list
                        self._REPORT_pts.ml_insert_elem_as_prev(
                            point_data,REPORT_LIST_NAME
                            )
                        if self.debug_lvl >= 10:
                            msglog.log(
                                'mpx:rz',DB,
                                '_proc_rznp_rd_val:Put value "%s" for '
                                '(%d,%d) into REPORT Q.'
                                % (point_data.value, src_addr, obj_id)
                                )
                if not point_data.cond is None: # if necy, notify waiters:
                    point_data.cond.acquire(self._read_wait_time)
                    try:
                        point_data.cond.notify()
                    finally:
                        point_data.cond.release()
    # another device on the network has requested an update
    def _proc_rznp_update_request(self, pkt):
        self._internal_lock.acquire()
        try:
            if self.debug_lvl >= 1:
                print_array_as_hex(array.array('B',pkt))
            # Process given pkt:
            a_src_addr = pkt[RZNP_SRC_1ST : RZNP_SRC_LAST + 1]
            # unpack yields a one-elem tuple. Pkt from
         # ldisc; do not specify endianess of src_addr:
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
            self._internal_lock.release()
        return
    def _reestablish_aml_ownership(self, point_data):
        assert self._internal_lock.locked(), (
            "_reestablish_aml_ownership requires self._internal_lock.locked()"
            )
        lan_addr = point_data.dst_addr
        obj_id = point_data.obj_id
        self._send_AML(lan_addr, obj_id)
        self.AML_Engine(self, point_data)
        if self.debug_lvl >= 2:
            msglog.log('mpx:rz', DB,
                       '_reestablish_aml_ownership(): Sent LAN_AML for %d,%d' %
                       (lan_addr, obj_id))
        return
    def _reestablish_global_aml_ownership(self):
        if self.debug_lvl >= 1:
            msglog.log('mpx:rz', DB,
                       '_reestablish_aml_ownership():'
                       ' Scanning for points requiring (re)LAN_AML.')
        self._internal_lock.acquire()
        try:
            if self._reestablish_global_aml_ownership_busy:
                return
            self._reestablish_global_aml_ownership_busy = True
            if self._reestablish_global_aml_ownership_entry is not None:
                self._reestablish_global_aml_ownership_entry.cancel()
            device_addresses = self._device_subscrs.keys()
        finally:
            self._internal_lock.release()
        try:
            for lan_addr in device_addresses:
                self._internal_lock.acquire()
                try:
                    if self._device_subscrs.has_key(lan_addr):
                        dev_subscr_data = self._device_subscrs[lan_addr]
                        subscribed_ids = dev_subscr_data.get_object_ids()
                finally:
                    self._internal_lock.release()
                for obj_id in subscribed_ids:
                    self._internal_lock.acquire()
                    try:
                        point_data = dev_subscr_data.get_point(obj_id)
                        if point_data is None:
                            continue
                        self._reestablish_aml_ownership(point_data)
                    finally:
                        self._internal_lock.release()
        finally:
            self._reestablish_global_aml_ownership_busy = False
        return
    def _reestablish_global_aml_ownership_callback(self):
        thread_pool.NORMAL.queue_noresult(
            self._reestablish_global_aml_ownership
            )
        return
    def _proc_rznp_rcvd_cml(self, pkt):
        # if we receive a Broadcast CML from another instance of PhWin
        # connected to a RS-232 port on a rz network board, we need to
        # resubscribe to all the non mpx_get/set points
        if self.log_interesting_cmls or self.debug_lvl >= 1:
            msglog.log(
                'mpx:rz', DB,
                'Received LAN_CML from interloping monitor,'
                ' (re)scheduling LAN_AML ownership in %s seconds.' %
                self._reestablish_global_aml_ownership_cml_timeout
                )
        self._internal_lock.acquire()
        try:
            if self._reestablish_global_aml_ownership_entry is not None:
                self._reestablish_global_aml_ownership_entry.cancel()
            self._reestablish_global_aml_ownership_entry = scheduler.after(
                self._reestablish_global_aml_ownership_cml_timeout,
                self._reestablish_global_aml_ownership_callback
                )
        finally:
            self._internal_lock.release()
        return
    def _proc_rznp_rcvd_aml(self, pkt):
        # if we receive a Broadcast AML from another instance of PhWin
        # connected to a RS-232 port on a rz network board, we need to set a
        # timer to take back the subscriptions if we do not receive a CML in a
        # resonable period of time.
        if self.log_interesting_cmls or self.debug_lvl >= 1:
            msglog.log(
                'mpx:rz', DB,
                'Received LAN_AML from interloping monitor,'
                ' (re)scheduling LAN_AML ownership in %s seconds.' %
                self._reestablish_global_aml_ownership_aml_timeout
                )
        self._internal_lock.acquire()
        try:
            if self._reestablish_global_aml_ownership_entry is not None:
                self._reestablish_global_aml_ownership_entry.cancel()
            self._reestablish_global_aml_ownership_entry = scheduler.after(
                self._reestablish_global_aml_ownership_aml_timeout,
                self._reestablish_global_aml_ownership_callback
                )
        finally:
            self._internal_lock.release()
        return
    def _send_AML(self, dst_addr, obj_id):
        ext = form_addr_obj_id_array(dst_addr, obj_id)
        # ldisc adds src_addr and hdr chksum
        pkt = form_net_pkt(dst_addr, LAN_AML, 0, ext)
        try:
            pkt.tofile(self._file_rznp) # send LAN_AML pkt to ldisc
        except Exception, e:
            reason = 'Unknown'
            errstr = 'Unknown'
            if hasattr(e, 'errno'):
                if errorcode.has_key(e.errno):
                    errstr = errorcode[e.errno]
                if e.errno == ENODEV:
                    reason = 'RZ controller not found.'
                if e.errno == EXFULL:
                    reason = 'Xmit Q is full.'
                if e.errno == EBUSY:
                    reason = 'Port is passive.'
                if e.errno == EINVAL:
                    reason = 'Ldisc rejected pkt.'
            msglog.log('mpx:rz', ERR,
                       '_send_AML(): '
                       'Failed to write LAN_AML pkt for '
                       '%d,%d to port: errno = %d (%s)\n'
                       'Reason: %s'
                       % (dst_addr, obj_id, e.errno, errstr, reason))
            msglog.exception()
            return e
        return None
    def _send_CML(self, lan_addr, obj_id):
        cml_ext = form_addr_obj_id_array(lan_addr, obj_id)
        # ldisc adds src_addr and hdr/ext chksums
        cml_pkt = form_net_pkt(lan_addr, LAN_CML, 0, cml_ext)
        try:
            cml_pkt.tofile(self._file_rznp)
        except Exception, e:
            reason = 'Unknown'
            errstr = 'Unknown'
            if hasattr(e, 'errno'):
                if errorcode.has_key(e.errno):
                    errstr = errorcode[e.errno]
                if e.errno == ENODEV:
                    reason = 'RZ controller not found.'
                if e.errno == EXFULL:
                    reason = 'Xmit Q is full.'
                if e.errno == EBUSY:
                    reason = 'Port is passive.'
                if e.errno == EINVAL:
                    reason = 'Ldisc rejected pkt.'
            msglog.log('mpx:rz', ERR,
                       '_send_CML(): '
                       'Failed to write LAN_CML pkt for '
                       '%d,%d to port: errno = %d (%s)\n'
                       'Reason: %s'
                       % (lan_addr, obj_id, e.errno, errstr, reason))
            msglog.exception()
            return e
        return None
    def _send_time(self):
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
        cml_pkt = form_net_pkt(0, LAN_TIME, 1, ta)
        try:
            cml_pkt.tofile(self._file_rznp)
        except IOError, e:
            msglog.log('broadway',ERR,'_send_time: Failed to write '
                       'LAN_TIME pkt to port: errno = %d' % e.errno)
        return

    def _proc_ACK(self, pkt):
        if (self._dskt_rzhs == None):
            # There is no connection to PhWin, then bail out:
            return
        else:
            # Just return an OS-level LAN_TO_HOST ACK:
            self._internal_lock.acquire()
            try:
                self.debug_print(1, 'Rtn ACK to host:')
                ext = array.array('B', [0x06])
                slave_pkt = form_slave_pkt(ext)
                self._dskt_sendall(slave_pkt.tostring(), 10)
            finally:
                self._internal_lock.release()
        return

    def _proc_to_host(self, raw_pkt):
        # If there is no connection to PhWin, then bail out:
        if (self._dskt_rzhs == None):
            return

        # 3rd Timestamp:
        self._tm1 = time.time()
        self._tm_del1 = self._tm1 - self._tm0
        if self._tm_del1_avg == 0:
            self._tm_del1_avg = self._tm_del1
        else:
            self._tm_del1_avg = (self._tm_del1_avg + self._tm_del1) / 2

        self.debug_print(1,
                         'Time from "Send RZNet Pkt" to "Recv RZNet Pkt":\n'
                         'Last: %0.3f. Avg: %0.3f.',
                         self._tm_del1, self._tm_del1_avg)

        # Re-format recvd rznet pkt for forwarding to PhWin:
        self._internal_lock.acquire()
        self.debug_print(1, CSI+'46m Pass-through pkt from rznet to host:'+CSIreset)
        ext = None
        if len(raw_pkt) > RZNP_HDR_LEN:
            # if it's an extended pkt, extract extension:
            # let form_slave_pkt() add/recalc ext chksum
            ext = array.array('B', raw_pkt[RZNP_HDR_LEN : len(raw_pkt) - 1])
        data = ord(raw_pkt[RZNP_DATA_1ST]) + (
            ord(raw_pkt[RZNP_DATA_LAST]) >> 8)
        slave_pkt = form_slave_pkt(ext)
        try:
            self._dskt_sendall(slave_pkt.tostring(), 10)
        finally:
            self._internal_lock.release()

        # 4th Timestamp:
        self._tm3 = time.time()
        self._tm_del3 = self._tm3 - self._tm1
        if self._tm_del3_avg == 0:
            self._tm_del3_avg = self._tm_del3
        else:
            self._tm_del3_avg = (self._tm_del3_avg + self._tm_del3) / 2

        self.debug_print(1,
                         'Time from "Recv RZNet Pkt" to "Send PhWin Pkt":\n'
                         'Last: %0.3f. Avg: %0.3f.',
                         self._tm_del3, self._tm_del3_avg)

    def _form_send_mem_response_ext(self, mem_addr, mem_page, num_bytes):
        self._internal_lock.acquire()
        try:
            ext = None
            self._get_addrs() # refresh addresses
            b_my_addr = form_long(self._rznp_addr)
            if (mem_addr == 0x44) and (mem_page == 0) and (num_bytes == 6):
                # Get Type/Address
                b_type = form_short(5)
                ext = array.array('B', [b_type[0], b_type[1],
                                        b_my_addr[0],  b_my_addr[1],
                                        b_my_addr[2],  b_my_addr[3]])
            elif (mem_addr == 0xE002) and (
                mem_page == 0) and (
                num_bytes == 2):
                # Get Version
                ext = array.array('B', [0, 0])
            elif (mem_addr == 0xF200) and (
                mem_page == 0) and (
                num_bytes == 4):
                # Get Alias
                ext = array.array('B', [b_my_addr[0], b_my_addr[1],
                                        b_my_addr[2], b_my_addr[3]])
            elif (mem_addr == 0xC003) and (
                mem_page == 0) and (
                num_bytes >= 4):
                b_next_addr = form_long(self._rznp_next_addr)
                ext = array.array('B', [b_next_addr[0], b_next_addr[1],
                                        b_next_addr[2], b_next_addr[3]])
                if (num_bytes == 7): # Get NextAddr/Date
                    ext_date = array.array('B', [RZNET_YEAR,
                                                 RZNET_MONTH,
                                                 RZNET_DAY])
                    ext.extend(ext_date)
            elif (mem_addr == 0x4020) and (
                mem_page == 0x8C) and (
                num_bytes == 1):
                # Get App Status
                ext = array.array('B', [1])

            elif mem_addr == RZNET_MEM_NODE_LIST:
                # Get Node List extension (already prepped by _get_node_list())
                ext = self._ext_nodes
            else:
                self.debug_print(0,
                                 'Recvd unknown LAN_SEND_MEM: mem_addr = '
                                 '0x%04x. mem_page = 0x%02x. num_bytes = %d',
                                 mem_addr, mem_page, num_bytes)
        finally:
            self._internal_lock.release()
        return ext

    def _proc_rznp_send_mem(self, pkt):
        self.debug_print(1, 'processing RZNetPeer LAN_SEND_MEM')
        a_ext_len = pkt[RZNP_DATA_1ST : RZNP_DATA_LAST + 1]
        # obtain the extension length (unpack yields a one-elem tuple). Pkt from
         # ldisc; do not specify endianess of ext_len:
        ext_len = struct.unpack('<H', a_ext_len)[0]
        if self.debug_lvl >= 1:
            print 'ext_len = 0x%04x' % ext_len
        if ext_len != 6:
            # all LAN_SEND_MEM pkts have exactly 6 bytes in extension
            self.debug_print(0,
                             'recvd LAN_SEND_MEM has wrong length. Want 6,'
                             ' Is %d', ext_len)
        # obtain the "mem addr" (unpack yields a one-elem tuple)
        mem_addr = struct.unpack('<H', pkt[14:16])[0]
        if self.debug_lvl >= 1:
            print 'mem_addr = 0x%04x' % mem_addr
        mem_page = pkt[16]
        if self.debug_lvl >= 1:
            print 'mem_page = 0x%04x' % mem_page
        # obtain num bytes to read (unpack yields a one-elem tuple)
        num_bytes = struct.unpack('<H', pkt[17:19])[0]
        if self.debug_lvl >= 1:
            print 'num_bytes = 0x%04x' % num_bytes

        ext = self._form_send_mem_response_ext(mem_addr, mem_page, num_bytes)
        if ext != None:
            a_src_addr = pkt[RZNP_SRC_1ST : RZNP_SRC_LAST + 1]
            # unpack yields a one-elem tuple
            src_addr = struct.unpack('<I', a_src_addr)[0]
            if self.debug_lvl >= 1:
                print 'src_addr = 0x%08x' % src_addr
            # form response to sender
            rsp_pkt = form_net_pkt(src_addr, LAN_TO_HOST, 0, ext)
            try: rsp_pkt.tofile(self._file_rznp)
            except IOError, e:
                msglog.log('broadway',ERR,
                           '_proc_rznp_send_mem: Failed to write '
                           'LAN_TO_HOST pkt to port: errno = %d' % e.errno)
        del pkt # GC NOW

    def _proc_rzhs_send_mem(self, pkt):
        self.debug_print(1, 'processing RZHostSlave LAN_SEND_MEM')
        a_ext_len = pkt[RZHM_DATA_1ST : RZHM_DATA_LAST + 1]
        # obtain the extension length (unpack yields a one-elem tuple)
        ext_len = struct.unpack('<H', a_ext_len)[0]
        if self.debug_lvl >= 1:
            print 'ext_len = 0x%04x' % ext_len
        if ext_len != 6:
            # all LAN_SEND_MEM pkts have exactly 6 bytes in extension
            self.debug_print(0,
                             'recvd LAN_SEND_MEM has wrong length. Want 6,'
                             ' Is %d', ext_len)
        # obtain the "mem addr" (unpack yields a one-elem tuple)
        mem_addr = struct.unpack('<H', pkt[10:12])[0]
        if self.debug_lvl >= 1:
            print 'mem_addr = 0x%04x' % mem_addr
        mem_page = pkt[12]
        if self.debug_lvl >= 1:
            print 'mem_page = 0x%04x' % mem_page
        # obtain num bytes to read (unpack yields a one-elem tuple)
        num_bytes = struct.unpack('<H', pkt[13:15])[0]
        if self.debug_lvl >= 1:
            print 'num_bytes = 0x%04x' % num_bytes

        ext = self._form_send_mem_response_ext(mem_addr, mem_page, num_bytes)
        if ext != None:
            rsp_pkt = form_slave_pkt(ext)
            self._dskt_sendall(rsp_pkt.tostring(), 10)
        del pkt # GC NOW

    def _proc_rzhs_to_mem(self, pkt):
        # example packet:
        #     16 01 FF FF FF FF 05 LL 00 CKSUM 20 40 8C 00/01 CKSUM
        # if the packet is addressed to the default modem server (0xFFFFFFFF)
        # (NOT broadcast) and the address of the data is: 0x4020 on page 0x8C
        # then: 
        #     if the value is a single byte of 0 then:
        #         prune all nodes below this rznet peer
        #     else if the value is a single byte of 1 then:
        #         read the xpoints.net file and create a new branch of nodes
        #         and start them
        ignore_pkt = False
        # Low 24 bits of address.
        dest_addr24 =  pkt[2:5].tostring()
        if dest_addr24 == "\xff\xff\xff":
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB, "pkt[2:6]: %r" % pkt[2:6])
            self._proc_ACK(pkt)
        else:
            b_my_addr24 = form_long(self._rznp_addr)[0:3]
            if (b_my_addr24[0] == ord(dest_addr24[0]) and
                b_my_addr24[1] == ord(dest_addr24[1]) and
                b_my_addr24[2] == ord(dest_addr24[2])):
                self._proc_ACK(pkt)
            else:
                if self.debug_lvl >= 2:
                    msglog.log("mpx:rz", DB,
                               "My address: XX %0X %0X %0X\n"
                               "  No LAN_TO_MEM ACK for dest XX %0X %0X %0X" %
                               (b_my_addr24[2], b_my_addr24[1], b_my_addr24[0],
                                pkt[4], pkt[3], pkt[2]))
                ignore_pkt = True
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB, "pkt[2:6]: %r" % pkt[2:6])
        if len(pkt) < 14:
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB, "len(pkt): %r" % len(pkt))
            ignore_pkt = True
        elif pkt[10:13].tostring() != "\x20\x40\x8c":
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB, "pkt[10:13]: %r" % pkt[10:13])
            ignore_pkt = True
        elif pkt[13] not in (0,1):
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB, "pkt[13]: %r" % pkt[13])
            ignore_pkt = True
        if ignore_pkt:
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB,
                           "_proc_rzhs_to_mem: Ignoring packet:\n%s ..." %
                           dump_tostring(pkt[0:32]))
            return
        action = pkt[13]
        if action == 0:
            self._rzhs_to_mem_stop_application()
        elif action == 1:
            self._rzhs_to_mem_start_application()
        else:
            raise EUnreachableCode()
        return
    def _rzhs_to_mem_stop_application_callback(self):
        if self.debug_lvl >= 2:
            msglog.log("mpx:rz", DB,
                       "_rzhs_to_mem_stop_application_callback()")
        try:
            application_parent = self._application_parent
            for application_node in application_parent.children_nodes():
                if self.debug_lvl >= 2:
                    msglog.log("mpx:rz", DB,
                               "  pruning: %r" %
                               application_node.as_node_url())
                application_node.prune(True)
        except:
            msglog.exception()
        return
    def _rzhs_to_mem_stop_application(self):
        if self.debug_lvl >= 2:
            msglog.log("mpx:rz", DB, "_rzhs_to_mem_stop_application()")
        self._application_running = 0
        self._command_q.queue_noresult(
            self._rzhs_to_mem_stop_application_callback
            )
        return
    def _rzhs_to_mem_start_application_callback(self):
        #this is only used by legacy application that live under a com port instead of the control service
        if self.debug_lvl >= 2:
            msglog.log("mpx:rz", DB,
                       "_rzhs_to_mem_start_application_callback()")
        try:
            application_parent = self._application_parent
            if self.debug_lvl >= 2:
                msglog.log("mpx:rz", DB, "  discover_children: %r" %
                           application_parent.as_node_url())
            application_parent.discover_children()
            for application_node in application_parent.children_nodes():
                if self.debug_lvl >= 2:
                    msglog.log("mpx:rz", DB, "  starting: %r" %
                               application_node.as_node_url())
                application_node.start()
        except:
            msglog.exception()
        return
    def _rzhs_to_mem_start_application(self):
        if self.debug_lvl >= 2:
            msglog.log("mpx:rz", DB, "_rzhs_to_mem_start_application()")
        if self._application_parent.parent.as_node_url() != '/services/control':
            self._command_q.queue_noresult(
                self._rzhs_to_mem_start_application_callback
                )
        #else not needed since control service should do this instead
        self._application_running = 1
        return
    def _proc_rzhs_token_list(self, pkt):
        self._internal_lock.acquire()
        try:
            self.debug_print(1, 'processing LAN_TOKEN_LIST')

            self._get_node_list() # recreate local node list from ldisc
            b_mem_nodes = form_short(RZNET_MEM_NODE_LIST)
            b_my_addr = form_long(self._rznp_addr)
            ext = array.array('B', [len(self._nodes_list), 0,
                                    b_mem_nodes[0], b_mem_nodes[1],
                                    2, b_my_addr[0], b_my_addr[1],
                                    b_my_addr[2],  b_my_addr[3],
                                    0,0,0,0,0,0,0,0])

            pkt = form_slave_pkt(ext)
            self._dskt_sendall(pkt.tostring(), 10)
            del pkt # GC NOW
        finally:
            self._internal_lock.release()

    def _proc_rzhs_AML(self, pkt):
        global REPORT_LIST_NAME
        self._internal_lock.acquire() # protect pt data cache
        try:
            if self.debug_lvl >= 1:
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
                        if self.log_interesting_cmls or self.debug_lvl >= 2:
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
                    if self.debug_lvl >= 2:
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
                        if self.debug_lvl >= 2:
                            msglog.log('mpx:rz',DB,
                                       '_proc_rzhs_AML: '
                                       'Added %d, %d to new pkt array' %
                                       (lan_addr, obj_id))
                    else:
                        # Enough room in existing array:
                        aml_exts_dict[lan_addr].extend(a)
                        if self.debug_lvl >= 2:
                            msglog.log('mpx:rz',DB,
                                       '_proc_rzhs_AML: '
                                       'Added %d, %d to end of extant array' %
                                       (lan_addr, obj_id))
                else:
                    # init new array and add to dict and to list:
                    aml_exts_dict[lan_addr] = a
                    aml_exts_list.append((lan_addr, a))
                    if self.debug_lvl >= 2:
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
                rznet_pkt = form_net_pkt(lan_addr, LAN_AML, 0,
                                         t_ext[1], PKTFL_NO_BCAST_RESP)
                try:
                    rznet_pkt.tofile(self._file_rznp) # send pkt to ldisc
                    if self.debug_lvl >= 1:
                        msglog.log('mpx:rz',DB,
                                   '_proc_rzhs_AML:Sent AML pkt to RZNet,'
                                   ' to %d' % lan_addr)
                    # Because it works; else, target RZ Controller can get
                    # confused:
                    time.sleep(2.0)
                except IOError, e:
                    msglog.log('broadway',ERR,'_proc_rzhs_AML: '
                               'Failed to write LAN_AML pkt to port: '
                               'errno = %d' % e.errno)
            # Form and send an ACK pkt back to PhWin:
            ack_ext = array.array('B', [0x06])
            ack_pkt = form_slave_pkt(ack_ext)
            try:
                self._dskt_sendall(ack_pkt.tostring(), 10)
            except:
                msglog.log('broadway',ERR,'_proc_rzhs_AML: Failed to write '
                           'LAN_TO_HOST ACK pkt to data socket.')
                msglog.exception()
            del pkt # GC NOW
        finally:
            self._internal_lock.release()
        return

    def _proc_rzhs_CML(self, pkt):
        global REPORT_LIST_NAME
        # If pkt was addressed to Default Modem Server, then it's intended for
        # re-"broadcast". However, since other (HTML) clients might still be
        # listening for values from the RZNet, we must walk the
        # known-subscribed nodes and unsubscribe only those that PhWin
        # alone is watching:
        a_dst_addr = pkt[RZHM_DST_1ST : RZHM_DST_LAST + 1]
        # strip off possible seq num
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
        self._internal_lock.acquire()
        try:
            # Need to send ACK to PhWin, even though it's not the broadcast
            # ACK that PhWin thinks it should be...:
            ack_ext = array.array('B', [0x06])
            ack_pkt = form_slave_pkt(ack_ext)
            try:
                self._dskt_sendall(ack_pkt.tostring(), 10)
            except:
                msglog.log('broadway',ERR,'_proc_rzhs_CML: Failed to write '
                           'LAN_TO_HOST ACK pkt to data socket.')
            del pkt # GC NOW
        finally:
            self._internal_lock.release()
        return

    def _proc_rzhs_REPORT(self, pkt):
        global REPORT_LIST_NAME
        self._internal_lock.acquire() # protect pt data cache
        try:
            a_ext_len = pkt[RZHM_DATA_1ST : RZHM_DATA_LAST + 1]
            # obtain the extension length (unpack yields a one-elem tuple)  any
            # lenght greater than 0 indicates retry request
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
                rsp_pkt = form_slave_pkt(upd_ext)
                self._last_response_pkt = rsp_pkt
            else:
                self.debug_print(1, 'rzhs retry for REPORT')
            try:
                self._dskt_rzhs.sendall(self._last_response_pkt.tostring(), 10)
            except:
                msglog.log('mpx:rz',ERR,'_proc_rzhs_REPORT: Failed to write '
                           'LAN_TO_HOST pkt to data socket.')
                msglog.exception()
            del pkt # decr ref count
        finally:
            self._internal_lock.release()

    def _proc_rzhs_ALARMS(self, pkt):
        # Return default, trivial response to request for Alarms:
        triv_ext = array.array('B', [0x02])
        triv_pkt = form_slave_pkt(triv_ext)
        try:
            self._dskt_sendall(triv_pkt.tostring(), 10)
        except:
            msglog.log('broadway',ERR,'_proc_rzhs_ALARMS: Failed to write '
                       'LAN_TO_HOST trivial pkt to data socket.')
            msglog.exception()
        del pkt # GC NOW

    def _subscr_scan(self, clr_phwin = 0):
        self.debug_print(1, 'Scanning for unrequested points to unsubscribe.')
        # disable all other accessors while we play with the points dict
        self._internal_lock.acquire()
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
                            if (self.log_interesting_cmls
                                or self.debug_lvl >= 2):
                                msglog.log('mpx:rz',DB,
                                           '_subscr_scan (CML): '
                                           'Added (%d,%d) to new pkt array'
                                           % (dst_addr, obj_id))
                        else:
                            # Enough room in existing array:
                            cml_exts_dict[dst_addr].extend(
                                form_addr_obj_id_array(dst_addr, obj_id)
                                )
                            if (self.log_interesting_cmls
                                or self.debug_lvl >= 2):
                                msglog.log('mpx:rz',DB,
                                           '_subscr_scan (CML): '
                                           'Added (%d,%d) to extant pkt array'
                                           % (dst_addr, obj_id))
                    else:
                        # Add a new array to dict and to list:
                        a = form_addr_obj_id_array(dst_addr, obj_id)
                        cml_exts_dict[dst_addr] = a
                        cml_exts_list.append((dst_addr, a))
                        if self.log_interesting_cmls or self.debug_lvl >= 2:
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
                pkt = form_net_pkt(dst_addr, LAN_CML, 0, ext,
                                   PKTFL_NO_BCAST_RESP)
                try:
                    pkt.tofile(self._file_rznp) # send pkt to ldisc
                    if self.log_interesting_cmls or self.debug_lvl >= 2:
                        msglog.log('mpx:rz',DB,
                                   '_subscr_scan:Sent CML pkt to RZNet, to %d'
                                   % dst_addr)
                except IOError, e:
                    msglog.log('broadway',ERR,'_subscr_scan: Failed to write '
                               'LAN_CML pkt to port: errno = %d' % e.errno)
                    msglog.exception()
        finally:
            self._internal_lock.release() # re-enable accessors
        return

    # Allow other threads to send commands that can interrupt and control this
    # thread SAFELY, via the integral cmd socket pair (near/far):
    def _send_cmd(self, cmd):
        self._internal_lock.acquire() # disable access to members
        try:
            self._far_cmd_skt.send(cmd) # cmd will emerge at the _near_cmd_skt
        finally:
            self._internal_lock.release() # re-enable access to members

    def _get_addrs(self):
        # Get own and next addresses from RS485 dev file:
        str_addrs = 8 * '\0'
        str_addrs = fcntl.ioctl(self._fd_rznp, RZNET_IOCGADDRS, str_addrs)
        self._rznp_addr, self._rznp_next_addr = struct.unpack(2 * 'I',
                                                              str_addrs)
        self.debug_print(
            1,
            'Read addrs from rznet ldisc ioctl. Own = %08x. Next = %08x.',
            self._rznp_addr, self._rznp_next_addr
            )
    def get_addrs(self): # externally-usable wrapper for _get_addrs()
        self._get_addrs() # update addrs from ldisc
        return (self._rznp_addr, self._rznp_next_addr)

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
        if self.debug_lvl > 1:
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
        if msg_lvl <= self.debug_lvl:
            if args:
                msg = msg % args
            prn_msg = 'RznetThread: ' + msg
            print prn_msg
        return

if __name__ == '__main__':
    print 'Starting unit test in rznet_line_handler.py...'

    float_val0 = -10e32
    print 'float_val0 = %0.10e' % float_val0
    ht_val = float_to_HiTech(float_val0);
    float_val1 = HiTech_to_float(ht_val.tostring());
    print 'float_val1 = %0.10e' % float_val1

    """
    rzlh = RznetLineHandler(None)
    for i in range(20):
        dst_addr = 0x1000
        obj_id = i
        p = Point(dst_addr, obj_id)
        p.reqd = 1
        rzlh._mon_pts[(dst_addr, obj_id)] = p # - init caching by adding dict
                                              #   entry for this point
    print '_mon_pts dict:'
    for k in rzlh._mon_pts.keys():
        print '(%04x,%04x)' % (k)
    rzlh._subscr_scan()
    """
    print 'Unit test in rznet_line_handler.py complete.'

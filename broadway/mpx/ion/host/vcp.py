"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
# Serial port tunneling implementation.
#
import os
import struct
import array
import select
import time

from port import Port

from mpx.lib import socket
from mpx.lib import ReloadableSingletonFactory

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.threading import Lock
from mpx.lib.threading import currentThread
from mpx.lib.threading import ImmortalThread

from mpx.lib.exceptions import EResourceError
from mpx.lib.exceptions import ETimeout
from mpx.lib.exceptions import MpxException

from mpx.lib.node import CompositeNode

from mpx.lib import msglog
from mpx.lib.msglog.types import WARN
from mpx.lib.msglog.types import ERR
from mpx.lib.msglog.types import INFO

class ERestart(MpxException):
    pass
    
class ESegmentError(MpxException):
    pass
    
PTY_DEVS = None
module_lock = Lock()
##
# The ION that manages a group of virtual com ports and is responsible
# for pty allocation
#
class TunnelManager(CompositeNode):
    def __init__(self, *args):
        global PTY_DEVS
        self._lock = Lock()
        self._pty_devs = []
        self._ptys_allocated = 0
        module_lock.acquire()
        try:
            if PTY_DEVS is None:
                PTY_DEVS = []
                for major in 'wxyz':
                    for minor in '0123456789abcdef':
                        PTY_DEVS.append('/dev/pty%s%s' % (major, minor))
        finally:
            module_lock.release()
            
    def configure(self, config):
        # vcp_limit is a "hidden" attribute.
        set_attribute(self, 'vcp_limit', 64, config, int)
        CompositeNode.configure(self, config)
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'vcp_limit', config, str)
        return config
    
    ##
    # Allocate a pseudo-terminal for use by the Port object.
    #
    # @return a string, ie. /dev/ptyr0. 
    def get_pty(self):
        global PTY_DEVS
        self._lock.acquire()
        try:
            while len(PTY_DEVS):
                pty = PTY_DEVS.pop()
                try:
                    # confirm that the pty is accessible.
                    fd = open(pty)
                    fd.close()
                    self._ptys_allocated += 1
                    return pty
                except:
                    pass
            raise EResourceError
        finally:
            self._lock.release()
        
##
#  The ION that represents a virtual com port (vcp) on a host.
#
class Vcp(Port):
    def __init__(self, *args):
        super(Vcp, self).__init__(*args)
        self._tcp_tunnel = None
        self._dev = None
        self._opened = False
    ##
    # Configure a vcp instance.
    #
    # @param config The port's configuration dictionary.
    # @key 'name' The name to associate with the Port.
    # @required
    # @key 'parent' The parent ION (typically '/interfaces/virtuals').
    # @required
    # @key 'baud' Set the baud rate to the specified value.
    # @defualt 9600
    # @key 'tcp_port' The TCP port to bind to
    # @default 5000
    # @key 'is_server' The mode the tunnel should be operating in.
    # @default 0
    # @key 'host' The host we are connecting to - if in client mode
    # @required
    # @key 'debug' Echo data read and written to standard out in a human
    #              readable format.
    # @default 0
    def configure(self, config):
        set_attribute(self, 'baud', 9600, config, str)
        set_attribute(self, 'tcp_port', 5000, config, int)
        set_attribute(self, 'mode', 'vcp', config, str)
        set_attribute(self, 'is_server', 0, config, int)
        set_attribute(self, 'p_timeout_msec', -1, config, int)
        if not self.is_server:
            set_attribute(self, 'host', REQUIRED, config)
        if not self._tcp_tunnel:
            self._tcp_tunnel = TcpTunnel(self)
        # note use of property to access dev to resolve super's configure() 
        super(Vcp, self).configure(config)
        config['dev'] = self.dev # added to config Dictionary for the benefit of the TCP Tunnel
        if not config.get('mode'):
            # add mode for _tcp_tunnel.configure
            config['mode'] = self.mode
        if not config.get('p_timeout_msec'):
            config['p_timeout_msec'] = self.p_timeout_msec
        self._tcp_tunnel.configure(config)
        if not self._tcp_tunnel.isAlive():
            self._tcp_tunnel.start()
        
    ##
    # Returns a dictionary of the vcp's attributes
    #
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = super(Vcp, self).configuration()
        get_attribute(self, 'baud', config)
        get_attribute(self, 'tcp_port', config, str)
        get_attribute(self, 'mode', config, str)
        if not self.is_server:
            get_attribute(self, 'host', config)
        # include tunnel statistics in configuration() response.
        if self._tcp_tunnel:
            config['tcp_bytes_rcvd'] = self._tcp_tunnel.tcp_bytes_rcvd
            config['tcp_bytes_sent'] = self._tcp_tunnel.tcp_bytes_sent
            config['serial_bytes_rcvd'] = self._tcp_tunnel.serial_bytes_rcvd
            config['serial_bytes_sent'] = self._tcp_tunnel.serial_bytes_sent
            config['connection_attempts'] = self._tcp_tunnel.connection_attempts
        return config
        
    ##
    # Open the port for read/write access and start the TCP tunnel.
    #
    # @todo Add a timeout to the open for acquiring the lock.
    #
    def open(self, blocking=0):
        super(Vcp, self).open(blocking)
        self._opened = True
        self._tcp_tunnel.start_tunnel()
        
    ## 
    # Close the port and disconnect the TCP connection.
    #
    def close(self):
        self._opened = False
        self._tcp_tunnel.stop_tunnel()
        super(Vcp, self).close()
        
    ##
    # Write a string or array to the serial port - iff TCP connection is
    # in connected state.
    #
    def write(self, buffer):
        if self.is_connected():
            super(Vcp, self).write(buffer)
        elif self._opened:
            self._tcp_tunnel.start_tunnel()
            super(Vcp, self).write(buffer)
        else:
            # still display debugging information
            if self.debug:
                print 'Port.write(self, buffer):'
                self.dump(buffer, ' > ')
    ##
    #Return connection status of tunnel
    #
    def is_connected(self):
        try:
            return self._tcp_tunnel.is_connected()
        except:
            pass
        return False
    
    def get(self):
        if self.is_connected():
            return 'connected'
        return 'not connected'
    
    def __get_dev(self):
        if not self._dev:
            self._dev = self.parent.get_pty()
        return self._dev
        
    dev = property(__get_dev)
    
READ = 0
WRITE = 1
class TcpTunnel(ImmortalThread):
    def __init__(self, vcp):
        #super(TcpTunnel, self).__init__(self)
        ImmortalThread.__init__(self)
        self._needs_reconfig = 0
        # link to the port object
        self._vcp = vcp
        self._lock = Lock()
        self._op_lock = Lock()
        # list of operations to apply to an {out|in}bound tcp 
        # segment. In the future this might include operations 
        # such as encryption or compression - for now, only the
        # header info. that is applied by devices such as 
        # Lantronix's UDS-10 is supported.  Up refers to what is
        # being applied to outbound tcp data, down to received.
        # Methods should be added to these lists in the order they
        # are to be applied.
        self._up_segment_ops = []
        self._down_segment_ops = []
        # transaction identifier - used only in vcp mode.
        self.__tid = 0
        self._pending_tid = 0
        # one and only poll object.  socket, serial fd and
        # command pipe are all polled.
        self._poll_obj = None
        # command pipe allows other threads to insert control
        # messages.
        self._cmd_pipe = None
        # both sides (serial & socket) of the tunnel
        self._sock_listen_fd = None
        self._sock_fd = None
        self._serial_port = None
        # tcp state management
        self._is_connected = 0
        self.is_active = 0
        # tunnel statistics
        self.tcp_bytes_rcvd = 0
        self.tcp_bytes_sent = 0
        self.serial_bytes_rcvd = 0
        self.serial_bytes_sent = 0
        self.connection_attempts = 0
            
    def configure(self, config):
        self.tty = '/dev/tty' + config['dev'][-2:]
        self.tcp_port = int(config['tcp_port'])
        self.mode = config['mode']
        self.timeout_msec = config['p_timeout_msec']

        if self.mode == 'vcp':
            if self._up_segment_ops.count(self._add_vcp_header) == 0:
                self._up_segment_ops.append(self._add_vcp_header)
            if self._down_segment_ops.count(self._remove_vcp_header) == 0:
                self._down_segment_ops.append(self._remove_vcp_header)
        self.is_server = int(config['is_server'])
        if self.is_server == 0:
            self.host = config['host']  # who we're connecting to.
        if self.is_active:
            # tunnel is being reconfigured "in flight".
            self._needs_reconfig = 1
            self._send_cmd('reconfig')
            if self._is_in_accept():
                self._clear_accept()
                    
    def run(self):
        self._needs_reconfig = 0
        if self.is_active:
            # we've restarted due to a configuration change
            self.start_tunnel()
        else:
            if not self._cmd_pipe:
                # set up the command pipe and begin to build the poll obj.
                self._cmd_pipe = os.pipe()
                self._poll_obj = select.poll()
                self._poll_obj.register(self._cmd_pipe[READ],
                    select.POLLIN | select.POLLERR | select.POLLHUP)
        while 1:
            # no poll timeout, wait here until kicked to start.
            evt = self._poll_obj.poll(-1)
            if evt[0][0] == self._cmd_pipe[READ]:
                if evt[0][1] == select.POLLIN:
                    cmd = os.read(self._cmd_pipe[READ], 32)
                    if cmd.find('start') >= 0:
                        self.start_tunnel()
            # cmd pipe poll err, critical, hard restart
            self._cmd_pipe = None
            self._poll_obj = None
            raise ERestart()
                        
    def start_tunnel(self):
        if self is not currentThread():
            self._send_cmd('start')
            return
        self._op_lock.acquire()
        try:
            self.is_active = 1
            # set up Port object for the tunnel that reads\writes to the 
            # slave device file of the pseudo-terminal pair. 
            if not self._serial_port:
                self._serial_port = Port()
            cfg = self._vcp.configuration()
            cfg['dev'] = self.tty
            cfg['name'] = '_slave'
            cfg['parent'] = self._vcp
            self._serial_port.configure(cfg)
            self._op_lock.release()
        except:
            self._op_lock.release()
        while self.is_active:
            if not self._serial_port.is_open():
                self._serial_port.open()
                self._serial_port.drain()
            try:
                if self.is_server:
                    self._do_listen()
                else:
                    self._do_connect()
            except:
                msglog.exception()
                if self._serial_port and not self._serial_port.is_open():
                    self._serial_port.close()

    def stop_tunnel(self):
        self.is_active = 0
        if self is not currentThread():
            self._send_cmd('stop')
            if self._is_in_accept():
                self._clear_accept()
        else:
            self._op_lock.acquire()
            try:
                self._tear_down_fds()
            finally:
                self._op_lock.release()
            #raise ERestart()
        
    def is_connected(self):
        self._op_lock.acquire()
        result = self._is_connected
        self._op_lock.release()
        return result
                                
    def _create_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s
            
    def _close_socket(self):
        self._is_connected = 0
        self._sock_fd.close()
            
    def _send_cmd(self, cmd):
        self._lock.acquire()
        try:
            os.write(self._cmd_pipe[WRITE], cmd)
        finally:
            self._lock.release()
            
    def _do_connect(self):
        while self.is_active:
            self._sock_fd = self._create_socket()
            while not self._is_connected:
                self.connection_attempts += 1
                try:
                    self._sock_fd.connect((self.host, self.tcp_port))
                    self._is_connected = 1
                except socket.gaierror, e:
                    # host related error, ie. hostname not resolving - possibly transient
                    self.connection_attempts += 1
                    msglog.log('VCP', WARN, 'Error resolving hostname %s.' % self.host)
                    time.sleep(60)
                    raise EConnectionError
                except socket.error, e:
                    # connection error, possibly transient - sleep for a bit and retry
                    self.connection_attempts += 1
                    time.sleep(30) 
            if self._needs_reconfig:
                self._is_connected = 0
                self._tear_down_fds()
                raise ERestart()
            # loop in _do_tunnel until the tcp connection or the framework 
            # based consumer (ie. protocol) "goes away".
            self._do_tunnel()
            self._is_connected = 0
            
    def _do_listen(self):
        if not self._sock_listen_fd:
            self._sock_listen_fd = self._create_socket()
            linger = struct.pack('ii', 1, 0)
            self._sock_listen_fd.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
            self._sock_listen_fd.bind(('', self.tcp_port))
            self._sock_listen_fd.listen(1)
        while self.is_active:
            while not self._is_connected:
                self.connection_attempts += 1
                self._sock_fd, addr = self._sock_listen_fd.accept()
                if self._vcp.debug:
                    msglog.log('VCP', INFO, 'Accepted connection.')
                self._is_connected = 1
            if self._needs_reconfig:
                self._is_connected = 0
                self._tear_down_fds()
                raise ERestart()
            # loop in _do_tunnel until the tcp connection or the framework 
            # based consumer (ie. protocol) "goes away".
            self._do_tunnel()
            self._is_connected = 0
        
    def _do_tunnel(self):
        MAX_READ = 512
        self._poll_obj.register(self._serial_port.file.fileno(),
            select.POLLIN | select.POLLERR | select.POLLHUP)
        self._poll_obj.register(self._sock_fd.fileno(),
            select.POLLIN | select.POLLERR | select.POLLHUP)
        while self.is_active:
            poll_evts = self._poll_obj.poll(self.timeout_msec)
            if not len(poll_evts):
                break
            # if there are multiple pending events, evaluate them in the order
            # cmd pipe, serial followed by socket.
            for fd in (self._cmd_pipe[READ], self._serial_port.file.fileno(), 
                self._sock_fd.fileno()):
                evt = self._get_poll_event(fd, poll_evts)
                if not evt:
                    continue
                if evt[0] == self._cmd_pipe[READ]:
                    if evt[1] == select.POLLIN:
                        cmd = os.read(evt[0], 32)
                        if cmd.find('stop') >= 0:
                            self.stop_tunnel()
                        else:
                            self._tear_down_fds()
                            raise ERestart()
                    else:
                        # cmd pipe error - completely tear down and restart
                        self._tear_down_fds()
                        self._poll_obj = None
                        self._cmd_pipe = None
                        msglog.log('VCP', ERR, 'Command pipe error - restarting service.')
                        raise ERestart()
                elif evt[0] == self._serial_port.file.fileno():
                    if evt[1] == select.POLLIN:
                        buff = array.array('B')
                        try:
                            self._serial_port.read(buff, MAX_READ, .025)
                        except ETimeout:
                            pass #shouldn't happen
                        data = buff.tostring()
                        del buff
                        self.serial_bytes_rcvd += len(data)
                        data = self._segment_run_up(data)
                        try:
                            self._sock_fd.send(data)
                        except socket.error, e:
                            self._close_socket()
                            return
                        self.tcp_bytes_sent += len(data)
                    else:
                        self._tear_down_fds()
                        raise ERestart()
                elif evt[0] == self._sock_fd.fileno():
                    if evt[1] == select.POLLIN:
                        buff = array.array('B')
                        try:
                            data = self._sock_fd.recv(MAX_READ)
                        except socket.error, e:
                            # error reading socket
                            self._close_socket()
                            msglog.log('VCP', WARN, 'Error reading socket.')
                            return
                        if data == '':
                            # broken connection
                            self._close_socket()
                            msglog.log('VCP', WARN, 'Broken socket on read.')
                            return
                        self.tcp_bytes_rcvd += len(data)
                        try:
                            data = self._segment_run_down(data)
                        except ESegmentError:
                            msglog.log('VCP', WARN, 'Error running down segment options.')
                            continue
                        buff.fromstring(data)
                        self._serial_port.write(buff)
                        self.serial_bytes_sent += len(buff)
                        del buff
                    else:
                        self._close_socket()
                        return
        self.stop_tunnel()
        
    def _tear_down_fds(self):
        if not self._serial_port.is_open():
            try:
                self._poll_obj.unregister(self._serial_port.file.fileno())
            except:
                pass
            self._serial_port.close()
        if self._sock_fd:
            try:
                self._poll_obj.unregister(self._sock_fd.fileno())
            except:
                pass
            self._close_socket()
        if self._sock_listen_fd:
            self._sock_listen_fd.close()
            self._sock_listen_fd = None
                
    def _segment_run_up(self, data):
        for segment_op in self._up_segment_ops:
            data = segment_op(data)
        return data
            
    def _segment_run_down(self, data):
        for segment_op in self._down_segment_ops:
            data = segment_op(data)
        return data
            
    def _add_vcp_header(self, data):
        hdr = ''
        if self.is_server:
            hdr = struct.pack('5B', 0xaa, 0xaa, 0x27, 0xb7, 0x00)
            hdr += struct.pack('B', len(data))
            hdr += struct.pack('B', self._pending_tid)
        else:
            hdr = struct.pack('5B', 0x00, 0x00, 0x14, 0xb7, 0x00)
            hdr += struct.pack('B', len(data))
            self._pending_tid = self._tid
            hdr += struct.pack('B', self._pending_tid)
        return hdr + data
            
    def _remove_vcp_header(self, data):
        soh_hi, soh_lo = struct.unpack('2B', data[0:2])
        soh = soh_hi << 8 | soh_lo
        bytes_expected = struct.unpack('B', data[5])[0] + 7
        if self.is_server:
            if soh != 0x0000 or len(data) != bytes_expected:
                msglog.log('VCP', WARN, 'Error removing VCP header.')
                raise ESegmentError()
            self._pending_tid = struct.unpack('B', data[6])[0]
        else:
            if soh != 0xaaaa or len(data) != bytes_expected or \
                self._pending_tid != struct.unpack('B', data[6])[0]:
                tid = struct.unpack('B', data[6])[0]
                msglog.log('VCP', WARN, 'Error removing VCP header.')
                raise ESegmentError()
        return data[7:]
            
    def _is_in_accept(self):
        if self.is_server and self.is_active and \
            self._is_connected == 0:
            return True
        else:
            return False
            
    # Prevents thread from continuously blocking in accept. 
    def _clear_accept(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', self.tcp_port))
            s.close()
        except:
            pass
            
    def _get_poll_event(self, fd, poll_evts):
        for evt in poll_evts:
            if evt[0] == fd:
                return evt
        return None
            
    def __increment_tid(self):
        if self.__tid >= 0xff:
            self.__tid = 0
        else:
            self.__tid += 1
        return self.__tid
            
    _tid = property(__increment_tid)
            
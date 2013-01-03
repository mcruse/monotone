"""
Copyright (C) 2002 2004 2010 2011 Cisco Systems

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
import array, time
from mpx.lib import socket
from mpx.lib.debug import _debug
from mpx.lib.threading import ImmortalThread, Thread, Lock, EKillThread
from mpx.lib import msglog

GlobalState = 0
debug = 0

class _TcpConnection:
    def __init__(self, socket=None, timeout=None):
        self.socket = socket
        self.debug = debug
        self.timeout = timeout
    def is_connection_request(self):
        pass
    def open_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    def close_connection(self):
        if self.socket:
            self.socket.close()
    def is_established_connection(self):
        return not self.socket._closedsocket
    def read(self, count=1024):
        if debug:
            print 'Read from socket: ', count, self.socket
        answer = self.socket.recv(count, self.timeout)
        if debug:
            print 'Got from socket:'
            _debug.dump(answer, 'Read from socket')
        return answer
    def write(self, buffer):
        if debug:
            _debug.dump(buffer, 'TcpConnection write bytes: ')
        self.socket.send(buffer, self.timeout)
    def read_MBAP(self):
        if debug: print 'TcpConnection read MBAP'
        mbap = self.read(6)
        if debug: print 'TcpConnection has read MBAP', mbap
        if mbap:
            return MBAP(decode=mbap)
        return None

class TcpServerConnection(_TcpConnection):
    def __init__(self, ip, port, device_server):
        _TcpConnection.__init__(self)
        self.ip = ip
        self.port = port
        self.device_server = device_server #node
        self.server_thread=_ServerThread(self) #start the main server thread
        self.server_thread.start()

    def open_connection(self):
        _TcpConnection.open_connection(self)
        self.set_reuse_addr()
        self.socket.bind((self.ip, self.port))

    def accept_connection(self):
        self.socket.listen(1)
        conn, addr = self.socket.accept()
        if debug: print 'accept_connection to: ', addr, conn
        c = _TcpConnection(conn)
        return c

    def set_reuse_addr (self):
        # try to re-use a server port if possible
        try:
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,self.socket.getsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR)|1)
        except socket.error:
            print 'failed to reuse socket'
            pass
    def ready(self): #answer true if server thread is ready to rock and roll
        return self.server_thread.ready
    
class TcpClientConnection(_TcpConnection):
    def __init__(self, ip, port=502, timeout=1.0):
        _TcpConnection.__init__(self, None, timeout)
        self.ip = ip
        self.port = port
    def open_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #, self.timeout)
        answer = self.socket.connect((self.ip, self.port), self.timeout)
        return answer
        
_mbap_str = """\
MBAP:
  transaction_id:    %s
  protocol_id:       %s
  length:            %s"""

class MBAP:
    def __init__(self, *args, **keywords):
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif len(args) == 2:
            self.encode(args[0], args[1], _transaction_id())
        elif len(args) == 3:
            self.encode(args[0], args[1], args[2])
        else:
            raise ETypeError('requires length unit_id [transaction_id] or decode')
    def __str__(self):
        global _mbap_str
        result = _mbap_str % (self.transaction_id, 
                              self.protocol_id,
                              self.length)
        return result
    def encode(self, length, unit_id, transaction_id):
        self.transaction_id = transaction_id
        self.protocol_id = 0
        self.length = length
        self.unit_id = unit_id
        self._update_encoding()
    def _update_encoding(self):
        self.encoding = chr((self.transaction_id >> 8) & 0xff) + \
                        chr(self.transaction_id & 0xff) + \
                        chr((self.protocol_id >> 8) & 0xff) + \
                        chr(self.protocol_id & 0xff) + \
                        chr((self.length >> 8) & 0xff) + \
                        chr(self.length & 0xff) # + \
                        #chr(self.unit_id)
    def decode(self, buffer):
        self.encoding = buffer
        buffer = array.array('B', buffer)
        if debug: print 'MBAP decode buffer: ', buffer
        self.transaction_id = buffer[0] * 256 + buffer[1]
        self.protocol_id = buffer[2] * 256 + buffer[3]
        self.length = buffer[4] * 256 + buffer[5]
        if debug: print 'MBAP : ', str(self)
        #self.unit_id = buffer[6]
    def is_message_header(self):
        if debug: print 'test MBAP for message header'
        if self.protocol_id != 0: return 0
        if self.length > 256: return 0
        if debug: print 'MBAP is message header!'
        return 1
    def get_message_length(self):
        return self.length
    def write_transaction_id(self, id):
        self.transaction_id = id
        self._update_encoding()
    def read_transaction_id(self):
        return self.transaction_id

_t_id = 0

def _transaction_id():
    _t_id += 1
    _t_id &= 0xFFFF
    return _t_id
#
# This thread listens to port 502 for modbus connect requests.
# When a connection is accepted, a new thread is spawned to
# handle requests until the socket is closed
#
class _ServerThread(ImmortalThread):

    def __init__(self, connection):
        ImmortalThread.__init__(self, name='MODBUS')
        self.connection = connection
        if debug: print 'init MODBUS Server '
        self.debug = debug
        self.ready = 0

    def reincarnate(self):
        msglog.log('broadway',msglog.types.INFO,
                    'MODBUS restarting\n')
        self.ready = 0
        self.connection.close_connection()

    def run(self):
        if debug: print '_MODBUS_Server: run'
        self.listen(self)

    def listen(self, thread): #called from immortal thread
        if self.debug: print 'open modbus tcpip listening port: ', self.connection.ip, self.connection.port
        try:
            self.connection.open_connection()
        except:
            print 'Unable to open listening port on: :', self.connection.port
            #thread.should_die()
            time.sleep(2)
            #raise EAlreadyRunning
        while self._continue_running:
            if self.debug: print 'wait for connection request'
            self.ready = 1
            new_conn = self.connection.accept_connection()
            if self.debug: print 'accept connection to : ', new_conn
            if self._continue_running:
                _ConnectionThread(new_conn, self.connection.device_server).start()
        if self.debug: print 'server thread stop listening'
        self.connection.close_connection()

def kill_a_server(server):
    ip = server.connection.ip
    port = server.connection.port
    server.should_die()
    #server.connection.close_connection()
    if debug: print 'close server for: ', ip, port
    cc = TcpClientConnection(ip,port)
    try:
        cc.open_connection()
    except:
        pass
    cc.close_connection()
    if debug: print 'test to see if server is still running'
    while server.isAlive():
        if debug: print 'waiting for thread to die'
        time.sleep(0.2)
    if debug: print 'should be closed now'

#
# This thread is spawed by the server thread that listens to port 502
# It loops on requests until the socket closes
# @todo use a thread pool to limit the number of threads created
# @todo use a timer to close inactive sockets
#
class _ConnectionThread(Thread):

    def __init__(self, connection, device_server):
        Thread.__init__(self, name='MODBUS')
        self.connection = connection
        self.device_server = device_server
        if debug: print 'init MODBUS Connection '
        self.debug = debug

    def run(self):
        if debug: print '_MODBUS_Server: run connection thread'
        try:
            self._process_connection()
            if debug: print '_ConnectionThread, end thread normally'
        finally:
            self.connection.close_connection()
            if debug: print '_ConnectionThread, connection closed'

    def _process_connection(self): #called from thread
        if self.debug: print 'process connection to : ', self.connection
        while 1: #self.connection.is_established_connection():
            if self.debug: print 'Wait for MBAP'
            try:
                mbap = self.connection.read_MBAP()
            except:
                if self.debug: print 'Peer closed connection'
                mbap = None
            if self.debug: print 'TcpIpServer, MBAP is: ', mbap
            if mbap is None:
                if self.debug: print 'TcpIpServer no MBAP, close connection'
                break
            if not mbap.is_message_header():
                if debug: print 'TcpIpServer is not message header'
                break
            if self.debug: print'TcpIpServer, read rest of command: ', mbap.length
            data = self.connection.read(mbap.length) #timeouts?
            if not data:
                if self.debug: print 'No data received, close connection and wait'
                break #connection closed, go wait for another
            if self.debug:
                print 'TcpIpServer, got command:'
                _debug.dump(data, 'command data')
            if len(data) != mbap.length:
                if self.debug: print 'TcpIpServer, did not get enough data'
                break
            if self.debug: print 'TcpIpServer, got data: ', len(data)
            response = None

            response = self.device_server.command(data)  #line handler will find the correct device node

            if response:
                if self.debug: 
                    print 'TcpIpServer, got resposne:'
                    _debug.dump(response.buffer, 'response')
                mbap.length = len(response.buffer)
                mbap._update_encoding()
                self.connection.write(mbap.encoding + response.buffer)
            else: #no response
                if self.debug: print 'TcpIpServer, no response to command!'
                break
    
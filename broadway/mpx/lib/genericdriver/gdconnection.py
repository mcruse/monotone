"""
Copyright (C) 2010 2011 Cisco Systems

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
import socket
import syslog
import threading
import array

import gdutil

# Required methods.
#  connect(numretries)
#  disconnect()
#  drain()
#  write()
#  read()
#  isConnected()
#  flush()

class BaseConnection:
    def __init__(self):
        self._connected = 0
        self.lock = gdutil.get_lock()
    #
    def isConnected(self):
        self.lock.acquire()
        try:
            return self._connected
        finally:
            self.lock.release()
    #
    def connect(self, numretries=1):
        self.lock.acquire()
        try:
            if self._connected:
                return 1
            else:
                ret =  self._connect(numretries)
                self._connected = 1
                return ret	
        finally:
            self.lock.release()
    #
    def disconnect(self):
        self.lock.acquire()
        try:
            if self._connected:
                ret =  self._disconnect()
                self._connected = 0
                return ret
        finally:
            self.lock.release()
    #
    def _connect(self, numretries):
        raise gdutil.GDException("Error - _connect must be implemented by subclass.")
    #
    def _disconnect(self):
        raise gdutil.GDException("Error - _disconnect must be implemented by subclass.")


class FrameworkSerialPortWrapper(BaseConnection):
    def __init__(self, port_node):
        self.port_node = port_node
        BaseConnection.__init__(self)
    #
    def drain(self):
        self.port_node.drain()
    #
    def flush(self):
        self.port_node.flush()
    #
    def _connect(self, numretries):
        return self.port_node.open()
    #
    def _disconnect(self):
        return self.port_node.close()
    #
    def write(self, data, timeout_secs):
        # Unfortunately the underlying serial port node does not (easily) support a
        # timeout on writing.
        return self.port_node.write(data)
    #
    def read(self, num_bytes, timeout_secs):
        buffer = array.array('B')

        st_time = gdutil.get_time()
        
        while len(buffer) < num_bytes:
            curtime = gdutil.get_time()
            if curtime - st_time > timeout_secs:
                raise gdutil.GDTimeoutException("Timeout reading data")

            bytes_read = self.port_node.read(buffer, num_bytes, timeout_secs)

            if len(buffer) == num_bytes:
                return buffer.tostring()

class BaseTCPSocketConnection(BaseConnection):
    def __init__(self, sock=None):
        if sock:
            self.sock = sock
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #
        BaseConnection.__init__(self)
    #
    def close(self):
        self.sock.close()
    #
    def drain(self):
        # @fixme: Possibly should check to make sure incoming buffer is drained.
        pass
    #
    def flush(self):
        # @fixme: Possibly should check to make sure outgoing buffer is flushed.
        pass
    #
    def write(self, msg, num_bytes, timeout_secs):
        st_time = gdutil.get_time()
        totalsent = 0
        while totalsent < num_bytes:
            # @fixme: Only send at most the appropriate number of remaining bytes
            #         (num_bytes - totalsent)
            curtime = gdutil.get_time()
            if curtime - st_time > timeout_secs:
                raise gdutil.GDTimeoutException("Timeout writing data")
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise gdutil.GDConnectionClosedException("Socket connection broken while writing")
            totalsent = totalsent + sent
            print 'totalsent', totalsent
    #
    def read(self, num_bytes, timeout_secs):
        st_time = gdutil.get_time()
        msg = ''
        while len(msg) < num_bytes:
            curtime = gdutil.get_time()
            if curtime - st_time > timeout_secs:
                raise gdutil.GDTimeoutException("Timeout reading data")
            chunk = self.sock.recv(num_bytes-len(msg))
            if chunk == '':
                raise gdutil.GDConnectionClosedException("Socket connection broken while reading")
            msg = msg + chunk
        return msg


class ClientTCPSocketConnection(BaseTCPSocketConnection):
    def __init__(self, ipaddr, port):
        self.ipaddr = ipaddr
        self.port = port
        #
        BaseTCPSocketConnection.__init__(self)
    #
    def _connect(self, numretries):
        return self.open()
    #
    def _disconnect(self):
        return self.close()
    #
    def open(self):
        self.sock.connect((self.ipaddr, self.port))

        # Set to non-blocking
        self.sock.setblocking(0)        
        

# Note: This class is mainly intended as an example and for unit tests, it probably
#       is not sufficient for a real TCP server which should handle multiple-
#       connections, etc.
class ServerTCPSocketConnection(BaseTCPSocketConnection):
    def __init__(self, eth_dev, port):
        self.eth_dev = eth_dev
        self.port = port
        #
        BaseTCPSocketConnection.__init__(self)

    # Note: Because this isn't a real server, open() blocks until a connection comes in.
    def open(self):
        # @fixme: For now, listen on all interfaces.  Should only listen on specified interface.
        self.sock.bind(('', self.port))
        self.sock.listen(5)
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)

        (clientsock,clientaddr) = self.sock.accept()
        
# Note: This class is mainly intended as an example and for unit tests, it probably
#       is not sufficient for a real TCP server which should handle multiple-
#       connections, etc.
class TCPServer:
    def __init__(self, eth_dev, port, connection_thread_factory):
        self.eth_dev = eth_dev
        self.port = port
        self.thread_factory = connection_thread_factory
        self.should_run = 1
        self.children_threads = []
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #
    def open(self):
        # @fixme: For now, listen on all interfaces.  Should only listen on specified interface.
        #self.sock.bind(('', self.port))
        self.sock.bind(('127.0.0.1', self.port))
        self.sock.listen(5)
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)

        # Set to non-blocking
        #self.sock.setblocking(0) 

        self.thread = threading.Thread(target=self.run)
        self.thread.start()
    #
    def close(self):
        self.should_run = 0
    #
    def run(self):
        while self.should_run:
            (clientsock,clientaddr) = self.sock.accept()

            sockobj = BaseTCPSocketConnection(clientsock)

            new_thread = self.thread_factory(self, sockobj, clientaddr)
            new_thread.start()

            self.children_threads.append(new_thread)

        for x in self.children_threads:
            x.stop()

        self.sock.shutdown()
        self.sock.close()


        
    

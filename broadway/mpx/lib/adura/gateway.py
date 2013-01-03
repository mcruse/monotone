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
from mpx.lib import socket
from mpx.lib import xmlrpclib
from mpx.lib import msglog

from mpx.lib.msglog.types import ERR
from mpx.lib.msglog.types import WARN

from mpx.lib.exceptions import EResourceError
from mpx.lib.exceptions import EConnectionError
from mpx.lib.exceptions import ETimeout

from mpx.lib.threading import Lock

import struct
import array

# timeout for socket operations
SOCK_OP_TIMEOUT = 30
ETIMEOUT_RETRY_LIMIT = 3

class TcpConnection(object):
    def __init__(self, port, host, debug):
        self.port = port
        self.host = host
        self._s = None
        self.debug = debug
        return
        
    def open_connection(self):
        try:
            self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, e:
            msglog.log('Adura', ERR, 'Error creating socket - stopping protocol.')
            raise EResourceError
        try:
            self._s.connect((self.host, self.port), timeout=SOCK_OP_TIMEOUT)
        except socket.gaierror, e:
            # host related error, ie. hostname not resolving.  possibly transient
            msglog.log('Adura', WARN, 'Error resolving host:%s.' % self.host)
            raise EConnectionError
        except socket.error, e:
            # connection error, possibly transient - error 106 ('Transport endpoint is already
            # connected) can be ignored.
            if e.args[0] != 106:
                msglog.log('Adura', WARN, 'Error connecting to gateway: %s.' % self.host)
                raise EConnectionError
        return

    def close_connection(self):
        return self._s.close()
        
    def connection_ok(self):
        if not self._s:
            return 0
        return self._s._connected

class SerialFramerIface(TcpConnection):
    def __init__(self, port, host, debug, protocol='T '):
        self.protocol = protocol
        super(SerialFramerIface, self).__init__(port, host, debug)
        return
        
    def open_connection(self):
        super(SerialFramerIface, self).open_connection()
        proto = self._s.recv(2, timeout=SOCK_OP_TIMEOUT)
        #assert proto == self.protocol
        self._s.send(self.protocol)
        return
        
    def get_next_msg(self):
        AMTYPE = 2
        SOCKETID = 11
        msg = ''
        etimeout_cnt = 0
        while 1:
            b = array.array('B')
            try:
                packet_len = struct.unpack('b', self._s.recv(1, timeout=SOCK_OP_TIMEOUT))[0]
                self._is_good_read(packet_len)
                msg = self._s.recv(packet_len, timeout=SOCK_OP_TIMEOUT)
                self._is_good_read(msg)
                etimeout_cnt = 0
            except socket.error, e:
                msglog.log('Adura', WARN, 'Adura error reading socket - reinitializing communication.')
                self.close_connection()
                raise EConnectionError
            except ETimeout:
                msglog.log('Adura', WARN, 'Adura socket timed out.')
                if etimeout_cnt > ETIMEOUT_RETRY_LIMIT:
                    #too many timeouts
                    self.close_connection()
                    raise EConnectionError 
                etimeout_cnt += 1
            except:
                #unaccounted for exception ...
                msglog.log('Adura', ERR, 'Error processing SerialFramerIface stream')
                msglog.exception()
                self.close_connection()
                raise
                
            b = array.array('B')
            b.fromstring(msg)
            if len(b) < (SOCKETID - 1):
                #print 'XX'
                continue
            if (b[0] == 0x7e and (((b[AMTYPE] == 0x31 or b[AMTYPE] == 0x33) or \
               ((b[SOCKETID] == 0x31 or b[SOCKETID] == 0x33) and (b[AMTYPE] == 0x0b or b[AMTYPE] == 0x0d))) \
               or b[AMTYPE] == 0xfd or b[SOCKETID] == 0x03)):
                # Profit!
                return b
            #else keep trying
        
    def _is_good_read(self, chunk):
        if chunk == '':
            msglog.log('Adura', WARN, 'Broken connection - reinitializing communication.')
            self.close_connection()
            raise EConnectionError
        return 1

class XCommandIface(TcpConnection):
    def __init__(self, port, host, debug):
        self.__lock = Lock() # lock serializes XCommandIface messaging
        super(XCommandIface, self).__init__(port, host, debug)
        return
        
    def write(self, method_name, params):
        self.__lock.acquire()
        try:
            if not self.connection_ok():
                self.open_connection()
            # marshal data from param tuple
            data = xmlrpclib.dumps(tuple([params]), method_name)
            #payload is 4 byte, little endian, field representing the length of
            #the xml data, followed by the data
            msg = struct.pack('<I', len(data)) + data
            try:
                self._s.send(msg)
            except:
                msglog.log('Adura', ERR, 'Error writing to XCommand socket.')
                raise EConnectionError
            rslt = self.read()
        finally:
            self.close_connection()
            self.__lock.release()
            
    def read(self):
        # leading 4 bytes indicates length of xml-rpc response payload 
        read_len = struct.unpack('<I', self._s.recv(4, timeout=SOCK_OP_TIMEOUT))[0]
        # retreive and marshall the results.  If the xml-rpc packet represents a 
        # fault condition, loads() raises a Fault exception.  @fixme - need a 
        # better understanding of their normal result structure
        rslt = xmlrpclib.loads(self._s.recv(read_len, timeout=SOCK_OP_TIMEOUT))[0]
        return rslt

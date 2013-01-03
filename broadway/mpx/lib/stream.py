"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import array
import os
import socket
import select
from mpx import properties
from mpx.lib import threading
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import ETimeout
import time

_tmp_dir = properties.get('TEMP_DIR')

##
# This stream is esentially a wrapper around 
# a socket connection.  The writes go in one 
# side of the socket and the read function comes
# out the other.  The producer and consumer for 
# this stream need to be in different threads 
# otherwise there would be a lockup the first
# time data was not waiting for the read.  Here 
# regulation of the stream is taken care of by the 
# buffer size of the underlying socket.
#
# @note Both writing and reading to this stream are
#       blocking.
class CrossThreadStream:
    def __init__(self):
        socket_name = os.path.join(_tmp_dir,
                                   'Stream.%d' % id(self))
        while os.path.exists(socket_name):
            try:    os.remove(socket_name)
            except: socket_name += 'x'
        s_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 
                                s_socket.getsockopt(socket.SOL_SOCKET,
                                                    socket.SO_REUSEADDR)|1)
        except Exception, e:
            print 'set reuse failed, %s' % e
        s_socket.bind(socket_name)
        try:
            s_socket.listen(1)
            self.c_connection = socket.socket(socket.AF_UNIX,
                                              socket.SOCK_STREAM)
            self.c_connection.connect(socket_name)
            self.s_connection, addr = s_socket.accept()
            self.s_connection.setblocking(1)
            self.c_connection.setblocking(1)
        finally:
            # Once the connection is established, we can delete the file.
            # It will be remove from its directory, but continue to exist
            # until this process is no longer connected to it.
            os.remove(socket_name)
        self._pollin = select.poll()
        self._pollin.register(self.s_connection.fileno(),select.POLLIN)
    
    def fileno(self):
        return self.s_connection.fileno()
    
    def write(self, data):
        return self.c_connection.send(data)
        
    ##
    # Read data stored in object from current
    # stream position forward.
    #
    # @param count  The maximum number of bytes
    #               to read.
    # @default  None, Read all data available.
    # @return Data.
    def read(self, count, timeout=None):
        if not self._pollin.poll(timeout):
            raise ETimeout('Read timed out')
        data = self.s_connection.recv(count)
        return data
    
    def readline(self, timeout=None):
        data = array.array('c')
        char = self.read(1,timeout)
        while char and char != '\n':
            data.fromstring(char)
            char = self.read(1,timeout)
        data.fromstring(char)
        return data.tostring()
    
    ##
    # Presumably this function is called by the same
    # thread that is doing the writing, so there should 
    # be no condition where data is still being written 
    # while data is being sent because c_connection is 
    # blocking.
    def close(self):
        self.c_connection.close()

##
# This data stream is to be used when the producer 
# and consumer are both running within the same thread.
# In order to make this work the producer needs to register
# and callback function which the Stream will call whenever
# there is not data waiting.
#
# @note Writing to this stream is non blocking and reading 
#       is blocking.
class StreamWithCallback(CrossThreadStream):
    def __init__(self, callback, buffer_size=1024):
        CrossThreadStream.__init__(self)
        self._lock = threading.Lock()
        self._pollout = select.poll()
        self._pollout.register(self.c_connection.fileno(),select.POLLOUT)
        self._callback = callback
        self.c_connection.setblocking(0)
        self.s_connection.setblocking(1)
        self._meta = {}
        self._buffer_size = buffer_size
        self._buffer = ''
    def set_meta(self, name, value):
        self._meta[name] = value
    def get_meta(self):
        return self._meta
    def get_meta_value(self,name):
        return self._meta[name]
    def write(self,data):
        try:
            count = self.c_connection.send(data)
        except socket.error,error:
            if error[0] == 11:
                return 0
            raise
        return count
    def read(self,count):
        while count > len(self._buffer):
            data = self._read(self._buffer_size)
            if not data:
                break
            self._buffer += data
        data = self._buffer[0:count]
        self._buffer = self._buffer[len(data):]
        return data
    def _read(self,count=1024):
        if not self._pollin.poll(0):
            self._callback(self)
            if not self._pollin.poll(0):
                raise ETimeout('Callback failed to write data')
        return self.s_connection.recv(count)
    def readline(self):
        line = ''
        data = self.read(self._buffer_size)
        while data and '\n' not in data:
            line += data
            data = self.read(self._buffer_size)
        if data:
            index = data.find('\n')+1
            line += data[0:index]
            self._buffer = data[index:] + self._buffer
        return line
        
##
# The idea behind the callback for this Stream
# is that it would use a combination of meta_data
# to keep information about the tuple's data.  For 
# example, the log object may put in the beginning 
# and ending sequence numbers along with the seek 
# values of those locations and perhaps the seq and 
# seek values for the current location.  It could 
# then use this information to do its searches, etc.
class StreamingTupleWithCallback:
    def __init__(self,get_item,get_length=None):
        self._meta = {}
        self.get_item = get_item
        self.get_length = get_length
    def set_meta(self, name, value):
        self._meta[name] = value
    def get_meta(self):
        return self._meta
    def get_meta_value(self,name):
        return self._meta[name]
    def __getitem__(self, index):
        return self.get_item(index, self)
    def __getslice__(self, start, end):
        values = []
        index = start
        try:
            while index < end:
                values.append(self.get_item(index,self))
                index += 1
        except IndexError:
            pass
        return values
    def __len__(self):
        if self.get_length == None:
            raise ENotImplemented()
        return self.get_length(self)
    def __iter__(self):
        return _TupleIterator(self)

class _TupleIterator:
    def __init__(self, tuple):
        self._tuple = tuple
        self._index = 0
    def next(self):
        try:
            item = self._tuple[self._index]
        except IndexError:
            raise StopIteration
        self._index += 1
        return item

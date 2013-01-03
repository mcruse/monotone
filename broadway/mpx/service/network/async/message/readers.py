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
from threading import Lock
from threading import Event
from cStringIO import StringIO
from mpx.lib import msglog

class BaseContentReader(object):
    def __init__(self):
        self._state_listeners = []
        self._finished_loading = Event()
        self._finished_loading.clear()
    def add_state_listener(self, callback):
        self._state_listeners.append(callback)
    def notify_complete(self):
        self._finished_loading.set()
        while self._state_listeners:
            listener = self._state_listeners.pop(0)
            try:
                listener(self)
            except:
                msglog.exception()
        assert len(self._state_listeners) == 0
    def await_completion(self, timeout = None):
        self._finished_loading.wait(timeout)
        return self.is_complete()
    def is_complete(self):
        return self._finished_loading.isSet()

class ContentReader(BaseContentReader):
    def __init__(self, length):
        self._content_length = length
        self._incoming_bytes = 0
        self._outgoing_bytes = 0
        self._update_load_status()
        self._incoming_content = StringIO()
        self._outgoing_content = StringIO()
        self._content_lock = Lock()
        self._set_terminator(length)
        super(ContentReader, self).__init__()
    def read(self, bytes = -1):
        bytes = bytes or -1
        self._content_lock.acquire()
        try:
            data = self._read(bytes)
            self._outgoing_bytes += len(data)
        finally: 
            self._content_lock.release()
        return data
    def getvalue(self):
        return self._incoming_content.getvalue()
    def _read(self, bytes):
        incominglocation = self._incoming_content.tell()
        outgoinglocation = self._outgoing_content.tell()
        self._outgoing_content.seek(0, 2)
        outgoingtotal = self._outgoing_content.tell()
        if bytes > 0:
            bytes -= outgoingtotal - outgoinglocation
        if bytes and self._incoming_bytes > outgoingtotal:
            self._incoming_content.seek(outgoingtotal)
            data = self._incoming_content.read(bytes)
            self._outgoing_content.write(data)
        self._incoming_content.seek(incominglocation)
        self._outgoing_content.seek(outgoinglocation)
        return self._outgoing_content.read(bytes)
    def close_streams(self):
        self._content_lock.acquire()
        try:
            self._incoming_content.close()
            self._outgoing_content.close()
        finally:
            self._content_lock.release()
    def handle_close(self):
        if not self.is_complete():
            msglog.log('broadway', msglog.types.WARN, 
                       '%r handle closed called.' % self)
    def collect_incoming_data(self, data):
        self._content_lock.acquire()
        try: 
            self._incoming_content.write(data)
            self._incoming_bytes += len(data)
        finally: 
            self._content_lock.release()
    def found_terminator(self):
        if self._content_length and not self._incoming_bytes:
            self._set_terminator(self._content_length)
        else:
            self._update_load_status()
            if not self.is_complete():
                raise Exception('Should not be receiving data.')
    def get_terminator(self):
        return self._terminator
    def _set_terminator(self, terminator):
        self._terminator = terminator
    def _update_load_status(self):
        if self._incoming_bytes == self._content_length:
            self.notify_complete()


class ClosingContentReader(BaseContentReader):
    def __init__(self):
        self._contents_lock = Lock()
        self._incoming_contents = []
        self._connection_closed = False
        self._outgoing_content = StringIO()
        super(ClosingContentReader, self).__init__()
    def read(self, bytes = -1):
        self._transfer_incoming_outgoing()
        return self._outgoing_content.read(bytes or -1)
    def _transfer_incoming_outgoing(self):
        self._contents_lock.acquire()
        contents = self._incoming_contents
        self._incoming_contents = []
        self._contents_lock.release()
        location = self._outgoing_content.tell()
        self._outgoing_content.seek(0, 2)
        map(self._outgoing_content.write, contents)
        self._outgoing_content.seek(location)
    def getvalue(self):
        self._transfer_incoming_outgoing()
        return self._outgoing_content.getvalue()
    def handle_close(self):
        self._connection_closed = True
        self._set_terminator(0)
        self.notify_complete()
    def collect_incoming_data(self, data):
        if self._done_reading_content():
            raise TypeError('Should not collecting data, closed.')
        self._contents_lock.acquire()
        try: 
            self._incoming_contents.append(data)
        finally: 
            self._contents_lock.release()
    def found_terminator(self):
        if self._done_reading_content():
            raise TypeError('Found terminator should not be called.')
        self._set_terminator(None)
    def get_terminator(self):
        return self._terminator
    def _set_terminator(self, terminator):
        self._terminator = terminator
    def _done_reading_content(self):
        return self._connection_closed


class ChunkedContentReader(BaseContentReader):
    """
        Reads content of unknown size that has been transport 
        encoded as chunked data.  Current implementation may 
        be somewhat innefficient in its use of terminators to 
        capture such small pieces of data as the chunk-size.
        Future enhancement may include more logic in collect 
        incoming data method to manage 
    """
    debuglevel = 0
    def __init__(self):
        self._incoming_content = StringIO()
        self._outgoing_content = StringIO()
        self._outgoing_content_bytes = 0
        self._outgoing_bytes_returned = 0
        self._buffered_data = ''
        self._chunk_number = 0
        self._chunk_length = 0
        self._chunk_bytes_read = 0
        self._content_length = 0
        self._content_bytes_read = 0
        self._consecutive_terminators = 0
        self._content_lock = Lock()
        super(ChunkedContentReader, self).__init__()
    def read(self, bytes = -1):
        bytes = bytes or -1
        self._content_lock.acquire()
        try:
            data = self._read(bytes)
            self._outgoing_bytes_returned += len(data)
        finally: 
            self._content_lock.release()
        return data
    def getvalue(self):
        return self._incoming_content.getvalue()
    def getvalue(self):
        self.read(-1)
        return self._outgoing_content.getvalue()
    def get_terminator(self):
        return self._terminator
    def _set_terminator(self, terminator):
        self._terminator = terminator
    def _read(self, bytes):
        incominglocation = self._incoming_content.tell()
        outgoinglocation = self._outgoing_content.tell()
        self._outgoing_content.seek(0, 2)
        outgoingtotal = self._outgoing_content.tell()
        if bytes > 0:
            bytes -= outgoingtotal - outgoinglocation
            if bytes < 0:
                bytes = 0
        if bytes and (incominglocation > outgoingtotal):
            self._incoming_content.seek(outgoingtotal)
            assert (self._outgoing_content.tell() == 
                    self._incoming_content.tell())
            data = self._incoming_content.read(bytes)
            self._outgoing_content.write(data)
        self._incoming_content.seek(incominglocation)
        self._outgoing_content_bytes = self._outgoing_content.tell()
        self._outgoing_content.seek(outgoinglocation)
        return self._outgoing_content.read(bytes)
    def handle_close(self):
        if not self.is_complete():
            msglog.log('broadway', msglog.types.WARN, 
                       '%r handle closed called.' % self)
    def collect_incoming_data(self, data):
        data = self._buffered_data + data
        self._buffered_data = ''
        while data:
            bytes_remaining = self._chunk_bytes_remaining()
            if bytes_remaining == 0:
                if self._done_reading_content():
                    self._buffered_data += data
                    data = ''
                else:
                    splitdata = data.lstrip().split('\r\n', 1)
                    if len(splitdata) == 2:
                        chunkdata = splitdata[0]
                        self._configure_next_chunk(chunkdata)
                        data = splitdata[1]
                    else:
                        self._buffered_data = data
                        data = ''
            else:
                content = data[0:bytes_remaining]
                self._incoming_content.write(content)
                self._chunk_bytes_read += len(content)
                self._content_bytes_read += len(content)
                data = data[bytes_remaining:]
    def found_terminator(self):
        if self._chunk_number == 0:
            self._set_terminator('\r\n\r\n')
        else:
            self.collect_incoming_data(self.get_terminator())
            if self._done_reading_content():
                self.notify_complete()
            else:
                contentread = self._content_bytes_read
                chunknumber = self._chunk_number
                chunkread = self._chunk_bytes_read
                print 'WARNING -- terminator found in content:'
                print '\t%d bytes into content.' % contentread
                print '\t%d bytes into chunk %d.' % (chunkread, chunknumber)
                print '\tcontinuing with response.'
    def _configure_next_chunk(self, line):
        extindex = line.find(';')
        if extindex >= 0:
            line = line[:extindex] # strip chunk-extensions
        try: 
            chunk_length = int(line, 16)
        except ValueError:
            msglog.log('broadway', msglog.types.ERR, 
                       'Failed to turn "%r" into chunk length.' % line)
            msglog.exception()
            raise
        self._chunk_number += 1
        self._chunk_bytes_read = 0
        self._chunk_length = chunk_length
        self._content_length += chunk_length
    def _done_reading_content(self):
        return (self._chunk_number > 0 and self._chunk_length == 0)
    def _chunk_bytes_remaining(self):
        return self._chunk_length - self._chunk_bytes_read
    def _bytes_remaining(self):
        return self._content_length - self._content_bytes_read
    def debug(self, level = 0):
        return level <= self.debuglevel

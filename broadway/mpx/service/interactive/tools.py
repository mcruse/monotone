"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from __future__ import with_statement
import urllib
import asyncore
import asynchat
from threading import RLock
from StringIO import StringIO
from mpx.lib import msglog

class Dispatcher(object, asyncore.dispatcher):
    def __init__(self, monitor):
        asyncore.dispatcher.__init__(self, map=monitor)

class AsyncChannel(object, asynchat.async_chat):
    def __init__(self, dispatcher, connection):
        self.dispatcher = dispatcher
        asynchat.async_chat.__init__(self)
        asyncore.dispatcher.__init__(self, map=self.dispatcher.monitor)
        self.setup_connection(connection)
    def setup_connection(self, connection):
        self.set_socket(connection, self.dispatcher.monitor)
        self.socket.setblocking(0)

class ByteBuffer(object):
    def __init__(self):
        self.buffers = []
        self.bytecount = 0
    def write(self, bytes):
        self.buffers.append(bytes)
        self.bytecount += len(bytes)
    def read(self):
        buffers = self.buffers
        self.buffers = []
        self.bytecount = 0
        return "".join(buffers)
    def __len__(self):
        return self.bytecount
    def __nonzero__(self):
        return bool(self.buffers)

class SimpleProducer(asynchat.simple_producer, object):
    pass

class QuoteProducer(object):
    def __init__(self, producer):
        self.producer = producer
        super(QuoteProducer, self).__init__()
    def more(self):
        data = self.producer.more()
        if data:
            data = urllib.quote(data)
        return data

class LineProducer(object):
    def __init__(self, producer):
        self.complete = False
        self.producer = producer
    def more(self):
        if self.complete:
            return ""
        sio = StringIO()
        data = self.producer.more()
        while data:
            sio.write(data)
            data = self.producer.more()
        else:
            sio.write("\r\n")
        sio.seek(0)
        self.complete = True
        return sio.read()

class ByteProducer(object):
    """
        Encode output data as needed so that it can 
        be written to a socket and shown on a console.
        
        Certain debugging output, such as that output by 
        soap proxies when debugging is turned on, use non-ascii 
        character codes.  This produces execption on transport 
        because Python will not automatically coerce encodings 
        in ambiguous scenarios.
    """
    def __init__(self, producer, encoding = 'UTF-8'):
        self.encoding = encoding
        self.producer = producer
    def encoded(self, data):
        if not isinstance(data, str):
            data = data.encode(self.encoding)
        return data
    def more(self):
        return self.encoded(self.producer.more())
    def fromstring(klass, string):
        producer = asynchat.simple_producer(string)
        return klass(producer)
    fromstring = classmethod(fromstring)

class OutputSplitter(object):
    def __init__(self, file):
        self.file = file
        self.files = set()
        super(OutputSplitter, self).__init__()
    def attach(self, file):
        self.files.add(file)
    def detach(self, file):
        self.files.discard(file)
    def attached(self, file):
        return file in self.files
    def write(self, bytes):
        result = self.file.write(bytes)
        for file in self.files.copy():
            try:
                file.write(bytes)
            except:
                msglog.exception(prefix="handled")
        return result
    def __getattr__(self, name):
        return getattr(self.file, name)

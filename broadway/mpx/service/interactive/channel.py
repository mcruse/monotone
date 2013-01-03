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
from __future__ import with_statement
import sys
import urllib
from mpx.lib import msglog
from mpx.service.interactive.tools import ByteBuffer
from mpx.service.interactive.tools import SimpleProducer
from mpx.service.interactive.tools import ByteProducer
from mpx.service.interactive.tools import LineProducer
from mpx.service.interactive.tools import QuoteProducer
from mpx.service.interactive.tools import AsyncChannel
from mpx.service.network.utilities.counting import Counter
from mpx.service.interactive.console import InteractiveSession

class ConsoleChannel(AsyncChannel):
    counter = Counter()
    def __init__(self, dispatcher, connection):
        super(ConsoleChannel, self).__init__(dispatcher, connection)
        self.number = self.counter.increment()
        self.buffer = ByteBuffer()
        self.setup_console()
    def setup_console(self):
        self.namespace = {'loadtools': self.loadtools}
        self.console = InteractiveSession(self)
        self.set_terminator('\r\n')
        self.console.start()
        self.initprompt()
    def initprompt(self):
        banner = [sys.version]
        banner.append("%s" % self.dispatcher)
        banner.append(str(self.dispatcher))
        banner.append(str(self))
        banner.append('<loadtools() will add standard tools>')
        self.console.prompt("\n".join(banner))
    def push(self, data):
        producer = SimpleProducer(data)
        producer = ByteProducer(producer)
        producer = QuoteProducer(producer)
        producer = LineProducer(producer)
        return self.push_with_producer(producer)
    def loadtools(self):
        from mpx.lib import msglog
        from mpx.lib.node import as_node
        from mpx.lib.node import as_node_url
        self.namespace['msglog'] = msglog
        self.namespace['as_node'] = as_node
        self.namespace['root'] = as_node('/')
        self.namespace['as_node_url'] = as_node_url
    def handle_connect(self):
        pass
    def handle_expt(self):
        self.debugout('%s handling exceptional event.', self, level=0)
        self.close()
    def handle_error(self):
        self.debugout('%s closing due to exception.', self, level=0)
        msglog.exception(prefix = 'handled')
        self.close()
    def close(self):
        self.console.stop()
        super(ConsoleChannel, self).close()
        self.debugout('%s closed and removed.', self, level=1)
    def recv(self, buffer_size):
        data = super(ConsoleChannel, self).recv(buffer_size)
        unquoted = urllib.unquote(data)
        self.debugout('%s << %r (%r)', self, data, unquoted, level=2)
        return data
    def send(self, data):
        result = super(ConsoleChannel, self).send(data)
        unquoted = urllib.unquote(data)
        self.debugout('%s >> %r (%r)', self, data, unquoted, level=2)
        return result
    def collect_incoming_data(self, bytes):
        self.buffer.write(bytes)
    def found_terminator(self):
        quoted = self.buffer.read()
        command = urllib.unquote(quoted)
        self.debugout('%s console.handle(%r)', self, command, level=1)
        self.console.handle(urllib.unquote(command))
    def __str__(self):
        status = [type(self).__name__]
        status.append('#%03d' % self.number)
        return ' '.join(status)
    def __repr__(self):
        status = [str(self)]
        return '<%s at %#x>' % (status, id(self))
    def debugout(self, message, *args, **kw):
        self.dispatcher.debugout(message, *args, **kw)

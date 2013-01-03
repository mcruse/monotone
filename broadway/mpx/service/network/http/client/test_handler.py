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
import time
import urllib
import string
from cStringIO import StringIO
from threading import Lock
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.service.network.http.response import Cookie

class TestHandler(CompositeNode):
    def __init__(self, *args):
        self.path = '/testhandler'
        self.output = '/var/mpx/log/testhandler.out'
        self.provides_security = True
        self._queue = []
        self._output = None
        self._output_lock = Lock()
        super(TestHandler, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path', self.path))
        self.setattr('output', config.get('output', self.output))
        super(TestHandler, self).configure(config)
    def configuration(self):
        config = super(TestHandler, self).configuration()
        config['path'] = self.getattr('path')
        config['output'] = self.getattr('output')
        return config
    def start(self):
        self._output = open(self.output, 'w')
        super(TestHandler, self).start()
    def stop(self):
        self._output.close()
        self._output = None
        super(TestHandler, self).stop()
    def next_request(self):
        try: 
            return self._queue.pop(0)
        except IndexError:
            return ''
    def add_request(self, request):
        self._queue.append(request)
    def match(self, path):
        return path.startswith(self.path)
    def handle_request(self, request):
        output = StringIO()
        command = request.get_command()
        header = '-- %s request [%d] [%s] --      ' 
        header %= (command, id(request), time.ctime())
        output.write(header)
        output.write('\n' + '*' * len(header) + '\n')
        output.write('<<< Request >>>\n')
        output.write(' - headers - \n')
        output.write(string.join(request.get_headers(), '\n') + '\n\n')
        output.write(' - content - \n')
        data = '-- No incoming data --'
        delimlength = len(data)
        if command == 'POST':
            data = request.get_data().read_all()
        output.write(data + '\n' + '-' * delimlength + '\n\n')
        response = Response(request)
        output.write('<<< Response >>>\n')
        command_cookie = Cookie('command_id', str(UUID()))
        command_cookie.add_attribute('path', '/')
        command_cookie.add_attribute('domain', '.domain.com')
        test_cookie = Cookie('test_id', str(UUID()))
        test_cookie.add_attribute('path', '/')
        test_cookie.add_attribute('domain', '.domain.com')
        content = self.next_request()
        response.add_cookie(command_cookie)
        response.add_cookie(test_cookie)
        response.push(content)
        output.write(' - headers - \n')
        for name,value in request.response_headers.items():
            output.write("%s: %s\n" % (name,value))
        output.write(' - content - \n')
        output.write(content or '-- No outgoing data --')
        output.write('\n' + '*' * len(header) + '\n\n')
        response.done()
        self.debug_dumps(output.getvalue())
    def debug_dumps(self, message):
        self._output_lock.acquire()
        try: 
            self.__debugoutput(message)
        finally:
            self._output_lock.release()
    def __debugoutput(self, message):
        self._output.seek(0, 2)
        if self._output.tell() >= 1024000:
            self._output.seek(0)
            self._output.truncate()
            self._output.write('*** OUTPUT FILE TRUNCATED ***')
        self._output.write(message)
        self._output.flush()
            
            

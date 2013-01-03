"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
# @todo Add auto-detect.

from mpx.lib.node import CompositeNode, as_node
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
from mpx.lib.exceptions import EIOError

from definitions import *
from module import Module

class LineHandler(CompositeNode):

    def __init__(self):
        CompositeNode.__init__(self)
        self.failures = 0
        self.commands = 0
        self.retry = 2
        self.retries = 0

    def configure(self,config):
        CompositeNode.configure(self,config)
        set_attribute(self, 'port', self.parent, config, as_node)
        set_attribute(self, 'timeout', 2.0, config, float)
        set_attribute(self, 'debug', 0, config, int)
        self.port.open()

    def configuration(self):
        config = CompositeNode.configuration(self)
        config['port'] = config['parent']
        get_attribute(self, 'timeout', config, str)
        get_attribute(self, 'debug', config, str)
        return config

    def command(self,cmdstr):
        try:
            self.port.lock()
            self.commands = self.commands + 1
            for i in range(0,self.retry):
                buffer = array.array('c')
                try:
                    # disregard any thing possibly left over in the buffer from
                    # prior queries.
                    self.port.drain()
                    self.port.write(cmdstr)
                    self.port.flush()
                    self.port.read_upto(buffer, (CR,LF), self.timeout)
                    return buffer
                except:
                    msglog.exception()
                    self.retries = self.retries + 1
        finally:
            self.port.unlock()

        self.failures = self.failures + 1
        raise EIOError, cmdstr

    def scan(self):
        for addr in range(0,0x100):
            try:
                m = Module()
                m.configure({'name':'adamXXXX', 'parent':self,
                             'line_handler':self, 'address':addr})
                print '0x%02X' % addr, '(%3d)' % addr, m.ReadModuleName()
            except EIOError:
                print "."
            del m

def factory():
    return LineHandler()

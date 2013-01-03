"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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

from mpx.service import SubServiceNode
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import as_node
from mpx.lib import pause, msglog, threading
from mpx.lib.exceptions import EAlreadyRunning, ENotImplemented

class DataExporter(SubServiceNode):
    def __init__(self):
        SubServiceNode.__init__(self)
        self.running = 0
        self.last_time = 0
        self.success_count = 0
    def configure(self, config):
        set_attribute(self, 'upload_interval', 900, config, int)
        set_attribute(self, 'type', 'exporter', config)
        SubServiceNode.configure(self, config)
        set_attribute(self, 'log', self.parent, config, as_node)
    def configuration(self):
        config = SubServiceNode.configuration(self)
        config['log'] = self.parent
        get_attribute(self, 'upload_interval', config, str)
        return config
    def start(self):
        if not self.running:
            self._thread = threading.Thread(target=self._start,args=())
            self.running = 1
            self._thread.start()
        else: raise EAlreadyRunning
    def stop(self):
        self._thread = None
        self.running = 0
    def _start(self):
        while self.running:
            start_time = self.last_time
            end_time = time.time()
            data = self.log.get_range('timestamp', start_time, end_time)
            try:
                self._send(data, start_time, end_time)
                self.last_time = end_time
                self.success_count += 1
            except:
                msglog.exception()
            pause(self.upload_interval)
    
    def _send(self, data, start_time, end_time):
        raise ENotImplemented

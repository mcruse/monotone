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
import sys
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.service.network.async.connection import monitor
from mpx.service.interactive.dispatch import ConsoleDispatcher
from mpx.service.interactive.tools import OutputSplitter

class InteractiveService(CompositeNode):
    def __init__(self):
        self.monitor = None
        self.dispatcher = None
        self.standard_error = None
        self.standard_output = None
        super(InteractiveService, self).__init__()
    def logoutput(self, message, *args, **kw):
        logtype = kw.get("type", msglog.types.DB)
        debuglevel = kw.get("level", 1)
        if logtype == msglog.types.DB and debuglevel > self.debug:
            return False
        msglog.log('broadway', logtype, message % args)
        return True
    def configure(self, config):
        set_attribute(self, 'interface', 'localhost', config)
        set_attribute(self, 'port', 9666, config, int)
        set_attribute(self,'debug', 0, config, int)
        return super(InteractiveService, self).configure(config)
    def configuration(self):
        config = super(InteractiveService, self).configuration()
        get_attribute(self, 'interface', config)
        get_attribute(self, 'port', config, str)
        get_attribute(self, 'debug', config, str)
        return config
    def start(self):
        if not isinstance(sys.stderr, OutputSplitter):
            self.standard_error = sys.stderr
            sys.stderr = OutputSplitter(sys.stderr)
        if not isinstance(sys.stdout, OutputSplitter):
            self.standard_output = sys.stdout
            sys.stdout = OutputSplitter(sys.stdout)
        if self.monitor is None:
            self.monitor = monitor.ChannelMonitor()
        if self.dispatcher is None:
            self.dispatcher = ConsoleDispatcher(self)
        if not self.monitor.is_running():
            self.monitor.start_monitor()
        if not self.dispatcher.is_dispatching():
            self.dispatcher.start_dispatching()
        self.logoutput('%s started.', self, type=msglog.types.INFO)
        return super(InteractiveService, self).start()
    def stop(self):
        if isinstance(sys.stderr, OutputSplitter):
            sys.stderr = self.standard_error
        if isinstance(sys.stdout, OutputSplitter):
            sys.stdout = self.standard_output
        if self.dispatcher is not None:
            if self.dispatcher.is_dispatching():
                self.dispatcher.stop_dispatching()
            self.dispatcher = None
        if self.monitor is not None:
            if self.monitor.is_running():
                self.monitor.stop_monitor()
            self.monitor = None
        self.logoutput('%s stopped.', self, type=msglog.types.INFO)
        return super(InteractiveService, self).stop()

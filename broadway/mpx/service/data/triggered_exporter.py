"""
Copyright (C) 2006 2011 Cisco Systems

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
from _exporter import Exporter
from synchronized_exporter import SynchronizedExporter
from mpx.lib.exceptions import ENotStarted,ENoSuchNode
from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.node import as_node
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.threading import Thread
from mpx.lib import msglog
import time

class TriggeredExporter(SynchronizedExporter):
    def __init__(self):
        SynchronizedExporter.__init__(self)
        self._sid = None
        self.evt = None #dil - debug
    def handle_log(self,event):
        self.debug_information('Log export triggered.')
        self.evt = event #dil - debug 
        value = event.results()[1]['value']
        if isinstance(value,Exception):
            raise value
        if value: # only export when value is true
            self.debug_information('Going to start export thread.')
            if self._lock.acquire(0):
                try:
                    thread = Thread(name=self.name, target=self.go,
                                    args=(time.time(),))
                    thread.start()
                finally:
                    self._lock.release()
            else:
                msglog.log('broadway',msglog.types.WARN, 
                           ('Last export still active, ' + 
                            'skipping current request.'))
                            
    def configure(self, config):
        set_attribute(self, 'trigger',REQUIRED,config)
        SynchronizedExporter.configure(self, config)
        
    def configuration(self):
        config = SynchronizedExporter.configuration(self)
        get_attribute(self,'trigger',config,str)
        return config
        
    def start(self):
        Exporter.start(self)
        if not self.running:
            self.running = 1
            self.connection = as_node(self.connection_node)
            self._time_keeper = PersistentDataObject(self)
            self._time_keeper.start_time = 0
            self._time_keeper.load()
            self._period = self.parent.parent.period
            self._setup_trigger()
        else: 
            raise EAlreadyRunning
            
    def _setup_trigger(self):
        try:
            self._sid = SM.create_delivered(self, {1:as_node(self.trigger)})
        except ENotStarted, ENoSuchNode:
            msg = 'TriggeredExporter trigger: %s does not exist - could be nascent' % self._trigger
            msglog.log('broadway',msglog.types.WARN,msg)
            scheduler.seconds_from_now_do(60, self._setup_trigger)

def factory():
    return TriggeredExporter()

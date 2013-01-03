"""
Copyright (C) 2002 2003 2006 2010 2011 Cisco Systems

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
from mpx.lib.exceptions import EBreakupTransfer,EIOError,ENoData
from mpx.lib.event import EventConsumerMixin

from mpx.lib.log import LogAddEntryEvent

from mpx.lib.node import as_node,as_node_url
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.threading import Lock,Thread
from mpx.lib import msglog

class SynchronizedExporter(Exporter,EventConsumerMixin):
    def __init__(self):
        self.running = 0
        self._lock = Lock()
        Exporter.__init__(self)
        EventConsumerMixin.__init__(self,self.handle_log,self.handle_error)
    def debug_information(self,message):
        if self.debug:
            debug = '%s Exporter => %s' % (self.name,message)
            msglog.log('broadway',msglog.types.DB,debug)
    def handle_log(self,event):
        self._event_count += 1
        self.debug_information('Log entry event caught.')
        if self._event_count >= self.log_multiple:
            self.debug_information('Going to start export thread.')
            if self._lock.acquire(0):
                try:
                    thread = Thread(name=self.name, target=self.go,
                                    args=(event.values[0],))
                    thread.start()
                    self._event_count = 0
                finally:
                    self._lock.release()
            else:
                msglog.log('broadway',msglog.types.WARN, 
                           ('Last export still active, ' + 
                            'skipping current request.'))
    def handle_error(self,exc):
        msglog.exception(exc)
    def configure(self, config):
        set_attribute(self,'log_multiple',1,config,int)
        set_attribute(self,'timeout',60,config,int)
        set_attribute(self,'connection_node','/services/network',config)
        set_attribute(self,'connection_attempts',3,config,int)
        Exporter.configure(self, config)
    def configuration(self):
        config = Exporter.configuration(self)
        get_attribute(self,'log_multiple',config,str)
        get_attribute(self,'connection_node',config)
        get_attribute(self,'connection_attempts',config)
        get_attribute(self,'timeout',config,int)
        return config
    def start(self):
        Exporter.start(self)
        if not self.running:
            self.running = 1
            self.connection = as_node(self.connection_node)
            self._event_count = self.log_multiple - 1
            self._time_keeper = PersistentDataObject(self)
            self._time_keeper.start_time = 0
            self._time_keeper.load()
            self._period = self.parent.parent.period
            self.parent.parent.event_subscribe(self, LogAddEntryEvent)
        else: 
            raise EAlreadyRunning
    def stop(self):
        self.running = 0
    def scheduled_time(self):
        return self._end_time
    def go(self, end_time):
        self.debug_information('Exporting.')
        self._lock.acquire()
        try:
            self._end_time = end_time
            self._export(end_time)
            self._end_time = None
            self.debug_information('Done Exporting.')
        except:
            msglog.exception()
        self._lock.release()
    def _export(self,end_time):
        attempts = 0
        connected = 0
        while attempts < self.connection_attempts:
            self.debug_information('Acquiring connection...')
            try:
                connected = self.connection.acquire()
            except:
                msglog.exception()
            if connected:
                self.debug_information('Connection acquired.')
                break
            self.debug_information('Failed to acquire.')
            attempts += 1
        else:
            self.debug_information('Connection failed, aborting.')
            raise EConnectionError('Failed to connect %s times' % attempts)
        try:
            last_break = 0
            end = end_time
            start_time = self._time_keeper.start_time
            while start_time <= end_time:
                self.debug_information('Getting data from %s to %s.' 
                                       % (start_time,end))
                data = self.log.get_range('timestamp',start_time,end)
                if not data:
                    self.debug_information('No Data to export.')
                    raise ENoData('timestamp',start_time,end)
                try:
                    self.debug_information('Calling format.')
                    output = self.formatter.format(data)
                    self.debug_information('Calling transport.')
                    self.transporter.transport(output)
                    self.debug_information('Done transporting.')
                    start_time = end + self._period
                except EBreakupTransfer, e:
                    entry = e.break_at
                    self.debug_information('Breaking up transfer.')
                    if entry['timestamp'] == last_break:
                        # prevents loop where transporter is just failing.
                        raise EIOError('EBreakupTransfer not progressing.')
                    last_break = entry['timestamp']
                    end = last_break - self._period
                    msglog.log('broadway',msglog.types.WARN,
                               'Breaking up data transfer at %s.' % end)
                else:
                    end = end_time
                    self._time_keeper.start_time = start_time
                    self._time_keeper.save()
        finally:
            if connected:
                self.connection.release()
    
def factory():
    return PeriodicExporter()

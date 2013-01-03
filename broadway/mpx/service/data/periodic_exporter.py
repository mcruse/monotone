"""
Copyright (C) 2002 2003 2004 2005 2008 2009 2010 2011 Cisco Systems

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
import string
from mpx import properties
from mpx.lib import pause, msglog
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.configure import map_to_attribute, map_from_attribute
from mpx.lib.configure import map_to_seconds, map_from_seconds, as_boolean
from mpx.lib.event import ConnectionEvent,EventConsumerMixin
from mpx.lib.exceptions import EAlreadyRunning, ENoData, EBreakupTransfer, \
     ENotEnabled,ETimeout,EConnectionError, ENoSuchName, EInvalidValue, EIOError
from mpx.lib.node import as_node, as_node_url
from mpx.lib.scheduler import scheduler
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.threading import Lock
from mpx.lib.thread_pool import ThreadPool

from _exporter import Exporter
from _formatter_exceptions import EInconsistantFormat, EIncompatiableFormat
from _transporter_exceptions import ETransporter

Exporter_ThreadPool = ThreadPool(2, name='PeriodicExporter-ThreadPool')

def _days_to_seconds(days):
    return float(days) * 86400
def _seconds_to_days(seconds):
    return str(seconds / 86400)

class _TimeStore(PersistentDataObject):
    def __init__(self, node):
        self.last_time = 0
        PersistentDataObject.__init__(self, node)
    def get_last_time(self):
        if 'last_time' not in self.loaded():
            self.load()
        return self.last_time
    def set_last_time(self, time):
        self.last_time = time
        self.save()

##
# Base class for all Exporters that export data
# periodically.
#
class PeriodicExporter(Exporter,EventConsumerMixin):
    def __init__(self):
        Exporter.__init__(self)
        EventConsumerMixin.__init__(self,
                                    self.handle_connected,
                                    self.connection_event_error)
        self.running = 0
        self._scheduled = None
        self._lock = Lock()
    def handle_connected(self,event):
        self.msglog('%s Got connection event' % self.name)
        if event.__class__ == ConnectionEvent:
            self.msglog('Connection state is %s.' % str(event.state))
            if event.state ==  ConnectionEvent.STATE.UP:
                self.msglog('Going to start export.')
                self.go()
        else:
            msg = (('Unknown event recieved by %s from %s.' %
                    (self.name,str(self.connection_node))) + 
                   ' Event: %s' % str(event))
            msglog.log('broadway',msglog.types.WARN,msg)
    def connection_event_error(self,exc,event):
        msg = ('Connection Event for ' +
               str(self.connection_node) +
               ' had the following Error\n' +
               'Event: ' + str(event) +
               'Error: ' + str(exc))
        msglog.log('broadway',msglog.types.WARN,msg)
    def msglog(self,msg,force=0):     
        if self.debug or force:
            msglog.log('broadway.mpx.service.data.periodic_exporter',
                       msglog.types.DB,msg) 
    def configure(self, config):
        map_to_attribute(self, 'period', 900, config, map_to_seconds)
        if self.period == 0:
            raise EInvalidValue('period',self.period,'Export period cannot be 0')
        set_attribute(self, 'debug', 0, config, as_boolean)
        set_attribute(self, 'synchronize_on', '00:00', config)
        set_attribute(self,'timeout',60,config,int)
        set_attribute(self,'connection_node','/services/network',config)
        set_attribute(self,'connection_attempts',3,config,int)
        set_attribute(self,'always_export',0,config,as_boolean)
        set_attribute(self,'breakup_on_period',0,config,as_boolean)
        Exporter.configure(self, config)
        self._time = _TimeStore(self)
    def configuration(self):
        config = Exporter.configuration(self)
        map_from_attribute(self, 'period', config, map_from_seconds)
        get_attribute(self,'connection_node',config)
        get_attribute(self,'debug',config,str)
        get_attribute(self,'connection_attempts',config)
        get_attribute(self,'timeout',config)
        get_attribute(self,'always_export',config,str)
        get_attribute(self, 'synchronize_on',config)
        get_attribute(self, 'breakup_on_period',config,str)
        return config
    def start(self):
        Exporter.start(self)
        if not self.running:
            node = as_node(self.connection_node)
            if hasattr(node,'event_subscribe'):
                node.event_subscribe(self,ConnectionEvent)
            else:
                if self.debug:
                    msg = ('Connection node: ' + str(self.connection_node) + 
                       ' is not an event producer.')
                    msglog.log('broadway',msglog.types.INFO,msg)
            self.connection = node
            self.running = 1
            self._init_next_time()
            self._schedule()
        else: 
            raise EAlreadyRunning
    def stop(self):
        self.running = 0
        if self._scheduled is not None:
            try:
                self._scheduled.cancel()
            except:
                pass
        Exporter.stop(self)
    def go(self, end_time, start_time=None):
        if self._lock.locked():
            msglog.log('broadway',msglog.types.WARN, \
                       'Last export still active, skipping current request.')
            return
        Exporter_ThreadPool.queue_noresult(self._complete, end_time, start_time)
    def scheduled_time(self):
        return self.next_time() - self.period
    def last_time(self):
        return self._time.get_last_time()
    def _schedule(self):
        next = self.next_time()
        self._scheduled = scheduler.at(next, self.go, (next,))
    def _complete(self, end_time, start_time=None):
        self._lock.acquire()
        try:
            self._export(end_time, start_time)
        except:
            msglog.exception()
        self._lock.release()
        if self.running:
            self._schedule()
    ##
    #
    def _init_next_time(self):
        time_format = '%Y%m%d %H:%M:%S'
        sync_format = '%Y%m%d ' + self.synchronize_on + ':00'
        current_time = int(time.time())
        f_sync = time.strftime(sync_format, self.time_function(current_time))
        f_now = time.strftime(time_format, self.time_function(current_time))
        sync = time.mktime(time.strptime(f_sync, time_format))
        now = time.mktime(time.strptime(f_now, time_format))
        if now > sync:
            # sync time in past, add one day to sync time.
            sync += map_to_seconds({'days':1})
        gap = sync - now
        if self.period > gap:
            sync_time = current_time + gap
        else:
            sync_time = current_time + (gap % self.period)
        #
        #
        #
        self._next_time = sync_time
        return self._next_time
    def next_time(self):
        current_time = time.time()
        while self._next_time < current_time:
            self._next_time += self.period
        return self._next_time
    def data_since_export(self):
        start_time = self.last_time()
        end_time = self.next_time()
        return self.log.get_slice('timestamp',start_time,end_time)
    def formatted_data_since_export_as_string(self):
        length = 0
        stream = self.formatted_data_since_export()
        text = stream.read(1024)
        while len(text) > length:
            length = len(text)
            text += stream.read(1024)
        return text
    def formatted_data_since_export(self):
        return self.formatter.format(self.data_since_export())
    def export_data_since_export(self):
        return self.transporter.transport(self.formatted_data_since_export())
    def _export(self,end_time, start_time=None):
        attempts = 0
        connected = 0
        while attempts < self.connection_attempts:
            self.msglog('Acquiring connection %s.' % str(self.connection_node))
            try:
                connected = self.connection.acquire()
            except:
                msglog.exception()
            if connected:
                self.msglog('Connection acquired')
                break
            attempts += 1
            self.msglog('Connection acquire failed %s times.' % attempts)
        else:
            raise EConnectionError('Failed to connect %s times' % attempts)
        try:
            if start_time is None:
                start_time = self.last_time()
            if start_time == 0 and self.breakup_on_period:
                self.msglog('Start Time is 0 and set to Break on Transfer.')
                start_time = self.log.get_first_record()['timestamp']
                self.msglog('Start Time set to timestamp of first row: %s' % time.ctime(start_time))
            retrieve = self.log.get_slice
            if self.log.name == 'msglog':
                msglog.log('msglog.exporter', msglog.types.INFO, 
                           'repr(mpx.properties)\n%s\n' % 
                           (repr(properties)))
                retrieve = self.log.get_range
                end_time = time.time()
            end = end_time
            if self.breakup_on_period:
                self.msglog('Breaking on period')
                end = start_time + self.period
            self.msglog('Full export of slice from %s to %s' %
                        (time.ctime(start_time),time.ctime(end_time)))
            while start_time != end_time:
                if end > end_time:
                    self.msglog('End greater than End Time.  Resetting to End Time')
                    end = end_time
                self.msglog('Going to export slice from %s to %s' % 
                            (time.ctime(start_time),time.ctime(end)))
                data = retrieve('timestamp',start_time,end)
                if (not data) and (not self.always_export):
                    raise ENoData('timestamp',start_time,end)
                self.msglog('Sending data to formatter.')
                try:
                    output = self.formatter.format(data)
                    if not output is None:
                        self.msglog('Sending formatted data to transporter.')
                        self.transporter.transport(output)
                    start_time = end
                except EBreakupTransfer, e:
                    entry = e.break_at
                    if entry['timestamp'] == end:
                        # prevents loop where transporter is just failing.
                        raise EIOError('EBreakupTransfer not progressing.')
                    end = entry['timestamp']
                    msglog.log('broadway',msglog.types.WARN,
                               'Breaking up data transfer at %s.' %
                               time.ctime(end))
                else:
                    self._time.set_last_time(start_time)
                    self.msglog('Data transported')
                    end = start_time + self.period
        finally:
            if hasattr(self.formatter, 'cancel'):
                self.formatter.cancel() # prevent mult copies of data at next successful transport
            if connected:
                self.msglog('Releasing connection.')
                self.connection.release()
    def nodebrowser_handler(self, nb, path, node, node_url):
        html = nb.get_default_view(node, node_url)
        html += '<h4>Commands</h4>\n'
        s = '%s?action=invoke&method=do_export' % self.name
        html += '<a href="%s">Force export via nodebrowser.</a>' %(s,)
        return html
    def do_export(self, end_time=None, start_time=None):
        if end_time is None:
            end_time = time.time()
        self.go(end_time, start_time)
        return 'Export triggered.'
        
def factory():
    return PeriodicExporter()

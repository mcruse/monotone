"""
Copyright (C) 2002 2003 2004 2005 2010 2011 Cisco Systems

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
from mpx.lib.configure import set_attribute,get_attribute, \
     REQUIRED, as_boolean
from mpx.lib.node import as_node,as_node_url
from mpx.service import ServiceNode
from mpx.service.data import Formatter,Transporter
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.scheduler import scheduler
from mpx.lib.exceptions import ENotStarted,MpxException

##
# Needs to create dictionary that looks like
# dictionary from log, and then put it in list 
# of one and send to formatter.
# {'alarm':alarm.source.name
class AlarmExporter(ServiceNode):
    def __init__(self):
        self._timestamp = 0
        ServiceNode.__init__(self)
    def configure(self,config):
        ServiceNode.configure(self,config)
        set_attribute(self,'connection','/services/network',config,as_node)
        set_attribute(self,'timeout',60,config,int)
        set_attribute(self, 'gm_time', 1, config, as_boolean)
        self.time_function = time.localtime
        if self.gm_time:
            self.time_function = time.gmtime
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self,'connection',config,as_node_url)
        get_attribute(self,'timeout',config,str)
        get_attribute(self, 'gm_time', config, str)
        return config
    def _add_child(self, node):
        if isinstance(node,Formatter):
            self.formatter = node
        elif isinstance(node,Transporter):
            self.transporter = node
        ServiceNode._add_child(self, node)
    def scheduled_time(self):
        return self._timestamp
    def export(self, alarm):
        entry = {}
        entry['alarm'] = alarm.source.name
        self._timestamp = alarm.timestamp
        entry['timestamp'] = alarm.timestamp
        entry['critical_value'] = alarm.critical
        values = alarm.values
        for key in values.keys():
            entry[key] = values[key]
        entry['message'] = alarm.message
        if hasattr(alarm, 'subject'):
            entry['subject'] = alarm.subject
        data = self.formatter.format([entry])
        tries = alarm.source.send_retries + 1
        while tries:
            tries -= 1
            try:
                if self.connection.acquire(self.timeout):
                    try:
                        self.transporter.transport(data)
                        return
                    finally:
                        self.connection.release()
            except:
                msglog.log('broadway',msglog.types.WARN,
                           'Failed attempt to send alarm %s' % alarm)
                msglog.exception()
        else:
            raise MpxException('Export failed.')

class AlarmLogger(ServiceNode):
    def __init__(self):
        self.__lock = Lock()
        ServiceNode.__init__(self)
    def configure(self,config):
        ServiceNode.configure(self,config)
        set_attribute(self,'log',REQUIRED,config)
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self,'log',config,as_node_url)
        return config
    def start(self):
        self.log = as_node(self.log)
        ServiceNode.start(self)
    def stop(self):
        self.log = as_node_url(self.log)
        ServiceNode.stop(self)
    def export(self,alarm):
        self.__lock.acquire()
        try:
            self.log.add_entry([time.time(),alarm.source.name,alarm.timestamp,
                                alarm.critical,alarm.values,alarm.message])
        finally:
            self.__lock.release()
class LogAndExport(ServiceNode):
    def __init__(self):
        self._lock = Lock()
        self._started = 0
        self._alarm = [] # can have a whole MESS o' alarms at startup...
        self._scheduled = None
        self.trigger_node_url_posn = None # allow source stamping
        self.trigger_node_msg_posn = None # allow source stamping
        self._waiting_alarm_sid = None
        ServiceNode.__init__(self)
    def configure(self, config):
        ServiceNode.configure(self, config)
        set_attribute(self, 'log', REQUIRED, config)
    def configuration(self):
        config = ServiceNode.configuration(self)
        get_attribute(self, 'log', config, as_node_url)
        return config
    def start(self):
        self._lock.acquire()
        try:
            self.log = as_node(self.log)
            columns_node = self.log.get_child('columns')
            self.ts_position = columns_node.get_child('timestamp').position
            # Allow source stamping:
            if columns_node.has_child('trigger_node_url'):
                self.trigger_node_url_posn = columns_node.get_child('trigger_node_url').position
            if columns_node.has_child('trigger_node_msg'):
                self.trigger_node_msg_posn = columns_node.get_child('trigger_node_msg').position
            self._started = 1
        finally:
            self._lock.release()
        self.export_waiting_alarm()
        return ServiceNode.start(self)
    def stop(self):
        if not self._waiting_alarm_sid is None:
            try:
                scheduler.remove(self._waiting_alarm_sid)
            except: # SID may already have expired and been removed...
                msglog.exception()
            self._waiting_alarm_sid = None
        self._started = 0
        ServiceNode.stop(self)
        return
    def export(self, alarm, attempt=0):
        self._lock.acquire()
        try:
            if (not self._started):
                self._alarm.append(alarm)
                # No need to set scheduler here; start() will call 
                # export_waiting_alarm()...
                return
            # Even if this node is already started, do not attempt to 
            # export alarm unless the linked log node and its collector 
            # object are extant and started:
            if (self.log.collector is None):
                self._alarm.append(alarm)
                if (self._waiting_alarm_sid is None): # if we're not already scheduled, do it:
                    # Need to wait long enough for log.start() to finish creating
                    # and starting collector. ***GUESS*** 10.0 sec. Symptom of not
                    # waiting long enough: ENotStarted error raised below:
                    self._waiting_alarm_sid = scheduler.after(10.0, self.export_waiting_alarm, ())
                return
        finally:
            self._lock.release()
        self.log.collector.pause()
        try:
            try:
                if not self.log.collector.running:
                    raise ENotStarted('Collector not started yet.')
                entry = self.log.collector.get_entry()
                entry[self.ts_position] = time.time()
                # Stamp source, if target log columns support it:
                if isinstance(self.trigger_node_url_posn, int):
                    entry[self.trigger_node_url_posn] = as_node_url(alarm.source)
                if isinstance(self.trigger_node_msg_posn, int):
                    entry[self.trigger_node_msg_posn] = str(alarm)
                self.log.add_entry(entry)
                t = time.time()
                for child in self.log.get_child('exporters').children_nodes():
                    child.go(t) # starts threads for long ops
            except:
                msglog.exception()
                if attempt > alarm.source.send_retries:
                    msglog.log('broadway',msglog.types.WARN,
                               'Export of alarm failed, aborting send.')
                    raise MpxException('Log and export failed.')
                else:
                    msglog.log('broadway',msglog.types.WARN,
                               'Log on alarm failed, delaying 1.0 sec.')
                    self._lock.acquire()
                    try:
                        if self._scheduled != None:
                            scheduler.cancel(self._scheduled)
                        self._scheduled = scheduler.after(1,self.export,
                                                          (alarm,attempt+1))
                    finally:
                        self._lock.release()
        finally:
            self.log.collector.play()
        return
    ##
    # export_waiting_alarm: forces logging/export of self._alarm elements
    # if self.log.collector was None during export().
    # @todo May need to spin off thread(s), to avoid delaying Scheduler.
    #
    def export_waiting_alarm(self):
        if (self._started == 1) \
           and (not self.log.collector is None):
            if not self._waiting_alarm_sid is None:
                try:
                    scheduler.remove(self._waiting_alarm_sid)
                except: # SID may already have expired and been removed...
                    msglog.exception()
                self._waiting_alarm_sid = None
            while len(self._alarm) > 0:
                init_len = len(self._alarm)
                alarm = self._alarm.pop(0)
                self.export(alarm) # should leave alarm off of list...
                if init_len <= len(self._alarm):
                    break # failed to keep alarm off the list
        elif (len(self._alarm) > 0):
            self._waiting_alarm_sid = scheduler.after(10.0, self.export_waiting_alarm, ())
        return


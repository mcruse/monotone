"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
import select
import asyncore
import threading
from mpx.lib import msglog
from mpx.componentry import implements
from mpx.service.network.async.connection.interfaces import IChannelMonitor
from mpx.service.network.async.connection.trigger import Trigger
from mpx.service.network.utilities.counting import Counter

class ChannelMonitor(dict):
    implements(IChannelMonitor)
    DEFAULTPARAM = object()
    
    def __init__(self, timeout = 30, *args, **kw):
        super(ChannelMonitor, self).__init__(*args, **kw)
        self._monitor_lock = threading.Lock()
        self._monitor_flag = threading.Event()
        self._monitor_thread = None
        self._setup_poll_function()
        self._setup_trigger_channel()
        self.set_timeout(timeout)
    def is_monitoring_thread(self, thread = None):
        if thread is None:
            thread = threading.currentThread()
        return thread is self._monitor_thread
    def set_timeout(self, timeout):
        self._timeout = timeout
    def check_channels(self):
        self.trigger_channel.trigger_event()
    def has_channel(self, channel):
        return self.has_key(channel.file_descriptor())
    def add_channel(self, channel):
        self.setdefault(channel.file_descriptor(), channel)
    def remove_channel(self, channel):
        try:
            del(self[channel.file_descriptor()])
        except KeyError:
            return False
        else:
            return True
    def start_monitor(self):
        self._monitor_lock.acquire()
        try:
            if self._is_running():
                raise TypeError('Channels already being monitored.')
            self._monitor_thread = MonitorThread(self)
            self._monitor_thread.setDaemon(1)
            self._monitor_flag.set()
            self._monitor_thread.start()
        finally:
            self._monitor_lock.release()
    def stop_monitor(self, timeout = DEFAULTPARAM):
        self._monitor_lock.acquire()
        try:
            if not self._is_running():
                raise TypeError('Channel is not being monitored.')
            monitor_thread = self._monitor_thread
            self._monitor_flag.clear()
            self.trigger_channel.trigger_event()
        finally:
            self._monitor_lock.release()
        if timeout is not self.DEFAULTPARAM:
            monitor_thread.join(timeout)
    def shutdown_channels(self):
        for channel in self.values():
            if channel is not self.trigger_channel:
                channel.close()
        self.trigger_channel.trigger_event()
    def join_monitor(self, timeout = None):
        self._monitor_lock.acquire()
        monitor_thread = self._monitor_flag
        self._monitor_lock.release()
        if monitor_thread is not None:
            return monitor_thread.join(timeout)
    def is_running(self):
        self._monitor_lock.acquire()
        try:
            result = self._is_running()
        finally:
            self._monitor_lock.release()
        return result
    def run_monitor(self):
        # Create local references for efficiency of loop.
        timeout = self._timeout
        should_monitor = self._monitor_flag.isSet
        poll_function = self._poll_function
        while should_monitor():
            poll_function(timeout, self)
    def _is_running(self):
        thread = self._monitor_thread
        return thread and thread.isAlive()
    def _setup_poll_function(self):
        try: 
            select.poll()
        except: 
            self._poll_function = asyncore.poll
        else: 
            self._poll_function = asyncore.poll2
    def _setup_trigger_channel(self):
        assert getattr(self, '_trigger_channel', None) is None
        self.trigger_channel = Trigger(self)
    def __repr__(self):
        status = [self.__class__.__module__ + '.' + self.__class__.__name__]
        if self.is_running():
            status.append('active')
        else:
            status.append('inactive')
        status.append('at %#x' % id(self))
        status.append(dict.__repr__(self))
        return '<%s>' % ' '.join(status)

class MonitorThread(threading.Thread):
    tm_counter = Counter(0)
    def __init__(self, monitor):
        self.monitor = monitor
        self.tm_number = self.tm_counter.increment()
        threading.Thread.__init__(self, None, None, self._get_name())
    def run(self):
        self.monitor.run_monitor()
    def _get_name(self):
        return '<%s.%s %d at %#x>' % (self.__class__.__module__, 
                                      self.__class__.__name__, 
                                      self.tm_number, id(self))
    def __repr__(self):
        return '%s for %s' % (self._get_name(), repr(self.monitor))

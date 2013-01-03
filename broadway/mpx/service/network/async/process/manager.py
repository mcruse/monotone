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
from threading import Thread
from threading import Event
from mpx.service.network.async.connection import monitor
from mpx.service.network.async.connection import channel
from mpx.service.network.utilities.counting import Counter

class TransactionManager(Thread):
    tm_counter = Counter(0)
    def __init__(self, channelmonitor = None):
        self.tm_number = self.tm_counter.increment()
        self._keep_running = Event()
        self._
        super(TransactionManager, self).__init__(None, None, repr(self))
    def _set_monitor(self, channelmonitor = None):
        if channelmonitor is None:
            channelmonitor = monitor.ChannelMonitor()
        else:
            assert isinstance(channelmonitor, monitor.ChannelMonitor)
        self.monitor = channelmonitor
    def start(self):
        self._keep_running.set()
        super(TransactionManager, self).start()
    def stop(self):
        self._keep_running.clear()
    def stop_and_wait(self, timeout = None):
        self.stop()
        return self.join(timeout)
    def send_request(self, request):
        host = request.get_host()
        port = request.get_port()
        connectiontype = request.get_type()
        if not self._channels.has_key((host, port, connectiontype)):
            channel = channel.Channel(self.monitor)
            channel.setup_connection(host, port, connectiontype)
            self._channels[(host, port, connectiontype)] = channel
        channel = self._channels[(host, port, connectiontype)]
        return channel.send_request(request)
    def __repr__(self):
        return '<%s.%s %d at %#x>' % (self.__class__.__module__, 
                                      self.__class__.__name__, 
                                      self.tm_number, id(self))

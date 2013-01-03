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
from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from mpx.lib import msglog

from mpx.lib.exceptions import MpxException

from mpx.lib.scheduler import scheduler

from mpx.lib.threading import Lock

from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM

from mpx.lib.thread_pool import NORMAL

import time        

##
# An iterable circular buffer with a configurable max length
# that is used to manage kwh entries
class CircList(object):
    class Iterator:
        def __init__(self, data):
            self.data = data[:]
            self.data.reverse()
            return
        
        def __iter__(self):
            return self
            
        def next(self):
            if not self.data:
                raise StopIteration
            return self.data.pop()
            
    def __init__(self, length):
        self._data = []
        self._full = 0
        self._max = length
        self._cur = 0
        return

    def append(self, x):
        if self._full == 1:
            for i in range (0, self._cur - 1):
                self._data[i] = self._data[i + 1]
            self._data[self._cur - 1] = x
        else:
            self._data.append(x)
            self._cur += 1
            if self._cur == self._max:
                self._full = 1
        return

    def get(self):
        return self._data

    def remove(self):
        if (self._cur > 0):
            del self._data[self._cur - 1]
            self._cur -= 1
        return
        
    def clear(self):
        self._data = []
        self._cur = 0
        self._full = 0
        return

    def maxsize(self):
        return self._max

    def __len__(self):
        return self._cur

    def __str__(self):
        return ''.join(self._data)
        
    def __iter__(self):
        return CircList.Iterator(self._data)
        
class KwList(CircList):
    def __init__(self, length):
        super(KwList, self).__init__(length)
        self.__last_ts = time.time()
        self.__last_kwh = None
        self.__lock = Lock()
        return
        
    def add(self, kwh, ts):
        try:
            kwh = float(kwh)
        except:
            return
        if self.__last_kwh is None:
            self.__last_kwh = kwh
        self.__lock.acquire()
        try:
            if kwh < self.__last_kwh or ts < self.__last_ts:
                # either time shifted on us or our kwh rolled\reset.
                self.clear()
            self.__last_ts = ts
            self.__last_kwh = kwh
            self.append(KwEntry(kwh, ts))
        finally:
            self.__lock.release()
        return

    def moving_average(self):
        avg = None
        self.__lock.acquire()
        try:
            if len(self) >= 2:
                 s_kw_entry = self._data[0]
                 e_kw_entry = self._data[-1]
                 delta_s = e_kw_entry.get_ts() - s_kw_entry.get_ts()
                 delta_kwh = e_kw_entry.get_kwh() - s_kw_entry.get_kwh()
                 avg = delta_kwh / self._seconds_as_hours(delta_s)
        finally:
            self.__lock.release()
        return avg

    def _seconds_as_hours(self, seconds):
        return (seconds / 60.0) / 60.0
    
class KwEntry(object):
    def __init__(self, kwh, ts):
        self.__kwh = kwh
        self.__ts = ts
        return

    def get_ts(self):
        return self.__ts

    def get_kwh(self):
        return self.__kwh
                
##
# ION that **approximates** kw by referencing a kwh node.
# 
class Kwh2Kw(CompositeNode):
    def __init__(self):
        self._history = None
        self._history_lock = Lock()
        self._sid = None
        self._nid = 1
        self._poll_failure = False
        self._scheduled = None
        self.running = False
        super(Kwh2Kw, self).__init__()
        return
        
    def configure(self, cd):
        super(Kwh2Kw, self).configure(cd)
        set_attribute(self, 'link', REQUIRED, cd)
        # sample_period and window used to set the number of
        # samples that constitutes the size of the moving avg.
        set_attribute(self, 'sample_period', 10.0, cd, float)
        set_attribute(self, 'window', 120, cd, int)
        self._window_size = self.window / self.sample_period
        if self.running:
            # reconfigure things
            self.stop()
            self.start()
        return
               
    def configuration(self):
        cd = super(Kwh2Kw, self).configuration()
        get_attribute(self, 'link', cd)
        get_attribute(self, 'sample_period', cd)
        get_attribute(self, 'window', cd)
        return cd
        
    def start(self):
        super(Kwh2Kw, self).start()
        self.running = True
        self._history = KwList(self._window_size)
        self._sid = SM.create_polled({self._nid:self.link})
        # retrieve an initial value to start things off 
        value = ts = None
        result = SM.poll_all(self._sid)
        if result is None:
            # still waiting
            try:
                value = as_node(self.link).get()
                ts = time.time()
            except:
                pass
        else:
            try:
                value = result[self._nid]['value']
                ts = result[self._nid]['timestamp']
            except:
                pass
            if isinstance(value, MpxException):
                value = None
        if value and ts:
            self._history.add(value, ts)
        self._scheduled = scheduler.seconds_from_now_do(self.sample_period, self.run_update)
        return
        
    def stop(self):
        self.running = False
        self._history = None
        try:
            SM.destroy(self._sid)
        except:
            pass
        self._sid = None
        self._history_lock.acquire()
        try:
            self._history = None
            s = self._scheduled
            self._scheduled = None
            if s is not None:
                try:
                    s.cancel()
                except:
                    pass
        finally:
            self._history_lock.release()
        return
        
    ##
    # update() can be relatively slow, run it on a threadpool
    def run_update(self):
        NORMAL.queue_noresult(self.update)
        return
        
    def update(self):
        try:
            value = ts = None
            result = SM.poll_all(self._sid)
            if result is not None:
                value = result[self._nid]['value']
                ts = result[self._nid]['timestamp']
            self._history_lock.acquire()
            try:
                if value is None or isinstance(value, MpxException):
                    # there were problems collecting during this period, 
                    # our calculation should not proceed
                    self._history.clear()
                    if not self._poll_failure:
                        # log the failure, but don't spam the msglog
                        self._poll_failure = True
                        msglog.log('Kwh2Kw', msglog.types.WARN, 
                                   'Failed to retrieve data from %s' % self.link)
                else:
                    self._poll_failure = False
                    self._history.add(value, ts)
            finally:
                self._history_lock.release()
        except:
            msglog.exception()
        self._scheduled = scheduler.seconds_from_now_do(self.sample_period, self.run_update)
        return
            
    def get(self, skipCache=0):
        return self._history.moving_average()

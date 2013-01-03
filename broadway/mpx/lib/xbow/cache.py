"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
from mpx.lib.threading import Lock
from mpx.lib.scheduler import scheduler
from mpx.lib.exceptions import *

uint8_t = 1
uint16_t = 2

class XbowCache:
    def __init__(self, timeout, scan_time):
        #self._c == {group_id:{addr:last_msg}}
        self._c = {}
        self._cache_lock = Lock() #can add more granular locking, if need be
        self._subscr_list = {} # == {(group_id,addr):[call_back_meth]}  ... 
        self.timeout = timeout
        if not scan_time:
            self.scan_time = max(self.timeout / 4, 30)
        self._scan_scheduled = None
        
    def stop(self):
        s = self._scan_scheduled
        self._scan_scheduled = None
        if s is not None:
            try:
                s.cancel()
            except:
                pass
                
    def add_group(self, group_id):
        try:
            self._cache_lock.acquire()
            if not self._c.has_key(group_id):
                self._c[group_id] = {}
        finally:
            self._cache_lock.release()
            
    def get_group_ids(self):
        return self._c.keys()
        
    def add_group(self, group_id):
        self._c[group_id] = {}
            
    def add_mote(self, group_id, addr):
        try:
            self._cache_lock.acquire()
            if not self._c.has_key(group_id):
                raise EInvalidValue('cannot add addr to non-existant group', group_id, 'add_mote')
            if not self._c[group_id].has_key(addr):
                self._c[group_id][addr] = None
        finally:
            self._cache_lock.release()
            
    def get_mote_ids(self, group_id):
        return self._c[group_id].keys()
            
    def add_msg(self, msg):
        addr = msg.get_address()
        group_id = msg.get_group()
        id = (group_id, addr)
        try:
            self._cache_lock.acquire()
            if group_id not in self.get_group_ids():
                self.add_group(group_id)
            self._c[group_id][addr] = msg
            if id in self._subscr_list.keys():
                call_backs = self._subscr_list[(group_id, addr)]
                for cb in call_backs:
                    cb()
        finally:
            self._cache_lock.release() 
            
    def get_msg(self, group_id, addr):
        return self._c[group_id][addr]
                       
    def add_callback(self, id, cb):
        #id == (group_id, addr) tuple
        try:
            self._cache_lock.acquire()
            if id in self._subscr_list.keys():
                self._subscr_list[id].append(cb)
            else:
                self._subscr_list[id] = [cb]
                # if we're the only subscribed value, fire off the timeout scanner
                if len(self._subscr_list.keys()) == 1:
                    self.setup_subscr_timer()
        finally:
            self._cache_lock.release()
            
    def remove_callback(self, id, cb):
        # id == (group_id, addr) tuple
        # cb needed just in case there are more than one callback
        try:
            self._cache_lock.acquire()
            if id in self._subscr_list.keys():
                try:
                    self._subscr_list[id].remove(cb)
                except:
                    # hrm, cb went missing
                    pass
        finally:
            self._cache_lock.release()
            
    def setup_subscr_timer(self):
        self._scan_scheduled = scheduler.at(self.next_scan_time(), self.scan, ())
        
    def next_scan_time(self):
        now = int(time.time())
        last_time = (now - (now % self.scan_time))
        next_time = last_time + self.scan_time
        return float(next_time)
        
    def scan(self):
        try:
            # see prev comment about improving lock granularity
            self._cache_lock.acquire()
            for id in self._subscr_list.keys():
                group_id = id[0]
                addr = id[1]
                t = time.time()
                if t - self._c[group_id][addr].time_stamp > self.timeout:
                    # set the msg to None which will result in the ion side generating ETimeout COV msg
                    self._c[group_id][addr] = None
                    for cb in self._subscr_list[id]:
                        try:
                            cb()
                        except:
                            msglog.exception()
            if self._subscr_list.keys():
                self.setup_subscr_timer()
            else:
                self._scan_scheduled = None
        finally:
            self._cache_lock.release()

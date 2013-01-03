"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
from moab.linux.lib import uptime
from threading import Event as Flag

class ItemCache(dict):
    def __init__(self, *args):
        self.born = uptime.secs()
        self.touched = uptime.secs()
        super(ItemCache, self).__init__(*args)
    def touch(self):
        self.touched = uptime.secs()
    def since_born(self):
        return uptime.secs() - self.born
    def since_touched(self):
        return uptime.secs() - self.touched
    def read(self, count=None):
        self.touch()
        keys = self.keys()
        if isinstance(count, int):
            keys = keys[0: count]
        return map(self.pop, keys)

class SimpleQueue(list):
    def __init__(self, *args):
        super(SimpleQueue, self).__init__(*args)
        self.activate()
    def active(self):
        return not self._active.isSet()
    def activate(self):
        self._active = Flag()
    def deactivate(self):
        self._active.set()
    def __call__(self):
        self.deactivate()
        return self

class EventQueue(list):
    def __init__(self, depth = 3):
        super(EventQueue, self).__init__()
        for i in range(depth):
            self.append(SimpleQueue())
        return
    def enqueue(self, event):
        while not self.queue.active():
            time.sleep(.01)
        return self.queue.append(event)
    def dequeue(self, index = 0):
        return self.queue.pop(index)
    def popqueue(self):
        self.append(SimpleQueue())
        return list.pop(self, 0)()
    def __len__(self):
        return len(self.queue)
    def __get_queue(self): return self[0]
    queue = property(__get_queue)


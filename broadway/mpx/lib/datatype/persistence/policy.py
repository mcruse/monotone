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
import threading
from mpx.lib.scheduler import scheduler
from mpx.componentry import implements
from mpx.lib.datatype.persistence.interfaces import IStoragePolicy

class StoragePolicy(object):
    implements(IStoragePolicy)
    def __init__(self):
        self.modified = {}
        self.manager = None
    def set_manager(self, manager):
        self.manager = manager
    def get_manager(self):
        return self.manager
    def note_modified(self, persistent):
        persistent.set_unsaved()
        self.modified[persistent.get_oid()] = persistent
    def commit(self):
        map(self.manager.store, self.modified.values())
        self.modified.clear()
    def terminate(self):
        self.commit()
        self.manager = None

class ChangeCountPolicy(StoragePolicy):
    def __init__(self, max_changes = 1):
        super(ChangeCountPolicy, self).__init__()
        self.max_changes = max_changes
        self.change_count = 0
    def note_modified(self, persistent):
        super(ChangeCountPolicy, self).note_modified(persistent)
        self.change_count += 1
        if self.change_count >= self.max_changes:
            self.commit()
    def commit(self):
        super(ChangeCountPolicy, self).commit()
        self.change_count = 0
        
class TimedPolicy(StoragePolicy):
    def __init__(self, seconds):
        super(TimedPolicy, self).__init__()
        self.seconds = seconds
        self.lock = threading.Lock()
        self.scheduled = None
    def note_modified(self, persistent):
        self.lock.acquire()
        try:
            super(TimedPolicy, self).notify_modified(persistent, modified)
            if self.scheduled is None:
                self.scheduled = scheduler.after(self.seconds, self.commit)
        finally: self.lock.release()
    def commit(self):
        self.lock.acquire()
        try:
            super(TimedPolicy, self).commit()
            if self.scheduled: 
                self.scheduled.cancel()
            self.scheduled = None
        finally: self.lock.release()
    def terminate(self):
        self.lock.acquire()
        try:
            if self.scheduled:
                self.scheduled.cancel()
            self.scheduled = None
        finally: self.lock.release()
        super(TimedPolicy, self).terminate()

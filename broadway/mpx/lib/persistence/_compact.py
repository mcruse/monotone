"""
Copyright (C) 2011 Cisco Systems

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
"""
    Import this module into the interactive prompt (i.e., 'console'), 
    to automatically compact existing Map Storage database files.  
    This will shrink existing GDBM DB files during runtime, but makes 
    no changes otherwise, and does not require patch or import/reload 
    of storage module.
    
    # To import.
    from mpx.lib.persistence import _compact
    
    # To Run once.
    _compact.compact()
    
    # To Run periodically (default period runs once per day).
    _compact.start_compactor()
    
    # Stop currently running periodic compactor.
    _compact.stop_compactor()
"""
from time import sleep
from threading import Event
from threading import Thread
from mpx.lib import msglog
from mpx.lib.persistence.storage import MapStorage
COMPACTOR = None

def compact():
    storages = []
    for storagemap in MapStorage.filesysmap.values():
        for storage in storagemap.values():
            if isinstance(storage, MapStorage):
                storages.append(storage)
    for storage in storages:
        if storage.opened() and hasattr(storage.database, "reorganize"):
            storage.storagelock.acquire()
            try:
                packed = storage.database.reorganize()
            except:
                msglog.warn("Compact DBM file %r failed." % storage.filepath)
                msglog.exception(prefix="handled")
            else:
                msglog.inform("Compacted DBM file %r." % storage.filepath)
            finally:
                storage.storagelock.release()
    return len(storages)

class Compactor(Thread):
    def __init__(self, period=24*60*60, *args, **kw):        
        self.period = period
        self.cancelled = Event()
        super(Compactor, self).__init__(*args, **kw)
    def start(self):
        if not self.isDaemon():
            self.setDaemon(True)
        return super(Compactor, self).start()
    def stop(self, blocking=False, timeout=15):
        self.cancelled.set()
        if blocking:
            self.join(timeout)
        return self.isAlive()
    def run(self):
        while not self.cancelled.isSet():
            try:
                packed = compact()
            except:
                msglog.error("Compactor failed to run compact().")
                msglog.exception(prefix="handled")
            else:
                msglog.debug("Compacted %d DB files." % packed)
            self.cancelled.wait(self.period)
        msglog.inform("Compactor thread exiting run-loop.")

def start_compactor(period=24*60*60):
    global COMPACTOR
    if COMPACTOR:
        raise Exception("Must run stop_compactor() before restarting.")
    COMPACTOR = Compactor(period)
    COMPACTOR.start()

def stop_compactor():
    global COMPACTOR
    if not COMPACTOR:
        raise Exception("Must run start_compactor() before stopping.")
    COMPACTOR.stop(True, 60)
    COMPACTOR = None

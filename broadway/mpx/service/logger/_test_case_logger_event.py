"""
Copyright (C) 2010 2011 Cisco Systems

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
##
# Test cases to exercise the PeriodicColumn class.

from mpx_test import DefaultTestFixture, main

import time

from mpx.lib import pause

from mpx.lib.event import EventConsumerAbstract
from mpx.lib.log import LogAddEntryEvent

from mpx.lib.node import CompositeNode

from mpx.lib.threading import Thread
from mpx.lib.threading import Lock

from mpx.service.logger.periodic_column import PeriodicColumn
from mpx.service.logger.periodic_log import PeriodicLog

class TestCase(DefaultTestFixture):
    def test_add_entry_event(self):
        class Consumer(EventConsumerAbstract):
            def __init__(self, *args, **kw):
                EventConsumerAbstract.__init__(self, *args, **kw)
                self.entries = []
                self.errors = []
                self.lock = Lock()
            def event_thread(self,event):
                # The values returned in the event:
                values = event.values
                # The column as read from the source Log instance:
                column_dict = event.source[event.seq]
                # A map of COLUMN_DICT keys to VALUES indexes.
                column_value_map = {
                    'c0':0,
                    }
                # Validate that the list of values matches the actual column in
                # the log:
                for key,index in column_value_map.items():
                    if not column_dict.has_key(key):
                        self.errors.append('column_dict has no %r key.' % key)
                        return
                    if index >= len(values):
                        self.errors.append('Index(%r) >= len(values:%r).' %
                                           (index, len(values)))
                        return
                    if column_dict[key] != values[index]:
                        self.errors.append(
                            'column_dict[%r]:%r != values[%r]:%r' % (
                            key, column_dict[key], index, values[index]))
                        return
                self.lock.acquire()
                try:
                    # If any entries are left, the test will fail.
                    self.entries.remove(values)
                except:
                    # Also, if errors is not empty the test will fail.
                    self.errors.append("Failed to find %r in entries." %
                                       values)
                self.lock.release()
            def event_handler(self,event):
                t = Thread(target=self.event_thread, args=(event,))
                t.start()
                return
        consumer = Consumer()
        p = PeriodicLog()
        p.configure({'name':'log','parent':None, 'period':0})
        h = CompositeNode()
        h.configure({'name':'columns','parent':p})
        c = PeriodicColumn()
        c.configure({'position':0, 'name':'c0', 'parent':h,
                     'function':'None',})
        p.event_subscribe(consumer, LogAddEntryEvent)
        p.start()
        try:
            for c0 in range(0,10):
                entry = [c0,]
                consumer.entries.append(entry)
                p.add_entry(entry)
            t1 = time.time()
            while consumer.entries:
                if (time.time() - t1) >= 1.0:
                    msgs = [
                        "Failed to recieve matching events after 1 second."
                        ]
                    msgs.extend(consumer.errors)
                    self.fail('\n'.join(msgs))
                pause(0.1)
        finally:
            p.stop()
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

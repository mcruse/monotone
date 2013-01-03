"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
# @todo  Need to add a test that does a trim greater than for a value
#        that crosses a seq barrier, then closes everything and re-opens 
#        it to make sure that the next entry added picks up with a previously
#        unused seq number.
from mpx_test import DefaultTestFixture, main

import os
import time

from mpx import properties

from mpx.lib import log
from mpx.lib import pause

from mpx.lib.event import EventConsumerAbstract

from mpx.lib.threading import Thread
from mpx.lib.threading import Lock

def _get_stream_length(stream):
    length = 0
    for entry in stream:
        length += 1
    return length

class TestCase(DefaultTestFixture):
    ##
    # Sets up self.log who is configured to have columns:
    # timestamp, reverse, c2, c3, c4 for seqs 0-19, 40-59, 80-99, 120-139 
    # and columns timestamp, reverse, c2, c3 for seqs: 20-39, 60-79, 100-119,
    # 140-159
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self._build_log('new_log_test', log)
        return
    def tearDown(self):
        try:
            self.log.destroy()
        finally:
            DefaultTestFixture.tearDown(self)
        return
    def test_upgrade(self):
        self.log.destroy()
        try:
            os.remove('/tmp/upgrade_test.log')
        except OSError:
            pass
        from mpx.upgrade.log import log_0
        self._build_log('upgrade_test', log_0)
        first = self.log[0:5]
        middle = self.log[10:15]
        end = self.log[-5:]
        new = log.Log('upgrade_test')
        self.failIf(os.path.exists(self.log.filename),
                    'Upgrade failed to remove old log file')
        self.failUnless(new[0:5][:] == first,
                        'New log beginning does not match old')
        self.failUnless(new[10:15][:] == middle,
                        'New log beginning does not match old')
        self.failUnless(new[-5:][:] == end,
                        'New log beginning does not match old')
        self.log = new
        return
    def _build_log(self, name, module):
        self.log = module.Log(name)
        # __init__(self, name = None, position = None, sort_order = None):
        self.c2 = module.ColumnConfiguration('c2', 2, 'none')
        self.c3 = module.ColumnConfiguration('c3', 3, 'none')
        self.c4 = module.ColumnConfiguration('c4', 4, 'none')
        self.timestamp = module.ColumnConfiguration('timestamp', 0,
                                                    'ascending')
        self.reverse = module.ColumnConfiguration('reverse', 1, 'descending')
        self.length = 160
        reverse = self.length
        for count in range(0, 4):
            self.log.configure([self.timestamp, self.reverse, self.c2,
                                self.c3, self.c4])
            for i in range(0, 20):
                t = time.time()
                if count == 0 and i == 0:
                    self.t1 = t
                self.log.add_entry([t, reverse, 2, 3, 4])
                reverse -= 1
            
            self.log.configure([self.timestamp, self.reverse,
                                self.c2, self.c3])
            for i in range(0, 20):
                t = time.time()
                self.log.add_entry([t, reverse, 2, 3])
                reverse -= 1
        self.t2 = t
        return
    def test_data_manager_configuration(self):
        dm = self.log.data_manager
        names = dm.get_names()
        self.failUnless(names == [self.timestamp.name, self.reverse.name,
                                  self.c2.name, self.c3.name, '_seq'],
                        'Data Manager failed to return correct ' +
                        'column names with None for seq')
        names = dm.get_names(0)
        self.failUnless(names == [self.timestamp.name, self.reverse.name,
                                  self.c2.name, self.c3.name, self.c4.name,
                                  '_seq'],
                        'Data Manager failed to return correct ' +
                        'column names for first record')
        names = dm.get_names(19)
        self.failUnless(names == [self.timestamp.name, self.reverse.name,
                                  self.c2.name, self.c3.name, self.c4.name,
                                  '_seq'],
                        'Data Manager failed to return correct ' +
                        'column names for 19th record, one before new config')
        names = dm.get_names()
        self.failUnless(names == [self.timestamp.name, self.reverse.name,
                                  self.c2.name, self.c3.name, '_seq'],
                        'Data Manager failed to return correct ' +
                        'column names 20th record, first after reconfig')
        return
    def test_data_manager_trim(self):
        dm = self.log.data_manager
        dm.trim(5, 'le')
        names = dm.get_names(0)
        self.failUnless(names == [self.timestamp.name, self.reverse.name,
                                  self.c2.name, self.c3.name, self.c4.name,
                                  '_seq'],
                        'Data Manager failed to return correct ' +
                        'column names for first record')
        dm.trim(20, 'le')
        keys = dm.column_data.keys()[:]
        keys.sort()
        self.failUnless(keys == [20,40,60,80,100,120,140],
                        'DataManager failed to remove configuration' +
                        ' data for rows that were trimmed')
        dm.trim(33,'le')
        keys = dm.column_data.keys()[:]
        keys.sort()
        self.failUnless(keys == [20,40,60,80,100,120,140],
                        'DataManager failed ' +
                        'to removed configuration data unessicarily')
        dm.trim(135,'ge')
        keys = dm.column_data.keys()[:]
        keys.sort()
        self.failUnless(keys == [20,40,60,80,100,120,140],
                        'DataManager failed ' +
                        'to removed configuration data unessicarily')
        dm.trim(100,'le')
        keys = dm.column_data.keys()[:]
        keys.sort()
        self.failUnless(keys == [100,120,140], 'DataManager failed ' +
                        'to removed configuration data unessicarily')
        dm.trim(0,'ge')
        keys = dm.column_data.keys()[:]
        keys.sort()
        self.failUnless(keys == [140], 'DataManager failed ' + \
                        'to correctly retain configuration when log deleted.')
        return
    def test_get_range_ascending(self):
        range = self.log.get_range('timestamp', self.t1, self.t2)
        self.failUnless(_get_stream_length(range) == (self.length),
                        'Wrong number of entries returned, ' + 
                        '_get_stream_length(range) == %s' %
                        _get_stream_length(range))
        self.failUnless(range[0]['timestamp'] == self.t1,
                        'Incorrect first entry')
        self.failUnless(range[-1]['timestamp'] == self.t2,
                        'Incorrect last entry')
        return
    def test_get_range_descending(self):
        range = self.log.get_range('reverse', 159, 100)
        self.failUnless(_get_stream_length(range) == 60,
                        'Wrong number of entries returned, ' + 
                        '_get_stream_length(range) == %s' %
                        _get_stream_length(range))
        self.failUnless(range[0]['reverse'] == 159, 'Incorrect first entry')
        self.failUnless(range[-1]['reverse'] == 100, 'Incorrect last entry')
        return
    def test_get_range_none(self):
        range = self.log.get_range('c2', 2, 2)
        self.failUnless(_get_stream_length(range) == self.length,
                        'Wrong number of entries returned, ' + 
                        '_get_stream_length(range) == %s' %
                        _get_stream_length(range))
        return
    def test_get_slice_ascending(self):
        self._get_slice_ascending()
        return
    def _get_slice_ascending(self):
        slice = self.log.get_slice('timestamp', self.t1, self.t2)
        self.failUnless(_get_stream_length(slice) == (self.length - 1),
                        'Wrong number of entries returned')
        self.failUnless(slice[0]['timestamp'] == self.t1,
                        'Incorrect first entry')
        return
    def test_get_slice_seq(self):
        s1 = self.log[0]
        self.failUnless(s1['timestamp'] == self.t1, 'Incorrect first item')
        s2 = self.log[-1]
        self.failUnless(s2['timestamp'] == self.t2,
                        'Incorrect last item, s2 = %s, t2 = %s' %
                        (s2, self.t2))
        s = self.log[:]
        self.failUnless(s[0]['timestamp'] == self.t1, 'Incorrect first entry')
        self.failUnless(s[-1]['timestamp'] == self.t2, 'Incorrect last entry')
        return
    def test_get_slice_descending(self):
        s = self.log.get_slice('reverse', 160, 1)
        self.failUnless(_get_stream_length(s) == (self.length - 1),
                        'Incorrect number of items')
        self.failUnless(s[0]['timestamp'] == self.t1, 'Incorrect first item')
        self.failUnless(s[-1]['reverse'] == 2, 'Incorrect last item')
        return
    def test_get_range_values_ascending(self):
        range = self.log.get_range_values('timestamp', self.t1, self.t2)
        self.failUnless(_get_stream_length(range) == (self.length),
                        'Wrong number of entries returned, ' + 
                        '_get_stream_length(range) == %s' %
                        _get_stream_length(range))
        self.failUnless(range[0][0] == self.t1, 'Incorrect first entry')
        self.failUnless(range[-1][0] == self.t2, 'Incorrect last entry')
        return
    def test_get_range_values_descending(self):
        range = self.log.get_range_values('reverse', 159, 100)
        self.failUnless(_get_stream_length(range) == 60,
                        'Wrong number of entries returned, ' + 
                        '_get_stream_length(range) == %s' %
                        _get_stream_length(range))
        self.failUnless(range[0][1] == 159, 'Incorrect first entry')
        self.failUnless(range[-1][1] == 100, 'Incorrect last entry')
        return
    def test_get_range_values_none(self):
        range = self.log.get_range_values('c2', 2, 2)
        self.failUnless(_get_stream_length(range) == self.length,
                        'Wrong number of entries returned, ' + 
                        '_get_stream_length(range) == %s' %
                        _get_stream_length(range))
        return
    def test_get_slice_values_ascending(self):
        self._get_slice_values_ascending()
        return
    def _get_slice_values_ascending(self):
        slice = self.log.get_slice_values('timestamp', self.t1, self.t2)
        self.failUnless(_get_stream_length(slice) == (self.length - 1),
                        'Wrong number of entries returned')
        self.failUnless(slice[0][0] == self.t1, 'Incorrect first entry')
        return
    def test_get_slice_values_descending(self):
        s = self.log.get_slice_values('reverse', 160, 1)
        self.failUnless(_get_stream_length(s) == (self.length - 1),
                        'Incorrect number of items')
        self.failUnless(s[0][0] == self.t1, 'Incorrect first item')
        self.failUnless(s[-1][1] == 2, 'Incorrect last item')
        return
    def test_data_loss(self):
        self.log.trim_ge('_seq',0)
        self.log._write_queue()
        self.log._trim_lock.acquire()
        self.log._write_lock.acquire()
        try:
            entries = []
            reverse = -1
            for i in range(0, 5):
                t = time.time()
                entries.append([t, reverse, 2, 3])
                self.log.add_entry(entries[-1])
                reverse -= 1
                pause(.1)
        finally:
            self.log._write_lock.release()
            self.log._trim_lock.release()
        self.log._write_queue()
        data = self.log.get_range('timestamp',0,time.time())
        self.failUnless(data[0]['timestamp'] == entries[0][0] and 
                        data[-1]['timestamp'] == entries[-1][0], 
                        'Log failed to get correct beginning or end')
        self.failUnless(len(data[:]) == len(entries), 
                        'Some entries lossed during trim')
        return
    def test_trim_gt_ascending(self):
        self.log.trim_gt('_seq', 115)
        self.failUnless(self.log[-1] == self.log[115])
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[-2] == 100, 'Failed to clean column_data')
        return
    def test_trim_lt_ascending(self):
        self.log.trim_lt('_seq', 25)
        self.failUnless(
            _get_stream_length(self.log.get_slice('_seq', 0, 26)) == 1
            )
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[0] == 20, 'Failed to clean column_data')
        return
    def test_trim_gt_descending(self):
        self.log.trim_gt('reverse', 135)
        self.failUnless(
            _get_stream_length(self.log.get_slice('_seq', 0, 26)) == 1
            )
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[0] == 20, 'Failed to clean column_data')
        return
    def test_trim_lt_descending(self):
        self.log.trim_lt('reverse', 45)
        self.failUnless(self.log[-1] == self.log[115])
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[-2] == 100, 'Failed to clean column_data')
        return
    def test_trim_ge_ascending(self):
        self.log.trim_ge('_seq', 115)
        self.failUnless(self.log[-1] == self.log[114])
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[-2] == 100, 'Failed to clean column_data')
        return
    def test_trim_le_ascending(self):
        self.log.trim_le('_seq', 25)
        self.failUnless(
            _get_stream_length(self.log.get_slice('_seq',0,27)) == 1
            )
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[0] == 20, 'Failed to clean column_data')
        return
    def test_trim_ge_descending(self):
        self.log.trim_ge('reverse', 135)
        self.failUnless(
            _get_stream_length(self.log.get_slice('_seq',0,27)) == 1
            )
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[0] == 20, 'Failed to clean column_data')
        return
    def test_trim_le_descending(self):
        self.log.trim_le('reverse', 45)
        self.failUnless(self.log[-1] == self.log[114])
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless(seqs[-2] == 100, 'Failed to clean column_data')
        return
    def test_trim_ge_below(self):
        self.log.trim_ge('_seq', -1)
        self.failUnless(_get_stream_length(self.log[:]) == 0)
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless((len(seqs) == 1) and (seqs[0] == 140),
                        'Failed to clean column_data')
        return
    def test_trim_ge_above(self):
        self.log.trim_ge('_seq', 180)
        self._get_slice_ascending()
        return
    def test_trim_le_above(self):
        self.log.trim_le('reverse', 160)
        self.failUnless(_get_stream_length(self.log[:]) == 0)
        seqs = self.log.data_manager.column_data.keys()
        seqs.sort()
        self.failUnless((len(seqs) == 1) and (seqs[0] == 140),
                        'Failed to clean column_data')
        return
    def test_trim_le_below(self):
        self.log.trim_le('reverse', 0)
        self._get_slice_ascending()
        return
    def test_get_range_consistency(self):
        range = self.log.get_range('reverse',140,139)
        t1 = range[0]['reverse']
        t2 = range[1]['reverse']
        r1 = self.log.get_range('reverse',t1,t2)
        r2 = self.log.get_range('reverse',t1,t2)
        self.failUnless(_get_stream_length(r1) == _get_stream_length(r2), 
                        'Returned different length ranges for same range')
        self.failUnless(r1[0] == r2[0], 'First entries do not match.')
        self.failUnless(r1[-1] == r2[-1],'Last entries do not match.')
        return
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
                    'timestamp':0, 'reverse':1, 'c2':2, 'c3':3
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
        self.log.event_subscribe(consumer, log.LogAddEntryEvent)
        reverse = -1
        for i in range(0, 5):
            t = time.time()
            entry = [t, reverse, 2, 3]
            consumer.entries.append(entry)
            self.log.add_entry(entry)
            reverse -= 1
            # pause(.1)
        t1 = time.time()
        while consumer.entries:
            if (time.time() - t1) >= 1.0:
                msgs = ["Failed to recieve matching events after 1 second."]
                msgs.extend(consumer.errors)
                self.fail('\n'.join(msgs))
            pause(0.1)
        return
if(__name__ == '__main__'):    
    main()

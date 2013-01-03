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
import time as _time
from random import random
from threading import Event
import moab.linux.lib.uptime as uptime
import mpx.lib.scheduler
from mpx.lib import pause
from mpx.lib import msglog
from mpx_test import main
from mpx_test import DefaultTestFixture
from mpx.lib.exceptions import EOverflow
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.threading import Lock

debug = 0
disable_others = 1

class mytime(object):
    def __init__(self, systime):
        self._skewlock = Lock()
        self._skewdetected = Event()
        self.base_time_time = systime
        self.base_uptime_time = uptime.secs()
    def notify_detected(self):
        self._skewlock.acquire()
        self._skewdetected.set()
        self._skewlock.release()
    def await_detection(self, timeout = None):
        self._skewlock.acquire()
        self._skewdetected.clear()
        self._skewlock.release()
        return self._skewdetected.wait(timeout)
    def time(self):
        dtime = uptime.secs() - self.base_uptime_time
        comp_time = dtime + self.base_time_time
        if debug:
            print 'mytime.time() returning %f.' % comp_time
        return comp_time
    def skew_base_time(self, skew):
        self.base_time_time = self.base_time_time + skew

class TestCase(DefaultTestFixture):
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.callback_count = 0
    def tearDown(self):
        DefaultTestFixture.tearDown(self)
        # Restore scheduler's time
        mpx.lib.scheduler._scheduler.time = _time
    def _wait_for_skew_detection(self, scheduler, timerep, timeout):
        if debug:
            print '%f: Entering _wait_for_skew_detection' % uptime.secs()
        scheduler.set_checktime_callback(timerep.notify_detected)
        timerep.await_detection(timeout)
        scheduler.set_checktime_callback(None)
        if debug:
            print '%f: Returning from _wait_for_skew_detection' % uptime.secs()
    def callback(self, *args):
        #print len(args)
        if len(args) == 2:
            #append something to the passed in args
            args[1].append(args[0])
        if debug:
            print '%f: In callback with %s.' % (uptime.secs(), str(args))
    def callback2(self, *args):
        self.callback_count = self.callback_count + 1
        if debug:
            print '%f: In callback2 with %s.' % (uptime.secs(),str(args))     
    def test_create_schedule(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        s.stop()
    def test_at_do(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.at_time_do(_time.time() + 2, self.callback, 'a')
        if len(s._entries) - 1:
            if s._entries[0] != a:
                raise 'Schedule entry mismatch after one add'
        else:
            raise 'Schedule entry not added'
        pause(3)
        if len(s._entries) - 1:
            raise 'Schedule entry did not disappear'
        s.stop()
        s.cancel(a)
    def test_at_do_callback(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        b=[] #add something to this list in the callback
        a = s.at_time_do(_time.time() + 2, self.callback, 'c', b)
        if len(s._entries) - 1:
            if s._entries[0] != a:
                raise 'Schedule entry mismatch after one add'
        else:
            raise 'Schedule entry not added'
        pause(3)
        if len(s._entries) - 1:
            raise 'Schedule entry did not disappear'
        if len(b) == 0:
            raise 'Callback did not run'
        if b[0] != 'c':
            raise 'No match on added object'
        s.stop()
        s.cancel(a)
    def test_cancel(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.at_time_do(_time.time() + 2, self.callback, 'd')
        b = s.at_time_do(_time.time() + 3, self.callback, 'e')
        if len(s._entries) < 3:
            raise 'Schedule entries not added for cancel test'
        s.cancel(b)
        if len(s._entries) != 2:
            raise 'There should be exactly one entry in schedule list'
        a.cancel()
        if len(s._entries) != 1:
            raise 'There should be exactly zero entries in schedule list'
        s.stop()
    def test_at_do_past(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        #this one should execute immediately
        a = s.at_time_do(_time.time() - 1, self.callback, 'a')
        b = s.at_time_do(_time.time() + 3, self.callback, 'b')
        pause(0.1)
        if len(s._entries) != 2:
            raise 'There should be exactly one entry in schedule list'
        b.cancel()
        if len(s._entries) != 1:
            raise 'There should be exactly zero entries in schedule list'
        s.stop()
    def test_cancel_nonexistant(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.at_time_do(_time.time() - 1, self.callback, 'a')  #this one should execute immediately
        b = s.at_time_do(_time.time() + 3, self.callback, 'b')
        pause(0.1)
        if len(s._entries) != 2:
            raise 'There should be exactly one entry in schedule list'
        s.cancel(a)
        if len(s._entries) != 2:
            raise 'There should be exactly one entry in schedule list after cancel (%s)' % str(s._entries)
        b.cancel()
        if len(s._entries) != 1:
            raise 'There should be exactly zero entries in schedule list'
        s.stop()
    def test_at(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.at(_time.time() + 2, self.callback)
        if len(s._entries) - 1:
            if s._entries[0] != a:
                raise 'Schedule entry mismatch after one add'
        else:
            raise 'Schedule entry not added'
        pause(3)
        if len(s._entries) - 1:
            raise 'Schedule entry did not disappear'
        s.stop()
        s.cancel(a)
    def test_after(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.after(2, self.callback)
        if len(s._entries) - 1:
            if s._entries[0] != a:
                raise 'Schedule entry mismatch after one add'
        else:
            raise 'Schedule entry not added'
        pause(3)
        if len(s._entries) - 1:
            raise 'Schedule entry did not disappear'
        s.stop()
        s.cancel(a)
    def test_seconds_from_now_do(self):
        if disable_others:
            return
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.seconds_from_now_do(2, self.callback, 'a')
        if len(s._entries) - 1:
            if s._entries[0] != a:
                raise 'Schedule entry mismatch after one add'
        else:
            raise 'Schedule entry not added'
        pause(3)
        if len(s._entries) - 1:
            raise 'Schedule entry did not disappear'
        s.stop()
        s.cancel(a)
    def test_recurring_items(self):
        if disable_others:
            return
        exp_count = 6
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        #mpx.lib.scheduler.debug = 1
        a = s.every(1, self.callback2)
        pause(exp_count - 1)
        s.stop()
        s.cancel(a)
        # Our callback should be called around exp_count times
        diff = abs(exp_count - self.callback_count)
        if diff > 1:
            cbcount = self.callback_count
            raise "Callback count should be %d, %d." % (exp_count, cbcount)
    def test_time_changing_backward_1(self):
        check_period = mpx.lib.scheduler._scheduler.time_check_period
        otime = mytime(_time.time())
        mpx.lib.scheduler._scheduler.time = otime
        mpx.lib.scheduler.entries.time = otime
        mpx.lib.scheduler._scheduler.debug = debug
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.at_time_do(_time.time() + check_period + .5,self.callback, 'b')
        mpx.lib.scheduler._scheduler.time.skew_base_time(check_period * -5)
        # Wait until the skew has been detected or a timeout
        self._wait_for_skew_detection(s, otime, check_period+1.0)
        if len(s._entries) != 2:
            raise "Schedule entry disappeared when it shouldn't have!"
        s.cancel(a)
        s.stop()        
    def test_time_changing_backward_2(self):
        check_period = mpx.lib.scheduler._scheduler.time_check_period
        otime = mytime(_time.time())
        mpx.lib.scheduler._scheduler.time = otime
        mpx.lib.scheduler.entries.time = otime
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        call_list = []
        c = s.at_time_do(_time.time() + check_period + .95,
                         self.callback, 'c', call_list)
        a = s.at_time_do(_time.time() + check_period + .5,
                         self.callback, 'a', call_list)
        b = s.seconds_from_now_do(check_period + .75,
                         self.callback, 'b', call_list)
        types = tuple(map(type, (a, b, c)))
        entries = [entry for entry in s._entries if type(entry) in types]
        if entries[0] is not a:
            raise "First should be %s, not %s" % (str(a), str(entries[0]))
        if entries[1] is not b:
            raise "Second should be %s, not %s" % (str(b), str(entries[1]))
        if entries[2] is not c:
            raise "Third should be %s, not is %s" % (str(c), str(entries[2]))
        mpx.lib.scheduler._scheduler.time.skew_base_time(check_period * -5)
        # Wait until the skew has been detected or a timeout
        self._wait_for_skew_detection(s, otime, check_period+2.0)
        entries = [entry for entry in s._entries if type(entry) in types]
        # OK, the order should now be b, a, c
        if entries[0] is not b:
            raise "First should be %s, not %s" % (str(b), str(entries[0]))
        if entries[1] is not a:
            raise "Second should be %s, not %s" % (str(a), str(entries[1]))
        if entries[2] is not c:
            raise "Third should be %s, not %s" % (str(c), str(entries[2]))
        s.cancel(a)
        s.cancel(b)
        s.cancel(c)
        s.stop()
    def test_time_changing_forward(self):
        check_period = mpx.lib.scheduler._scheduler.time_check_period
        otime = mytime(_time.time())
        mpx.lib.scheduler._scheduler.time = otime
        mpx.lib.scheduler.entries.time = otime
        mpx.lib.scheduler._scheduler.debug = debug
        s = mpx.lib.scheduler.AutoStartScheduler()
        s.setdebug(debug)
        a = s.at_time_do(_time.time() + (check_period * 2.0),
                         self.callback, 'b')
        mpx.lib.scheduler._scheduler.time.skew_base_time(check_period * 4.0)
        # Wait until the skew has been detected or a timeout
        self._wait_for_skew_detection(s, otime, check_period+1.0)
        if len(s._entries) != 1:
            raise "Schedule entry did not disappear when it should have!"
        s.cancel(a)
        s.stop()
    def test_create_many(self):
        cursystime = _time.time()
        curuptime = uptime.secs()
        # Create 1000 entries
        count = 1000
        # Earliest entry executes in 20 seconds.
        offset = 60
        # Schedule for random value between offset and offset + range
        variation = 180
        # Generate offset list
        offsets = [offset +  (variation * random()) for i in range(count)]
        systimes = [cursystime + offset for offset in offsets]
        sched = mpx.lib.scheduler.Scheduler()
        sched.setdebug(debug)
        sched.start()
        entries = [sched.after(offset, self.callback2) for offset in offsets]
        scheduled = sched._entries.getentries()
        for entry in entries:
            assert entry in scheduled, 'Entry %s not present in queue' % entry
        for entry in entries:
            sched.remove_entry(entry)
        scheduled = sched._entries.getentries()
        for entry in entries:
            assert entry not in scheduled, 'Entry %s present in queue' % entry
        for entry in entries:
            try:
                sched.remove_entry(entry)
            except IndexError:
                pass
            else:
                raise AssertionError('2nd remove should raise IndexError')
        for entry in entries:
            # Although not in scheduler, no exc should be raised.
            try:
                entry.cancel()
            except IndexError:
                raise AssertionError('entry.cancel() raised IndexError')
        entries = [sched.at(systime, self.callback2) for systime in systimes]
        scheduled = sched._entries.getentries()
        for entry in entries:
            assert entry in scheduled, 'Entry %s not present in queue' % entry
        for entry in entries:
            sched.remove_entry(entry)
        scheduled = sched._entries.getentries()
        for entry in entries:
            assert entry not in scheduled, 'Entry %s present in queue' % entry
        for entry in entries:
            try:
                sched.remove_entry(entry)
            except IndexError:
                pass
            else:
                raise AssertionError('2nd remove should raise IndexError')
        for entry in entries:
            # Although not in scheduler, no exc should be raised.
            try:
                entry.cancel()
            except IndexError:
                raise AssertionError('entry.cancel() raised IndexError')
        assert len(sched._entries) == 1, 'More than one entry left'
        sched.stop()
    def test_run_many(self):
        cursystime = _time.time()
        curuptime = uptime.secs()
        # Create 1000 entries
        count = 1000
        # Earliest entry executes in 20 seconds.
        offset = 5
        # Schedule for random value between offset and offset + range
        variation = 5
        # Generate offset list
        offsets = [offset +  (variation * random()) for i in range(count)]
        sched = mpx.lib.scheduler.Scheduler()
        sched.setdebug(debug)
        sched.start()
        entries = [sched.after(offset, self.callback2) for offset in offsets]
        pause(offset + variation)
        callbacks = self.callback_count
        assert callbacks == count, 'Counted %d, not %d' % (callbacks, count)
        assert len(sched._entries) == 1, 'More than one entry left'
        sched.stop()
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

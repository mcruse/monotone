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
import os
import time
import select
from threading import Lock
from threading import Event
from threading import Thread
from mpx.lib import msglog
from moab.linux.lib import uptime
from mpx.lib.thread import log_startup
from exceptions import EActionExpired
from exceptions import EActionPremature
from entries import AbsoluteEntry
from entries import RelativeEntry
from entries import RecurringEntry
from datatypes import Collection
from notifier import Condition

ZERODEBUG = 0
STANDARDDEBUG = 1
VERBOSEDEBUG = 2
VERBOSEWSTDOUT = 5

###
# time_check_period: Defines how often (in seconds) we wake up and check to see
#                    if time.time() has drifted relative to uptime.secs().
# allow_time_error:  Defines how large an error (in seconds) we allow in
#                    time.time() (vs uptime.secs()) before it is considered
#                    a problem and appropriate schedule entries are
#                    rescheduled.
##
time_check_period = 15.0
allow_time_error =   1.0
timeprecision = 3
debug = 0

class Scheduler(Thread):
    def __init__(self, resolution=0.01):
        super(Scheduler, self).__init__(name='Scheduler(%d)' % id(self))
        self.resolution = resolution
        self._condition = Condition()
        self._entries = Collection()
        self._last_uptime = None
        self._last_systime = None
        self._setupflags()
        self._setupwatches()
        self._checktimecallback = None
        self.debugout('instantiated', STANDARDDEBUG)
    def set_checktime_callback(self, callback):
        self._checktimecallback = callback
    def _setupflags(self):
        # Flag indicates start() invoked.
        self._started = Event()
        # Flag indicate stop() invoked.
        self._stopped = Event()
        # Flag indicates scheduler is enabled.
        self._enabled = Event()
        # Flag indicates scheduler actively executing.
        self._running = Event()
        self._debug = debug
        self.enable()
    def _setupwatches(self):
        self._last_uptime = uptime.secs()
        self._last_systime = time.time()
    def enable(self):
        self.debugout('enabling', STANDARDDEBUG)
        self._enabled.set()
    def disable(self):
        self.debugout('disabled', STANDARDDEBUG)
        self._enabled.clear()
    def await_enable(self, timeout = None):
        return self._enabled.wait(timeout)
    def start(self, *args, **kw):
        if self.is_started():
            raise TypeError('%s already started.' % self.getName())
        self._started.set()
        self.setDaemon(True)
        self.debugout('starting', STANDARDDEBUG)
        super(Scheduler, self).start(*args, **kw)
        timecheckentry = self.every(
            time_check_period, self._check_time_progression)
        self.timecheckentry = timecheckentry
        self.debugout('created time checker %s', STANDARDDEBUG, timecheckentry)
    def stop(self, timeout = None):
        self._stopped.set()
        self._enabled.set()
        self._condition.acquire()
        try:
            self._condition.notify()
        finally:
            self._condition.release()
        return super(Scheduler, self).join(timeout)
    def is_enabled(self):
        return self._enabled.isSet()
    def is_disabled(self):
        return not self.is_enabled()
    def is_started(self):
        return self._started.isSet()
    def is_stopped(self):
        return self._stopped.isSet()
    def is_running(self):
        return self._running.isSet()
    def should_run(self):
        return self.is_started() and not self.is_stopped()
    def at(self, when, target, args=()):
        entry = AbsoluteEntry(self, when, target, args)
        self.add_entry(entry)
        return entry
    def after(self, delay, target, args=()):
        entry = RelativeEntry(self, delay, target, args)
        self.add_entry(entry)
        return entry
    def every(self, period, target, args=()):
        entry = RecurringEntry(self, period, target, args)
        self.add_entry(entry)
        return entry
    def at_time_do(self, when, target, *args):
        return self.at(when, target, args)
    def seconds_from_now_do(self, delay, target, *args):
        return self.after(delay, target, args)
    def every_seconds_do(self, period, target, *args):
        return self.every(period, target, args)
    def cancel_entry(self, entry):
        self.debugout('canceling entry %s', STANDARDDEBUG, entry)
        entry.cancel()
    cancel = cancel_entry
    def remove_entry(self, entry):
        self.debugout('removing entry %s', STANDARDDEBUG, entry)
        self._condition.acquire()
        try: 
            index = self._entries.removeentry(entry)
        finally: 
            self._condition.release()
        self.debugout('removed entry %s at %d', STANDARDDEBUG, entry, index)
        return index
    def add_entry(self, entry):
        self.debugout('adding entry %s', VERBOSEDEBUG, entry)
        self._condition.acquire()
        try:
            index = self._entries.addentry(entry)
            if index == 0:
                self._condition.notify()
        finally: 
            self._condition.release()
        return index
    def enabled(self, value = None):
        if value is not None:
            if value:
                self.enable()
            else:
                self.disable()
        return self.is_enabled()
    def testdebug(self, level = 1):
        return self.getdebug() >= level
    def getdebug(self):
        return self._debug
    def setdebug(self, level):
        self._debug = int(level)
    def debugout(self, message, dblevel = 1, *args):
        """
            String inside message may have format specifiers 
            to be applied to variable lenth arguments '*args'.
            Objects passed in as arguments are only converted 
            iff the debug level is equal to or greater than 
            passed in debug level 'debuglevel.'  This enhances 
            performance while allowing methods to output debug 
            messages without explicitly testing debug level.
        """
        if self.testdebug(dblevel):
            if len(args):
                message = message % args
            self.logmessage(message, msglog.types.DB)
            if self.testdebug(VERBOSEWSTDOUT):
                # Also output to stdout if debug at or above 5.
                print '%s: %s' % (self, message)
        return
    def logmessage(self, message, mtype=msglog.types.INFO, autoprefix=True):
        """
            Convenience method to log to message log.  Default behaviour 
            prepends 'str(self): ' to entry so that callers may skip 
            doing so themselves.  Set 'autoprefix' to False to prevent 
            prepend behaviour from occuring.
        """
        if autoprefix:
            message = '%s: %s' % (self, message)
        msglog.log('broadway', mtype, message)
    def run(self):
        log_startup(self, self.getName(), 'SchedulerThread')
        self.debugout('entering run() loop', STANDARDDEBUG)
        while self.should_run():
            self._running.set()
            try:
                self._schedulerloop()
            except:
                msglog.exception(prefix = 'handled')
                msglog.log('broadway', msglog.types.WARN, 
                           '%s re-entering run loop.' % self.getName())
            self._running.clear()
        else:
            self.debugout('exiting run() loop', STANDARDDEBUG)
        self.debugout('exiting run()', STANDARDDEBUG)
    def _schedulerloop(self):
        self._condition.acquire()
        try:
            while not self.is_stopped():
                if self.is_enabled():
                    self.debugout('run() tick', VERBOSEDEBUG)
                    tock = self._tick()
                    if tock != 0:
                        self.debugout('run() waiting(%0.3f)',VERBOSEDEBUG,tock)
                        self._condition.wait(tock)
                    else:
                        self.debugout('run() skipping wait(0)', VERBOSEDEBUG)
                    self.debugout('run() tock', VERBOSEDEBUG)
                else:
                    self.debugout('run() awaiting enable', STANDARDDEBUG)
                    self.await_enable()
                    self.debugout('run() re-entering loop', STANDARDDEBUG)
            else:
                self.debugout('run() stopping', STANDARDDEBUG)
        finally:
            self._condition.release()
    def _tick(self):
        reschedule = []
        entries = self._entries.popentries(uptime.secs())
        self._condition.release()
        try:
            for entry in entries:
                try:
                    entry.execute()
                except EActionExpired:
                    pass
                except EActionPremature:
                    message = 'entry %s execution premature, will reschedule'
                    self.debugout(message, STANDARDDEBUG, entry)
                    reschedule.append(entry)
                except:
                    msglog.exception()
                else: 
                    if isinstance(entry, RecurringEntry):
                        reschedule.append(entry)
        finally:
            self._condition.acquire()
        for entry in reschedule:
            entry.computewhen()
        self._entries.addentries(reschedule)
        nextrun = self._entries.nextruntime()
        if nextrun is not None:
            nextrun = max(0, nextrun - uptime.secs())
        return nextrun
    def __str__(self):
        return self.getName()
    def __repr__(self):
        status = [self.getName()]
        if self.is_enabled():
            status.append('enabled')
        if self.is_stopped():
            status.append('stopped')
        elif self.is_started():
            status.append('started')
            if self.is_running():
                status.append('running')
        status.append('(%d entries)' % len(self._entries))
        return '<%s>' % ' '.join(status)
    def _check_time_progression(self):
        self.debugout('checking time progression', VERBOSEDEBUG)
        curuptime = uptime.secs()
        cursystime = time.time()
        diff_uptime = curuptime - self._last_uptime
        diff_systime = cursystime - self._last_systime
        diff_diff = diff_systime - diff_uptime
        # If the difference between the way that time.time() is
        # progressing and the way that uptime.secs() is progressing
        # has grown larger than our allowable error (allow_time_error),
        # then have entry list rebuild itself so to correctly reflect 
        # newly calculated uptime values and order of entries.
        if abs(diff_diff) > allow_time_error:
            self.debugout('time.time() drift %0.3fs', STANDARDDEBUG, diff_diff)
            self._condition.acquire()
            try:
                # Get all entries
                entries = self._entries.getentries()
                for entry in entries:
                    # Have each recompute due time
                    entry.computewhen()
                self.debugout('entry due-times recomputed', STANDARDDEBUG)
                # Create new entries collection from possibly unsorted entries
                self._entries.rebuild()
                self.debugout('entry collection rebuilt', STANDARDDEBUG)
            finally:
                # Executed within 'tick()', no need to notify.
                self._condition.release()
            # Reset baseline watch values to diff at time of check
            self._last_uptime = curuptime
            self._last_systime = cursystime
        else:
            self.debugout('drift %0.3fs ignored', VERBOSEDEBUG, diff_diff)
        # Callback hook for unit test monitoring resync
        if self._checktimecallback:
            self._checktimecallback()
    ##
    # Methods following this point are deprecated and have been 
    # left here for backwards compatibility reasons.  
    def debug_output(self, message=None, location=None):
        """
            Use preferred 'debugout' method instead.
        """
        if self._debug:
            if message:
                print '%f: SCHEDULER: %s' % (uptime.secs(), message)
    def debug(self, level = None):
        """
            Use preferred methods 'getdebug' and 'setdebug' instead.
        """
        if level is not None:
            self.setdebug(level)
        return self.getdebug()

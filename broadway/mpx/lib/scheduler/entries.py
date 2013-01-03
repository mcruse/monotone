"""
Copyright (C) 2008 2009 2010 2011 Cisco Systems

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
    Defines multiple variations of scheduler entry objects.
    All entry types extend abstract base class AbstractEntry; 
    which defines the entry interface and implements the vast 
    majority of entry methods.
"""

import time
import inspect
from threading import Lock
from threading import currentThread as current_thread
from mpx.lib import msglog
from moab.linux.lib import uptime
from exceptions import EActionExpired
from exceptions import EActionPremature
from datatypes import Flag
###
# Note: uptime.secs() is used in several places in the following code,
#       notably several places where time.time() used to be used.
#       uptime.secs() is basically seconds-since-last-boot and has
#       the nice property of always moving forward at around 1.0
#       per second versus time.time() which is subject to change
#       if the user updates the time, if a ntp server updates the
#       time, etc.
##

###
# Flags setup below are 'explicit' flags.  
# Corresponding method exposed to test each 
# flags state.  Public methods all implement 
# locking to maintain flag state consistency.
# Additional test methods generate result based 
# on state of two or more flags.  Each such method 
# does not have a corresonding 'explicit' flag.  To 
# keep state knowledge packaged cohesively, any all 
# test methods for non-explicit states have corresponding 
# private method of same name beginning with '_'.  Public 
# methods implement locking.
# NOTE: Flag instances are callable and so methods using 
# private method tests need not differentiate between methods 
# of entry object versus references directly to Flag instances.
##

class AbstractEntry(object):
    def currentsystime():
        return time.time()
    currentsystime = staticmethod(currentsystime)
    def currentuptime():
        return uptime.secs()
    currentuptime = staticmethod(currentuptime)
    def __init__(self, schedule, target, args):
        super(AbstractEntry, self).__init__()
        self._schedule = schedule
        self._target = target
        self._args = args
        self._setupflags()
        self._statelock = Lock()
        self.computewhen()
    def runswhen(self):
        """
            Return up-time value at which entry is 
            scheduled to run.  This value is calculated 
            and updated when 'computewhen()' is invoked; 
            value returned is always the value configured 
            by most recent computewhen() call.
        """
        return self._targetuptime
    def computewhen(self):
        """
            Calculate, or recalculate, target run time 
            value in terms of system up time.
            
            NOTE - this method uses dynamic 'runuptime()' 
            method to get up to date run time target value.
        """
        self._targetuptime = self.runuptime()
    def runuptime(self):
        """
            Dynamically generated target up-time value.  
            This value is used interally by 'computewhen()' 
            in order to configure the entry's run time 
            target.
            
            NOTE - this method uses dynamic 'rundelay()' 
            method to get offset from current up-time and 
            calculate target up-time.
        """
        return self.currentuptime() + self.rundelay()
    def rundelay(self, currenttime = None):
        """
            Return delay, in seconds, between now and when entry runs.
        """
        raise NotImplementedError('abstract rundelay() must be overridden')
    def _setupflags(self):
        self._cancelled = Flag(False)
        self._executed = Flag(False)
        self._executing = Flag(False)
        self._failed = Flag(False)
        self._scheduled = Flag(True)
    def scheduled(self):
        self._statelock.acquire()
        try: 
            return self._scheduled.isSet()
        finally: 
            self._statelock.release()
    def cancelled(self):
        self._statelock.acquire()
        try: 
            return self._cancelled.isSet()
        finally: 
            self._statelock.release()
    def executing(self):
        self._statelock.acquire()
        try: 
            return self._executing.isSet()
        finally: 
            self._statelock.release()
    def executing_caller(self):
        """
            Returns True if caller is currently running 
            as entry's execution 
        """
        self._statelock.acquire()
        try: 
            executing = self._executing.isSet()
            return executing and self._schedule is current_thread()
        finally: 
            self._statelock.release()
    def isdue(self):
        return self.rundelay() <= 0
    def executable(self):
        """
            Return True if entry may still be executed.  An 
            entry may be executed if it is not currently 
            executing and has not yet been executed.
        """
        self._statelock.acquire()
        try:
            return self._executable()
        finally:
            self._statelock.release()
    def overdue(self):
        """
            A entry is overdue iff it may still be executed 
            and the current uptime is greater than the target 
            uptime at which the entry was scheduled to execute.
        """
        # Order chosen to avoid race-condition.
        self._statelock.acquire()
        try:
            return self._overdue()
        finally:
            self._statelock.release()
    def executed(self):
        self._statelock.acquire()
        try: 
            return self._executed.isSet()
        finally: 
            self._statelock.release()
    def expired(self):
        self._statelock.acquire()
        try:
            return self._expired()
        finally: 
            self._statelock.release()
    ##
    # No semi-private test-method can implement locking.
    # This allows indescriminate use of methods versus 
    # direct invocation of flag instances without 
    # making it easy to accidentally block on double-lock.
    def _expired(self):
        return self._executed() or self._cancelled()
    def _executable(self):
        return not (self._executing() or self._expired())
    def _overdue(self):
        return (self.currentuptime() > self.runuptime()) and self._executable()
    def runsystime(self):
        """
            Return time at which entry is supposed to run.
        """
        return self.rundelay() + self.currentsystime()
    def execute(self):
        self._statelock.acquire()
        try:
            if not self._executable():
                raise EActionExpired('Scheduled action %s has expired' % self)
            else:
                self._executing.set()
        finally:
            self._statelock.release()
        try:
            try: 
                value = self._target(*self._args)
            except:
                self._failed.set()
                message = 'Entry Exception running: "%s%s"'
                msglog.log('broadway', msglog.types.DB, 
                           message % (self._target, self._args))
                raise
            else:
                self._failed.clear()
        finally:
            self._statelock.acquire()
            # Ordering chosen to prefer overlap than gap.
            self._executed.set()
            self._executing.clear()
            self._scheduled.clear()
            self._statelock.release()
        return value
    def cancel(self):
        self._statelock.acquire()
        try:
            self._cancelled.set()
            if self._scheduled():
                try:
                    self._schedule.remove_entry(self)
                except IndexError:
                    message = 'IndexError removing %s (at %#x)'
                    self._schedule.debugout(message, 1, self, id(self))
            self._scheduled.clear()
        finally:
            self._statelock.release()
        self._schedule.debugout('%s cancelled', 1, self)
    def __bigstr__(self):
        status = ['%s' % type(self).__name__]
        status.append(self._get_actionstr())
        if self._executable():
            execution = 'pending'
        if self._executed():
            status.append('executed')
            if self._failed():
                status.append('failed')
            else:
                status.append('succeeded')
        elif self._executing():
            status.append('executing')
        elif self._cancelled():
            status.append('cancelled')
        elif self._overdue():
            status.append('overdue')
        runtime = self.runuptime()
        status.append('due %0.2f' % runtime)
        rundelay = runtime - self.currentuptime()
        if rundelay < 0:
            sign = '-'
        else:
            sign = '+'
        status.append('(now %s %0.2f sec)' % (sign, abs(rundelay)))
        return ' '.join(status)
    def __littlestr__(self):
        state = 'Pending'
        if self._executed:
            state = 'Executed'
            if self._failed:
                state += ', Failed'
            else:
                state += ', Succeeded'
        elif self._cancelled:
            state = 'Cancelled'
        elif self._overdue():
            state = 'Overdue'
        return ('Scheduled Action: %s%s due %s -> %s' %
                (self._target,self._args,self.runswhen(),state))
    __str__ = __bigstr__
    def _get_actionstr(self):
        action = self._target
        description = [str(action)]
        try:
            if inspect.ismethod(action):
                if action.im_self is not None:
                    description.insert(0, type(action.im_self).__name__)
                description[-1] = action.im_func.__name__
            elif inspect.isfunction(action):
                description[-1] = action.__name__
            elif inspect.isclass(action):
                description.insert(0, action.__name__)
                description.pop()
        except:
            pass
        return '%s%s' % ('.'.join(description), self._args)

class AbsoluteEntry(AbstractEntry):
    def __init__(self, schedule, abs_when, target, args):
        self._absolute_runtime = abs_when
        super(AbsoluteEntry, self).__init__(schedule, target, args)
    def rundelay(self):
        return self._absolute_runtime - self.currentsystime()
    def execute(self):
        if not self.isdue():
            raise EActionPremature()
        return super(AbsoluteEntry, self).execute()

class RelativeEntry(AbstractEntry):
    def __init__(self, schedule, delay, target, args):
        self._configureddelay = delay
        self._scheduledstart = self.currentuptime()
        super(RelativeEntry, self).__init__(schedule, target, args)
    def runuptime(self):
        return self._scheduledstart + self._configureddelay
    def rundelay(self):
        return self.runuptime() - self.currentuptime()
    def reset(self):
        self._statelock.acquire()
        try:
            if self._executing():
                return None
            elif self._executed():
                return None
            elif self._cancelled():
                return None
            elif not self._scheduled():
                return None
            else:
                # Remove self from scheduled entries
                self._schedule.remove_entry(self)
                # Reset start-time, time from which delay is offset
                self._scheduledstart = self.currentuptime()
                # Reset runswhen value based on new start time
                self.computewhen()
                # Re-add to schedule to be inserted with new runswhen()
                self._schedule.add_entry(self)
        finally:
            self._statelock.release()
        return self

class RecurringEntry(RelativeEntry):
    def __init__(self, schedule, period, target, args):
        self.period = period
        RelativeEntry.__init__(self, schedule, 0, target, args)
    def execute(self):
        result = super(RecurringEntry, self).execute()
        self._statelock.acquire()
        try:
            self._setupflags()
            # Set delay to period since first run had delay 0 sec
            self._configureddelay = self.period
            # Reset start-time so next when calc computes next run
            self._scheduledstart = self.currentuptime()
        finally:
            self._statelock.release()
        return result

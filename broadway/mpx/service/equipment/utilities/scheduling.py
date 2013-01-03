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
import time
from threading import Lock
from mpx.lib import msglog
from mpx.lib import EnumeratedValue
from mpx.service.network.utilities.counting import Counter
DEBUG = False
THREADED = False

class SubscriptionExecutioner(object):
    PENDING = EnumeratedValue(0, 'Pending')
    PREPARING = EnumeratedValue(1, 'Preparing for export')
    GETTING = EnumeratedValue(2, 'Getting data')
    FORMATTING = EnumeratedValue(3, 'Formatting data')
    SENDING = EnumeratedValue(4, 'Starting transaction')
    SCHEDULING = EnumeratedValue(5, 'Scheduling next export')
    COMPLETED = EnumeratedValue(6, 'Completed')
    STAGES = [PENDING, PREPARING, GETTING, 
              FORMATTING, SENDING, SCHEDULING, COMPLETED]
    def __init__(self, group, subscription):
        self.group = group
        self.subscription = subscription
        self.stagecallbacks = [(self.execute_prepare,), 
                               (self.execute_get_data,), 
                               (self.execute_format_data,), 
                               (self.execute_start_transaction,), 
                               (self.execute_schedule_export,)]
        self.stagearguments = ()
    def get_stage(self):
        return self.STAGES[-len(self.stagecallbacks) - 1]
    def execute(self):
        stage = self.get_stage()
        stagemethods = self.stagecallbacks.pop(0)
        try:
            for stagemethod in stagemethods:
                stagearguments = self.stagearguments
                result = stagemethod(*stagearguments)
                self.stagearguments = (result,)
        except Exception, error:
            self.subscription.handle_export_exception(error, stage)
            if not self.is_complete():
                self.group.notify_stage_aborted(self, stage)
            else:
                self.group.notify_executioner_aborted(self)
            self.stagecallbacks, self.stagearguments = [], ()
        else: 
            if not self.is_complete():
                self.group.notify_stage_executed(self, stage)
            else:
                self.group.notify_executioner_executed(self)
    def execute_prepare(self):
        return self.subscription.prepare_to_export()
    def execute_get_data(self, *args):
        return self.subscription.get_export_data()
    def execute_format_data(self, changes):
        return self.subscription.format_export_data(changes)
    def execute_start_transaction(self, data):
        return self.subscription.start_export_transaction(data)
    def execute_schedule_export(self, *args):
        return self.subscription.schedule_next_export()
    def cancel(self):
        return self.group.notify_executioner_cancelled(self)
    def is_complete(self):
        return len(self.stagecallbacks) == 0
    def __str__(self):
        description = 'Executioner for %s at %s: %s'
        return description % (
            self.subscription, 
            time.ctime(self.group.timestamp), 
            self.get_stage())

class SubscriptionGroup(object):
    def __init__(self, monitor, timestamp):
        self.monitor = monitor
        self.timestamp = timestamp
        self.stagelock = Lock()
        self.stage_aborted = []
        self.stage_executed = []
        self.executioners = []
        self.pending_executioners = []
        self.aborted_executioners = []
        self.executed_executioners = []
        self.cancelled_executioners = []
        self.stage_counter = Counter()
        self.active_executioners = Counter()
        self.monitor.debugout('Created %s' % self, 1)
    def add_subscription(self, subscription):
        executioner = SubscriptionExecutioner(self, subscription)
        self.executioners.append(executioner)
        self.stagelock.acquire()
        self.pending_executioners.append(executioner)
        self.stagelock.release()
        return executioner
    def notify_stage_executed(self, executioner, stage):
        self.stagelock.acquire()
        self.stage_executed.append(executioner)
        active = self.active_executioners.pre_decrement()
        self.stagelock.release()
        if not active:
            self.stage_execution_complete()
    def notify_stage_aborted(self, executioner, stage):
        self.stagelock.acquire()
        self.stage_aborted.append(executioner)
        active = self.active_executioners.pre_decrement()
        self.stagelock.release()
        if not active:
            self.stage_execution_complete()
    def notify_executioner_aborted(self, executioner):
        self.stagelock.acquire()
        self.aborted_executioners.append(executioner)
        active = self.active_executioners.pre_decrement()
        self.stagelock.release()
        if not active:
            self.stage_execution_complete()
    def notify_executioner_cancelled(self, executioner):
        self.stagelock.acquire()
        try:
            foundexecutioner = self.pending_executioners.count(executioner)
            if foundexecutioner:
                self.pending_executioners.remove(executioner)
                self.cancelled_executioners.append(executioner)
        finally:
            self.stagelock.release()
        return foundexecutioner
    def notify_executioner_executed(self, executioner):
        self.stagelock.acquire()
        if executioner is not self:
            self.executed_executioners.append(executioner)
        active = self.active_executioners.pre_decrement()
        self.stagelock.release()
        if not active:
            self.stage_execution_complete()
    def stage_execution_complete(self):
        self.stagelock.acquire()
        try:
            while self.stage_aborted:
                self.aborted_executioners.append(self.stage_aborted.pop(0))
            while self.stage_executed:
                self.pending_executioners.append(self.stage_executed.pop(0))
            pending = len(self.pending_executioners)
        finally:
            self.stagelock.release()
        if DEBUG:
            stagenumber = self.stage_counter.value
            message = '[%s] executed stage %d'
            self.monitor.debugout(message % (self, stagenumber))
        self.stage_counter.increment()
        if pending:
            self.execute_next_stage()
        else:
            message = 'Completed %s'
            self.monitor.debugout(message % (repr(self)[1:-1]))
            self.monitor.notify_group_executed(self)
    def execute_next_stage(self):
        self.stagelock.acquire()
        try:
            # Increment once for this execution.
            self.active_executioners.increment()
            executioners = self.pending_executioners
            # Preemptively inrement for all executioners to avoid race.
            self.pending_executioners = []
            self.active_executioners.increment(len(executioners))
        finally:
            self.stagelock.release()
        for executioner in executioners:
            try:
                if THREADED:
                    self.monitor.enqueue_work(executioner.execute)
                else:
                    executioner.execute()
            except:
                msglog.exception()
                self.notify_executioner_aborted(executioner)
        self.notify_executioner_executed(self)
    def execute(self):
        if DEBUG:
            self.monitor.debugout('[%s] executing' % repr(self)[1:-1])
        self.monitor.enqueue_work(self.execute_next_stage)
    def __str__(self):
        return 'Execution Group %s' % time.ctime(self.timestamp)
    def __repr__(self):
        status = ['%dP' % len(self.pending_executioners)]
        status.append('%dA' % len(self.aborted_executioners))
        status.append('%dC' % len(self.cancelled_executioners))
        status.append('%dE' % len(self.executed_executioners))
        status = ['(%s)' % stat for stat in status]
        status.insert(0, '%d executioners' % len(self.executioners))
        return '<%s %s>' % (self, ' '.join(status))







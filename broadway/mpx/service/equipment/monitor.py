"""
Copyright (C) 2007 2008 2010 2011 Cisco Systems

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
from Queue import Queue
from Queue import Empty
from threading import Lock
from threading import RLock
from threading import Event as Flag
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.componentry import implements
from mpx.lib.scheduler import scheduler
from mpx.lib.neode.node import rootspace
from mpx.lib.neode.node import CompositeNode
from mpx.lib.persistence.datatypes import PersistentDictionary
from mpx.lib.persistent import PersistentDataObject
from mpx.service.network.utilities.counting import Counter
from mpx.service.network.utilities.timing import Timer
from data.transporters.exceptions import ETransactionException
from data.transporters.exceptions import ETransactionInProgress
from data.transporters.exceptions import ETransactionTimeout
from data.transporters.interfaces import ITransporter
from data.formatters.interfaces import IFormatter
from utilities.scheduling import SubscriptionGroup
from utilities.processing import WorkThread
from utilities import Dictionary
from interfaces import *

DEBUG = 0
TESTING = True

def frompdo(pdodata):
    pdodata.subscriptions = []
    pdodata.load()
    configurations = pdodata.subscriptions[:]
    decode = PushedSubscription.from_dictionary
    subscriptions = map(decode, configurations)
    return dict([(sub.id(), sub) for sub in subscriptions])

class EquipmentMonitor(CompositeNode):
    implements(IEquipmentMonitor)
    def __init__(self, *args):
        self.test_machines = []
        self.synclock = RLock()
        self.threadcount = 1
        self.formatter = None
        self.transporter = None
        self.smservice = None
        self.subscriptions = None
        self.running = Flag()
        self.work_threads = []
        self.work_queue = Queue()
        self.scheduling_lock = Lock()
        self.execution_groups = Dictionary()
        self.smnodeurl = '/services/Subscription Manager'
        super(EquipmentMonitor, self).__init__(*args)
    def configure(self, config):
        self.smnodeurl = config.get('subscription_manager', self.smnodeurl)
        self.threadcount = int(config.get('threadcount', self.threadcount))
        super(EquipmentMonitor, self).configure(config)
    def configuration(self):
        config = super(EquipmentMonitor, self).configuration()
        config['subscription_manager'] = self.smnodeurl
        config['threadcount'] = str(self.threadcount)
        return config
    def start(self):
        if self.is_running():
            raise TypeError("Equipment Monitor already running.")
        if TESTING and not self.test_machines:
            self.test_machines = setup_machines()
            machinecount = len(self.test_machines)
            self.debugout("Setup %d test machines" % machinecount)
        self.synclock.acquire()
        try:
            self.running.set()
            if self.subscriptions and not self.subscriptions.closed():
                self.subscriptions.close()
            self.formatter = None
            self.transporter = None
            children = self.children_nodes()
            for childnode in children:
                if IFormatter.providedBy(childnode):
                    if self.formatter is not None:
                        raise TypeError("Already has formatter child.")
                    self.formatter = childnode
                if ITransporter.providedBy(childnode):
                    if self.transporter is not None:
                        raise TypeError("Already has transporter child.")
                    self.transporter = childnode
            if not self.formatter:
                raise TypeError("Must have one formatter child node.")
            if not self.transporter:
                raise TypeError("Must have one transporter child node.")
            self.smservice = as_node(self.smnodeurl)
            self.subscriptions = PersistentDictionary(
                self.name, encode=self.serialize_subscription, 
                decode=self.unserialize_subscription)
            pdodata = PersistentDataObject(self)
            if os.path.exists(pdodata.filename()):
                msglog.log('broadway', msglog.types.WARN, 
                           "Equipment Monitor upgrading persistence.")
                migrate = frompdo(pdodata)
                self.subscriptions.update(migrate)
                message = "Equipment Monitor merged %d subscriptions."
                message = message % len(migrate)
                msglog.log('broadway', msglog.types.INFO, message)
                pdodata.destroy()
                msglog.log('broadway', msglog.types.WARN, 
                           "Equipment Monitor destroyed old persistence.")
                msglog.log('broadway', msglog.types.INFO, 
                           "Equipment Monitor persistence upgrade complete.")
            del(pdodata)
            message = 'Equipment Monitor startup: %s %s'
            for subscription in self.subscriptions.values():
                try:
                    subscription.setup_subscription()
                except:
                    msglog.exception(prefix="handled")
                else:
                    self.debugout(message % ('setup', subscription))
            skipcounts = []
            for i in range(0, 1 + len(self.subscriptions) / 30):
                skipcounts.extend([i + 1] * 30)
            self.setup_work_threads()
            for subscription in self.subscriptions.values():
                try: 
                    subscription.start(skipcounts.pop())
                except: 
                    msglog.exception(prefix = "Handled")        
                else:
                    self.debugout(message % ('started', subscription))
        except:
            self.cleanup_resources()
            self.running.clear()
            raise
        finally:
            self.synclock.release()
        super(EquipmentMonitor, self).start()
    def stop(self):
        if not self.is_running():
            raise TypeError('Equipment Monitor not running.')
        self.synclock.acquire()
        try:
            self.running.clear()
            message = "Equipment Monitor shutdown: %s %s"
            for subscription in self.subscriptions.values():
                try: 
                    subscription.stop()
                except: 
                    msglog.exception(prefix='Handled')
                else:
                    self.debugout(message % ('stopped', subscription))
            self.teardown_work_threads()
        except:
            message = "Exception caused Eqiupment Monitor shutdown to fail."
            msglog.log('broadway', msglog.types.ERR, message)
            self.running.set()
            raise
        else:
            self.cleanup_resources()
        finally:
            self.synclock.release()
        super(EquipmentMonitor, self).stop()
    def get_subscription(self, sid, default = None):
        return self.subscriptions.get(sid, default)
    def get_subscription_manager(self):
        return self.smservice
    def get_formatter(self):
        return self.formatter
    def get_transporter(self):
        return self.transporter
    def schedule_subscription(self, subscription, timestamp):
        self.scheduling_lock.acquire()
        try:
            schedulegroup = self.execution_groups.get(timestamp)
            if schedulegroup is None:
                schedulegroup = SubscriptionGroup(self, timestamp)
                self.execution_groups[timestamp] = schedulegroup
                schedulegroup.scheduled = scheduler.at(
                    timestamp, schedulegroup.execute)
            schedentry = schedulegroup.add_subscription(subscription)
        finally:
            self.scheduling_lock.release()
        return schedentry
    def enqueue_work(self, callback, *args):
        self.work_queue.put((callback, args))
    def dequeue_work(self, blocking = True):
        return self.work_queue.get(blocking)
    def is_running(self):
        return self.running.isSet()
    def assert_running(self):
        if not self.is_running():
            raise TypeError('Service must be running.')
        return
    def create_pushed(self, target, node_table, period=2, retries=10):
        self.assert_running()
        pushed = PushedSubscription(self, target, node_table, period, retries)
        sid = pushed.setup_subscription()
        self.subscriptions[sid] = pushed
        message = ['Equipment Monitor created subscription: ']
        message.append('Target URL: %s' % target)
        message.append('Period: %d sec' % period)
        message.append('Subscription ID: %s' % sid)
        if isinstance(node_table, str):
            message.append('Subscription for children of: %s' % node_table)
        else:
            firstthree = node_table.items()[0:3]
            message.append('Number of nodes: %d' % len(node_table))
            message.append('First three nodes: %s' % (firstthree,))
        self.debugout('\n    '.join(message), 2)
        pushed.start(1)
        return sid
    def cancel(self, sid):
        self.assert_running()
        if self.pause(sid):
            subscription = self.subscriptions.pop(sid)
            message = 'Equipment Monitor cancelled subscription: "%s"'
            self.debugout(message % sid, 2)
            return True
        return False
    def pause(self, sid, delay = None):
        subscription = self.subscriptions.get(sid)
        if subscription and subscription.is_running():
            subscription.stop()
            return True
        else:
            return False
    def play(self, sid):
        self.assert_running()
        subscription = self.subscriptions[sid]
        if not subscription.is_running():
            subscription.start()
            return True
        else:
            return False
    def reset(self, sid):
        subscription = self.subscriptions.get(sid)
        if subscription:
            subscription.reset_subscription()
            return True
        else:
            return False
    def list_subscriptions(self):
        return self.subscriptions.keys()
    def notify_group_executed(self, group):
        self.scheduling_lock.acquire()
        try:
            self.execution_groups.pop(group.timestamp)
        finally:
            self.scheduling_lock.release()
    def cleanup_resources(self):
        self.synclock.acquire()
        try:
            for group in self.execution_groups:
                try: 
                    group.scheduled.cancel()
                except:
                    msglog.exception(prefix="handled")
            self.execution_groups.clear()
            try:
                while self.work_queue.get_nowait():
                    pass
            except Empty:
                pass
            if self.transporter:
                commonitor = self.transporter.monitor
                transmanager = self.transporter.transaction_manager
                try:
                    commonitor.shutdown_channels()
                except:
                    msglog.exception(prefix="handled")
                transmanager.controllers.clear()
            if self.subscriptions and not self.subscriptions.closed():            
                self.subscriptions.close()
            self.subscriptions = None
            self.transporter = None
            self.formatter = None
        finally:
            self.synclock.release()
    def setup_work_threads(self):
        assert self.is_running()
        assert len(self.work_threads) == 0
        while len(self.work_threads) < self.threadcount:
            monitor = WorkThread(self.is_running, self.dequeue_work)
            monitor.setDaemon(True)
            monitor.start()
            self.work_threads.append(monitor)
        return len(self.work_threads)
    def teardown_work_threads(self):
        assert not self.is_running()
        threadcount = len(self.work_threads)
        map(self.work_queue.put, [None] * threadcount)
        while self.work_threads:
            self.work_threads.pop().join()
        return threadcount
    def serialize_subscription(self, subscription):
        return repr(subscription.as_dictionary())
    def unserialize_subscription(self, data):
        return PushedSubscription.from_dictionary(eval(data))
    def debugout(self, dbmessage, dblevel = 1):
        if dblevel <= DEBUG: 
            msglog.log('broadway', msglog.types.DB, dbmessage)

class PushedSubscription(object):
    subscription_counter = Counter()
    def __init__(self, monitor, target, nodetable, period, retries, sid=None):
        self.subscription_number = self.subscription_counter.increment()
        self._setup_collaborators(monitor)
        self.node_table = nodetable
        self.target = target
        self.period = period
        self.retries = retries
        self.sid = sid
        self.running = Flag()
        self._setup = Flag()
        self._setup_counters()
        self._setup_timers()
        self._setup_trackers()
        super(PushedSubscription, self).__init__()
    def id(self):
        return self.sid
    def is_running(self):
        return self.running.isSet()
    def is_setup(self):
        return self._setup.isSet()
    def get_target(self):
        return self.target
    def start(self, skip = 0):
        assert not self.is_running()
        self._reset_timers()
        self._reset_counters()
        self._reset_trackers()
        if not self.is_setup():
            self.setup_subscription()
        self.running.set()
        self.run_timer.start()
        self.exports_skipped.decrement(skip)
        self.schedule_next_export(skip)
        return self.sid
    def stop(self):
        assert self.is_running()
        self.running.clear()
        self.run_timer.stop()
        try: 
            self.manager.destroy(self.sid)
        except: 
            msglog.exception(prefix="Handled")
    def reset_subscription(self):
        self._export_all_values = True
    def setup_subscription(self):
        assert not self.is_setup()
        try:
            self.sid = self.manager.create_polled(
                self.node_table, None, self.sid)
        except:
            msglog.exception()
        else:
            self._setup.set()
        assert self.is_setup()
        return self.sid
    def teardown_subscription(self):
        assert self.is_setup()
        try: 
            self.manager.destroy(self.sid)
        except: 
            msglog.exception(prefix="Handled")
        else:
            self._setup.clear()
        assert not self.is_setup()
        return self.sid
    def next_poll_time(self, skip = 0):
        offset = self.period + (skip * self.period)
        return ((int(time.time()) / self.period) * self.period) + offset
    def exports_possible(self):  
        runtime = self.export_time - self.first_export_time
        return (runtime / self.period)
    def prepare_to_export(self):
        exportstart = time.time()
        self.exports_started.increment()
        self.check_missed_exports(exportstart)
        transaction = self.active_transaction
        if transaction:
            if transaction.is_complete():
                if transaction.succeeded():
                    self.handle_export_success(transaction)
                else:
                    raise ETransactionException(transaction)
            elif transaction.is_expired():
                raise ETransactionTimeout(transaction)
            else:
                raise ETransactionInProgress(transaction)
        self._reset_timers()
        self.export_timer.start(exportstart)
    def get_export_data(self):
        messages = []
        self.poll_timer.start()
        if self._export_all_values:
            dblevel = 2
            messages.append('Polled all values')
            data = self.manager.poll_all(self.sid)
            self._export_all_values = False
        else:
            dblevel = 3
            messages.append('Polled COV values')
            data = self.manager.poll_changed(self.sid)
        self.poll_timer.stop()
        if self.debuglevel(dblevel):
            messages.append('%d values being returned' % len(data))
            self.debugout('%s\n' % '\n\t'.join(messages))
        return data
    def format_export_data(self, data):
        self.debugout('Formatting data.', 2)
        self.format_timer.start()
        data = self.formatter.format(data)
        self.format_timer.stop()
        self.debugout('Data formatted.', 2)
        return data
    def start_export_transaction(self, data):
        self.debugout('Creating export transaction', 2)

        self.active_transaction = self.transporter.transport(self.target, data, sid=self.sid)
        if(self.active_transaction == None):
            return
        self.transaction_start_timer.start()
        self.transaction_start_timer.stop()
        self.transaction_life_timer.start()
        self.active_transaction.set_timeout(self.period * 3)
        self.active_transaction.add_state_listener(self.notify_complete)
        if self.debuglevel(2):
            self.debugout('Export transaction created', 2)
            if self.debuglevel(4):
                self.debugout('Export transaction data: \n%r\n\n' % data)
        self.exports_processed.increment()
    def schedule_next_export(self, skip = 0):
        if not self.is_running():
            message = 'Not rescheduling because subscription stopped.'
            self.debugout(message, 1)
            return
        nextexport = self.next_poll_time(skip)
        if self.export_time is None:
            self.first_export_time = nextexport
        self.export_time = nextexport
        self.monitor.schedule_subscription(self, nextexport)
        self.exports_skipped.increment(skip)
        self.exports_scheduled.increment()
        return nextexport
    def handle_export_success(self, transaction):
        self.active_transaction = None
        self.export_successes.increment()
    def handle_export_timeout(self, error):
        """
            Transaction still pending and time exceeded export 
            period, which is also transport timeout value.
            No data has been sent to the server.
        """
        try:
            transaction = error.transaction
            errors = self.export_timeouts.pre_increment()
            message = 'Handling timed out export: %s' % transaction
            self.msglog(message, msglog.types.WARN)
            try: 
                transaction.handle_timeout()
            except:
                msglog.exception()
            self.record_failed_export(transaction, errors)
        finally:
            self.active_transaction = None
            self.schedule_next_export(1)
    def handle_export_pending(self, error):
        self.exports_deferred.increment()
        self.debugout('Previous export still pending.', 1)
        self.schedule_next_export(0)
    def handle_export_failure(self, error):
        """
            Transaction completed but returned error response 
            code.  Data was sent to the server and a response 
            was sent back, but the response code indicates that 
            the server failed to handle the request properly.
        """
        try:
            transaction = error.transaction
            failures = self.export_errors.pre_increment()
            if self.debuglevel(2):
                message = 'Handling errored out export: %r' % transaction
                self.msglog(message, msglog.types.WARN)
                self.record_failed_export(transaction, failures)
        finally:
            self.active_transaction = None
            self.schedule_next_export(1)
    def handle_export_exception(self, error, stage = None):
        """
            An uncaught exception was raised during export 
            process.  This indicates that one of the export 
            methods raised an exception.  The status may be 
            anything from uninitialized to the request having 
            been sent, and the response having been received.
            
            This method resets the subscription and reschedules 
            next export after skipping one period.
        """
        if not self.is_running():
            message = 'Ignoring exception because subscription stopped.'
            self.debugout(message, 1)
            return
        messages = ['Handling export exception']
        if isinstance(error, ETransactionInProgress):
            self.handle_export_pending(error)
        elif isinstance(error, ETransactionTimeout):
            self.handle_export_timeout(error)
        elif isinstance(error, ETransactionException):
            self.handle_export_failure(error)
        else:
            try:
                warning = msglog.types.WARN
                self.msglog('Handling uknown exception', warning)
                msglog.exception(prefix = 'handling')
                self.reset_subscription()
                self.msglog('Subscription reset', msglog.types.INFO)
                self.export_timer.stop()
                self.msglog('Export timer stopped', msglog.types.INFO)
                messages.append('Export timer stopped.')
                transaction = self.active_transaction
                if transaction:
                    try:
                        transaction.handle_error()
                    except:
                        self.msglog('Notify transaction failed.', warning)
                        msglog.exception(prefix = 'Handled')
                    else:
                        self.msglog(
                           'Transaction notified of failure', msglog.types.INFO)
            finally:
                self.active_transaction = None
                self.schedule_next_export(1)
                self.msglog('One export will be skipped', warning)
    def check_missed_exports(self, actual):
        scheduled = self.export_time
        exportdelta = actual - scheduled
        exportsmissed = int(exportdelta / self.period)
        if exportsmissed > 0:
            messages = ['Missed exports detected']
            messages.append('Scheduled export: %s' % time.ctime(scheduled))
            messages.append('Actual export: %s' % time.ctime(actual))
            messages.append('Configured period: %s' % self.period)
            messages.append('Delta between exports: %s' % exportdelta)
            messages.append('Periods missed: %s' % exportsmissed)
            self.msglog('%s\n' % '\n\t'.join(messages), msglog.types.WARN)
            self.exports_missed.increment(exportsmissed)
        return exportsmissed
    def record_successful_export(self, transaction, successes):
        messages = ['%s:' % self.toString()]
        runtime = self.export_time - self.first_export_time
        average = runtime / successes
        if self.debuglevel(2):
            message = 'Exports: %d, runtime: %0.1f sec'
            messages.append(message % (successes, runtime))
        if self.debuglevel(2):
            message = 'Period: %0.2f sec, effective: ~ %0.2f sec'
        else:
            message = '(%0.0f => ~%0.2f)'
        messages.append(message % (self.period, average))
        if self.debuglevel(2):
            messages.append(transaction.stats()[1:-1])
            messages.append(', '.join(self._timer_strings()))
            messages = ['\t\t- %s' % message for message in messages]
            messages.insert(0, 'Statistics of completed export:')
            message = '%s\n' % '\n'.join(messages)
        else:
            timeitems = [(timer.get_name().lower(), timer.get_lapse()) 
                         for timer in self._get_timers() 
                         if (timer.get_start() and timer.get_stop())]
            flighttime = transaction.get_flighttime()
            timeitems.append(('flight', flighttime))
            timestrs = ['(%s %0.2f)' % item for item in timeitems]
            messages.extend(timestrs)
            message = ' '.join(messages)
        self.debugout(message, 1)
    def record_failed_export(self, transaction, failures, outputdata = False):
        warning = msglog.types.WARN
        information = msglog.types.INFO
        self.msglog('Transaction failed: %r' % transaction, information)
        self.msglog('Failed request: %r' % transaction.request, information)
        if outputdata or self.debuglevel(2):
            message = 'Failed request data: \n%r\n'
            self.debugout(message % transaction.request.data)
        if transaction.is_complete():
            response = transaction.get_response()
            self.msglog('Failed response: %r.' % response, information)
            message = 'Failed response data: \n%r\n'
            self.debugout(message % response.read(), 0)
    def notify_complete(self, transaction):
        if transaction is self.active_transaction:
            self.transaction_life_timer.stop()
            self.export_timer.stop()
            if transaction.succeeded():
                successes = self.export_successes.value + 1
                if self.debuglevel(1):
                    self.monitor.enqueue_work(
                        self.record_successful_export, transaction, successes)
            else:
                failures = self.export_errors.value + 1
                self.monitor.enqueue_work(
                    self.record_failed_export, transaction, failures)
        else:
            messages = ['Completed transaction is not current']
            messages.append('Current: %r' % self.active_transaction)
            messages.append('Completed: %r' % transaction)
            self.msglog('\n\t- '.join(messages), msglog.types.WARN)
    def _setup_collaborators(self, monitor):
        self.monitor = monitor
        self.manager = monitor.get_subscription_manager()
        self.formatter = monitor.get_formatter()
        self.transporter = monitor.get_transporter()
    def _setup_counters(self):
        self.export_successes = Counter()
        self.export_timeouts = Counter()
        self.export_errors = Counter()
        self.exports_started = Counter()
        self.exports_processed = Counter()
        self.exports_deferred = Counter()
        self.export_transactions = Counter()
        self.exports_scheduled = Counter()
        self.export_exceptions = Counter()
        # Export scheduled following skip.
        self.exports_skipped = Counter()
        # Scheduled export called late.
        self.exports_missed = Counter()
    def _reset_counters(self):
        self.export_successes.reset()
        self.export_timeouts.reset()
        self.export_errors.reset()
        self.exports_started.reset()
        self.exports_processed.reset()
        self.exports_deferred.reset()
        self.export_transactions.reset()
        self.exports_scheduled.reset()
        self.export_exceptions.reset()
        self.exports_skipped.reset()
        self.exports_missed.reset()
    def _setup_timers(self):
        self.run_timer = Timer('Runtime')
        self.poll_timer = Timer('Poll')
        self.format_timer = Timer('Format')
        self.export_timer = Timer('Export')
        self.transaction_start_timer = Timer('Trans start')
        self.transaction_life_timer = Timer('Trans life')
    def _reset_timers(self):
        self.poll_timer.reset()
        self.format_timer.reset()
        self.export_timer.reset()
        self.transaction_start_timer.reset()
        self.transaction_life_timer.reset()
    def _setup_trackers(self):
        self.export_time = None
        self.first_export_time = None
        self.active_transaction = None
        self._export_all_values = False
    def _reset_trackers(self):
        self._setup_trackers()
    def _timer_string(self, prefix = '\t', sep = '\n'):
        timestrs = ['%s%s' % (prefix, timestr) 
                    for timstr in self._timer_strings()]
        return sep.join(timestrs)
    def _timer_strings(self):
        timers = self._get_timers()
        return map(str, timers)
    def _get_timers(self):
        return [self.export_timer, self.poll_timer, self.format_timer, 
                self.transaction_start_timer, self.transaction_life_timer]
    def debugout(self, dbmessage, dblevel = 1):
        if self.debuglevel(dblevel):
            self.msglog(dbmessage, msglog.types.DB)
    def debuglevel(self, level = 1):
        return level <= DEBUG
    def msglog(self, message, mtype = msglog.types.INFO, autoprefix = True):
        if autoprefix:
            message = '[%s] %s' % (self, message)
        msglog.log('broadway', mtype, message)
    def as_dictionary(self):
        configuration = {}
        configuration['monitor'] = self.monitor.url
        configuration['target'] = self.target
        configuration['nodes'] = self.node_table
        configuration['period'] = self.period
        configuration['retries'] = self.retries
        configuration['sid'] = self.sid
        return configuration
    def from_dictionary(klass, configuration):
        if not configuration.has_key('monitor'):
            msglog.log('broadway', msglog.types.WARN, 
                       'Creating monitor URL from formatter parent to '
                       'recreate subscription from %r' % configuration)
            formatter = rootspace.as_node(configuration['formatter'])
            configuration['monitor'] = formatter.parent.url
        monitor = rootspace.as_node(configuration['monitor'])
        target = configuration['target']
        nodes = configuration['nodes']
        period = configuration['period']
        retries = configuration['retries']
        sid = configuration['sid']
        return klass(monitor, target, nodes, period, retries, sid)
    from_dictionary = classmethod(from_dictionary)
    def __repr__(self):
        classname = self.__class__.__name__
        subscriptionnumber = self.subscription_number
        details = ['%s #%04d [%s]' % (classname, subscriptionnumber, self.sid)]
        counts = ['%dES' % self.exports_started.value]
        counts.append('%dEM' % self.exports_missed.value)
        counts.append('%dED' % self.exports_deferred.value)
        counts.append('%dEP' % self.exports_processed.value)
        counts.append('%dGD' % self.export_successes.value)
        counts.append('%dBD' % self.export_errors.value)
        counts.append('%dTO' % self.export_timeouts.value)
        counts.append('%dSK' % self.exports_skipped.value)
        details.append('(%s)' % '/'.join(counts))
        return '<%s>' % ' '.join(details)
    def toString(self):
        details = ['PS #%04d' % self.subscription_number]
        counts = ['%dES' % self.exports_started.value]
        counts.append('%dEM' % self.exports_missed.value)
        counts.append('%dED' % self.exports_deferred.value)
        counts.append('%dEP' % self.exports_processed.value)
        counts.append('%dGD' % self.export_successes.value)
        counts.append('%dBD' % self.export_errors.value)
        counts.append('%dTO' % self.export_timeouts.value)
        counts.append('%dSK' % self.exports_skipped.value)
        details.append('(%s)' % '/'.join(counts))
        return ' '.join(details)
    def __str__(self):
        classname = self.__class__.__name__
        return '%s #%d %r' % (classname, self.subscription_number, self.sid)

from mpx.service.virtuals._machine_generator import MachineBuilder
def setup_machine(filepath, name):
    configuration = open(filepath, 'r')
    builder = MachineBuilder(configuration)
    machine = builder.build(name, '/aliases/Equipment')
    print 'Setup Machine: ' + machine.name
    return machine

def setup_machines(basedir = '/var/mpx/config', extension = 'csv'):
    filenames = os.listdir(basedir)
    profiles = []
    for filename in filenames:
        if filename.endswith('.' + extension):
            filepath = os.path.join(basedir, filename)
            devicename = filename[0:filename.rindex('.')]
            profiles.append((filepath, devicename))
    machines = []
    for filepath, devicename in profiles:
        msglog.log('broadway', msglog.types.INFO, 
                   'Created machine "%s" from %s' % (devicename, filepath))
        try: 
            machines.append(setup_machine(filepath, devicename))
        except:
            msglog.exception(prefix = 'Handled')
    return machines

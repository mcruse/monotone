"""
Copyright (C) 2003 2005 2006 2010 2011 Cisco Systems

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
#
#
# @todo 2. Add emergency pool class that creates new temporary threads.
#          I.e.  It never waits for a thread to become active (may not
#          even have an actual pool.)
# @todo 3. Name the threads in the pool.

from exceptions import ENotRunning, EInternalError
from threading import NOTHING as NORESULT
from threading import Queue as _Queue
from threading import QueueFull as _QueueFull
from threading import ImmortalThread as _ImmortalThread
from threading import currentThread as _currentThread
from threading import Lock as _Lock
from threading import Condition as _Condition
from mpx.lib.thread import log_startup
from mpx.lib import msglog
import os

from time import sleep as _sleep
from _singleton import ReloadableSingletonFactory as \
     _ReloadableSingletonFactory

class _Unique:
    pass

_NOTSET = _Unique()

class _SingleShotQueue:
    __common_lock = _Lock()
    def __init__(self):
        self.__value = _NOTSET
        self.__ready = None
        return
    ##
    # @note Timeout is ignored because the PendingResult should not ever
    #       block.
    def put(self, object, timeout=None):
        self.__common_lock.acquire()
        if self.__value is not _NOTSET:
            self.__common_lock.release()
            raise EInternalError(
                "Only one put is allowed on a _SingleShotQueue."
                )
        self.__value = object
        if self.__ready is not None:
            self.__common_lock.release()
            self.__ready.acquire()
            self.__ready.notify()
            self.__ready.release()
        else:
            self.__common_lock.release()
        return
    def get(self, timeout=None):
        self.__common_lock.acquire()
        result = self.__value
        if result is not _NOTSET:
            self.__common_lock.release()
            return result
        else:
            if self.__ready is None:
                self.__ready = _Condition(self.__common_lock)
        self.__common_lock.release()
        self.__ready.acquire()
        if self.__value is _NOTSET:
            self.__ready.wait(timeout)
        result = self.__value
        if result is _NOTSET:
            result = NORESULT
        self.__ready.release()
        return result

class PendingAction(object):
    def __init__(self, action, *args, **keywords):
        self.__action = action
        self.__args = args
        self.__keywords = keywords
        return
    def __str__(self):
        return """PendingAction(%s):
    action:   %r
    args:     %r
    keywords: %r""" % (id(self), self.__action, self.__args, self.__keywords,)
    def _invoke(self, thread_queue):
        try:
            self.__action(*self.__args, **self.__keywords)
        except Exception, e:
            msglog.exception()
        return

class PendingResult(PendingAction):
    def __init__(self, response_queue, key, action, *args, **keywords):
        PendingAction.__init__(self, action, *args, **keywords)
        if response_queue is None:
            assert key is None, ("If queue is None, then key must be None.")
            self.__queue = _SingleShotQueue()
            self.__key = _NOTSET
        else:
            self.__queue = response_queue
            self.__key = key
        self.__result = NORESULT
        self.__exception = None
        return
    def __str__(self):
        return """PendingResult(%s):
    action:   %r
    args:     %r
    keywords: %r

    result:           %r
    response_queue:   %r
    result_exception: %r""" % (id(self),
                               self._PendingAction__action,
                               self._PendingAction__args,
                               self._PendingAction__keywords,
                               self.__result, self.__queue, self.__exception)
    def result(self, timeout=None):
        if self.__result is NORESULT:
            self.__queue.get(timeout)
        if self.__exception:
            raise self.__exception
        return self.__result
    def key(self):
        return self.__key
    def _invoke(self, thread_queue):
        try:
            self.__result = self._PendingAction__action(
                *self._PendingAction__args,
                **self._PendingAction__keywords
                )
        except Exception, e:
            self.__exeption = e
            self.__result = None
        if self.__queue is not None:
            try:
                if self.__queue.__class__ is not _SingleShotQueue:
                    # It's an 'external' queue, use a regular reference.
                    self.__queue.put(self, 0.0)
                else:
                    # It's a result() only queue, use a weak reference.
                    self.__queue.put(None, 0.0)
            except _QueueFull:
                # The target queue is full, but the thread pool refuses to
                # wait.  Requeue this 'no longer pending' result on the
                # thread pool with the action redefined as queuing the
                # result to the target queue.
                # @fixme Log an error that the target queue is full...
                self.__queue = None
                self._PendingAction__action = self.__queue.put
                self._PendingAction__args = (self, 0.0)
                self._PendingAction__keywords = {}
                # @note Thread queues never block.
                thread_queue.put(self)
            else:
                # Dereference everything no longer required.
                self.__queue = None
                self._PendingAction__action = None
                self._PendingAction__args = None
                self._PendingAction__keywords = None
        return

class _PoolThread(_ImmortalThread):
    _new_index = 0
    def __init__(self, queue, name='_PoolThread'):
        _ImmortalThread.__init__(self, name=name)
        self.__queue = queue
        self.__running = 1
        self.__started = 0
        self._new_index += 1		# @fixme:  Ugly, not atomic...
        self.__index = self._new_index
        self.__name = name
        return
    def run(self):
        self.__started = 1
        while self.__running:
            action = self.__queue.get()
            action._invoke(self.__queue)
        return
    def start(self):
        _ImmortalThread.start(self)
        log_startup(self,
                    'Thread Pool Thread With Name %s and Index %d' %
                    (self.__name, self.__index),
                    'TPT-%s-%d' % (self.__name, self.__index))
        while not self.__started:
            _sleep(0.001)
        return
    ##
    # Special method, invoked as an action that was queued to stop the target
    # thread.  If the current thread is not the target thread, requeue the
    # action so the target gets another shot at dequeuing it.  If the current
    # thread is the target, then mark 
    # self as should_die, set the __running flag to false and return.
    def __stop(self):
        current = _currentThread()
        target = self
        if current is target:
            self.should_die()
            self.__running = 0
        else:
            self.__queue.put(PendingResult(None, None, self.__stop))
            _sleep(0.001)
        return
    ##
    # Called by another thread to stop this thread.
    def stop(self, timeout=None):
        self.__queue.put(PendingResult(None, None, self.__stop))
        self.join(timeout)
        return

class ThreadPool:
    ##
    # Instanciate a ThreadPool of <code>maxthreads</code> threads.
    # @param maxthreads The maximum number of threads in the pool.
    def __init__(self, maxthreads, name='ThreadPool-?'):
        self.__queue = _Queue()
        self.__threads = []
        self.__running = 0
        self.__name = name
        for i in xrange(0,maxthreads):
            t = _PoolThread(self.__queue, name=self.__name + "(%d)" % i)
            t.start()
            self.__threads.append(t)
            self.__running = 1
        return
    ##
    # @return The number of threads in the thread pool.
    def size(self):
        return len(self.__threads)
    ##
    # Change the number of threads available in the thread pool.
    def resize(self, maxthreads):
        assert maxthreads > 0, "maxthreads must be > 0."
        while maxthreads != self.size():
            if maxthreads < self.size():
                t = self.__threads.pop()
                t.stop(0.0)
            else:
                t = _PoolThread(self.__queue)
                t.start()
                self.__threads.append(t)
        return
    ##
    # Stop all running threads in this pool, waiting up 60 seconds for each
    # thread to exit.
    #
    # @note This method primarily exists to support instanciation via the
    #       ReloadableSingletonFactory.
    def _unload(self):
        self.__running = 0
        while self.__threads:
            t = self.__threads.pop()
            t.stop(60.0)
        return
    def singleton_unload_hook(self):
        self._unload()
        return
    ##
    # Queue an ACTION on a ThreadPool for later processing.  Once queued,
    # the caller can interact with the returned PendingResult to determin when
    # the ACTION was completed and what it value it returned (or exception it
    # raised).
    #
    # @note If ACTION results in an uncaught exception, the exception is
    #       available via the returned PendingResult object and therefore is
    #       NOT logged to the msglog.
    #
    # @param action The callable object to invoke.
    # @param *args The arguments to pass to the callable object when it is
    #              invoked.
    # @param **keywords The keywords  to pass to the callable object when it is
    #                   invoked.
    # @return The PendingResult of the queued action.
    def queue(self, action, *args, **keywords):
        if not self.__running:
            raise ENotRunning
        assert callable(action), (
            "The action must be callable"
            )
        result = PendingResult(None, None, action, *args, **keywords)
        self.__queue.put(result)
        return result
    ##
    # Queue an ACTION on a ThreadPool for later processing.  On completion of
    # the ACTION it is put on the provided QUEUE as a PendingResult instance
    # which can be identified by it's KEY.
    #
    # @note If ACTION results in an uncaught exception, the exception is
    #       available via the queued PendingResult object and therefore is
    #       NOT logged to the msglog.
    #
    # @param queue The queue on which the result is put.
    # @param key A client specified identifier for this pending result.
    # @param action The callable object to invoke.
    # @param *args The arguments to pass to the callable object when it is
    #              invoked.
    # @param **keywords The keywords  to pass to the callable object when it is
    #                   invoked.
    # @return None
    def queue_on(self, queue, key, action, *args, **keywords):
        assert callable(action), (
            "The action must be callable"
            )
        self.__queue.put(PendingResult(queue, key, action, *args, **keywords))
        return None
    ##
    # Queue an ACTION on a ThreadPool for later processing.  Once queued,
    # the caller was no handle on the ACTION and no access to the result.
    #
    # @note This is more effecient than ThreadPool.queue() and
    #       ThreadPool.queue_on() because fewer objects are instanciated and
    #       intereacted with.
    # @note If ACTION results in an uncaught exception, the exception is
    #       logged to the msglog.
    #
    # @param action The callable object to invoke.
    # @param *args The arguments to pass to the callable object when it is
    #              invoked.
    # @param **keywords The keywords  to pass to the callable object when it is
    #                   invoked.
    # @return None
    def queue_noresult(self, action, *args, **keywords):
        if not self.__running:
            raise ENotRunning
        assert callable(action), (
            "The action must be callable"
            )
        self.__queue.put(PendingAction(action, *args, **keywords))
        return None
    ##
    # Queue an PendingResult on a ThreadPool for later processing.  Once
    # queued, the caller can interact with the PendingResult to determine when
    # the PENDING_RESULT was completed and what it value it returned (or
    # exception it raised).
    #
    # @note If PENDING_RESULT results in an uncaught exception, the exception
    #       is available via the returned PendingResult object and therefore is
    #       NOT logged to the msglog.
    #
    # @param pending_result The PendingResult to queue for deferred
    #                       processing.
    # @return PendingResult The PENDING_RESULT instance passed in.
    def queue_pending_result(self, pending_result):
        if not self.__running:
            raise ENotRunning
        self.__queue.put(pending_result)
        return pending_result
    ##
    # Queue an PendingAction on a ThreadPool for later processing.  Once
    # queued, the caller has no access to the result.
    #
    # @note This is more effecient than ThreadPool.queue_pending_result()
    #       because fewer objects are instanciated and intereacted with.
    # @note If PENDING_ACTION results in an uncaught exception, the exception
    #       is logged to the msglog.
    #
    # @param pending_action A PendingAction instance.
    # @return None
    def queue_pending_action(self, pending_action):
        if not self.__running:
            raise ENotRunning
        self.__queue.put(pending_action)
        return None

EMERGENCY = _ReloadableSingletonFactory(ThreadPool, 1, 'EMERGENCY')
HIGH = _ReloadableSingletonFactory(ThreadPool, 3, 'HIGH')
NORMAL = _ReloadableSingletonFactory(ThreadPool, 5, 'NORMAL')
LOW = _ReloadableSingletonFactory(ThreadPool, 2, 'LOW')

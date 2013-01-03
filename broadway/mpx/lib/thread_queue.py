"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
# A thread queue is similar to a thread pool (technically it uses a thread
# pool) that allows for some resource loading of shared pools and also some
# serialization of processing.

from threading import NOTHING as _NOTHING
from threading import Queue as _Queue
from threading import Lock as _Lock

from thread_pool import PendingAction
from thread_pool import PendingResult

class _PoolMixin:
    def __init__(self):
        self.__thread_queue = None
        self.__original_invoke = self._invoke
        self._invoke = self.__invoke
        return
    def __invoke(self, *args, **keywords):
        try:
            self.__original_invoke(*args, **keywords)
        finally:
            self.__thread_queue._lock.acquire()
            self.__thread_queue._n_active -= 1
            self.__thread_queue._lock.release()
            self.__thread_queue._drain()
        return

class ThreadQueueAction(PendingAction, _PoolMixin):
    def __init__(self, action, *args, **keywords):
        PendingAction.__init__(self, action, *args, **keywords)
        _PoolMixin.__init__(self)
        return
    def __str__(self):
        return (
            "**********************************\n" +
            ("ThreadQueueAction(%s):\n" % id(self)) +
            PendingAction.__str__(self) +
            "\n**********************************"
            )

class ThreadQueueResult(PendingResult, _PoolMixin):
    def __init__(self, response_queue, key,
                 action, *args, **keywords):
        PendingResult.__init__(self, response_queue, key,
                               action, *args, **keywords)
        _PoolMixin.__init__(self)
        return
    def __str__(self):
        return (
            "**********************************\n" +
            ("ThreadQueueResult(%s):\n" % id(self)) +
            PendingResult.__str__(self) +
            "\n**********************************"
            )

class ThreadQueue:
    def __init__(self, pool, max_threads=None):
        self._pool = pool
        self._max_threads = max_threads
        self._queue = _Queue()
        self._lock = _Lock()
        self._n_active = 0
        return
    def _drain(self):
        self._lock.acquire()
        try:
            while self._n_active < self._max_threads:
                pending_item = self._queue.get(0.0)
                if pending_item is _NOTHING:
                    break
                pending_item._pm_schedule(pending_item)
                self._n_active += 1
        finally:
            self._lock.release()
        return
    def singleton_unload_hook(self):
        self._unload()
        return
    ##
    # @note This method primarily exists to support instanciation via the
    #       ReloadableSingletonFactory.
    def _unload(self):
        self._pool._unload()
        return
    ##
    # Queue a ThreadQueueResult on a ThreadQueue for later processing.  Once
    # queued, the caller can interact with the ThreadQueueResult to determine
    # when the PENDING_RESULT was completed and what it value it returned (or
    # exception it raised).
    #
    # @note If PENDING_RESULT results in an uncaught exception, the exception
    #       is available via the returned ThreadQueueResult object and
    #       therefore is NOT logged to the msglog.
    #
    # @param pending_result The ThreadQueueResult to queue for deferred
    #                       processing.
    # @return ThreadQueueResult The PENDING_RESULT instance passed in.
    def queue_pending_result(self, pending_result):
        assert isinstance(pending_result, ThreadQueueResult), (
            "pending_result must be an instance of ThreadQueueResult"
            )
        pending_result._PoolMixin__thread_queue = self
        pending_result._pm_schedule = self._pool.queue_pending_result
        self._queue.put(pending_result)
        self._drain()
        return pending_result
    ##
    # Queue an ThreadQueueAction on a ThreadPool for later processing.  Once
    # queued, the caller has no access to the result.
    #
    # @note This is more effecient than ThreadPool.queue_pending_result()
    #       because fewer objects are instanciated and intereacted with.
    # @note If PENDING_ACTION results in an uncaught exception, the exception
    #       is logged to the msglog.
    #
    # @param pending_action A ThreadQueueAction instance.
    # @return None
    def queue_pending_action(self, pending_action):
        assert isinstance(pending_action, ThreadQueueAction), (
            "pending_result must be an instance of ThreadQueueAction"
            )
        pending_action._PoolMixin__thread_queue = self
        pending_action._pm_schedule = self._pool.queue_pending_action
        self._queue.put(pending_action)
        self._drain()
        return None
    ##
    # Queue an ACTION on a ThreadPool for later processing.  Once queued,
    # the caller can interact with the returned ThreadQueueResult to determin
    # when the ACTION was completed and what it value it returned (or exception
    # it raised).
    #
    # @note If ACTION results in an uncaught exception, the exception is
    #       available via the returned ThreadQueueResult object and therefore
    #       is NOT logged to the msglog.
    #
    # @param action The callable object to invoke.
    # @param *args The arguments to pass to the callable object when it is
    #              invoked.
    # @param **keywords The keywords  to pass to the callable object when it is
    #                   invoked.
    # @return The ThreadQueueResult of the queued action.
    def queue(self, action, *args, **keywords):
        pending_result = ThreadQueueResult(None, None,
                                           action, *args, **keywords) 
        self.queue_pending_result(pending_result)
        return pending_result
    ##
    # Queue an ACTION on a ThreadPool for later processing.  On completion of
    # the ACTION it is put on the provided QUEUE as a ThreadQueueResult
    # instance which can be identified by it's KEY.
    #
    # @note If ACTION results in an uncaught exception, the exception is
    #       available via the queued ThreadQueueResult object and therefore is
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
        self.queue_pending_result(ThreadQueueResult(queue, key,
                                                    action, *args, **keywords))
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
        self.queue_pending_action(ThreadQueueAction(action, *args, **keywords))
        return None

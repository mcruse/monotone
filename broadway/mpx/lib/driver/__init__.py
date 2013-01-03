"""
Copyright (C) 2002 2003 2004 2008 2011 Cisco Systems

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
# This module implements node drivers.

import sys as _sys
import traceback as _tb
import time

from mpx.lib import EnumeratedValue
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute
from mpx.lib.exceptions import *
from mpx.lib.node import ConfigurableNode
from mpx.lib.node import as_deferred_node
from mpx.lib.node import as_node_url
from mpx.lib.scheduler import scheduler
from mpx.lib.threading import Lock
from mpx.lib.thread_pool import ThreadPool

NUM_THREADS = 3
##
# instead of performing on the schedulers thread,
# this threadpool singleton is used to actually
# drive nodes.
class ThreadPoolSingleton(object):
    __instance = None
    def __init__(self, maxthreads=NUM_THREADS, name='Periodic Driver ThreadPool'):
        if ThreadPoolSingleton.__instance is None:
            ThreadPoolSingleton.__instance = ThreadPoolSingleton.__impl(maxthreads, name)
            self.__dict__['_ThreadPoolSingleton__instance'] = ThreadPoolSingleton.__instance
        return
    def __getattr__(self, attr):
        # Delegate to implementation
        return getattr(self.__instance, attr)
    def __setattr__(self, attr):
        # Delegate to implementation
        return setattr(self.__instance, attr, value)
    class __impl(ThreadPool):
        pass

##
# A periodic driver ...
class PeriodicDriver(ConfigurableNode):
    def __init__(self):
        ConfigurableNode.__init__(self)
        self._url = 'unknown'
        self._poll_event = None
        self._period = 30
        # Pre-load attributes.
        self.output = REQUIRED
        self.input = REQUIRED
        self.period = self._period
        self.asyncOK = 1
        self.cov_mode = 0
        self.debug = 0
        self.conversion = 'none'
        self.__running = False
        self._thread_pool = ThreadPoolSingleton()
        self._init_debug()
        self._output_lock = Lock()
        self._changes_at = 0
        self._value = None 
        self._lock = Lock()
        return
    def _conversion(self, value):
        if self.conversion == 'float':
            return float(value)
        if self.conversion == 'int':
            return int(value)
        if self.conversion == 'str':
            return str(value)
        return value
    def _begin_critical_section(self):
        self._lock.acquire()
        return
    def _end_critical_section(self):
        self._lock.release()
        return
    def _init_debug(self):
        #self.debug = 4
        self.DEBUG1 = self._debug_stub 
        self.DEBUG2 = self._debug_stub 
        self.DEBUG3 = self._debug_stub 
        self.DEBUG_EXC = self._debug_stub 
        if self.debug > 0:
            self.DEBUG_EXC = self._debug_exc
            self.DEBUG1 = self._debug_print
            if self.debug > 1:
                self.DEBUG2 = self._debug_print
                if self.debug > 2:
                    self.DEBUG3 = self._debug_print
        return
    def _schedule(self):
        self.DEBUG3("_schedule():\n")
        self._cancel_polling()
        if self.__running:
            self._poll_event = scheduler.after(
                self._period, self._queue_lock_and_poll_input)
        self.DEBUG3("_schedule: return\n")
        return
    def _drive_output(self, value):
        self._output_lock.acquire()
        try:
            self._output(value)
        finally:
            self._output_lock.release()
        return
    def _output(self, value):
        # always drive the output when not in cov_mode - otherwise,
        # only drive the output if the input has changed.
        if self.enabled and (not self.cov_mode or (value != self._value)):
            self.DEBUG3("_drive_output:  self.output=%s\n", self.output)
            self.output.set(value)
            self._value = value
            self.DEBUG2("_drive_output:  set:%r, got:%r\n",
                       value, self.output.get)
        else:
            self.DEBUG3("_drive_output:  No change\n")
        self.DEBUG3("_drive_output: return\n")
        return
    def time_remaining(self):
        self._output_lock.acquire()
        try:
            return self._changes_at - time.time()
        finally:
            self._output_lock.release()
        return
    def _cancel_polling(self):
        self.DEBUG3("_cancel_polling():\n")
        if self._poll_event is not None:
            e = self._poll_event
            self._poll_event = None
            if not e.expired():
                e.cancel()
                self.DEBUG2("_cancel_polling: canceled %s\n", e)
        self.DEBUG3("_cancel_polling: return\n")
        return
    def _poll_input(self):
        self._poll_event = None
        self.DEBUG3("_poll_input():\n")
        # @fixme: Create n "priority" threads for schedulies to use.
        #         ReadyTask(threads_queue, function), .__call_ -> add queue.
        try:
            self._drive_output(self._conversion(self.input.get()))
        except Exception, e:
            try:
                self.output.set_exception(e)
            except:
                pass
            # Start falling back...
            self.DEBUG_EXC("AUTO drive of output failed.")
            if self.backoff_on_failure:
                self._period = self._period * 2
                self.DEBUG1("Adjusting period to every %s seconds.",
                            self._period)
        else:
            if self.debug and self._period > self.period:
                self.DEBUG1("Restoring period to every %s seconds.",
                            self.period)
            self._period = self.period
        self._schedule() #this is what keeps us going
        self.DEBUG3("_poll_input: return\n")
        return
    def _queue_lock_and_poll_input(self):
        self._thread_pool.queue_noresult(self._lock_and_poll_input)
        return
    def _lock_and_poll_input(self):
        self.DEBUG3("_lock_and_poll_input()\n")
        self._begin_critical_section()
        try: self._poll_input()
        finally:
            self._end_critical_section()
            self.DEBUG3("_lock_and_poll_input: return\n")
        return
    def _debug_exc(self, fmt='', *args):
        _sys.stderr.write("EXCEPTION:  %r\n" % (fmt % args))
        _tb.print_exc(None,_sys.stderr)
        _sys.stderr.flush()
        return
    def _debug_print(self, fmt, *args):
        try:
            converted_args = []
            for arg in args:
                if callable(arg):
                    arg = arg()
                converted_args.append(arg)
            converted_args = tuple(converted_args)
            _sys.stderr.write("DEBUG(%r):  %s" % (self._url,
                                                  (fmt % converted_args)))
            _sys.stderr.flush()
        except:
            _sys.stderr.write("DEBUG FAILED:  self.DEBUG(%r, %r)\n" %
                              (fmt, args))
            self._debug_exc()
            _sys.stderr.write("\tself._url:  %r\n" % self._url)
            _sys.stderr.write("\tfmt:  %r\n" % fmt)
            _sys.stderr.write("\tconverted_args:  %r\n" % converted_args)
            _sys.stderr.flush()
        return
    def _debug_stub(self, fmt, *args):
        return
    ##
    # @see ConfigurableNode#configure
    #
    def configure(self, config):
        set_attribute(self, 'debug', self.debug, config, int)
        self._init_debug()
        self.DEBUG3("configure(%r):\n", config)
        ConfigurableNode.configure(self, config)
        self._url = as_node_url(self)
        if self.output is REQUIRED:
            self.output = self.parent
        set_attribute(self, 'output', self.parent, config, self.as_deferred_node)
        set_attribute(self, 'input', REQUIRED, config, self.as_deferred_node)
        set_attribute(self, 'period', self.period, config, float)
        set_attribute(self, 'asyncOK', self.asyncOK, config, int)
        # in cov mode, only changing values are driven.
        set_attribute(self, 'cov_mode', self.cov_mode, config, int)
        set_attribute(self, 'enabled', 1, config, as_boolean)
        set_attribute(self, 'backoff_on_failure', 0, config, as_boolean)
        set_attribute(self, 'conversion', self.conversion, config, str)
        self._period = self.period
        return
        
    ##
    # Get this objects configuration.
    #
    # @return Dictionary containg configuration.
    # @see ConfigurableNode#configuration
    #
    def configuration(self):
        config = ConfigurableNode.configuration(self)
        get_attribute(self, 'output', config, as_node_url)
        get_attribute(self, 'input', config, as_node_url)
        get_attribute(self, 'period', config, str)
        get_attribute(self, 'asyncOK', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'enabled', config, str)
        get_attribute(self, 'backoff_on_failure', config, str)
        get_attribute(self, 'conversion', config, str)
        return config
    def start(self):
        self.DEBUG3("start():\n")
        ConfigurableNode.start(self)
        self.__running = True
        self._begin_critical_section()
        try: self._poll_input()
        finally: self._end_critical_section()
        self.DEBUG3("start: return\n")
        return
    def stop(self):
        self.DEBUG3("stop():\n")
        ConfigurableNode.stop(self)
        self.__running = False
        self._begin_critical_section()
        try: self._cancel_polling()
        finally: self._end_critical_section()
        self.DEBUG3("stop: return\n")
        return
    def get_result(self, skipCache=0, **keywords):
        self.DEBUG3("get_result(skipCache=%r)\n", skipCache)
        result = Result()
        self._begin_critical_section()
        try: result.value = self._value
        finally: self._end_critical_section()
        result.timestamp = time.time()
        result.cached = not self.asyncOK
        self.DEBUG3("get_result: return %r\n", result)
        return result
    def disable(self):
        self._output_lock.acquire()
        try:
            self.enabled = 0
        finally:
            self._output_lock.release()
        return
    def is_disabled(self):
        self._output_lock.acquire()
        try:
            return not self.enabled
        finally:
            self._output_lock.release()
        return
    def enable(self):
        self._output_lock.acquire()
        try:
            self.enabled = 1
        finally:
            self._output_lock.release()
        return
    def is_enabled(self):
        self._output_lock.acquire()
        try:
            return self.enabled
        finally:
            self._output_lock.release()
        return
    def get(self, skipCache=0):
        self._begin_critical_section()
        try: result = self._value
        finally: self._end_critical_section()
        self.DEBUG3("get(skipCache=%r): return %r\n", skipCache, result)
        return result
    def as_deferred_node(self, node_ref):
        #set_attribute does not pass THIS node in for relative URLs
        return as_deferred_node(node_ref, self)
##
# A periodic relay driver.
class PeriodicRelayDriver(ConfigurableNode):
    def __init__(self):
        ConfigurableNode.__init__(self)
        self._url = 'unknown'
        self._poll_event = None
        self._period = 0.2
        # Pre-load attributes.
        self.off_text = "Off"
        self.on_text = "On"
        self.auto_text = "Auto"
        self.reverse_output = 0
        self.output = REQUIRED
        self.input = REQUIRED
        self.period = self._period
        self.asyncOK = 1
        self.state = 2
        self.debug = 0
        self.__running = False
        self._init_debug()
        self.OFF = EnumeratedValue(0, self.off_text)
        self.ON = EnumeratedValue(1, self.on_text)
        self.AUTO = EnumeratedValue(2, self.auto_text)
        self._NORMAL = 0
        self._SAFETY = 1
        self._output_state = self._NORMAL
        self._output_lock = Lock()
        self._changes_at = 0
        self._waiting_value = None
        self._value = None
        self._lock = Lock()
        return
    def _begin_critical_section(self):
        self._lock.acquire()
        return
    def _end_critical_section(self):
        self._lock.release()
        return
    def _init_debug(self):
        self.DEBUG1 = self._debug_stub 
        self.DEBUG2 = self._debug_stub 
        self.DEBUG3 = self._debug_stub 
        self.DEBUG_EXC = self._debug_stub 
        if self.debug > 0:
            self.DEBUG_EXC = self._debug_exc
            self.DEBUG1 = self._debug_print
            if self.debug > 1:
                self.DEBUG2 = self._debug_print
                if self.debug > 2:
                    self.DEBUG3 = self._debug_print
        return
    def _schedule(self):
        self.DEBUG3("_schedule():\n")
        self._cancel_polling()
        if self.__running:
            self._poll_event = scheduler.after(
                self._period, self._lock_and_poll_input)
        self.DEBUG3("_schedule: return\n")
        return
    def _drive_output(self, value, force=0):
        self._output_lock.acquire()
        try:
            if force:
                # Immediatly change the value.
                self._value = value
                self.output.set(value)
            else:
                # May be delayed by minimum on/off times.
                self._output(value)
        finally:
            self._output_lock.release()
        return
    def _output(self, value):
        value = value ^ self.reverse_output
        if self.enabled and (value is not self._value):
            self.DEBUG3("_drive_output:  self.output=%s\n", self.output)
            if self._output_state == self._SAFETY:
                self._waiting_value = value
            else:
                self.output.set(value)
                self._waiting_value = None
                self._value = value
                if (value == 1) and self.min_on_time > 0:
                    self._output_state = self._SAFETY
                    scheduler.after(self.min_on_time,
                                    self._clear_safety,())
                    self._changes_at = time.time() + self.min_on_time
                elif (value == 0) and self.min_off_time > 0:
                    self._output_state = self._SAFETY
                    scheduler.after(self.min_off_time,
                                    self._clear_safety,())
                    self._changes_at = time.time() + self.min_off_time
            self.DEBUG2("_drive_output:  set:%r, got:%r\n",
                       value, self.output.get)
        else:
            self.DEBUG3("_drive_output:  No change\n")
        self.DEBUG3("_drive_output: return\n")
        return
    def time_remaining(self):
        self._output_lock.acquire()
        try:
            if self._output_state == self._NORMAL:
                return 0
            return self._changes_at - time.time()
        finally:
            self._output_lock.release()
        return
    def _clear_safety(self):
        self._output_lock.acquire()
        try:
            self._output_state = self._NORMAL
            if self._waiting_value != None:
                self._output(self._waiting_value)
        finally:
            self._output_lock.release()
        return
    def _cancel_polling(self):
        self.DEBUG3("_cancel_polling():\n")
        if self._poll_event is not None:
            e = self._poll_event
            self._poll_event = None
            if not e.expired():
                e.cancel()
                self.DEBUG2("_cancel_polling: canceled %s\n", e)
        self.DEBUG3("_cancel_polling: return\n")
        return
    def _poll_input(self):
        self._poll_event = None
        self.DEBUG3("_poll_input():\n")
        # @fixme: Create n "priority" threads for schedulies to use.
        #         ReadyTask(threads_queue, function), .__call_ -> add queue.
        if self.state is self.AUTO:
            try:
                self._drive_output(int(self.input.get()))
            except:
                # Start falling back...
                self.DEBUG_EXC("AUTO drive of output failed.")
                self._period = self._period * 2
                self.DEBUG1("Adjusting period to every %s seconds.",
                            self._period)
            else:
                if self.debug and self._period > self.period:
                    self.DEBUG1("Restoring period to every %s seconds.",
                                self.period)
                self._period = self.period
            self._schedule()
        else:
            value = int(self.state)
        self.DEBUG3("_poll_input: return\n")
        return
    def _lock_and_poll_input(self):
        self.DEBUG3("_lock_and_poll_input()\n")
        self._begin_critical_section()
        try: self._poll_input()
        finally:
            self._end_critical_section()
            self.DEBUG3("_lock_and_poll_input: return\n")
        return
    def _set_state(self, value):
        self.DEBUG3("_set_state(%r):\n", value)
        self.ENUM_LIST = [self.OFF, self.ON, self.AUTO]
        self.STR_LIST = [str(self.OFF), str(self.ON), str(self.AUTO)]
        if value not in self.ENUM_LIST:
            if value in self.STR_LIST:
                value = self.ENUM_LIST[self.STR_LIST.index(value)]
            else:
                exception = EInvalidValue('state', value)
                self.DEBUG3("_set_state: raise %r\n", exception)
                raise exception
        else:
            value = self.ENUM_LIST[self.ENUM_LIST.index(value)]
        self.state = value
        self.DEBUG3("_set_state: %r\n", self.state)
        return self.state
    def _debug_exc(self, fmt='', *args):
        _sys.stderr.write("EXCEPTION:  %r\n" % (fmt % args))
        _tb.print_exc(None,_sys.stderr)
        _sys.stderr.flush()
        return
    def _debug_print(self, fmt, *args):
        try:
            converted_args = []
            for arg in args:
                if callable(arg):
                    arg = arg()
                converted_args.append(arg)
            converted_args = tuple(converted_args)
            _sys.stderr.write("DEBUG(%r):  %s" % (self._url,
                                                  (fmt % converted_args)))
            _sys.stderr.flush()
        except:
            _sys.stderr.write("DEBUG FAILED:  self.DEBUG(%r, %r)\n" %
                              (fmt, args))
            self._debug_exc()
            _sys.stderr.write("\tself._url:  %r\n" % self._url)
            _sys.stderr.write("\tfmt:  %r\n" % fmt)
            _sys.stderr.write("\tconverted_args:  %r\n" % converted_args)
            _sys.stderr.flush()
        return
    def _debug_stub(self, fmt, *args):
        return
    ##
    # @see ConfigurableNode#configure
    #
    def configure(self, config):
        set_attribute(self, 'debug', self.debug, config, int)
        self._init_debug()
        self.DEBUG3("configure(%r):\n", config)
        # @fixme Add the option to output on change (default), output every
        #        time, or the check the outputs state.
        ConfigurableNode.configure(self, config)
        self._url = as_node_url(self)
        if self.output is REQUIRED:
            self.output = self.parent
        set_attribute(self, 'off_text', self.off_text, config, str)
        set_attribute(self, 'on_text', self.on_text, config, str)
        set_attribute(self, 'auto_text', self.auto_text, config, str)
        set_attribute(self, 'reverse_output', self.reverse_output, config, int)
        set_attribute(self, 'output', self.parent, config, self.as_deferred_node)
        set_attribute(self, 'input', REQUIRED, config, self.as_deferred_node)
        set_attribute(self, 'period', self.period, config, float)
        set_attribute(self, 'asyncOK', self.asyncOK, config, int)
        set_attribute(self, 'state', self.state, config, self._set_state)
        set_attribute(self, 'enabled', 1, config, as_boolean)
        set_attribute(self, 'min_on_time', 0, config, float)
        set_attribute(self, 'min_off_time', 0, config, float)
        return
        
    ##
    # Get this objects configuration.
    #
    # @return Dictionary containg configuration.
    # @see ConfigurableNode#configuration
    #
    def configuration(self):
        config = ConfigurableNode.configuration(self)
        get_attribute(self, 'off_text', config, str)
        get_attribute(self, 'on_text', config, str)
        get_attribute(self, 'auto_text', config, str)
        get_attribute(self, 'reverse_output', config, str)
        get_attribute(self, 'output', config, self.as_deferred_node)
        get_attribute(self, 'input', config, as_node_url)
        get_attribute(self, 'period', config, str)
        get_attribute(self, 'asyncOK', config, str)
        get_attribute(self, 'state', config, str)
        get_attribute(self, 'debug', config, str)
        get_attribute(self, 'enabled', config, str)
        get_attribute(self, 'min_on_time', config, str)
        get_attribute(self, 'min_off_time', config, str)
        return config
    def start(self):
        self.DEBUG3("start():\n")
        self.OFF.text(self.off_text)
        self.ON.text(self.on_text)
        self.AUTO.text(self.auto_text)
        ConfigurableNode.start(self)
        self.__running = True
        self._begin_critical_section()
        try: self._poll_input()
        finally: self._end_critical_section()
        self.DEBUG3("start: return\n")
        return
    def stop(self):
        self.DEBUG3("stop():\n")
        ConfigurableNode.stop(self)
        self.__running = False
        self._begin_critical_section()
        try: self._cancel_polling()
        finally: self._end_critical_section()
        self.DEBUG3("stop: return\n")
        return
    def get_result(self, skipCache=0, **keywords):
        self.DEBUG3("get_result(skipCache=%r)\n", skipCache)
        result = Result()
        self._begin_critical_section()
        try: result.value = self.state
        finally: self._end_critical_section()
        result.timestamp = time.time()
        result.cached = not self.asyncOK
        self.DEBUG3("get_result: return %r\n", result)
        return result
    def disable(self):
        self._output_lock.acquire()
        try:
            self.enabled = 0
        finally:
            self._output_lock.release()
        return
    def is_disabled(self):
        self._output_lock.acquire()
        try:
            return not self.enabled
        finally:
            self._output_lock.release()
        return
    def enable(self):
        self._output_lock.acquire()
        try: 
            self.enabled = 1
        finally:
            self._output_lock.release()
        return
    def is_enabled(self):
        self._output_lock.acquire()
        try:
            return self.enabled
        finally:
            self._output_lock.release()
    def set_min_on_time(self, min):
        self._output_lock.acquire()
        try:
            self.min_on_time = min
        finally:
            self._output_lock.release()
        return
    def get_min_on_time(self):
        return self.min_on_time
    def set_min_off_time(self, min):
        self._output_lock.acquire()
        try:
            self.min_off_time = min
        finally:
            self._output_lock.release()
        return
    def get_min_off_time(self):
        return self.min_off_time
    def get(self, skipCache=0):
        self._begin_critical_section()
        try: result = self.state
        finally: self._end_critical_section()
        self.DEBUG3("get(skipCache=%r): return %r\n", skipCache, result)
        return result
    def states(self):
        self.DEBUG3("states():\n")
        list = []
        list.extend(self.ENUM_LIST)
        self.DEBUG3("states: return %r\n", list)
        return list
    def set(self, value, asyncOK=1):
        self.DEBUG3("set(%r, asyncOK=%r):\n", value, asyncOK)
        self._begin_critical_section()
        try:
            self._set_state(value)
            self.asyncOK = asyncOK
            self._cancel_polling()
            if self.state == self.AUTO:
                self._poll_input()
            else:
                # Explicitly set ON/OFF states bypass the minimum on/off times.
                self._drive_output(int(self.state), 1)
            self.DEBUG3("set: return\n")
        finally:
            self._end_critical_section()
        return
    def as_deferred_node(self, node_ref):
        #set_attribute does not pass THIS node in for relative URLs
        return as_deferred_node(node_ref, self)

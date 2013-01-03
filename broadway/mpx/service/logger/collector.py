"""
Copyright (C) 2001 2002 2004 2006 2008 2010 2011 Cisco Systems

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
# @import types, time, select, threading, thread, mpx.lib
#
import time
import select
import mpx
import mpx.lib
from mpx.lib.node import as_node
from mpx.lib import threading
from mpx.lib.exceptions import EAlreadyRunning
from mpx.lib.exceptions import ETypeError
from mpx.lib.scheduler import scheduler
from types import *

##
# @return An integer indicating the relative postion of c1 and c2 where:<br>
#         < 0: if c1 should be before c2.<br>
#         0: if c1 is in the same position as c2.<br>
#         > 0: if c1 should be after c2.
def _column_sort(c1, c2):
    return c1.position - c2.position

##
#
class Collector:
    ##
    # @author Craig Warren
    # @param name
    #  name of the collector
    # @param log
    #  the log that the collector should use
    # @param period
    #  the period to collect at in seconds. Example 900 = 15 mins
    # @param trgger
    #  an optional nodepath of a trigger that gates whether or not a log entry should be collected
    # @return None
    #
    def __init__(self, log, period, trigger=None):
        self.log = log
        self.period = period
        self.poll = select.poll()
        self._lock = threading.Lock()
        self._scheduled = None
        self.running = 0
        self.msglog = mpx.lib.msglog
        self.columns = []
        self.trigger = trigger
        self._collect_failure = {}
    def pause(self):
        self._lock.acquire()
    def play(self):
        self._lock.release()
    ##
    # @author Craig Warren
    # @param column
    #   an instanciated mpx.service.logger.column to add
    # @return None
    #
    def add_column(self,column):
        self.columns.append(column)
        self.columns.sort(_column_sort)
    def go(self):
        if self._scheduled is not None and self.scheduled_time() > time.time():
            # The drifting clock has done us in...
            self._scheduled = scheduler.at(self.scheduled_time(), self.go, ())
            return
        thread = threading.Thread(name=self.log.name,
                                  target=self.collect,args=())
        thread.start()
    def collect(self):
        self._lock.acquire()
        try:
            if self.trigger:
                try:
                    v = as_node(self.trigger).get()
                except:
                    self.msglog.log("logger", self.msglog.types.ERR,
                                    "Could not resolve trigger - possibly nascent.")
                    v = 1
                if v:
                    self._collect()
            else:
                self._collect()
        finally:
            self._lock.release()
            if self.running:
                self._schedule()
    ##
    # @author Craig Warren
    #   collects the data and add_entry into the log
    #   for all the columns in self.columns
    # @return None
    #
    def _collect(self):         
        entry = self.get_entry()
        self.log.add_entry(entry)
    def get_entry(self):
        entry = []
        for column in self.columns:
            column_name = log_name = 'unknown'
            try: column_name = column.name
            except: self.msglog.exception()
            try:
                entry.append(column.function())
                self._collect_failure[column_name] = False
            except:
                entry.append(None)
                if not self._collect_failure.get(column_name):
                    self.msglog.exception()
                    # Report information about the columnn that failed.
                    try:	log_name = self.log.name
                    except:	self.msglog.exception()
                    self.msglog.log("logger", self.msglog.types.ERR,
                                    "Could not get value for column %r in log %r."
                                    % (column_name, log_name,))
                    self._collect_failure[column_name] = True
                # If function not callable - likely start related issue wrt AutoDiscovered nodes
                # Try to restart the column
                if not callable(column.function):
                    self.msglog.log("logger", self.msglog.types.ERR,
                                    "Restarting column %r in log %r."
                                    % (column_name, log_name,))
                    try:
                        column.stop()
                        column.start()
                    except: self.msglog.exception()
                continue
        return entry
    def _schedule(self):
        if self.period == 0:
            self._scheduled = None
            return
        self._scheduled = scheduler.at(self.next_scheduled_time(),self.go,())
    ##
    # @author Craig Warren
    #   starts a new thread to collect the data
    #   prints a messages type INFO to the msglog stating that it started
    # @return None
    #
    def start(self):
        if self.running:
            raise EAlreadyRunning('Collector is already running')
        self.running = 1
        self._schedule()
        msg = '%s:  Starting "%s" collector.' % ('/services/logger',
                                                 self.log.name)
        self.msglog.log('broadway', self.msglog.types.INFO, msg)
    ##
    # @author Craig Warren
    #   stops the collector form collecting data
    #   prints a message type INFO to the msglog stating that it's stopping
    # @return None
    #
    def stop(self):
        self.running = 0
        scheduled = self._scheduled
        self._scheduled = None
        if scheduled is not None:
            try:
                scheduled.cancel()
            except:
                pass
        msg = '%s:  Stopping "%s" collector.' % ('/services/logger',
                                                 self.log.name)
        self.msglog.log('broadway', self.msglog.types.INFO, msg)  
    ##
    # @author Craig Warren
    #   determines the next scheduled time to collect data
    # @return float
    #  the value in seconds from the epoch of the next scheduled time to
    #  collect data
    #
    def next_scheduled_time(self):
        now = int(time.time())
        last_time = now - (now % self.period)
        next_time = last_time + self.period
        return float(next_time)
    ##
    # @author Craig Warren
    #   the sceduled time the collection took place
    # @return float
    #   the number of secs since the epoch of the last
    #   time the data was collected
    #
    def scheduled_time(self):
        if self.period == 0:
            self._scheduled = None
            return time.time()
        return float(int(self.next_scheduled_time()) - self.period)


"""
Copyright (C) 2003 2008 2010 2011 Cisco Systems

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
import types
import string
from Queue import Queue
from mime_types import table
from mpx.lib import threading

class Fifo(list):
    def is_empty(self):
        return not len(self)
    def first(self):
        return self[0]
    def last(self):
        return self[-1]
    def get_first(self, default = None):
        if self:
            return self[0]
        return default
    def get_last(self, default = None):
        if self:
            return self[-1]
        return default
    def pop (self):
        try:
            return (1, list.pop(self, 0))
        except IndexError:
            return (0, None)
    def push(self, data):
        self.append(data)

class RequestManager(object):
    def __init__(self):
        self._queue = AdjustableQueue()
        self._thread_surplus = 0
    def add_threads(self,count):
        assert (type(count) is types.IntType or
                type(count) is types.LongType),("count must be an integer")
        assert count > 0, ("count must be > 0")
        self._thread_surplus -= count
        while self._thread_surplus < 0:
            r = RequestThread(self._queue)
            r.start()
            self._thread_surplus += 1
            self._queue.set_threshold(self._queue.get_threshold() + 1)
        return
    def remove_threads(self,count):
        assert (type(count) is types.IntType or
                type(count) is types.LongType),("count must be an integer")
        assert count > 0, ("count must be > 0")
        self._thread_surplus -= count
        return
    def add_request(self,request):
        self._queue.put(request)
        return
    def accepting_requests(self):
        return not self._queue.full()

class AdjustableQueue(Queue):
    def set_threshold(self, maxsize):
        self.maxsize = maxsize
    def get_threshold(self):
        return self.maxsize

class RequestThread(threading.ImmortalThread):
    _sequence = 0
    def __init__(self,queue):
        self.__active_request = None
        self.queue = queue
        threading.ImmortalThread.__init__(self,name=self._next_name())
        return
    def __get_active_request(self):
        request = self.__active_request
        if request is None:
            raise AttributeError('No request active.')
        return request
    active_request = property(__get_active_request)
    def _next_name(self):
        self._sequence += 1
        return "Redusa Request Pool %d" % self._sequence
    def run(self):
        while 1:
            try:
                self.__active_request =  self.queue.get()
                try: self._handle_active_request()
                finally: self.__active_request = None
            except Exception, error:
                raise
        return
    def _handle_active_request(self):
        request = self.active_request
        try: request.send_to_handler()
        #CSCtf12664
        except Exception, e: request.exception(e.message)


# It is tempting to add an __int__ method to this class, but it's not
# a good idea.  This class tries to gracefully handle integer
# overflow, and to hide this detail from both the programmer and the
# user.  Note that the __str__ method can be relied on for printing out
# the value of a counter:
#
# >>> print 'Total Client: %s' % self.total_clients
#
# If you need to do arithmetic with the value, then use the 'as_long'
# method, the use of long arithmetic is a reminder that the counter
# will overflow.
class Counter:
    "general-purpose counter"
    def __init__ (self, initial_value=0):
        self.value = initial_value
    def increment (self, delta=1):
        result = self.value
        try:
            self.value = self.value + delta
        except OverflowError:
            self.value = long(self.value) + delta
        return result
    def decrement (self, delta=1):
        result = self.value
        try:
            self.value = self.value - delta
        except OverflowError:
            self.value = long(self.value) - delta
        return result
    def as_long (self):
        return long(self.value)
    def __nonzero__ (self):
        return self.value != 0
    def __repr__ (self):
        return '<counter value=%s at %x>' % (self.value, id(self))
    def __str__ (self):
        return str(long(self.value))[:-1]
def get_content_type(path):
    ext = _get_extension(path)
    return table[ext]
def get_extension(content_type):
    for entry in table.items():
        if content_type == entry[1]:
            return entry[0]
    raise KeyError(content_type)
def _get_extension(path):
    dirsep = string.rfind(path, '/')
    dotsep = string.rfind(path, '.')
    if dotsep > dirsep:
        return path[dotsep+1:]
    else:
        return ''


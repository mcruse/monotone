"""
Copyright (C) 2001 2002 2005 2007 2008 2010 2011 Cisco Systems

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
from time import time, sleep

from mpx.lib.modbus.command import ReadHoldingRegisters
from mpx.ion import Result
from mpx.lib.node import CompositeNode
from mpx.lib import msglog
from mpx.lib.exceptions import ETimeout
from mpx.lib.threading import Lock

CSI = '\x1b[' #ANSI escape
CSIreset = CSI+'0m'

debug = 0

class _EntryION(CompositeNode):
    def __init__(self, cache, name, offset,
                 unbound_read, unbound_write):
        self.cache = cache
        self.offset = offset
        self.read = unbound_read
        self.write = unbound_write
        self.debug = 0
        ##
        # bit field:
        #   bit 0=byte order, 1=word order, bit 2=bit order. 000=Network order
        self.orders = 0
        return
    def get(self, skipCache=0):
        if self.debug: print 'Get modbus point', self.offset, self.cache
        return self.get_result(skipCache).value
    def get_result(self, skipCache=0):
        cache = self.cache
        cache.lock.acquire()
        try:
            if skipCache or (cache.response is None) or \
               ((cache.timestamp + cache.ttl) < time()):
                cached = 0
                cache._refresh()
            else:
                cached = 1
            result = Result()
            result.timestamp = cache.timestamp
            result.cached = cached
            result.value = apply(self.read, [cache.response,
                                             self.offset,
                                             cache.start,
                                             self.orders])
        finally:
            cache.lock.release()
        return result
    def _set(self, value, asyncOK=1):
        cache = self.cache
        cache.lock.acquire()
        try:
            apply(self.write, [cache.writer, self.offset, value, self.orders])
            cache.response = None
        finally:
            cache.lock.release()

class EntryION(_EntryION):
    def __init__(self, cache, name, offset,
                 unbound_read, unbound_write):
        CompositeNode.__init__(self)
        _EntryION.__init__(self, cache, name, offset,
                 unbound_read, unbound_write)
        self.configure({'parent':cache.ion,'name':name})
    def set(self, value, asyncOK=1):
        self._set(value, asyncOK)

class RegisterCache:
    def __init__(self, ion, slave_address, writer_class, ttl=1.0,
                 entry=None, ip=None):
        self.ion = ion
        self.lh = ion.line_handler
        self.slave_address = slave_address
        self.writer = writer_class(self)
        self.ttl = ttl
        self.start = None
        self.count = 0
        self.last  = self.start
        self.map   = {}
        self.command  = None
        self.response = None
        self.timestamp = time()
        self.entry = entry
        self.ip = ip
        self.lock = Lock() # Light weight, non-reentrant lock.
        self.error_count = 0
        self.last_error = None
        self.error_rate = 0.0


    def map_register_entry(self, entry): #for subclasses of _GenericPoint
        self._map_register(entry, entry.length)
        return self
        
    def map_register(self, start, count, name, unbound_read, unbound_write):
        entry = EntryION(self, name, start, unbound_read, unbound_write)
        entry.read_command_class = ReadHoldingRegisters
        self._map_register(entry, count)
        return entry

    #Entry can be either the local EntryION or a subclass of _GenericPoint
    def _map_register(self, entry, count):
        start = entry.offset
        self.map[entry.name] = entry

        end = start + count - 1
        if not self.count:
            self.start = start
            self.last = end
        if start < self.start:
            self.start = start
        if end > self.last:
            self.last = end

        self.count = self.last - self.start + 1
        self.response = None
        self.command = entry.read_command_class(self.slave_address,
                                            self.start, self.count)
        return
    def _refresh(self):
        t1 = time()
        e = None
        self.lh.port.lock()
        for i in range(0,self.lh.retries):
            try:
                if self.ip is None:
                    self.response = self.lh.command(self.command)
                else:
                    self.response = self.lh.command(self.command, self.ip)
                self.timestamp = time()
                e = None
                self.last_error = None
                self.error_rate = self.error_rate * 99.0 / 100.0

                break
            except Exception, e:
                if self.ip:
                    sleep(3) #get tcp sockets some time to recover
                pass
        # Not in finally because in all exceptions are caught.
        self.lh.port.unlock()
        if debug:
            if e is None:
                print CSI+(
                    '46m READ: %s to: %s took: %05d msec, error: %s' %
                    (str(self), str(self.ip), 1000*(time() - t1), str(e))
                    )+CSIreset
            else:
                print CSI+(
                    '41;37;1m READ: %s to: %s took: %05d msec, error: %s' %
                    (str(self), str(self.ip), 1000*(time() - t1), str(e))
                    )+CSIreset
        if e:
            self.last_error = e
            self.error_count += 1
            self.error_rate = ((self.error_rate * 99.0 ) + 1.0) / 100.0
            if self.lh.report_timeouts or self.response is None:
                raise ETimeout(str(e))
        return
    def get_result(self, name, skipCache=0):
        entry = self.map[name]
        return entry.get_result(skipCache)

    def get_value(self, name, skipCache=0):
        return self.get_result(self, name, skipCache).value
    def __str__(self):
        return (
            'modbus register cache, start: %04d count: %02d ttl: %02d ip: %s'
            % (self.start, self.count, self.ttl, str(self.ip))
            )

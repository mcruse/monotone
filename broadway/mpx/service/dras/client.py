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
from SOAPpy.Types import *

from mpx.lib import msglog
from mpx.lib import Result

from mpx.lib.msglog.types import INFO

from mpx.lib.node import CompositeNode

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.soap.soap_proxy import RemoteWebServiceProxy

from mpx.lib.thread_pool import NORMAL

from mpx.lib.threading import Lock

from mpx.lib.scheduler import scheduler

from mpx.lib.exceptions import ETimeout

import time

class DRASManager(RemoteWebServiceProxy):
    def __init__(self):
        super(DRASManager, self).__init__()
        self.__scheduled = None
        self.__observers = {}
        self.__lock = Lock()
        self.running = 0
        return
        
    def configure(self, cd):
        super(DRASManager, self).configure(cd)
        set_attribute(self, 'poll_freq', 60, cd, int)
        set_attribute(self, 'debug', 0, cd, int)
        return
        
    def configuration(self):
        cd = super(DRASManager, self).configuration()
        get_attribute(self, 'poll_freq', cd)
        get_attribute(self, 'debug', cd)
        return cd
    
    def start(self):
        super(DRASManager, self).start()
        if self.debug > 1:
            # dump soap messages to the console
            self._set_soap_debug_lvl(1)
        if not self.running:
            self.running = 1
            self._trigger_queue()
        return
        
    def stop(self):
        self.running = 0
        super(DRASManager, self).stop()
        return
        
    def _set_soap_debug_lvl(self, lvl):
        self._proxy.soapproxy.config.dumpSOAPIn = lvl
        self._proxy.soapproxy.config.dumpSOAPOut = lvl
        return
    
    def register(self, soap_func, obj):
        self.__lock.acquire()
        try:
            callback_list = self.__observers.get(soap_func)
            if callback_list is None:
                callback_list = []
                self.__observers[soap_func] = callback_list
            if not obj in callback_list:
                callback_list.append(obj)
        finally:
            self.__lock.release()
        return
                
    def unregister(self, soap_func, obj):
        self.__lock.acquire()
        try:
            callback_list = self.__observers.get(soap_func)
            if callback_list is None:
                return
            try:
                callback_list.remove(obj)
            except ValueError:
                # it's already gone
                pass
        finally:
            self.__lock.release()
        return
        
    def _do_poll(self):
        if self.debug:
            msglog.log(
                'DRAS',
                INFO,
                'Polling the demand response server'
            )
        for soap_func, callback_list in self.__observers.items():
            for obj in callback_list:
                args = obj.get_args()
                try:
                    if args:
                        value = soap_func(*args)
                    else:
                        value = soap_func()
                except:
                    # SOAP errors live here
                    if self.debug:
                        msglog.log(
                            'DRAS',
                            INFO,
                            'Error polling the demand response server'
                        )
                        msglog.exception()
                    value = ETimeout()
                obj.update(value)
        self._schedule()
        return

    def _trigger_queue(self):
        NORMAL.queue_noresult(self._do_poll)
        return
        
    def _schedule(self):
        if self.running:
            self.poll_freq
            self._scheduled = scheduler.seconds_from_now_do(
                self.poll_freq, 
                self._trigger_queue
            )
        return
            
class Observer(CompositeNode):
    def __init__(self):
        self._last_result = None
        super(Observer, self).__init__()
        return
        
    def update(self, value):
        ts = time.time()
        if self._last_result is None:
            last_ts = ts
            changes = 0
        else:
            last_ts = self._last_result.timestamp
            changes = self._last_result.changes
        if not isinstance(value, Exception):
            # we've found that different servers
            # ie. pg&e vs sce, despite sharing wsdl's
            # have different return values.  :(
            value = self._get_value(value)
        self._last_result = Result(
            value,
            ts,
            0,
            changes
        )
        return
    
    def _get_value(self, value):
        try:
            value = float(value)
        except ValueError:
            if isinstance(value, str):
                vmap = {'false':0, 'true':1}
                value = vmap.get(value.lower(), value)
        return value
        
    def get_args(self):
        return ()
        
    def get(self, skipCache=0):
        return self.get_result(skipCache).value
        
    def get_result(self, skipCache=0):
        return self._last_result
            
class EventPending(Observer):
    def start(self):
        soap_func = getattr(self.parent, 'isAPEEventPending')
        self.parent.register(soap_func, self)
        super(EventPending, self).start()
        return
        
    def stop(self):
        soap_func = getattr(self.parent, 'isAPEEventPending')
        self.parent.unregister(soap_func, self)
        return
    
class Price(Observer):
    def start(self):
        soap_func = getattr(self.parent, 'getPrice')
        self.parent.register(soap_func, self)
        super(Price, self).start()
        return
        
    def stop(self):
        soap_func = getattr(self.parent, 'getPrice')
        self.parent.unregister(soap_func, self)
        super(Price, self).stop()
        return
    
    def get_args(self):
        args = (doubleType(0.0, 'double_1'),)
        if self._last_result and isinstance(self._last_result.value, float):
            args = (doubleType(self._last_result.value, 'double_1'),)
        return args
            
    

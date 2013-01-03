"""
Copyright (C) 2010 2011 Cisco Systems

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
    Point Caches are collections of points whose values 
    are updated by subscription.
    
    The Cached Points within a Point Cache are configured 
    with a 'source', which is the node from which the Cached 
    Point's value comes from.
    
    At startup, Point Cache instances create subscriptions 
    whose node-tables map Cached Point names to Cached Point 
    sources.  
    
    Periodic Point Caches periodically poll the subscription 
    for changes, updating Cached Point children when new values 
    are received.
    
    Eventually support for a Pushed Point Cache will be added, 
    which use delivered subscriptions to receive updates as 
    they occur.
    
    Cached Points will support COV.  Upon being updated, the 
    Cached Point will generate a COV event.
"""
import time
from threading import RLock
from mpx.lib import msglog
from mpx.lib import Result
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.lib.scheduler import scheduler
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import as_boolean
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.event import EventConsumerMixin
from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ChangeOfValueEvent as COVEvent
from moab.linux.lib import uptime
Undefined = object()

class PointCache(CompositeNode, EventConsumerMixin):
    """
        Collection of points whose values are provided by subscription.
        
        Point Caches can be poll-based or notification-based, which 
        is controlled by the boolean 'polled' attribute's value.
        
        Polled Point Caches can be configured with a period, in which 
        case the subscription is polled periodically to provide updates.
        
        If a polled Point Cache's period is 0 (zero), then no automatic 
        polling takes place.  Such Point Cache's values must be explicitly 
        updated by invoking the Point Cache's "refresh()" method.
    """
    def __init__(self):
        self.sid = None
        self.period = 0
        self.polled = False
        self.manager = None
        self.scheduled = None
        super(PointCache, self).__init__()
    def subscribed(self):
        return self.sid is not None
    def nodemap(self):
        points = self.children_nodes()
        return dict([(point.name,point.source) for point in points])
    def configure(self, config):
        set_attribute(self, "period", 0, config, int)
        set_attribute(self, "polled", False, config, as_boolean)
        return super(PointCache, self).configure(config)
    def configuration(self):
        config = super(PointCache, self).configuration()
        get_attribute(self, 'period', config, str)
        get_attribute(self, 'polled', config, str)
        return config
    def start(self):
        if self.scheduled:
            raise TypeError("start() invoked with non-None scheduled")
        self.manager = as_node("/services/Subscription Manager")
        if self.has_children():
            if self.polled:
                # Set timeout to None with subscription.
                self.sid = self.manager.create_polled(self.nodemap(), None)
                if self.period:
                    self.scheduled = scheduler.every(self.period,self.refresh)
            else:
                self.sid = self.manager.create_delivered(self, self.nodemap())            
        return super(PointCache, self).start()
    def stop(self):
        if self.scheduled:
            self.scheduled.cancel()
        self.scheduled = None
        if self.subscribed():
            self.manager.destroy(self.sid)
        self.sid = None
        self.manager = None
        return super(PointCache, self).stop()
    def event_handler(self, event):
        self.update(event.results())
    def event_exception(self, exc, event):
        msglog.exception()
    def refresh(self):
        if not self.polled:
            raise TypeError("refresh() called on non-polled Point Cache")            
        return self.update(self.manager.poll_changed(self.sid))
    def update(self, changes):
        for nid,result in changes.items():
            try:
                self.get_child(nid).update(result)
            except:
                msglog.exception()
        return len(changes)
    def get_results(self):
        results = {}
        for point in self.children_nodes():
            results[point.name] = point.get_result()
        return results
    def get_values(self):
        values = {}
        for point in self.children_nodes():
            values[point.name] = point.get_value()
        return values
    def _add_child(self, *args, **kw):
        if self.is_running():
            raise TypeError("Cannot add children while running")
        return super(PointCache, self)._add_child(*args, **kw)
    def _remove_child(self, *args, **kw):
        if self.is_running():
            raise TypeError("Cannot remove child while running")
        return super(PointCache, self)._remove_child(*args, **kw)

class CachedPoint(CompositeNode, EventProducerMixin):
    """
        Point whose value is updated by parent point-cache.
    """
    def __init__(self):
        self.source = None
        self.updated = 0
        self.synclock = RLock()
        self.result = Undefined
        self.support_cov = False
        self.created = uptime.secs()
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
    def configure(self, config):
        set_attribute(self, "source", REQUIRED, config)
        set_attribute(self, "support_cov", False, config, as_boolean)
        return super(CachedPoint, self).configure(config)
    def configuration(self):
        config = super(CachedPoint, self).configuration()
        get_attribute(self, "source", config)
        get_attribute(self, "support_cov", config, str)
        return config
    def since_created(self):
        return uptime.secs() - self.created
    def since_updated(self):
        return uptime.secs() - self.updated
    def initialized(self):
        return self.result is not Undefined
    def has_cov(self):
        return self.support_cov
    def get_result(self):
        self.synclock.acquire()
        try:
            if not self.initialized():
                raise TypeError("Cached value not unitialized.")
            result = self.result
        finally:
            self.synclock.release()
        return result
    def get_value(self):
        """
            Get current value.
        """
        return self.get_result().value
    def get(self):
        """
            Get current value, raising exception if value is error.
        """
        value = self.get_value()
        if isinstance(value, Exception):
            raise value
        return value
    def update(self, result):
        if not isinstance(result, Result):
            if isinstance(result, dict):
                result = Result.from_dict(result)
            else:
                message = "update() expects Result instance, not: %r"
                raise ValueError(message % result)
        self.synclock.acquire()
        try:
            if self.initialized():
                previous = self.get_value()
            else:
                previous = None
            self.result = result
            value = self.get_value()
            self.updated = uptime.secs()
        finally:
            self.synclock.release()
        if self.support_cov:
            self.event_generate(COVEvent(self, previous, value, time.time()))
        if self.debug:
            msglog.debug("%s updated: %r" % (self, result))

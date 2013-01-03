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
import time
import math
import bisect
import itertools
from Queue import Queue
from threading import Lock
from operator import itemgetter
from functools import update_wrapper
from collections import deque
from collections import defaultdict
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import CompositeNode
from mpx.lib.thread_pool import NORMAL
from mpx.lib.scheduler import scheduler
from mpx.service.alarms2.alarmevent import StateEvent
from moab.linux.lib import uptime
DEBUG = 0
Undefined = object()

class PrioritySet(object):
    """
        Priority sorted set of values.
        
        Maintains sorted set of unique values based on numeric 
        priority.  Intended use as high-performance sorted 
        sequence of Event GUIDs, prioritized by timestamp.
        
        Default sort-order is ascending, placing oldest 
        Event GUIDs last; use keyword argument 'descending' 
        with True value to reverse default.
    """
    def __init__(self, **kw):
        self.entries = []
        self.valuemap = {}
        self._descending = kw.get("descending", False)
        super(PrioritySet, self).__init__()
    def add(self, priority, value):
        if self.has_value(value):
            if priority == self.priority(value):
                return
            self.remove(value)
        self._insert(priority, value)
    def remove(self, value):
        index = self.index(value)
        self.entries.pop(index)
        self.valuemap.pop(value)
        return index
    def priority(self, value):
        """
            Get priority of existing entry by value.
        """
        if not self.has_value(value):
            raise ValueError("index(value) value not in sequence: %r" % value)
        return self.valuemap[value]
    def index(self, value):
        """
            Get the index of an existing entry based on its value.
        """
        priority = self.priority(value)
        return self._insertion_index(self._as_entry(priority, value)) - 1
    def clear(self):
        self.entries = []
        self.valuemap.clear()
    def values(self):
        return set(self.valuemap)
    def has_value(self, value):
        return value in self.valuemap
    def slice(self, start=0, stop=None, fromvalues=None, **kw):
        return list(self.iterslice(start, stop, fromvalues, **kw))
    def iterslice(self, start=0, stop=None, fromvalues=None, **kw):
        values = self
        if fromvalues is not None:
            if not isinstance(fromvalues, set):
                fromvalues = set(fromvalues)
            values = itertools.ifilter(fromvalues.__contains__, self)
        if kw.get("reverse", False):
            values = list(values)
            values.reverse()
        return itertools.islice(values, start, stop)
    def __contains__(self, value):
        return self.has_value(value)
    def __getitem__(self, index):
        return self.entries[index][1]
    def __getslice__(self, start, stop):
        return [entry[1] for entry in self.entries[start: stop]]
    def __len__(self):
        return len(self.entries)
    def _insert(self, priority, value):
        assert not self.has_value(value)
        entry = self._as_entry(priority, value)
        index = self._insertion_index(entry)
        self.entries.insert(index, entry)
        self.valuemap[value] = priority
        return index    
    def _insertion_index(self, entry):
        """
            Get the index at which an entry should be inserted.
        """
        return bisect.bisect_right(self.entries, entry)
    def _as_entry(self, priority, value):
        if self._descending:
            priority = -priority
        return (priority, value)
    def _get_descending(self):
        """
            Accessor for 'descending' attribute, 
            so that it can be managed as read-only.
        """
        return self._descending
    descending = property(_get_descending)

class QueryClient(set):
    def __init__(self):
        self.fields = ()
        self.values = []
        self.seen = set()
        self.itemmap = {}
        self.stop = -1
        self.start = -1
        self.query = None
        self.reversed = None
        self.query_to_time = None
        self.query_from_time = None
        self.created = self.touched = uptime.secs()
        super(QueryClient, self).__init__()
    def touch(self):
        self.touched = uptime.secs()
    def since_created(self):
        return uptime.secs() - self.created
    def since_touched(self):
        return uptime.secs() - self.touched
    def set_query(self, query, options=None):
        if query != self.query:
            self.query = query.copy()
            self.query_to_time = query.pop("toTime", None)
            self.query_from_time = query.pop("fromTime", None)
            self.fields = query.keys()
            self.values = map(query.get, self.fields)
            self.update(self.itemmap)
        elif options is not None:
            if options.get("reset", False):
                self.seen.clear()
        return
    def matches(self, item):
        if self.query_from_time is not None:
            if item["createdUTC"] < self.query_from_time:
                return False
        if self.query_to_time is not None:
            if item["createdUTC"] > self.query_to_time:
                return False
        return map(item.get, self.fields) == self.values
    def update(self, items):
        if not isinstance(items, dict):
            items = dict([(item["id"], item) for item in items])
        if self.query:
            for guid,item in items.items():
                if self.matches(item):
                    self.add(guid)
                else:
                    self.discard(guid)
        else:
            super(QueryClient, self).update(items)
        self.itemmap.update(items)
        self.seen.difference_update(items)
    def remove(self, item):
        guid = item["id"]
        self.discard(guid)
        self.seen.discard(guid)
        self.itemmap.pop(guid, None)
    def filtered(self, guids, start=0, stop=None, **kw):
        return list(self.iterfiltered(guids, start, stop, **kw))
    def iterfiltered(self, guids, start=0, stop=None, **kw):
        count = len(self)
        if start > count:
            return ()
        elif stop is not None:
            stop = min(stop, count)
        if self.query:
            guids = itertools.ifilter(self.__contains__, guids)
        reversed = kw.get("reverse", False)
        if reversed:
            guids = list(guids)
            guids.reverse()
        # May use later for caching query results.
        self.stop = stop
        self.start = start
        self.reversed = reversed
        return itertools.islice(guids, start, stop)
    def getitems(self, guids=None):
        if guids is None:
            guids = self
        items = []
        returned = set()
        for index,guid in enumerate(guids):
            values = {}
            if guid not in self.seen:
                values.update(self.itemmap[guid])
            items.append({"id": guid, "index": index, "values": values})
            returned.add(guid)
        self.seen = returned
        return items
    def __str__(self):
        count = len(self)
        total = len(self.itemmap)
        query = self.query or "None"
        typename = type(self).__name__
        return "%s(%s, %d of %d matches)" % (typename, query, count, total)
    def __repr__(self):
        return "<%s at %#x>" % (self, id(self))

def timed(function, timefunc=time.time):
    name = function.__name__
    message = "Took %0.3f seconds to invoke " + name + "()."
    def wrapper(*args, **kw):
        tstart = timefunc()
        result = function(*args, **kw)
        tstop = timefunc()
        if DEBUG:
            msglog.debug(message % (tstop - tstart))
        return result
    update_wrapper(wrapper, function)
    return wrapper

def uptimed(function):
    return timed(function, uptime.secs)

class EventStore(CompositeNode):
    def collection_factory():
        return PrioritySet(descending=True)
    collection_factory = staticmethod(collection_factory)
    def __init__(self):
        self.ttl = 60
        self.items = {}
        self.manager = None
        self.events = Queue()
        self.closed = deque()
        self._last_trimmed = 0
        self.synclock = Lock()
        self.subscription = None
        self.scheduled_startup = None
        self.clients = defaultdict(QueryClient)
        self.created = PrioritySet(descending=True)
        self.byname = defaultdict(self.collection_factory)
        self.bystate = defaultdict(self.collection_factory)
        self.byorigin = defaultdict(self.collection_factory)
        self.bypriority = defaultdict(self.collection_factory)
        self.collections = {"name": self.byname, 
                            "state": self.bystate,
                            "origin": self.byorigin, 
                            "priority": self.bypriority}
        super(EventStore, self).__init__()
    @timed
    def start(self):
        if self.is_running():
            self.stop()
        self.synclock.acquire()
        try:
            self.manager = as_node("/services/Alarm Manager")
            self.scheduled_startup = scheduler.after(0, self.check_startup)
        finally:
            self.synclock.release()
        return super(EventStore, self).start()
    @timed
    def stop(self):
        self.synclock.acquire()
        try:
            if self.scheduled_startup:
                self.scheduled_startup.cancel()
            self.scheduled_startup = None
            if self.subscription:
                try:
                    self.manager.dispatcher.unregister(self.subscription)
                except:
                    msglog.exception(prefix="handled")
            self.subscription = None
            self.clear()
            self.manager = None
        finally:
            self.synclock.release()
        return super(EventStore, self).stop()
    def check_startup(self):
        self.synclock.acquire()
        try:
            if self.manager.is_running():
                self.scheduled_startup = None
                NORMAL.queue_noresult(self._initialize)
            else:
                self.scheduled_startup = scheduler.after(5,self.check_startup)
        finally:
            self.synclock.release()
    @timed
    def _initialize(self):
        self.synclock.acquire()
        try:
            self.subscription = self.manager.register_for_type(
                self.handle_event, StateEvent, None, True)
            events = self.manager.get_all_events()
            eventitems = [(event,event.asitem()) for event in events]
            self._handle_event_items(eventitems)
        finally:
            self.synclock.release()
    def since_trimmed(self):
        return uptime.secs() - self._last_trimmed
    @timed
    def trim_expired(self):
        count = 0
        self.synclock.acquire()
        try: 
            count += len(self._trim_clients())
            count += len(self._trim_events())
            self._last_trimmed = uptime.secs()
        finally:
            self.synclock.release()
        return count
    @timed
    def _trim_clients(self):
        trimmed = []
        for cid,client in self.clients.items():
            if client.since_touched() > self.ttl:
                self.clients.pop(cid)
                trimmed.append(cid)
                print "Cleaned client %r: %s" % (cid, client)
        return trimmed
    @timed
    def _trim_events(self):
        trimmed = []
        expiration = uptime.secs() - self.ttl
        while self.closed and self.closed[0][0] < expiration:
            closed,guid = self.closed.popleft()
            try:
                item = self.items.pop(guid)
            except KeyError:
                msglog.warn("Failed to remove closed event.  Error follows: ")
                msglog.exception(prefix="handled")
            else:
                self.created.remove(guid)
                self.byname[item["name"]].remove(guid)
                self.bystate[item["state"]].remove(guid)
                self.byorigin[item["origin"]].remove(guid)
                self.bypriority[item["priority"]].remove(guid)
                for client in self.clients.values():
                    client.remove(item)
                trimmed.append(guid)
        return trimmed
    def clear(self):
        self.byname.clear()
        self.bystate.clear()
        self.byorigin.clear()
        self.bypriority.clear()
        self.created.clear()
        self.clients.clear()
        self.items.clear()
    @timed
    def handle_event(self, event):
        if self.since_trimmed() >= self.ttl:
            self.trim_expired()
        if isinstance(event, StateEvent):
            event = event.source
        item = event.asitem()
        self.synclock.acquire()
        try:
            self._handle_event_items([(event,item)])
        finally:
            self.synclock.release()
    @timed
    def _handle_event_items(self, eventitems):
        items = {}
        curtime = uptime.secs()
        for event,item in eventitems:
            guid = event.GUID
            timestamp = event.created()
            self.created.add(timestamp, guid)
            self.byname[item["name"]].add(timestamp, guid)
            self.bystate[item["state"]].add(timestamp, guid)
            self.byorigin[item["origin"]].add(timestamp, guid)
            self.bypriority[item["priority"]].add(timestamp, guid)
            newstate = item["state"]
            if guid in self.items:
                oldstate = self.items[guid]["state"]
                if oldstate != newstate: 
                    self.bystate[oldstate].remove(guid)
                    if newstate == "CLOSED":
                        self.closed.append((curtime,guid))
            elif newstate == "CLOSED":
                self.closed.append((curtime,guid))
            items[guid] = item
            self.items[guid] = item
        for client in self.clients.values():
            client.update(items)
    def client(self, cid, touch=True):
        self.synclock.acquire()
        try:
            if cid not in self.clients:
                self.clients[cid].update(self.items)
            client = self.clients[cid]
        finally:
            self.synclock.release()
        if touch:
            client.touch()
        if self.since_trimmed() >= self.ttl:
            self.trim_expired()
        return client
    @timed
    def fetch(self, params=(), **kwargs):
        response = {}
        params = dict(params)
        params.update(kwargs)
        query = params.get("query")
        start = params.get("start", 0)
        options = params.get("queryOptions")
        count = params.get("count", len(self.items) - start)
        stop = start + count
        if "clientId" in params:
            cid = params.get("clientId")
        else:
            cid = str(UUID())
        if "sort" in params:
            sort = params["sort"]
        else:
            sort = [{"attribute": "createdUTC", "descending": True}]
        if len(sort) != 1:
            raise ValueError("single-attribute sorting only, not: %r" % sort)
        attribute = sort[0]["attribute"]
        descending = sort[0].get("descending", False)
        client = self.client(cid)
        client.set_query(query, options)
        if attribute == "created" or attribute == "createdUTC":
            reverse = not descending
            collection = self.created
            guids = client.filtered(collection, start, stop, reverse=reverse)
        else:
            if DEBUG:
                msglog.debug("Event Store client fetching by: %r" % attribute)
            if attribute not in self.collections:
                raise ValueError("sort attribute unknown: %r" % attribute)
            guids = []
            collection = self.collections[attribute]
            for key in sorted(collection.keys(), reverse=descending):
                remaining = stop - len(guids)
                if remaining <= 0:
                    break
                guids.extend(client.filtered(collection[key], 0, remaining))
            guids = guids[start: stop]
        items = client.getitems(guids)
        response["clientId"] = cid
        response["start"] = start
        response["items"] = items
        response["count"] = len(items)
        response["total"] = len(client)
        return response

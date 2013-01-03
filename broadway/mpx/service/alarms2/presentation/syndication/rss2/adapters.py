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
# Refactor 2/11/2007
import time
import urllib
from feed import rss
from feed import tools
from threading import Lock
from moab.linux.lib import uptime
from mpx.componentry import adapts
from mpx.componentry import implements
from mpx.componentry import register_adapter
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2Document
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2RssElement
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2ItemElement
from mpx.www.w3c.syndication.rss2.interfaces import IRSS2ChannelElement
from mpx.service.cloud.manager import FormationUpdated
from mpx.service.alarms2.interfaces import IAlarmManager
from mpx.service.alarms2.interfaces import IAlarmEvent
from mpx.service.alarms2.interfaces import IStateEvent
from mpx.service.alarms2.interfaces import IAlarm
from mpx.service.alarms2.alarmevent import AlarmEvent
from mpx.service.alarms2.alarmevent import StateEvent
from mpx.service.alarms2.alarm import Alarm
from mpx.lib.eventdispatch import Event
from utilities import ItemCache
from utilities import SimpleQueue
from utilities import EventQueue

class RSS2AlarmManager(object):
    implements(IRSS2Document)
    adapts(IAlarmManager)
    def __new__(klass, manager):
        syndicator_name = '__' + klass.__name__
        syndicator = getattr(manager, syndicator_name, None)
        if syndicator is None:
            print 'Creating new RSS2AlarmManager'
            syndicator = super(RSS2AlarmManager, klass).__new__(klass)
            setattr(manager, syndicator_name, syndicator)
            syndicator.initialize(manager)
        return syndicator
    def initialize(self, manager):
        self.debug = 0
        self.manager = manager
        self.cache_lock = Lock()
        self.cache_ttl = 30
        self.closed_event_ttl = 3 * 60
        self.caches = {}
        self.close_events = {}
        self.event_queue = EventQueue()
        self.hostname = AlarmEvent.LOCALORIGIN
        self.uri_base = 'http://' + self.hostname
        if self.uri_base[-1] == '/':
            self.uri_base = self.uri_base[0:-1]
        self.categories = {
            'RAISED': rss.Category("Raised"),
            'INACTIVE': rss.Category("Inactive"),
            'ACCEPTED': rss.Category("Accepted"),
            'CLEARED': rss.Category("Cleared"),
            'CLOSED': rss.Category("Closed")
        }
        self.last_pub_time = None
        self.updatesub = self.manager.register_for_type(
            self.initialize_caches, FormationUpdated)
        self.subscription = self.manager.register_for_type(
            self.handle_alarm_update, StateEvent, None, True)
        self.initialize_caches()
    def initialize_caches(self, *args):
        if self.debug: tstart = time.time()
        print 'RSS2 Syndic initializing caches because: %s' % (args,)
        events = []
        self.cache_lock.acquire()
        try:
            self.event_queue.popqueue()
            for group in map(Alarm.get_events, self.manager.get_alarms()):
                events.extend(group)
            events.extend(self.manager.get_remote_events())
            events.extend(self.event_queue.popqueue())
            self.caches = {None: ItemCache()}
            cache = self.process_events(events)
        finally:
            self.cache_lock.release()
        if self.debug:
            tend = time.time()
            tlapse = tend - tstart
            print 'RSS2 cache init of %s events took %s seconds.' % (len(events), tlapse)
        return cache
    def process_events(self, events):
        if not self.cache_lock.locked():
            raise Exception('Process events cannot be called unless locked.')
        cache = {}
        if events: 
            guids = map(Event.get_guid, events)
            items = map(self.item_from_event, events)
            cache.update(zip(guids, items))
            for existing in self.caches.values():
                existing.update(cache)
        return cache
    def handle_alarm_update(self, event):
        if self.debug: 
            tstart = time.time()
        if isinstance(event, StateEvent):
            event = event.source
        if event.is_state('closed'):
            self.close_events[event.GUID] = uptime.secs()
        self.event_queue.enqueue(event)
        if self.cache_lock.acquire(0):
            try:
                self.trim_expired_caches()
                self.process_events(self.event_queue.popqueue())
            finally: 
                self.cache_lock.release()
        else: 
            print 'Alarm update not processing queue; locked.'
        if self.debug:
            tend = time.time()
            tlapse = tend - tstart
            print 'Took RSS2 Syndic %s secs to handle alarm event.' % tlapse
        return
    def render(self, request_path = None, cache_id = None):
        if request_path is None:
            request_path = '/syndication'
        xmldoc = self.setup_xmldoc()
        channel = self.setup_channel(request_path)
        xmldoc.root_element.channel = channel
        self.cache_lock.acquire()
        try:
            self.trim_expired_caches()
            queue = self.event_queue.popqueue()
            if queue: 
                self.process_events(queue)
        finally: 
            self.cache_lock.release()
        items = self.get_items(cache_id)
        map(channel.items.append, items)
        return str(xmldoc)
    def setup_xmldoc(self):
        xmldoc = rss.XMLDoc()
        xmldoc.root_element = rss.RSS()
        return xmldoc
    def setup_channel(self, request_path):
        publish_time = time.time()
        channel = rss.Channel()
        channel.title = rss.Title("Network Building Mediator Alarms")
        if request_path[0] != '/':
            request_path = '/' + request_path
        url = self.uri_base + request_path
        channel.link = rss.Link(url)
        channel.description = rss.Description("RSS 2.0 feed of Network "
                                              "Building Mediator alarms.")
        if self.last_pub_time is not None:
            channel.last_build_date = rss.LastBuildDate(self.last_pub_time)
        self.last_pub_time = publish_time
        channel.generator = rss.Generator("Network Building "
                                          "Mediator Alarm Syndication")
        channel.docs = rss.Docs('http://blogs.law.harvard.edu/tech/rss')
        return channel
    def get_items(self, cid):
        """
            Get Alarm Event Items that have not been returned to 
            client with ID "cid".  If client ID is None, return all.
        """
        count = None
        if cid:
            count = 250
            if cid not in self.caches:
                self.caches[cid] = ItemCache(self.caches[None])
        cache = self.caches[cid]
        return cache.read(count)
    def trim_expired_caches(self):
        if not self.cache_lock.locked():
            raise Exception('Must be locked to trim caches.')
        removed = []
        now = uptime.secs()
        allitems = self.caches[None]
        for guid,closed in self.close_events.items():
            if (now - closed) > self.closed_event_ttl:
                if guid in allitems:
                    del(allitems[guid])
                del(self.close_events[guid])
        for cid,cache in self.caches.items():
            if cid and (cache.since_touched() > self.cache_ttl):
                del(self.caches[cid])
                removed.append(cid)
        if self.debug and removed:
            print 'Cache trim trimmed the following IDs: %s.' % (removed,)
        return removed
    def item_from_event(self, event):
        if isinstance(event, StateEvent):
            event = event.source
        return IRSS2ItemElement(event).as_item()

class RSS2AlarmEventItem(object):
    implements(IRSS2ItemElement)
    adapts(IAlarmEvent)
    def __init__(self, alarmevent):
        self.alarmevent = alarmevent
        super(RSS2AlarmEventItem, self).__init__()
    def as_item(self):
        event = self.alarmevent
        item = rss.Item()
        alarm = event.source
        priority = alarm.priority
        if not priority: 
            priority = 'Normal'
        title = "%s (%s): %s" % (alarm.name, priority, event.state.upper())
        link = "http://%s/syndication?guid=%s" % (event.origin, event.GUID)
        item.title = rss.Title(title)
        item.link = rss.Link(link)
        item.guid = rss.Guid(event.GUID)
        item.pub_date = rss.PubDate(event.created())
        description = alarm.description
        for change in event.get_audit():
            description += '<br />\n%s.  ' % change.tostring()
        item.description = rss.Description(tools.escape_html(description))
        item.source = rss.Source(event.origin, 
                                 "http://%s/syndication" % event.origin)
        eventcategory = rss.Category('Event')
        alarmcategory = rss.Category('Alarm')
        item.categories.append(eventcategory)
        item.categories.append(alarmcategory)
        return item
    def render(self):
        return str(self.as_item())

register_adapter(RSS2AlarmManager)
register_adapter(RSS2AlarmEventItem)

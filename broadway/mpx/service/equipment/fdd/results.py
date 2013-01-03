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
import time
import string
import calendar
import feedparser
from threading import Event
from threading import Thread
from mpx.lib import msglog
from mpx.lib.thread_pool import NORMAL
from mpx.lib.scheduler import scheduler
from mpx.lib.neode.node import CompositeNode
from mpx.service.equipment.fdd.interim import FaultEvent

def _which_fault(name):
    if name.count('Damper Fault'):
        return 0
    if name.count('Economizer Fault'):
        return 1
    if name.count('Static Alarm'):
        return 2
    raise TypeError('Unknown type', name)

class SyndicationConsumer(CompositeNode):
    def __init__(self, *args):
        self.events = []
        self.timeout = 45
        self.period = 60
        self._running = Event()
        self.faults = [None, None, None]
        self.priority = 'Fault'
        self.target_url = 'http://www.sensuseye.com/admin/RSS/Location.aspx?location_id=38'
        super(SyndicationConsumer, self).__init__(*args)
    def refresh_feed(self):
        try: 
            self._refresh_feed()
        finally:
            self.reschedule()
    def _refresh_feed(self, document = None):
        if document is None:
            document = feedparser.parse(self.target_url)
        items = document.entries[:]
        items.reverse() # oldes first.
        for item in items:
            titledata = item.title
            descriptionstart = 0
            descriptionend = titledata.rfind(' - ')
            namestart = descriptionend + len(' - ')
            nameend = titledata.find(': ', namestart)
            statestart = nameend + len(': ')
            stateend = len(titledata)
            description = titledata[descriptionstart:descriptionend]
            faultname = titledata[namestart:nameend]
            faultstate = titledata[statestart:stateend]
            guidlink = item.get('guid')
            guid = guidlink[guidlink.rfind('/') + 1:]
            # item.updated_parsed is 9-tuple as returned by time.gtime()
            timestamp = float(calendar.timegm(item.updated_parsed))
            detail = item.description
            origin = item.get('link')
            if not origin:
                origin = self.target_url
            faultindex = _which_fault(faultname)
            existing = self.faults[faultindex]
            print "Handling %s GUID %s state %s" % (faultname, guid, faultstate)
            fault = None
            if existing:
                print 'Existing fault %s: %s' % (existing.title, existing.state)
                if faultstate == 'Normal':
                    print 'New fault state is Normal'
                    if existing.GUID == guid:
                        print 'GUID matches existing.'
                        message = 'Fault %s returning to Normal from %s'
                        print message % (existing.title, existing.state)
                        existing.set_state('Normal', timestamp, detail)
                        self.faults[faultindex] = None
                        continue
                    else:
                        print 'GUID does not match existing.' 
                        print 'Ingoring %s return to Normal' % existing.title
                        print '\tExisting fault in state %s' % existing.state
                        existingupdated = time.ctime(existing.timestamp)
                        currentupdated = time.ctime(timestamp)
                        print '\tExisting last updated at %s' % existingupdated
                        print '\tCurent entry updated at %s' % currentupdated
                        continue
                elif existing.GUID != guid:
                    print 'Faultstate not normal and GUID not matching: %s %s' % (faultstate, guid)
                    message = 'Warning: New %s implies closure of existing.'
                    print message % (existing.title)
                    print '\tExisting fault state is %s.' % existing.state
                    print '\tNew fault state is %s' % faultstate
                    print '\tNew fault RSS item is:'
                    print print_feed_item(item)
                    print '\tClosing existing to allow new life-cycle.'
                    existing.set_state('Normal', timestamp, 
                                       'Implicitly closed because new event.')
                    self.faults[faultindex] = None
                else:
                    print 'Non-normal with matching GUID.' 
                    fault = self.faults[faultindex]
                    self.faults[faultindex] = None
            elif faultstate == 'Normal':
                print 'Ingoring %s return to Normal' % faultname
                print '\tNo open faults of that type.'
                continue
            if fault is None:
                try:
                    fault = FaultEvent.get_event(guid)
                except KeyError:
                    fault = FaultEvent(self, faultname, timestamp, 
                                       description, origin, guid)
                else:
                    print 'Fault %s existed unknown.' % fault
            self.faults[faultindex] = fault
            fault.set_state(faultstate, timestamp, detail)
    def start_auto(self, period = 60):
        self.period = period
        running = self._running.isSet()
        self._running.set()
        if not running:
            self.reschedule(0)
    def stop_auto(self):
        self._running.clear()
        next = self._next_run
        self._next_run = None
        if next: next.cancel
    def reschedule(self, period = None):
        if period is None:
            period = self.period
        if self._running.isSet():
            self._next_run = scheduler.after(period, self._queue_refresh)
    def _queue_refresh(self):
        self._next_run = None
        NORMAL.queue_noresult(self.refresh_feed)


def print_feed_item(item):
    names = item.keys()
    names.sort()
    for name in names:
        data = str(item[name])
        data = data or repr(data)
        print name
        while data:
            print ' ' * 5 + data[0:60]
            data = data[60:]
    return


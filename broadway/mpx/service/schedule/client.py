"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
import time, copy
from schedule import ScheduleData
from mpx.lib import msglog
from mpx.lib.threading import Lock
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute,get_attribute
from mpx.lib.exceptions import ENotImplemented
from mpx.lib.exceptions import EInvalidValue
from mpx.lib.datetime import *
from mpx.lib.event import EventConsumerMixin,\
     ChangeOfValueEvent,ScheduleChangedEvent,EventConsumerMixin

class Client(CompositeNode,EventConsumerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventConsumerMixin.__init__(self,self._handle_event,
                                    self._handle_exception)
    def start(self):
        self.parent.event_subscribe(self,ChangeOfValueEvent)
        self.parent.event_subscribe(self,ScheduleChangedEvent)
        CompositeNode.start(self)
    def stop(self):
        self.parent.event_unsubscribe(self,ChangeOfValueEvent)
        self.parent.event_unsubscribe(self,ScheduleChangedEvent)
        CompositeNode.stop(self)
    def configure(self,config):
        set_attribute(self,'description','',config)
        CompositeNode.configure(self,config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self,'description',config)
        return config
    def _handle_event(self,event):
        if isinstance(event,ChangeOfValueEvent):
            self._value_changed(event,event.old_value,event.value)
        elif isinstance(event,ScheduleChangedEvent):
            self._schedule_changed(event,event.new_schedule)
    def _handle_exception(self,exc):
        msglog.exception()
    def _value_changed(self,event,old,new):
        pass
    def _schedule_changed(self,event,schedule):
        pass
##
# @note Lock may be overkill here.
class VistaClient(Client):
    def __init__(self):
        self._lock = Lock()
        self._update = 0
        self._schedule_data = None
        self._schedule = None
        Client.__init__(self)
    def configure(self,config):
        Client.configure(self,config)
    def configuration(self):
        config = Client.configuration(self)
        return config
    def start(self):
        Client.start(self)
    def stop(self):
        Client.stop(self)
    def _update_schedule(self):
        schedule_data = self._schedule_data
        if schedule_data is None:
            self._schedule = None
            return
        default = {}
        weekly = schedule_data.weekly()
        days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        day_count = 0
        for day_list in weekly:
            actions = []
            for time_value in day_list.time_values:
                time_int = int(time_value.time)
                actions.append({'action':time_value.value,
                                'hour':time_int / 3600,
                                'minute':(time_int % 3600) / 60})
            default[days[day_count]] = actions
            day_count += 1
        exceptions = []
        special_events = schedule_data.special_events()
        for event in special_events:
            actions = []
            for time_value in event.time_values:
                time_int = int(time_value.time)
                actions.append({'action':time_value.value,
                                'hour':time_int / 3600,
                                'minute':(time_int % 3600) / 60})
            dates = []
            for calendar_entry in event.period.calendar_entries:
                if calendar_entry.type == 0:
                    # calendar_entry.days is Date obj.
                    date = calendar_entry.days
                    year = date.value[0]
                    month = date.value[1]
                    day = date.value[2]
                    dates.append(({'year':year,'month':month,'day':day},
                                  {'year':year,'month':month,'day':day}))
                elif calendar_entry.type == 1:
                    # calendar_entry.days is DateRange
                    start = calendar_entry.days.start_date
                    year = start.value[0]
                    month = start.value[1]
                    day = start.value[2]
                    start = {'year':year,'month':month,'day':day}
                    end = calendar_entry.days.end_date
                    year = end.value[0]
                    month = end.value[1]
                    day = end.value[2]
                    end = {'year':year,'month':month,'day':day}
                    dates.append((start,end))
                elif calendar_entry.type == 2:
                    raise EInvalidValue('type',calendar_entry.type,
                                        'Do not support WeekNday.')
                else:
                    raise EInvalidValue('type',calendar_entry.type,
                                        'Unrecognized CalendarEntry type.')
            for start,end in dates:
                exceptions.append({'name':event.name,
                                   'start_date':start,
                                   'end_date':end,
                                   'events':actions})
        self._schedule = {'default':default,'exceptions':exceptions}
    def _update_schedule_data(self):
        s = self.parent.get_schedule()
        sd = None
        if s is None:
            sd = ScheduleData()
        else:
            sd = ScheduleData(s._name, self.description, None, s._effective)
        sd._weekly = []
        default = self._schedule['default']
        days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        for i in range(0,len(days)):
            day_list = default[days[i]]
            time_values = []
            for event in day_list:
                value = event['action']
                hour = event['hour']
                minute = event['minute']
                time_of_day = TimeOfDay('%s:%s' % (hour,minute))
                time_values.append(TimeValue(time_of_day,value))
            sd._weekly.append(DailySchedule(time_values))
        sd._special_events = []
        exceptions = self._schedule['exceptions']
        for exception in exceptions:
            name = exception['name']
            year = exception['start_date']['year']
            month = exception['start_date']['month']
            day = exception['start_date']['day']
            start = Date((year,month,day,))
            year = exception['end_date']['year']
            month = exception['end_date']['month']
            day = exception['end_date']['day']
            end = Date((year,month,day,))
            date_range = DateRange(start,end)
            entry = CalendarEntry(1,date_range)
            time_values = []
            for event in exception['events']:
                value = event['action']
                hour = event['hour']
                minute = event['minute']
                time_of_day = TimeOfDay('%s:%s' % (hour,minute))
                time_values.append(TimeValue(time_of_day,value))
            sd._special_events.append(SpecialEvent(name,Calendar([entry]),
                                               time_values=time_values))
        self._schedule_data = sd
    def _schedule_changed(self,event,schedule):
        if event.source is self:
            # Prevents double lock and unecessary work.
            return
        self._lock.acquire()
        try:
            self._schedule_data = schedule
            self._update = 1
        finally:
            self._lock.release()
    def get(self, skipCache=0):
        self._lock.acquire()
        try:
            if isinstance(self._schedule_data,Exception):
                raise self._schedule_data
            if self._update:
                self._update_schedule()
            self._update = 0
            schedule = self._schedule
        finally:
            self._lock.release()
        return schedule
    def set(self,schedule):
        self._lock.acquire()
        try:
            self._schedule = schedule
            self._update_schedule_data()
            self.parent.set_schedule(self,self._schedule_data)
            self._update = 0
        finally:
            self._lock.release()
    def schedule_name(self):
        return self._schedule_data.name()

##default = {'default':{'Mon':[{'action':1,'hour':8},
##                             {'action':0,'hour':17}],
##                      'Tue':[{'action':1,'hour':8},
##                             {'action':0,'hour':17}],
##                      'Wed':[{'action':1,'hour':8},
##                             {'action':0,'hour':17}],
##                      'Thu':[{'action':1,'hour':8},
##                             {'action':0,'hour':17}],
##                      'Fri':[{'action':1,'hour':8},
##                             {'action':0,'hour':17}],
##                      'Sat':[{'action':1,'hour':9},
##                             {'action':0,'hour':15}],
##                      'Sun':[{'action':0,'hour':0}]},
##           'exceptions':[{'name':'holiday',
##                          'events':[{'action':0,'hour':0}],
##                          'date':{'year':2003,'month':11,'day':23}},
##                         {'name':'short day',
##                          'events':[{'action':1,'hour':9},
##                                    {'action':0,'hour':15}],
##                          'date':{'year':2004,'month':1,'day':1}}]}


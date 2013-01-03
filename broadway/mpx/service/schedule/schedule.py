"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx.lib import msglog,datetime
from mpx.lib.configure import set_attribute,get_attribute,REQUIRED
from mpx.lib.node import CompositeNode
from mpx.lib.uuid import UUID
from mpx.lib.threading import Condition,Lock
from mpx.lib.event import EventProducerMixin
from mpx.lib.event import ScheduleChangedEvent
from mpx.lib.event import ChangeOfValueEvent
from mpx.lib.exceptions import ENotImplemented

##
# @todo We are doing a lot here to keep threads from modifying 
#       data members and screwing us, or each other, up.  We are
#       currently checking several things to prevent conflicts 
#       while avoiding the dreaded deepcopy, however, threads 
#       can still screw up each other by hanging on to references 
#       to objects while losing a reference to copy, and then 
#       modifying the object directly.
class ScheduleData:
    def __init__(self,name=None,description=None,weekly=None, \
                 effective=None,special_events=None,id=None):
        if name is None:
            name = ''
        self._name = name
        if description is None:
            description = ''
        self._description = description
        if not weekly:
            weekly = []
            for i in range(0,7):
                weekly.append(datetime.DailySchedule())
        self._weekly = weekly
        if effective is None:
            effective = datetime.DateRange(None,None)
        self._effective = effective
        if not special_events:
            special_events = []
        self._special_events = special_events
        if id is None:
            id = UUID()
        self._id = id
    def name(self):
        return self._name
    def description(self):
        return self._description
    def id(self):
        return self._id
    def weekly(self):
        return self._weekly
    def effective(self):
        return self._effective
    def special_events(self):
        return self._special_events
    def as_list(self):
        rtn_lst = [self._name, self._description,[],self._effective.as_list(),[],self._id]
        for ds in self._weekly:
            rtn_lst[2].append(ds.as_list())
        for se in self._special_events:
            rtn_lst[4].append(se.as_list())
        return rtn_lst
    def from_list(self, sd_lst):
        self._name = sd_lst[0]
        self._description = sd_lst[1]
        self._weekly = []
        for ds_lst in sd_lst[2]:
            ds = datetime.DailySchedule()
            ds.from_list(ds_lst)
            self._weekly.append(ds)
        self._effective.from_list(sd_lst[3])
        self._special_events = []
        for se_lst in sd_lst[4]:
            se = datetime.SpecialEvent()
            se.from_list(se_lst)
            self._special_events.append(se)
        self._id = sd_lst[5]
class Schedule(CompositeNode,EventProducerMixin):
    def __init__(self):
        CompositeNode.__init__(self)
        EventProducerMixin.__init__(self)
        self._schedule_lock = Lock()
        self._schedule_condition = Condition()
        self._value_lock = Lock()
        self._value_condition = Condition()
        self.__schedule = None
        self.__value = None
    def configure(self,config):
        CompositeNode.configure(self,config)
    def configuration(self):
        config = CompositeNode.configuration(self)
        return config
    def start(self):
        CompositeNode.start(self)
    def stop(self):
        CompositeNode.stop(self)
    def set_schedule(self,client,schedule):
        self._schedule_lock.acquire()
        self._schedule_condition.acquire()
        try:
            self.__schedule = schedule
            self._schedule_condition.notifyAll()
        finally:
            self._schedule_lock.release()
            self._schedule_condition.release()
        self.event_generate(ScheduleChangedEvent(client,schedule))
    def get_schedule(self):
        self._schedule_lock.acquire()
        try:
            schedule = self.__schedule
        finally:
            self._schedule_lock.release()
        if isinstance(schedule,Exception):
            raise schedule
        return schedule
    ##
    # @param schedule Schedule client believes to be current.
    def get_next_schedule(self,schedule,timeout=None):
        self._schedule_lock.acquire()
        try:
            if schedule is not self.__schedule:
                return self.__schedule
            self._schedule_condition.acquire()
        finally:
            self._schedule_lock.release()
        try:
            self._schedule_condition.wait(timeout)
            schedule = self.__schedule
        finally:
            self._schedule_condition.release()
        if isinstance(schedule,Exception):
            raise schedule
        return schedule
    def is_schedule_current(self,schedule):
        self._schedule_lock.acquire()
        try:
            changed = not schedule is self.__schedule
        finally:
            self._schedule_lock.release()
        return changed
    def _set(self,value):
        self._value_lock.acquire()
        self._value_condition.acquire()
        try:
            old = self.__value
            self.__value = value
            self._value_condition.notifyAll()
        finally:
            self._value_lock.release()
            self._value_condition.release()
        if old != value:
            self.event_generate(ChangeOfValueEvent(self,old,value))
    def get(self, skipCache=0):
        self._value_lock.acquire()
        try:
            value = self.__value
        finally:
            self._value_lock.release()
        return value
    def get_next_value(self,value,timeout=None):
        self._value_lock.acquire()
        try:
            if value != self.__value:
                return self.__value
            self._value_condition.acquire()
        finally:
            self._value_lock.release()
        try:
            self._value_condition.wait(timeout)
            value = self.__value
        finally:
            self._value_condition.release()
        return value
    def is_value_current(self,value):
        self._value_lock.acquire()
        try:
            changed = not value == self.__value
        finally:
            self._value_lock.release()
        return changed


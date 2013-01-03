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
"""
trane_sched_client.py
"""

import types, copy
from mpx.lib import EnumeratedValue
from mpx.lib.exceptions import EInvalidValue, ENoSuchName
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import CompositeNode, as_node, as_internal_node, as_node_url
from mpx.lib.event import ScheduleChangedEvent, EventConsumerMixin
from mpx.service.schedule import client, schedule
from mpx.lib import msglog
import mpx.ion.bacnet.trane.object
from mpx.lib.bacnet.trane.datatype import SummitTimeEventValue_seq, SummitSpecialEvent_seq
from mpx.lib.threading import Thread, Lock, RLock
from mpx.lib.scheduler import _Schedule as TimerSched
from mpx.lib.bacnet.property import BACnetPropertyObjectName
from mpx.lib.bacnet.trane.property import BACnetPropertyEffectivePeriod
from mpx.lib.bacnet.datatype import BACnetCharacterString
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER

# For Subscription Mgmt:
import time
#from mpx.service.subscription_manager import _manager
#from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER as sm # singleton ref
from mpx.service.schedule.schedule import ScheduleData
from mpx.lib import datetime

def get_signature_t(t_exception):
   t_start = t_exception.date_valid.start_date
   t_end = t_exception.date_valid.end_date
   i_start = datetime.Date([t_start.year, t_start.month, t_start.day])
   i_end = datetime.Date([t_end.year, t_end.month, t_end.day])
   date_range = datetime.DateRange(i_start, i_end)
   sig = [tuple(eval(str(date_range)))]
   for stev_seq in t_exception.event_list:
      v = stev_seq.event_type.value
      v %= 2 # convert Trane "Normal Stop" (2) to Ideal "Off" (0); lv "Normal Start" (1) same as Ideal "On" (1)
      sig.extend([stev_seq.time.hour, stev_seq.time.minute, stev_seq.time.second, v])
   sig = tuple(sig)
   return sig
      
def get_signature_i(i_exception):
   assert i_exception.period.calendar_entries[0].type == 1
   date_range = i_exception.period.calendar_entries[0].days
   sig = [tuple(eval(str(date_range)))]
   for tv in i_exception.time_values:
      time = tv.time.get_time_tuple()
      sig.extend([time[3], time[4], time[5], tv.value])
   sig = tuple(sig)
   return sig
      
def t2i_none(value, sched_client):
   return value

def t2i_name(t_value, sched_client):
   if not isinstance(t_value, BACnetPropertyObjectName):
      return t_value.__class__.__name__ # probably an instance of an error class...
   return t_value.data.value # Python str

# Methods and Class PropConverter below: convert between Trane and Ideal Schedule types:
# @param trane_weekly_inst input param; BACnetPropertyWeeklySchedule
#    Day-number formats:
#        Trane:     0 = Sunday, 6 = Saturday
#        EnvIdeal:  0 = Monday, 6 = Sunday
#        BACnet:    1 = Sunday, 7 = Saturday
def t2i_weekly(trane_weekly_inst, sched_client):
   trane_weekly_list = trane_weekly_inst.value
   ideal_weekly = []
   for day_list in trane_weekly_list:
      daily_sched = datetime.DailySchedule()
      for stev_seq in day_list:
         stev_list = stev_seq.value
         cur_stev = stev_list[0].value # time is first elem (3-tuple) in list that reps stev
         tt = [0,0,0,cur_stev[0],cur_stev[1],cur_stev[2],0,0,0] # make time 9-tuple
         time = datetime.TimeOfDay(tt)
         value = stev_list[1].value % 2 # (Normal Start = 1) -> "1"; (Normal Stop = 2) -> "0"
         #value = (stev_list[1] == 'Normal Start') # (Normal Start = 1) -> "1"; (all others) -> "0"
         tv = datetime.TimeValue(time, value)
         daily_sched.time_values.append(tv)
      ideal_weekly.append(daily_sched)
   # Rearrange given Trane day-number format into EnvIdeal day-number format:
   sunday = ideal_weekly.pop(0)
   ideal_weekly.append(sunday)
   return ideal_weekly # an array of DailySchedule instances

def t2i_exceptions(trane_excs, sched_client):
   t_spec_evt_list = trane_excs.value
   i_excs = []
   i_excs_names = {} # used to filter duplicate events, as det'd by signature
   for t_spec_evt in t_spec_evt_list:
      name = 'Unknown'
      calendar = None
      if t_spec_evt.calendar_period is None:
         if t_spec_evt.date_valid is None:
            raise EInvalidValue('calendar_period AND date_valid', None, \
                                'Only one of the two values (calendar_period, \
                                date_valid) may be None (ie OPTIONAL).')
         sig = get_signature_t(t_spec_evt)
         name = sched_client.get_exception_name(sig)
         if i_excs_names.has_key(name):
            continue # ONLY ONE EVENT WITH A GIVEN SIGNATURE IS ALLOWED IN A GIVEN SCHEDULE
         i_excs_names[name] = 0 # just want fast determination if we've seen this event already
         t_start = t_spec_evt.date_valid.start_date
         t_end = t_spec_evt.date_valid.end_date
         i_start = datetime.Date([t_start.year, t_start.month, t_start.day])
         i_end = datetime.Date([t_end.year, t_end.month, t_end.day])
         date_range = datetime.DateRange(i_start, i_end)
         calendar_entry = datetime.CalendarEntry(1, date_range) # "1": 2nd param is datetime.DateRange
         calendar = datetime.Calendar([calendar_entry])
      else:
         #@FIXME: Need to support SummitObjectRefs to standalone BCU Calendar objects,
         # as well as the conversion of the Summit Calendar data to datetime.Calendar data.
         # ALSO need to implement efficient use of single instances of datetime.Calendar
         # objects by multiple datetime.SpecialEvent objects (via refs). AND we need to
         # generate unique hash for use as key in _exc_dates_to_name map:
         #calendar = t_spec_evt.calendar_period # ???
         raise EInvalidValue('calendar_period', t_spec_evt.calendar_period, \
                             'SummitObjectRefs to standalone BCU '\
                             'Calendar objects are not yet supported.')
      i_time_vals = []
      for stev_seq in t_spec_evt.event_list:
         t_time_list = [0,0,0,stev_seq.time.hour,stev_seq.time.minute,stev_seq.time.second,0,0,0]
         i_time = datetime.TimeOfDay(t_time_list)
         i_val = stev_seq.event_type.value % 2 # (Normal Start = 1) -> "1"; (Normal Stop = 2) -> "0"
         #value = (stev_list[1] == 'Normal Start') # (Normal Start = 1) -> "1"; (all others) -> "0"
         i_time_val = datetime.TimeValue(i_time, i_val)
         i_time_vals.append(i_time_val)
      i_spec_evt = datetime.SpecialEvent(name, calendar, i_time_vals)
      i_excs.append(i_spec_evt)
   return i_excs

# @param trane_eff input param; BACnetPropertyEffectivePeriod (owns instance of BACnetDateRange)
def t2i_effective(trane_eff, sched_client):
   if trane_eff.__class__ is not BACnetPropertyEffectivePeriod:
      return datetime.DateRange(datetime.Date((None, None, None,)), datetime.Date((None, None, None,)))
   rng_val = trane_eff.data.value
   i_start_date = datetime.Date(rng_val[0]) # pass in 3tuple
   i_end_date = datetime.Date(rng_val[1]) # pass in 3tuple
   ideal_eff = datetime.DateRange(i_start_date, i_end_date)
   return ideal_eff

def t2i_member_list(trane_member_list, sched_client):
   ideal_member_list = [] # no explicit member list supported by ideal Schedule class
   return ideal_member_list

def i2t_none(value, sched_client):
   return value

def i2t_name(i_value, sched_client):
   return i_value

def i2t_weekly(ideal_weekly, sched_client):
   trane_weekly = []
   for daily_sched in ideal_weekly:
      day_list = []
      for time_val in daily_sched.time_values:
         tt9 = time_val.time.get_time_tuple()
         value = 2 # default to "Normal Stop"
         if time_val.value == 1:
            value = 1 # set to "Normal Start" if so specified
         stev_init_list = [(tt9[3],tt9[4],tt9[5]),value]
         stev_seq = SummitTimeEventValue_seq(stev_init_list)
         day_list.append(stev_seq)
      trane_weekly.append(day_list)
   # Rearrange given EnvIdeal day-number format into Trane day-number format:
   sunday = trane_weekly.pop(6)
   trane_weekly.insert(0,sunday)
   return trane_weekly

def i2t_exceptions(ideal_excs, sched_client):
   trane_excs = []
   for i_spec_evt in ideal_excs:
      cal_entry = i_spec_evt.period.calendar_entries[0]
      assert (cal_entry.type == 1), 'CalendarEntry has type %u. Must have type DateRange.' % cal_entry.type
      sig = get_signature_i(i_spec_evt)
      sched_client.add_exception_name(i_spec_evt.name, sig)
      stev_list = []
      for i_time_val in i_spec_evt.time_values:
         time_list = list(i_time_val.time.get_time_tuple())
         time_list = time_list[3:6] # only want hour,minute,second
         value = 1 # default to Normal Start
         if i_time_val.value == 0:
            value = 2 # Normal Stop
         stev_seq = SummitTimeEventValue_seq([time_list, value])
         stev_list.append(stev_seq)
      priority = i_spec_evt.evt_priority
      sse_seq = SummitSpecialEvent_seq([eval(str(cal_entry.days)), None, stev_list, priority])
      trane_excs.append(sse_seq)
   return trane_excs

# @param ideal_eff input param; datetime.DateRange
def i2t_effective(ideal_eff, sched_client):
   if (ideal_eff.start_date is None) \
      or (ideal_eff.end_date is None):
      return None
   i_start = ideal_eff.start_date
   t_start = (i_start.value[0], i_start.value[1], i_start.value[2])
   i_end = ideal_eff.end_date
   t_end = (i_end.value[0], i_end.value[1], i_end.value[2])
   trane_eff = [t_start, t_end]
   return trane_eff # list of 2 3tuples

def i2t_member_list(ideal_member_list, sched_client):
   trane_member_list = [] # no explicit member list supported by ideal Schedule class
   return trane_member_list

class PropConverter:
   def __init__(self, sched_client, t_sched_obj_node, node_name, attr_name, t2i, i2t):
      self._attr_name = attr_name
      # No need to be able to handle a "not yet" response from get_child(). If a BACnetTimeout
      # error occurs, then the cause is something serious (programming error, bad BCU behavior):
      self._node = t_sched_obj_node.get_child(node_name, wait_for_discovery=1)
      self._t2i = t2i
      self._i2t = i2t
      self._sched_client = sched_client # saved to pass to converters, for client-instance data
      # Trane/BACnet Schedule Objects do not support native COV. However, we should
      # still be able to use the "delivered" (as opposed to "polled") version of
      # subscription management. In this case, we let the SM use whatever efficiencies
      # it can:
      # @fixme Disabled use of SubscriptionMgr for schedules to reduce BACnet traffic and to
      # prevent thread conflicts and de-synch. Re-enable when SM and object/value model have
      # been revved for improved efficiency.
      #self._sid = sm.create_delivered(sched_client, {self._node.name:self._node})
   def get_node(self):
      return self._node
   def get_trane_value(self, ideal_value):
      return self._i2t(ideal_value)
   def get_ideal_value(self, trane_value):
      return self._t2i(trane_value)
   def set_in_schedule(self, sched_data, trane_value): # sched_data is input and output; trane_value is input
      setattr(sched_data, self._attr_name, self._t2i(trane_value, self._sched_client))
   def set_in_device(self, sched_data): # sched_data param is input; output is to node
      i_value = getattr(sched_data, self._attr_name)
      if i_value is None:
         return # do not set this property in the device
      t_value = self._i2t(i_value, self._sched_client)
      if t_value is None:
         return # do not set this property in the device
      self._node.set(t_value)
   def get_cur_t_value(self):
      t_value = self._node.get()
      return t_value
class _PersistentDataObject(PersistentDataObject):
   def global_context(self):
      return {'EnumeratedValue':EnumeratedValue}
class TraneBACnetSchedClient(client.Client):
   def __init__(self):
      CompositeNode.__init__(self)
      EventConsumerMixin.__init__(self, self._handle_event)
      self._ts_node = None
      self._lock = RLock() # need to allow multiple "acquires" by same thread
      self._convs_node = {}
      self._convs_name = {}
      self.running = 0
      # Create TimerSched, timer IDs, and periods for start_retry():
      self._start_retry_sched = TimerSched()
      self._start_retry_sched_entry = None # returned from call to _Schedule.after()
      self._start_retry_timer_ID = 0
      self._start_retry_delay = 1.0 # sec
      self._PDO = None
   def configure(self, cd):
      client.Client.configure(self, cd)
      set_attribute(self, 'ts_node_path', REQUIRED, cd, str)
      if hasattr(self, 'ts_node_path') and type(self.ts_node_path) != types.StringType:
         raise EInvalidValue('type of ts_node_path', type(ts_node_path), 'Must be StringType rep of URL.')
   def configuration(self):
      cd = client.Client.configuration(self)
      get_attribute(self, 'ts_node_path', cd, str)
      return cd
   def start(self):
      # Obtain ref to linked Trane Schedule Object node using given internal URL:
      try:
         self._ts_node = as_node(self.ts_node_path)
      except ENoSuchName, segment:
         msglog.log('mpx',msglog.types.INFO,'Starting start_retry_thread() for ' \
                    'BACnet Client child node of %s' % self.parent.name)
         # Target node may be dynamic, and our query above may have kicked off an autodiscovery
         # sequence on another thread. So, bail out now, and schedule another try for later...:
         self._start_retry_sched_entry = self._start_retry_sched.after( \
                       self._start_retry_delay, self.start_retry_thread, (self._start_retry_timer_ID,))
         return
      self._start_init() # finish startup ONLY if Trane Schedule Object node already exists
   def start_retry_thread(self, tmr_ID):
      if tmr_ID != self._start_retry_timer_ID:
         return
      t = Thread(None,self.start_retry)
      t.start()
   def start_retry(self):
      """start_retry: Timer callback to re-attempt acquisition of ref to previously unavailable 
         Schedule node"""
      # Obtain ref to linked Trane Schedule Object node using given internal URL:
      go = 1
      while go:
         try:
            self._ts_node = as_node(self.ts_node_path)
            go = 0
         except ENoSuchName, segment:
            time.sleep(1.0)
      self._start_init()
   def _start_init(self):
      """start_init: Does bulk of work for starting a TraneBACnetSchedClient node."""
      if not isinstance(self._ts_node, mpx.ion.bacnet.trane.object.Schedule):
         msglog.log('broadway', msglog.types.ERR, 'node path %s does not lead to' \
                    'Trane Schedule Object node' % self.ts_node_path)
         return
      #self._PDO = _PersistentDataObject(self,dmtype=GC_NEVER)
      self._PDO = PersistentDataObject(self,dmtype=GC_NEVER)
      self._PDO.exc_dates_to_name = {}
      self._PDO._unknown_idx = 0
      self._PDO.load()
      # Init converter maps for applicable Trane Schedule Object Properties:
      self._convs_node = {}
      self._convs_name = {}
      init_list = [ \
                   ['object_name', '_name', t2i_name, i2t_name], \
                   ['effective_period', '_effective', t2i_effective, i2t_effective], \
                   ['exception_schedule', '_special_events', t2i_exceptions, i2t_exceptions], \
                   ['weekly_schedule', '_weekly', t2i_weekly, i2t_weekly], \
                   #['member_list', '???', t2i_member_list, i2t_member_list], \
                  ]
      sd = ScheduleData()
      for i in init_list:
         pc = PropConverter(self, self._ts_node, i[0], i[1], i[2], i[3])
         n = pc.get_node()
         self._convs_node[n] = pc
         self._convs_name[n.name] = pc
         trane_value = n.get()
         pc.set_in_schedule(sd, trane_value)
      self.parent.set_schedule(self, sd)
      client.Client.start(self) # register for events
      self.running = 1
   def stop(self):
      self.running = 0
      #sm.destroy(self._sid)
      self._sid = None
      client.Client.stop(self)
   # If it is anticipated that the calling thread will spend "a long time" in this method,
   # then this method should queue up a method and its args in one of the three singleton
   # thread_pools (LOW priority, NORMAL, HIGH).
   def _handle_event(self, event): # overload superclass method to handle device-driven events:
      #if isinstance(event, _manager.ChangeValueEvent): # change event from a TSO Property node:
         #results = event.results()
         #try:
            #sd = self.parent.get_schedule()
         #except: # exception is raised if schedule "value" is an Exception instance
            #sd = None
         #if (sd is None) or (isinstance(sd, Exception)):
            #s = ScheduleData()
         #else:
            #w = copy.deepcopy(sd._weekly)
            #x = copy.deepcopy(sd._special_events)
            #f = copy.deepcopy(sd._effective)
            #s = ScheduleData(sd._name,sd._description,w,f,x)
         #self._lock.acquire()
         #try: # not expecting any exceptions; just want to ensure that lock is released in "finally"
            ## Use given (property) event data to update Ideal Schedule's data:
            #for node_name in results.keys():
               #pc = self._convs_name[node_name]
               #t_value = results[node_name]['value']
               #if isinstance(t_value, Exception):
                  #msglog.log('broadway',msglog.types.WARN,'TraneBACnetSchedClient._handle_event: value of %s is exception: %s' %
                             #(node_name, str(t_value)))
                  #s = t_value # parent node understands Exception subclasses offered as "schedules"
                  #break
               #pc.set_in_schedule(s, t_value)
            #self.parent.set_schedule(self, s) # including this call before lock.release() means lock MUST be RLock
         #finally:
            #self._lock.release()
      if event.source == self: # no more processing if this Client instance generated the event
         return
      else:
         client.Client._handle_event(self, event)
   # Handle changing values in Ideal Schedule:
   def _value_changed(self,event,old,new):
      pass #@FIXME: add code when Schedule has accessors for indiv ScheduleData attributes
   def _schedule_changed(self, event, sched_data):
      #@FIXME: change to write_prop_mult (instead of individual write_props) if/when feasible.
      # Clear out daterng/name associations, since entire schedule has been set (including
      # all exception schedules):
      if not isinstance(sched_data,Exception):
         self._lock.acquire()
         try:
            self._PDO.exc_dates_to_name.clear()
            self._PDO.save()
            # Note: Only need to set props that clients are allowed to modify:
            for pc in self._convs_name.values():
               pc.set_in_device(sched_data)            # send given property value to BCU
               t_value = pc.get_cur_t_value()          # get value of given property from BCU
               pc.set_in_schedule(sched_data, t_value) # send value from BCU to Ideal Sched
         finally:
            self._lock.release()
   def add_exception_name(self, name, sig):
      self._PDO.exc_dates_to_name[sig] = name
      self._PDO.save() # save expanded map
   def get_exception_name(self, sig):
      if self._PDO.exc_dates_to_name.has_key(sig):
         name = self._PDO.exc_dates_to_name[sig]
      else:
         name = 'Unknown' + str(self._PDO._unknown_idx)
         self.add_exception_name(name, sig)
         self._PDO._unknown_idx += 1
      return name

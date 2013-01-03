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
##
# Provides a set of classes to implement basic scheduling functions
# @see BACnet standard, sections 12.7,  20.2.12, 20.2.13

import time
from types import StringType, TupleType, IntType, ListType, FloatType
from exceptions import ENotImplemented, EInvalidValue, EAttributeError
from magnitude import MagnitudeInterface

class TimeOfDay(object):
    ##
    # @param value: time since LOCAL midnight, in the format HH:MM:SS or HH:MM
    # (both strings), or int or float of seconds, or 3-elem or 9-elem tuple or list
    # @note there are 86400 seconds in one day
    # @param None (default), implies time now
    # Value is saved as time 3-tuple (H,M,S) since midnight LOCAL time, NOT as GM/UTC 
    #   time, since most UI and programming of other devices is done in local time.
    def __init__(self, value=None):
        self.__dict__['_dyn_attrs'] = {'hour':0, 'minute':1, 'second':2}
        self._set_value(value)
    def __getattr__(self, attribute):
        if self.__dict__['_dyn_attrs'].has_key(attribute):
            return self.value[self.__dict__['_dyn_attrs'][attribute]]
        if not self.__dict__.has_key(attribute):
            raise EAttributeError(attribute)
        return self.__dict__[attribute]
    def __setattr__(self, attribute, value):
        if self._dyn_attrs.has_key(attribute):
            self.__dict__['value'][self._dyn_attrs[attribute]] = value
            self.__dict__['_int_value'] = None
            self.__dict__['_str_value'] = None
        elif attribute == 'value':
            self._set_value(value)
        else:
            self.__dict__[attribute] = value
    def _set_value(self, value):
        if value is None:
            tt = time.localtime()
            value = [tt[3], tt[4] , tt[5]]
        elif type(value) == StringType:
            try:
                tt = time.strptime(value,'%H:%M:%S')
            except:
                try:
                    tt = time.strptime(value,'%H:%M')
                except:
                    raise EInvalidValue('Incorrect time string format',
                                        value, 'Use %H:%M:%S or %H:%M')
            value = [tt[3], tt[4] , tt[5]]
        elif (type(value) == TupleType) or (type(value) == ListType): # tuple or list
            if len(value) == 3: # 3-elem
                value = [value[0], value[1], value[2]]
            elif len(value) == 9: # 9-elem ("time tuple")
                value = [value[3], value[4], value[5]]
            else:
                raise EInvalidValue('value',value,'Incorrect num elems in time tuple/list; '\
                                    'must be 3-elem or 9-elem')
        elif isinstance(value, (IntType, FloatType)): # value is given in seconds
            tt = time.gmtime(int(value)) # use gmtime (not localtime) because gm does not apply tz offsets
            value = [tt[3], tt[4], tt[5]]
        else:
            raise EInvalidValue('value',value,'must be int, float, time string, '\
                                'or 3-elem or 9-elem tuple or list')
        self.__dict__['value'] = value # 3-elem list (H,M,S)
        self.__dict__['_int_value'] = None
        self.__dict__['_str_value'] = None
    def __str__(self):
        if self._str_value is None:
            self._str_value = '%s:%s:%s' % (str(self.value[0]), str(self.value[1]), str(self.value[2]))
        return self._str_value
    def __int__(self): # returns num sec since midnight
        if self._int_value is None:
            value_copy = list(self.value)
            filler = time.localtime() # use current time elems for any wild card
            for i in range(3):
                if value_copy[i] is None:
                    value_copy[i] = filler[i+3]
            self._int_value = (value_copy[0] *3600) + (value_copy[1] * 60) + value_copy[2]
        return self._int_value
    def __float__(self):
        return float(self.__int__())
    def get_time_tuple(self):
        return (0,0,0,self.value[0],self.value[1],self.value[2],0,0,0)
    def __cmp__(self, o):
        for i in range(3):
            if (self.value[i] is None) or (o.value[i] is None) or (self.value[i] == o.value[i]):
                continue
            elif self.value[i] > o.value[i]:
                return 1
            else:
                return -1
        return 0
    def __add__(self, o):
        return self.__class__(int(self) + int(o))
    def __sub__(self, o):
        return self.__class__(int(self) - int(o))
##
# provides a local date object, independent of time
# Input Values:
#  None (defaults to current local tuple)
#  Local Tuple or List
#  GMT Days Since Epoch Int or Float
#  
class Date(object):
    def __init__(self, value=None):
        self.__dict__['_dyn_attrs'] = {'year':0, 'month':1, 'day':2, 'weekday':6}
        self._set_value(value)
    def __getattr__(self, attribute):
        if self.__dict__['_dyn_attrs'].has_key(attribute):
            return self.value[self.__dict__['_dyn_attrs'][attribute]]
        if not self.__dict__.has_key(attribute):
            raise EAttributeError(attribute)
        return self.__dict__[attribute]
    def __setattr__(self, attribute, value):
        if self._dyn_attrs.has_key(attribute):
            val_list = list(self.__dict__['value'])
            val_list[self._dyn_attrs[attribute]] = value
            self.__dict__['value'] = tuple(val_list)
            self.__dict__['_float_value'] = None
            self.__dict__['_str_value'] = None
        elif attribute == 'value': # despite checks below, caller can still pass in bad values for list elems...
            self._set_value(value)
        else:
            self.__dict__[attribute] = value
    def _set_value(self, v):
        val_list = list(time.localtime()) #starting point
        if (type(v) == IntType) or (type(v) == FloatType):
            val_list = list(time.localtime(v * 86400)) # input is in DAYS since epoch (GMT); convert to (LOCAL) time-tuple
        elif (type(v) == TupleType) or (type(v) == ListType) or (type(v) == time.struct_time):
            if len(v) == 3:
                val_list = [v[0],v[1],v[2],0,0,0,0,0,0]
            elif len(v) == 9:
                val_list = list(v)
            else: # not standard time tuple OR simple date 3-tuple (YYYY, MM, DD):
                raise EInvalidValue('Date', v, \
                                    'Invalid num elems in list or tuple; must have 3 or 9')
            val_list[7]=0  # show unknown day-of-year
            # If no relevant Nones, make sure that weekday, day-of-year, and DST are correct:
            if (val_list[0] is not None) and (val_list[1] is not None) and (val_list[2] is not None):
                val_list = list(time.localtime(time.mktime(val_list)))
        elif not v is None:
            raise EInvalidValue('Date', v, \
                                'Must be int, float, or 3-elem or 9-elem list or tuple')
        val_list[3]=0  # zero out hours
        val_list[4]=0  # zero out minutes
        val_list[5]=0  # zero out seconds
        val_list[8]=0  # do NOT use DST: screws up difference calcs
        self.__dict__['value'] = tuple(val_list)
        self.__dict__['_float_value'] = None
        self.__dict__['_str_value'] = None
    def __str__(self):
        if self._str_value is None:
            self._str_value = '(%s,%s,%s)' \
                % (self.value[0], self.value[1], self.value[2])
        return self._str_value    
    def __int__(self): # returns (whole) num GMT DAYS since epoch; always rounds up; DO NOT USE FOR CALCULATIONS!!!:
        f = self.__float__()
        i = float(int(f))
        if f > i:
            return i + 1
        return i
    def __float__(self): # return num GMT DAYS (incl. fractions!) since epoch:
        if self._float_value is None:
            val_list = list(self.value)
            filler = time.localtime() # use current date elems for any wild card
            for i in range(0,3): # interested ONLY in date elems (YYYY,MM,DD) of list
                if val_list[i] is None:
                    val_list[i] = filler[i]
            sec_since_epoch = time.mktime(tuple(val_list))
            self._float_value = sec_since_epoch / 86400.0
        return self._float_value
    def __cmp__(self, o):
        for i in range(3):
            if (self.value[i] is None) or (o.value[i] is None) or (self.value[i] == o.value[i]):
                continue
            elif self.value[i] > o.value[i]:
                return 1
            else:
                return -1
        return 0
    def as_list(self):
        return [self.value[0],self.value[1],self.value[2]]
    def __add__(self, o):
        return self.__class__(float(self) + float(o))
    def __sub__(self, o):
        if (type(o) == IntType) or (type(o) == FloatType):
            # Rtn instance of Date, representing self less given number of days:
            return self.__class__(float(self) - float(o)) 
        elif isinstance(o,self.__class__):
            # Rtn a float (days between self and o; includes self but not o):
            return float(self) - float(o) 

##
# if the start_date is unspecified, it means: 
#   "any date up to and including the end_date." 
# If the end_date is unspecified, it means:
#   "any date from the start_date on."
# If both start_date and end_date are None, is means:
#   "no date match", by convention
class DateRange(object):
    def __init__(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = Date((None, None, None,))
        elif not isinstance(start_date, Date):
            start_date = Date(start_date)
        if end_date is None:
            end_date = Date((None, None, None,))
        elif not isinstance(end_date, Date):
            end_date = Date(end_date)
        self.start_date = start_date
        self.end_date = end_date
    def within_range(self, now=None):
        if now is None:
            now = Date() #now means now!
        after_start = 0
        if (now >= self.start_date):
            after_start = 1
        before_end = 0
        if (now <= self.end_date):
            before_end = 1
        return after_start and before_end
    def get_range(self):
        dates = []
        day = int(self.start_date)
        date = Date(day)
        while self.within_range(date):
            dates.append(date)
            day += 1
            date = Date(day)
        return dates
    def match(self, now=None):
        return self.within_range(now)
    def get_duration(self): # in days, including both start and end
        return int(self.end_date - self.start_date + 1)
    def __setattr__(self, attribute, value):
        if attribute == 'start_date':
            if not isinstance(value,Date):
                value = Date(value)
            self.__dict__['start_date'] = value
        elif attribute == 'end_date':
            if not isinstance(value,Date):
                value = Date(value)
            self.__dict__['end_date'] = value
        else:
            self.__dict__[attribute] = value
    # __eq__: Must handle pathological cases like this:
    # self =  [(2003,10,10), (None, 5, 5)]
    # other = [(None,10,10), (2001, None, 5)]
    # Without special attention, these ranges, which cannot possibly be equal,
    # would compare as equal. So, do straight- AND cross-comparisons:
    def __eq__(self,other):
        return ((self.start_date == other.start_date) \
              and (self.end_date == other.end_date) \
              and (self.start_date <= other.end_date) \
              and (self.end_date >= other.start_date))
    def __str__(self):
        return '[%s,%s]' % (str(self.start_date), str(self.end_date))
    def as_list(self):
        rtn_lst = [self.start_date.as_list(), self.end_date.as_list()]
        return rtn_lst
    def from_list(self, dr_lst):
        self.start_date = Date(dr_lst[0])
        self.end_date = Date(dr_lst[1])
        
class TimeValue(object):
    """
    class TimeValue: represents an event trigger point in time. Includes the
    value/action to be set/performed when triggered.
    """
    def __init__(self,time=None,value=None):
        self.time = time # TimeOfDay
        # for Costco, boolean (0 or 1) only; eventually,
        #   any number, function, or object(?)
        self.value = value
    def __eq__(self,other):
        return (self.time == other.time) and (self.value == other.value)
    def as_list(self):
        rtn_list = [self.time.value, self.value] #@FIXME: when self.value becomes non-numeric, -> "self.value.as_list()"
        return rtn_list
    def from_list(self, tv_lst):
        self.time = TimeOfDay(tv_lst[0])
        self.value = tv_lst[1]

class DailySchedule(object):
    # Use None as default, since any other default is only instanciated once.
    # That single instance will be used for ALL subsequent ctor calls that
    # do not specify a value for time_values! (Ie the defaults are contained
    # in the dictionary for the DailySchedule.__init__() method.)
    def __init__(self,time_values = None): 
        # list of TimeValue triggers for this DailySchedule
        if time_values is None:
            time_values = []
        self.time_values = time_values
        # index of last-activated TimeValue
        self.cur_time_val_idx = None
    def __eq__(self,other):
        return self.time_values == other.time_values
    def as_list(self):
        rtn_list = []
        for tv in self.time_values:
            rtn_list.append(tv.as_list())
        return rtn_list
    def from_list(self, ds_lst):
        self.time_values = []
        for tv_lst in ds_lst:
            tv = TimeValue()
            tv.from_list(tv_lst)
            self.time_values.append(tv)
# week_of_month
#  1 = days numbered 1-7
#  2 = days numbered 8-14
#  3 = days numbered 15-21
#  4 = days numbered 22-28
#  5 = days numbered 29-31
#  6 = last 7 days of this month
#  0xFF = any week of this month
##
# @todo Add get_date_range function to represent this as
#       a date range.
class WeekNDay(object):
    def __init__(self,month=None,week=None,day=None):
        self.month = month # (1..12), or 0xFF for any month
        self.week_of_month = week
        # (1..7), 1 = Mon, or 0xFF for any day of week
        self.day_of_week = day
        
class Calendar(object):
    def __init__(self,entries=None):
        if entries is None:
            entries = []
        self.calendar_entries = entries
    def __eq__(self,other):
        return self.calendar_entries == other.calendar_entries
    def as_list(self):
        rtn_lst = []
        for ce in self.calendar_entries:
            rtn_lst.append(ce.as_list())
        return rtn_lst
    def from_list(self, cal_lst):
        self.calendar_entries = []
        for ce_lst in cal_lst:
            ce = CalendarEntry()
            ce.from_list(ce_lst)
            self.calendar_entries.append(ce)
##
# @todo I think all days can be turned into DateRange.
class CalendarEntry(object):
    """
    class CalendarEntry: specifies one or more days
    """
    def __init__(self,entry_type=None,days=None):
        # type for self.days = 0:Date, 1:DateRange, 2:WeekNDay
        self.type = entry_type
        self.days = days
    def __eq__(self,other):
        return (self.type == other.type) and (self.days == other.days)
    def as_list(self):
        rtn_lst = [self.type, self.days.as_list()]
        return rtn_lst
    def from_list(self, ce_lst):
        self.type = ce_lst[0]
        if self.type == 0:
            raise ENotImplemented('Currently, must use ONLY DateRanges as CalendarEntry periods') #@FIXME: to do
        elif self.type == 1:
            self.days = DateRange()
            self.days.from_list(ce_lst[1])
        else:
            raise ENotImplemented('Currently, must use ONLY DateRanges as CalendarEntry periods') #@FIXME: to do
class SpecialEvent(object):
    def __init__(self,name=None,period=None,time_values=None,priority=8):
        if name is None:
            name = ''
        self.name = name
        self.period = period # Calendar object
        self.time_values = time_values
        self.cur_time_val_idx = None # index of last-activated TimeValue
        # (1..16), 1 = highest; default to mid-level priority
        #   Used to resolve overlapping SpecialEvent periods
        self.evt_priority = priority 
    def __eq__(self,other):
        return ((self.period == other.period) and
                (self.time_values == other.time_values) and
                (self.evt_priority == other.evt_priority))
    def as_list(self):
        rtn_lst = [self.name, self.period.as_list(),[]]
        for tv in self.time_values:
            rtn_lst[2].append(tv.as_list())
        return rtn_lst
    def from_list(self, se_lst):
        self.name = se_lst[0]
        self.period = Calendar()
        self.period.from_list(se_lst[1])
        self. time_values = []
        for tv_lst in se_lst[2]:
            tv = TimeValue()
            tv.from_list(tv_lst)
            self.time_values.append(tv)
class DateTime(object):
    def __init__(self,date=None,time=None):
        self.date = date
        self.time = time
    def __eq__(self,other):
        return (self.date == other.date) and (self.time == other.time)

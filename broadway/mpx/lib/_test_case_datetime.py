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
_test_case_datetime.py
"""
import copy
from mpx_test import DefaultTestFixture, main
from mpx.lib.datetime import *

class TestCase(DefaultTestFixture): 
    def __init__(self,method_name):
        DefaultTestFixture.__init__(self,method_name)
    def setUp(self):
        DefaultTestFixture.setUp(self)
    def tearDown(self):
        DefaultTestFixture.tearDown(self)    
    def test_TimeOfDay(self):
        tod0 = TimeOfDay()
        time.sleep(2)
        tod1 = TimeOfDay()
        assert tod1 > tod0, 'Default init of TimeOfDay failed.'
        tt0 = (2003,10,31,12,59,59,0,0,-1)
        tod0 = TimeOfDay(tt0)
        tt1 = tod0.get_time_tuple()
        assert tt1[3:6] == tt0[3:6], 'Failed to init TimeOfDay from 9-tuple'
        tod1 = TimeOfDay('12:59:59')
        tt1 = tod1.get_time_tuple()
        assert tt1[3:6] == tt0[3:6], 'Failed to init TimeOfDay from "H:M:S" string'
        assert tod0 == tod1
        tod1 = TimeOfDay('12:59')
        tt1 = tod1.get_time_tuple()
        assert tt1[3:5] == tt0[3:5], 'Failed to init TimeOfDay from "H:M" string'
        try:
            tod1 = TimeOfDay('12,59,59')
        except Exception, e:
            assert isinstance(e,EInvalidValue), 'Failed to raise EInvalidValue after getting invalid string in TimeOfDay init'
        else:
            assert 0, 'Failed to raise exception after getting invalid string in TimeOfDay init'
        tod1 = TimeOfDay((12,59,59,))
        assert tod0 == tod1, 'Failed to init TimeOfDay with 3-tuple, or to compare it to another TOD'
        assert int(tod0) == int(tod1), 'Failed to convert TimeOfDay to int'
        assert float(tod0) == float(tod1), 'Failed to convert TimeOfDay to float'
        try:
            tod1 = TimeOfDay((12,59,59,1,))
        except Exception, e:
            assert isinstance(e,EInvalidValue), 'Failed to raise EInvalidValue after getting invalid (4-)tuple in TimeOfDay init'
        else:
            assert 0, 'Failed to raise exception after getting invalid (4-)tuple in TimeOfDay init'
        tod1 = TimeOfDay((12,59,None,))
        assert tod0 == tod1, 'Failed to compare wild card seconds in TimeOfDay properly'
        tod1 = TimeOfDay((13,None,None,))
        assert tod0 < tod1, 'Failed to compare partially wild-carded TimeOfDay'
        tod1 = TimeOfDay([0,0,0]) + 7135
        assert tod1.value == [1,58,55], 'Failed to add integer to TimeOfDay'
        tod1.hour = 3
        tod1.minute = 2
        tod1.second = 1
        assert tod1.value == [3,2,1], 'Failed to set one or more attributes of TimeOfDay'
        tod1.value = [1,2,3]
        assert tod1.value == [1,2,3], 'Failed to set value attribute of TimeOfDay'
        tod1_copy = copy.deepcopy(tod1)
        assert tod1 == tod1_copy, 'Failed to do a proper deepcopy on TimeOfDay object'
    def test_Date(self):
        d0 = Date()
        tt_now = time.localtime()
        assert d0.as_list() == [tt_now[0],tt_now[1],tt_now[2]], 'Default init of Date failed.'
        tt1 = (2003,10,31,12,59,59,0,0,-1)
        d1 = Date(tt1)
        assert d1.as_list() == [2003,10,31], 'Failed to init Date with 9-tuple, or to distill Date to 3-list'
        num_days = float(d1)
        assert num_days == 12356.333333333334, 'Failed to return proper number of days as float() of Date'
        d1 = Date(12356.333333333334)
        assert d1.as_list() == [2003,10,31], 'Failed to init new Date object with float'
        d1 = Date((d0.year,None,d0.day,))
        assert d1 == d0, 'Failed to init Date with tuple (Y,M,D)'
        try:
            d1 = Date((2003,10,31,1,))
        except Exception, e:
            assert isinstance(e,EInvalidValue), 'Failed to raise EInvalidValue after getting invalid (4-)tuple in Date init'
        else:
            assert 0, 'Failed to raise exception after getting invalid (4-)tuple in Date init'
        d1 = Date(tt1)
        d0 = Date([2003,10,None])
        assert d0 == d1, 'Failed to init or compare Date with wildcarded day'
        d0 = TimeOfDay((2004,None,None,))
        assert d0 > d1, 'Failed to compare Date with wild-carded month and day'
        d0 = Date([2003,1,1]) + 397
        assert d0.as_list() == [2004,2,2], 'Failed to add integer to Date'
        d0.year = 2003
        d0.month = 2
        d0.day = 1
        assert d0.as_list() == [2003,2,1], 'Failed to set one or more attributes of Date'
        d0.value = [2001,2,3]
        assert d0.as_list() == [2001,2,3], 'Failed to set value attribute of Date'
        st = time.struct_time(tt1)
        d0 = Date(st)
        assert d0.as_list() == [2003,10,31] and d0.value[3:6] == (0,0,0), 'Failed to init new Date with type "time.struct_time" object'
        gmt_secs = time.mktime(tt1)
        next_day_days = gmt_secs/86400 + 1
        next_day = Date(next_day_days)
        assert next_day.as_list() == [2003,11,1] and next_day.value[3:6] == (0,0,0), 'Failed to add 1 day to existing Date properly'
        next_day_copy = copy.deepcopy(next_day)
        assert next_day == next_day_copy, 'Failed to do a proper deepcopy on Date object'
    def test_DateRange(self):
        dr0 = DateRange(None, [2003,10,15])
        dr1 = DateRange(Date([2000,1,1]))
        assert dr0 == dr1, 'Failed to init DateRange with defaults, or to compare wildcarded DateRanges'
        dr0.end_date.year = 1999
        assert dr0 != dr1, 'Failed to compare DateRanges with wildcards properly'
        d0 = Date()
        assert dr1.within_range(d0), 'Failed to determine that a given Date was within a DateRange with a wildcarded end_date'
        dr0 = DateRange([2003,1,1],[2004,2,2])
        # get_duration() includes every day in the CLOSED interval [start_date,end_date],
        # (ie including both start_date and end_date themselves):
        assert dr0.get_duration() == 398, 'Failed to calculate proper duration for a DateRange with no wildcards'
        dr0.start_date = Date()
        dr0.end_date = dr0.start_date + 30
        assert dr0.get_duration() == 31, 'Failed to set/get start_date or end_date in DateRange, OR failed to calc duration properly'
        assert dr0.within_range(dr0.start_date), 'Failed to determine that start_date is within range of DateRange'
        assert dr0.within_range(dr0.end_date), 'Failed to determine that end_date is within range of DateRange'
    def test_TimeValue(self):
        tod = TimeOfDay([11,59,59])
        tv0 = TimeValue(tod, 1)
        tv1 = TimeValue()
        tv1.time = tod
        tv1.value = 1
        assert tv0 == tv1, 'Failed to init and/or compare two TimeValues'
        assert tv0.as_list() == [[11,59,59],1], 'Failed to distill TimeValue to list properly'
        l = [[11,59,59],0]
        tv1.from_list(l)
        assert tv1.as_list() == l, 'Failed to init TimeValue from list'
    def test_DailySchedule(self):
        tv_list = [[[8,0,0],1],[[13,30,30],0],[[21,45,45],1],[[23,59,59],0]]
        ds0 = DailySchedule()
        ds0.from_list(tv_list)
        assert ds0.as_list() == tv_list, 'Failed to init DailySchedule from list'
    def test_SpecialEvent_Calendar_CalendarEntry(self):
        cal_list = [[1,[[2003,1,15],[2003,4,15]]],[1,[[2003,4,15],[2003,6,15]]],[1,[[2003,6,15],[2004,2,2]]]]
        cal = Calendar()
        cal.from_list(cal_list)
        assert cal.calendar_entries[2].days.get_duration() == 233, 'Failed to init Calendar from list'
        assert cal.as_list() == cal_list, 'Failed to distill Calendar to list'
        tv_list = [[[8,0,0],1],[[13,30,30],0],[[21,45,45],1],[[23,59,59],0]]
        se_list = ['SpecEvt0',cal_list,tv_list]
        se0 = SpecialEvent()
        se0.from_list(se_list)
        assert se0.name == 'SpecEvt0', 'Failed to init SpecialEvent from list: name'
        assert se0.period.calendar_entries[2].days.get_duration() == 233, 'Failed to init SpecialEvent from list: period'
        assert (int(se0.time_values[3].time) - int(se0.time_values[2].time)) == 8054, 'Failed to init SpecialEvent from list: time_values'
        assert se0.as_list() == se_list, 'Failed to distill SpecialEvent to list properly'
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        
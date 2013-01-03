"""
Copyright (C) 2002 2003 2005 2010 2011 Cisco Systems

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

from mpx.lib import tzinfo
from mpx.lib.exceptions import ENotImplemented
from mpx.service import ServiceNode

from time_attribute import MilliSeconds
from time_attribute import TimeAttribute

##
# @interface
# TimeZone has 7 children: year,month,day,minute,seconds,milliseconds
# year node returns the year (example 2002)
# month node returns month as an interger range [1,12]
# day node returns day as an integer range[1,31]
# hour node returns hour as and integer range [0,23]
# minute node returns minute as a integer range [0,59]
# second node returns seconds as an integer range[0,61]
# weekday node returns an integer specifying the day of the week
#   monday=0 range[0,6]
# millisecond returns milliseconds as a float
class TimeZone(ServiceNode):
    ##
    # adds children year,month,day,minute,
    # seconds,weekday,milliseconds nodes
    def __init__(self):
        ServiceNode.__init__(self)
        self._tzklass = tzinfo.TZInfo
        year = {'name':'year','index':0}
        month = {'name':'month','index':1}
        day = {'name':'day','index':2}
        hour = {'name':'hour','index':3}
        minute  = {'name':'minute','index':4}
        second  = {'name':'second','index':5}
        weekday = {'name':'weekday','index':6}
        ta = [year,month,day,hour,minute,weekday,second]
        for x in ta:
            y = TimeAttribute(x['index'])
            y.configure({'name':x['name'],'parent':self})
        milliseconds = MilliSeconds()
        milliseconds.configure({'name':'milliseconds','parent':self})   
        return
    def get_tzinfo(self, sample_time=None):
        return self._tzklass(sample_time)
    def get_tzinfo_range(self, start, end):
        return tzinfo.get_tzinfo_range(self._tzklass, start, end)
    ##
    # @interface
    # @param using The unixtime to convert to a time tuple.
    # @return tuple of time values
    # tuple format
    # index 0 - year (for example, 1993)
    # index 1 - month range [1,12]
    # index 2 - day range [1,31]
    # index 3 - hour  range [0,23]
    # index 4 - minute range [0,59]
    # index 5 - second range [0,61]
    # index 6 - weekday range [0,6], Monday is 0
    # index 7 - Julian day  range [1,366]
    # index 8 - daylight savings  0, 1
    # @exception raise an ENotImplemented
    def time_tuple(self, using=None):
        raise ENotImplemented()
    def _time(self):
        return self.parent.get()

##
# TimeZone class that returns the current time
# in UTC time in seconds since the epochs
class UTC(TimeZone):
    def __init__(self):
        TimeZone.__init__(self)
        self._tzklass = tzinfo.UTCTZInfo
        return
    ##
    # @return seconds since the epochs in UTC time
    def get(self, skipCache=0):
        t = self._time()
        fractional = t - int(t)
        return time.mktime(self.time_tuple(t)) + fractional
    ##
    # @return a tuple of time values
    def time_tuple(self,using=None):
        if using is None: using = self._time()
        return time.gmtime(using)

##
# TimeZone class that returns the current time
# in Local time in seconds since the epochs.        
class Local(TimeZone):
    def __init__(self):
        TimeZone.__init__(self)
        self._tzklass = tzinfo.LocalTZInfo
        return
    ##
    # @return seconds since the epochs in Local time
    def get(self, skipCache=0):
        t = self._time()
        fractional = t - int(t)
        return time.mktime(self.time_tuple(t)) + fractional
    ##
    # @return a tuple of time values
    def time_tuple(self, using=None):
        if using is None: using = self._time()
        return time.localtime(using)

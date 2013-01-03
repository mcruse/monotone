"""
Copyright (C) 2008 2011 Cisco Systems

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
# Helper functions for dealing with timezones, localtime and daylight-time.

import time

class TZInfo(object):
    SECOND = 1
    MINUTE = SECOND*60
    HOUR = MINUTE*60
    DAY = HOUR*24
    WEEK = DAY*7
    YEAR = 365*DAY
    def __init__(self, sample_time=None):
        self.sample_time = sample_time
        self.has_dst = None
        self.is_dst = None
        self.next_dst_toggle = None
        self.tz_offsets = None
        self.tz_names = None
        return
    def as_dict(self):
        return {
            'sample_time':self.sample_time,
            'has_dst':self.has_dst,
            'is_dst':self.is_dst,
            'next_dst_toggle':self.next_dst_toggle,
            'tz_offsets':self.tz_offsets,
            'tz_names':self.tz_names,
            }
    def __repr__(self):
        return repr(self.as_dict())

class LocalTZInfo(TZInfo):
    ##
    # @note Python 2.2 based implementation.  It's not historically accurate as
    #       the timezone information only pertains to the "current" definition
    #       of localtime.
    def _calculate_next_dst_toggle(klass, now):
        now = int(now)
        if not time.daylight:
            return 0
        def scan_next_dst_toggle(begin, end, steps):
            if steps:
                step = steps.pop(0)
                ts_right = begin
                lt_right = time.localtime(begin)
                end = end - step
                while ts_right <= end:
                    ts_left = ts_right
                    lt_left = lt_right
                    ts_right += step
                    lt_right = time.localtime(ts_right)
                    if lt_left.tm_isdst != lt_right.tm_isdst:
                        return scan_next_dst_toggle(ts_left, ts_right, steps)
            return end
        return scan_next_dst_toggle(
            now, now+klass.YEAR,
            [klass.WEEK, klass.DAY, klass.HOUR, klass.MINUTE, klass.SECOND]
            )
    _calculate_next_dst_toggle = classmethod(_calculate_next_dst_toggle)
    def __init__(self, sample_time=None):
        if sample_time is None:
            sample_time = time.time()
        self.sample_time = sample_time
        lt_sample_time = time.localtime(sample_time)
        self.has_dst = time.daylight
        self.is_dst = lt_sample_time.tm_isdst
        self.next_dst_toggle = self._calculate_next_dst_toggle(sample_time)
        if self.has_dst:
            self.tz_offsets = (time.timezone, time.altzone)
            self.tz_names = time.tzname
        else:
            self.tz_offsets = (time.timezone, time.timezone)
            self.tz_names = (time.tzname[0], time.tzname[0])
        return

class UTCTZInfo(TZInfo):
    def __init__(self, sample_time=None):
        if sample_time is None:
            sample_time = time.time()
        self.sample_time = sample_time
        self.has_dst = 0
        self.is_dst = 0
        self.next_dst_toggle = 0
        self.tz_offsets = (0, 0)
        self.tz_names = ('UTC', 'UTC')
        return

def get_tzinfo_range(klass, start, end):
    result = []
    while start and (start < end):
        tzinfo = klass(start)
        result.append(tzinfo)
        start = tzinfo.next_dst_toggle
    return result

#
# Install the XMLRPC Marshaller:
#
from xmlrpclib import register_marshaller
from xmlrpclib import ObjectMarshaller

class TZInfoMarshaller(ObjectMarshaller):
    def encode_on(self, xmlrpc_marshaller, *args):
        xmlrpc_marshaller.dump_struct(*map(lambda arg: arg.as_dict(), args))
        return
    def encode(self, d):
        raise 'Huh?'
    def decode(self, d):
        raise 'Huh?'

register_marshaller(TZInfo, TZInfoMarshaller())

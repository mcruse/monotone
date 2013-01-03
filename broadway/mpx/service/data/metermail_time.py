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
import calendar
import time

class DSTRange(object):
    def __init__(self, year):
        self._dst_start = None
        self._dst_end = None
        start_dst, end_dst = scan_year_for_dst(year)
        if start_dst:
            self._dst_start = (
                W3CDateTime(start_dst).as_string_YYYYMMDDhhmmss_utc()
                )
        if end_dst:
            self._dst_end = W3CDateTime(end_dst).as_string_YYYYMMDDhhmmss_utc()
        return
    def __eq__(self, other):
        return (
            (self._dst_start == other._dst_start) and
            (self._dst_end == other._dst_end)
            )

    def dst_start_text(self):
        return self._dst_start
    def dst_end_text(self):
        return self._dst_end

class DSTBias(object):
    def __init__(self):
        self._bias = str(time.timezone/60)
        self._dst_bias = str((time.altzone - time.timezone)/60)
    def bias_text(self):
        return self._bias
    def dst_bias_text(self):
        return self._dst_bias

dst_range_map = {}

def dst_range(year):
    global dst_range_map
    if dst_range_map.has_key(year):
        return dst_range_map[year]
    range_object = DSTRange(year)
    dst_range_map[year] = range_object
    return range_object

DST_BIAS = DSTBias()

class W3CDateTime(object):
    fmt_y = "%04d"
    fmt_ym = fmt_y + "-%02d"
    fmt_ymd = fmt_ym + "-%02d"
    fmt_ymd_hm  = fmt_ymd + "T%02d:%02d%s"
    fmt_ymd_hms = fmt_ymd + "T%02d:%02d:%02d%s"
    fmt_ymd_hmss = fmt_ymd + "T%02d:%02d:%02d.%06d%s"
    def __init__(self, seconds_since_epoch_utc=None):
        if seconds_since_epoch_utc is None:
            self._time = time.time()
        else:
            self._time = seconds_since_epoch_utc
        return
    def _TZD_local_string(klass, local_time):
        if local_time.tm_isdst:
            tz_offset = time.altzone
        else:
            tz_offset = time.timezone
        if tz_offset < 0:
            tz_offset = abs(tz_offset)
            tz_direction = "+" # "Ahead" of UTC (e.g. Europe)
        else:
            tz_direction = "-" # "Behind" UTC (e.g. North America)
        hh = int(tz_offset / 3600)
        mm = int((tz_offset % 3600) / 60)
        return "%s%02d:%02d" % (tz_direction, hh, mm)
    _TZD_local_string = classmethod(_TZD_local_string)
    def as_string_YYYYMMDDhhmmss_local(self):
        local_time = time.localtime(self._time)
        return self.fmt_ymd_hms % (
            local_time.tm_year,
            local_time.tm_mon,
            local_time.tm_mday,
            local_time.tm_hour,
            local_time.tm_min,
            local_time.tm_sec,
            self._TZD_local_string(local_time)
            )
    def as_string_YYYYMMDDhhmmss_utc(self):
        utc_time = time.gmtime(self._time)
        return self.fmt_ymd_hms % (
            utc_time.tm_year,
            utc_time.tm_mon,
            utc_time.tm_mday,
            utc_time.tm_hour,
            utc_time.tm_min,
            utc_time.tm_sec,
            "Z"
            )
    def as_string_YYYYMMDDhhmmsss_local(self):
        local_time = time.localtime(self._time)
        return self.fmt_ymd_hmss % (
            local_time.tm_year,
            local_time.tm_mon,
            local_time.tm_mday,
            local_time.tm_hour,
            local_time.tm_min,
            local_time.tm_sec,
            0,
            self._TZD_local_string(local_time)
            )
    def as_string_YYYYMMDDhhmmsss_utc(self):
        utc_time = time.gmtime(self._time)
        return self.fmt_ymd_hmss % (
            utc_time.tm_year,
            utc_time.tm_mon,
            utc_time.tm_mday,
            utc_time.tm_hour,
            utc_time.tm_min,
            utc_time.tm_sec,
            0,
            "Z"
            )
    def as_string_local(self):
        return self.as_string_YYYYMMDDhhmmsss_local()
    def as_string_utc(self):
        return self.as_string_YYYYMMDDhhmmsss_utc()

#
# This section contains voodoo to use the UNIX localtime() facility to
# determine if and when DST starts and ends for a specified year given this
# Mediator's timezone configuration at start time.  This is the, um, easiest
# way I found in Python 2.2.  It's crude, but the results for each year
# requested are cached so the overhead is only incurred once for any given year
# requested.
#

def scan_for_dst_transition_by(start, end, by):
    initial_state = time.localtime(start).tm_isdst
    start += by
    end += by
    for t in xrange(start, end, by):
        if time.localtime(t).tm_isdst != initial_state:
            return t
    return None

def scan_for_dst_transition(start, end):
    MINUTE = 60
    HOUR = 60*MINUTE
    DAY = 24*HOUR
    THIRTYDAYS = 30*DAY
    not_yet_dst = start
    #
    # Find 30 day period in which DST starts.
    #
    already_dst = scan_for_dst_transition_by(not_yet_dst, end, THIRTYDAYS)
    if not already_dst:
        # No DST...
        return None
    not_yet_dst = max(not_yet_dst, already_dst-THIRTYDAYS)
    #
    # Find day in which DST starts.
    #
    already_dst = scan_for_dst_transition_by(not_yet_dst, end, DAY)
    not_yet_dst = max(not_yet_dst, already_dst-DAY)
    #
    # Find hour in which DST starts.
    #
    already_dst = scan_for_dst_transition_by(not_yet_dst, end, HOUR)
    not_yet_dst = max(not_yet_dst, already_dst-HOUR)
    #
    # Find minute in which DST starts.
    #
    already_dst = scan_for_dst_transition_by(not_yet_dst, end, MINUTE)
    not_yet_dst = max(not_yet_dst, already_dst-MINUTE)
    #
    # Find second on which DST starts.
    #
    return scan_for_dst_transition_by(not_yet_dst, end, 1)

def scan_for_start_dst(start, end):
    assert not time.localtime(start).tm_isdst
    return scan_for_dst_transition(start, end)

def scan_for_end_dst(start, end):
    assert time.localtime(start).tm_isdst
    return scan_for_dst_transition(start, end)

def scan_year_for_dst(year):
    year_begin = calendar.timegm((year, 1, 1, 0, 0, 0))
    year_end = calendar.timegm((year+1, 1, 1, 0, 0, 0)) - 1
    start_dst = scan_for_start_dst(year_begin, year_end)
    if not start_dst:
        return (None, None)
    end_dst = scan_for_end_dst(start_dst, year_end)
    return (start_dst, end_dst)


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
##
# This module provides classes and functions for extracting meaningful
# information from /proc/#/stat in what is hopefully an efficient, yet
# lazy manner.

# List of common "/proc/#/stat" fields and the function to interpret the data:
pid_stat_action_list = (
    ("pid", int),
    ("comm", lambda x: x[1:-1]),
    ("state", lambda x: x),
    ("ppid", int),
    ("pgrp", int),
    ("session", int),
    ("tty_num", int),
    ("tty_pgrp", int),
    ("flags", int),
    ("min_flt", int),
    ("cmin_flt", int),
    ("maj_flt", int),
    ("cmaj_flt", int),
    ("utime", int),  # user jiffies (1/100s, not HZ)
    ("stime", int),  # system jiffies (1/100s, not HZ)
    ("cutime", int), # child user jiffies (1/100s, not HZ)
    ("cstime", int), # child system jiffies (1/100s, not HZ)
    ("priority", int),
    ("nice", int),
    ("timeout", int), # 0?
    ("alarm", int),   # seems to be jiffies?
    ("start_time", int), # jiffies after boot started (1/100s, not HZ)
    ("vsize", int),
    ("rss", int),
    ("rss_rlim", int),
    ("start_code", int),
    ("end_code", int),
    ("start_stack", int),
    ("esp", int),
    ("eip", int),
    ("obsolete_pending", int),
    ("obsolete_blocked", int),
    ("obsolete_sigign", int),
    ("obsolete_sigcatch", int),
    ("wchan", int),
    ("nswap", int),
    ("cnswap", int),
    )

# Create map of field names to (index, conversion_function) tuples:
pid_stat_action_map = {}
for i in range(0, len(pid_stat_action_list)):
    pid_stat_action_map[pid_stat_action_list[i][0]] = (
        i, pid_stat_action_list[i][1]
        )

class ProcStatDict(object):
    def __init__(self, pid):
        self.__dict__['_pid'] = pid
        self.__dict__['_dict'] = {}
        self.__dict__['_stats'] = open('/proc/%d/stat' % pid).read().split(' ')
        return
    def _load(self, key):
        i, f = pid_stat_action_map[key]
        value = f(self._stats[i])
        self._dict[key] = value
        return value
    def __len__(self):
        return len(pid_stat_action_list)
    def __iter__(self):
        return iter(pid_stat_action_map.keys())
    def __contains__(self, key):
        return pid_stat_action_map.__contains__(key)
    def __getitem__(self, key):
        return self._dict[key] if self._dict.has_key(key) else self._load(key)
    def __setitem__(self, key, value):
        raise TypeError(
            "'ProcStatDict' object does not support item assignment"
            )
    def __delattr__(self, key):
        raise TypeError(
            "'ProcStatDict' object does not support item deletion"
            )
    def __setattr__(self, name, value):
        raise TypeError(
            "'ProcStatDict' object does not support attribute assignment"
            )
    def keys(self):
        return pid_stat_action_map.keys()
    def has_key(self, key):
        return self.__contains__(key)
    def iterkeys(self):
        return self.__iter__()
    def items(self):
        if self.__len__() > len(self._dict):
            for k in self.iterkeys():
                if k not in self._dict:
                    self._load(k)
        return self._dict.items()
    def iteritems(self):
        # Cheat and pre-load the internal stat dictionary:
        if self.__len__() > len(self._dict):
            for k in self.iterkeys():
                if k not in self._dict:
                    self._load(k)
        return self._dict.iteritems()
    def itervalues(self):
        # Cheat and pre-load the internal stat dictionary:
        if self.__len__() > len(self._dict):
            for k in self.iterkeys():
                if k not in self._dict:
                    self._load(k)
        return self._dict.itervalues()

##
# An object that exposes /proc/#/stat fields as attributes and adds a
# helper `cpu_jiffies' attribute that sums `stime' and `utime' to
# match how ps and top calculate a process' total CPU time.
class ProcStatFields(object):
    def __init__(self, pid):
        self.__dict__['_dict'] = ProcStatDict(pid)
    def __getattr__(self, name):
        if self._dict.has_key(name):
            value = self._dict[name]
            self.__dict__[name] = value
            return value
        if name == 'cpu_jiffies':
            value = self._dict['stime'] # 'System' time.
            value += self._dict['utime'] # 'User' time.
            self.__dict__[name] = value
            return value
        raise AttributeError(
            "type object '%s' has no attribute '%s'" % (
                self.__class__.__name__, name)
            )

##
# Convert jiffies (time values reported in /proc/#/stat fields)
# to a float representation of seconds.
def jiffies_to_seconds(jiffies):
    return jiffies/100.

##
# Convert jiffies (time values reported in /proc/#/stat fields)
# to a dictrionary of 'minutes', 'seconds', and 'centiseconds'.
def ps_time_dict(jiffies):
    scratch = jiffies
    centiseconds = jiffies % 100
    scratch /= 100
    seconds = scratch % 60
    scratch /= 60
    minutes = scratch
    return {
        "minutes":minutes,
        "seconds":seconds,
        "centiseconds":centiseconds,
        }

##
# Return a string representation of jiffies: MM:SS.cc
def ps_time_str(jiffies):
    return ("%(minutes)d:%(seconds)02d.%(centiseconds)02d" %
            ps_time_dict(jiffies))

##
# Factory that returns a ProcStatFields instance for a given process.
def proc_pid_stat(pid):
    return ProcStatFields(pid)

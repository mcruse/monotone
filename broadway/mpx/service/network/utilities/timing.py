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
from mpx.componentry import implements
from interfaces import ITimer
from counting import Counter

class Timer(object):
    implements(ITimer)
    def __init__(self, name = '', firststart = False, firststop = False):
        self.name = name
        self.firststart = firststart
        self.firststop = firststop
        self.tstart = self.tstop = None
        self.startcounter = Counter()
        self.stopcounter = Counter()
        self.resetcounter = Counter()
        self.timetotal = _TimeAccumulator()
    def start(self, tstart = None):
        self.startcounter.increment()
        self.tstart = (self.firststart and self.tstart) or tstart or time.time()
    def stop(self, tstop = None):
        self.startcounter.increment()
        self.tstop = (self.firststop and self.tstop) or tstop or time.time()
    def get_name(self):
        return self.name
    def get_start(self):
        return self.tstart
    def get_stop(self):
        return self.tstop
    def get_lapse(self):
        return (self.tstop or time.time()) - self.tstart
    def reset(self):
        self.resetcounter.increment()
        if self.get_start() and self.get_stop():
            self.timetotal.append(self.get_lapse())
        self.tstart = self.tstop = None
    def __repr__(self):
        timestr = self.get_timestr()
        return '<Timer [%#x] %s: %s>' % (id(self), self.name, timestr)
    def __str__(self):
        return '%s Timer: %s' % (self.name, self.get_timestr(True))
    def get_timestr(self, lapseonly = False):
        start = self.get_start()
        stop = self.get_stop()
        if lapseonly:
            if start and stop:
                timestr = '%0.3f seconds' % self.get_lapse()
            else:
                timestr = 'unavailable'
        else:
            if start:
                startstr = time.strftime('%H:%M:%S', time.localtime(start))
                timestr = 'Started %s' % startstr
                if stop:
                    stopstr = time.strftime('%H:%M:%S', time.localtime(stop))
                    timestr = '%s-%s (%0.3f seconds)'
                    timestr = timestr % (startstr, stopstr, stop - start)
            else:
                timestr = 'Not started'
        return timestr

class _TimeAccumulator(object):
    def __init__(self, startvalue = 0):
        self.incrementcounter = Counter()
        self.accumulated_time = startvalue
    def preappend(self, delta):
        preappend = self.accumulated_time
        self.accumulated_time += delta
        self.incrementcounter.increment()
        return preappend
    def postappend(self, delta):
        self.accumulated_time += delta
        self.incrementcounter.increment()
        return self.accumulated_time
    append = postappend

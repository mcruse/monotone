"""
Copyright (C) 2002 2010 2011 2012 Cisco Systems

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
# Time service.  A service that returns the current time.  Time is expressed in
# seconds since the epochs.  The Time service returns seconds in UTC time.  The
# time service has 2 children, UTC and Local 

import time, os
from mpx import properties as P
from mpx.service import ServiceNode
from mpx.lib import msglog
from mpx.lib.scheduler import scheduler
from mpx.lib.thread_pool import LOW
from time_zone import UTC,Local

##
# Node that returns the current time.
# Current time is expressed in seconds since epochs in UTC time.
# The class has to children, UTC and Local
class Time(ServiceNode):
    ##
    # Adds 2 children, UTC and Local
    def __init__(self):
        ServiceNode.__init__(self)
        UTC().configure({'name':'UTC','parent':self})
        Local().configure({'name':'local','parent':self})
        self._tz_mtime = None
        self._in_err = False
        self._scheduled = None
    
    def start(self):
        self.tz_change_detector()
        ServiceNode.start(self)
    ##
    # @return seconds since the epochs in UTC 
    def get(self, skipCache=0):
        return time.time()
    
    def tz_change_detector(self):
        LOW.queue_noresult(self._tz_change_detector)
    
    def _tz_change_detector(self):
        sched_after = 13
        try:
            if os.path.islink(P.TIMEZONE_FILE):
                mtime = os.lstat(P.TIMEZONE_FILE)[8] 
                if mtime != self._tz_mtime:
                    time.tzset()
                    self._tz_mtime = mtime           
            self._in_err = False
        except:
            if not self._in_err:
                msglog.log(
                    self.as_node_url(), 
                    msglog.types.WARN,
                    'Error monitoring TZ file'
                    )
                msglog.exception()
                self._in_err = True
            sched_after = 61
        self._scheduled = scheduler.after(sched_after, self.tz_change_detector)
        
    def time_call(self, name, *args):
        return getattr(time, name)(*args)
    
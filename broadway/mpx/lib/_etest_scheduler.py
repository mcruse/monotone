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
# Engineering test for:
#
#   http://bugzilla.envenergy.com/bugzilla/show_bug.cgi?id=5241
#
#   Fundimental framework scheduler needs to survive date/time changes.

"""
    $ python -i mpx/lib/_etest_scheduler.pyc

    OVERVIEW

    Invoking this module interactively defines functions that an
    engineer can use to verify that bug #5241 has been fixed.  The two
    major functions are start() and stop() which can be run from the
    interactive prompt.
    
    The start function is used to schedule two callbacks: one is
    scheduled for a relative time and the other for an absolute time
    (identified as 'R' and 'A' respectively).  This program
    calculates both times so that they occur essentially at the same
    time.  Each callback prints a single line and then reschedules
    itself for the next invocation.  The format of the output is:

        c: invocation-time (scheduled-time,)

        Where:

        'c' is the callback identifier ('A' for the absolute
        callback and 'R' for the relative callback).
        'invocation-time' is the actual time that the callback
        was invoked and 'scheduled-time' is the time that the
        callback was scheduled for invocation.

    Example output:

        >>> start()
        R: 1074037689.0 (1074037689.0,)
        A: 1074037689.0 (1074037689.0,)
        A: 1074037690.01 (1074037690.0,)
        R: 1074037690.01 (1074037690.0,)

    Notice that since both callbacks's are scheduled for the same time, it
    is indeterminate which callback is invoked first.

    The start function accepts an optional 'period' argument that can be
    used to adjust the frequency, allowing for periods that exceed the
    fixes 15 second time change detection.

    The stop function sets a flag that will prevent the timers from
    rescheduling after their next invocation.  This is a hacky little
    test, so strange things can happen if you don't wait for both
    callbacks to stop before invoking start again.  There is a clear
    stopped message:

    >>> start()
    A: 1074042337.02 (1074042337.0,)
    R: 1074042337.02 (1074042337.0,)
    >>> stop()
    R: 1074042338.02 (1074042338.0,) - STOPPED
    A: 1074042338.02 (1074042338.0,) - STOPPED

    INTERACTIVE FUNCTION SUMMARY

    >>> help() # Displays this message.
    >>> start(period=1) # Schedule the absolute and relative
                        # timers to run every 'period'
                        # seconds (1 second is the default).
    >>> stop() # Timers will not reschedule after their next
               # invocation.
"""

import time
import math
import os

from mpx.lib.scheduler import scheduler

should_run = 0

def help():
    os.system("cat <<EOF | more \n%s\nEOF" % __doc__)
    return

def relative_callback(period,*args):
    global should_run
    this_time = time.time()
    if should_run:
        next_time = math.floor(time.time()) + period
        scheduler.after(next_time-time.time(),
                        relative_callback, (period,next_time,))
        print 'R: %s %s' % (this_time, args)
    else:
        print 'R: %s %s - STOPPED' % (this_time, args)
    return

def absolute_callback(period,*args):
    global should_run
    this_time = time.time()
    if should_run:
        next_time = math.floor(time.time()) + period
        scheduler.at(next_time,
                     absolute_callback, (period,next_time,))
        print 'A: %s %s' % (this_time, args)
    else:
        print 'A: %s %s - STOPPED' % (this_time, args)
    return

def start(period=1.0, *args):
    global should_run
    if not should_run:
        should_run = 1
        first_time = math.floor(time.time()) + period
        scheduler.at(first_time, absolute_callback, (period,first_time,))
        scheduler.after(first_time-time.time(),
                        relative_callback, (period,first_time,))
    return

def stop():
    global should_run
    should_run = 0
    return

if __name__ == "__main__":
    help()

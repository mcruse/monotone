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
_test_case_uptime.py
"""

import time
from mpx.lib.threading import Thread
from mpx_test import DefaultTestFixture, main

import moab.linux.lib.uptime as _uptime
import moab.linux.lib.uptime_debug as _uptime_debug

debug = 0

num_threads = 10

class TestCThread(Thread):
    def __init__(self):
        self.secs = None
        self.go = 0
        self.going = 0
        self.stopped = 0
        Thread.__init__(self)
    def run(self):
        # Wait until we've been told to go
        while 1:
            if self.go == 1:
                break
            time.sleep(.5)
        self.going = 1
        while 1:
            secs = _uptime_debug.secs()
            if self.go == 0:
                break
        self.secs = _uptime_debug.secs()
        self.stopped = 1
  
class TestCase(DefaultTestFixture):
    # Just a basic sanity check.
    def _test_a(self):
        point_1 = _uptime.secs()
        time.sleep(1)
        point_2 = _uptime.secs()
        diff = point_2 - point_1
        assert abs(1 - diff) < .01, "Difference should be very close to 1, was %f" % diff
        assert diff > 0, "Difference should be positive"

    # Test uptime wrapping functionality.
    def _test_b(self):
        # Override _uptime.secs() with our own function
        mpx.lib.uptime._uptime.secs = mysecs

        tdata = ((500,  500),
                 (700,  700),
                 (300, 1000),
                 (400, 1100),
                 (500, 1200),
                 (600, 1300),
                 (100, 1500),
                 )
        for x in tdata:
            osecs = x[0]
            esecs = x[1]
    
            set_override_secs(osecs)

            secs = mpx.lib.uptime.secs()
            assert secs == esecs, "Seconds should be %f, instead are %f" % (esecs, secs)

    # Test the case where several threads call uptime.secs() right when a
    # wrap occurs.  This tests the wrapping and uptime_offset functionality
    # as well as making sure that we are thread-safe, etc.
    def test_c(self):
        start_secs = 500
        min_secs = 200
        max_secs = min_secs + 50

        # Reset internal data structures in uptime
        _uptime_debug.override_secs(0.0)
        
        # The number of seconds that we expected to see when the threads are
        # done.  It is start_secs (which ends up being the value used as
        # a maximum uptime seen when we wrap) + max_secs.
        exp_secs = start_secs + max_secs
        
        _uptime_debug.override_secs(start_secs)
        

        mythreads = []
        # Create a bunch of threads to call uptime.secs()
        for i in range(0, num_threads):
            nt = TestCThread()
            nt.start()
            mythreads.append(nt)

        # Give the threads a chance to come up
        time.sleep(5)

        if debug:
            print "Telling threads to GO."
        for x in mythreads:
            x.go = 1

        # Give the threads a chance to get started
        all_going = 0
        counter = 0
        while not all_going:
            counter = counter + 1
            if counter > 3000:
                raise "Waited too long for threads to start."
            all_going = 1
            for x in mythreads:
                if not x.going:
                    all_going = 0
            time.sleep(.1)

        if debug:
            print "All threads appear to be going."
            
        # Now cause a wrap
        _uptime_debug.override_secs(min_secs)

        # Give the threads a chance to run for a while
        for c in range(min_secs+1, max_secs):
            time.sleep(.05)
            _uptime_debug.override_secs(c)

        # Now tell all the threads to stop
        if debug:
            print "Telling threads to STOP."
        for x in mythreads:
            x.go = 0

        # Give the threads a chance to finish
        all_stopped = 0
        counter = 0
        while not all_stopped:
            counter = counter + 1
            if counter > 2000:
                raise "Waited too long for threads to stop."
            all_stopped = 1
            for x in mythreads:
                if not x.stopped:
                    all_stopped = 0
            time.sleep(.1)

        # Threads should be done now
        for x in mythreads:
            if x.secs == None:
                raise "At least one thread did not finish (%s)" % str(x)
            else:
                if debug:
                    print 'Got value of %f for %s.' % (x.secs, str(x))
        
        # Check to make sure that what the threads saw falls close to
        # what it should have been.
        for x in mythreads:
            diff = x.secs - exp_secs
            if abs(diff) > 2:
                raise "Thread (%s) did not get the expected value " \
                      "for seconds (%f vs %f)." % (str(x), x.secs,
                                                   exp_secs)

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
        

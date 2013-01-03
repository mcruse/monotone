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
##
# Test cases to exercise the debugging logic of simple locks.
#

from mpx_test import DefaultTestFixture, main

from moab.linux.lib import uptime
from mpx.lib import pause
from mpx.lib.thread import start_new_thread
from mpx.lib.threading import Thread, currentThread
from mpx.lib.debugging_locks import allocate1, allocate2, set_lock_attributes
from mpx.lib.debugging_locks import _ReentrantAcquireAssertion
from mpx.lib.debugging_locks import _WrongThreadAssertion

import mpx.lib.debugging_locks as _dlocks

class TestCase(DefaultTestFixture):
    def test_1_debug_on(self):
        l = allocate1()
        if l.owner is not None:
            raise 'Broken debugging code.'
        if l in l.locked_list:
            raise 'Broken debugging code.'
        l.acquire()
        if l not in l.locked_list:
            raise 'Broken debugging code.'
        if l.owner != currentThread():
            raise 'Broken debugging code.'
        return
    def test_reentrant_acquire(self):
        l = allocate1()
        l.acquire()
        try:
            l.acquire()
        except _ReentrantAcquireAssertion:
            return
        raise 'Failed to detect a reentrant acquire'
    def test_release_by_other_thread(self):
        def acquire_it_elsewhere(lock):
            lock.acquire()
        l = allocate1()
        test_thread = Thread(target=acquire_it_elsewhere,args=(l,))
        test_thread.start()
        while l not in l.locked_list:
            pause(0.1)
        try:
            l.release()
        except _WrongThreadAssertion:
            return
        raise "Failed to detect a release of another thread's acquire."
    #
    def test_acquire_timeout(self):
        _dlocks.approach = 2
        l = allocate2()
        l.acquire()
        for i in (.2, 1, 2, 5, 10):
            set_lock_attributes(l, i, 'Test Lock #1')
            st_time = uptime.secs()
            try:
                l.acquire()
            except:
                pass
            en_time = uptime.secs()
            elapsed_time = en_time - st_time
            if abs(elapsed_time - i) > .2:
                mstr =  'Did not timeout in the specified, time '
                mstr += '(%f seconds).  ' % i
                mstr += 'Instead got %f seconds.' % elapsed_time
                raise mstr


#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()

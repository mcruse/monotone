"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx

from mpx.lib.log import Log
import time
import thread

log = Log("test")

#comfiguring what we want to log ( the fields)
log.configure(("column1",))

def test1(l,value,number_of_times=10):
    print "test1()"
    #start time
    counter = 0      
    while counter < number_of_times:
        #adding some values
        print "calling add entry"
        l.add_entry((value,))
        counter = counter + 1
        
        
thread1Counter=1
thread2Counter=11
thread3Counter=4
thread4Counter=100
thread5Counter=13
thread6Counter=3

thread.start_new_thread(test1,(log,1,thread1Counter))
test1(log,2,thread2Counter)
thread.start_new_thread(test1,(log,3,thread3Counter))
log.lock()
test1(log,4,thread4Counter)
log.unlock()
thread.start_new_thread(test1,(log,5,thread5Counter))
test1(log,6,thread6Counter)

time.sleep(3)

import test_test

result = test_test.test()

print "thread1Counter=" + str(thread1Counter) +  " result=" + str(result["counter1"])
print "thread2Counter=" + str(thread2Counter) +  " result=" + str(result["counter2"])
print "thread3Counter=" + str(thread3Counter) +  " result=" + str(result["counter3"])
print "thread4Counter=" + str(thread4Counter) +  " result=" + str(result["counter4"])
print "thread5Counter=" + str(thread5Counter) +  " result=" + str(result["counter5"])
print "thread6Counter=" + str(thread6Counter) +  " result=" + str(result["counter6"])

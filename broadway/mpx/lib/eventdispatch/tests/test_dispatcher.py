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
from mpx.lib.eventdispatch import dispatcher

dispatch1 = dispatcher.Dispatcher()
class Source(object):
    pass

source1 = Source()
source2 = Source()

args1 = None
def callback1(*args):
    print 'callback 1:\n\t'
    print args
    global args1
    args1 = args

args2 = None
def callback2(*args):
    print 'callback 2:\n\t'
    print args
    global args2
    args2 = args

args3 = None
def callback3(*args):
    print 'callback 3:\n\t'
    print args
    global args3
    args3 = args


class Event1(object): pass

event1 = Event1()
event1.source = source1
event1.subject = None

class Event2(object): pass

event2 = Event2()
event2.source = source2
event2.subject = None

sub1 = dispatch1.register_for_type(callback1,Event1,source1)
sub2 = dispatch1.register_for_type(callback2,Event2,source2)

# callback1 only
dispatch1.dispatch(event1)

# callback2 only
dispatch1.dispatch(event2)

class Event3(Event1):
    pass


event3 = Event3()
event3.source = source1
event3.subject = None
# callback1 should be called...
dispatch1.dispatch(event3)
sub3 = dispatch1.register_for_type(callback1,Event3,source1)
# callback1 should be called twice.
dispatch1.dispatch(event3)
# callback1 should only be called once.
dispatch1.dispatch(event1)

class Event5(object): pass

event5 = Event5()
sub4 = dispatch1.register_for_topic(callback1, 'topic1')
sub5 = dispatch1.register_for_topics(callback2, ['topic2', 'topic3', 'topic4'])
# Should call callback1 one time.
dispatch1.dispatch(event5, 'topic1')
# Should call callback1 one time.
dispatch1.dispatch(event1)
# Should call callback1 twice.
dispatch1.dispatch(event1, 'topic1')
# Should call callback1 once and callback2 once.
dispatch1.dispatch(event5, ['topic2', 'topic1'])
# Should call callback1 once and callback2 once.
dispatch1.dispatch(event5, ['topic2', 'topic1', 'topic3'])
# Should call callback1 twice and callback2 once.
dispatch1.dispatch(event1, ['topic1', 'topic2', 'topic3'])
dispatch1.unregister(sub5)
# Should call callback1 once.
dispatch1.dispatch(event5, ['topic2', 'topic1', 'topic3'])
# Should call callback1 twice.
dispatch1.dispatch(event1, ['topic2', 'topic1', 'topic3'])
dispatch1.unregister(sub4)
# Should call callback1 once.
dispatch1.dispatch(event1, ['topic2', 'topic1', 'topic3'])




# no callbacks
event2.source = source1
dispatch1.dispatch(event2)
event2.source = source2

# callback 2 and 3
sub3 = dispatch1.register_for_type(callback3,Event2)
dispatch1.dispatch(event2)

# callback 3 only
event2.source = source1
dispatch1.dispatch(event2)
event2.source = source2

# callback 1 only
dispatch1.dispatch(event1)
dispatch1.unregister(sub1)
# no callbacks
dispatch1.dispatch(event1)

# callbacks 2 and 3
dispatch1.dispatch(event2)
dispatch1.unregister(sub2)
# callback 3 only.
dispatch1.dispatch(event2)

dispatch1.unregister(sub3)
# no callbacks from either
dispatch1.dispatch(event1)
dispatch1.dispatch(event2)

sub1 = dispatch1.register_for_type(callback1,Event1,source1)
sub2 = dispatch1.register_for_type(callback2,Event2,source2)
sub3 = dispatch1.register_for_type(callback3,Event2)


dispatch1a = dispatcher.Dispatcher()
dispatch1b = dispatcher.Dispatcher()
assert ((dispatch1 is not dispatch1a) and (dispatch1 is not dispatch1b) and (dispatch1a is not dispatch1b)), 'Name of None should always create new.'

dispatch2a = dispatcher.Dispatcher('2')
dispatch2b = dispatcher.Dispatcher('2')
assert dispatch2a is dispatch2b, 'Dispatchers should be same with same id'

dispatch3 = dispatcher.Dispatcher('3')
assert ((dispatch3 is not dispatch2a) and (dispatch3 is not dispatch1a)), 'Different id should have different dispatcher.'

source3 = Source()

class Event3(object): pass

event3 = Event3()
event3.source = source3
event3.subject = None
sub4 = dispatch3.register_for_type(callback3,Event3,source3)


sub5 = dispatch3.register_for_type(callback2,Event2,source3)

# should call callback2 and callback3 from first dispatcher
dispatch1.dispatch(event2)

# should call callback1 from first dispatcher
dispatch1.dispatch(event1)


import time
from mpx.lib.eventdispatch import dispatcher

callback_count = 0
def speed_callback(*args):
    global callback_count
    callback_count += 1
    return callback_count


class Event(object):
    pass


speedevent = Event()
speedd = dispatcher.Dispatcher('Speed Test')
speedsub = speedd.register_for_type(speed_callback,Event)


def test_speed(dispatcher, event, count):
    tstart = time.time()
    for i in range(count):
        dispatcher.dispatch(event)
    tend = time.time()
    tlapse = tend - tstart
    print 'Dispatching %s events took %s seconds.' % (count, tlapse)
    return tlapse


event = Event()
test_speed(speedd, event, 1000)

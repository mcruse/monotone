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
# Refactor 2/11/2007
import time
from mpx.service.alarms2.alarm import Alarm
from mpx.service.alarms2.alarmevent import AlarmEvent, StateChangedEvent
from mpx.service.alarms2.alarmmanager import AlarmManager
from mpx.lib.neode.node import NodeSpace, CompositeNode, RootNode
from mpx.lib.neode.tests import test_tree

test_tree.queue_node(AlarmManager, test_tree.services, 'Alarm Manager')
ns = test_tree.build_tree('mpx://localhost:5150')
root = ns.as_node('/')
services = ns.as_node('/services')
alarm_manager = services.get_child('Alarm Manager')


a1 = ns.create_node(Alarm)
a1.configure({'parent': alarm_manager, 'name': 'Test Alarm 1', 'priority': 'low', 'description': 'Really, this is just test 1'})

a2 = ns.create_node(Alarm)
a2.configure({'parent': alarm_manager, 'name': 'Test Alarm 2', 'priority': 'low', 'description': 'Really, this is just test 2'})

a3 = ns.create_node(Alarm)
a3.configure({'parent': alarm_manager, 'name': 'Test Alarm 3', 'priority': 'low', 'description': 'Really, this is just test 3'})

a4 = ns.create_node(Alarm)
a4.configure({'parent': alarm_manager, 'name': 'Test Alarm 4', 'priority': 'low', 'description': 'Really, this is just test 4'})

a5 = ns.create_node(Alarm)
a5.configure({'parent': alarm_manager, 'name': 'Test Alarm 5', 'priority': 'low', 'description': 'Really, this is just test 5'})

a6 = ns.create_node(Alarm)
a6.configure({'parent': alarm_manager, 'name': 'Test Alarm 6', 'priority': 'low', 'description': 'Really, this is just test 6'})

a7 = ns.create_node(Alarm)
a7.configure({'parent': alarm_manager, 'name': 'Test Alarm 7', 'priority': 'low', 'description': 'Really, this is just test 7'})

a1.start()
a2.start()
a3.start()
a4.start()
a5.start()
a6.start()
a7.start()


class Trigger(object):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

trigger1 = Trigger('Trigger 1')
trigger2 = Trigger('Trigger 2')
trigger3 = Trigger('Trigger 3')
trigger4 = Trigger('Trigger 4')
trigger5 = Trigger('Trigger 5')
trigger6 = Trigger('Trigger 6')

class Callback(object):
    def __init__(self, name):
        self.name = name
        self.subscription = None
        self.event = None
        self.alarm = None
        self.args = None
    def __call__(self, subscription, event, *args):
        self.subscription = subscription
        self.event = event
        self.alarm = event.source
        self.args = args
        print '%s (%s):\n\t%s' % (self.name, id(subscription), event)

callbacks = {}
for i in range(0,10):
    callbacks[i] = Callback('callback%s' % i)

sub1 = a1.register(callbacks[1], AlarmEvent)
sub2 = a2.register(callbacks[2], AlarmEvent)
sub3 = a3.register(callbacks[3], AlarmEvent)
sub4 = a4.register(callbacks[4], AlarmEvent)
sub5 = a5.register(callbacks[5], AlarmEvent)


a1.trigger(trigger1,time.time(),'1-1')
assert AlarmEvent.get_event(callbacks[1].event.id) is callbacks[1].event, (
    'ID lookup failed')
a1.trigger(trigger1,time.time(),'1-2')
a1.trigger(trigger1,time.time(),'1-3')
a1.trigger(trigger1,time.time(),'1-4')
a1.trigger(trigger1,time.time(),'1-5')
a1.clear(trigger1,time.time(),{'a1':'fine'})

a1.trigger(trigger1,time.time(),'1-1')
a1.trigger(trigger1,time.time(),'1-2')
a1.trigger(trigger1,time.time(),'1-3')
a1.trigger(trigger1,time.time(),'1-4')
a1.trigger(trigger1,time.time(),'1-5')

ef = a1.event_factory
inactive = ef.get_by_state(['inactive'])
raised = ef.get_by_state(['raised'])
assert inactive != raised, 'Wrong event lists.'
assert (inactive + raised) == ef.get_by_state(['inactive','raised'])
cleared = ef.get_by_state(['cleared'])
not_cleared = ef.get_by_state([], ['cleared'])
assert (inactive + raised) == not_cleared
assert len(ef.get_by_state()) == 11
assert len(ef.get_by_state([],['inactive'])) == 10

for event in a1.get_events():
    assert AlarmEvent.get_event(event.id) is event, 'Lookup failed'

ec = cleared[-1]
ec.notify('acknowledge',trigger1,time.time(),'Testing close.')


a2.trigger(trigger2,time.time(),{'a2':'too high!'})
assert AlarmEvent.get_event(callbacks[2].event.id) is callbacks[2].event, (
    'ID lookup failed')
a3.trigger(trigger3,time.time(),{'a3':'too high!'})
assert AlarmEvent.get_event(callbacks[3].event.id) is callbacks[3].event, (
    'ID lookup failed')
a4.trigger(trigger4,time.time(),{'a4':'too high!'})
assert AlarmEvent.get_event(callbacks[4].event.id) is callbacks[4].event, (
    'ID lookup failed')
a5.trigger(trigger5,time.time(),{'a5':'too high!'})
assert AlarmEvent.get_event(callbacks[5].event.id) is callbacks[5].event, (
    'ID lookup failed')

sub6 = alarm_manager.register(callbacks[6], AlarmEvent, a6)
a6.trigger(trigger6,time.time(),{'a6':'too stupid!'})

a1.trigger(trigger1,time.time(),{'a1':'too low!'})
a2.trigger(trigger2,time.time(),{'a2':'too low!'})
a3.trigger(trigger3,time.time(),{'a3':'too low!'})
a4.trigger(trigger4,time.time(),{'a4':'too low!'})
a5.trigger(trigger5,time.time(),{'a5':'too low!'})
a6.trigger(trigger6,time.time(),{'a6':'too low!'})

from mpx.service.alarms2.alarmevent import StateChangedEvent

def statecallback(sub, event):
    print 'State Change Callback:'
    print '\tSubcription: %s' % sub
    print '\tevent: %s' % event
    print '\tevent.__dict__.items() -> %s' % (event.__dict__.items,)

a1event = callbacks[1].event
s1 = a1.register(statecallback,StateChangedEvent,None,a1)
a1.trigger(trigger1,time.time(),{'a1':'too low!'})
a2.trigger(trigger1,time.time(),{'a1':'too low!'})
sub = a1.dispatcher.get_subscription(s1)
sub.add_event_subject(a2)
a1.trigger(trigger1,time.time(),{'a1':'too low!'})
a2.trigger(trigger1,time.time(),{'a1':'too low!'})
sub.remove_event_subject(a2)
a1.trigger(trigger1,time.time(),{'a1':'too low!'})
a2.trigger(trigger1,time.time(),{'a1':'too low!'})

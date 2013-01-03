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
import time
from mpx.service.alarms2.presentation.syndication.http import request_handler

SV = request_handler.SyndicationViewer
sv = SV()

from mpx.lib.node import as_node
server = as_node('/services/network/http_server')
c = server.children_nodes()[7].configuration()
c['name'] = 'syndication_viewer'
c['request_path'] = '/syndication'
sv.configure(c)

from mpx.service.alarms2.alarmmanager import AlarmManager
from mpx.lib.neode.node import NodeSpace, CompositeNode, RootNode
from mpx.lib.neode.tests import test_tree

test_tree.queue_node(AlarmManager, test_tree.services, 'Alarm Manager')
ns = test_tree.build_tree('')
services = ns.as_node('/services')
alarm_manager = services.get_child('Alarm Manager')

from mpx.service.alarms2.alarm import Alarm
from mpx.service.alarms2.alarmevent import AlarmEvent, StateChangedEvent

import random


class Trigger(object):
      def __init__(self, name):
          self.name = name
      def __str__(self):
          return self.name


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


alarm_count = 20
alarm_types = ['High Temp ', 'Low Temp ', 'Low Pressure ', 'High Pressure ', 'Fire ', 'Flood ', 'VAV Failure ']
alarm_locations = ['roof top', 'control room', 'Bldg 100', 'Bldg 120', 'Computer room', 'NOC', 'reception']
alarm_priorities = ['High', 'Low', 'Moderate']
alarm_descriptions = ['Critical alarm', 'Requires immediate intervention', 'Nuiscance alarm', 'Test alarm only', 'Drill alarm', 'Fire alarm', 'Equipment danger alarm']
alarms = []


for value in range(0, alarm_count):
    index1 = int(len(alarm_types) * random.random())
    index2 = int(len(alarm_locations) * random.random())
    index3 = int(len(alarm_descriptions) * random.random())
    index4 = int(len(alarm_priorities) * random.random())
    alarms.append({'parent': alarm_manager,
                   'name': alarm_types[index1] + ' (' + alarm_locations[index2] + ')',
                   'priority': alarm_priorities[index4],
                   'description': alarm_descriptions[index3]})

for value in range(0, alarm_count):
    config = alarms[value]
    name = config['name']
    alarm = ns.create_node(Alarm)
    failures = 0
    while True:
        try: alarm.configure(config)
        except ValueError, error:
            failures += 1
            print 'Failed to create alarm with name: %s' % config['name']
            print '\tError: ' + str(error)
            config['name'] = name + ' %s' % failures
            print '\twill retry with name: %s' % config['name']
        else: break
    alarm.start()
    alarm.__trigger = Trigger('Trigger%s (%s)' % (value, config['name']))
    alarm.__callback = Callback('Callback%s (%s)' % (value, config['name']))
    alarm.__subscription = alarm.register(alarm.__callback, AlarmEvent)
    alarms[value] = alarm


fwservices = as_node('/services')
fwservices._add_child(alarm_manager)
sv.start()
sv.nodespace = alarm_manager.nodespace
server.server.install_handler(sv)


actions = [Alarm.trigger, Alarm.clear]
def update():
    for value in range(0, alarm_count):
         actions[int(len(actions)*random.random())](alarms[value], alarms[value].__trigger, time.time() - (len(alarms) - value), 'Random action')

def trigger(index):
    print 'Triggering: ', alarms[index].name
    alarms[index].trigger(alarms[index].__trigger, time.time() - (len(alarms) - index), 'Manual trigger call')

def clear(index):
    print 'Clearing: ', alarms[index].name
    alarms[index].clear(alarms[index].__trigger, time.time() + (len(alarms) - index), 'Manual Clear call')

def name(index):
    print 'Alarm %s: ' % index, alarms[index].name

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
from mpx.lib.node import as_node, as_node_url
from mpx.componentry import implements
cloud_manager = as_node('/services/Cloud Manager')
cm = cloud_manager


ns = cloud_manager.nodespace

class Event(object):
    implements(IPropogatable)
    def __init__(self, event):
        self.event = event
    def serialize(self):
        return str(self.event)

formation = ['http://192.168.0.120/cloud',
             'http://192.168.0.120/cloud1',
             'http://192.168.0.120/cloud2',
             'http://192.168.0.120/cloud3',
             'http://192.168.0.120/cloud4']
cloud_manager.handle_formation_update(str(formation))
e = Event('Event')
cloud_manager.handle_local_event(e, 'shane')


from mpx.lib.node import as_node
am = as_node('/services/Alarm Manager')
import cPickle
from mpx.componentry.interfaces import IPickles
alarms = am.get_alarms()
pickles = []
for alarm in alarms:
    pickles.append(cPickle.dumps(alarm))
for i in range(0, len(pickles)):
    file = open('/tmp/alarm%s' % i, 'w')
    file.write(pickes[i])
    file.close()


a1 = alarms[0]
a1p = IPickles(a1)
a1data = cPickle.dumps(a1p)
a2 = alarms[1]
a2p = IPickles(a2)
a2data = cPickle.dumps(a2p)
f1 = open('/tmp/a1','w')
f1.write(a1data)
f1.close()
f2 = open('/tmp/a2','w')
f2.write(a2data)
f2.close()

f1 = open('/tmp/a1','r')
f2 = open('/tmp/a2','r')
a1data = f1.read()
a2data = f2.read()
f1.close()
f2.close()



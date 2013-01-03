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
import time
# The following two imports are used for generating
# bogus alarms for development & testing purposes.
# When this is no longer required, they can be
# ripped out too.
import os
from random import Random
from mpx.service.hal.alarms import Alarm, NewAlarmsEvent
from mpx.service.hal.client import Client
from mpx.lib.configure import set_attribute, get_attribute, as_boolean
from mpx.lib.node import as_node
from mpx.lib.scheduler import scheduler

# @fixme: Shortly this code will be refactored to use its own thread
#         instead of doing potentially long tasks via the scheduler.
class T100Client(Client):
   def __init__(self):
       Client.__init__(self)
       self.debug = 0
       self.node = None
       self.h_node = None
       self.h_alarms = None
       self.generatebogus = 0
       self.sid = None
       # Seed the random number generator
       self.rand = Random(os.getpid())
   def configure(self,config):
       set_attribute(self,'node','/interfaces/com1/tracer100',config)
       set_attribute(self,'generatebogus',0,config,as_boolean)
       Client.configure(self,config)
   def configuration(self):
       config = Client.configuration(self)
       get_attribute(self,'node',config)
       if self.debug:
           get_attribute(self,'generatebogus',config)
       return config
   def start(self):
       Client.start(self)
       self.h_node = as_node(self.node)
       self.h_alarms = self.h_node.get_child('tracer_alarm_points')
       self.sid = scheduler.after(15, self.poll_alarms)
   def stop(self):
       Client.stop( self )
       if self.sid:
           scheduler.cancel(self.sid)
   def poll_alarms(self):
       if not self._running:
           return
       ret_alarms = []
       new_alarms = self.h_alarms.get_new_alarms()
       
       if new_alarms:
           for rsp in new_alarms:
               if rsp.is_critical():
                   al_type = 'Critical'
               else:
                   al_type = 'Non-Critical'
               a = Alarm(id=rsp.unitnum(),
                         type=al_type,
                         source=rsp.unitnum(),
                         data=rsp.message(),
                         state=rsp.code(),
                         timestamp=rsp.time())
               ret_alarms.append(a)

       if self.generatebogus:
           # Generate bogus alarms roughly 1/16 of the time
           roll = self.rand.randint(1,16)
           if roll == 16:
               how_many = 1
               do_multiple = self.rand.randint(0,1)
               if do_multiple:
                   how_many = self.rand.randint(1,10)
               if self.debug:
                   print '%f: Generating %d random alarm(s).' % (time.time(),
                                                                 how_many)
               for i in range(0, how_many):
                   is_not_crit = self.rand.randint(0,4)
                   if is_not_crit == 0:
                       al_type = 'Critical'
                   else:
                       al_type = 'Non-Critical'
                   a = Alarm(id='test_%.2d' % (i+1),
                             type=al_type,
                             source=1,
                             data='This is test alarm #%d.' % (i+1),
                             state=i,
                             timestamp=time.time())
                   ret_alarms.append(a)

       if ret_alarms:
           ae = NewAlarmsEvent(self, ret_alarms)
           self.parent.event_generate(ae)

           # While we are at it, acknowledge any critical alarms.
           self.h_alarms.ack_critical_alarms()
       
       self.sid = scheduler.after(15, self.poll_alarms)
